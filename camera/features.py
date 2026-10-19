"""Landmarks of one video frame -> one 148-number feature vector for the sign model.

Why these features (precision):
  * Signing-space coordinates. Everything is measured in a BODY frame: origin between the shoulders,
    unit = shoulder width, x axis from the signer's right shoulder to their left shoulder, y axis down.
    So the result does not change when the signer stands closer or further, moves in the picture, or the
    phone is held slightly tilted, and it is IDENTICAL for a mirrored (selfie) image.
  * Hand shape in a HAND frame. 20 finger landmarks relative to the wrist, divided by hand size, in the
    body-frame axes: handshape is separated from where the hand is.
  * Dominant / non-dominant, not left / right. Hands are matched to the pose's wrists (anatomical,
    reliable) and ordered dominant first. Left-handed signers: left_handed=True.
  * Non-manual markers. Brows, eyes, mouth (MediaPipe blendshapes) and head yaw/pitch/roll, because ISL
    marks yes/no questions with raised brows and negation with a head shake.

Layout (148):  [dominant hand 64][non-dominant hand 64][pose 10][face 10]
  hand (64): 20 x (x, y, z) finger points in the hand frame (60) · wrist x, y in the body frame (2)
             · hand size / shoulder width (1) · present 0/1 (1)
  pose (10): dominant elbow, non-dominant elbow, dominant wrist, non-dominant wrist, nose — x, y in body frame
  face (10): brow_up, brow_down, eye_wide, jaw_open, mouth_pucker, mouth_funnel, yaw, pitch, roll (/90°), present
"""
import math

import numpy as np

N_HAND, N_POSE, N_FACE = 64, 10, 10
N_FEAT = 2 * N_HAND + N_POSE + N_FACE            # 148
HZ = 25                                          # features are resampled to 25 frames per second
FACE_NAMES = ["brow_up", "brow_down", "eye_wide", "jaw_open", "mouth_pucker", "mouth_funnel",
              "yaw", "pitch", "roll", "face_present"]
FEATURE_NAMES = ([f"D_{i}{a}" for i in range(1, 21) for a in "xyz"] + ["D_wx", "D_wy", "D_size", "D_present"]
                 + [f"N_{i}{a}" for i in range(1, 21) for a in "xyz"] + ["N_wx", "N_wy", "N_size", "N_present"]
                 + ["elbow_D_x", "elbow_D_y", "elbow_N_x", "elbow_N_y", "wrist_D_x", "wrist_D_y",
                    "wrist_N_x", "wrist_N_y", "nose_x", "nose_y"] + FACE_NAMES)
IDX_D_PRESENT, IDX_N_PRESENT = N_HAND - 1, 2 * N_HAND - 1
IDX_BROW_UP, IDX_YAW, IDX_FACE_PRESENT = 2 * N_HAND + N_POSE + 0, 2 * N_HAND + N_POSE + 6, N_FEAT - 1
IDX_D_WRIST_Y = N_HAND - 3


class FrameLandmarks:
    """What the landmark detector found in one frame (pixel units; z in the same units as x)."""

    def __init__(self, w, h, hands=None, pose=None, blend=None, face_matrix=None):
        self.w, self.h = w, h
        self.hands = hands or []           # list of (21, 3) arrays + optional handedness label
        self.handedness = []               # "Left"/"Right" per hand as MediaPipe reports it (selfie view)
        self.pose = pose                   # (33, 4) x, y, z, visibility  or None
        self.blend = blend                 # {blendshape name: score} or None
        self.face_matrix = face_matrix     # 4x4 or None


def _frame(lm):
    """Body frame from the pose shoulders. Returns (origin, u, v, scale, mirrored)."""
    if lm.pose is not None and lm.pose[11, 3] > 0.3 and lm.pose[12, 3] > 0.3:
        L, R = lm.pose[11, :2], lm.pose[12, :2]          # signer's left / right shoulder
        d = L - R
        sw = float(np.linalg.norm(d))
        if sw > 1e-3:
            u = d / sw
            v = np.array([-u[1], u[0]])
            if v[1] < 0:                                 # y axis always points down the body
                v = -v
            return (L + R) / 2, u, v, sw, bool(L[0] < R[0])
    return np.array([lm.w / 2, lm.h / 2]), np.array([1.0, 0.0]), np.array([0.0, 1.0]), 0.3 * lm.w, False


def _assign(lm, left_handed):
    """Returns (dominant (21,3) or None, non-dominant or None) using the pose wrists (anatomical)."""
    hands = lm.hands[:2]
    if not hands:
        return None, None
    dom_w, non_w = (15, 16) if left_handed else (16, 15)   # pose 16 = right wrist, 15 = left wrist
    if lm.pose is not None:
        pd, pn = lm.pose[dom_w, :2], lm.pose[non_w, :2]
        cost = [(np.linalg.norm(h[0, :2] - pd), np.linalg.norm(h[0, :2] - pn)) for h in hands]
        if len(hands) == 1:
            return (hands[0], None) if cost[0][0] <= cost[0][1] else (None, hands[0])
        if cost[0][0] + cost[1][1] <= cost[0][1] + cost[1][0]:
            return hands[0], hands[1]
        return hands[1], hands[0]
    # no pose: fall back on MediaPipe's handedness (it assumes a mirrored selfie image)
    want = "Left" if left_handed else "Right"
    dom = non = None
    for h, lab in zip(hands, lm.handedness or ["Right", "Left"]):
        if lab == want and dom is None:
            dom = h
        else:
            non = h
    return dom, non


