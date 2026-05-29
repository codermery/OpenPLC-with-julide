/*
  JULIDE ROBOT - ESP8266 + L298N + HC-SR04
  OpenPLC Modbus TCP Client + Web Joystick Server

  Donanim:
  - ESP8266 NodeMCU / LoLin V3
  - L298N motor surucu
  - HC-SR04 mesafe sensoru

  Ag:
  - PC Windows hotspot: PLC_GATE_CTRL / 12345678
  - Kapi ESP OpenPLC IP: 192.168.137.218
  - OpenPLC Modbus TCP Port: 502
  - Unit ID: 0

  OpenPLC coil haritasi:
  - STATUS_PASS_ALLOWED : coil 6
  - STATUS_EMERGENCY    : coil 7
  - CMD_ROBOT_REQUEST   : coil 8
  - CMD_ROBOT_PASSED    : coil 10

  Web joystick:
  - http://<JULIDE_IP>/
  - /api/move?cmd=f/b/l/r/s
  - /api/status
  - /api/gate_mode?enabled=1/0
*/

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
// Raw Modbus TCP client kullaniliyor; ekstra Modbus kutuphanesi gerekmez.

// ================= WIFI / OPENPLC AYARLARI =================

const char* WIFI_SSID = "PLC_GATE_CTRL";
const char* WIFI_PASS = "12345678";

IPAddress PLC_IP(192, 168, 137, 218);
const uint16_t PLC_PORT = 502;
const uint8_t MODBUS_UNIT_ID = 0;

const char* ROBOT_ID = "julide";

// ================= OPENPLC MODBUS COIL HARITASI =================

const uint16_t COIL_Q_READY = 0;
const uint16_t COIL_Q_REQUEST = 1;
const uint16_t COIL_Q_PASS_ALLOWED = 2;
const uint16_t COIL_Q_EMERGENCY = 3;

const uint16_t COIL_STATUS_READY = 4;
const uint16_t COIL_STATUS_REQUEST = 5;
const uint16_t COIL_STATUS_PASS_ALLOWED = 6;
const uint16_t COIL_STATUS_EMERGENCY = 7;

const uint16_t COIL_CMD_ROBOT_REQUEST = 8;
const uint16_t COIL_CMD_HMI_ALLOW = 9;
const uint16_t COIL_CMD_ROBOT_PASSED = 10;
const uint16_t COIL_CMD_EMERGENCY = 11;
const uint16_t COIL_CMD_RESET = 12;

// ================= KAPI AKISI AYARLARI =================

bool gateModeEnabled = false;  // Guvenli baslangic: joystick testinde kapi otomasyonu kapali
bool STOP_AFTER_GATE_PASS = true;

unsigned long GATE_PASS_DRIVE_MS = 3000;
unsigned long PLC_POLL_INTERVAL_MS = 800;
unsigned long MODBUS_PULSE_MS = 200;

unsigned long lastWifiCheck = 0;
unsigned long WIFI_CHECK_INTERVAL_MS = 10000;

unsigned long lastModbusCheck = 0;
unsigned long MODBUS_CHECK_INTERVAL_MS = 30000;

unsigned long lastEmergencyMonitor = 0;
unsigned long EMERGENCY_MONITOR_INTERVAL_MS = 1500;

// ================= MOTOR PINLERI =================

const int IN1 = 5;    // D1 - GPIO5  - Sol motor yon 1
const int IN2 = 4;    // D2 - GPIO4  - Sol motor yon 2
const int IN3 = 14;   // D5 - GPIO14 - Sag motor yon 1
const int IN4 = 12;   // D6 - GPIO12 - Sag motor yon 2

const int ENA = 13;   // D7 - GPIO13 - Sol PWM
const int ENB = 15;   // D8 - GPIO15 - Sag PWM

// ================= MESAFE SENSORU =================

const int TRIG_PIN = 0;    // D3 - GPIO0
const int ECHO_PIN = 16;   // D0 - GPIO16

float stopDistanceCm = 5.0;
float slowDistanceCm = 10.0;

unsigned long lastDistanceCheck = 0;
unsigned long distanceCheckInterval = 100;
float lastDistanceCm = -1;

