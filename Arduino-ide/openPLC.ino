/*
  OpenPLC / ESP8266 Factory Gate Controller
  - 4-channel relay = PLC state outputs
  - SG90 servo = barrier actuator
  - WiFi HTTP API = HMI + robot communication

  Pins:
  D1 -> Relay IN1 -> K1 Ready / Blue
  D2 -> Relay IN2 -> K2 Request / Yellow
  D5 -> Relay IN3 -> K3 Pass Allowed / Green
  D6 -> Relay IN4 -> K4 Emergency / Red
  D7 -> Servo Signal
*/

#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <Servo.h>

// ===================== WIFI CONFIG =====================

// true  -> ESP kendi WiFi ağını açar
// false -> Var olan WiFi ağına bağlanır
#define USE_AP_MODE true

const char* AP_SSID = "PLC_GATE_CTRL";
const char* AP_PASS = "12345678";

// Yarışma/ev ağına bağlanmak istersen USE_AP_MODE false yap
const char* STA_SSID = "WIFI_ADI";
const char* STA_PASS = "WIFI_SIFRESI";

// ===================== PIN CONFIG =====================

#define RELAY_K1_PIN D1
#define RELAY_K2_PIN D2
#define RELAY_K3_PIN D5
#define RELAY_K4_PIN D6

#define SERVO_PIN    D7

// Çoğu 4'lü röle modülü ACTIVE LOW çalışır.
// Röle ters çalışırsa bunu false yap.
const bool RELAY_ACTIVE_LOW = true;

// Servo açıları
const int SERVO_CLOSED_ANGLE = 0;
const int SERVO_OPEN_ANGLE   = 120;

// Geçiş izninden sonra otomatik kapanma süresi
const unsigned long AUTO_CLOSE_MS = 6000;

// ===================== GLOBALS =====================

ESP8266WebServer server(80);
Servo gateServo;

enum GateState {
  STATE_READY = 1,        // K1 - Mavi
  STATE_REQUEST = 2,      // K2 - Sarı
  STATE_PASS_ALLOWED = 3, // K3 - Yeşil
  STATE_EMERGENCY = 4     // K4 - Kırmızı
};

GateState currentState = STATE_READY;

unsigned long passStartMs = 0;
String lastEvent = "boot";
String lastRobotId = "none";

// ===================== UTILS =====================

String boolJson(bool v) {
  return v ? "true" : "false";
}

String stateName(GateState s) {
  switch (s) {
    case STATE_READY:
      return "READY";
    case STATE_REQUEST:
      return "REQUEST";
    case STATE_PASS_ALLOWED:
      return "PASS_ALLOWED";
    case STATE_EMERGENCY:
      return "EMERGENCY";
    default:
      return "UNKNOWN";
  }
}

void relayWrite(uint8_t pin, bool on) {
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(pin, on ? LOW : HIGH);
  } else {
    digitalWrite(pin, on ? HIGH : LOW);
  }
}

void allRelaysOff() {
  relayWrite(RELAY_K1_PIN, false);
  relayWrite(RELAY_K2_PIN, false);
  relayWrite(RELAY_K3_PIN, false);
  relayWrite(RELAY_K4_PIN, false);
}

void applyOutputs() {
  allRelaysOff();

  if (currentState == STATE_READY) {
    relayWrite(RELAY_K1_PIN, true);
    gateServo.write(SERVO_CLOSED_ANGLE);
  }

  else if (currentState == STATE_REQUEST) {
    relayWrite(RELAY_K2_PIN, true);
    gateServo.write(SERVO_CLOSED_ANGLE);
  }

  else if (currentState == STATE_PASS_ALLOWED) {
    relayWrite(RELAY_K3_PIN, true);
    gateServo.write(SERVO_OPEN_ANGLE);
  }

  else if (currentState == STATE_EMERGENCY) {
    relayWrite(RELAY_K4_PIN, true);
    gateServo.write(SERVO_CLOSED_ANGLE);
  }
}

void setState(GateState newState, String eventName) {
  currentState = newState;
  lastEvent = eventName;

  if (newState == STATE_PASS_ALLOWED) {
    passStartMs = millis();
  }

  applyOutputs();

  Serial.print("[STATE] ");
  Serial.print(stateName(currentState));
  Serial.print(" | Event: ");
  Serial.println(lastEvent);
}

