// Vanitra — text -> Morse vibration timeline. Pure C++ (no Arduino) so it is unit-tested on a PC.
// Standard Morse timing in "units": dot 1, dash 3, gap inside a letter 1, between letters 3, words 7.
#pragma once
#include <ctype.h>
#include <stdint.h>
#include <string.h>

namespace morse {

struct Step { bool on; uint16_t ms; };
constexpr int MAX_STEPS = 400;

struct Timeline {
  Step steps[MAX_STEPS];
  int n = 0;
  uint32_t totalMs() const { uint32_t t = 0; for (int i = 0; i < n; i++) t += steps[i].ms; return t; }
  void add(bool on, uint16_t ms) {
    if (n > 0 && steps[n - 1].on == on) { steps[n - 1].ms += ms; return; }   // merge gaps
    if (n < MAX_STEPS) steps[n++] = {on, ms};
  }
};

inline const char *code(char c) {
  static const char *L[26] = {".-", "-...", "-.-.", "-..", ".", "..-.", "--.", "....", "..", ".---", "-.-", ".-..", "--",
                              "-.", "---", ".--.", "--.-", ".-.", "...", "-", "..-", "...-", ".--", "-..-", "-.--", "--.."};
  static const char *D[10] = {"-----", ".----", "..---", "...--", "....-", ".....", "-....", "--...", "---..", "----."};
  c = toupper((unsigned char)c);
  if (c >= 'A' && c <= 'Z') return L[c - 'A'];
  if (c >= '0' && c <= '9') return D[c - '0'];
  switch (c) {
    case '?': return "..--..";
    case '.': return ".-.-.-";
    case ',': return "--..--";
    case '!': return "-.-.--";
    case '/': return "-..-.";
    default: return nullptr;   // unsupported characters are skipped
  }
}

// Danger pattern: three long buzzes, clearly different from any letter.
inline void buildAlert(Timeline &t, uint16_t unit) {
  for (int i = 0; i < 3; i++) { t.add(true, unit * 6); t.add(false, unit * 2); }
}

// Builds the vibration timeline for `text`. unit = dot length in ms (80-160 is comfortable).
// "*ALERT" -> danger pattern. Always ends with the motor off.
inline void build(const char *text, uint16_t unit, Timeline &t) {
  t.n = 0;
  if (strcmp(text, "*ALERT") == 0) { buildAlert(t, unit); return; }
  bool needLetterGap = false, pendingWord = false;
  for (const char *p = text; *p; p++) {
    if (*p == ' ') { pendingWord = needLetterGap; continue; }
    const char *c = code(*p);
    if (!c) continue;
    if (pendingWord) t.add(false, unit * 7);
    else if (needLetterGap) t.add(false, unit * 3);
    pendingWord = false;
    for (const char *s = c; *s; s++) {
      if (s != c) t.add(false, unit);
      t.add(true, *s == '.' ? unit : unit * 3);
    }
    needLetterGap = true;
  }
  if (t.n > 0) t.add(false, unit * 3);
}

}  // namespace morse
