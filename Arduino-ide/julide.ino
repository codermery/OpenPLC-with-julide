/*
  JULIDE ROBOT - ESP8266 + L298N + HC-SR04 + WiFi PLC Gate Communication

  Sabit hız: 350
  Kullanıcı komutları:
  - ileri / f
  - geri / b
  - sol / l
  - sag / r
  - dur / s

  Kapı akışı:
  1. Robot ileri gider.
  2. Kapıya / engele 5 cm kala durur.
  3. PLC kapı kontrol ESP'sine istek gönderir.
  4. GUI'den geçiş izni bekler.
  5. İzin gelince kapıdan geçer.
  6. PLC'ye "geçtim" bildirir.
  7. Robot durur.
*/

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

// ================= WIFI / PLC AYARLARI =================

// Kapı kontrol ESP'sinin açtığı WiFi ağı
const char* PLC_WIFI_SSID = "PLC_GATE_CTRL";
const char* PLC_WIFI_PASS = "12345678";

// Kapı kontrol ESP'sinin IP adresi
const char* PLC_BASE_URL = "http://192.168.4.1";

// Robot ID
const char* ROBOT_ID = "julide";

// Kapı geçiş davranışı
bool gateModeEnabled = true;

// Kapıdan geçtikten sonra robot dursun mu?
bool STOP_AFTER_GATE_PASS = true;

// Kapıdan geçiş için ileri sürme süresi
unsigned long GATE_PASS_DRIVE_MS = 3000;

// PLC status sorgulama aralığı
unsigned long PLC_POLL_INTERVAL_MS = 500;

// WiFi tekrar bağlanma kontrolü
unsigned long lastWifiCheck = 0;
unsigned long WIFI_CHECK_INTERVAL_MS = 3000;

// ================= MOTOR PINLERI =================

// Yön pinleri
const int IN1 = 5;    // D1 - GPIO5  - Sol motor yön 1
const int IN2 = 4;    // D2 - GPIO4  - Sol motor yön 2
const int IN3 = 14;   // D5 - GPIO14 - Sağ motor yön 1
const int IN4 = 12;   // D6 - GPIO12 - Sağ motor yön 2

// Hız pinleri
const int ENA = 13;   // D7 - GPIO13 - Sol hız PWM
const int ENB = 15;   // D8 - GPIO15 - Sağ hız PWM

// ================= MESAFE SENSORU =================

const int TRIG_PIN = 0;    // D3 - GPIO0
const int ECHO_PIN = 16;   // D0 - GPIO16

float stopDistanceCm = 5.0;    // 5 cm kala dur / kapı isteği gönder
float slowDistanceCm = 10.0;   // 10 cm kala yavaşla

unsigned long lastDistanceCheck = 0;
unsigned long distanceCheckInterval = 100;

// ================= MOTOR AYARLARI =================

bool LEFT_INVERT  = false;
bool RIGHT_INVERT = false;

// SABİT HIZLAR
const int motorSpeed = 350;
const int slowSpeed  = 220;

const int startBoost = 430;
const int boostTime  = 80;

// ================= HAREKET DURUMU =================

enum MotionState {
  STOPPED,
  FORWARD,
  BACKWARD,
  TURN_LEFT,
  TURN_RIGHT
};

MotionState currentMotion = STOPPED;

// ================= KAPI PLC DURUMU =================

enum GateWorkflowState {
  GATE_IDLE,
  GATE_WAITING_PERMISSION,
  GATE_PASSING
};

GateWorkflowState gateState = GATE_IDLE;

unsigned long lastPlcPoll = 0;
unsigned long gatePassStartMs = 0;
unsigned long ignoreDistanceSafetyUntil = 0;

WiFiClient wifiClient;

