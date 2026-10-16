// Lists every I2C device. Glove: SDA 16 / SCL 17 (MPU6050 0x68, OLED 0x3C).
// Wristband OLED: change to SDA 8 / SCL 9.
#include <Wire.h>
#define SDA_PIN 16
#define SCL_PIN 17

void setup() {
  Serial.begin(115200);
  delay(1500);
  Wire.begin(SDA_PIN, SCL_PIN);
}

void loop() {
  int found = 0;
  Serial.printf("Scanning SDA %d / SCL %d ...\n", SDA_PIN, SCL_PIN);
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  0x%02X %s\n", a, a == 0x68 ? "MPU6050" : a == 0x69 ? "MPU6050 (AD0 high)" : a == 0x3C ? "SSD1306 OLED" : "");
      found++;
    }
  }
  if (!found) Serial.println("  nothing - check 3V3, GND, SDA/SCL not swapped");
  delay(3000);
}