// Web joystick v6: eski davranis.
// Yon komutu robotu hareket ettirir, robot DUR komutu gelene kadar devam eder.
// Otomatik 700 ms durdurma KAPALI.
const bool MANUAL_AUTO_STOP_ENABLED = false;
const unsigned long MANUAL_COMMAND_TIMEOUT_MS = 0;
unsigned long manualMotionTimeoutAt = 0;

// ================= MOTOR AYARLARI =================

bool LEFT_INVERT  = false;
bool RIGHT_INVERT = false;

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

bool lastPlcConnected = false;
bool lastPassAllowed = false;
bool lastEmergency = false;

// ================= SERVER / MODBUS =================

ESP8266WebServer server(80);

uint16_t modbusTransactionId = 1;

// ================= FORWARD DECLARATIONS =================

void stopMotors();
void forward();
void backward();
void turnLeft();
void turnRight();
float readDistanceCm();
void processGateWorkflow();
void distanceSafetyControl();
void setupWebServer();
void sendJson(const String &json, int code = 200);
String boolToJson(bool value);
String ipToString(IPAddress ip);
bool doMoveCommand(const String &cmd);
void handleApiMove();
void handleApiStatus();
void handleApiGateMode();
void handleApiSettings();
void handleApiGateRequest();
void handleApiGatePassed();
void handleApiGateForcePass();
void startGatePassing();
void autoStopManualMotion();
void armManualMotionTimeout();
void clearManualMotionTimeout();

// ================= RAW MODBUS TCP =================

// ================= SETUP =================

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(30);
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
  Serial.println("JULIDE ROBOT - OpenPLC Raw Modbus + Stable Web Joystick v7");
  Serial.println("------------------------------------------------");

  connectToWiFi();

  maintainModbusConnection(true);

  setupWebServer();
  server.begin();

  Serial.println("[WEB] Joystick server basladi.");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[WEB] URL: http://");
    Serial.print(WiFi.localIP());
    Serial.println("/");
  }

  printSettings();
  printCommands();
}

// ================= LOOP =================

void loop() {
  readSerialCommand();
  maintainWiFi();
  // Web joystick'in donmaması için sürekli Modbus TCP test etmiyoruz.
  // PLC durumunu gate workflow veya /api/plc/status çağrıları okur.
  server.handleClient();

  processGateWorkflow();
  // v6: manuel joystick komutlari otomatik durdurulmaz; DUR butonu beklenir.
  distanceSafetyControl();
}

// ================= WIFI =================

void connectToWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleepMode(WIFI_NONE_SLEEP);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("[WiFi] Aga baglaniyor: ");
  Serial.println(WIFI_SSID);

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
  if (millis() - lastWifiCheck < WIFI_CHECK_INTERVAL_MS) return;
  lastWifiCheck = millis();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.print("[WiFi] Bagli degil. Status=");
    Serial.println(WiFi.status());
    lastPlcConnected = false;
    // Soft reconnect: disconnect zorlamadan ayni aga tekrar baglanmayi dene.
    WiFi.begin(WIFI_SSID, WIFI_PASS);
  }
}

// ================= RAW MODBUS TCP =================

bool readExact(WiFiClient &client, uint8_t *buffer, size_t length, unsigned long timeoutMs) {
  size_t received = 0;
  unsigned long start = millis();

  while (received < length && millis() - start < timeoutMs) {
    while (client.available() && received < length) {
      buffer[received++] = client.read();
    }
    delay(1);
    server.handleClient();
  }

  return received == length;
}

bool openModbusSocket(WiFiClient &client) {
  if (WiFi.status() != WL_CONNECTED) {
    lastPlcConnected = false;
    return false;
  }

  client.setTimeout(1500);
  client.setNoDelay(true);

  bool ok = client.connect(PLC_IP, PLC_PORT);
  lastPlcConnected = ok;

  return ok;
}

