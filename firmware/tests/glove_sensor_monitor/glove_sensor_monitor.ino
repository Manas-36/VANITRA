// Prints every glove sensor 10x per second — use it to check wiring before calibrating.
// Bend each finger: its flex mV should change by 500+ mV. Bring a magnet to each Hall sensor:
// its mV should move 300+ mV away from ~1650 mV. Tilt the hand: roll/pitch follow.
// Open Tools > Serial Plotter for live graphs.
#include <Wire.h>
static const int FLEX[5] = {4, 5, 6, 7, 8};
static const int HALL[4] = {9, 10, 1, 2};
#define SDA_PIN 16
#define SCL_PIN 17
bool imu = false;

void setup() {
  Serial.begin(115200);
  delay(1500);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.beginTransmission(0x68);
  imu = Wire.endTransmission() == 0;
  if (imu) { Wire.beginTransmission(0x68); Wire.write(0x6B); Wire.write(0); Wire.endTransmission(); }
  Serial.println(imu ? "MPU6050 found" : "MPU6050 NOT found");
}

void loop() {
  for (int i = 0; i < 5; i++) Serial.printf("flex%d:%d ", i + 1, analogReadMilliVolts(FLEX[i]));
  for (int i = 0; i < 4; i++) Serial.printf("hall%d:%d ", i + 1, analogReadMilliVolts(HALL[i]));
  if (imu) {
    Wire.beginTransmission(0x68); Wire.write(0x3B); Wire.endTransmission(false);
    Wire.requestFrom(0x68, 6);
    float ax = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.f;
    float ay = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.f;
    float az = (int16_t)(Wire.read() << 8 | Wire.read()) / 16384.f;
    Serial.printf("roll:%.0f pitch:%.0f", atan2f(ay, az) * 57.3f, atan2f(-ax, sqrtf(ay * ay + az * az)) * 57.3f);
  }
  Serial.println();
  delay(100);
}
