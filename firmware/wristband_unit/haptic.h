// Vanitra wristband — non-blocking vibration player (coin ERM motor on a MOSFET, PWM drive).
#pragma once
#include <Arduino.h>
#include "config.h"
#include "morse.h"

static morse::Timeline hapTl;
static int hapIdx = -1;
static uint32_t hapStepEnd = 0;

static void motor(bool on) { ledcWrite(HAPTIC_PIN, on ? HAPTIC_DUTY : 0); }

static void hapticBegin() {
  ledcAttach(HAPTIC_PIN, HAPTIC_PWM_HZ, 8);
  motor(false);
}

static bool hapticBusy() { return hapIdx >= 0; }

static void hapticStart() {
  if (hapTl.n == 0) return;
  hapIdx = 0;
  motor(hapTl.steps[0].on);
  hapStepEnd = millis() + hapTl.steps[0].ms;
}

static void hapticPlayText(const char *text, uint16_t unit) {
  morse::build(text, unit, hapTl);
  hapticStart();
}

// Raw pattern helper: pulses of `onMs` separated by `offMs`.
static void hapticPulses(int count, uint16_t onMs, uint16_t offMs) {
  hapTl.n = 0;
  for (int i = 0; i < count; i++) { hapTl.add(true, onMs); hapTl.add(false, offMs); }
  hapticStart();
}

static void hapticStop() { hapIdx = -1; motor(false); }

// Call every loop(). Returns true while playing.
static bool hapticUpdate() {
  if (hapIdx < 0) return false;
  if ((int32_t)(millis() - hapStepEnd) < 0) return true;
  hapIdx++;
  if (hapIdx >= hapTl.n) { hapticStop(); return false; }
  motor(hapTl.steps[hapIdx].on);
  hapStepEnd += hapTl.steps[hapIdx].ms;
  return true;
}
