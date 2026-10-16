// PC test: the firmware feature code + neural net must match the Python training code exactly.
// Build & run:  make -C firmware/tests/host      (any g++ / clang++)
#include <cmath>
#include <cstdio>
#include "../../glove_unit/features.h"
#include "../../glove_unit/mlp.h"
#include "test_vectors.h"

int main() {
  int fails = 0;
  for (int t = 0; t < TV_N; t++) {
    vf::Window w;
    for (int k = 0; k < vf::WIN; k++) {
      const float *r = &TV_FRAMES[(t * vf::WIN + k) * 15];
      vf::Sample s;
      for (int i = 0; i < 5; i++) s.flex[i] = r[i];
      for (int i = 0; i < 4; i++) s.hall[i] = r[5 + i];
      s.ax = r[9]; s.ay = r[10]; s.az = r[11]; s.gx = r[12]; s.gy = r[13]; s.gz = r[14];
      w.push(s);
    }
    float f[vf::N_FEAT], p[VM_N_OUT];
    vf::computeFeatures(w, f);
    float maxErr = 0;
    for (int i = 0; i < vf::N_FEAT; i++) maxErr = fmaxf(maxErr, fabsf(f[i] - TV_FEATURES[t * vf::N_FEAT + i]));
    int best = vf::mlpPredict(f, p);
    float pErr = 0;
    for (int k = 0; k < VM_N_OUT; k++) pErr = fmaxf(pErr, fabsf(p[k] - TV_PROBS[t * VM_N_OUT + k]));
    bool ok = maxErr < 1e-3f && pErr < 1e-3f && best == TV_BEST[t];
    printf("vector %d: feature err %.2e, prob err %.2e, class %s (%s) %s\n", t, maxErr, pErr, VM_LABELS[best],
           best == TV_BEST[t] ? "match" : "MISMATCH", ok ? "OK" : "FAIL");
    fails += !ok;
  }
  // ring buffer order: oldest first after wrap-around
  vf::Window w;
  for (int k = 0; k < vf::WIN + 3; k++) { vf::Sample s{}; s.flex[0] = (float)k; w.push(s); }
  if (w.at(0).flex[0] != 3.f || w.at(vf::WIN - 1).flex[0] != (float)(vf::WIN + 2)) { puts("ring buffer FAIL"); fails++; }
  printf("%s\n", fails ? "GLOVE TESTS FAILED" : "glove tests passed");
  return fails ? 1 : 0;
}
