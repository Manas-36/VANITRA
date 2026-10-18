"""Generate SYNTHETIC glove recordings so the training pipeline can be tested without hardware.

    python ml/make_synthetic_data.py            -> ml/data_synthetic/<LABEL>/*.csv

The numbers are invented hand shapes + motions, NOT real sign data. A model trained on them only
proves the pipeline and the firmware run end to end. Record real data with collect_data.py.
"""
import csv
import math
import os

import numpy as np

from vanitra_features import COLUMNS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data_synthetic")
HZ = 50

#            flex (thumb..little, 0 straight 1 bent)   hall (H1..H4)  roll pitch  motion
PROTO = {
    "REST":       ((0.20, 0.25, 0.25, 0.30, 0.30), (0, 0, 0, 0), 0, -10, "drift"),
    "HELLO":      ((0.00, 0.00, 0.00, 0.00, 0.00), (0, 0, 0, 0), 80, 30, "out"),
    "THANK_YOU":  ((0.05, 0.00, 0.00, 0.00, 0.00), (0, 0, 0, 0), 10, 40, "down"),
    "YES":        ((0.60, 1.00, 1.00, 1.00, 1.00), (0, 0, 1, 0), 10, 0, "nod"),
    "NO":         ((0.50, 0.20, 0.20, 1.00, 1.00), (1, 0, 0, 0), 60, 10, "tap"),
    "PLEASE":     ((0.05, 0.00, 0.00, 0.00, 0.00), (0, 0, 0, 0), 85, 0, "circle"),
    "SORRY":      ((0.10, 1.00, 1.00, 1.00, 1.00), (0, 0, 1, 0), 85, 0, "circle"),
    "HELP":       ((0.00, 1.00, 1.00, 1.00, 1.00), (0, 0, 1, 0), 90, 0, "lift"),
    "WATER":      ((0.80, 0.00, 0.00, 0.00, 1.00), (0, 0, 0, 0), 70, 40, "tap"),
    "FOOD":       ((0.50, 0.50, 0.50, 0.50, 0.50), (1, 0, 0, 0), 60, 50, "tap"),
    "TOILET":     ((0.50, 0.90, 1.00, 1.00, 1.00), (0, 1, 0, 0), 20, 20, "shake"),
    "STOP":       ((0.05, 0.00, 0.00, 0.00, 0.00), (0, 0, 0, 0), 90, 10, "chop"),
    "GOOD":       ((0.05, 0.00, 0.00, 0.00, 0.00), (0, 0, 0, 0), 0, 30, "down"),
    "BAD":        ((0.05, 0.00, 0.00, 0.00, 0.00), (0, 0, 0, 0), 0, 20, "flip"),
    "NAME":       ((0.80, 0.00, 0.00, 1.00, 1.00), (0, 0, 0, 1), 90, 0, "tap"),
    "I_LOVE_YOU": ((0.00, 0.00, 1.00, 1.00, 0.00), (0, 0, 1, 0), 0, 60, "none"),
    "WHAT":       ((0.00, 0.00, 0.00, 0.00, 0.00), (0, 0, 0, 0), 175, 0, "shake"),
    "WHERE":      ((0.80, 0.00, 1.00, 1.00, 1.00), (0, 0, 1, 0), 10, 60, "wave"),
    "DOCTOR":     ((0.80, 0.30, 0.30, 0.30, 1.00), (0, 0, 0, 0), 0, 0, "tap"),
    "OK":         ((0.50, 0.60, 0.00, 0.00, 0.00), (1, 0, 0, 0), 30, 50, "none"),
    "WAIT":       ((0.00, 0.00, 0.00, 0.00, 0.00), (0, 0, 0, 0), 175, 10, "wiggle"),
}


def motion(kind, t, rng):
    """Returns (droll, dpitch, flex_wiggle) in degrees / flex units at time t (s)."""
    w = 2 * math.pi
    if kind == "nod":    return 0, 25 * math.sin(w * 2.0 * t), 0
    if kind == "tap":    return 0, 15 * abs(math.sin(w * 1.5 * t)), 0
    if kind == "shake":  return 30 * math.sin(w * 2.5 * t), 0, 0
    if kind == "wave":   return 35 * math.sin(w * 1.5 * t), 0, 0
    if kind == "circle": return 20 * math.sin(w * 1.0 * t), 20 * math.cos(w * 1.0 * t), 0
    if kind == "out":    return 0, -40 * ((t * 1.2) % 1.0), 0
    if kind == "down":   return 0, -50 * ((t * 1.0) % 1.0), 0
    if kind == "lift":   return 0, 35 * ((t * 1.0) % 1.0), 0
    if kind == "chop":   return 0, -60 * ((t * 1.6) % 1.0), 0
    if kind == "flip":   return 170 * ((t * 0.9) % 1.0), -20 * ((t * 0.9) % 1.0), 0
    if kind == "wiggle": return 0, 0, 0.25 * math.sin(w * 4 * t)
    if kind == "drift":  return 8 * math.sin(w * 0.2 * t + rng.uniform(0, 6)), 6 * math.sin(w * 0.13 * t), 0
    return 0, 0, 0


def take(label, user_rng, rng, seconds=4.0):
    flex0, hall0, roll0, pitch0, kind = PROTO[label]
    flex_bias = user_rng.normal(0, 0.06, 5)
    roll_bias, pitch_bias = user_rng.normal(0, 8), user_rng.normal(0, 6)
    speed = rng.uniform(0.8, 1.25)
    rows, prev = [], None
    n = int(seconds * HZ)
    for i in range(n):
        t = i / HZ * speed
        dr, dp, wig = motion(kind, t, rng)
        roll = roll0 + roll_bias + dr + rng.normal(0, 1.5)
        pitch = float(np.clip(pitch0 + pitch_bias + dp + rng.normal(0, 1.5), -85, 85))
        flex = np.clip(np.array(flex0) + flex_bias + rng.normal(0, 0.03, 5)
                       + np.array([wig, wig, -wig, wig, -wig]), 0, 1)
        hall = [h if rng.random() > 0.03 else 1 - h for h in hall0]
        r, p = math.radians(roll), math.radians(pitch)
        ax = -math.sin(p) + rng.normal(0, 0.03)
        ay = math.cos(p) * math.sin(r) + rng.normal(0, 0.03)
        az = math.cos(p) * math.cos(r) + rng.normal(0, 0.03)
        if prev is None:
            gx = gy = gz = 0.0
        else:
            gx = (roll - prev[0]) * HZ + rng.normal(0, 3)
            gy = (pitch - prev[1]) * HZ + rng.normal(0, 3)
            gz = rng.normal(0, 3)
        prev = (roll, pitch)
        rows.append([i * 20, *np.round(flex, 3), *hall, round(ax, 3), round(ay, 3), round(az, 3),
                     round(gx, 1), round(gy, 1), round(gz, 1)])
    return rows


def main(users=6, takes=3, seed=7):
    rng = np.random.default_rng(seed)
    for label in PROTO:
        os.makedirs(os.path.join(OUT, label), exist_ok=True)
    for u in range(users):
        user_rng = np.random.default_rng(seed * 100 + u)
        for label in PROTO:
            for k in range(takes):
                path = os.path.join(OUT, label, f"synth{u}_t{k}.csv")
                with open(path, "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(COLUMNS)
                    w.writerows(take(label, user_rng, rng))
    print(f"wrote {users * takes * len(PROTO)} synthetic takes to {OUT}")


if __name__ == "__main__":
    main()
