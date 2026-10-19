"""Feature extraction — a line-for-line mirror of firmware/glove_unit/features.h.

If you change one, change the other, then run `make -C firmware/tests/host` (parity test) and retrain.
A recording is a CSV with columns COLUMNS (one row per 20 ms frame, as streamed by the glove).
"""
import numpy as np

N_FLEX, N_HALL, WIN, N_FEAT = 5, 4, 25, 16
COLUMNS = (["t_ms"] + [f"flex{i+1}" for i in range(N_FLEX)] + [f"hall{i+1}" for i in range(N_HALL)]
           + ["ax", "ay", "az", "gx", "gy", "gz"])
# two gloves: the right glove streams the left glove's frame too (received over ESP-NOW) + a link flag
COLUMNS_2 = COLUMNS + ["L_" + c for c in COLUMNS[1:]] + ["left_ok"]
FEATURE_NAMES = ([f"flex{i+1}_mean" for i in range(N_FLEX)] + [f"hall{i+1}_frac" for i in range(N_HALL)]
                 + ["roll_mean", "pitch_mean", "roll_delta", "pitch_delta",
                    "gyro_mean", "gyro_max", "accel_std"])
RAD = 57.2957795


def _roll(ay, az):
    return np.arctan2(ay, az) * RAD


def _pitch(ax, ay, az):
    return np.arctan2(-ax, np.sqrt(ay * ay + az * az)) * RAD


def _wrap180(d):
    return (d + 180.0) % 360.0 - 180.0


def compute_features(win):
    """win: array (n, 15) = flex5, hall4, ax, ay, az, gx, gy, gz (oldest first). Returns (16,)."""
    win = np.asarray(win, dtype=np.float64)
    n = len(win)
    f = np.zeros(N_FEAT)
    f[0:5] = win[:, 0:5].mean(axis=0)
    f[5:9] = win[:, 5:9].mean(axis=0)
    ax, ay, az, gx, gy, gz = (win[:, 9 + i] for i in range(6))
    roll, pitch = _roll(ay, az), _pitch(ax, ay, az)
    r = roll / RAD
    f[9] = np.arctan2(np.sin(r).sum(), np.cos(r).sum()) * RAD / 180.0
    f[10] = pitch.mean() / 90.0
    f[11] = _wrap180(roll[-1] - roll[0]) / 180.0
    f[12] = (pitch[-1] - pitch[0]) / 90.0
    g = np.sqrt(gx * gx + gy * gy + gz * gz)
    f[13] = g.mean() / 250.0
    f[14] = g.max() / 250.0
    a = np.sqrt(ax * ax + ay * ay + az * az)
    var = (a * a).mean() - a.mean() ** 2
    f[15] = np.sqrt(var) if var > 0 else 0.0
    return f


def windows_from_recording(frames, stride=5):
    """frames: (N, 15) array of one take. Yields feature vectors for every full window."""
    for end in range(WIN, len(frames) + 1, stride):
        yield compute_features(frames[end - WIN:end])