void sendJson(int code, String body) {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  server.send(code, "application/json", body);
}

String makeStatusJson() {
  bool isReady = currentState == STATE_READY;
  bool isRequest = currentState == STATE_REQUEST;
  bool isPass = currentState == STATE_PASS_ALLOWED;
  bool isEmergency = currentState == STATE_EMERGENCY;

  String json = "{";

  json += "\"device\":\"openplc_gate_controller\",";
  json += "\"state\":" + String((int)currentState) + ",";
  json += "\"state_name\":\"" + stateName(currentState) + "\",";
  json += "\"last_event\":\"" + lastEvent + "\",";
  json += "\"last_robot_id\":\"" + lastRobotId + "\",";

  json += "\"robot_request\":" + boolJson(isRequest) + ",";
  json += "\"pass_allowed\":" + boolJson(isPass) + ",";
  json += "\"barrier_open\":" + boolJson(isPass) + ",";
  json += "\"emergency\":" + boolJson(isEmergency) + ",";

  int servoAngle = isPass ? SERVO_OPEN_ANGLE : SERVO_CLOSED_ANGLE;
  json += "\"servo_angle\":" + String(servoAngle) + ",";

  json += "\"relays\":{";
  json += "\"K1_ready_blue\":" + boolJson(isReady) + ",";
  json += "\"K2_request_yellow\":" + boolJson(isRequest) + ",";
  json += "\"K3_pass_green\":" + boolJson(isPass) + ",";
  json += "\"K4_emergency_red\":" + boolJson(isEmergency);
  json += "},";

  json += "\"pins\":{";
  json += "\"D1\":\"K1_READY\",";
  json += "\"D2\":\"K2_REQUEST\",";
  json += "\"D5\":\"K3_PASS_ALLOWED\",";
  json += "\"D6\":\"K4_EMERGENCY\",";
  json += "\"D7\":\"SERVO_SIGNAL\"";
  json += "}";

  json += "}";

  return json;
}

// ===================== HTTP HANDLERS =====================

void handleRoot() {
  String html = "";
  html += "<html><head><meta charset='UTF-8'>";
  html += "<title>ESP8266 PLC Gate Controller</title></head><body>";
  html += "<h2>ESP8266 OpenPLC Gate Controller</h2>";
  html += "<p>State: <b>" + stateName(currentState) + "</b></p>";
  html += "<ul>";
  html += "<li><a href='/status'>/status</a></li>";
  html += "<li><a href='/robot/request?id=robot1'>/robot/request?id=robot1</a></li>";
  html += "<li><a href='/hmi/allow'>/hmi/allow</a></li>";
  html += "<li><a href='/robot/passed?id=robot1'>/robot/passed?id=robot1</a></li>";
  html += "<li><a href='/hmi/emergency_on'>/hmi/emergency_on</a></li>";
  html += "<li><a href='/hmi/reset'>/hmi/reset</a></li>";
  html += "</ul>";
  html += "</body></html>";

  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "text/html", html);
}

void handleStatus() {
  sendJson(200, makeStatusJson());
}

// Robot kapıya geldiğinde bunu çağıracak
void handleRobotRequest() {
  if (server.hasArg("id")) {
    lastRobotId = server.arg("id");
  } else {
    lastRobotId = "robot_unknown";
  }

  if (currentState == STATE_EMERGENCY) {
    lastEvent = "robot_request_rejected_emergency";
    sendJson(423, makeStatusJson());
    return;
  }

  if (currentState == STATE_READY) {
    setState(STATE_REQUEST, "robot_request_received");
  } else {
    lastEvent = "robot_request_received_but_state_not_ready";
  }

  sendJson(200, makeStatusJson());
}

// Robot kapıdan geçtiğinde bunu çağıracak
void handleRobotPassed() {
  if (server.hasArg("id")) {
    lastRobotId = server.arg("id");
  }

  if (currentState == STATE_PASS_ALLOWED) {
    setState(STATE_READY, "robot_passed_gate_closed");
  } else {
    lastEvent = "robot_passed_signal_ignored";
  }

  sendJson(200, makeStatusJson());
}

