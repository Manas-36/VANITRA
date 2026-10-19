"""Vanitra temporal CNN — a tiny 1D convolutional network that reads the raw glove signal over time.

Pure NumPy (no PyTorch / TensorFlow), so it trains on any laptop and its maths can be mirrored
line-for-line in C++ (firmware/glove_unit/cnn.h). Change both together.

Input  : one window of SEQ_LEN calibrated frames x n_in channels, oldest first
         one glove  (15): flex1..5 (0 straight..1 bent), hall1..4 (0/1), ax, ay, az (g), gx, gy, gz (deg/s)
         two gloves (30): the 15 right-glove channels, then the same 15 for the left glove (L_ prefix)
         camera   (148): landmark features from camera/features.py (other layer sizes, same maths)
Network: per-channel standardise
         conv1d k5  15->24  ReLU  maxpool 2      (50 -> 25 steps)
         conv1d k5  24->32  ReLU  maxpool 2      (25 -> 12 steps)
         conv1d k3  32->32  ReLU
         global average pool + global max pool  (64 numbers)
         dense 64 -> N classes, softmax
All convolutions use 'same' zero padding. About 10 k weights (40 KB as float32), ~0.23 M multiply-adds.

Why a CNN and not only the 16-feature MLP (model v1)?  The MLP averages each 0.5 s window, so it
cannot see ORDER (bend-then-lift vs lift-then-bend) and only sees half a sign. The CNN looks at
1.0 s and learns its own motion detectors, so dynamic signs and new users are handled better.
"""
import numpy as np

SEQ_LEN = 50          # 50 frames x 20 ms = 1.0 s
HAND_CH = ([f"flex{i+1}" for i in range(5)] + [f"hall{i+1}" for i in range(4)]
           + ["ax", "ay", "az", "gx", "gy", "gz"])
N_CH = 15                                                    # one glove
CHANNELS = HAND_CH
CHANNELS_2 = HAND_CH + ["L_" + c for c in HAND_CH]           # two gloves (30)
LAYERS = [(5, 24, True), (5, 32, True), (3, 32, False)]      # (kernel, out channels, maxpool after)


# ----------------------------------------------------------------------------- init
def init_params(n_out, seed=0, n_in=N_CH, layers=None):
    layers = layers or LAYERS
    rng = np.random.default_rng(seed)
    p, cin = {}, n_in
    for i, (k, cout, _pool) in enumerate(layers, 1):
        fan_in = k * cin
        p[f"W{i}"] = (rng.standard_normal((fan_in, cout)) * np.sqrt(2.0 / fan_in)).astype(np.float64)
        p[f"b{i}"] = np.zeros(cout)
        cin = cout
    p["Wd"] = rng.standard_normal((2 * cin, n_out)) * np.sqrt(1.0 / (2 * cin))
    p["bd"] = np.zeros(n_out)
    return p


# ----------------------------------------------------------------------------- layers
def _im2col(x, k):
    """x (B, L, C) -> (B*L, k*C), 'same' zero padding. Row order (j, c) matches cnn.h."""
    B, L, C = x.shape
    p = k // 2
    xp = np.zeros((B, L + 2 * p, C), dtype=x.dtype)
    xp[:, p:p + L] = x
    cols = np.stack([xp[:, j:j + L, :] for j in range(k)], axis=2)      # (B, L, k, C)
    return cols.reshape(B * L, k * C)


def _col2im(dcols, B, L, C, k):
    p = k // 2
    d = dcols.reshape(B, L, k, C)
    dxp = np.zeros((B, L + 2 * p, C))
    for j in range(k):
        dxp[:, j:j + L, :] += d[:, :, j, :]
    return dxp[:, p:p + L]


def _pool_fwd(x):
    B, L, C = x.shape
    lo = L // 2
    xr = x[:, :2 * lo].reshape(B, lo, 2, C)
    idx = xr.argmax(axis=2)
    out = np.take_along_axis(xr, idx[:, :, None, :], axis=2)[:, :, 0, :]
    return out, (idx, L)


