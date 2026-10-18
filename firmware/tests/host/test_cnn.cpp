// PC test: the firmware CNN (cnn.h) must match the NumPy training code (ml/vanitra_cnn.py).
// Build & run:  make -C firmware/tests/host
#include <cmath>
#include <cstdio>
#include "../../glove_unit/cnn.h"
#include "test_vectors_cnn.h"

int main() {
  int fails = 0;
  for (int t = 0; t < TVC_N; t++) {
    vc::SeqWindow w;
    for (int k = 0; k < 7; k++) w.push(vf::Sample{});   // junk first: checks ring-buffer wrap-around
    for (int k = 0; k < vc::L0; k++) {
      const float *r = &TVC_FRAMES[(t * vc::L0 + k) * VC_N_CH];
      vf::Sample s;
      for (int i = 0; i < 5; i++) s.flex[i] = r[i];
      for (int i = 0; i < 4; i++) s.hall[i] = r[5 + i];
      s.ax = r[9]; s.ay = r[10]; s.az = r[11]; s.gx = r[12]; s.gy = r[13]; s.gz = r[14];
      w.push(s);
    }
    float p[VC_N_OUT];
    int best = vc::cnnPredict(w, p);
    float err = 0;
    for (int k = 0; k < VC_N_OUT; k++) err = fmaxf(err, fabsf(p[k] - TVC_PROBS[t * VC_N_OUT + k]));
    bool ok = err < 1e-3f && best == TVC_BEST[t];
    printf("cnn vector %d: prob err %.2e, class %s (%s) %s\n", t, err, VC_LABELS[best],
           best == TVC_BEST[t] ? "match" : "MISMATCH", ok ? "OK" : "FAIL");
    fails += !ok;
  }
  printf("%s\n", fails ? "CNN TESTS FAILED" : "cnn tests passed");
  return fails ? 1 : 0;
}
