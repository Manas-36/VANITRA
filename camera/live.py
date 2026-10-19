"""Vanitra live decoder: phone camera (and/or gloves) -> ISL signs -> English text, on the laptop.

    python camera/live.py --source phone                 # phone browser streams, text + speech come back
    python camera/live.py --source 0 --preview           # webcam / DroidCam / Iriun, with a preview window
    python camera/live.py --source phone --glove COM5    # camera + gloves fused (best accuracy)
    python camera/live.py --replay camera/data/HELLO/manas_x.npz camera/data/WATER/...   # recorded features

Pipeline (every step can be tuned from the command line):
  frame -> MediaPipe hands/pose/face -> 148 features (features.py) -> 25 Hz resampling
        -> sign CNN on the last 1.6 s, every 80 ms -> [fused with the glove CNN]
        -> sign spotter: a sign is accepted when the same gloss stays on top (p >= --conf) for --stable steps
        -> sentence ends after --gap s without a sign (hands down) -> gloss language model (beam search over
           each sign's top guesses) -> ISL grammar -> English (lang/vanitra_lang)
        -> raised brows over the sentence = yes/no question; head shake = negation (non-manual markers)
"""
import argparse
import collections
import os
import sys
import threading
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "ml"))
sys.path.insert(0, os.path.join(ROOT, "lang"))

import vanitra_cnn as vc  # noqa: E402
from features import IDX_BROW_UP, IDX_FACE_PRESENT, IDX_YAW, Resampler, compute  # noqa: E402
from signdata import hands_active  # noqa: E402
from vanitra_lang import BigramLM, Lexicon, SentenceBuilder, SignEvent, Translator  # noqa: E402


class SignModel:
    def __init__(self, path):
        z = np.load(path, allow_pickle=False)
        self.p = {k: z[k] for k in z.files if k[0] in "Wb"}
        self.mean, self.std = z["mean"], z["std"]
        self.labels = [str(s) for s in z["labels"]]
        self.layers = [tuple(int(v) for v in r) for r in z["layers"]] if "layers" in z.files else None
        self.seq = int(z["seq"]) if "seq" in z.files else vc.SEQ_LEN
        self.info = str(z["info"])
        self.rest = self.labels.index("REST") if "REST" in self.labels else -1

    def probs(self, window):
        return vc.forward(self.p, self.mean, self.std, np.asarray(window)[None], layers=self.layers)[0][0]


class SignSpotter:
    """Turns the 12.5 Hz probability stream into discrete sign events with their top-N guesses."""

    def __init__(self, labels, rest, conf=0.55, stable=3, repeat_gap=1.5, nbest=4):
        self.labels, self.rest, self.conf, self.stable, self.repeat_gap, self.nbest = \
            labels, rest, conf, stable, repeat_gap, nbest
        self.run_k, self.run_n, self.run_sum = -1, 0, None
        self.last_k, self.last_t, self.rested = -1, -1e9, True

    def update(self, p, t, force_rest=False):
        k = int(np.argmax(p))
        if force_rest or k == self.rest:
            self.run_k, self.run_n, self.run_sum, self.rested = -1, 0, None, True
            return None
        if p[k] < self.conf:
            self.run_k, self.run_n, self.run_sum = -1, 0, None
            return None
        if k == self.run_k:
            self.run_n += 1
            self.run_sum = self.run_sum + p
        else:
            self.run_k, self.run_n, self.run_sum = k, 1, p.copy()
        if self.run_n != self.stable:
            return None
        if k == self.last_k and not self.rested and t - self.last_t < self.repeat_gap:
            return None
        avg = self.run_sum / self.run_n
        top = np.argsort(-avg)[:self.nbest]
        self.last_k, self.last_t, self.rested = k, t, False
        return SignEvent(t, [(self.labels[i], float(avg[i])) for i in top if i != self.rest], "camera")


