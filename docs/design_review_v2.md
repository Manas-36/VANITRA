# Design review → hardware & model v2 (Oct 2026)

A critical look at Vanitra v1.0 before the parts are bought, and what changed because of it.
Schematic: [wiring/glove_unit.svg](wiring/glove_unit.svg) · decisions D14–D20 in [decisions.md](decisions.md) · model: [ml_pipeline.md](ml_pipeline.md#v2-temporal-cnn).

## Verdict

The architecture is sound: two offline ESP32-S3 units, per-user calibration, a REST class with a confidence gate, and a PC-tested model export. The weak points are elsewhere.

- **The glove's analog front end is fragile.** This covers how the flex sensors are mounted, how they are read and how the board is powered.
- **The model throws away time.** It averages half a second of signal into 16 numbers.
- **The vocabulary and the wristband do not yet match the target users**, deaf Indians who sign ISL.
- **None of the accuracy numbers in the reports have been measured on this design.**

v2 fixes the first two in hardware and code, and flags the third and fourth as decisions for the team.

## Problems found, ranked

| # | Severity | Problem | Why it matters | v2 change |
|---|---|---|---|---|
| 1 | Critical | **ASL-style vocabulary for Indian users.** Most ISL signs and the ISL alphabet use **two hands**. | One glove can never cover ISL fingerspelling, and the users the reports name sign ISL. | Not changed in code (team decision). Pick one-handed ISL signs for v2 (`ml/vocabulary.csv`). Plan a second glove over ESP-NOW for v3. |
| 2 | Critical | **The 90–94 % / 85–90 % / 350–500 ms figures are from the 2025 breadboard.** The shipped model is synthetic. | Judges and examiners ask "measured how?". | `train_cnn.py` reports **leave-one-user-out** and **drift** accuracy for both models on the same folds. Publish only those numbers. |
| 3 | Major | **The model sees 0.5 s, reduced to averages.** | The order of movement is lost (lift-then-bend = bend-then-lift), and most signs take longer than half a second. | **Temporal CNN** on 1.0 s of raw signal (D18). The MLP stays selectable. |
| 4 | Major | **Flex sensors fail at the pins and drift when glued along their length.** | Cracked pins cause intermittent readings, and the glove then speaks wrong words. A glued strip creases, which adds hysteresis and drift. | Mounting rules below. Thumb keeps a 2.2″ sensor; the other fingers get **4.5″** (D14). **Fault detection** in firmware (D17). **Drift augmentation** in training. |
| 5 | Major | **High-impedance dividers feed the ESP32 SAR ADC directly** (no capacitor). | The ADC's sampling capacitor charges from a 20–50 kΩ source and keeps part of the previous channel's voltage. This adds noise and crosstalk between fingers. | **100 nF on every analog input** (D15). |
| 6 | Major | **3.7 V → MT3608 boost → 5 V → board LDO → 3.3 V.** | The boost's switching ripple rides into the 3.3 V rail that powers the ratiometric sensors. Two conversions also waste battery, and the boost is one more part to fail. | **Battery → low-dropout 3.3 V LDO → 3V3 pin.** The amplifier runs from the battery directly (D16). |
| 7 | Moderate | **One 47 kΩ resistor for every flex sensor.** | Swing is largest when R = √(R_flat·R_bent). 47 kΩ suits a 2.2″ sensor but wastes range on a 4.5″. | 22 kΩ for 4.5″, 33 kΩ for 2.2″, plus the rule for any other sensor. |
| 8 | Moderate | **The glove is hard-wired to the electronics.** | It cannot be washed, and a sensor cannot be swapped at a competition. | **J1/J2/J3 plug-in harness** (D19). |
| 9 | Moderate | **The battery divider sits before the switch.** | It draws about 18 µA forever and flattens a stored glove. | Divider moved **after** the switch. |
| 10 | Moderate | **Silent failure modes:** a broken flex reads as "fully bent", and a low battery shifts the sensor rail. | The user cannot tell why the glove is wrong. | Firmware **reports a stuck flex** (OLED + beep + serial) and **warns at 3.5 V**. |
| 11 | Minor | 4 × SS49E draw about 6–10 mA each, all the time. | A noticeable share of the battery. | Not changed. If battery life is short, power them through a P-MOSFET or use a lower-current linear Hall IC. |
| 12 | Minor | The MPU6050 is end-of-life, and GY-521 clones vary. | Supply risk, noisier gyro. | Not changed. For a new IMU, ICM-42688-P or LSM6DSO (driver change in `sensors.h`). |
| 13 | Product | **Wristband:** most deaf users do not know Morse, and ESP-SR recognises only English and Mandarin. | Content arrives in a code the user has to learn, and there is no Hindi or Marathi. | Not changed here. Make the **OLED text the main channel** and keep vibration for alerts and the short codes. Note the language limit in the report. |

## Should the flex sensor be replaced?

**No, not by a different technology for this build.** Replace the *grade* and the *installation*. A bend sensor per finger is the right category for a ₹7k offline glove. Most of the flex sensor's bad reputation comes from problems 4–7 above, which are fixable. Each alternative fixes one weakness but brings a harder one for Vanitra specifically:

| Option | Reliability | Cost for 5 fingers | The catch for Vanitra |
|---|---|---|---|
| **Resistive flex, done right (v2)** | Good once mounted properly; some drift, which calibration and augmentation absorb | ≈ ₹4,200 (4 × 4.5″ + 1 × 2.2″) | Needs careful strain relief. Some hysteresis remains. |
| IMU on every finger (6 IMUs) | No wear or fatigue | ≈ ₹1,000 + I2C mux | **Finger bend is invisible to gravity when the palm faces sideways** (thumb-up hand: the bend axis is vertical). You would need gyro integration (drift) or magnetometers, and the **fingertip magnets would wreck magnetometers**. It also needs 20+ wires. |
| Magnet + linear Hall across each knuckle | No contact, no fatigue | ≈ ₹150 | **Crosstalk** with the 8 fingertip magnets and the 4 contact Halls already on the glove. Needs rigid 3D-printed hinges. |
| Capacitive soft bend sensors (e.g. Bend Labs) | Excellent: low drift, low hysteresis | ₹15,000+ imported | Cost and sourcing. |
| Optical (LED + phototransistor in a dark tube) | Fair; varies from build to build | ≈ ₹200 | Light leaks and tube kinks. Each sensor needs its own calibration. |
| Velostat / conductive thread | Poor: large drift | ≈ ₹100 | Worse than what you have. |

**Upgrade path (v3, if you write a research paper):** six IMUs (hand + 5 fingers) with the temporal model, and conductive-fabric contact pads instead of magnets so magnetometers become usable. That is a full redesign, not a sensor swap.

**Budget option:** keep 2.2″ sensors on every finger (saves about ₹1,980). Centre each one over the PIP joint, keep 33–47 kΩ dividers, and apply every other v2 change.

### Mounting rules (these matter more than the part)

1. **Anchor only the pin end**, to a stiff patch on the back of the hand at the knuckle. The strip slides inside a sewn fabric or silicone sleeve along the finger, and the tip stays free. **Never glue it along its length.**
2. **The pins must never bend.** Solder the wires, add heat-shrink over the pins and the first 15 mm, then hot-glue a small stiffener (a PCB offcut) across the joint. This is where nearly all flex sensors die.
3. Mount the **printed side out**, and bend only in the direction the sensor is designed for.
4. Use **silicone-insulated 28–30 AWG multi-strand wire** with a loop of slack at the wrist. Never use solid-core wire on a finger.
5. **Recalibrate every time the glove is put on** (hold BOOT 2 s). The firmware already supports this.

## The circuit (glove v2)

![Glove v2 schematic](wiring/glove_unit.png)

The pins are unchanged from v1, so the firmware pin map and the Wokwi diagram still apply. What changed:

- **Flex:** 3V3 → flex → J1 → GPIO, with R (22 kΩ fingers, 33 kΩ thumb) and 100 nF to GND on the cuff.
- **Hall:** SS49E OUT → J2 → 100 nF → GPIO, plus 100 nF across VCC–GND at each sensor.
- **Power:** LiPo → TP4056 + DW01 → switch → **VSYS** → AP2112K-3.3 / ME6211C33 → board **3V3** pin. VSYS → MAX98357A VIN (+100 µF). The board's 5V pin is left free.
- **Battery sense:** VSYS → 100k/100k (+100 nF) → GPIO3, after the switch.
- The **IMU** moves to the cuff side of a 4-pin JST-SH (J3), so the glove part is washable.

## The AI (model v2): temporal CNN

`ml/vanitra_cnn.py` + `ml/train_cnn.py` → `firmware/glove_unit/model_cnn.h` → `cnn.h` on the ESP32-S3.

```
15 channels x 50 frames (1.0 s)  ->  conv k5 24  ->  pool  ->  conv k5 32  ->  pool  ->  conv k3 32
                                  ->  [mean | max over time]  ->  dense  ->  softmax (21 signs incl. REST)
```

- **About 10 k weights (40 KB), ~0.23 M multiply-adds, a few ms per call** on the S3. It runs every 100 ms behind the same confidence gate, stability check and REST logic as v1.
- **Written in NumPy, not PyTorch.** It trains on any laptop. The C++ is a line-for-line mirror, and the PC test checks that both give the same probabilities (to 1e-7).
- **Training augmentation** mimics real glove problems:
  - time-stretch 0.8–1.25×
  - per-finger flex gain/offset (drift, re-wearing)
  - IMU tilt up to 12°
  - noise and Hall flicker
- **The report compares CNN and MLP on the same folds.** It covers clean windows and "drifted" ones (glove re-worn without recalibrating), and supports `--by-user` for the honest new-person number.
- **`ml/live_decoder.py`** runs the same model and the same speaking rules on a laptop. It shows the top-3 guesses live, builds a transcript, can speak aloud, and can replay recorded takes. Use it for demos and for tuning before flashing.

**Results so far are synthetic only.** These figures are leave-one-user-out on the generated data (6 fake signers, 378 takes); regenerate the report with `python ml/train_cnn.py --synthetic --by-user`.

| Model | Clean | Drifted |
|---|---|---|
| CNN v2 | 98.1 % | 98.0 % |
| MLP v1 | 97.2 % | 96.8 % |

This proves the pipeline runs end to end, and that the drift augmentation does its job. It says nothing about real accuracy. The one weak pair, **THANK_YOU vs GOOD (about 80 %)**, is a real vocabulary problem, not a model problem. In the vocabulary both are a flat hand moving down from the chin. Give one of them a clearly different sign. The real comparison comes from your recordings. Record them with `collect_data.py` (≥ 5 takes × every sign × ≥ 3 people), run `python ml/train_cnn.py --by-user`, and ship whichever model wins (`GESTURE_MODEL` in `config.h`).

## Not verified yet

- **Firmware:** the glove sketch compiles on a PC against Arduino stubs, with both models and `-Wall -Wextra` clean. The PC parity tests pass. **It has not been built with the ESP32 Arduino core after these changes and has not run on hardware.**
- **Hardware:** the divider values follow the Spectra datasheet ranges. Measure your own sensors flat and at a natural fist, and recompute R = √(R_flat·R_bent).
- **Power:** check LDO dropout on your module at 3.5 V with the speaker playing.
