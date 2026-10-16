// =====================================================================================
//  VANITRA — wristband unit (speech -> Morse vibration)
//  INMP441 mic -> ESP-SR (WakeNet "Hi ESP" + MultiNet phrase recognition, fully offline)
//  -> short Morse code on a vibration motor (+ optional OLED text)
//  Board: ESP32-S3-DevKitC-1 N16R8 · Arduino IDE, esp32 core 3.x · "ESP32S3 Dev Module"
//  Tools: Flash 16MB, PSRAM OPI, Partition "ESP SR 16M (3MB APP/7MB SPIFFS/2.9MB MODEL)",
//         USB CDC On Boot: Enabled.  The speech models are flashed automatically with the sketch.
//
//  Use:  hearing person says "Hi ESP" (or the wearer taps the button), then a phrase from phrases.csv.
//        Tap = listen now · double tap = replay last message · hold 1.5 s = Morse speed
//  Serial (115200): type any text + Enter to feel it in Morse (practice / demo).
// =====================================================================================
#include <Preferences.h>
#include "ESP_I2S.h"
#include "ESP_SR.h"
#include "config.h"
#include "commands.h"
#include "morse.h"
#include "haptic.h"

#if HAS_OLED
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
static Adafruit_SSD1306 oled(128, 64, &Wire, -1);
#endif
static bool oledOk = false;

static I2SClass i2s;
static volatile int pendingCmd = -1;
static volatile bool evWake = false, evTimeout = false;
static int lastCmd = -1;
static int speed = MORSE_DEFAULT_SPEED;
static bool srPaused = false;
static String serialLine, lastText;

// ------------------------------------------------------------------ LED + OLED
static void led(uint8_t r, uint8_t g, uint8_t b) { rgbLedWrite(STATUS_LED, r, g, b); }
static void ledIdle() { led(0, 8, 0); }

static void morseString(const char *text, char *out, size_t n) {
  out[0] = 0;
  if (strcmp(text, "*ALERT") == 0) { strncpy(out, "!!! ALERT !!!", n); return; }
  for (const char *p = text; *p; p++) {
    const char *c = (*p == ' ') ? "/" : morse::code(*p);
    if (!c) continue;
    strncat(out, c, n - strlen(out) - 1);
    strncat(out, " ", n - strlen(out) - 1);
  }
}

static void show(const char *title, const char *text, const char *code) {
#if HAS_OLED
  if (!oledOk) return;
  oled.clearDisplay();
  oled.setTextSize(1); oled.setCursor(0, 0); oled.print(title);
  oled.setTextSize(strlen(text) <= 10 ? 2 : 1); oled.setCursor(0, 16); oled.print(text);
  oled.setTextSize(1); oled.setCursor(0, 48); oled.print(code);
  oled.display();
#endif
}

// ------------------------------------------------------------------ messages
static void playMessage(const char *morseText, const char *display) {
  char code[96];
  morseString(morseText, code, sizeof code);
  Serial.printf("[vibrate] %s  ->  %s   (%s)\n", display, code, MORSE_SPEED_NAMES[speed]);
  show("MESSAGE", display, code);
  if (!srPaused) { ESP_SR.pause(); srPaused = true; }   // motor noise must not reach the mic
  led(30, 0, 30);
  hapticPlayText(morseText, MORSE_UNITS[speed]);
}

static void playCommand(int id) {
  if (id < 0 || id >= CMD_COUNT) return;
  lastCmd = id;
  lastText = "";
  playMessage(PHRASES[id].morse, PHRASES[id].display);
}

// ------------------------------------------------------------------ speech recognition (runs in the ESP-SR task)
static void onSrEvent(sr_event_t event, int command_id, int phrase_id) {
  switch (event) {
    case SR_EVENT_WAKEWORD: evWake = true; break;
    case SR_EVENT_WAKEWORD_CHANNEL: ESP_SR.setMode(SR_MODE_COMMAND); break;
    case SR_EVENT_TIMEOUT: evTimeout = true; ESP_SR.setMode(SR_MODE_WAKEWORD); break;
    case SR_EVENT_COMMAND:
      Serial.printf("[heard] \"%s\" -> %s\n", SR_COMMANDS[phrase_id].str, PHRASES[command_id].name);
      pendingCmd = command_id;
      ESP_SR.setMode(SR_MODE_COMMAND);   // keep listening for a follow-up until timeout
      break;
    default: break;
  }
}

