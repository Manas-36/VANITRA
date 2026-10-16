# Test plan and acceptance criteria

These are the KPIs from the blue book (§3.8), turned into tests that anyone can repeat with this firmware. Record the results in `docs/results/` (CSV + a short note) and only quote numbers in reports and decks after they are measured here.

## Automated (no hardware)
| Test | Command | Pass |
|---|---|---|
| Feature + neural-net parity (Python vs C++) | `make -C firmware/tests/host` | `glove tests passed` |
| Morse timing (dots, dashes, gaps, alert) | same | `morse tests passed` |
| Both firmwares compile | Arduino IDE / arduino-cli (see setup.md) | no errors |

## Bench tests
| ID | What | How | Target (blue book KPI) |
|---|---|---|---|
| T1 | Sensor ranges | `glove_sensor_monitor`: bend each finger, bring a magnet to each Hall sensor | flex span ≥ 500 mV; Hall change ≥ 300 mV |
| T2 | Gesture accuracy, known users | 20 attempts per sign per user, after calibration; count correct spoken words | **≥ 90 %** |
| T3 | Gesture accuracy, new user | as T2, with a person who is not in the training data (also `train.py --by-user`) | report it (expect lower) |
| T4 | False speech | 5 min of normal hand use (typing, drinking, gesturing) with no signing; count words spoken | ≤ 1 per 5 min |
| T5 | Glove latency | film the hand and listen at 240 fps (phone slow-mo); time from sign completed to start of the voice | **350–500 ms** |
| T6 | Phrase recognition, quiet room | 2 speakers × 22 meanings × 5 tries at 0.5–1 m | **≥ 85 %** correct meaning |
| T7 | Phrase recognition, noisy | as T6 with a fan / class noise (~60 dB) | report it |
| T8 | Wristband latency | time from end of phrase to first buzz | ≤ 1 s |
| T9 | Morse legibility | the wearer names 20 random short codes, at SLOW and NORMAL speed, after 10 min practice | ≥ 80 % at SLOW |
| T10 | Battery life | full charge, glove classifying + speaking once a minute / wristband listening; log VBAT on serial | **4–6 h** minimum |
| T11 | Comfort | 30 min continuous wear, 3 users, 1–5 rating | ≥ 4/5 |

## Recording results
Make `docs/results/<date>_<test>.csv` with one row per attempt, for example `user,sign,attempt,spoken,correct,latency_ms`. Summarise each test in `docs/results/README.md`. For T2/T3, also add the `ml/reports/confusion.png` from the model that was used.

## Results so far
| Test | Result | Hardware / firmware |
|---|---|---|
| Parity + Morse unit tests | ✅ pass (feature error ~1e-6, probability error ~1e-7) | PC, v1.0 |
| Firmware build | ✅ glove 889 KB, wristband 738 KB (core 3.2.0) | v1.0 |
| T2, T6, T5 (blue book, 2025) | 90–94 %, 85–90 %, 350–500 ms | first breadboard prototype, earlier firmware; not yet repeated |
| T1–T11 on v1.0 | ⏳ not run yet | — |
