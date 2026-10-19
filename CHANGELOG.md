# Changelog

## v3.0-dev — 19 Oct 2026 · two gloves, ISL sentences, phone camera
**Tested on PC with synthetic data only. Not yet run with hardware, a real phone camera or real signers.**
- **ISL study** ([docs/isl_language.md](docs/isl_language.md)): sign parameters, two-handed sign types, grammar (time first, verb last, wh/NOT final, facial yes/no questions), what gloves vs camera can see.
- **Two gloves:**
  - the same firmware on both; role set over serial (`r`); `glove_link.h` (ESP-NOW, 36-byte frames at 50 Hz, link-loss fallback);
  - 30-channel CNN with left-glove drop-out augmentation;
  - the stream gains 31 columns; `collect_data.py` / `train_cnn.py` accept one- or two-glove takes.
- **Vocabulary:** 58 ISL glosses + REST, shared by gloves and camera; voice clips regenerated (espeak).
- **Language engine (`lang/vanitra_lang`):**
  - lexicon (~100 glosses), phrase table, 79-sentence gloss corpus;
  - interpolated bigram gloss LM with beam search over the n-best;
  - rule-based ISL → English;
  - fingerspelling merge; non-manual markers.
  - Tests: all corpus sentences pass; on held-out noisy input, fully correct sentences rise from 67 % to 79 %.
- **Phone-camera decoder (`camera/`):**
  - HTTPS/WebSocket phone page (camera in, text and speech out);
  - MediaPipe hands/pose/face → 148 mirror-invariant signing-space features;
  - recorder; video-dataset extractor (INCLUDE) for transfer learning; trainer with held-out signer and fine-tuning;
  - live decoder with sign spotter, LM and grammar; `eval_sentences.py` (gloss error rate, `--grid` tuning); glove + camera fusion.
- `ml/live_decoder.py` now outputs English sentences.
- [docs/training_guide.md](docs/training_guide.md): how to reach high precision (data protocol, transfer learning, personalisation, tuning, fusion, scaling up).
- BOM: left glove added (≈ ₹15,800 total).

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