static void listenNow() {
  ESP_SR.setMode(SR_MODE_COMMAND);
  led(0, 0, 40);
  hapticPulses(2, 60, 90);              // "listening" tick-tick
  show("LISTENING", "...", "say a phrase");
}

// ------------------------------------------------------------------ button: tap / double tap / hold
static void cycleSpeed() {
  speed = (speed + 1) % 3;
  Preferences p; p.begin("vanitra", false); p.putUChar("speed", speed); p.end();
  const char *letter = speed == 0 ? "S" : speed == 1 ? "N" : "F";
  playMessage(letter, MORSE_SPEED_NAMES[speed]);
}

static void handleButton() {
  static uint32_t downAt = 0, lastTapAt = 0;
  static bool wasDown = false, held = false, tapPending = false;
  bool down = digitalRead(BUTTON_PIN) == LOW;
  uint32_t now = millis();
  if (down && !wasDown) { downAt = now; held = false; }
  if (down && !held && now - downAt > 1500) { held = true; tapPending = false; cycleSpeed(); }
  if (!down && wasDown && !held && now - downAt > 30) {
    if (tapPending && now - lastTapAt < 400) {          // double tap -> replay
      tapPending = false;
      if (lastCmd >= 0) playCommand(lastCmd);
      else if (lastText.length()) playMessage(lastText.c_str(), lastText.c_str());
    } else { tapPending = true; lastTapAt = now; }
  }
  if (tapPending && !down && now - lastTapAt >= 400) { tapPending = false; listenNow(); }
  wasDown = down;
}

// ------------------------------------------------------------------ serial: type text to feel it
static void handleSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c != '\n') { if (serialLine.length() < 60) serialLine += c; continue; }
    serialLine.trim();
    if (serialLine.length()) {
      serialLine.toUpperCase();
      lastText = serialLine;
      lastCmd = -1;
      playMessage(lastText.c_str(), lastText.c_str());
    }
    serialLine = "";
  }
}

// ------------------------------------------------------------------ setup / loop
void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  hapticBegin();
  Preferences p; p.begin("vanitra", true); speed = p.getUChar("speed", MORSE_DEFAULT_SPEED) % 3; p.end();

#if HAS_OLED
  Wire.begin(OLED_SDA, OLED_SCL);
  Wire.beginTransmission(0x3C);
  if (Wire.endTransmission() == 0 && oled.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    oledOk = true;
    oled.setTextColor(SSD1306_WHITE);
  }
#endif

  i2s.setPins(MIC_SCK, MIC_WS, -1, MIC_SD);
  i2s.setTimeout(1000);
  if (!i2s.begin(I2S_MODE_STD, 16000, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO)) {
    Serial.println("[mic] I2S init failed - check INMP441 wiring");
  }
  ESP_SR.onEvent(onSrEvent);
  bool ok = ESP_SR.begin(i2s, SR_COMMANDS, SR_COMMANDS_LEN, SR_CHANNELS_STEREO, SR_MODE_WAKEWORD);
  Serial.printf("\nVANITRA wristband %s. %d phrases. Say \"Hi ESP\" or tap the button. Morse speed %s.\n",
                ok ? "ready" : "SPEECH INIT FAILED (PSRAM on? partition ESP SR 16M?)", (int)SR_COMMANDS_LEN,
                MORSE_SPEED_NAMES[speed]);
  show("VANITRA", ok ? "READY" : "SR FAILED", "say: Hi ESP");
  playMessage("V", "READY");             // short hello buzz: ...-
}

void loop() {
  handleSerial();
  handleButton();

  if (evWake) {
    evWake = false;
    led(0, 0, 40);
    if (!hapticBusy()) hapticPulses(2, 60, 90);
    show("LISTENING", "...", "say a phrase");
  }
  if (evTimeout) { evTimeout = false; ledIdle(); }

  int cmd = pendingCmd;
  if (cmd >= 0 && !hapticBusy()) { pendingCmd = -1; playCommand(cmd); }

  if (!hapticUpdate() && srPaused) {     // playback finished -> listen again
    ESP_SR.resume();
    srPaused = false;
    ledIdle();
  }
  delay(2);
}