// ================= SETUP =================

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  pinMode(ENA, OUTPUT);
  pinMode(ENB, OUTPUT);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  digitalWrite(TRIG_PIN, LOW);

  analogWriteRange(1023);
  analogWriteFreq(1000);

  stopMotors();

  Serial.println();
  Serial.println("JULIDE ROBOT - Sabit Hiz + OpenPLC Kapi Uyumlu");
  Serial.println("----------------------------------------------");

  connectToPlcWiFi();

  Serial.println("Komutlar:");
  Serial.println("ileri / f  -> ileri git");
  Serial.println("geri  / b  -> geri git");
  Serial.println("sol   / l  -> sola don");
  Serial.println("sag   / r  -> saga don");
  Serial.println("dur   / s  -> dur");
  Serial.println("----------------------------------------------");

  printSettings();
}

// ================= LOOP =================

void loop() {
  readSerialCommand();

  maintainWiFi();

  processGateWorkflow();

  distanceSafetyControl();
}

// ================= WIFI =================

void connectToPlcWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(PLC_WIFI_SSID, PLC_WIFI_PASS);

  Serial.print("[WiFi] PLC agina baglaniyor: ");
  Serial.println(PLC_WIFI_SSID);

  unsigned long startAttempt = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 15000) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("[WiFi] Baglandi.");
    Serial.print("[WiFi] Robot IP: ");
    Serial.println(WiFi.localIP());

    Serial.print("[WiFi] Robot MAC: ");
    Serial.println(WiFi.macAddress());
  } else {
    Serial.println("[WiFi] Baglanamadi. Robot seri komutla yine calisir.");
  }
}

void maintainWiFi() {
  if (millis() - lastWifiCheck < WIFI_CHECK_INTERVAL_MS) {
    return;
  }

  lastWifiCheck = millis();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Kopuk. Tekrar baglaniliyor...");
    WiFi.disconnect();
    WiFi.begin(PLC_WIFI_SSID, PLC_WIFI_PASS);
  }
}

// ================= HTTP / PLC =================

int plcGet(String path, String &payload) {
  payload = "";

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[PLC] WiFi bagli degil.");
    return -1;
  }

  HTTPClient http;

  String url = String(PLC_BASE_URL) + path;

  http.begin(wifiClient, url);
  http.setTimeout(2000);

  int httpCode = http.GET();

  if (httpCode > 0) {
    payload = http.getString();
  } else {
    Serial.print("[PLC] HTTP hata: ");
    Serial.println(httpCode);
  }

  http.end();

  return httpCode;
}

bool plcRequestGate() {
  String payload;

  String path = "/robot/request?id=" + String(ROBOT_ID);

  Serial.print("[PLC] Kapi istegi gonderiliyor: ");
  Serial.println(path);

  int code = plcGet(path, payload);

  Serial.print("[PLC] HTTP code: ");
  Serial.println(code);
  Serial.print("[PLC] Response: ");
  Serial.println(payload);

  return code == 200;
}

bool plcNotifyPassed() {
  String payload;

  String path = "/robot/passed?id=" + String(ROBOT_ID);

  Serial.print("[PLC] Robot gecti bildirimi: ");
  Serial.println(path);

  int code = plcGet(path, payload);

  Serial.print("[PLC] HTTP code: ");
  Serial.println(code);
  Serial.print("[PLC] Response: ");
  Serial.println(payload);

  return code == 200;
}

bool plcReadStatus(bool &passAllowed, bool &emergency) {
  String payload;

  int code = plcGet("/status", payload);

  if (code != 200) {
    Serial.println("[PLC] Status okunamadi.");
    return false;
  }

  passAllowed = payload.indexOf("\"pass_allowed\":true") >= 0;
  emergency   = payload.indexOf("\"emergency\":true") >= 0;

  Serial.print("[PLC] Status: ");
  Serial.println(payload);

  return true;
}

// ================= KAPI AKISI =================

