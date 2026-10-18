# Firmware

| Folder | Board settings | What |
|---|---|---|
| `glove_unit/` | ESP32S3 Dev Module · 16MB · OPI PSRAM · *16M Flash (3MB APP/9.9MB FATFS)* | sign → speech |
| `wristband_unit/` | ESP32S3 Dev Module · 16MB · **OPI PSRAM** · ***ESP SR 16M*** | speech → Morse vibration |
| `tests/*` | any ESP32-S3 | one-part hardware checks |
| `tests/host/` | your PC (`make`) | logic tests, no ESP32 needed |
| `wokwi/glove/` | Wokwi simulator | glove with pots instead of sensors |

Arduino IDE 2 + **esp32 core 3.x** (built with 3.2.0). Libraries: Adafruit SSD1306 + Adafruit GFX (OLED). ESP-SR and ESP_I2S come with the core.

Generated files — don't edit by hand:
- `glove_unit/model_cnn.h` ← `ml/train_cnn.py` (v2 CNN, default; `GESTURE_MODEL` in `config.h`)
- `glove_unit/model.h` ← `ml/train.py` (v1 MLP)
- `glove_unit/voice_clips.h` ← `ml/make_voice_clips.py`
- `wristband_unit/commands.h` ← `tools/make_sr_commands.py` (from `phrases.csv`)
- `tests/host/test_vectors.h` ← `ml/train.py`

Pins: `*/config.h` (drawn in `docs/wiring/`). Setup: [docs/setup.md](../docs/setup.md).
