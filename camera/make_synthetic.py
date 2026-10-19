"""SYNTHETIC camera takes (148 features at 25 Hz) to test the camera pipeline without a camera.

    python camera/make_synthetic.py [--users 3 --takes 4 --labels HELLO WATER ...]  -> camera/data_synthetic/

Each label gets an invented smooth trajectory of hand shape + hand position (+ a second hand for some).
Takes start and end with the hands down (REST), like real recordings. Not real ISL - pipeline test only.
"""
import argparse
import hashlib
import os

import numpy as np

from features import N_FEAT, N_HAND
from signdata import HERE, load_vocab

OUT = os.path.join(HERE, "data_synthetic")


def proto(label):
    r = np.random.default_rng(int(hashlib.md5(label.encode()).hexdigest()[:8], 16))
    return dict(shape=r.normal(0, 0.6, (2, 60)), pos=r.uniform([-1.2, -0.8], [1.2, 1.2], (2, 2)),
                move=r.normal(0, 0.4, (2, 2)), freq=r.uniform(0.6, 2.0), two=r.random() < 0.4)


def rest_frames(n, rng):
    x = np.zeros((n, N_FEAT), np.float32)
    x[:, -1] = 1.0                                           # face visible
    x[:, 2 * N_HAND + 6:2 * N_HAND + 10] = [0.3, 2.2, -0.3, 2.2]  # wrists low (pose)
    return x + rng.normal(0, 0.01, x.shape).astype(np.float32)


def sign_frames(label, n, rng, ub):
    P = proto(label)
    t = np.arange(n) / 25.0
    x = np.zeros((n, N_FEAT), np.float32)
    for h in range(2 if P["two"] else 1):
        o = h * N_HAND
        x[:, o:o + 60] = P["shape"][h] + ub[h] + rng.normal(0, 0.03, (n, 60))
        ph = rng.uniform(0, 1)
        x[:, o + 60] = P["pos"][h, 0] + P["move"][h, 0] * np.sin(2 * np.pi * P["freq"] * (t + ph))
        x[:, o + 61] = P["pos"][h, 1] + P["move"][h, 1] * np.cos(2 * np.pi * P["freq"] * (t + ph))
        x[:, o + 62] = 0.45
        x[:, o + 63] = 1.0
    x[:, -1] = 1.0
    return x


def take(label, rng, ub):
    if label == "REST":
        return rest_frames(int(rng.integers(40, 70)), rng)
    pre, post = int(rng.integers(5, 15)), int(rng.integers(5, 15))
    n = int(rng.integers(22, 40))
    return np.concatenate([rest_frames(pre, rng), sign_frames(label, n, rng, ub), rest_frames(post, rng)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=3)
    ap.add_argument("--takes", type=int, default=4)
    ap.add_argument("--labels", nargs="*")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    labels = args.labels or [l for l, _ in load_vocab()]
    rng = np.random.default_rng(3)
    for u in range(args.users):
        ub = np.random.default_rng(100 + u).normal(0, 0.1, (2, 60))
        for l in labels:
            os.makedirs(os.path.join(args.out, l), exist_ok=True)
            for k in range(args.takes):
                np.savez(os.path.join(args.out, l, f"synth{u}_t{k}.npz"), x=take(l, rng, ub), label=l, user=f"synth{u}")
    print(f"wrote {args.users * args.takes * len(labels)} synthetic camera takes to {args.out}")


if __name__ == "__main__":
    main()