bool maintainModbusConnection(bool force) {
  if (WiFi.status() != WL_CONNECTED) {
    lastPlcConnected = false;
    return false;
  }

  if (!force && millis() - lastModbusCheck < MODBUS_CHECK_INTERVAL_MS) {
    return lastPlcConnected;
  }

  lastModbusCheck = millis();

  Serial.print("[MODBUS] OpenPLC TCP test: ");
  Serial.print(PLC_IP);
  Serial.print(":");
  Serial.println(PLC_PORT);

  WiFiClient testClient;
  bool ok = openModbusSocket(testClient);

  if (ok) {
    testClient.stop();
    lastPlcConnected = true;
    Serial.println("[MODBUS] TCP OK.");
  } else {
    lastPlcConnected = false;
    Serial.println("[MODBUS] TCP baglanamadi.");
  }

  return lastPlcConnected;
}

bool modbusWriteSingleCoil(uint16_t coilAddress, bool value) {
  WiFiClient client;

  if (!openModbusSocket(client)) {
    Serial.println("[MODBUS] Socket acilamadi.");
    return false;
  }

  uint16_t tx = modbusTransactionId++;
  uint16_t coilValue = value ? 0xFF00 : 0x0000;

  uint8_t req[12];
  req[0] = highByte(tx);
  req[1] = lowByte(tx);
  req[2] = 0x00;
  req[3] = 0x00;
  req[4] = 0x00;
  req[5] = 0x06;
  req[6] = MODBUS_UNIT_ID;
  req[7] = 0x05;  // Write Single Coil
  req[8] = highByte(coilAddress);
  req[9] = lowByte(coilAddress);
  req[10] = highByte(coilValue);
  req[11] = lowByte(coilValue);

  client.write(req, sizeof(req));
  client.flush();

  uint8_t header[7];
  if (!readExact(client, header, 7, 2500)) {
    Serial.println("[MODBUS] Write response header timeout.");
    client.stop();
    lastPlcConnected = false;
    return false;
  }

  uint16_t len = ((uint16_t)header[4] << 8) | header[5];
  if (len < 2 || len > 260) {
    Serial.println("[MODBUS] Write response length invalid.");
    client.stop();
    return false;
  }

  uint8_t pdu[260];
  size_t pduLen = len - 1;  // Unit ID header[6] olarak okundu, kalan PDU

  if (!readExact(client, pdu, pduLen, 2500)) {
    Serial.println("[MODBUS] Write response PDU timeout.");
    client.stop();
    lastPlcConnected = false;
    return false;
  }

  client.stop();

  if (pdu[0] == 0x85) {
    Serial.print("[MODBUS] Write exception code: ");
    Serial.println(pdu[1]);
    return false;
  }

  if (pdu[0] != 0x05) {
    Serial.print("[MODBUS] Unexpected write function: ");
    Serial.println(pdu[0], HEX);
    return false;
  }

  lastPlcConnected = true;
  return true;
}

bool modbusReadCoils(uint16_t startAddress, uint16_t count, bool *values) {
  if (count == 0 || count > 16) return false;

  WiFiClient client;

  if (!openModbusSocket(client)) {
    Serial.println("[MODBUS] Socket acilamadi.");
    return false;
  }

  uint16_t tx = modbusTransactionId++;

  uint8_t req[12];
  req[0] = highByte(tx);
  req[1] = lowByte(tx);
  req[2] = 0x00;
  req[3] = 0x00;
  req[4] = 0x00;
  req[5] = 0x06;
  req[6] = MODBUS_UNIT_ID;
  req[7] = 0x01;  // Read Coils
  req[8] = highByte(startAddress);
  req[9] = lowByte(startAddress);
  req[10] = highByte(count);
  req[11] = lowByte(count);

  client.write(req, sizeof(req));
  client.flush();

  uint8_t header[7];
  if (!readExact(client, header, 7, 2500)) {
    Serial.println("[MODBUS] Read response header timeout.");
    client.stop();
    lastPlcConnected = false;
    return false;
  }

  uint16_t len = ((uint16_t)header[4] << 8) | header[5];
  if (len < 3 || len > 260) {
    Serial.println("[MODBUS] Read response length invalid.");
    client.stop();
    return false;
  }

  uint8_t pdu[260];
  size_t pduLen = len - 1;

  if (!readExact(client, pdu, pduLen, 2500)) {
    Serial.println("[MODBUS] Read response PDU timeout.");
    client.stop();
    lastPlcConnected = false;
    return false;
  }

  client.stop();

  if (pdu[0] == 0x81) {
    Serial.print("[MODBUS] Read exception code: ");
    Serial.println(pdu[1]);
    return false;
  }

  if (pdu[0] != 0x01) {
    Serial.print("[MODBUS] Unexpected read function: ");
    Serial.println(pdu[0], HEX);
    return false;
  }

  uint8_t byteCount = pdu[1];
  if (byteCount < 1) return false;

  for (uint16_t i = 0; i < count; i++) {
    uint8_t b = pdu[2 + (i / 8)];
    values[i] = (b >> (i % 8)) & 0x01;
  }

  lastPlcConnected = true;
  return true;
}

