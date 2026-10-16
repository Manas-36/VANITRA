// Vanitra glove — speech output. Pre-recorded WAV clips (voice_clips.h, made by
// ml/make_voice_clips.py) are played through a MAX98357A I2S amplifier. Fully offline.
#pragma once
#include <Arduino.h>
#include <ESP_I2S.h>
#include "config.h"
#include "voice_clips.h"

static I2SClass i2s;

static void voiceBegin() {
  pinMode(AMP_SD_PIN, OUTPUT);
  digitalWrite(AMP_SD_PIN, LOW);
  i2s.setPins(I2S_BCLK, I2S_LRC, I2S_DOUT);
  if (!i2s.begin(I2S_MODE_STD, VOICE_SAMPLE_RATE, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO)) {
    Serial.println("[voice] I2S init failed");
  }
}

// Short tone, used when a word has no clip (and at boot).
static void voiceBeep(int freq = 880, int ms = 120) {
  const int rate = VOICE_SAMPLE_RATE;
  static int16_t buf[256];
  digitalWrite(AMP_SD_PIN, HIGH);
  i2s.configureTX(rate, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO);
  long total = (long)rate * ms / 1000, done = 0;
  float ph = 0, step = 2.f * PI * freq / rate;
  while (done < total) {
    int n = min((long)256, total - done);
    for (int i = 0; i < n; i++) { buf[i] = (int16_t)(6000 * sinf(ph)); ph += step; }
    i2s.write((uint8_t *)buf, n * 2);
    done += n;
  }
  digitalWrite(AMP_SD_PIN, LOW);
}

// Blocks while the clip plays (typically 0.5 - 1.2 s).
static void voiceSay(int labelIndex) {
  if (labelIndex < 0 || labelIndex >= VOICE_N || VOICE_CLIPS[labelIndex].len == 0) {
    voiceBeep();
    return;
  }
  digitalWrite(AMP_SD_PIN, HIGH);
  delay(5);  // amp wake-up
  i2s.playWAV((uint8_t *)VOICE_CLIPS[labelIndex].data, VOICE_CLIPS[labelIndex].len);
  digitalWrite(AMP_SD_PIN, LOW);
}
