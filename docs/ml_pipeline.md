# Gesture ML pipeline

Two models share the same recordings. **v2 (default): temporal CNN** on 1.0 s of raw signal, described in the [v2 section](#v2-temporal-cnn). **v1: feature MLP** on 0.5 s, described in sections 3–4. Choose with `GESTURE_MODEL` in `firmware/glove_unit/config.h`.

```
glove (stream mode 's') ──USB──> collect_data.py ──> ml/data/<LABEL>/<user>_<time>.csv
                                                        │
                       vanitra_features.py  <── same maths ──>  firmware/glove_unit/features.h
                                                        │
                                train.py  (grouped cross-validation, MLP 16-32-N)
                                    ├──> firmware/glove_unit/model.h          (weights as C arrays)
                                    ├──> firmware/tests/host/test_vectors.h   (Python == C++ check)
                                    └──> ml/reports/report.md + confusion.png
```

## 1. Vocabulary
`ml/vocabulary.csv` lists every sign, the words the glove says (`say`) and a hint on how to perform it. **REST** (no sign) must stay in the list. It is never spoken, and it is what stops the glove from talking all the time. To change the vocabulary (for example to ISL), edit the CSV, record data, retrain, and re-run `make_voice_clips.py`.

## 2. Record
```bash
python ml/collect_data.py --port COM5 --user pragati
python ml/collect_data.py --port COM5 --user shubham --labels HELLO WATER REST   # only some signs
```
- Calibrate the glove for the person first (hold BOOT 2 s).
- A take lasts 4 s. **Keep repeating the sign for the whole take** at a natural speed.
- At least **5 takes per sign per person, from 3 or more people**. More people beats more takes.
- Record **3× more REST** than any single sign: hand relaxed, typing, holding a bottle, scratching, walking, half-formed shapes.
- The files are plain CSV (`t_ms, flex1..5, hall1..4, ax, ay, az, gx, gy, gz`), already calibrated, so data from different people can be combined.

## 3. Features (16 per 0.5 s window)
| # | Feature | Captures |
|---|---|---|
| 0–4 | mean bend of each finger (0 straight … 1 fist) | hand shape |
| 5–8 | fraction of the window each Hall sensor is in contact | fingertip contacts (O vs C, K vs V …) |
| 9–10 | mean roll, mean pitch | palm orientation |
| 11–12 | change in roll, pitch across the window | sweeping / flipping signs |
| 13–14 | mean and max rotation speed | static vs moving |
| 15 | spread of acceleration magnitude | taps, shakes |

Windows are taken every 5 frames (100 ms), so one 4 s take gives about 36 training windows.

## 4. Train
```bash
python ml/train.py                # data in ml/data
python ml/train.py --by-user      # leave-one-person-out: the honest "new user" number
python ml/train.py --hidden 48    # bigger network if accuracy plateaus
```
Cross-validation is **grouped**: windows from the same take (or, with `--by-user`, the same person) never appear in both the training and the test split. This stops overlapping windows from inflating the accuracy. The confusion matrix shows which signs get mixed up. Fix those by changing how the sign is performed, adding Hall placements, or recording more takes.

The output `model.h` contains plain float arrays (about 1.3k weights, ~5 KB). `mlp.h` runs it on the ESP32-S3 in well under 1 ms.

## 5. Check and flash
```bash
make -C firmware/tests/host        # Python features/probabilities == C++ (to 1e-3)
```
Flash the glove, type `p` in the serial monitor and watch the live predictions.

## 6. Tuning on the device (`config.h`)
| Define | Default | Raise it if… | Lower it if… |
|---|---|---|---|
| `CONF_THRESHOLD` | 0.85 | it says words you did not sign | it misses signs |
| `STABLE_COUNT` | 3 (300 ms) | it flickers between words | it feels slow |
| `REPEAT_GAP_MS` | 2500 | it repeats a held sign | you want fast repeats |

## Synthetic data (no hardware)
`python ml/make_synthetic_data.py` writes invented takes to `ml/data_synthetic/`. `python ml/train.py --synthetic` then builds a **placeholder** `model.h` (flagged `VM_PLACEHOLDER 1`). Use this only to test the pipeline, the firmware build and the Wokwi simulation. The accuracy it prints says nothing about real signing.

## v2: temporal CNN
```
ml/data/<LABEL>/*.csv ──> train_cnn.py ──┬─> firmware/glove_unit/model_cnn.h        (run by cnn.h)
   (same recordings)    vanitra_cnn.py   ├─> firmware/tests/host/test_vectors_cnn.h (NumPy == C++ check)
                        (NumPy CNN)      ├─> ml/models/vanitra_cnn.npz             (live_decoder.py)
                                         └─> ml/reports/cnn_report.md              (CNN vs MLP, clean + drifted)
```
```bash
python ml/train_cnn.py                 # 5-fold by take + final model (~10 min on a laptop)
python ml/train_cnn.py --by-user       # leave-one-person-out: quote THIS number
python ml/train_cnn.py --folds 0       # just train + export (~2 min)
make -C firmware/tests/host            # parity: glove MLP, glove CNN, Morse
python ml/live_decoder.py --port COM5 --speak     # watch it decode live
python ml/live_decoder.py --replay ml/data/HELLO/<take>.csv
```
**Network.** The input is 15 channels × 50 frames (1.0 s), standardised per channel. Then conv k5→24, ReLU, max-pool 2 → conv k5→32, ReLU, max-pool 2 → conv k3→32, ReLU → mean and max over time (64) → dense → softmax. That is about 10 k weights (40 KB) and about 0.23 M multiply-adds per call, run every 100 ms.

**Augmentation (training only).**
- Random 0.8–1.25× time-stretch.
- Per-finger flex gain ×0.85–1.15 and offset ±0.05, which simulates drift or re-wearing.
- Random IMU rotation up to 12°.
- Gyro gain ×0.8–1.2, sensor noise, and 2 % Hall flicker.

**Report.** For every fold, both the CNN and the v1 MLP are trained on the same takes and tested on the same windows. The MLP sees the last 0.5 s of each CNN window, which is what it would see at that moment on the glove. Each model is tested twice:
- on **clean** windows;
- on **drifted** windows: flex gain −8…−18 %, offset +0.04…+0.10, and a 10° IMU tilt, which is what a session looks like when the glove is put back on without recalibrating.

**Latency.** A sign is recognised once the 1.0 s window contains enough of it, plus `STABLE_COUNT` × 100 ms. Expect about 0.6–1.0 s from the start of a sign. That is slower to start than v1, but it sees the whole sign.

**Synthetic data.** `python ml/make_synthetic_data.py && python ml/train_cnn.py --synthetic` builds a placeholder `model_cnn.h` (`VC_PLACEHOLDER 1`). It is a pipeline test only.