class NonManual:
    """Raised brows (yes/no question) and head shake (negation) relative to the signer's own neutral face."""

    def __init__(self, hz=25):
        self.brow_hist = collections.deque(maxlen=hz * 20)
        self.yaw = collections.deque(maxlen=int(hz * 1.2))

    def update(self, f, signing):
        if f[IDX_FACE_PRESENT] < 0.5:
            return 0.0, 0.0
        b = float(f[IDX_BROW_UP])
        if not signing:
            self.brow_hist.append(b)                      # neutral face = while not signing
        base = np.median(self.brow_hist) if len(self.brow_hist) > 10 else 0.15
        brow = float(np.clip((b - base) / 0.15, 0, 1))
        self.yaw.append(float(f[IDX_YAW]) * 90)
        shake = 0.0
        if len(self.yaw) > 8:
            y = np.array(self.yaw)
            d = np.diff(y)
            flips = np.sum(np.sign(d[1:]) != np.sign(d[:-1]))
            if y.max() - y.min() > 12 and flips >= 2:
                shake = 1.0
        return brow, shake


class GloveFusion:
    """Reads the RIGHT glove's USB stream in a thread and gives the glove model's probabilities on demand."""

    def __init__(self, port, model_path, labels):
        import serial
        self.m = SignModel(model_path)
        self.map = [self.m.labels.index(l) if l in self.m.labels else -1 for l in labels]
        self.win = collections.deque(maxlen=self.m.seq)
        self.ser = serial.Serial(port, 115200, timeout=0.5)
        time.sleep(1.5)
        self.ser.write(b"s")
        n_in = len(self.m.mean)
        self.n_in = n_in
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        while True:
            line = self.ser.readline().decode(errors="ignore").strip()
            if line.startswith("D,"):
                v = line.split(",")[2:]
                if len(v) >= 15:
                    a = np.zeros(self.n_in)
                    vals = np.array(v[:self.n_in], dtype=float)
                    a[:len(vals)] = vals
                    self.win.append(a)

    def probs(self):
        if len(self.win) < self.m.seq:
            return None
        pg = self.m.probs(np.array(self.win))
        return np.array([pg[i] if i >= 0 else 1e-4 for i in self.map])


def fuse(p_cam, p_glove, w_cam=0.5):
    if p_glove is None:
        return p_cam
    z = np.exp(w_cam * np.log(p_cam + 1e-6) + (1 - w_cam) * np.log(p_glove + 1e-6))
    return z / z.sum()


class Decoder:
    """Everything after the features. Feed features at 25 Hz with step(); returns messages to show."""

    def __init__(self, model, conf=0.55, stable=3, gap=1.8, w_lm=0.3, every=2, glove=None, w_cam=0.5):
        self.m, self.every, self.glove, self.w_cam = model, every, glove, w_cam
        self.win = collections.deque(maxlen=model.seq)
        self.spot = SignSpotter(model.labels, model.rest, conf, stable)
        lex = Lexicon()
        self.sb = SentenceBuilder(Translator(lex), BigramLM.default(lex.glosses()), gap=gap, w_lm=w_lm)
        self.nm = NonManual()
        self.n = 0
        self.last_top = []

    def step(self, t, f):
        out = []
        self.win.append(f)
        self.n += 1
        signing = bool(hands_active(np.asarray(f)[None])[0])
        brow, shake = self.nm.update(f, signing)
        self.sb.add_nonmanual(brow, shake)
        if len(self.win) == self.m.seq and self.n % self.every == 0:
            p = fuse(self.m.probs(np.array(self.win)), self.glove.probs() if self.glove else None, self.w_cam)
            top = np.argsort(-p)[:3]
            self.last_top = [(self.m.labels[i], float(p[i])) for i in top]
            # no forced REST when the hands drop: the 1.6 s window recognises a sign mostly as it finishes
            ev = self.spot.update(p, t)
            if ev and ev.nbest:
                self.sb.add(ev)
                out.append({"type": "partial", "glosses": self.sb.partial(), "top": self.last_top})
        s = self.sb.poll(t) if not signing else None
        if s:
            out.append({"type": "sentence", "glosses": s.glosses, "text": s.english, "yn": s.yn, "neg": s.neg})
        return out

    def flush(self, t):
        s = self.sb.poll(t, force=True)
        return [{"type": "sentence", "glosses": s.glosses, "text": s.english, "yn": s.yn, "neg": s.neg}] if s else []


