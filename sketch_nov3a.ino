#define SPEAKER_PIN D7  // Speaker connected here

void setup() {
  Serial.begin(9600);

  pinMode(D1, OUTPUT);  // CALL_NURSE
  pinMode(D2, OUTPUT);  // NEED_WATER
  pinMode(D3, OUTPUT);  // PAIN
  pinMode(D8, OUTPUT);  // WASHROOM
  pinMode(D5, OUTPUT);  // EMERGENCY
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(SPEAKER_PIN, OUTPUT);

  // Turn all LEDs OFF initially
  digitalWrite(D1, LOW);
  digitalWrite(D2, LOW);
  digitalWrite(D3, LOW);
  digitalWrite(D8, LOW);
  digitalWrite(D5, LOW);
}

void loop() {
  digitalWrite(LED_BUILTIN, HIGH);

  if (Serial.available() > 0) {
    String gesture = Serial.readStringUntil('\n');
    gesture.trim();

    // Turn off all LEDs first
    digitalWrite(D1, LOW);
    digitalWrite(D2, LOW);
    digitalWrite(D3, LOW);
    digitalWrite(D8, LOW);
    digitalWrite(D5, LOW);

    // ====== Handle Gestures ======
    if (gesture == "CALL_NURSE") {
      digitalWrite(D1, HIGH);
      playTune1();
    }
    else if (gesture == "NEED_WATER") {
      digitalWrite(D2, HIGH);
      playTune2();
    }
    else if (gesture == "PAIN") {
      digitalWrite(D3, HIGH);
      playTune3();
    }
    else if (gesture == "WASHROOM") {
      digitalWrite(D8, HIGH);
      playTune4();
    }
    else if (gesture == "EMERGENCY") {
      digitalWrite(D5, HIGH);
      playTune5();
    }
    else {
      // Unknown gesture → turn everything off
      digitalWrite(D1, LOW);
      digitalWrite(D2, LOW);
      digitalWrite(D3, LOW);
      digitalWrite(D8, LOW);
      digitalWrite(D5, LOW);
    }
  }
  else {
    // No serial data → keep LEDs off
    digitalWrite(D1, LOW);
    digitalWrite(D2, LOW);
    digitalWrite(D3, LOW);
    digitalWrite(D8, LOW);
    digitalWrite(D5, LOW);
  }
}

// ==============================
//        MELODY FUNCTIONS
// ==============================

void playTone(int freq, int duration) {
  tone(SPEAKER_PIN, freq, duration);
  delay(duration * 1.2);
  noTone(SPEAKER_PIN);
}

// CALL_NURSE — calm rising tone
void playTune1() {
  int notes[] = {262, 294, 330, 349, 392};
  for (int i = 0; i < 5; i++) playTone(notes[i], 150);
}

// NEED_WATER — short double beep
void playTune2() {
  for (int i = 0; i < 2; i++) {
    playTone(523, 200);
    delay(100);
  }
}

// PAIN — fast alarm-like beeps
void playTune3() {
  for (int i = 0; i < 5; i++) {
    playTone(700, 100);
    delay(80);
  }
}

// WASHROOM — gentle descending tone
void playTune4() {
  int notes[] = {784, 698, 622, 587, 523};
  for (int i = 0; i < 5; i++) playTone(notes[i], 180);
}

// EMERGENCY — loud repeating siren pattern
void playTune5() {
  for (int i = 0; i < 3; i++) {
    playTone(900, 300);
    playTone(600, 300);
  }
}
