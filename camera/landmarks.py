"""MediaPipe Tasks landmark detection: 2 hands + upper-body pose + face (blendshapes, head pose).

The three model files (~20 MB in total) are downloaded once from Google's model storage into
camera/models/. Everything after that runs offline on the laptop CPU.
Needs:  pip install mediapipe opencv-python
"""
import os
import urllib.request

import numpy as np

from features import FrameLandmarks

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(HERE, "models")
BASE = "https://storage.googleapis.com/mediapipe-models"
MODELS = {
    "hand": ("hand_landmarker.task", f"{BASE}/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"),
    "pose_lite": ("pose_landmarker_lite.task",
                  f"{BASE}/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"),
    "pose_full": ("pose_landmarker_full.task",
                  f"{BASE}/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"),
    "face": ("face_landmarker.task", f"{BASE}/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"),
}


def ensure_model(key):
    name, url = MODELS[key]
    path = os.path.join(MODEL_DIR, name)
    if not os.path.exists(path):
        os.makedirs(MODEL_DIR, exist_ok=True)
        print(f"downloading {name} (one time) ...")
        urllib.request.urlretrieve(url, path + ".part")
        os.replace(path + ".part", path)
    return path


class Landmarker:
    def __init__(self, face=True, pose="lite", min_conf=0.5):
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mpt
            from mediapipe.tasks.python import vision
        except ImportError as e:
            raise SystemExit("pip install mediapipe opencv-python") from e
        self.mp = mp
        V = vision.RunningMode.VIDEO
        opt = lambda key: mpt.BaseOptions(model_asset_path=ensure_model(key))  # noqa: E731
        self.hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
            base_options=opt("hand"), running_mode=V, num_hands=2, min_hand_detection_confidence=min_conf,
            min_hand_presence_confidence=min_conf, min_tracking_confidence=min_conf))
        self.pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=opt(f"pose_{pose}"), running_mode=V, num_poses=1))
        self.face = None
        if face:
            self.face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
                base_options=opt("face"), running_mode=V, num_faces=1, output_face_blendshapes=True,
                output_facial_transformation_matrixes=True))
        self.last_ms = -1

    def __call__(self, bgr, t_s):
        """bgr: OpenCV image. t_s: timestamp in seconds (must increase). Returns FrameLandmarks."""
        import cv2
        h, w = bgr.shape[:2]
        ms = max(int(t_s * 1000), self.last_ms + 1)
        self.last_ms = ms
        img = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        out = FrameLandmarks(w, h)
        hr = self.hands.detect_for_video(img, ms)
        for lms, cats in zip(hr.hand_landmarks, hr.handedness):
            out.hands.append(np.array([[p.x * w, p.y * h, p.z * w] for p in lms], dtype=np.float32))
            out.handedness.append(cats[0].category_name if cats else "")
        pr = self.pose.detect_for_video(img, ms)
        if pr.pose_landmarks:
            out.pose = np.array([[p.x * w, p.y * h, p.z * w, p.visibility if p.visibility is not None else 1.0]
                                 for p in pr.pose_landmarks[0]], dtype=np.float32)
        if self.face is not None:
            fr = self.face.detect_for_video(img, ms)
            if fr.face_blendshapes:
                out.blend = {c.category_name: c.score for c in fr.face_blendshapes[0]}
            if fr.facial_transformation_matrixes:
                out.face_matrix = np.asarray(fr.facial_transformation_matrixes[0])
        return out


def draw(bgr, lm):
    """Draw the detected landmarks on the image (preview window)."""
    import cv2
    for hand in lm.hands:
        for a, b in [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11),
                     (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]:
            cv2.line(bgr, tuple(int(x) for x in hand[a, :2]), tuple(int(x) for x in hand[b, :2]), (0, 220, 255), 2)
    if lm.pose is not None:
        for a, b in [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]:
            if lm.pose[a, 3] > 0.3 and lm.pose[b, 3] > 0.3:
                cv2.line(bgr, tuple(int(x) for x in lm.pose[a, :2]), tuple(int(x) for x in lm.pose[b, :2]),
                         (255, 160, 0), 2)
    return bgr
