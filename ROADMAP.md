<div align="center">

# 🗺️ Vanitra Roadmap

**From the SCS mini project to a tested two-way wearable**

![Done](https://img.shields.io/badge/done-16-2ea44f?style=for-the-badge)
![To do](https://img.shields.io/badge/to_do-24-6e7781?style=for-the-badge)
![Phase](https://img.shields.io/badge/now-phase_3_bring--up-0e7c86?style=for-the-badge)

`████████████░░░░░░░░░░░░░░░░░░`  **16 / 40 tasks**

</div>

> Tick the boxes as tasks are finished, and update the badge numbers and the bar (1 block ≈ 1.3 tasks).

## Phase 1 — SCS mini project (AY 2025-26) ✅
- [x] Problem definition, WHO / India statistics, literature review
- [x] Concept: sensor glove + speech-to-haptic wristband
- [x] CAD of glove and wristband, labelled diagrams
- [x] Wokwi simulation of glove and speech unit
- [x] Breadboard glove prototype (flex + IMU on ESP32-S3)
- [x] Blue book + IEEE-format paper (v1 Aug 2025, v2 Oct 2025)

## Phase 2 — Hackanova 5.0 + v1.0 repository ✅
- [x] Hackanova 5.0 hardware-track deck and 36-hour plan (team Mtx.Vanitra)
- [x] One consistent pin map (fixes GPIO 4-7 / 9-13 mismatch) — [decisions D1](docs/decisions.md)
- [x] Glove firmware: calibration, 16-feature window, on-chip neural net, confidence gate, I2S voice, OLED
- [x] Wristband firmware: ESP-SR wake word + 49 phrases, Morse short codes, 3 speeds, button, OLED
- [x] ML pipeline: data collection, grouped cross-validation, export to `model.h`, voice clips
- [x] PC unit tests (Python ↔ C++ parity, Morse timing); both firmwares compile on core 3.2.0
- [x] Schematics (SVG/PNG), BOM, Wokwi diagram for the new pin map
- [x] Docs: setup, wiring, architecture, ML, test plan, decisions, report errata

## Phase 3 — Hardware bring-up 🔄 (next)
- [ ] Buy parts from `hardware/bom.csv` (v2 glove: 4.5″ flex, LDO, JST connectors, 100 nF caps …)
- [ ] Glove: sensors on the glove, pass `glove_sensor_monitor` (T1)
- [ ] Glove: `i2c_scan`, `speaker_test`; flash `glove_unit`, calibrate
- [ ] Wristband: `mic_level_test`, `haptic_test`; flash `wristband_unit`
- [ ] Power: glove LiPo → LDO (v2), wristband LiPo → MT3608; no brown-outs while the speaker plays
- [ ] Open the Wokwi diagram and fix any pin names that do not connect

## Phase 4 — Data + first real model
- [ ] Decide vocabulary: keep the ASL-style 20 or switch to ISL (edit `ml/vocabulary.csv`)
- [ ] Record ≥ 5 takes × 21 labels × 3 people (+ extra REST)
- [ ] `train_cnn.py --by-user` (CNN vs MLP); ship the winner; fix the most confused pairs
- [ ] Record human voice clips (`make_voice_clips.py --wav-dir`)
- [ ] Tune `CONF_THRESHOLD`, `STABLE_COUNT` on the glove

## Phase 5 — Wristband tuning
- [ ] Test all 22 meanings with 2 speakers, quiet and noisy (T6, T7)
- [ ] Replace phrases that are often misheard; regenerate `commands.h`
- [ ] Morse legibility with 3 wearers at SLOW / NORMAL (T9)

## Phase 6 — Measure + write up
- [ ] T2–T5 gesture accuracy, false speech, latency
- [ ] T8 wristband latency, T10 battery, T11 comfort
- [ ] Results in `docs/results/` with confusion matrix
- [ ] Update blue book Ch. 4–5 and the paper (apply [ERRATA](docs/report/ERRATA.md))
- [ ] Demo video (bidirectional conversation)

## Phase 7 — v2.0 ideas
- [ ] ESP-NOW link: wristband confirms the glove's spoken word by touch
- [ ] FSR fingertip pressure sensors
- [ ] Custom PCB for the glove cuff (start from `docs/images/pcb_layout_glove.png`)
- [ ] Sweat-proof enclosure and strap; low-power sleep between signs
- [x] Temporal 1D-CNN gesture model + PC live decoder (v2.0-dev, placeholder until real data)
- [x] Glove hardware v2 design: 4.5″ flex, ADC filtering, LDO power, plug-in harness ([review](docs/design_review_v2.md))
- [ ] Hindi / Marathi phrases and voice; ISL dynamic signs (choose one-handed ISL subset first)
