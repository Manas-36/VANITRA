// Vanitra glove unit — pins and tuning.
// Board: ESP32-S3-DevKitC-1 N16R8 (Arduino: "ESP32S3 Dev Module").
// Pin map is the single source of truth — docs/pin_map.md and docs/wiring/*.svg are drawn from it.
#pragma once

// ---------------------------------------------------------------- flex sensors (ADC1)
// Each flex sensor: 3V3 -> flex -> pin -> R -> GND, plus 100 nF from pin to GND (hardware v2).
// v2: thumb 2.2" with R = 33k, index..little 4.5" with R = 22k. Rule: R = sqrt(R_flat * R_bent).
// Order: thumb, index, middle, ring, little.
static const int FLEX_PINS[5] = {4, 5, 6, 7, 8};          // ADC1_CH3..CH7
#define FLEX_OPEN_MV      120   // below this the sensor or its wire is broken (pin pulled to GND)
#define FLEX_SHORT_MV     3150  // above this the sensor is shorted (pin at 3V3)

// ---------------------------------------------------------------- Hall sensors (ADC1)
// SS49E linear Hall sensors, OUT read as analog. Magnets sit on the fingertips.
// H1 thumb tip, H2 thumb side (index contact), H3 palm centre (curled fingertips), H4 index-middle side.
static const int HALL_PINS[4] = {9, 10, 1, 2};            // ADC1_CH8, CH9, CH0, CH1
#define HALL_ON_MV        250   // |V - baseline| above this = magnet near (contact)
#define HALL_OFF_MV       150   // ...and below this = released (hysteresis)

// ---------------------------------------------------------------- I2C: MPU6050 (0x68) + optional OLED (0x3C)
#define I2C_SDA           16
#define I2C_SCL           17
#define MPU_ADDR          0x68
#define HAS_OLED          1     // 0.96" SSD1306; auto-skipped at runtime if not found

// ---------------------------------------------------------------- speaker: MAX98357A I2S amplifier
#define I2S_BCLK          12
#define I2S_LRC           13
#define I2S_DOUT          14
#define AMP_SD_PIN        21    // MAX98357A SD: HIGH = on, LOW = shutdown (saves ~2 mA)

// ---------------------------------------------------------------- misc
#define BUTTON_PIN        0     // BOOT button: short = repeat last word, hold 2 s = calibrate
#define VBAT_PIN          3     // battery via 100k/100k divider (ADC1_CH2)
#define STATUS_LED        RGB_BUILTIN   // on-board WS2812 (GPIO48 on DevKitC-1 v1.0, GPIO38 on v1.1)

#define VBAT_LOW_V        3.50f // v2 power runs the 3.3 V LDO straight from the cell: warn below this
                                // (the LDO drops out and the sensor rail sags, which shifts calibration)

// ---------------------------------------------------------------- gesture model
#define GESTURE_MODEL_MLP 1     // v1: 0.5 s window, 16 hand-made features, MLP (model.h)
#define GESTURE_MODEL_CNN 2     // v2: 1.0 s window, raw signal, temporal CNN (model_cnn.h)
#define GESTURE_MODEL     GESTURE_MODEL_CNN

// ---------------------------------------------------------------- recognition tuning
#define SAMPLE_HZ         50    // sensor frame rate
#define CLASSIFY_EVERY    5     // run the model every N frames (=100 ms)
#define CONF_THRESHOLD    0.85f // softmax probability needed
#define STABLE_COUNT      3     // same answer N times in a row before speaking
#define REPEAT_GAP_MS     2500  // same word again only after REST or this long
#define SPEAK_COOLDOWN_MS 600   // ignore the hand right after speaking
