// Vanitra glove — sensor reading + per-user calibration (stored in flash with Preferences).
#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <Preferences.h>
#include "config.h"
#include "features.h"

struct Calibration {
  float flexStraight[5];   // mV with the finger straight
  float flexBent[5];       // mV with the finger fully bent (fist)
  float hallBase[4];       // mV with no magnet near (hand open)
  float gyroBias[3];       // deg/s at rest
  bool valid;
};

static Calibration cal;
static bool hallState[4] = {false, false, false, false};
static bool imuOk = false;
static uint8_t flexFault = 0;           // bit i set = flex i reads open/short for > 0.5 s (v2)
static uint8_t flexFaultCount[5] = {0};

// ------------------------------------------------------------------ raw reads
static float readMv(int pin, int n = 4) {
  uint32_t s = 0;
  for (int i = 0; i < n; i++) s += analogReadMilliVolts(pin);
  return (float)s / n;
}

static void mpuWrite(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}

static bool mpuBegin() {
  Wire.beginTransmission(MPU_ADDR);
  if (Wire.endTransmission() != 0) return false;
  mpuWrite(0x6B, 0x00);  // wake up, internal clock
  mpuWrite(0x1A, 0x03);  // DLPF 44 Hz
  mpuWrite(0x1B, 0x08);  // gyro +-500 deg/s  (65.5 LSB per deg/s)
  mpuWrite(0x1C, 0x08);  // accel +-4 g        (8192 LSB per g)
  return true;
}

// accel in g, gyro in deg/s (bias not removed)
static bool mpuRead(float &ax, float &ay, float &az, float &gx, float &gy, float &gz) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((uint8_t)MPU_ADDR, (uint8_t)14) != 14) return false;
  int16_t v[7];
  for (int i = 0; i < 7; i++) v[i] = (int16_t)((Wire.read() << 8) | Wire.read());
  ax = v[0] / 8192.f; ay = v[1] / 8192.f; az = v[2] / 8192.f;
  gx = v[4] / 65.5f;  gy = v[5] / 65.5f;  gz = v[6] / 65.5f;   // v[3] = temperature
  return true;
}

// ------------------------------------------------------------------ calibration storage
static void calDefaults() {
  for (int i = 0; i < 5; i++) { cal.flexStraight[i] = 2150; cal.flexBent[i] = 1150; }
  for (int i = 0; i < 4; i++) cal.hallBase[i] = 1650;
  for (int i = 0; i < 3; i++) cal.gyroBias[i] = 0;
  cal.valid = false;
}

static void calLoad() {
  Preferences p;
  p.begin("vanitra", true);
  if (p.getBytesLength("cal") == sizeof(Calibration)) p.getBytes("cal", &cal, sizeof(Calibration));
  else calDefaults();
  p.end();
}

static void calSave() {
  cal.valid = true;
  Preferences p;
  p.begin("vanitra", false);
  p.putBytes("cal", &cal, sizeof(Calibration));
  p.end();
}

// Average all channels for `ms` milliseconds. Used by the calibration steps.
static void averageChannels(uint32_t ms, float *flex, float *hall, float *gyro) {
  double f[5] = {0}, h[4] = {0}, g[3] = {0};
  int n = 0, ng = 0;
  uint32_t t0 = millis();
  while (millis() - t0 < ms) {
    for (int i = 0; i < 5; i++) f[i] += readMv(FLEX_PINS[i]);
    for (int i = 0; i < 4; i++) h[i] += readMv(HALL_PINS[i]);
    float ax, ay, az, gx, gy, gz;
    if (imuOk && mpuRead(ax, ay, az, gx, gy, gz)) { g[0] += gx; g[1] += gy; g[2] += gz; ng++; }
    n++;
    delay(10);
  }
  for (int i = 0; i < 5; i++) flex[i] = f[i] / n;
  for (int i = 0; i < 4; i++) hall[i] = h[i] / n;
  for (int i = 0; i < 3; i++) gyro[i] = ng ? g[i] / ng : 0;
}

// ------------------------------------------------------------------ calibrated frame
static void sensorsBegin() {
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);   // 0 - ~3.1 V
  Wire.begin(I2C_SDA, I2C_SCL, 400000);
  imuOk = mpuBegin();
  calLoad();
}

// Fills one calibrated frame for the feature window.
static void readFrame(vf::Sample &s, float *rawFlexMv = nullptr, float *rawHallMv = nullptr) {
  for (int i = 0; i < 5; i++) {
    float mv = readMv(FLEX_PINS[i]);
    if (rawFlexMv) rawFlexMv[i] = mv;
    // v2: a cracked flex sensor or broken wire shows up as the pin stuck near GND or 3V3
    bool bad = mv < FLEX_OPEN_MV || mv > FLEX_SHORT_MV;
    if (!bad) { flexFaultCount[i] = 0; flexFault &= ~(1 << i); }
    else if (flexFaultCount[i] < 255 && ++flexFaultCount[i] > 25) flexFault |= (1 << i);
    float span = cal.flexBent[i] - cal.flexStraight[i];
    float x = fabsf(span) < 50 ? 0 : (mv - cal.flexStraight[i]) / span;
    s.flex[i] = constrain(x, 0.f, 1.f);
  }
  for (int i = 0; i < 4; i++) {
    float mv = readMv(HALL_PINS[i]);
    if (rawHallMv) rawHallMv[i] = mv;
    float d = fabsf(mv - cal.hallBase[i]);           // either magnet pole works
    if (!hallState[i] && d > HALL_ON_MV) hallState[i] = true;
    else if (hallState[i] && d < HALL_OFF_MV) hallState[i] = false;
    s.hall[i] = hallState[i] ? 1.f : 0.f;
  }
  float ax = 0, ay = 0, az = 1, gx = 0, gy = 0, gz = 0;
  if (imuOk) mpuRead(ax, ay, az, gx, gy, gz);
  s.ax = ax; s.ay = ay; s.az = az;
  s.gx = gx - cal.gyroBias[0]; s.gy = gy - cal.gyroBias[1]; s.gz = gz - cal.gyroBias[2];
}

static float batteryVolts() { return readMv(VBAT_PIN, 8) * 2.f / 1000.f; }
