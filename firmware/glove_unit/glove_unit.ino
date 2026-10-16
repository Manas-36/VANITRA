// =====================================================================================
//  VANITRA — glove unit (gesture -> speech)
//  5 flex + 4 Hall (SS49E) + MPU6050  ->  feature window  ->  on-device neural net  ->  voice clip
//  Board: ESP32-S3-DevKitC-1 N16R8 · Arduino IDE, esp32 core 3.x · "ESP32S3 Dev Module"
//  Tools: Flash 16MB, PSRAM OPI, Partition "16M Flash (3MB APP/9.9MB FATFS)", USB CDC On Boot: Enabled
//  Libraries: Adafruit SSD1306 + Adafruit GFX (only if HAS_OLED 1)
//
//  Serial (115200): h help · c calibrate · s/x stream raw frames on/off (for ml/collect_data.py)
//                   p predictions on/off · i info
// =====================================================================================
#include "config.h"
#include "features.h"
#include "mlp.h"
#include "sensors.h"
#include "voice.h"
#include "display.h"

static vf::Window win;
static bool streaming = false, printPred = false;
static uint32_t frameNo = 0, nextFrameUs = 0;

// recognition state
static int candidate = -1, candidateCount = 0, lastSpoken = -1;
static bool restSinceLast = true;
static uint32_t lastSpokenMs = 0, cooldownUntil = 0;

// ------------------------------------------------------------------ status LED
static void led(uint8_t r, uint8_t g, uint8_t b) { rgbLedWrite(STATUS_LED, r, g, b); }
static void ledIdle() { if (streaming) led(12, 0, 12); else if (cal.valid) led(0, 10, 0); else led(14, 0, 0); }

// ------------------------------------------------------------------ calibration
static void countdown(const char *what, uint8_t r, uint8_t g, uint8_t b) {
  Serial.printf("[cal] %s ...\n", what);
  displayShow("CALIBRATION", what, "get ready");
  for (int i = 0; i < 4; i++) { led(r, g, b); delay(250); led(0, 0, 0); delay(250); }
  led(r, g, b);
  displayShow("CALIBRATION", what, "hold still...");
}

static void runCalibration() {
  float flex[5], hall[4], gyro[3];
  countdown("OPEN HAND", 0, 0, 40);          // fingers straight, magnets away, hand still
  averageChannels(3000, flex, hall, gyro);
  for (int i = 0; i < 5; i++) cal.flexStraight[i] = flex[i];
  for (int i = 0; i < 4; i++) cal.hallBase[i] = hall[i];
  for (int i = 0; i < 3; i++) cal.gyroBias[i] = gyro[i];

  countdown("MAKE A FIST", 40, 25, 0);
  averageChannels(3000, flex, hall, gyro);
  bool ok = true;
  for (int i = 0; i < 5; i++) {
    cal.flexBent[i] = flex[i];
    float span = cal.flexBent[i] - cal.flexStraight[i];
    Serial.printf("[cal] flex %d: straight %.0f mV, bent %.0f mV, span %.0f mV\n", i + 1, cal.flexStraight[i], cal.flexBent[i], span);
    if (fabsf(span) < 150) { ok = false; Serial.printf("[cal]   ! flex %d barely changes - check wiring / divider\n", i + 1); }
  }
  for (int i = 0; i < 4; i++) Serial.printf("[cal] hall %d baseline %.0f mV\n", i + 1, cal.hallBase[i]);
  calSave();
  win.clear();
  displayShow("CALIBRATION", ok ? "DONE" : "CHECK FLEX", ok ? "saved" : "see serial log");
  led(0, 40, 0); delay(600);
  ledIdle();
}

// ------------------------------------------------------------------ speaking
static void speak(int k, float p) {
  Serial.printf("SAY,%s,%.2f\n", VM_LABELS[k], p);
  char foot[24];
  snprintf(foot, sizeof foot, "conf %d%%", (int)(p * 100));
  displayShow("VANITRA SAYS", VM_SAY[k], foot);
  led(0, 30, 30);
  voiceSay(VM_VOCAB_INDEX[k]);
  ledIdle();
  lastSpoken = k;
  lastSpokenMs = millis();
  restSinceLast = false;
  cooldownUntil = millis() + SPEAK_COOLDOWN_MS;
  candidate = -1; candidateCount = 0;
  win.clear();             // the speaking time is not part of the next gesture
}

