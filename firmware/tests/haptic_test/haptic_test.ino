// Vibration motor check: S-O-S in Morse forever, at the wristband's normal speed (120 ms dot).
// Wiring: GPIO4 -> MOSFET gate (100 ohm), 100k gate->GND, motor between 3V3 and drain, diode across motor.
#define HAPTIC_PIN 4
#define UNIT 120

void buzz(int units) { ledcWrite(HAPTIC_PIN, 230); delay(units * UNIT); ledcWrite(HAPTIC_PIN, 0); delay(UNIT); }

void setup() {
  Serial.begin(115200);
  ledcAttach(HAPTIC_PIN, 5000, 8);
}

void loop() {
  Serial.println("... --- ...");
  for (int i = 0; i < 3; i++) buzz(1);
  delay(2 * UNIT);
  for (int i = 0; i < 3; i++) buzz(3);
  delay(2 * UNIT);
  for (int i = 0; i < 3; i++) buzz(1);
  delay(3000);
}
