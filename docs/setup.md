# Setup — from parts to a working pair

## 1. Software
- **Arduino IDE 2.x.** In *Boards Manager*, install **esp32 by Espressif, version 3.x**. v1.0 was compiled with 3.2.0.
- In *Library Manager*, install **Adafruit SSD1306** and **Adafruit GFX Library**. These are only needed when `HAS_OLED 1`, which is the default.
- **Python 3.10+** for the ML tools: `pip install -r ml/requirements.txt`.

## 2. Board settings (Tools menu)

| Setting | Glove | Wristband |
|---|---|---|
| Board | ESP32S3 Dev Module | ESP32S3 Dev Module |
| Flash Size | 16MB (128Mb) | 16MB (128Mb) |
| PSRAM | OPI PSRAM | **OPI PSRAM (required)** |
| Partition Scheme | 16M Flash (3MB APP/9.9MB FATFS) | **ESP SR 16M (3MB APP/7MB SPIFFS/2.9MB MODEL)** |
| USB CDC On Boot | Enabled | Enabled |
| Upload / Serial | the **USB** port (or COM port of the UART port with CDC disabled) | same |

With arduino-cli:
```bash
arduino-cli compile -u -p COM5 -b "esp32:esp32:esp32s3:FlashSize=16M,PSRAM=opi,PartitionScheme=app3M_fat9M_16MB,CDCOnBoot=cdc" firmware/glove_unit
arduino-cli compile -u -p COM6 -b "esp32:esp32:esp32s3:FlashSize=16M,PSRAM=opi,PartitionScheme=esp_sr_16,CDCOnBoot=cdc" firmware/wristband_unit
```
With the ESP SR partition selected, the wristband's speech models (`srmodels.bin`) are flashed automatically together with the sketch.

## 3. Bring-up, one part at a time
Wire each part following [wiring.md](wiring.md), flash a test sketch from `firmware/tests/`, and check its output before moving on.

| Sketch | Check |
|---|---|
| `i2c_scan` | Shows 0x68 (MPU6050) and 0x3C (OLED) |
| `glove_sensor_monitor` | Each flex reading changes by 500 mV or more when bent. Each Hall reading moves 300 mV or more when a magnet comes close. Roll and pitch follow the hand. Use the Serial Plotter. |
| `speaker_test` | A clear three-tone chime every 2 s |
| `mic_level_test` | The bar jumps when you talk and stays low when the room is quiet |
| `haptic_test` | S-O-S buzzes you can clearly feel |

## 4. Glove
1. Flash `firmware/glove_unit`. The serial monitor should print `VANITRA glove ready. IMU: ok`.
2. **Calibrate** by holding BOOT for 2 s, or by typing `c`:
   - LED blinks blue: open your hand flat, fingers straight and still, for 3 s.
   - LED blinks yellow: make a tight fist for 3 s.
   - LED turns green: saved. The calibration is kept in flash.
   Calibrate again whenever someone else wears the glove.
3. The models shipped in `model_cnn.h` (v2, default) and `model.h` (v1) are **placeholders trained on synthetic data**. Record real data and train before expecting correct words (next section).
4. Serial commands: `h` help · `c` calibrate · `p` print live predictions · `i` info · `s` / `x` stream raw frames on / off.

## 5. Train the glove on real signs
See [ml_pipeline.md](ml_pipeline.md). In short:
```bash
python ml/collect_data.py --port COM5 --user manas      # each person, every sign, 5+ takes
python ml/train_cnn.py --by-user                         # v2: writes firmware/glove_unit/model_cnn.h (+ CNN vs MLP report)
python ml/train.py                                       # v1: writes firmware/glove_unit/model.h
make -C firmware/tests/host                              # optional: PC parity test
```
Then re-flash the glove.

Voice: `python ml/make_voice_clips.py` (espeak-ng) or `--wav-dir recordings/`, where the folder holds your own `HELLO.wav`, `THANK_YOU.wav` and so on.

## 6. Wristband
1. Flash `firmware/wristband_unit` with the **ESP SR 16M** partition. You should feel a short `...-` (V) buzz at start-up.
2. Say **"Hi ESP"**. You feel tick-tick and the LED turns blue. Then say a phrase from `firmware/wristband_unit/phrases.csv`, e.g. "are you okay". The band vibrates `OK?`.
3. **Button:** tap = listen now without the wake word · double tap = replay the last message · hold 1.5 s = cycle the speed SLOW → NORMAL → FAST.
4. Type any text in the serial monitor and press Enter to feel it in Morse. This is useful for practice and demos.

**Adding phrases:** edit `phrases.csv` (alternatives separated by `|`), then run
```bash
pip install --no-deps g2p_en && pip install nltk inflect
python tools/make_sr_commands.py
```
and re-flash. Prefer phrases of 2–4 words; single short words ("yes", "no") are recognised less reliably and trigger more false matches. The maximum is 200 phrases.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Glove: `IMU: MISSING` | Run `i2c_scan`. Check that SDA 16 / SCL 17 are not swapped and that AD0 is on GND. |
| A flex reading barely changes | Wrong divider: the flex must go to 3V3 and the 47k to GND. Calibration warns `span < 150 mV`. |
| Hall sensor stuck at 0 or 1 | Turn the magnet over or move it closer. Recalibrate with the magnets **away** from the sensors. |
| Glove speaks random words | The model is still the placeholder, or calibration was done by someone else. Retrain, or raise `CONF_THRESHOLD`. |
| No sound | Run `speaker_test`. Check that the amp's SD pin is on GPIO21 (or tied to VIN) and that VIN is 5 V. |
| Wristband: `SPEECH INIT FAILED` | PSRAM must be set to **OPI** and the partition must be **ESP SR 16M**. The board must be an N16R8. |
| Wristband never hears the wake word | Run `mic_level_test`. Check L/R → GND and that the mic hole faces out. Speak 0.5–1 m away. |
| Brown-out resets when the speaker or motor runs | Glove v2: check the 100 µF at the amp VIN and the 10 µF at the LDO, and charge the battery (the LDO drops out below about 3.5 V). Wristband: MT3608 at 5.0 V with a good LiPo, plus 470 µF across 5V/GND. |