def _pool_bwd(dout, cache):
    idx, L = cache
    B, lo, C = dout.shape
    dxr = np.zeros((B, lo, 2, C))
    np.put_along_axis(dxr, idx[:, :, None, :], dout[:, :, None, :], axis=2)
    dx = np.zeros((B, L, C))
    dx[:, :2 * lo] = dxr.reshape(B, 2 * lo, C)
    return dx


# ----------------------------------------------------------------------------- forward / backward
def forward(p, mean, std, x, train=False, drop=0.0, rng=None, layers=None):
    """x: (B, L, n_in) raw frames. Returns (probs, cache)."""
    layers = layers or LAYERS
    h = (np.asarray(x, dtype=np.float64) - mean) / std
    caches = []
    for i, (k, cout, pool) in enumerate(layers, 1):
        B, L, C = h.shape
        cols = _im2col(h, k)
        z = (cols @ p[f"W{i}"] + p[f"b{i}"]).reshape(B, L, cout)
        a = np.maximum(z, 0.0)
        pc = None
        if pool:
            a, pc = _pool_fwd(a)
        caches.append((cols, z, pc, (B, L, C, k)))
        h = a
    B, L3, C3 = h.shape
    gmax_idx = h.argmax(axis=1)
    feat = np.concatenate([h.mean(axis=1), h.max(axis=1)], axis=1)
    mask = None
    if train and drop > 0:
        mask = (rng.random(feat.shape) >= drop) / (1.0 - drop)
        feat = feat * mask
    logits = feat @ p["Wd"] + p["bd"]
    logits -= logits.max(axis=1, keepdims=True)
    e = np.exp(logits)
    probs = e / e.sum(axis=1, keepdims=True)
    return probs, (caches, h.shape, gmax_idx, feat, mask)


def backward(p, cache, probs, y, n_out, smooth=0.05, class_w=None):
    caches, (B, L3, C3), gmax_idx, feat, mask = cache
    target = np.full((B, n_out), smooth / n_out)
    target[np.arange(B), y] += 1.0 - smooth
    w = np.ones(B) if class_w is None else class_w[y]
    w = w / w.sum()
    loss = -(w * (target * np.log(probs + 1e-12)).sum(axis=1)).sum()
    dlogits = (probs - target) * w[:, None]
    g = {"Wd": feat.T @ dlogits, "bd": dlogits.sum(axis=0)}
    dfeat = dlogits @ p["Wd"].T
    if mask is not None:
        dfeat = dfeat * mask
    dh = np.repeat(dfeat[:, None, :C3] / L3, L3, axis=1)
    dmax = np.zeros((B, L3, C3))
    np.put_along_axis(dmax, gmax_idx[:, None, :], dfeat[:, None, C3:], axis=1)
    dh = dh + dmax
    for i in range(len(caches), 0, -1):
        cols, z, pc, (Bb, L, C, k) = caches[i - 1]
        if pc is not None:
            dh = _pool_bwd(dh, pc)
        dz = (dh * (z > 0)).reshape(Bb * L, -1)
        g[f"W{i}"] = cols.T @ dz
        g[f"b{i}"] = dz.sum(axis=0)
        if i > 1:
            dh = _col2im(dz @ p[f"W{i}"].T, Bb, L, C, k)
    return loss, g


class Adam:
    def __init__(self, params, lr=2e-3, wd=1e-4, b1=0.9, b2=0.999):
        self.lr, self.wd, self.b1, self.b2, self.t = lr, wd, b1, b2, 0
        self.m = {k: np.zeros_like(v) for k, v in params.items()}
        self.v = {k: np.zeros_like(v) for k, v in params.items()}

    def step(self, p, g):
        self.t += 1
        for k in p:
            gk = g[k] + (self.wd * p[k] if k.startswith("W") else 0.0)
            self.m[k] = self.b1 * self.m[k] + (1 - self.b1) * gk
            self.v[k] = self.b2 * self.v[k] + (1 - self.b2) * gk * gk
            mh = self.m[k] / (1 - self.b1 ** self.t)
            vh = self.v[k] / (1 - self.b2 ** self.t)
            p[k] -= self.lr * mh / (np.sqrt(vh) + 1e-8)


