# camera/ — phone-camera ISL decoder (runs on the laptop)

Phone camera → laptop → MediaPipe landmarks → sign CNN → ISL grammar → English text, which is sent back to the phone, shown large and spoken.

| File | Purpose |
|---|---|
| `phone_bridge.py` | HTTPS/WebSocket server and the phone web page (camera in, text and speech out) |
| `sources.py` | phone / webcam / DroidCam / IP Webcam URL / video file |
| `landmarks.py` | MediaPipe hands + pose + face (downloads 3 model files once) |
| `features.py` | 148 body-relative, mirror-invariant features + 25 Hz resampling |
| `record.py` | record signs or sentences (prompts appear on the phone) |
| `extract_videos.py` | landmarks from a video dataset (e.g. INCLUDE) for pre-training |
| `train_sign.py` | train, validate on a held-out signer, fine-tune |
| `live.py` | live decoding, optional glove fusion |
| `eval_sentences.py` | gloss error rate on recorded sentences; `--grid` tunes the decoder |
| `make_synthetic.py`, `tests/` | pipeline tests without a camera |

Setup and usage: [../docs/camera_decoder.md](../docs/camera_decoder.md) · how to make it precise: [../docs/training_guide.md](../docs/training_guide.md)
