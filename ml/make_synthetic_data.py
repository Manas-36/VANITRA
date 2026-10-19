"""Generate SYNTHETIC two-glove recordings so the training pipeline can be tested without hardware.

    python ml/make_synthetic_data.py              -> ml/data_synthetic/<LABEL>/synth<u>_t<k>.csv (31 columns)
    python ml/make_synthetic_data.py --one-glove  -> 16-column takes (right glove only)

Every label in ml/vocabulary.csv gets an invented, label-seeded "sign": a right-hand shape + contacts +
orientation + motion, and a left-hand role drawn from the three kinds of two-handed sign found in sign
languages (one-handed / both hands active and symmetric / left hand a still base). The numbers are NOT
real ISL signs. A model trained on them only proves the pipeline, firmware and simulation run end to end.
Record real data with collect_data.py.
"""
import argparse
import csv
import hashlib
import math
import os

import numpy as np

from vanitra_features import COLUMNS, COLUMNS_2

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data_synthetic")
HZ = 50
SHAPES = [(0.0, 0.0, 0.0, 0.0, 0.0), (0.6, 1.0, 1.0, 1.0, 1.0), (0.8, 0.0, 1.0, 1.0, 1.0), (0.8, 0.0, 0.0, 1.0, 1.0),
          (0.0, 0.0, 1.0, 1.0, 0.0), (0.5, 0.5, 0.5, 0.5, 0.5), (0.8, 0.0, 0.0, 0.0, 1.0), (0.0, 1.0, 1.0, 1.0, 1.0),
          (0.5, 0.6, 0.0, 0.0, 0.0), (0.8, 0.3, 0.3, 0.3, 1.0), (0.2, 0.0, 0.0, 0.0, 0.0), (0.8, 1.0, 1.0, 1.0, 0.0)]
MOTIONS = ["none", "nod", "tap", "shake", "wave", "circle", "out", "down", "lift", "chop", "flip", "wiggle"]


def load_labels():
    with open(os.path.join(HERE, "vocabulary.csv"), newline="", encoding="utf-8") as f:
        return [r["label"] for r in csv.DictReader(f)]


def proto(label):
    """Deterministic invented sign for a label."""
    if label == "REST":
        return dict(shape=(0.2, 0.25, 0.25, 0.3, 0.3), hall=(0, 0, 0, 0), roll=0, pitch=-10, motion="drift",
                    left="rest", lshape=(0.2, 0.25, 0.25, 0.3, 0.3), lroll=0, lpitch=-10)
    r = np.random.default_rng(int(hashlib.md5(label.encode()).hexdigest()[:8], 16))
    hall = tuple(int(x) for x in (r.random(4) < 0.18))
    return dict(shape=SHAPES[r.integers(len(SHAPES))], hall=hall, roll=float(r.choice([0, 30, 60, 90, 175])),
                pitch=float(r.choice([-20, 0, 20, 40, 60])), motion=str(r.choice(MOTIONS)),
                left=str(r.choice(["rest", "rest", "symmetric", "base"])), lshape=SHAPES[r.integers(len(SHAPES))],
                lroll=float(r.choice([0, 90, 175])), lpitch=float(r.choice([0, 30])))


def motion(kind, t, phase):
    """(droll, dpitch, flex_wiggle) at time t (s)."""
    w = 2 * math.pi
    t = t + phase
    return {"nod": (0, 25 * math.sin(w * 2.0 * t), 0), "tap": (0, 15 * abs(math.sin(w * 1.5 * t)), 0),
            "shake": (30 * math.sin(w * 2.5 * t), 0, 0), "wave": (35 * math.sin(w * 1.5 * t), 0, 0),
            "circle": (20 * math.sin(w * t), 20 * math.cos(w * t), 0), "out": (0, -40 * ((t * 1.2) % 1.0), 0),
            "down": (0, -50 * (t % 1.0), 0), "lift": (0, 35 * (t % 1.0), 0), "chop": (0, -60 * ((t * 1.6) % 1.0), 0),
            "flip": (170 * ((t * 0.9) % 1.0), -20 * ((t * 0.9) % 1.0), 0), "wiggle": (0, 0, 0.25 * math.sin(w * 4 * t)),
            "drift": (8 * math.sin(w * 0.2 * t), 6 * math.sin(w * 0.13 * t), 0)}.get(kind, (0, 0, 0))