def predict_proba(p, mean, std, x, batch=512, layers=None):
    out = []
    for i in range(0, len(x), batch):
        out.append(forward(p, mean, std, x[i:i + batch], layers=layers)[0])
    return np.concatenate(out) if out else np.zeros((0, p["bd"].shape[0]))


# ----------------------------------------------------------------------------- data helpers
def windows(frames, stride=5, seq=SEQ_LEN):
    """All full windows of one take, (n, seq, channels)."""
    frames = np.asarray(frames)
    ends = range(seq, len(frames) + 1, stride)
    if len(frames) < seq:
        return np.zeros((0, seq, frames.shape[1]))
    return np.stack([frames[e - seq:e] for e in ends])


def stretch_crop(frames, rng, seq, lo=0.8, hi=1.25):
    """Random crop of a take, time-stretched to seq frames (linear interpolation)."""
    n = len(frames)
    src = max(4, min(int(round(seq * rng.uniform(lo, hi))), n))
    start = rng.integers(0, n - src + 1)
    seg = frames[start:start + src]
    t = np.linspace(0, src - 1, seq)
    i0 = np.floor(t).astype(int)
    i1 = np.minimum(i0 + 1, src - 1)
    a = (t - i0)[:, None]
    return seg[i0] * (1 - a) + seg[i1] * a


def _rot(rng, max_deg):
    axis = rng.standard_normal(3)
    axis /= np.linalg.norm(axis)
    a = np.radians(rng.uniform(-max_deg, max_deg))
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K


def augment_window(frames, rng, seq=SEQ_LEN, left_drop=0.1):
    """Random window from a take with realistic glove variation. frames: (N, 15) or (N, 30) one take.

    - time stretch 0.8-1.25x        (people sign at different speeds)
    - flex gain/offset per finger   (calibration drift, sensor creep, glove fit)
    - IMU tilt up to 12 deg         (MPU6050 mounted slightly differently), per glove
    - sensor noise, gyro gain, rare Hall flicker
    - two gloves: with probability left_drop the left glove reads all zeros (radio link lost),
      so the model still works one-handed when the link drops
    """
    w = stretch_crop(frames, rng, seq)
    for h in range(w.shape[1] // 15):
        o = 15 * h
        if h == 1 and rng.random() < left_drop:
            w[:, o:o + 15] = 0.0
            continue
        w[:, o + 5:o + 9] = np.round(w[:, o + 5:o + 9])                  # Hall stays 0/1
        w[:, o:o + 5] = np.clip(w[:, o:o + 5] * rng.uniform(0.85, 1.15, 5) + rng.normal(0, 0.05, 5)
                                + rng.normal(0, 0.02, (seq, 5)), 0.0, 1.0)
        flick = rng.random((seq, 4)) < 0.02
        w[:, o + 5:o + 9] = np.where(flick, 1 - w[:, o + 5:o + 9], w[:, o + 5:o + 9])
        R = _rot(rng, 12)
        w[:, o + 9:o + 12] = w[:, o + 9:o + 12] @ R.T + rng.normal(0, 0.02, (seq, 3))
        w[:, o + 12:o + 15] = (w[:, o + 12:o + 15] @ R.T) * rng.uniform(0.8, 1.2) + rng.normal(0, 2.0, (seq, 3))
    return w


def drift(x, rng):
    """Stress test: what a session after re-wearing the glove looks like (no retraining)."""
    x = x.copy()
    for h in range(x.shape[-1] // 15):
        o = 15 * h
        x[..., o:o + 5] = np.clip(x[..., o:o + 5] * rng.uniform(0.82, 0.92, 5) + rng.uniform(0.04, 0.10, 5), 0, 1)
        R = _rot(rng, 10)
        x[..., o + 9:o + 12] = x[..., o + 9:o + 12] @ R.T
        x[..., o + 12:o + 15] = x[..., o + 12:o + 15] @ R.T
    return x
