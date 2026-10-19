"""Turn a folder of sign videos (e.g. the INCLUDE ISL dataset) into training takes for train_sign.py.

    python camera/extract_videos.py  path/to/INCLUDE  camera/data_include
    python camera/extract_videos.py  path/to/videos   camera/data  --map camera/include_map.csv

Label = the video's parent folder name, cleaned: "48. Hello" -> "HELLO", "Thank you" -> "THANK-YOU".
--map CSV (columns: folder,gloss) renames folders to our glosses and skips folders not in the map.
Resumable: videos already extracted are skipped. Uses the same landmarks + features as live decoding,
so a model pretrained here transfers directly.

INCLUDE: 263 ISL word signs, ~4.3k videos, CC BY 4.0 — https://zenodo.org/records/4010759
"""
import argparse
import csv
import glob
import os
import re

import numpy as np

from features import HZ, Resampler, compute

VIDEO_EXT = (".mov", ".mp4", ".avi", ".mkv", ".webm", ".m4v")


def clean(name):
    name = re.sub(r"^\d+\.\s*", "", name).strip()
    return re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--map", help="CSV folder,gloss")
    ap.add_argument("--no-face", action="store_true")
    args = ap.parse_args()
    from landmarks import Landmarker
    import cv2

    mapping = None
    if args.map:
        with open(args.map, newline="", encoding="utf-8") as f:
            mapping = {r["folder"]: r["gloss"] for r in csv.DictReader(f)}
    vids = [p for p in glob.glob(os.path.join(args.src, "**", "*"), recursive=True) if p.lower().endswith(VIDEO_EXT)]
    print(f"{len(vids)} videos")
    lmk = Landmarker(face=not args.no_face)
    t_off = 0.0                                   # MediaPipe VIDEO mode needs ever-increasing timestamps
    for n, path in enumerate(sorted(vids), 1):
        folder = os.path.basename(os.path.dirname(path))
        label = mapping.get(folder) if mapping else clean(folder)
        if not label:
            continue
        dst = os.path.join(args.out, label, re.sub(r"\W+", "_", os.path.splitext(os.path.basename(path))[0]) + ".npz")
        if os.path.exists(dst):
            continue
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        rs, xs, i = Resampler(), [], 0
        while True:
            ok, img = cap.read()
            if not ok:
                break
            if max(img.shape[:2]) > 720:          # speed: landmarks do not need full HD
                s = 720 / max(img.shape[:2])
                img = cv2.resize(img, None, fx=s, fy=s)
            t = t_off + i / fps
            xs += [f for _t, f in rs.push(t, compute(lmk(img, t)))]
            i += 1
        t_off += i / fps + 1.0
        if len(xs) < 8:
            print(f"  skip (too short / no person): {path}")
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        np.savez(dst, x=np.array(xs, np.float32), label=label, user="ext", hz=HZ)
        if n % 25 == 0:
            print(f"  {n}/{len(vids)}  {label}")
    print("done ->", args.out)


if __name__ == "__main__":
    main()
