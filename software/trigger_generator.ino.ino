const int TRIGGER_PIN = 2;
const unsigned long PULSE_INTERVAL = 33333UL;
const unsigned int PULSE_WIDTH = 1000;
unsigned long lastPulseTime = 0;

void setup() {
  pinMode(TRIGGER_PIN, OUTPUT);
  digitalWrite(TRIGGER_PIN, LOW);
  Serial.begin(115200);
  Serial.println("Trigger generator started (30 Hz)");
}

void loop() {
  unsigned long now = micros();
  if (now - lastPulseTime >= PULSE_INTERVAL) {
    lastPulseTime = now;
    digitalWrite(TRIGGER_PIN, HIGH);
    delayMicroseconds(PULSE_WIDTH);
    digitalWrite(TRIGGER_PIN, LOW);
  }
}