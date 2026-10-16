# Wokwi simulation — glove unit

Same idea as the Wokwi model in the SCS report (Fig. 9), updated to the current pin map.

| Real part | In the simulation |
|---|---|
| 5 flex sensors (GPIO 4–8) | 5 slide potentiometers — slide = bend |
| 4 SS49E Hall sensors (GPIO 9, 10, 1, 2) | 4 knobs — **middle = no magnet**, turn away from the middle = magnet near |
| MPU6050 (SDA 16 / SCL 17) | Wokwi MPU6050 — click it to tilt / shake |
| SSD1306 OLED | Wokwi SSD1306 — shows the recognised word |
| MAX98357A + speaker | not simulated (the word is printed on Serial and the OLED) |

**wokwi.com:** new *ESP32-S3* project → paste `diagram.json` → add all files from `firmware/glove_unit/` → add the libraries *Adafruit SSD1306* and *Adafruit GFX* → Start. `voice_clips.h` is 2 MB; if the web editor refuses it, run `python ml/make_voice_clips.py` with a shorter vocabulary, or replace it with an empty table (`VOICE_N` entries of `{nullptr, 0}`) for the simulation.

**VS Code:** install the Wokwi extension, compile with
`arduino-cli compile -b esp32:esp32:esp32s3:FlashSize=16M,PSRAM=opi,PartitionScheme=app3M_fat9M_16MB,CDCOnBoot=default --output-dir firmware/glove_unit/build firmware/glove_unit`, then open this folder and start the simulator (USB CDC On Boot must be *Disabled* for the simulator, because Wokwi shows the UART serial port).

Try it: type `c` in the serial monitor and follow the OLED (sliders all left = open hand, all right = fist). Then type `p` to see live predictions. The placeholder model was trained on synthetic data, so it will mostly answer REST — it is there to show the pipeline, not real signs.

> The diagram was written by hand to match `config.h` and has not been opened in Wokwi yet. If a wire shows as unconnected, drag it onto the pin named in the table.
