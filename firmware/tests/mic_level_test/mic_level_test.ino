// INMP441 check: prints a loudness bar. Talk / clap — the bar should jump; silence ~ near zero.
// Wiring: SCK 17, WS 47, SD 16, L/R -> GND, VDD 3V3, GND.
#include <ESP_I2S.h>
#define MIC_SCK 17
#define MIC_WS 47
#define MIC_SD 16
I2SClass i2s;
int16_t buf[512];

void setup() {
  Serial.begin(115200);
  i2s.setPins(MIC_SCK, MIC_WS, -1, MIC_SD);
  Serial.println(i2s.begin(I2S_MODE_STD, 16000, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO) ? "I2S ok" : "I2S FAILED");
}

void loop() {
  size_t n = i2s.readBytes((char *)buf, sizeof buf) / 2;
  double acc = 0;
  int used = 0;
  for (size_t i = 0; i < n; i += 2) { acc += (double)buf[i] * buf[i]; used++; }   // left channel
  int rms = used ? (int)sqrt(acc / used) : 0;
  int bars = constrain(rms / 150, 0, 60);
  Serial.printf("%5d |", rms);
  for (int i = 0; i < bars; i++) Serial.print('#');
  Serial.println();
  delay(50);
}
