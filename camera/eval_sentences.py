"""Measure (and tune) continuous sentence decoding on recorded sentences.

    python camera/record.py --source phone --user pragati --sentences --takes 1     # record test sentences
    python camera/eval_sentences.py                                                  # gloss error rate
    python camera/eval_sentences.py --grid                                           # tune the decoder

Reports gloss error rate (GER = substitutions + insertions + deletions / reference glosses, like WER) and
exact-sentence accuracy, with the language model on and off. --grid searches conf / stable / LM weight
and prints the best setting to pass to live.py. Use signers that the model was NOT trained on.
"""
import argparse
import glob
import itertools
import os

import numpy as np

from live import Decoder, SignModel
from signdata import HERE


def edit_distance(a, b):
    d = np.arange(len(b) + 1)
    for i, x in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (x != y))
    return int(d[-1])


def run(model, items, conf, stable, w_lm, gap=1.8):
    errs = refs = exact = 0
    for x, ref in items:
        dec = Decoder(model, conf=conf, stable=stable, gap=gap, w_lm=w_lm)
        hyp, t = [], 0.0
        for i, f in enumerate(x):
            t = i / 25
            hyp += [g for m in dec.step(t, f) if m["type"] == "sentence" for g in m["glosses"]]
        hyp += [g for m in dec.flush(t + 10) for g in m["glosses"]]
        e = edit_distance(hyp, ref)
        errs, refs, exact = errs + e, refs + len(ref), exact + (e == 0)
    return errs / max(refs, 1), exact / max(len(items), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "data_sentences"))
    ap.add_argument("--model", default=os.path.join(HERE, "models", "sign_model.npz"))
    ap.add_argument("--grid", action="store_true")
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(args.data, "*.npz")))
    if not files:
        raise SystemExit(f"no sentence recordings in {args.data} (camera/record.py --sentences)")
    items = [(np.load(f)["x"], [str(g) for g in np.load(f)["glosses"]]) for f in files]
    m = SignModel(args.model)
    for w in (0.0, 0.3):
        ger, ex = run(m, items, 0.55, 3, w)
        print(f"LM weight {w}:  gloss error rate {ger:.1%} · exact sentences {ex:.1%}  ({len(items)} sentences)")
    if args.grid:
        best = None
        for conf, stable, w in itertools.product((0.45, 0.55, 0.65), (2, 3, 4), (0.15, 0.3, 0.5)):
            ger, ex = run(m, items, conf, stable, w)
            if best is None or ger < best[0]:
                best = (ger, ex, conf, stable, w)
        ger, ex, conf, stable, w = best
        print(f"best: --conf {conf} --stable {stable} --w-lm {w}  ->  GER {ger:.1%}, exact {ex:.1%}")


if __name__ == "__main__":
    main()
