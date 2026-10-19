// Vanitra — glove-to-glove radio link (ESP-NOW: direct, no router, a few ms latency).
// The LEFT glove sends every calibrated sensor frame (50 Hz). The RIGHT glove keeps the newest one and
// feeds both hands to the model. If no left frame arrived for LINK_MAX_AGE_MS, the left hand counts as
// missing (zeros) and the model falls back to one-handed recognition (it is trained for that).
#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <string.h>
#include "config.h"
#include "features.h"

namespace glink {

constexpr uint16_t MAGIC = 0x4E56;   // "VN"

struct __attribute__((packed)) Packet {
  uint16_t magic;
  uint16_t pair;       // LINK_PAIR_ID: only gloves with the same id listen to each other
  uint16_t seq;
  int16_t v[15];       // flex x10000, hall 0/1, accel x1000 (g), gyro x10 (deg/s)
};
static_assert(sizeof(Packet) == 36, "packet layout");

static const uint8_t BROADCAST[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
static Packet rx;
static volatile uint32_t rxMs = 0, rxCount = 0, rxLost = 0;
static uint16_t txSeq = 0, rxLastSeq = 0;
static bool started = false;

static inline int16_t q(float x, float k) {
  float v = x * k;
  return (int16_t)(v > 32767.f ? 32767 : (v < -32768.f ? -32768 : lroundf(v)));
}

inline void pack(const vf::Sample &s, Packet &p) {
  for (int i = 0; i < 5; i++) p.v[i] = q(s.flex[i], 10000.f);
  for (int i = 0; i < 4; i++) p.v[5 + i] = s.hall[i] > 0.5f ? 1 : 0;
  p.v[9] = q(s.ax, 1000.f); p.v[10] = q(s.ay, 1000.f); p.v[11] = q(s.az, 1000.f);
  p.v[12] = q(s.gx, 10.f);  p.v[13] = q(s.gy, 10.f);  p.v[14] = q(s.gz, 10.f);
}

inline void unpack(const Packet &p, vf::Sample &s) {
  for (int i = 0; i < 5; i++) s.flex[i] = p.v[i] / 10000.f;
  for (int i = 0; i < 4; i++) s.hall[i] = (float)p.v[5 + i];
  s.ax = p.v[9] / 1000.f; s.ay = p.v[10] / 1000.f; s.az = p.v[11] / 1000.f;
  s.gx = p.v[12] / 10.f;  s.gy = p.v[13] / 10.f;  s.gz = p.v[14] / 10.f;
}

static void onRecv(const esp_now_recv_info_t *, const uint8_t *data, int len) {
  if (len != (int)sizeof(Packet)) return;
  Packet p;
  memcpy(&p, data, sizeof p);
  if (p.magic != MAGIC || p.pair != LINK_PAIR_ID) return;
  portENTER_CRITICAL(&mux);
  if (rxCount) rxLost += (uint16_t)(p.seq - rxLastSeq - 1);
  rxLastSeq = p.seq;
  rx = p;
  rxMs = millis();
  rxCount++;
  portEXIT_CRITICAL(&mux);
}

// sender = LEFT glove. Both gloves must use the same LINK_CHANNEL.
inline bool begin(bool sender) {
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_channel(LINK_CHANNEL, WIFI_SECOND_CHAN_NONE);
  if (esp_now_init() != ESP_OK) return false;
  if (sender) {
    esp_now_peer_info_t peer = {};
    memcpy(peer.peer_addr, BROADCAST, 6);
    peer.channel = LINK_CHANNEL;
    peer.encrypt = false;
    if (esp_now_add_peer(&peer) != ESP_OK) return false;
  } else {
    esp_now_register_recv_cb(onRecv);
  }
  started = true;
  return true;
}

inline void send(const vf::Sample &s) {
  if (!started) return;
  Packet p;
  p.magic = MAGIC;
  p.pair = LINK_PAIR_ID;
  p.seq = txSeq++;
  pack(s, p);
  esp_now_send(BROADCAST, (const uint8_t *)&p, sizeof p);
}

// Newest left-glove frame, if it is younger than LINK_MAX_AGE_MS.
inline bool latest(vf::Sample &s) {
  Packet p;
  uint32_t t;
  portENTER_CRITICAL(&mux);
  p = rx;
  t = rxMs;
  bool any = rxCount > 0;
  portEXIT_CRITICAL(&mux);
  if (!any || millis() - t > LINK_MAX_AGE_MS) return false;
  unpack(p, s);
  return true;
}

inline void stats(uint32_t &received, uint32_t &lost, uint32_t &ageMs) {
  portENTER_CRITICAL(&mux);
  received = rxCount;
  lost = rxLost;
  ageMs = rxCount ? millis() - rxMs : 0xFFFFFFFF;
  portEXIT_CRITICAL(&mux);
}

}  // namespace glink
