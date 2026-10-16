# Gesture ML pipeline

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
