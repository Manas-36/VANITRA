# Design decisions

Why the v1.0 design looks the way it does. Several decisions resolve contradictions between the SCS blue book, the IEEE paper and the Hackanova deck (listed in [report/ERRATA.md](report/ERRATA.md)).

## D1 — One pin map, owned by the firmware
**Problem.** The Hackanova deck put 5 flex sensors on "GPIO 4–7" (4 pins) and Hall sensors on "GPIO 9–13" (5 pins). The blue book said 2–4 Hall sensors.
**Decision.** Use **5 flex sensors on GPIO 4, 5, 6, 7, 8** and **4 Hall sensors on GPIO 9, 10, 1, 2**, all on ADC1 (ADC2 is not used). The pins are defined in `firmware/*/config.h`, and the schematics and [wiring.md](wiring.md) copy them. Four Hall sensors match the Wokwi model, which had 4 contact inputs.

## D2 — The IMU is a core sensor, not optional
**Problem.** The blue book called the MPU6050 "optional", while the paper and deck treat it as core.
**Decision.** It is **core**. Six of the 16 model features (roll, pitch, their change, gyro mean/max, accel spread) come from it. Without it, static hand shapes still work, but signs that differ only in motion (YES vs SORRY, GOOD vs BAD) cannot be told apart. The firmware still runs if the IMU is missing, so that wiring faults are easy to find.

## D3 — Analog Hall sensors (SS49E) instead of digital switches
The paper's formula is `if V_hall > V_threshold → contact`, which needs an analog output. Common A3144 switches also need ≥ 4.5 V. The **SS49E** is linear, runs on 3.3 V and is cheap. The firmware stores each sensor's no-magnet baseline during calibration and uses **|V − baseline|** with hysteresis (on > 250 mV, off < 150 mV), so either magnet pole works.

## D4 — The wristband recognises a fixed phrase list, not open dictation
**Problem.** The paper claimed "offline speech-to-text" with 85–90 % word accuracy on an ESP32-S3. General dictation on a microcontroller is not realistic, and judges will ask about it.
**Decision.** Use Espressif **ESP-SR** (WakeNet + MultiNet), which runs fully offline on the ESP32-S3 with PSRAM. It recognises up to 200 pre-defined phrases. v1.0 ships **49 phrases → 22 meanings** (`firmware/wristband_unit/phrases.csv`). This is the "keyword detection" framing the Hackanova deck already used. To add phrases, edit the CSV and run `tools/make_sr_commands.py`.

## D5 — Electret + preamp → INMP441 I2S microphone
ESP-SR expects clean 16 kHz digital audio over I2S. The INMP441 is digital, costs about the same as an electret + MAX9814, and avoids ADC noise. The wiring follows Espressif's reference example (SCK 17, WS 47, SD 16).

## D6 — Vibrate short codes, not whole sentences
At a comfortable 120 ms dot, Morse runs at about 10 words per minute, so a full sentence would take 15–30 s. Each meaning therefore has a **short code** of 1–6 characters ("are you okay" → `OK?`, "do you want water" → `WATER?`). A message takes **1–8 s** at normal speed (measured from `morse.h` timings). Danger phrases ("watch out") use a special pattern of three long buzzes that cannot be mistaken for a letter. There are three speeds (160/120/90 ms dot), changed by holding the button.
**Morse timing vs. the deck.** The deck said 50 ms dots and 150 ms dashes. A coin ERM motor needs about 30–50 ms just to spin up, so 50 ms dots are hard to feel. v1.0 starts at a 160 ms dot (learning) and lets the user speed up.

## D7 — The wristband output is haptic Morse, with optional OLED text
**Problem.** The reports said haptic Morse, but the deck's block diagram ended in "Text" and its plan mentioned "text on display".
**Decision.** **Morse vibration is the primary output** (silent, works without looking). A 0.96" OLED is **optional** on both units: on the wristband it shows the full sentence, and on the glove it shows the word being spoken so the signer can confirm it. The firmware detects at runtime whether an OLED is fitted.

## D8 — Glove speech = recorded clips over I2S, not a buzzer
The glove must say real words offline. Pre-made WAV clips (16 kHz mono, about 450 KB for 20 words) are embedded in flash and played through a **MAX98357A** I2S amplifier. `ml/make_voice_clips.py` creates them with espeak-ng, or from your own recordings, which sound much better. There is no runtime TTS and no SD card.

## D9 — Our own tiny neural network instead of TensorFlow Lite
The model is a 16→32→21 MLP (about 1,200 multiply-adds, well under 1 ms). It is exported by `ml/train.py` as plain C arrays (`model.h`) and run by about 40 lines of C++ (`mlp.h`). This avoids the TFLite toolchain, keeps the firmware easy to read, and lets the PC test check that the C++ output **matches Python to 1e-6**. TFLite Micro (bundled with core 3.x) remains an option if a 1D-CNN is needed for continuous signing.

## D10 — Window features instead of raw frames
The features are the mean flex per finger, the fraction of time each Hall sensor is in contact, roll/pitch and their change, and gyro mean/max and accel spread over **0.5 s**. They cover static signs (shape) and simple dynamic signs (motion) with only 16 numbers, which suits a small dataset collected by students. The window, features and model are all fixed in one place (`features.h` ↔ `vanitra_features.py`).

## D11 — REST class + confidence gate + stability
Real use is mostly "no sign". Without a REST class and a gate, the glove would talk all the time. A word is spoken only when the model says the same non-REST label with p ≥ 0.85 **three times in a row** (300 ms). The same word is not repeated unless the hand returns to REST or 2.5 s pass. All of these are `#define`s in `config.h`.

## D12 — Same board for both units
Both units use the **ESP32-S3-DevKitC-1 N16R8**. ESP-SR needs the PSRAM, the glove gets room for clips and future models, and one spare board covers both units.

## D13 — Power: 1S LiPo → TP4056 → MT3608 (5 V) → board 5V pin
These are cheap, easy-to-find modules. The board's own regulator makes 3.3 V. The amplifier runs directly from 5 V for volume. The battery voltage is read through a 100k/100k divider. Estimated runtime on 1000 mAh is about 8 h (glove) and about 5 h (wristband; ESP-SR keeps the CPU busy). These are estimates to be measured (see [testing.md](testing.md)).

## Open questions
- ASL or ISL? The vocabulary uses one-handed ASL-style signs because the glove is on one hand. For Indian users, an **ISL** vocabulary is the obvious next step: change `ml/vocabulary.csv` and record new data. No code changes are needed.
- Should the glove and wristband talk to each other (ESP-NOW)? Useful for confirming spoken words on the wrist. Planned for v2.0.
