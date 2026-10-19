"""Camera sign data: loading takes, training augmentation, and the camera network configuration.

Take files: camera/data/<LABEL>/<user>_<time>.npz with
    x      (T, 148) features at 25 Hz (features.py)
    label  gloss, user  signer name
"""
import csv
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "ml"))
sys.path.insert(0, os.path.join(ROOT, "lang"))

import vanitra_cnn as vc  # noqa: E402
from features import IDX_D_PRESENT, IDX_FACE_PRESENT, IDX_N_PRESENT, N_FEAT, N_HAND, N_POSE  # noqa: E402

SEQ = 40                                                 # 40 frames x 40 ms = 1.6 s
LAYERS = [(5, 96, True), (5, 128, True), (3, 128, False)]


def load_vocab():
    with open(os.path.join(ROOT, "ml", "vocabulary.csv"), newline="", encoding="utf-8") as f:
        return [(r["label"], r["say"]) for r in csv.DictReader(f)]


def hands_active(x, low=1.6):
    """Frames where a hand is visible AND raised above about waist height (signing space)."""
    d = (x[:, IDX_D_PRESENT] > 0.5) & (x[:, N_HAND - 3] < low)
    n = (x[:, IDX_N_PRESENT] > 0.5) & (x[:, 2 * N_HAND - 3] < low)
    return d | n


def trim(x, margin=4):
    """Cut the hands-down start and end of a take, so training windows contain the sign, not the wait."""
    a = np.where(hands_active(x))[0]
    if len(a) < 4:
        return x
    return x[max(0, a[0] - margin): a[-1] + margin + 1]


def load_takes(data_dir, labels=None, do_trim=True):
    """-> list of (label, user, path, x (T, 148)). labels=None: every folder is a label.
    Sign takes are trimmed to the active part (REST takes are kept whole)."""
    takes = []
    for d in sorted(glob.glob(os.path.join(data_dir, "*"))):
        label = os.path.basename(d)
        if not os.path.isdir(d) or (labels is not None and label not in labels):
            continue
        for p in sorted(glob.glob(os.path.join(d, "*.npz"))):
            z = np.load(p, allow_pickle=False)
            x = z["x"].astype(np.float32)
            if len(x) < 8:
                continue
            if do_trim and label != "REST":
                x = trim(x)
            user = str(z["user"]) if "user" in z.files else os.path.basename(p).split("_")[0]
            takes.append((label, user, p, x))
    return takes


def pad_to(x, n):
    return np.pad(x, ((0, n - len(x)), (0, 0)), mode="edge") if len(x) < n else x


def eval_windows(x, stride=4):
    """Fixed windows over a take for testing; short takes are edge-padded."""
    return vc.windows(pad_to(x, SEQ), stride, SEQ)


def _rot3(rng, deg):
    return vc._rot(rng, deg)


def augment(x, rng, hand_drop=0.15, face_drop=0.25, mirror=False):
    """One random training window from a take, with camera-realistic variation."""
    w = vc.stretch_crop(pad_to(x, SEQ), rng, SEQ, 0.75, 1.35).astype(np.float64)
    for h in range(2):
        o = h * N_HAND
        pres = w[:, o + N_HAND - 1] > 0.5
        pts = w[:, o:o + 60].reshape(SEQ, 20, 3)
        pts = pts @ _rot3(rng, 12).T * rng.uniform(0.92, 1.08)            # hand pose / size variation
        pts += rng.normal(0, 0.02, pts.shape)                               # landmark jitter
        w[:, o:o + 60] = pts.reshape(SEQ, 60)
        w[:, o + 60:o + 62] = w[:, o + 60:o + 62] * rng.uniform(0.9, 1.1) + rng.normal(0, 0.08, 2)
        w[:, o + 62] *= rng.uniform(0.9, 1.1)
        if rng.random() < hand_drop:                                        # detector misses the hand
            a = rng.integers(0, SEQ - 3)
            b = min(SEQ, a + rng.integers(3, 11))
            w[a:b, o:o + N_HAND] = 0.0
        w[~pres, o:o + N_HAND] = 0.0
    p0 = 2 * N_HAND
    w[:, p0:p0 + N_POSE] = w[:, p0:p0 + N_POSE] * rng.uniform(0.9, 1.1) + rng.normal(0, 0.03, N_POSE)
    if rng.random() < face_drop:                                            # model must not need the face
        w[:, p0 + N_POSE:] = 0.0
    if mirror and rng.random() < 0.5:                                       # left-handed signer
        d, n = w[:, :N_HAND].copy(), w[:, N_HAND:2 * N_HAND].copy()
        w[:, :N_HAND], w[:, N_HAND:2 * N_HAND] = n, d
        for o in (0, N_HAND):
            w[:, o:o + 60:3] *= -1
            w[:, o + 60] *= -1
        w[:, p0:p0 + N_POSE:2] *= -1
    return w


__all__ = ["SEQ", "LAYERS", "N_FEAT", "IDX_D_PRESENT", "IDX_N_PRESENT", "IDX_FACE_PRESENT", "load_vocab",
           "load_takes", "trim", "hands_active", "eval_windows", "augment", "pad_to", "vc"]