def hand_frames(shape, hall, roll0, pitch0, kind, n, speed, phase, ubias, rng):
    flex_bias, roll_b, pitch_b = ubias
    rows, prev = [], None
    for i in range(n):
        dr, dp, wig = motion(kind, i / HZ * speed, phase)
        roll = roll0 + roll_b + dr + rng.normal(0, 1.5)
        pitch = float(np.clip(pitch0 + pitch_b + dp + rng.normal(0, 1.5), -85, 85))
        flex = np.clip(np.array(shape) + flex_bias + rng.normal(0, 0.03, 5) + np.array([wig, wig, -wig, wig, -wig]), 0, 1)
        h = [x if rng.random() > 0.03 else 1 - x for x in hall]
        r, p = math.radians(roll), math.radians(pitch)
        acc = (-math.sin(p) + rng.normal(0, 0.03), math.cos(p) * math.sin(r) + rng.normal(0, 0.03),
               math.cos(p) * math.cos(r) + rng.normal(0, 0.03))
        gyro = (0.0, 0.0, 0.0) if prev is None else ((roll - prev[0]) * HZ + rng.normal(0, 3),
                                                     (pitch - prev[1]) * HZ + rng.normal(0, 3), rng.normal(0, 3))
        prev = (roll, pitch)
        rows.append([*np.round(flex, 3), *h, *(round(a, 3) for a in acc), *(round(g, 1) for g in gyro)])
    return rows


def take(label, user_rng, rng, two, seconds=4.0):
    P = proto(label)
    n = int(seconds * HZ)
    speed, phase = rng.uniform(0.8, 1.25), rng.uniform(0, 1)
    ub = (user_rng.normal(0, 0.06, 5), user_rng.normal(0, 8), user_rng.normal(0, 6))
    right = hand_frames(P["shape"], P["hall"], P["roll"], P["pitch"], P["motion"], n, speed, phase, ub, rng)
    if not two:
        return [[i * 20, *r] for i, r in enumerate(right)]
    lb = (user_rng.normal(0, 0.06, 5), user_rng.normal(0, 8), user_rng.normal(0, 6))
    if P["left"] == "symmetric":              # both hands do the same thing (mirrored roll)
        left = hand_frames(P["shape"], (0, 0, 0, 0), -P["roll"], P["pitch"], P["motion"], n, speed, phase, lb, rng)
    elif P["left"] == "base":                 # left hand is a still base the right hand acts on
        left = hand_frames(P["lshape"], (0, 0, 0, 0), P["lroll"], P["lpitch"], "none", n, speed, phase, lb, rng)
    else:                                     # one-handed sign: left hand relaxed and drifting
        left = hand_frames((0.2, 0.25, 0.25, 0.3, 0.3), (0, 0, 0, 0), 0, -10, "drift", n, speed, phase, lb, rng)
    return [[i * 20, *r, *l, 1] for i, (r, l) in enumerate(zip(right, left))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=6)
    ap.add_argument("--takes", type=int, default=3)
    ap.add_argument("--one-glove", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    labels = load_labels()
    cols = COLUMNS if args.one_glove else COLUMNS_2
    for u in range(args.users):
        user_rng = np.random.default_rng(args.seed * 100 + u)
        for label in labels:
            os.makedirs(os.path.join(OUT, label), exist_ok=True)
            for k in range(args.takes):
                with open(os.path.join(OUT, label, f"synth{u}_t{k}.csv"), "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(cols)
                    w.writerows(take(label, user_rng, rng, not args.one_glove))
    print(f"wrote {args.users * args.takes * len(labels)} synthetic {'one' if args.one_glove else 'two'}-glove takes to {OUT}")


if __name__ == "__main__":
    main()