def _hand_feats(hand, org, u, v, sw):
    f = np.zeros(N_HAND)
    if hand is None:
        return f
    wrist = hand[0]
    hs = float(np.linalg.norm(hand[9, :2] - wrist[:2])) or 1.0
    rel = hand[1:] - wrist
    f[0:60:3] = rel[:, :2] @ u / hs
    f[1:60:3] = rel[:, :2] @ v / hs
    f[2:60:3] = rel[:, 2] / hs
    f[60] = (wrist[:2] - org) @ u / sw
    f[61] = (wrist[:2] - org) @ v / sw
    f[62] = hs / sw
    f[63] = 1.0
    return f


def _head_angles(m):
    R = np.asarray(m)[:3, :3]
    yaw = math.degrees(math.atan2(R[0, 2], R[2, 2]))
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, -R[1, 2]))))
    roll = math.degrees(math.atan2(R[1, 0], R[1, 1]))
    return yaw, pitch, roll


def compute(lm, left_handed=False):
    """FrameLandmarks -> (148,) float32."""
    org, u, v, sw, mirrored = _frame(lm)
    dom, non = _assign(lm, left_handed)
    f = np.zeros(N_FEAT, dtype=np.float32)
    f[0:N_HAND] = _hand_feats(dom, org, u, v, sw)
    f[N_HAND:2 * N_HAND] = _hand_feats(non, org, u, v, sw)
    o = 2 * N_HAND
    if lm.pose is not None:
        ids = (14, 13, 16, 15, 0) if not left_handed else (13, 14, 15, 16, 0)
        for k, i in enumerate(ids):
            p = lm.pose[i, :2] - org
            f[o + 2 * k], f[o + 2 * k + 1] = p @ u / sw, p @ v / sw
    o += N_POSE
    if lm.blend is not None:
        b = lm.blend
        g = lambda *ks: float(np.mean([b.get(k, 0.0) for k in ks]))  # noqa: E731
        f[o + 0] = g("browInnerUp", "browOuterUpLeft", "browOuterUpRight")
        f[o + 1] = g("browDownLeft", "browDownRight")
        f[o + 2] = g("eyeWideLeft", "eyeWideRight")
        f[o + 3] = g("jawOpen")
        f[o + 4] = g("mouthPucker")
        f[o + 5] = g("mouthFunnel")
        if lm.face_matrix is not None:
            yaw, pitch, roll = _head_angles(lm.face_matrix)
            s = -1.0 if mirrored else 1.0
            f[o + 6], f[o + 7], f[o + 8] = s * yaw / 90, pitch / 90, s * roll / 90
        f[o + 9] = 1.0
    return f


class Resampler:
    """Turns features at irregular camera timestamps into a steady HZ stream (linear interpolation).
    Short detection drop-outs (<= hold_s) of a hand or the face are bridged with the last good value."""

    def __init__(self, hz=HZ, hold_s=0.15):
        self.dt = 1.0 / hz
        self.hold_s = hold_s
        self.prev = None          # (t, f)
        self.next_t = None
        self.last_seen = {}       # block -> (t, values)

    def _bridge(self, t, f):
        blocks = {"D": (0, N_HAND, IDX_D_PRESENT), "N": (N_HAND, 2 * N_HAND, IDX_N_PRESENT),
                  "F": (2 * N_HAND + N_POSE, N_FEAT, IDX_FACE_PRESENT)}
        f = f.copy()
        for name, (a, b, pres) in blocks.items():
            if f[pres] > 0.5:
                self.last_seen[name] = (t, f[a:b].copy())
            elif name in self.last_seen and t - self.last_seen[name][0] <= self.hold_s:
                f[a:b] = self.last_seen[name][1]
        return f

    def push(self, t, f):
        """Returns a list of (t, features) on the HZ grid (possibly empty)."""
        f = self._bridge(t, np.asarray(f, dtype=np.float32))
        out = []
        if self.prev is None:
            self.prev, self.next_t = (t, f), t
            return [(t, f)]
        t0, f0 = self.prev
        if t - t0 > 1.0:                                  # long gap (paused stream): restart the grid
            self.prev, self.next_t = (t, f), t
            return [(t, f)]
        while self.next_t + self.dt <= t + 1e-9:
            self.next_t += self.dt
            a = (self.next_t - t0) / max(t - t0, 1e-6)
            g = f0 * (1 - a) + f * a
            for pres in (IDX_D_PRESENT, IDX_N_PRESENT, IDX_FACE_PRESENT):  # flags: nearest, not blended
                g[pres] = f0[pres] if a < 0.5 else f[pres]
            out.append((self.next_t, g))
        self.prev = (t, f)
        return out
