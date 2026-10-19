"""Where the video comes from.

  --source phone                         the phone's browser (phone_bridge.py), text goes back to the phone
  --source 0                             a webcam, or a phone used as a webcam (DroidCam / Iriun / Camo)
  --source http://192.168.1.7:8080/video IP Webcam (Android) / DroidCam MJPEG URL
  --source clip.mp4                      a recorded video (processed frame by frame, nothing dropped)
"""
import os
import threading
import time


def open_source(spec, port=8443):
    """Returns (frame iterator yielding (bgr, t_seconds), bridge or None)."""
    if spec == "phone":
        from phone_bridge import PhoneBridge
        b = PhoneBridge(port=port)
        return b.frames(), b
    return opencv_frames(spec), None


def opencv_frames(spec):
    import cv2
    src = int(spec) if str(spec).isdigit() else spec
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise SystemExit(f"cannot open video source {spec!r}")
    if os.path.exists(str(spec)):                       # a file: every frame, timestamps from its fps
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        i = 0
        while True:
            ok, img = cap.read()
            if not ok:
                return
            yield img, i / fps
            i += 1
    # live camera / stream: a reader thread keeps only the newest frame, so we never fall behind
    latest = {"img": None, "t": 0.0, "n": 0}
    lock = threading.Lock()

    def reader():
        while True:
            ok, img = cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            with lock:
                latest.update(img=img, t=time.time(), n=latest["n"] + 1)

    threading.Thread(target=reader, daemon=True).start()
    seen = 0
    while True:
        with lock:
            n, img, t = latest["n"], latest["img"], latest["t"]
        if n == seen or img is None:
            time.sleep(0.003)
            continue
        seen = n
        yield img, t
