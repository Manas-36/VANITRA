"""Vanitra live decoder — watch the AI read the glove in real time on a laptop.

    python ml/live_decoder.py --port COM5                 # glove plugged in over USB (Windows)
    python ml/live_decoder.py --port /dev/ttyACM0 --speak # Linux/macOS, and say the words aloud
    python ml/live_decoder.py --replay ml/data/HELLO/manas_20261020_101500.csv   # no glove needed

It puts the glove in stream mode ('s'), runs the SAME temporal CNN as the firmware
(ml/models/vanitra_cnn.npz, written by train_cnn.py) on a sliding 1.0 s window every 100 ms, and applies
the SAME acceptance rules as the glove (confidence gate, stability, REST, repeat gap; firmware config.h).
Two gloves: plug in the RIGHT glove; it streams both hands.
Every accepted sign (with its top guesses) goes to the ISL language layer (lang/vanitra_lang): after a
pause of --sentence-gap seconds the gloss sequence is decoded with the gloss language model and turned
into an English sentence (ISL grammar: time first, verb last, wh-word / NOT at the end).

Use it to: demo on a projector, debug which signs get confused, and tune CONF_THRESHOLD/STABLE_COUNT
before flashing. Needs numpy (+ pyserial for --port, pyttsx3 for --speak).
"""
import argparse
import csv
import os
import sys
import time
from collections import deque

import numpy as np

import vanitra_cnn as vc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lang"))
from vanitra_lang import BigramLM, Lexicon, SentenceBuilder, SignEvent, Translator  # noqa: E402


class Model:
    def __init__(self, path):
        z = np.load(path, allow_pickle=False)
        self.p = {k: z[k] for k in z.files if k[0] in "Wb"}
        self.mean, self.std = z["mean"], z["std"]
        self.labels = [str(s) for s in z["labels"]]
        self.say = [str(s) for s in z["say"]]
        self.info = str(z["info"])
        self.rest = self.labels.index("REST") if "REST" in self.labels else -1

    def probs(self, window):
        return vc.forward(self.p, self.mean, self.std, window[None])[0][0]


class Gate:
    """Same rules as onPrediction() in firmware/glove_unit/glove_unit.ino."""

    def __init__(self, rest, conf=0.85, stable=3, repeat_gap=2.5, cooldown=0.6):
        self.rest, self.conf, self.stable, self.repeat_gap, self.cooldown = rest, conf, stable, repeat_gap, cooldown
        self.cand, self.count, self.last, self.last_t, self.rest_since, self.cool_until = -1, 0, -1, 0.0, True, 0.0

    def update(self, k, p, t):
        if k == self.rest:
            self.rest_since, self.cand, self.count = True, -1, 0
            return None
        if p < self.conf or t < self.cool_until:
            self.count = 0
            return None
        self.count = self.count + 1 if k == self.cand else 1
        self.cand = k
        if self.count < self.stable:
            return None
        if k == self.last and not self.rest_since and t - self.last_t < self.repeat_gap:
            return None
        self.last, self.last_t, self.rest_since, self.cool_until = k, t, False, t + self.cooldown
        self.cand, self.count = -1, 0
        return k


def frames_from_serial(port):
    import serial  # pyserial
    ser = serial.Serial(port, 115200, timeout=0.5)
    time.sleep(1.5)
    ser.write(b"s")
    try:
        while True:
            line = ser.readline().decode(errors="ignore").strip()
            if line.startswith("D,"):
                parts = line.split(",")[2:]          # drop "D" and t_ms
                if len(parts) in (15, 31):           # one glove / two gloves (+ left_ok)
                    yield np.array(parts[:30], dtype=float), time.time()
    finally:
        ser.write(b"x")
        ser.close()


def frames_from_csv(path, realtime):
    with open(path, newline="") as f:
        rows = list(csv.reader(f))[1:]
    t0 = time.time()
    for i, r in enumerate(rows):
        t = i * 0.02
        if realtime:
            time.sleep(max(0.0, t0 + t - time.time()))
        yield np.array(r[1:31], dtype=float), t0 + t


def bar(p, width=24):
    n = int(round(p * width))
    return "█" * n + "·" * (width - n)


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--port")
    src.add_argument("--replay", help="a recorded take (CSV from collect_data.py)")
    ap.add_argument("--model", default=os.path.join(HERE, "models", "vanitra_cnn.npz"))
    ap.add_argument("--conf", type=float, default=0.85)
    ap.add_argument("--stable", type=int, default=3)
    ap.add_argument("--sentence-gap", type=float, default=2.5)
    ap.add_argument("--speak", action="store_true", help="say the words with pyttsx3")
    ap.add_argument("--fast", action="store_true", help="replay without waiting (for tests)")
    args = ap.parse_args()

    if not os.path.exists(args.model):
        sys.exit(f"{args.model} not found - run python ml/train_cnn.py first")
    m = Model(args.model)
    print(f"model: {m.info}")
    if "SYNTHETIC" in m.info:
        print("!! placeholder model trained on synthetic data - retrain on real glove recordings !!")
    tts = None
    if args.speak:
        try:
            import pyttsx3
            tts = pyttsx3.init()
        except Exception as e:  # noqa: BLE001
            print("speech off:", e)

    gate = Gate(m.rest, args.conf, args.stable)
    lex = Lexicon()
    sb = SentenceBuilder(Translator(lex), BigramLM.default(lex.glosses()), gap=args.sentence_gap)
    win = deque(maxlen=vc.SEQ_LEN)
    n_in, transcript, n, t = len(m.mean), [], 0, 0.0
    stream = frames_from_serial(args.port) if args.port else frames_from_csv(args.replay, not args.fast)

    def finish(sent):
        transcript.append(sent.english)
        print(f"\n>> {sent.english}     ({' '.join(sent.glosses)})")
        if tts:
            tts.say(sent.english)
            tts.runAndWait()

    try:
        for frame, t in stream:
            f = np.zeros(n_in)
            f[:min(n_in, len(frame))] = frame[:n_in]
            win.append(f)
            n += 1
            if len(win) < vc.SEQ_LEN or n % 5:
                continue
            p = m.probs(np.array(win))
            top = np.argsort(p)[::-1][:4]
            said = gate.update(int(top[0]), float(p[top[0]]), t)
            live = "  ".join(f"{m.labels[k]:>10s} {bar(p[k], 10)} {p[k]:4.0%}" for k in top[:3])
            sys.stdout.write("\r" + live + "   ")
            sys.stdout.flush()
            if said is not None:
                sb.add(SignEvent(t, [(m.labels[k], float(p[k])) for k in top if k != m.rest]))
                print(f"\n   sign: {m.labels[said]}  ({p[said]:.0%})   so far: {' '.join(sb.partial())}")
            if int(top[0]) == m.rest:
                sent = sb.poll(t)
                if sent:
                    finish(sent)
    except KeyboardInterrupt:
        pass
    sent = sb.poll(t + 999, force=True)
    if sent:
        finish(sent)
    print("\n\nTranscript:")
    for s in transcript:
        print("  -", s)

if __name__ == "__main__":
    main()