def show(msg, tts=None):
    if msg["type"] == "partial":
        tops = "  ".join(f"{g} {p:.0%}" for g, p in msg["top"])
        print(f"   … {' '.join(msg['glosses']):40s} [{tops}]")
    elif msg["type"] == "sentence":
        print(f"\n>> {msg['text']}     ({' '.join(msg['glosses'])})\n")
        if tts:
            tts.say(msg["text"])
            tts.runAndWait()


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--source", help="phone | camera index | stream URL | video file")
    src.add_argument("--replay", nargs="+", help="feature files (.npz from record.py) played back to back")
    ap.add_argument("--model", default=os.path.join(HERE, "models", "sign_model.npz"))
    ap.add_argument("--glove", help="serial port of the RIGHT glove to fuse with the camera")
    ap.add_argument("--glove-model", default=os.path.join(ROOT, "ml", "models", "vanitra_cnn.npz"))
    ap.add_argument("--w-cam", type=float, default=0.5, help="camera weight when fusing with the glove")
    ap.add_argument("--conf", type=float, default=0.55)
    ap.add_argument("--stable", type=int, default=3, help="steps of 80 ms the same sign must stay on top")
    ap.add_argument("--gap", type=float, default=1.8, help="seconds of hands-down that end a sentence")
    ap.add_argument("--w-lm", type=float, default=0.3, help="language model weight (0 = off)")
    ap.add_argument("--left-handed", action="store_true")
    ap.add_argument("--no-face", action="store_true", help="skip face landmarks (faster, no question/negation cues)")
    ap.add_argument("--preview", action="store_true", help="show the camera with landmarks on the laptop")
    ap.add_argument("--speak", action="store_true", help="laptop speaks the sentences (pyttsx3)")
    ap.add_argument("--port", type=int, default=8443)
    args = ap.parse_args()

    if not os.path.exists(args.model):
        sys.exit(f"{args.model} not found - record signs (camera/record.py) and train (camera/train_sign.py)")
    model = SignModel(args.model)
    print("model:", model.info)
    glove = GloveFusion(args.glove, args.glove_model, model.labels) if args.glove else None
    dec = Decoder(model, args.conf, args.stable, args.gap, args.w_lm, glove=glove, w_cam=args.w_cam)
    tts = None
    if args.speak:
        try:
            import pyttsx3
            tts = pyttsx3.init()
        except Exception as e:  # noqa: BLE001
            print("laptop speech off:", e)

    if args.replay:                                       # recorded features: no camera, no MediaPipe
        t = 0.0
        for path in args.replay:
            for f in np.load(path)["x"]:
                for m in dec.step(t, f):
                    show(m, tts)
                t += 1 / 25
        for m in dec.flush(t + 10):
            show(m, tts)
        return

    from landmarks import Landmarker, draw
    from sources import open_source
    lmk = Landmarker(face=not args.no_face)
    frames, bridge = open_source(args.source, args.port)
    rs = Resampler()
    if bridge:
        bridge.send({"type": "status", "text": "laptop ready - start signing"})
    fps_n, fps_t = 0, time.time()
    try:
        for img, t in frames:
            lm = lmk(img, t)
            for tg, f in rs.push(t, compute(lm, args.left_handed)):
                for m in dec.step(tg, f):
                    show(m, tts)
                    if bridge:
                        bridge.send(m)
            fps_n += 1
            if args.preview:
                import cv2
                view = draw(img.copy(), lm)
                top = "  ".join(f"{g} {p:.0%}" for g, p in dec.last_top)
                cv2.putText(view, top, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 255, 200), 2)
                cv2.imshow("Vanitra", view)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            if time.time() - fps_t > 5:
                print(f"   [{fps_n / (time.time() - fps_t):.1f} frames/s processed]")
                fps_n, fps_t = 0, time.time()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
