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
    float junk[VC_N_CH] = {0};
    for (int k = 0; k < 7; k++) w.push(junk);           // junk first: checks ring-buffer wrap-around
    for (int k = 0; k < vc::L0; k++) w.push(&TVC_FRAMES[(t * vc::L0 + k) * VC_N_CH]);
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