void beginGateRequest(float distance) {
  if (!gateModeEnabled) {
    stopMotors();
    Serial.println("[GATE] Gate mode kapali. Sadece durdu.");
    return;
  }

  if (gateState != GATE_IDLE) {
    return;
  }

  stopMotors();

  Serial.println();
  Serial.println("[GATE] Kapi bolgesine gelindi.");
  Serial.print("[GATE] Mesafe: ");
  Serial.print(distance);
  Serial.println(" cm");

  bool ok = plcRequestGate();

  if (ok) {
    gateState = GATE_WAITING_PERMISSION;
    lastPlcPoll = 0;

    Serial.println("[GATE] PLC'ye talep gonderildi. Gecis izni bekleniyor...");
  } else {
    Serial.println("[GATE] PLC'ye talep gonderilemedi. Robot durdu.");
  }
}

void processGateWorkflow() {
  if (gateState == GATE_IDLE) {
    return;
  }

  if (gateState == GATE_WAITING_PERMISSION) {
    if (millis() - lastPlcPoll < PLC_POLL_INTERVAL_MS) {
      return;
    }

    lastPlcPoll = millis();

    bool passAllowed = false;
    bool emergency = false;

    bool ok = plcReadStatus(passAllowed, emergency);

    if (!ok) {
      return;
    }

    if (emergency) {
      stopMotors();
      gateState = GATE_IDLE;
      Serial.println("[GATE] PLC acil durumda. Robot beklemeye alindi.");
      return;
    }

    if (passAllowed) {
      startGatePassing();
    }
  }

  else if (gateState == GATE_PASSING) {
    if (millis() - gatePassStartMs >= GATE_PASS_DRIVE_MS) {
      finishGatePassing();
    }
  }
}

void startGatePassing() {
  Serial.println("[GATE] Gecis izni geldi. Robot kapidan geciyor...");

  gateState = GATE_PASSING;
  gatePassStartMs = millis();

  // Kapıdan geçiş sırasında sensör bariyeri tekrar görüp durdurmasın diye
  // kısa süre mesafe güvenliği pas geçilir.
  ignoreDistanceSafetyUntil = millis() + GATE_PASS_DRIVE_MS + 1000;

  setLeftMotor(true);
  setRightMotor(true);

  currentMotion = FORWARD;
  applySpeedWithBoost();
}

void finishGatePassing() {
  Serial.println("[GATE] Kapidan gecis tamamlandi. PLC'ye bildiriliyor...");

  plcNotifyPassed();

  gateState = GATE_IDLE;

  if (STOP_AFTER_GATE_PASS) {
    stopMotors();
    Serial.println("[GATE] Demo modu: Robot kapidan sonra durdu.");
  } else {
    currentMotion = FORWARD;
    analogWrite(ENA, motorSpeed);
    analogWrite(ENB, motorSpeed);
    Serial.println("[GATE] Robot devam ediyor.");
  }
}

// ================= SERIAL KOMUTLAR =================

void readSerialCommand() {
  if (!Serial.available()) {
    return;
  }

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  cmd.toLowerCase();

  if (cmd == "f" || cmd == "ileri") {
    forward();
  }
  else if (cmd == "b" || cmd == "geri") {
    backward();
  }
  else if (cmd == "l" || cmd == "sol") {
    turnLeft();
  }
  else if (cmd == "r" || cmd == "sag" || cmd == "sağ") {
    turnRight();
  }
  else if (cmd == "s" || cmd == "dur") {
    stopMotors();
    gateState = GATE_IDLE;
    Serial.println("Durdu.");
  }
  else {
    Serial.println("Bilinmeyen komut.");
    Serial.println("Kullan: ileri, geri, sol, sag, dur");
  }
}

// ================= MESAFE KONTROL =================

