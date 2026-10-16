// MAX98357A check: plays a rising 3-tone chime every 2 s.
// Wiring: BCLK 12, LRC 13, DIN 14, SD 21 (or SD to VIN), GAIN open (9 dB), VIN 5V, speaker + / -.
#include <ESP_I2S.h>
#define I2S_BCLK 12
#define I2S_LRC 13
#define I2S_DOUT 14
#define AMP_SD 21
I2SClass i2s;
int16_t buf[256];

void tone_(int f, int ms) {
  const int rate = 16000;
  long total = (long)rate * ms / 1000, done = 0;
  float ph = 0, step = 2 * PI * f / rate;
  while (done < total) {
    int n = min(256L, total - done);
    for (int i = 0; i < n; i++) { buf[i] = 8000 * sinf(ph); ph += step; }
    i2s.write((uint8_t *)buf, n * 2);
    done += n;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(AMP_SD, OUTPUT);
  digitalWrite(AMP_SD, HIGH);
  i2s.setPins(I2S_BCLK, I2S_LRC, I2S_DOUT);
  Serial.println(i2s.begin(I2S_MODE_STD, 16000, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO) ? "I2S ok" : "I2S FAILED");
}

void loop() {
  tone_(523, 200); tone_(659, 200); tone_(784, 300);
  Serial.println("chime");
  delay(2000);
}
