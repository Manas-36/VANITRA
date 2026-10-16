// PC test for the wristband Morse timeline.
#include <cstdio>
#include <cstring>
#include "../../wristband_unit/morse.h"

static int fails = 0;
static void expect(bool c, const char *what) { if (!c) { printf("FAIL: %s\n", what); fails++; } }

// Turns a timeline back into dots/dashes/gaps so it can be compared with a string.
static void render(const morse::Timeline &t, uint16_t u, char *out) {
  out[0] = 0;
  for (int i = 0; i < t.n; i++) {
    int units = t.steps[i].ms / u;
    if (t.steps[i].on) strcat(out, units == 1 ? "." : units == 3 ? "-" : "#");
    else strcat(out, units == 1 ? "" : units == 3 ? " " : units == 7 ? " / " : "?");
  }
}

int main() {
  morse::Timeline t;
  char s[512];
  const uint16_t u = 100;
  morse::build("SOS", u, t);  render(t, u, s); expect(!strcmp(s, "... --- ... "), "SOS");
  // total = 3 dots(3) + 2 gaps(2) + letter gap 3 + 3 dashes (9) + 2 gaps + 3 + 3 dots + 2 gaps + final 3 = 30 units
  expect(t.totalMs() == 30 * u, "SOS duration");
  morse::build("HI YOU", u, t); render(t, u, s); expect(!strcmp(s, ".... .. / -.-- --- ..- "), "word gap");
  morse::build("ok?", u, t);  render(t, u, s); expect(!strcmp(s, "--- -.- ..--.. "), "lower case + ?");
  morse::build("A@B", u, t);  render(t, u, s); expect(!strcmp(s, ".- -... "), "unknown char skipped");
  morse::build("", u, t);     expect(t.n == 0, "empty text");
  morse::build("*ALERT", u, t); expect(t.n == 6 && t.steps[0].on && t.steps[0].ms == 600, "alert pattern");
  morse::build("HI", u, t);   expect(!t.steps[t.n - 1].on, "ends with motor off");
  printf("%s\n", fails ? "MORSE TESTS FAILED" : "morse tests passed");
  return fails ? 1 : 0;
}
