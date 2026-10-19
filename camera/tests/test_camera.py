"""Camera pipeline tests (no camera or MediaPipe needed).   python camera/tests/test_camera.py"""
import asyncio
import os
import ssl
import sys
import tempfile
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from features import N_FEAT, FrameLandmarks, Resampler, compute  # noqa: E402


def fake_person(w=640, h=480, dx=0.0, scale=1.0, rng=None):
    rng = rng or np.random.default_rng(0)
    pose = np.zeros((33, 4), np.float32)
    pose[:, 3] = 1.0
    c = np.array([w / 2 + dx, h / 2])
    def P(x, y):
        return c + scale * np.array([x, y])
    pose[11, :2], pose[12, :2] = P(60, 0), P(-60, 0)            # signer's left shoulder on image right
    pose[13, :2], pose[14, :2] = P(80, 90), P(-80, 90)
    pose[15, :2], pose[16, :2] = P(40, 60), P(-40, -20)          # right wrist raised
    pose[0, :2] = P(0, -80)
    hand_r = np.c_[P(-40, -20) + scale * rng.normal(0, 25, (21, 2)), scale * rng.normal(0, 10, 21)]
    hand_r[0, :2] = P(-40, -20)
    hand_l = np.c_[P(40, 60) + scale * rng.normal(0, 25, (21, 2)), scale * rng.normal(0, 10, 21)]
    hand_l[0, :2] = P(40, 60)
    lm = FrameLandmarks(w, h, [hand_l.astype(np.float32), hand_r.astype(np.float32)], pose,
                        {"browInnerUp": 0.4, "jawOpen": 0.2}, np.eye(4))
    return lm


def mirror(lm):
    m = FrameLandmarks(lm.w, lm.h)
    m.hands = [np.c_[lm.w - h[:, 0], h[:, 1], h[:, 2]] for h in lm.hands]
    m.pose = lm.pose.copy()
    m.pose[:, 0] = lm.w - lm.pose[:, 0]
    m.blend, m.face_matrix = lm.blend, lm.face_matrix
    return m


def test_feature_size_and_hand_order():
    f = compute(fake_person())
    assert f.shape == (N_FEAT,) and f[63] == 1 and f[127] == 1
    assert f[61] < f[64 + 61]           # dominant (right) wrist is higher (smaller y) than the left one


def test_mirror_invariance():
    lm = fake_person()
    assert np.allclose(compute(lm), compute(mirror(lm)), atol=1e-4)


def test_position_and_distance_invariance():
    a = compute(fake_person(rng=np.random.default_rng(1)))
    b = compute(fake_person(dx=90, scale=1.6, rng=np.random.default_rng(1)))
    assert np.allclose(a, b, atol=1e-4)


def test_left_handed_swaps_hands():
    lm = fake_person()
    r, l = compute(lm), compute(lm, left_handed=True)
    assert np.allclose(r[:64], l[64:128], atol=1e-5)


def test_resampler_grid_and_bridging():
    rs = Resampler(hz=25, hold_s=0.15)
    f = np.ones(N_FEAT, np.float32)
    out = rs.push(0.0, f)
    g = f.copy()
    g[63] = 0                                       # dominant hand lost for one frame
    out += rs.push(0.033, g)
    out += rs.push(0.066, f)
    out += rs.push(0.5, f)
    ts = [t for t, _ in out]
    assert np.allclose(np.diff(ts), 0.04)
    assert all(x[63] == 1 for _, x in out)          # the short drop-out was bridged


def test_decoder_end_to_end_on_synthetic():
    import subprocess
    from make_synthetic import rest_frames, take
    d = tempfile.mkdtemp()
    labels = ["REST", "I", "YOU", "WATER", "WANT", "WHERE", "TOILET", "NOT", "UNDERSTAND", "NAME", "WHAT"]
    subprocess.run([sys.executable, os.path.join(HERE, "..", "make_synthetic.py"), "--users", "3", "--takes", "4",
                    "--out", d, "--labels", *labels], check=True, capture_output=True)
    model = os.path.join(d, "m.npz")
    subprocess.run([sys.executable, os.path.join(HERE, "..", "train_sign.py"), "--data", d, "--epochs", "10",
                    "--out", model], check=True, capture_output=True)
    from live import Decoder, SignModel
    rng, ub = np.random.default_rng(5), np.random.default_rng(101).normal(0, 0.1, (2, 60))
    want = {("I", "WATER", "WANT"): "I want water.", ("TOILET", "WHERE"): "Where is the toilet?",
            ("I", "UNDERSTAND", "NOT"): "I don't understand.", ("YOU", "NAME", "WHAT"): "What is your name?"}
    x = np.concatenate([np.concatenate([take(g, rng, ub) for g in s] + [rest_frames(70, rng)]) for s in want])
    dec, got = Decoder(SignModel(model)), []
    for i, f in enumerate(x):
        got += [m["text"] for m in dec.step(i / 25, f) if m["type"] == "sentence"]
    assert got == list(want.values()), got


def test_phone_bridge_roundtrip():
    import cv2
    from aiohttp import ClientSession, WSMsgType
    from phone_bridge import PhoneBridge
    b = PhoneBridge(port=18443)
    ok, jpg = cv2.imencode(".jpg", np.full((120, 160, 3), 128, np.uint8))

    async def client():
        ctx = ssl.create_default_context()
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        async with ClientSession() as s:
            async with s.get("https://127.0.0.1:18443/", ssl=ctx) as r:
                assert "Vanitra camera" in await r.text()
            async with s.ws_connect("wss://127.0.0.1:18443/ws", ssl=ctx) as ws:
                await ws.send_bytes(np.float64(123.0).tobytes() + jpg.tobytes())
                msg = await ws.receive(timeout=5)
                assert msg.type == WSMsgType.TEXT and '"ack"' in msg.data
                b.send({"type": "sentence", "text": "I want water.", "glosses": ["I", "WATER", "WANT"]})
                msg = await ws.receive(timeout=5)
                assert "I want water." in msg.data
    asyncio.run(client())
    img, _t = next(b.frames())
    assert img.shape == (120, 160, 3)


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            t0 = time.time()
            try:
                fn()
                print(f"ok   {name}  ({time.time() - t0:.1f} s)")
            except Exception as e:  # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