// HMI üzerindeki "Geçiş izni ver" butonu
void handleHmiAllow() {
  if (currentState == STATE_EMERGENCY) {
    lastEvent = "hmi_allow_blocked_emergency";
    sendJson(423, makeStatusJson());
    return;
  }

  setState(STATE_PASS_ALLOWED, "hmi_pass_allowed");
  sendJson(200, makeStatusJson());
}

// HMI üzerindeki "Reddet / hata" butonu
void handleHmiDeny() {
  setState(STATE_EMERGENCY, "hmi_denied_or_fault");
  sendJson(200, makeStatusJson());
}

// HMI üzerindeki "Acil stop" butonu
void handleEmergencyOn() {
  setState(STATE_EMERGENCY, "emergency_on");
  sendJson(200, makeStatusJson());
}

// HMI üzerindeki "Acil stop kaldır" veya "Reset" butonu
void handleReset() {
  setState(STATE_READY, "system_reset_ready");
  sendJson(200, makeStatusJson());
}

// Manuel test için bariyer aç
void handleManualOpen() {
  if (currentState == STATE_EMERGENCY) {
    sendJson(423, makeStatusJson());
    return;
  }

  setState(STATE_PASS_ALLOWED, "manual_open");
  sendJson(200, makeStatusJson());
}

// Manuel test için bariyer kapat
void handleManualClose() {
  setState(STATE_READY, "manual_close");
  sendJson(200, makeStatusJson());
}

void handleNotFound() {
  sendJson(404, "{\"error\":\"endpoint_not_found\"}");
}

// ===================== WIFI SETUP =====================

void setupWiFi() {
  if (USE_AP_MODE) {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);

    Serial.println();
    Serial.println("[WiFi] AP Mode Started");
    Serial.print("[WiFi] SSID: ");
    Serial.println(AP_SSID);
    Serial.print("[WiFi] IP: ");
    Serial.println(WiFi.softAPIP());
  } 
  
  else {
    WiFi.mode(WIFI_STA);
    WiFi.begin(STA_SSID, STA_PASS);

    Serial.println();
    Serial.print("[WiFi] Connecting to ");
    Serial.println(STA_SSID);

    unsigned long startAttempt = millis();

    while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 20000) {
      delay(500);
      Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println();
      Serial.println("[WiFi] Connected");
      Serial.print("[WiFi] IP: ");
      Serial.println(WiFi.localIP());
    } else {
      Serial.println();
      Serial.println("[WiFi] STA failed. Starting fallback AP...");
      WiFi.mode(WIFI_AP);
      WiFi.softAP(AP_SSID, AP_PASS);
      Serial.print("[WiFi] Fallback AP IP: ");
      Serial.println(WiFi.softAPIP());
    }
  }
}

// ===================== SETUP / LOOP =====================

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(RELAY_K1_PIN, OUTPUT);
  pinMode(RELAY_K2_PIN, OUTPUT);
  pinMode(RELAY_K3_PIN, OUTPUT);
  pinMode(RELAY_K4_PIN, OUTPUT);

  allRelaysOff();

  gateServo.attach(SERVO_PIN);
  gateServo.write(SERVO_CLOSED_ANGLE);

  setupWiFi();

  server.on("/", handleRoot);
  server.on("/status", handleStatus);

  // Robot endpoints
  server.on("/robot/request", handleRobotRequest);
  server.on("/robot/passed", handleRobotPassed);

  // HMI endpoints
  server.on("/hmi/allow", handleHmiAllow);
  server.on("/hmi/deny", handleHmiDeny);
  server.on("/hmi/emergency_on", handleEmergencyOn);
  server.on("/hmi/reset", handleReset);

  // Manual test endpoints
  server.on("/hmi/manual/open", handleManualOpen);
  server.on("/hmi/manual/close", handleManualClose);

  server.onNotFound(handleNotFound);

  server.begin();
  Serial.println("[HTTP] Server started");

  setState(STATE_READY, "boot_ready");
}

void loop() {
  server.handleClient();

  // Geçiş izni verildikten sonra robot "geçtim" demezse
  // belirli süre sonra kapı otomatik kapanır.
  if (currentState == STATE_PASS_ALLOWED) {
    if (millis() - passStartMs >= AUTO_CLOSE_MS) {
      setState(STATE_READY, "auto_close_timeout");
    }
  }
}

