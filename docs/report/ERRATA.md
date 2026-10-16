# Errata — 2025 reports vs. the v1.0 design

Fix these before submitting the blue book or paper again. The right-hand column shows what this repo now does.

| # | Where | What it says | Problem | Correct / v1.0 |
|---|---|---|---|---|
| 1 | Hackanova deck, slide 3 + plan | 5 flex sensors on **GPIO 4–7** | 4 pins for 5 sensors | GPIO **4, 5, 6, 7, 8** ([decisions D1](../decisions.md)) |
| 2 | Hackanova deck | Hall sensors on **GPIO 9–13** (5 pins) | Blue book says 2–4 Hall sensors | **4** SS49E on GPIO **9, 10, 1, 2** |
| 3 | Blue book §4.1, §4.4, §6.1 | IMU "optional" | Paper and deck treat it as core | IMU is **core** (D2) |
| 4 | Deck block diagram + plan | Wristband output "Text" / "text on display" | Reports say haptic Morse | Morse vibration **plus** optional OLED text (D7) |
| 5 | Paper §VI-B | Accuracy varied "under non-ideal **lighting**" | The glove has no camera; lighting does not matter | Say "with new users, sweat or loose fit" |
| 6 | Paper Fig. 2 caption | "Glove Unit" | The figure shows the wristband | "Fig. 2. Speech unit (wristband)" |
| 7 | Paper §IV-F(c) | Heading "Hall Effect Sensor Detection" | The text describes Morse encoding (duplicate heading) | "c) Text-to-Morse Encoding" |
| 8 | Paper §III-E | "...low-resource settings.**[]**" | Empty citation | Cite [12] (TinyML) or remove |
| 9 | Paper author block | "**Third Year**-36 / 16 / 02" | Now final year | "Final Year" (or keep if the paper is dated 2025) |
| 10 | Paper + blue book refs [5], [6] | URLs end in `?utm_source=chatgpt.com` | Tracking suffix | Delete the suffix |
| 11 | Blue book | "**REFRENCES**" | Spelling | "REFERENCES" |
| 12 | Paper §V-E, §VI-B | "lightweight speech-to-text", 85–90 % **word** recognition | Open STT on an ESP32-S3 is not realistic | "Offline phrase recognition (ESP-SR MultiNet) of a fixed list of up to 200 phrases" (D4) |
| 13 | Paper title page / affiliations | "Mechatronics **Engineeing**" | Spelling | "Engineering" |
| 14 | Paper §II | "**THERORETICAL** BACKGROUND" | Spelling | "THEORETICAL" |
| 15 | Paper §IV-D, §IV-F | "**Labled** Diagram", "**Relevent** Formula" | Spelling | "Labelled", "Relevant" |
| 16 | Paper Fig. 10 | "WokWi Simulation of **Speeh** Unit" | Spelling | "Speech" (also "Wokwi") |
| 17 | Paper §VI-A (Aug version) | "General Electrical Schematic of **Sppech** unit" | Spelling | "Speech" |
| 18 | Paper refs [11] | "...for **Dump** People" | Typo in the cited title (check the original) | "Dumb" as in the original title |
| 19 | Deck plan | Morse "50 ms dots, 150 ms dashes" | Too short to feel on a coin ERM motor | Dot 160 / 120 / 90 ms selectable (D6) |
| 20 | Blue book §1.4.2 | "Static American Sign Language alphabets" | The vocabulary is now 20 words/phrases, static and dynamic | Update scope to the vocabulary in `ml/vocabulary.csv` |
| 21 | All reports | Results 90–94 % / 85–90 % / 350–500 ms | Measured on the first prototype; v1.0 is new code | Re-measure with [testing.md](../testing.md) before quoting |