bool plcWriteCoil(uint16_t coilAddress, bool value, const char* name) {
  bool ok = modbusWriteSingleCoil(coilAddress, value);

  Serial.print("[PLC] ");
  Serial.print(name);
  Serial.print(" coil ");
  Serial.print(coilAddress);
  Serial.print(" = ");
  Serial.print(value ? "TRUE" : "FALSE");
  Serial.print(" -> ");
  Serial.println(ok ? "OK" : "FAIL");

  return ok;
}

bool plcPulseCoil(uint16_t coilAddress, const char* name) {
  Serial.print("[PLC] Pulse: ");
  Serial.println(name);

  if (!plcWriteCoil(coilAddress, true, name)) return false;

  unsigned long start = millis();
  while (millis() - start < MODBUS_PULSE_MS) {
    server.handleClient();
    delay(1);
  }

  return plcWriteCoil(coilAddress, false, name);
}

bool plcReadStatus(bool &passAllowed, bool &emergency) {
  passAllowed = false;
  emergency = false;

  // Python testinde doğrulanan şekilde statusları blok halinde okuyoruz:
  // coil 4 READY, 5 REQUEST, 6 PASS_ALLOWED, 7 EMERGENCY.
  bool values[4] = {false, false, false, false};

  bool ok = false;
  for (int attempt = 1; attempt <= 3; attempt++) {
    ok = modbusReadCoils(COIL_STATUS_READY, 4, values);

    if (ok) {
      break;
    }

    Serial.print("[PLC] Status okuma denemesi basarisiz: ");
    Serial.println(attempt);
    delay(120);
    server.handleClient();
  }

  if (!ok) {
    Serial.println("[PLC] Status okuma basarisiz.");
    return false;
  }

  passAllowed = values[2];  // coil 6
  emergency = values[3];    // coil 7

  lastPassAllowed = passAllowed;
  lastEmergency = emergency;

  Serial.print("[PLC] STATUS_READY=");
  Serial.print(values[0] ? "TRUE" : "FALSE");
  Serial.print(" | STATUS_REQUEST=");
  Serial.print(values[1] ? "TRUE" : "FALSE");
  Serial.print(" | STATUS_PASS_ALLOWED=");
  Serial.print(passAllowed ? "TRUE" : "FALSE");
  Serial.print(" | STATUS_EMERGENCY=");
  Serial.println(emergency ? "TRUE" : "FALSE");

  return true;
}

bool plcRequestGate() {
  return plcPulseCoil(COIL_CMD_ROBOT_REQUEST, "CMD_ROBOT_REQUEST");
}

bool plcNotifyPassed() {
  return plcPulseCoil(COIL_CMD_ROBOT_PASSED, "CMD_ROBOT_PASSED");
}

void monitorEmergencyWhenMoving() {
  if (gateState != GATE_IDLE) return;
  if (currentMotion == STOPPED) return;
  if (millis() - lastEmergencyMonitor < EMERGENCY_MONITOR_INTERVAL_MS) return;

  lastEmergencyMonitor = millis();

  bool passAllowed = false;
  bool emergency = false;

  if (plcReadStatus(passAllowed, emergency) && emergency) {
    stopMotors();
    gateState = GATE_IDLE;
    Serial.println("[GATE] Acil durum algilandi. Robot durdu.");
  }
}

