// Vanitra — tiny neural network (one hidden layer, ReLU, softmax) for gesture classification.
// Weights live in model.h, written by ml/train.py. Pure C++ so it is unit-tested on a PC.
#pragma once
#include <math.h>
#include "model.h"

namespace vf {

// x: VM_N_IN raw features. probs: VM_N_OUT outputs. Returns the most likely class index.
inline int mlpPredict(const float *x, float *probs) {
  float z[VM_N_IN];
  for (int i = 0; i < VM_N_IN; i++) z[i] = (x[i] - VM_MEAN[i]) / VM_STD[i];

  float h[VM_N_HID];
  for (int j = 0; j < VM_N_HID; j++) {
    float acc = VM_B1[j];
    for (int i = 0; i < VM_N_IN; i++) acc += z[i] * VM_W1[i * VM_N_HID + j];
    h[j] = acc > 0.f ? acc : 0.f;
  }

  float maxv = -1e30f;
  for (int k = 0; k < VM_N_OUT; k++) {
    float acc = VM_B2[k];
    for (int j = 0; j < VM_N_HID; j++) acc += h[j] * VM_W2[j * VM_N_OUT + k];
    probs[k] = acc;
    if (acc > maxv) maxv = acc;
  }
  float sum = 0.f;
  for (int k = 0; k < VM_N_OUT; k++) {
    probs[k] = expf(probs[k] - maxv);
    sum += probs[k];
  }
  int best = 0;
  for (int k = 0; k < VM_N_OUT; k++) {
    probs[k] /= sum;
    if (probs[k] > probs[best]) best = k;
  }
  return best;
}

}  // namespace vf
