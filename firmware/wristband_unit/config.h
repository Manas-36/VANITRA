// Vanitra wristband unit — pins and tuning.
// Board: ESP32-S3-DevKitC-1 N16R8 (8 MB PSRAM is REQUIRED by ESP-SR speech recognition).
#pragma once

// ---------------------------------------------------------------- INMP441 I2S microphone
#define MIC_SCK          17     // BCLK
#define MIC_WS           47     // LRCL / WS
#define MIC_SD           16     // DOUT of the mic -> ESP32 data in.  L/R pin -> GND (left channel)

// ---------------------------------------------------------------- vibration motor
#define HAPTIC_PIN       4      // gate of AO3400 / 2N7000 MOSFET (or base of 2N2222 via 1 kOhm)
#define HAPTIC_PWM_HZ    5000
#define HAPTIC_DUTY      230    // 0-255, strength of the buzz

// ---------------------------------------------------------------- UI
#define BUTTON_PIN       5      // to GND. tap = listen now, double tap = replay, hold 1.5 s = speed
#define STATUS_LED       RGB_BUILTIN
#define HAS_OLED         1      // optional 0.96" SSD1306 shows the text; skipped if not found
#define OLED_SDA         8
#define OLED_SCL         9
#define VBAT_PIN         1      // battery via 100k/100k divider

// ---------------------------------------------------------------- Morse speeds (dot length, ms)
static const uint16_t MORSE_UNITS[3] = {160, 120, 90};   // slow (learning), normal, fast
static const char *const MORSE_SPEED_NAMES[3] = {"SLOW", "NORMAL", "FAST"};
#define MORSE_DEFAULT_SPEED 0
