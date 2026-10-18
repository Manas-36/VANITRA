// Vanitra glove — picks the gesture model at compile time (config.h: GESTURE_MODEL).
//   GESTURE_MODEL_CNN (default, v2): 1.0 s of raw frames -> temporal CNN (cnn.h + model_cnn.h)
//   GESTURE_MODEL_MLP (v1)         : 0.5 s -> 16 features -> MLP       (mlp.h + model.h)
// The rest of the sketch only uses the CLS_* names below, so both models drop in.
#pragma once
#include "config.h"
#include "features.h"

#if GESTURE_MODEL == GESTURE_MODEL_CNN
#include "cnn.h"
#define CLS_N_OUT        VC_N_OUT
#define CLS_REST_INDEX   VC_REST_INDEX
#define CLS_LABELS       VC_LABELS
#define CLS_SAY          VC_SAY
#define CLS_VOCAB_INDEX  VC_VOCAB_INDEX
#define CLS_INFO         VC_INFO
#define CLS_PLACEHOLDER  VC_PLACEHOLDER
#define CLS_NAME         "temporal CNN v2 (1.0 s window)"
static vc::SeqWindow clsWin;
static void clsPush(const vf::Sample &s) { clsWin.push(s); }
static void clsClear() { clsWin.clear(); }
static bool clsReady() { return clsWin.full(); }
static int clsPredict(float *probs) { return vc::cnnPredict(clsWin, probs); }
#else
#include "mlp.h"
#define CLS_N_OUT        VM_N_OUT
#define CLS_REST_INDEX   VM_REST_INDEX
#define CLS_LABELS       VM_LABELS
#define CLS_SAY          VM_SAY
#define CLS_VOCAB_INDEX  VM_VOCAB_INDEX
#define CLS_INFO         VM_INFO
#define CLS_PLACEHOLDER  VM_PLACEHOLDER
#define CLS_NAME         "feature MLP v1 (0.5 s window)"
static vf::Window clsWin;
static void clsPush(const vf::Sample &s) { clsWin.push(s); }
static void clsClear() { clsWin.clear(); }
static bool clsReady() { return clsWin.full(); }
static int clsPredict(float *probs) {
  float f[vf::N_FEAT];
  vf::computeFeatures(clsWin, f);
  return vf::mlpPredict(f, probs);
}
#endif
