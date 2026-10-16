# Presentations

| File | Event |
|---|---|
| [Vanitra_SCS_Mini_Project.pptx](Vanitra_SCS_Mini_Project.pptx) | SCS mini project review, AY 2025-26 (13 slides) |
| [Mtx.Vanitra_Hackanova_5.0_Hardware.pdf](Mtx.Vanitra_Hackanova_5.0_Hardware.pdf) | Hackanova 5.0, hardware track — team **Mtx.Vanitra** |

Before the next presentation:
- SCS deck **slide 6** still has the template's "Road map of operation management" text (Define / Analysis / Improvement / Control) — replace it with `docs/wiring/system_overview.png`.
- Use the schematics from `docs/wiring/*.png` and the pin map from `docs/wiring.md` (the Hackanova slide's GPIO 4-7 / 9-13 is wrong — see `docs/report/ERRATA.md`).
- Say "offline phrase recognition (ESP-SR)" rather than "speech-to-text".
- Only quote accuracy numbers measured with `docs/testing.md`.

Likely judge questions and short answers:
| Question | Answer |
|---|---|
| How is speech recognised offline on a microcontroller? | Espressif ESP-SR (WakeNet + MultiNet) on the ESP32-S3 with 8 MB PSRAM, fixed list of up to 200 phrases, no cloud. |
| Why Morse? Deaf users don't know Morse. | Short codes (HI, OK?, WATER?) are learnt in minutes; the full text is also on the OLED. Morse is silent and screen-free; three speeds plus a slow learning speed. |
| What about different hand sizes? | Per-user calibration (open hand + fist, 6 s) normalises every flex sensor to 0..1; Hall uses each sensor's own baseline. |
| How do you avoid speaking random words? | REST class + 85 % confidence + same answer 3× in a row + repeat lockout. |
| ASL or ISL? | Vocabulary is a CSV; ISL is the next dataset (no code change). |
| Cost? | ≈ ₹7,000 for both units (hardware/bom.csv), most of it the flex sensors. |