// ================= KAPI AKISI =================

void beginGateRequest(float distance) {
  if (!gateModeEnabled) {
    stopMotors();
    Serial.println("[GATE] Gate mode kapali. Sadece durdu.");
    return;
  }

  if (gateState != GATE_IDLE) return;

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
  if (gateState == GATE_IDLE) return;

  if (gateState == GATE_WAITING_PERMISSION) {
    if (millis() - lastPlcPoll < PLC_POLL_INTERVAL_MS) return;
    lastPlcPoll = millis();

    bool passAllowed = false;
    bool emergency = false;

    bool ok = plcReadStatus(passAllowed, emergency);
    if (!ok) return;

    if (emergency) {
      stopMotors();
      gateState = GATE_IDLE;
      Serial.println("[GATE] PLC acil durumda. Robot durdu.");
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
  clearManualMotionTimeout();
  Serial.println("[GATE] Gecis izni geldi. Robot kapidan geciyor...");

  gateState = GATE_PASSING;
  gatePassStartMs = millis();
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
  if (!Serial.available()) return;

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
  else if (cmd == "status") {
    printRuntimeStatus();
  }
  else if (cmd == "gate_on") {
    gateModeEnabled = true;
    Serial.println("Gate mode: ON");
  }
  else if (cmd == "gate_off") {
    gateModeEnabled = false;
    Serial.println("Gate mode: OFF");
  }
  else if (cmd == "request") {
    plcRequestGate();
  }
  else if (cmd == "passed") {
    plcNotifyPassed();
  }
  else {
    Serial.println("Bilinmeyen komut.");
    printCommands();
  }
}

void printCommands() {
  Serial.println("Komutlar:");
  Serial.println("ileri / f       -> ileri git");
  Serial.println("geri  / b       -> geri git");
  Serial.println("sol   / l       -> sola don");
  Serial.println("sag   / r       -> saga don");
  Serial.println("dur   / s       -> dur");
  Serial.println("status          -> durum yazdir");
  Serial.println("gate_on/off     -> kapi modunu ac/kapat");
  Serial.println("request         -> PLC'ye manuel robot request pulse");
  Serial.println("passed          -> PLC'ye manuel robot passed pulse");
  Serial.println("------------------------------------------------");
}

// ================= MESAFE KONTROL =================

void distanceSafetyControl() {
  if (millis() - lastDistanceCheck < distanceCheckInterval) return;
  lastDistanceCheck = millis();

  if (currentMotion != FORWARD) return;

  if (millis() < ignoreDistanceSafetyUntil) return;

  if (gateState == GATE_WAITING_PERMISSION) return;

  float distance = readDistanceCm();
  lastDistanceCm = distance;

  if (distance <= 0) return;

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
  if (duration == 0) return -1;

  return duration * 0.0343 / 2.0;
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

// ================= MOTOR YON =================

void setLeftMotor(bool forwardDirection) {
  if (LEFT_INVERT) forwardDirection = !forwardDirection;

  if (forwardDirection) {
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
  } else {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
  }
}

void setRightMotor(bool forwardDirection) {
  if (RIGHT_INVERT) forwardDirection = !forwardDirection;

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
  lastDistanceCm = distance;

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

// ================= WEB SERVER =================

void setupWebServer() {
  server.on("/", HTTP_GET, handleRoot);
  server.on("/api/move", HTTP_GET, handleApiMove);
  server.on("/api/status", HTTP_GET, handleApiStatus);
  server.on("/api/gate_mode", HTTP_GET, handleApiGateMode);
  server.on("/api/settings", HTTP_GET, handleApiSettings);
  server.on("/api/gate/request", HTTP_GET, handleApiGateRequest);
  server.on("/api/gate/passed", HTTP_GET, handleApiGatePassed);
  server.on("/api/gate/force_pass", HTTP_GET, handleApiGateForcePass);
  server.on("/api/plc/status", HTTP_GET, []() { bool p=false, e=false; bool ok=plcReadStatus(p,e); String j="{\"ok\":"; j += ok ? "true" : "false"; j += ",\"pass_allowed\":" + boolToJson(p) + ",\"emergency\":" + boolToJson(e) + "}"; sendJson(j, ok ? 200 : 500); });

  server.on("/f", HTTP_GET, []() { doMoveCommand("f"); sendJson("{\"ok\":true,\"cmd\":\"f\"}"); });
  server.on("/b", HTTP_GET, []() { doMoveCommand("b"); sendJson("{\"ok\":true,\"cmd\":\"b\"}"); });
  server.on("/l", HTTP_GET, []() { doMoveCommand("l"); sendJson("{\"ok\":true,\"cmd\":\"l\"}"); });
  server.on("/r", HTTP_GET, []() { doMoveCommand("r"); sendJson("{\"ok\":true,\"cmd\":\"r\"}"); });
  server.on("/s", HTTP_GET, []() { doMoveCommand("s"); sendJson("{\"ok\":true,\"cmd\":\"s\"}"); });

  server.onNotFound([]() {
    sendJson("{\"ok\":false,\"error\":\"not_found\"}", 404);
  });
}

void handleRoot() {
  String html = R"rawliteral(
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jülide Joystick</title>
<style>
body{font-family:Arial,sans-serif;background:#111827;color:#e5e7eb;margin:0;padding:18px;text-align:center}
.card{max-width:520px;margin:auto;background:#1f2937;border-radius:18px;padding:18px;box-shadow:0 10px 30px #0006}
h1{font-size:24px;margin:8px 0 16px}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin:18px 0}
button{font-size:20px;padding:18px;border:0;border-radius:14px;background:#2563eb;color:white;font-weight:700}
button:active{transform:scale(.98);background:#1d4ed8}
.stop{background:#dc2626}
.small{font-size:15px;padding:12px;background:#374151}
.on{background:#059669}.off{background:#6b7280}
pre{text-align:left;background:#0b1220;padding:12px;border-radius:12px;overflow:auto;font-size:13px}
</style>
</head>
<body>
<div class="card">
<h1>Jülide Web Joystick v6</h1><p>Komut modu: Basılan yön, DUR komutuna kadar devam eder.</p>
<div class="grid">
<div></div><button onclick="move('f')">İLERİ</button><div></div>
<button onclick="move('l')">SOL</button><button class="stop" onclick="move('s')">DUR</button><button onclick="move('r')">SAĞ</button>
<div></div><button onclick="move('b')">GERİ</button><div></div>
</div>
<div class="grid">
<button class="small on" onclick="gate(1)">Gate ON</button>
<button class="small off" onclick="gate(0)">Gate OFF</button>
<button class="small" onclick="refresh()">Status</button>
<button class="small" onclick="fetch('/api/gate/request').then(refresh)">Request</button>
<button class="small" onclick="fetch('/api/gate/passed').then(refresh)">Passed</button>
<button class="small on" onclick="fetch('/api/gate/force_pass').then(refresh)">Geç</button>
<button class="small stop" onclick="move('s')">STOP</button>
</div>
<pre id="status">loading...</pre>
</div>
<script>
async function move(c){try{await fetch('/api/move?cmd='+c,{cache:'no-store'});refresh()}catch(e){show(e)}}
async function gate(v){try{await fetch('/api/gate_mode?enabled='+v,{cache:'no-store'});refresh()}catch(e){show(e)}}
function show(x){document.getElementById('status').textContent=typeof x==='string'?x:JSON.stringify(x,null,2)}
async function refresh(){try{let r=await fetch('/api/status',{cache:'no-store'});show(await r.json())}catch(e){show('status error: '+e)}}
setInterval(refresh,1000); refresh();
</script>
</body>
</html>
)rawliteral";
  server.send(200, "text/html; charset=utf-8", html);
}

void handleApiMove() {
  if (!server.hasArg("cmd")) {
    sendJson("{\"ok\":false,\"error\":\"missing_cmd\"}", 400);
    return;
  }

  String cmd = server.arg("cmd");
  cmd.trim();
  cmd.toLowerCase();

  bool ok = doMoveCommand(cmd);

  String json = "{\"ok\":";
  json += ok ? "true" : "false";
  json += ",\"cmd\":\"" + cmd + "\"}";
  sendJson(json, ok ? 200 : 400);
}

bool doMoveCommand(const String &cmd) {
  if (cmd == "f" || cmd == "ileri") {
    forward();
    return true;
  }
  if (cmd == "b" || cmd == "geri") {
    backward();
    return true;
  }
  if (cmd == "l" || cmd == "sol") {
    turnLeft();
    return true;
  }
  if (cmd == "r" || cmd == "sag" || cmd == "sağ") {
    turnRight();
    return true;
  }
  if (cmd == "s" || cmd == "dur") {
    clearManualMotionTimeout();
    stopMotors();
    gateState = GATE_IDLE;
    Serial.println("[WEB] Durdu.");
    return true;
  }

  return false;
}

void armManualMotionTimeout() {
  if (!MANUAL_AUTO_STOP_ENABLED) {
    manualMotionTimeoutAt = 0;
    return;
  }
  manualMotionTimeoutAt = millis() + MANUAL_COMMAND_TIMEOUT_MS;
}

void clearManualMotionTimeout() {
  manualMotionTimeoutAt = 0;
}

void autoStopManualMotion() {
  if (!MANUAL_AUTO_STOP_ENABLED) return;
  if (manualMotionTimeoutAt == 0) return;
  if (gateState != GATE_IDLE) return;
  if (currentMotion == STOPPED) {
    manualMotionTimeoutAt = 0;
    return;
  }
  if ((long)(millis() - manualMotionTimeoutAt) >= 0) {
    stopMotors();
    manualMotionTimeoutAt = 0;
    Serial.println("[WEB] Joystick timeout: otomatik durdu.");
  }
}

void handleApiGateMode() {
  if (!server.hasArg("enabled")) {
    sendJson("{\"ok\":false,\"error\":\"missing_enabled\"}", 400);
    return;
  }

  String enabled = server.arg("enabled");
  gateModeEnabled = (enabled == "1" || enabled == "true" || enabled == "on");

  String json = "{\"ok\":true,\"gate_mode_enabled\":";
  json += gateModeEnabled ? "true" : "false";
  json += "}";
  sendJson(json);
}

void handleApiGateRequest() {
  bool ok = plcRequestGate();
  if (ok) gateState = GATE_WAITING_PERMISSION;
  sendJson(ok ? "{\"ok\":true,\"cmd\":\"request\"}" : "{\"ok\":false,\"cmd\":\"request\"}", ok ? 200 : 500);
}

void handleApiGatePassed() {
  bool ok = plcNotifyPassed();
  if (ok) gateState = GATE_IDLE;
  sendJson(ok ? "{\"ok\":true,\"cmd\":\"passed\"}" : "{\"ok\":false,\"cmd\":\"passed\"}", ok ? 200 : 500);
}

void handleApiGateForcePass() {
  // Fallback/manuel test:
  // GUI Allow verdikten sonra Jülide status okuyamazsa bu endpoint robotu
  // doğrudan kapıdan geçiş sekansına alır.
  if (gateState == GATE_PASSING) {
    sendJson("{\"ok\":true,\"already_passing\":true}");
    return;
  }

  Serial.println("[WEB] Force pass komutu alindi.");
  startGatePassing();
  sendJson("{\"ok\":true,\"cmd\":\"force_pass\"}");
}


void handleApiSettings() {
  String json = "{";
  json += "\"motor_speed\":" + String(motorSpeed) + ",";
  json += "\"slow_speed\":" + String(slowSpeed) + ",";
  json += "\"stop_distance_cm\":" + String(stopDistanceCm, 1) + ",";
  json += "\"slow_distance_cm\":" + String(slowDistanceCm, 1) + ",";
  json += "\"gate_pass_drive_ms\":" + String(GATE_PASS_DRIVE_MS) + ",";
  json += "\"plc_ip\":\"" + ipToString(PLC_IP) + "\"";
  json += "}";
  sendJson(json);
}

void handleApiStatus() {
  // Status sayfasi icin hafif guncelleme.
  if (WiFi.status() == WL_CONNECTED) {
    maintainModbusConnection(false);
  }

  if (millis() - lastDistanceCheck > 250) {
    float d = readDistanceCm();
    if (d > 0) lastDistanceCm = d;
  }

  bool passAllowed = lastPassAllowed;
  bool emergency = lastEmergency;

  // /api/status hafif kalsin: her 500 ms web status isteginde Modbus okuma yapma.
  // PLC statusu gate workflow sirasinda veya manuel /api/plc/status ile guncellenir.

  String json = "{";
  json += "\"robot_id\":\"" + String(ROBOT_ID) + "\",";
  json += "\"wifi_connected\":" + boolToJson(WiFi.status() == WL_CONNECTED) + ",";
  json += "\"robot_ip\":\"" + ipToString(WiFi.localIP()) + "\",";
  json += "\"plc_ip\":\"" + ipToString(PLC_IP) + "\",";
  json += "\"plc_connected\":" + boolToJson(lastPlcConnected) + ",";
  json += "\"motion\":\"" + motionToString(currentMotion) + "\",";
  json += "\"gate_state\":\"" + gateStateToString(gateState) + "\",";
  json += "\"distance_cm\":" + String(lastDistanceCm, 1) + ",";
  json += "\"gate_mode_enabled\":" + boolToJson(gateModeEnabled) + ",";
  json += "\"pass_allowed\":" + boolToJson(passAllowed) + ",";
  json += "\"emergency\":" + boolToJson(emergency) + ",";
  json += "\"manual_mode\":\"latch_until_stop\"";
  json += "}";

  sendJson(json);
}

void sendJson(const String &json, int code) {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(code, "application/json; charset=utf-8", json);
}

String boolToJson(bool value) {
  return value ? "true" : "false";
}

String ipToString(IPAddress ip) {
  return String(ip[0]) + "." + String(ip[1]) + "." + String(ip[2]) + "." + String(ip[3]);
}

String motionToString(MotionState state) {
  switch (state) {
    case STOPPED: return "STOPPED";
    case FORWARD: return "FORWARD";
    case BACKWARD: return "BACKWARD";
    case TURN_LEFT: return "TURN_LEFT";
    case TURN_RIGHT: return "TURN_RIGHT";
    default: return "UNKNOWN";
  }
}

String gateStateToString(GateWorkflowState state) {
  switch (state) {
    case GATE_IDLE: return "GATE_IDLE";
    case GATE_WAITING_PERMISSION: return "GATE_WAITING_PERMISSION";
    case GATE_PASSING: return "GATE_PASSING";
    default: return "UNKNOWN";
  }
}

// ================= LOG / SETTINGS =================

void printSettings() {
  Serial.println("Ayarlar:");
  Serial.print("WiFi SSID: ");
  Serial.println(WIFI_SSID);
  Serial.print("OpenPLC IP: ");
  Serial.println(PLC_IP);
  Serial.print("OpenPLC Port: ");
  Serial.println(PLC_PORT);
  Serial.print("OpenPLC Unit ID: ");
  Serial.println(MODBUS_UNIT_ID);

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
  Serial.println("------------------------------------------------");
}

void printRuntimeStatus() {
  Serial.println("Runtime Status:");
  Serial.print("WiFi: ");
  Serial.println(WiFi.status() == WL_CONNECTED ? "CONNECTED" : "DISCONNECTED");
  Serial.print("Robot IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("PLC connected: ");
  Serial.println(lastPlcConnected ? "YES" : "NO");
  Serial.print("Motion: ");
  Serial.println(motionToString(currentMotion));
  Serial.print("Gate state: ");
  Serial.println(gateStateToString(gateState));
  Serial.print("Distance: ");
  Serial.print(lastDistanceCm);
  Serial.println(" cm");
  Serial.print("Gate mode: ");
  Serial.println(gateModeEnabled ? "ON" : "OFF");
  Serial.print("Pass allowed: ");
  Serial.println(lastPassAllowed ? "TRUE" : "FALSE");
  Serial.print("Emergency: ");
  Serial.println(lastEmergency ? "TRUE" : "FALSE");
  Serial.println("------------------------------------------------");
}
