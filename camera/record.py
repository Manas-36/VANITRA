"""Record camera training data: each take = one sign, saved as 25 Hz landmark features (no video kept).

    python camera/record.py --source phone --user manas                    # all signs in ml/vocabulary.csv
    python camera/record.py --source phone --user manas --labels WATER HELLO REST --takes 8
    python camera/record.py --source 0 --user pragati --preview            # webcam with a preview window
    python camera/record.py --source phone --user manas --sentences        # whole sentences (for testing)

How a take goes: the prompt appears on the phone and in the terminal -> 3-2-1 -> "GO": sign ONCE at a
natural speed with hands starting and ending DOWN -> saved to camera/data/<LABEL>/<user>_<time>.npz.
Only landmark numbers are stored (privacy: no faces or video on disk), so the files are tiny.

Good data beats a big model (docs/training_guide.md):
  * >= 10 takes per sign per signer, >= 3 signers (+ a Deaf ISL signer as the reference)
  * vary distance, light, background, clothing, sitting/standing, phone angle between sessions
  * record REST generously: hands down, scratching face, fixing hair, holding a phone, talking
"""
import argparse
import os
import sys
import time

import numpy as np

from features import HZ, Resampler, compute
from signdata import HERE, ROOT, load_vocab

sys.path.insert(0, os.path.join(ROOT, "lang"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--labels", nargs="*")
    ap.add_argument("--takes", type=int, default=5)
    ap.add_argument("--seconds", type=float, default=3.0, help="length of one take (REST takes x2)")
    ap.add_argument("--sentences", action="store_true", help="record sentences from lang/data/isl_corpus.txt")
    ap.add_argument("--out", default=None)
    ap.add_argument("--left-handed", action="store_true")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--port", type=int, default=8443)
    args = ap.parse_args()

    from landmarks import Landmarker, draw
    from sources import open_source

    if args.sentences:
        from vanitra_lang import load_corpus
        items = [(" ".join(g), en) for g, en, _m in load_corpus()]
        out_dir = args.out or os.path.join(HERE, "data_sentences")
    else:
        vocab = load_vocab()
        if args.labels:
            vocab = [v for v in vocab if v[0] in args.labels]
        items = [(l, s or "(no sign: hands down / idle)") for l, s in vocab]
        out_dir = args.out or os.path.join(HERE, "data")
    plan = [(g, en, k) for g, en in items for k in range(args.takes)]

    lmk = Landmarker()
    frames, bridge = open_source(args.source, args.port)

    def say(text):
        print(text)
        if bridge:
            bridge.send({"type": "prompt", "text": text})

    rs = Resampler()
    i, state, t_state, buf = 0, "ready", None, []
    say(f"{len(plan)} takes. Stand so your head, shoulders and hands are in view.")
    try:
        for img, t in frames:
            lm = lmk(img, t)
            feats = rs.push(t, compute(lm, args.left_handed))
            if t_state is None:
                t_state = t
            g, en, k = plan[i]
            dur = args.seconds * (2 if g == "REST" else 1) * (2.5 if args.sentences else 1)
            if state == "ready" and t - t_state > 1.5:
                state, t_state = "count", t
            elif state == "count":
                n = 3 - int(t - t_state)
                say(f"[{i + 1}/{len(plan)}]  {g}  —  \"{en}\"   take {k + 1}   ...{n}" if n > 0 else
                    f"GO:  {g}")
                if n <= 0:
                    state, t_state, buf = "rec", t, []
            elif state == "rec":
                buf += [f for _tg, f in feats]
                if t - t_state >= dur:
                    x = np.array(buf, np.float32)
                    stamp = time.strftime("%Y%m%d_%H%M%S")
                    if args.sentences:
                        os.makedirs(out_dir, exist_ok=True)
                        path = os.path.join(out_dir, f"{args.user}_{stamp}_{i}.npz")
                        np.savez(path, x=x, glosses=np.array(g.split()), english=en, user=args.user, hz=HZ)
                    else:
                        os.makedirs(os.path.join(out_dir, g), exist_ok=True)
                        path = os.path.join(out_dir, g, f"{args.user}_{stamp}_{k}.npz")
                        np.savez(path, x=x, label=g, user=args.user, hz=HZ)
                    seen = x[:, 63].mean() if len(x) else 0
                    say(f"saved {len(x)} frames -> {os.path.relpath(path, ROOT)}  (dominant hand seen {seen:.0%})")
                    i += 1
                    if i >= len(plan):
                        say("done - thank you!")
                        break
                    state, t_state = "ready", t
            if args.preview:
                import cv2
                cv2.putText(img, f"{g} [{state}]", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
                cv2.imshow("Vanitra record", draw(img, lm))
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