void distanceSafetyControl() {
  if (millis() - lastDistanceCheck < distanceCheckInterval) {
    return;
  }

  lastDistanceCheck = millis();

  if (currentMotion != FORWARD) {
    return;
  }

  // Kapıdan geçiş sırasında sensör bariyeri tekrar görüp durdurmasın diye
  if (millis() < ignoreDistanceSafetyUntil) {
    return;
  }

  // PLC'den izin beklerken zaten duruyor
  if (gateState == GATE_WAITING_PERMISSION) {
    return;
  }

  float distance = readDistanceCm();

  if (distance <= 0) {
    return;
  }

  if (distance <= stopDistanceCm) {
    Serial.print("On engel / kapi algilandi. Mesafe: ");
    Serial.print(distance);
    Serial.println(" cm");

    beginGateRequest(distance);
  }
  else if (distance <= slowDistanceCm) {
    analogWrite(ENA, slowSpeed);
    analogWrite(ENB, slowSpeed);

    Serial.print("Engel yakin, yavasladi. Mesafe: ");
    Serial.print(distance);
    Serial.print(" cm | Hiz: ");
    Serial.println(slowSpeed);
  }
  else {
    analogWrite(ENA, motorSpeed);
    analogWrite(ENB, motorSpeed);
  }
}

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 25000);

  if (duration == 0) {
    return -1;
  }

  float distance = duration * 0.0343 / 2.0;
  return distance;
}

// ================= HIZ =================

void applySpeedWithBoost() {
  if (motorSpeed == 0) {
    analogWrite(ENA, 0);
    analogWrite(ENB, 0);
    return;
  }

  analogWrite(ENA, startBoost);
  analogWrite(ENB, startBoost);
  delay(boostTime);

  analogWrite(ENA, motorSpeed);
  analogWrite(ENB, motorSpeed);
}

void printSettings() {
  Serial.print("Sabit hiz: ");
  Serial.print(motorSpeed);
  Serial.println(" / 1023");

  Serial.print("Yavaslama hizi: ");
  Serial.print(slowSpeed);
  Serial.println(" / 1023");

  Serial.print("Boost: ");
  Serial.print(startBoost);
  Serial.print(" | Boost suresi: ");
  Serial.print(boostTime);
  Serial.println(" ms");

  Serial.print("Yavaslama mesafesi: ");
  Serial.print(slowDistanceCm);
  Serial.println(" cm");

  Serial.print("Durma / kapi algilama mesafesi: ");
  Serial.print(stopDistanceCm);
  Serial.println(" cm");

  Serial.print("Kapidan sonra dur: ");
  Serial.println(STOP_AFTER_GATE_PASS ? "EVET" : "HAYIR");

  Serial.print("Kapidan gecis suresi: ");
  Serial.print(GATE_PASS_DRIVE_MS);
  Serial.println(" ms");
}

// ================= MOTOR YON =================

void setLeftMotor(bool forwardDirection) {
  if (LEFT_INVERT) {
    forwardDirection = !forwardDirection;
  }

  if (forwardDirection) {
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
  } else {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
  }
}

void setRightMotor(bool forwardDirection) {
  if (RIGHT_INVERT) {
    forwardDirection = !forwardDirection;
  }

  if (forwardDirection) {
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);
  } else {
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, HIGH);
  }
}

// ================= HAREKET =================

void forward() {
  float distance = readDistanceCm();

  if (distance > 0 && distance <= stopDistanceCm) {
    Serial.print("Ileri gitmedi. Kapi / engel algilandi. Mesafe: ");
    Serial.print(distance);
    Serial.println(" cm");

    beginGateRequest(distance);
    return;
  }

  setLeftMotor(true);
  setRightMotor(true);

  currentMotion = FORWARD;
  applySpeedWithBoost();

  Serial.println("Ileri.");
}

void backward() {
  setLeftMotor(false);
  setRightMotor(false);

  currentMotion = BACKWARD;
  applySpeedWithBoost();

  Serial.println("Geri.");
}

void turnLeft() {
  setLeftMotor(false);
  setRightMotor(true);

  currentMotion = TURN_LEFT;
  applySpeedWithBoost();

  Serial.println("Sola don.");
}

void turnRight() {
  setLeftMotor(true);
  setRightMotor(false);

  currentMotion = TURN_RIGHT;
  applySpeedWithBoost();

  Serial.println("Saga don.");
}

void stopMotors() {
  currentMotion = STOPPED;

  analogWrite(ENA, 0);
  analogWrite(ENB, 0);

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}
