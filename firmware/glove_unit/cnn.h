// Vanitra — temporal CNN (model v2) for gesture classification.
// Weights live in model_cnn.h, written by ml/train_cnn.py. Pure C++ (no Arduino, no TFLite), so it is
// unit-tested on a PC against the NumPy code (firmware/tests/host/test_cnn.cpp). Mirrors ml/vanitra_cnn.py:
//   standardise -> conv k5 (15->24) ReLU pool2 -> conv k5 (24->32) ReLU pool2 -> conv k3 (32->32) ReLU
//   -> [global mean | global max] -> dense -> softmax
// ~0.23 M multiply-adds per call; a few ms on the ESP32-S3 at 240 MHz. ~16 KB of static RAM.
#pragma once
#include <math.h>
#include "features.h"    // vf::Sample
#include "model_cnn.h"

namespace vc {

constexpr int L0 = VC_SEQ_LEN;
constexpr int L1 = VC_POOL1 ? L0 / 2 : L0;
constexpr int L2 = VC_POOL2 ? L1 / 2 : L1;
constexpr int L3 = VC_POOL3 ? L2 / 2 : L2;

// Ring buffer of the last L0 frames (1.0 s). at(0) = oldest.
struct SeqWindow {
  vf::Sample buf[L0];
  int head = 0, count = 0;
  void push(const vf::Sample &s) {
    buf[head] = s;
    head = (head + 1) % L0;
    if (count < L0) count++;
  }
  bool full() const { return count == L0; }
  const vf::Sample &at(int i) const { return buf[(head + i) % L0]; }
  void clear() { head = count = 0; }
};

// Channel order = ml/vanitra_cnn.py CHANNELS = the CSV columns streamed by the glove.
inline void sampleToChannels(const vf::Sample &s, float *o) {
  for (int i = 0; i < 5; i++) o[i] = s.flex[i];
  for (int i = 0; i < 4; i++) o[5 + i] = s.hall[i];
  o[9] = s.ax; o[10] = s.ay; o[11] = s.az;
  o[12] = s.gx; o[13] = s.gy; o[14] = s.gz;
}

// 'same' zero-padded 1D convolution + ReLU. in [L][Cin], out [L][Cout], W[(j*Cin + c)*Cout + o].
inline void convSameRelu(const float *in, int L, int Cin, const float *W, const float *b, int k, int Cout, float *out) {
  const int p = k / 2;
  float acc[64];
  for (int t = 0; t < L; t++) {
    for (int o = 0; o < Cout; o++) acc[o] = b[o];
    for (int j = 0; j < k; j++) {
      const int ti = t + j - p;
      if (ti < 0 || ti >= L) continue;
      const float *x = in + ti * Cin;
      for (int c = 0; c < Cin; c++) {
        const float xv = x[c];
        const float *w = W + (j * Cin + c) * Cout;
        for (int o = 0; o < Cout; o++) acc[o] += xv * w[o];
      }
    }
    float *y = out + t * Cout;
    for (int o = 0; o < Cout; o++) y[o] = acc[o] > 0.f ? acc[o] : 0.f;
  }
}

// Max-pool by 2 along time (an odd last step is dropped, like NumPy). In place is fine.
inline void pool2(const float *in, int L, int C, float *out) {
  for (int t = 0; t < L / 2; t++)
    for (int c = 0; c < C; c++) {
      const float a = in[(2 * t) * C + c], b2 = in[(2 * t + 1) * C + c];
      out[t * C + c] = a > b2 ? a : b2;
    }
}

// Runs the network on the window. probs: VC_N_OUT outputs. Returns the most likely class index.
inline int cnnPredict(const SeqWindow &w, float *probs) {
  static float a0[L0 * VC_N_CH];
  static float a1[L0 * VC_C1];
  static float a2[L1 * VC_C2];
  static float a3[L2 * VC_C3];
  static_assert(VC_C1 <= 64 && VC_C2 <= 64 && VC_C3 <= 64, "acc[] in convSameRelu holds 64 channels");

  for (int t = 0; t < L0; t++) {
    float ch[VC_N_CH];
    sampleToChannels(w.at(t), ch);
    for (int c = 0; c < VC_N_CH; c++) a0[t * VC_N_CH + c] = (ch[c] - VC_MEAN[c]) / VC_STD[c];
  }
  convSameRelu(a0, L0, VC_N_CH, VC_W1, VC_B1, VC_K1, VC_C1, a1);
  if (VC_POOL1) pool2(a1, L0, VC_C1, a1);
  convSameRelu(a1, L1, VC_C1, VC_W2, VC_B2, VC_K2, VC_C2, a2);
  if (VC_POOL2) pool2(a2, L1, VC_C2, a2);
  convSameRelu(a2, L2, VC_C2, VC_W3, VC_B3, VC_K3, VC_C3, a3);
  if (VC_POOL3) pool2(a3, L2, VC_C3, a3);

  float feat[2 * VC_C3];
  for (int c = 0; c < VC_C3; c++) {
    float s = 0.f, m = a3[c];
    for (int t = 0; t < L3; t++) {
      const float v = a3[t * VC_C3 + c];
      s += v;
      if (v > m) m = v;
    }
    feat[c] = s / L3;
    feat[VC_C3 + c] = m;
  }

  float maxv = -1e30f;
  for (int k = 0; k < VC_N_OUT; k++) {
    float acc = VC_BD[k];
    for (int i = 0; i < 2 * VC_C3; i++) acc += feat[i] * VC_WD[i * VC_N_OUT + k];
    probs[k] = acc;
    if (acc > maxv) maxv = acc;
  }
  float sum = 0.f;
  for (int k = 0; k < VC_N_OUT; k++) {
    probs[k] = expf(probs[k] - maxv);
    sum += probs[k];
  }
  int best = 0;
  for (int k = 0; k < VC_N_OUT; k++) {
    probs[k] /= sum;
    if (probs[k] > probs[best]) best = k;
  }
  return best;
}

}  // namespace vc
