// Vanitra — feature extraction for one gesture window.
// Pure C++ (no Arduino), so it is unit-tested on a PC (firmware/tests/host) and mirrored
// line-for-line in ml/vanitra_features.py. Change both together, then retrain.
#pragma once
#include <math.h>

namespace vf {

constexpr int N_FLEX = 5;
constexpr int N_HALL = 4;
constexpr int WIN    = 25;   // 25 frames x 20 ms = 0.5 s window
constexpr int N_FEAT = 16;

// One sensor frame, already calibrated:
// flex 0 = straight .. 1 = fully bent, hall 0/1 = contact, accel in g, gyro in deg/s.
struct Sample {
  float flex[N_FLEX];
  float hall[N_HALL];
  float ax, ay, az;
  float gx, gy, gz;
};

inline float rollDeg(const Sample &s)  { return atan2f(s.ay, s.az) * 57.2957795f; }
inline float pitchDeg(const Sample &s) { return atan2f(-s.ax, sqrtf(s.ay * s.ay + s.az * s.az)) * 57.2957795f; }
inline float wrap180(float d) {
  while (d > 180.f) d -= 360.f;
  while (d < -180.f) d += 360.f;
  return d;
}

// Ring buffer of the last WIN frames. at(0) = oldest.
struct Window {
  Sample buf[WIN];
  int head = 0, count = 0;
  void push(const Sample &s) {
    buf[head] = s;
    head = (head + 1) % WIN;
    if (count < WIN) count++;
  }
  bool full() const { return count == WIN; }
  const Sample &at(int i) const { return buf[(head + i) % WIN]; }
  void clear() { head = count = 0; }
};

// Feature vector (N_FEAT):
//  0-4  mean flex per finger              5-8  fraction of window each Hall sensor is in contact
//  9    circular mean roll / 180          10   mean pitch / 90
//  11   roll change (last-first) / 180    12   pitch change / 90
//  13   mean |gyro| / 250                 14   max |gyro| / 250
//  15   std of |accel| (g)                -> static vs moving signs
inline void computeFeatures(const Window &w, float *f) {
  const int n = w.count;
  for (int i = 0; i < N_FEAT; i++) f[i] = 0.f;
  if (n == 0) return;

  float sinR = 0, cosR = 0, pitchSum = 0, gyroSum = 0, gyroMax = 0, aSum = 0, aSq = 0;
  for (int k = 0; k < n; k++) {
    const Sample &s = w.at(k);
    for (int i = 0; i < N_FLEX; i++) f[i] += s.flex[i];
    for (int i = 0; i < N_HALL; i++) f[N_FLEX + i] += s.hall[i];
    float r = rollDeg(s) / 57.2957795f;
    sinR += sinf(r);
    cosR += cosf(r);
    pitchSum += pitchDeg(s);
    float g = sqrtf(s.gx * s.gx + s.gy * s.gy + s.gz * s.gz);
    gyroSum += g;
    if (g > gyroMax) gyroMax = g;
    float a = sqrtf(s.ax * s.ax + s.ay * s.ay + s.az * s.az);
    aSum += a;
    aSq += a * a;
  }
  for (int i = 0; i < N_FLEX + N_HALL; i++) f[i] /= n;
  f[9]  = atan2f(sinR, cosR) * 57.2957795f / 180.f;
  f[10] = pitchSum / n / 90.f;
  f[11] = wrap180(rollDeg(w.at(n - 1)) - rollDeg(w.at(0))) / 180.f;
  f[12] = (pitchDeg(w.at(n - 1)) - pitchDeg(w.at(0))) / 90.f;
  f[13] = gyroSum / n / 250.f;
  f[14] = gyroMax / 250.f;
  float mean = aSum / n;
  float var = aSq / n - mean * mean;
  f[15] = var > 0 ? sqrtf(var) : 0.f;
}

}  // namespace vf
