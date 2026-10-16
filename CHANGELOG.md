# Changelog

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
