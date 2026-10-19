# Phone-camera decoder

The phone films the signer, and the laptop decodes ISL. The English text goes back to the phone, where it is shown in large type and spoken aloud. Everything after the one-time model download runs **offline on the laptop**, and the phone needs no app.

```
phone browser ──JPEG frames over Wi-Fi (WebSocket, HTTPS)──▶ laptop
  camera                                                     MediaPipe: 2 hands + pose + face
  ◀── live glosses + English sentence (+ phone speaks it) ── 148 features → sign CNN (1.6 s window)
                                                             [+ glove CNN over USB] → sign spotter
                                                             → gloss LM + ISL grammar → English
```

## 1. Install (laptop: Windows, macOS or Linux, Python 3.10+)
```bash
pip install -r camera/requirements.txt -r ml/requirements.txt
```
The first run downloads the MediaPipe models (~20 MB) into `camera/models/`.

## 2. Connect the phone (pick one)

| Option | Command | Notes |
|---|---|---|
| **Phone browser (recommended)** | `python camera/live.py --source phone` | Open the printed `https://<laptop-ip>:8443` on the phone, tap *Advanced → Proceed* (self-signed certificate), and allow the camera. Text and speech come back to the phone. Phone and laptop must be on the same Wi-Fi, or the laptop on the phone's hotspot. |
| IP Webcam (Android app) | `--source http://<phone-ip>:8080/video` | MJPEG stream; text only on the laptop |
| DroidCam / Iriun / Camo | `--source 1` (the virtual webcam index) | Shows up as a webcam; text only on the laptop |
| Laptop webcam / video file | `--source 0` / `--source clip.mp4` | For testing |

Test the link alone with `python camera/phone_bridge.py`, which prints the frames per second received.

**Framing:** head, both shoulders and both hands inside the picture. Phone at chest height, 1–2 m away, steady (a stand or a book). Light from the front, plain background if you can.

## 3. Record, train, run
```bash
python camera/record.py --source phone --user manas --takes 10                # every sign in ml/vocabulary.csv
python camera/record.py --source phone --user manas --labels REST --takes 20  # lots of REST
python camera/train_sign.py --val-user pragati                                # honest new-signer accuracy
python camera/live.py --source phone                                          # decode
python camera/live.py --source phone --glove COM5                             # + gloves (fusion)
```
For precision, read [training_guide.md](training_guide.md): transfer learning from INCLUDE, per-user fine-tuning, decoder tuning with `eval_sentences.py --grid`.

## 4. Tuning while live

| Flag | Default | Raise it if… | Lower it if… |
|---|---|---|---|
| `--conf` | 0.55 | it outputs signs you did not make | it misses signs |
| `--stable` | 3 (240 ms) | it flickers between signs | fast signing is missed |
| `--gap` | 1.8 s | sentences get cut in the middle | you wait too long for the text |
| `--w-lm` | 0.3 | context should correct more | it "hears" what it expects |

**Speed:** MediaPipe hands + pose + face run at roughly 15–25 frames/s on a typical laptop CPU. The decoder needs only 25 Hz. `--no-face` is faster, but then yes/no questions need the `QUESTION` sign.

**Privacy:** `record.py` saves only landmark numbers, never images.

## Status
Tested without a camera:
- feature invariance (mirror, position, distance);
- resampling;
- phone-bridge round trip;
- synthetic sentences decoded end to end (`python camera/tests/test_camera.py`).

**Not yet tested:**
- the MediaPipe detection itself (its model files could not be downloaded in the build environment);
- a real phone;
- any real ISL signing.