// Confidence gate + stability (hysteresis) so the voice never flickers between words.
static void onPrediction(int k, float p) {
  if (printPred) Serial.printf("P,%s,%.2f\n", VM_LABELS[k], p);
  if (k == VM_REST_INDEX) { restSinceLast = true; candidate = -1; candidateCount = 0; return; }
  if (p < CONF_THRESHOLD || millis() < cooldownUntil) { candidateCount = 0; return; }
  if (k == candidate) candidateCount++;
  else { candidate = k; candidateCount = 1; }
  if (candidateCount < STABLE_COUNT) return;
  bool repeat = (k == lastSpoken) && !restSinceLast && (millis() - lastSpokenMs < REPEAT_GAP_MS);
  if (!repeat) speak(k, p);
}

// ------------------------------------------------------------------ serial commands
static void printHelp() {
  Serial.println(F("Vanitra glove — commands: h help | c calibrate | s stream on | x stream off | "
                   "p predictions on/off | i info"));
}

static void printInfo() {
  Serial.printf("[info] model: %d inputs, %d hidden, %d classes (%s)\n", VM_N_IN, VM_N_HID, VM_N_OUT, VM_INFO);
  Serial.printf("[info] IMU %s, calibration %s, battery %.2f V\n", imuOk ? "ok" : "MISSING", cal.valid ? "saved" : "DEFAULT", batteryVolts());
  for (int i = 0; i < 5; i++) Serial.printf("[info] flex %d straight %.0f bent %.0f mV\n", i + 1, cal.flexStraight[i], cal.flexBent[i]);
  for (int i = 0; i < 4; i++) Serial.printf("[info] hall %d base %.0f mV\n", i + 1, cal.hallBase[i]);
}

static void handleSerial() {
  if (!Serial.available()) return;
  char c = Serial.read();
  switch (c) {
    case 'h': printHelp(); break;
    case 'c': runCalibration(); break;
    case 's': streaming = true; Serial.println("[stream] on"); ledIdle(); break;
    case 'x': streaming = false; Serial.println("[stream] off"); ledIdle(); break;
    case 'p': printPred = !printPred; break;
    case 'i': printInfo(); break;
    default: break;
  }
}

// ------------------------------------------------------------------ BOOT button
static void handleButton() {
  static uint32_t downAt = 0;
  static bool wasDown = false, longDone = false;
  bool down = digitalRead(BUTTON_PIN) == LOW;
  if (down && !wasDown) { downAt = millis(); longDone = false; }
  if (down && !longDone && millis() - downAt > 2000) { longDone = true; runCalibration(); }
  if (!down && wasDown && !longDone && millis() - downAt > 40) {
    if (lastSpoken >= 0) speak(lastSpoken, 1.0f);    // repeat last word
  }
  wasDown = down;
}

// ------------------------------------------------------------------ setup / loop
void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  sensorsBegin();
  displayBegin();
  voiceBegin();
  led(0, 0, 30);
  Serial.printf("\nVANITRA glove ready. IMU: %s. Calibration: %s.\n", imuOk ? "ok" : "MISSING", cal.valid ? "loaded" : "not done (hold BOOT 2 s)");
  printHelp();
  displayShow("VANITRA", "READY", cal.valid ? "glove unit" : "hold BOOT: calibrate");
  voiceBeep(660, 80); voiceBeep(990, 80);
  ledIdle();
  nextFrameUs = micros();
}

void loop() {
  handleSerial();
  handleButton();

  if ((int32_t)(micros() - nextFrameUs) < 0) return;
  if (micros() - nextFrameUs > 100000UL) nextFrameUs = micros();   // resync after speaking
  nextFrameUs += 1000000UL / SAMPLE_HZ;

  vf::Sample s;
  readFrame(s);
  win.push(s);
  frameNo++;

  if (streaming) {
    Serial.printf("D,%lu", (unsigned long)millis());
    for (int i = 0; i < 5; i++) Serial.printf(",%.3f", s.flex[i]);
    for (int i = 0; i < 4; i++) Serial.printf(",%.0f", s.hall[i]);
    Serial.printf(",%.3f,%.3f,%.3f,%.1f,%.1f,%.1f\n", s.ax, s.ay, s.az, s.gx, s.gy, s.gz);
  }

  if (win.full() && frameNo % CLASSIFY_EVERY == 0) {
    float f[vf::N_FEAT], probs[VM_N_OUT];
    vf::computeFeatures(win, f);
    int k = vf::mlpPredict(f, probs);
    if (!streaming) onPrediction(k, probs[k]);
  }
}
