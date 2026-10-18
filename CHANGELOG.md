# Changelog

## v2.0-dev — 18 Oct 2026 · design review, glove hardware v2, temporal CNN
**Software and drawings only. Not yet built with the ESP32 core or run on hardware.**
- [Design review](docs/design_review_v2.md): 13 problems ranked; the flex-sensor question answered with a comparison of alternatives.
- Glove hardware v2 ([schematic](docs/wiring/glove_unit.svg)):
  - 4.5″ flex on the fingers, 2.2″ on the thumb, divider R = √(R_flat·R_bent) (22k / 33k)
  - 100 nF on every analog input
  - LiPo → LDO → 3V3 (MT3608 removed from the glove), amplifier on VSYS
  - battery divider after the switch
  - J1/J2/J3 plug-in harness
  - BOM updated (≈ ₹9,300 total)
- Model v2: `ml/vanitra_cnn.py` (NumPy 1D-CNN with augmentation), `ml/train_cnn.py` (CNN vs MLP on the same folds, clean and drifted, `--by-user`), `firmware/glove_unit/cnn.h` + `model_cnn.h` (placeholder, synthetic). `GESTURE_MODEL` in `config.h` selects the model.
- `ml/live_decoder.py`: live top-3, firmware-identical speaking rules, transcript, optional speech, replay of recorded takes.
- Firmware: flex open/short detection (`SENSOR FAULT`), low-battery warning at 3.5 V, `classifier.h` model switch.
- Tests: `firmware/tests/host/test_cnn.cpp` (NumPy ↔ C++ CNN parity).
- Fix: synthetic take files are now named `synth<user>_t<k>.csv`, so `--by-user` sees 6 users instead of one.

## v1.0 — 16 Oct 2026 · repository + firmware rewrite
**Software complete, not yet run on hardware.**
- One pin map for both units (5 flex on GPIO 4–8, 4 SS49E Hall on GPIO 9/10/1/2, MPU6050 on 16/17, MAX98357A on 12/13/14/21; wristband INMP441 on 17/47/16, motor on 4, button on 5).
- Glove firmware: per-user calibration (open hand + fist) saved in flash, 50 Hz sampling, 0.5 s window with 16 features, on-chip MLP 16-32-21, confidence gate + stability + repeat lockout, voice clips over I2S, optional OLED, serial stream mode for data collection.
- Wristband firmware: ESP-SR offline wake word ("Hi ESP") + 49 phrases → 22 meanings, Morse short codes with a danger pattern, 3 speeds, tap / double-tap / hold button, typed-text practice mode, optional OLED.
- ML pipeline: `collect_data.py`, `train.py` (grouped CV, confusion matrix, exports `model.h` + parity vectors), `make_voice_clips.py`, synthetic data generator. Shipped `model.h` is a **placeholder trained on synthetic data**.
- `tools/make_sr_commands.py`: phrases.csv → ESP-SR phoneme table.
- PC unit tests: Python ↔ C++ feature/net parity, Morse timing.
- Hardware test sketches, Wokwi diagram, schematics (SVG/PNG), BOM (≈ ₹7,050), docs, report errata.

## v0.2 — Hackanova 5.0 (hardware track)
- Team Mtx.Vanitra deck: problem, architecture, components, outcomes, 36-hour plan, challenges.

## v0.1 — SCS mini project, AY 2025-26
- Concept, CAD (glove + wristband), Wokwi simulations, breadboard glove prototype.
- Blue book (6 chapters) and IEEE-format paper (v1 Aug 2025, v2 Oct 2025).
- Reported on the first prototype: 90–94 % gesture accuracy, 85–90 % speech-to-Morse, 350–500 ms latency.
