// Vanitra glove — optional 0.96" SSD1306 OLED on the I2C bus (0x3C).
// Shows the word being spoken so the signer can confirm what the listener heard.
#pragma once
#include <Arduino.h>
#include "config.h"

#if HAS_OLED
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
static Adafruit_SSD1306 oled(128, 64, &Wire, -1);
static bool oledOk = false;

static void displayBegin() {
  Wire.beginTransmission(0x3C);
  if (Wire.endTransmission() != 0) return;           // not fitted
  oledOk = oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  if (oledOk) { oled.setTextColor(SSD1306_WHITE); oled.clearDisplay(); oled.display(); }
}

// title: small line on top; big: main text (auto-sized); foot: small bottom line
static void displayShow(const char *title, const char *big, const char *foot = "") {
  if (!oledOk) return;
  oled.clearDisplay();
  oled.setTextSize(1); oled.setCursor(0, 0); oled.print(title);
  int len = strlen(big);
  oled.setTextSize(len <= 10 ? 2 : 1);
  oled.setCursor(0, 22); oled.print(big);
  oled.setTextSize(1); oled.setCursor(0, 56); oled.print(foot);
  oled.display();
}
#else
static void displayBegin() {}
static void displayShow(const char *, const char *, const char * = "") {}
#endif
