# Jülide Robot + OpenPLC Gate Automation System

**PLC tabanlı kapı kontrol sistemi ile mobil robot entegrasyonu — ESP8266 / Modbus TCP / Ladder Diagram / PySide6 HMI**

---

## Demo Video

<p align="center">
  <a href="https://www.youtube.com/watch?v=nVAnG_Sywss">
    <img src="https://img.youtube.com/vi/nVAnG_Sywss/maxresdefault.jpg" alt="Jülide Robot + OpenPLC Gate Demo" width="720">
  </a>
</p>

<p align="center">
  <iframe width="720" height="405" src="https://www.youtube.com/embed/nVAnG_Sywss" title="Jülide Robot + OpenPLC Gate Demo" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
</p>

<p align="center">
  <a href="https://www.youtube.com/watch?v=nVAnG_Sywss">YouTube'da izle</a>
</p>

---

## İçindekiler

0. [Demo Video](#demo-video)
1. [Genel Tanım](#1-genel-tanım)
2. [Sistem Mimarisi](#2-sistem-mimarisi)
3. [Donanım Bileşenleri](#3-donanım-bileşenleri)
4. [Yazılım Bileşenleri](#4-yazılım-bileşenleri)
5. [OpenPLC Gate Ladder State Machine](#5-openplc-gate-ladder-state-machine)
6. [Modbus TCP Coil Haritası](#6-modbus-tcp-coil-haritası)
7. [Servo Kontrol Mantığı](#7-servo-kontrol-mantığı)
8. [Jülide Robot Çalışma Mantığı](#8-jülide-robot-çalışma-mantığı)
9. [GUI / HMI Çalışma Mantığı](#9-gui--hmi-çalışma-mantığı)
10. [Karşılaşılan Hatalar ve Çözümler](#10-karşılaşılan-hatalar-ve-çözümler)
11. [Kurulum ve Çalıştırma](#11-kurulum-ve-çalıştırma)
12. [Test Senaryosu](#12-test-senaryosu)
13. [Repo Klasör Yapısı](#13-repo-klasör-yapısı)
14. [Güvenlik Notları](#14-güvenlik-notları)
15. [Lessons Learned](#15-lessons-learned)
16. [Teknik Özet](#16-teknik-özet)

---

## 1. Genel Tanım

Bu proje; **ESP8266 tabanlı Jülide** adlı mobil robotun, **OpenPLC** ile programlanmış bir **otomatik kapı (gate) kontrol sistemi** ile haberleşmesini sağlayan, küçük ölçekli bir PLC + robotik entegrasyon örneğidir.

### Projenin Amacı

Endüstriyel tesislerde gezgin robotların kapı geçiş prosedürlerine uymak zorunda olduğu senaryolar vardır: robot kapıya yaklaşır, kapı kontrol sistemiyle haberleşir, operatör onay verir, kapı açılır, robot geçer, kapı kapanır. Bu proje bu süreci aşağıdaki bileşenlerle küçük ölçekte uygular:

- **Gate ESP8266 / OpenPLC** — Ladder Diagram ile programlanmış PLC, röle ve servo kontrolü.
- **Jülide Robot ESP8266** — Arduino C++ ile çalışan, L298N motorlu, HC-SR04 sensörlü, web joystickli mobil robot.
- **PC GUI / HMI** — PySide6 ile geliştirilmiş operatör arayüzü; Modbus TCP ile gate'e bağlanır.

### Akış Özeti

```
Robot kapıya yaklaşır
  → PLC'ye REQUEST gönderir
    → Operatör GUI'den ALLOW verir
      → Servo açılır, robot geçer
        → Robot PASSED bildirir
          → Servo kapanır, sistem READY'ye döner
```

Bu proje eğitim amaçlıdır; IEC 61131-3 Ladder Diagram, Modbus TCP protokolü ve gömülü sistemler konusunda pratik bir uygulama örneği sunar.

---

## 2. Sistem Mimarisi

### Ağ Topolojisi

PC, Windows Mobile Hotspot açar. Gate ESP8266 ve Jülide aynı ağa Wi-Fi üzerinden bağlanır.

| Parametre | Değer |
|---|---|
| Hotspot SSID | `PLC_GATE_CTRL` |
| Hotspot Şifre | `12345678` |
| Gate ESP IP | `192.168.137.218` (örnek) |
| Modbus TCP Port | `502` |
| Modbus Unit ID | `0` |

### Ağdaki Roller

| Cihaz | Rol |
|---|---|
| Gate ESP8266 / OpenPLC | Modbus TCP Server |
| Jülide ESP8266 | Modbus TCP Client + HTTP Web Server |
| PC GUI | Modbus TCP Client |
| Browser / Operatör | HTTP Client (Jülide joystick arayüzü) |

### Sistem Diyagramı

```
┌─────────────────────────────────────────┐
│           PC / Windows Hotspot          │
│         SSID: PLC_GATE_CTRL             │
└────────────┬────────────────────────────┘
             │ Wi-Fi (192.168.137.x)
    ┌────────┴───────────┐
    │                    │
┌───▼──────────┐  ┌──────▼──────────────────────┐
│ Gate ESP8266 │  │     Jülide ESP8266 Robot     │
│  OpenPLC     │  │  Arduino C++ / Web Server    │
│  Ladder Diag │  │  L298N + HC-SR04             │
│  Modbus TCP  │◄─┤  Modbus TCP Client           │
│  Server :502 │  │  HTTP Server (joystick)      │
└───┬──────────┘  └──────────────────────────────┘
    │                          ▲
    │ Modbus TCP               │ HTTP (joystick)
    ▼                          │
┌─────────────────┐    ┌───────┴──────┐
│   PC GUI / HMI  │    │   Browser /  │
│   PySide6       │    │   Operatör   │
│   Modbus Client │    └──────────────┘
└─────────────────┘
```

### Komut Akışı

```
[PC GUI / PySide6]
    │
    │  Modbus TCP: CMD_HMI_ALLOW (coil 9)
    │              CMD_EMERGENCY (coil 11)
    │              CMD_RESET     (coil 12)
    │
    ▼
[Gate ESP8266 / OpenPLC Ladder]
    │  K1 READY  → %QX0.0 → coil 0
    │  K2 REQUEST → %QX0.1 → coil 1
    │  K3 PASS_ALLOWED → %QX0.2 → coil 2
    │  K4 EMERGENCY → %QX0.3 → coil 3
    │  Servo PWM → GPIO13 / D7
    ▲
    │  Modbus TCP: CMD_ROBOT_REQUEST (coil 8)
    │              CMD_ROBOT_PASSED  (coil 10)
    │
[Jülide Robot ESP8266]
    │
    │  HTTP (joystick / status)
    ▼
[Browser / Operatör]
```

---

## 3. Donanım Bileşenleri

### 3.1 Gate ESP8266 Tarafı

| Bileşen | Adet | Not |
|---|---|---|
| ESP8266 NodeMCU / Wemos D1 | 1 | OpenPLC target |
| 4 kanal röle modülü | 1 | Active-low |
| SG90 servo motor | 1 | Gate açma/kapama |
| USB güç kaynağı / 5V | 1 | ESP + röle beslemesi |
| Jumper kablolar | — | — |

#### Röle Pin Haritası

| Pin Adı | GPIO | NodeMCU Pin | Röle |
|---|---|---|---|
| Q_READY | GPIO5 | D1 | K1 READY |
| Q_REQUEST | GPIO4 | D2 | K2 REQUEST |
| Q_PASS_ALLOWED | GPIO14 | D5 | K3 PASS_ALLOWED |
| Q_EMERGENCY | GPIO12 | D6 | K4 EMERGENCY |

#### Servo Bağlantısı

| Bağlantı | Hedef |
|---|---|
| Servo Signal | GPIO13 / D7 |
| Servo VCC | 5V / VIN |
| Servo GND | GND |

> **Active-Low Röle Notu:** Kullanılan 4 kanal röle modülü active-low çalışır. GPIO LOW olduğunda röle aktif (çeker), HIGH olduğunda pasif (bırakır). Bu nedenle Ladder programında fiziksel Q çıkışları (`Q_READY`, `Q_REQUEST`, vb.) ters mantıkla yazılmıştır:
> ```
> Q_READY := NOT(M_READY);
> ```

---

### 3.2 Jülide Robot ESP8266 Tarafı

| Bileşen | Adet | Not |
|---|---|---|
| ESP8266 NodeMCU / LoLin V3 | 1 | Arduino IDE target |
| L298N motor sürücü | 1 | 4 TT motor |
| 4x TT motor | 4 | Tekerlekli şasi |
| HC-SR04 ultrasonik sensör | 1 | Mesafe ölçümü |
| LiPo / pil paketi | 1 | Motor güç beslemesi |
| USB güç / power bank | 1 | ESP güç beslemesi |

#### Jülide Pin Haritası

| Sinyal | GPIO | NodeMCU Pin |
|---|---|---|
| L298N IN1 | GPIO5 | D1 |
| L298N IN2 | GPIO4 | D2 |
| L298N IN3 | GPIO14 | D5 |
| L298N IN4 | GPIO12 | D6 |
| L298N ENA (PWM) | GPIO13 | D7 |
| L298N ENB (PWM) | GPIO15 | D8 |
| HC-SR04 TRIG | GPIO0 | D3 |
| HC-SR04 ECHO | GPIO16 | D0 |

---

## 4. Yazılım Bileşenleri

### Bileşen Tablosu

| Bileşen | IDE | Dil / Teknoloji | Görev |
|---|---|---|---|
| Gate ESP8266 | OpenPLC Editor | Ladder Diagram (IEC 61131-3) | PLC state machine, röle kontrolü, servo PWM |
| Jülide ESP8266 | Arduino IDE | Arduino C++ / ESP8266 | Motor, HC-SR04, Modbus TCP client, HTTP joystick |
| PC GUI / HMI | VS Code / Cursor | Python 3 + PySide6 | Operatör HMI, allow/emergency/reset, durum izleme |

### 4.1 Gate / OpenPLC Editor

- **Geliştirme Ortamı:** OpenPLC Editor (masaüstü uygulaması)
- **Programlama Dili:** Ladder Diagram — IEC 61131-3
- **Hedef Platform:** ESP8266 NodeMCU
- **Haberleşme:** Modbus TCP Server (port 502)
- **Temel İşlev:** State machine, röle çıkışları, servo PWM kontrolü

#### Neden OpenPLC + Ladder?

Proje ilk başta Gate ESP de Arduino HTTP üzerinden kontrol ediliyordu. Ancak bu yapı, endüstriyel PLC mantığından uzaktır ve proje kapsamı gereği Ladder Diagram ile yeniden yazıldı. OpenPLC Editor, ESP8266 üzerinde IEC 61131-3 uyumlu Ladder programı derlemeyi ve Modbus TCP slave olarak çalıştırmayı sağlar.

### 4.2 Jülide Robot / Arduino IDE

- **Geliştirme Ortamı:** Arduino IDE
- **Programlama Dili:** Arduino C++ (ESP8266 Arduino Core)
- **Haberleşme:**
  - Gate ESP'ye **Modbus TCP Client** (raw TCP soket, kütüphanesiz)
  - Kullanıcıya **HTTP Web Server** (joystick arayüzü)
- **Temel İşlev:** Motor kontrolü, mesafe algılama, gate request/passed akışı

### 4.3 PC GUI / VS Code veya Cursor

- **Geliştirme Ortamı:** VS Code / Cursor
- **Programlama Dili:** Python 3.10+
- **Framework:** PySide6
- **Haberleşme:** pymodbus üzerinden Modbus TCP Client
- **Temel İşlev:** Operatör paneli — durum gösterimi, komut gönderimi

#### Gerekli Python Paketleri

```bash
pip install PySide6 pymodbus
```

---

## 5. OpenPLC Gate Ladder State Machine

Gate ESP8266 üzerindeki OpenPLC programı, IEC 61131-3 ST (Structured Text) olarak derlenen ama Ladder Diagram ile tasarlanan bir **state machine** çalıştırır. Program döngü süresi 20 ms (`TASK task0 INTERVAL := T#20ms`).

### State Tanımları

#### READY
- Sistem hazır, bekleme modunda.
- `M_READY = TRUE`
- K1 READY rölesi aktif (GPIO5 LOW).
- Servo kapalı konumda (`DUTY = 5.0`).
- Robot geliş bekleniyor.

#### REQUEST
- Jülide kapıya geldi ve geçiş istedi.
- `M_REQUEST = TRUE`
- K2 REQUEST rölesi aktif (GPIO4 LOW).
- Operatör onayı bekleniyor.
- Servo kapalı kalır.

#### PASS_ALLOWED
- GUI üzerinden geçiş izni verildi.
- `M_PASS_ALLOWED = TRUE`
- K3 PASS_ALLOWED rölesi aktif (GPIO14 LOW).
- Servo açık konuma geçer (`DUTY = 7.5`).
- Jülide geçebilir.

#### EMERGENCY
- Acil durum aktif.
- `M_EMERGENCY = TRUE`
- K4 EMERGENCY rölesi aktif (GPIO12 LOW).
- Tüm diğer state'ler sıfırlanır.
- Robot durmalıdır.

### State Geçiş Diyagramı

```
          ┌─────────────────────────────────┐
          │                                 │
          ▼                                 │ CMD_RESET
        READY ◄────────── CMD_ROBOT_PASSED ──┘
          │
          │ CMD_ROBOT_REQUEST
          ▼
        REQUEST
          │
          │ CMD_HMI_ALLOW
          ▼
      PASS_ALLOWED
          │
          │ CMD_ROBOT_PASSED
          ▼
        READY

   (Herhangi bir state'den)
          │
          │ CMD_EMERGENCY
          ▼
       EMERGENCY
          │
          │ CMD_RESET
          ▼
        READY
```

### State Geçiş Koşulları

| Tetikleyici | Önceki State | Sonraki State |
|---|---|---|
| `CMD_ROBOT_REQUEST` | READY | REQUEST |
| `CMD_HMI_ALLOW` | REQUEST | PASS_ALLOWED |
| `CMD_ROBOT_PASSED` | PASS_ALLOWED | READY |
| `CMD_EMERGENCY` | Herhangi | EMERGENCY |
| `CMD_RESET` | Herhangi | READY |

### Program Kaynak Kodu (Özet — program.st)

```pascal
PROGRAM main
  VAR
    M_READY          : BOOL := True;
    M_REQUEST        : BOOL := False;
    M_PASS_ALLOWED   : BOOL := False;
    M_EMERGENCY      : BOOL := False;
    PWM_CONTROLLER0  : PWM_CONTROLLER;
    PWM_CONTROLLER1  : PWM_CONTROLLER;
    PWM_CONTROLLER2  : PWM_CONTROLLER;
    SERVO_CHANNEL    : SINT := 13;
    SERVO_FREQ       : REAL := 50.0;
    SERVO_DUTY_CLOSED: REAL := 5.0;
    SERVO_DUTY_OPEN  : REAL := 7.5;
  END_VAR
  VAR
    Q_READY          AT %QX0.0 : BOOL;   (* coil 0 — K1 *)
    Q_REQUEST        AT %QX0.1 : BOOL;   (* coil 1 — K2 *)
    Q_PASS_ALLOWED   AT %QX0.2 : BOOL;   (* coil 2 — K3 *)
    Q_EMERGENCY      AT %QX0.3 : BOOL;   (* coil 3 — K4 *)
    STATUS_READY     AT %QX0.4 : BOOL;   (* coil 4 *)
    STATUS_REQUEST   AT %QX0.5 : BOOL;   (* coil 5 *)
    STATUS_PASS_ALLOWED AT %QX0.6 : BOOL;(* coil 6 *)
    STATUS_EMERGENCY AT %QX0.7 : BOOL;   (* coil 7 *)
    CMD_ROBOT_REQUEST AT %QX1.0 : BOOL;  (* coil 8  — robot request *)
    CMD_HMI_ALLOW    AT %QX1.1 : BOOL;   (* coil 9  — GUI allow *)
    CMD_ROBOT_PASSED AT %QX1.2 : BOOL;   (* coil 10 — robot passed *)
    CMD_EMERGENCY    AT %QX1.3 : BOOL;   (* coil 11 — emergency *)
    CMD_RESET        AT %QX1.4 : BOOL;   (* coil 12 — reset *)
  END_VAR

  (* State transitions — Ladder mantığının ST karşılığı *)
  IF CMD_ROBOT_REQUEST AND M_READY THEN
    M_REQUEST := TRUE;
    M_READY   := FALSE;
  END_IF;
  IF CMD_HMI_ALLOW AND M_REQUEST THEN
    M_PASS_ALLOWED := TRUE;
    M_REQUEST      := FALSE;
  END_IF;
  IF CMD_ROBOT_PASSED AND M_PASS_ALLOWED THEN
    M_READY        := TRUE;
    M_PASS_ALLOWED := FALSE;
  END_IF;
  IF CMD_EMERGENCY THEN
    M_EMERGENCY    := TRUE;
    M_READY        := FALSE;
    M_REQUEST      := FALSE;
    M_PASS_ALLOWED := FALSE;
  END_IF;
  IF CMD_RESET THEN
    M_READY        := TRUE;
    M_REQUEST      := FALSE;
    M_PASS_ALLOWED := FALSE;
    M_EMERGENCY    := FALSE;
  END_IF;

  (* Active-low relay outputs *)
  Q_READY        := NOT(M_READY);
  Q_REQUEST      := NOT(M_REQUEST);
  Q_PASS_ALLOWED := NOT(M_PASS_ALLOWED);
  Q_EMERGENCY    := NOT(M_EMERGENCY);

  (* Status coils for monitoring *)
  STATUS_READY        := M_READY;
  STATUS_REQUEST      := M_REQUEST;
  STATUS_PASS_ALLOWED := M_PASS_ALLOWED;
  STATUS_EMERGENCY    := M_EMERGENCY;

  (* Servo PWM control *)
  PWM_CONTROLLER0(EN := M_READY,        CHANNEL := SERVO_CHANNEL,
                  FREQ := SERVO_FREQ,   DUTY := SERVO_DUTY_CLOSED);
  PWM_CONTROLLER1(EN := M_PASS_ALLOWED, CHANNEL := SERVO_CHANNEL,
                  FREQ := SERVO_FREQ,   DUTY := SERVO_DUTY_OPEN);
  PWM_CONTROLLER2(EN := CMD_ROBOT_PASSED, CHANNEL := SERVO_CHANNEL,
                  FREQ := SERVO_FREQ,   DUTY := SERVO_DUTY_CLOSED);
END_PROGRAM
```

---

## 6. Modbus TCP Coil Haritası

Gerçek donanım üzerinde test edilerek doğrulanmış adres haritası. Yüksek adres aralıkları (`%QX80.x` → coil 640+) ESP8266 OpenPLC target'ında çalışmadı; aşağıdaki düşük adres aralığı kullanıldı.

### Fiziksel Röle Çıkışları (Active-Low)

| Değişken | IEC Adresi | Coil | Röle | GPIO |
|---|---|---|---|---|
| `Q_READY` | `%QX0.0` | 0 | K1 READY | GPIO5 / D1 |
| `Q_REQUEST` | `%QX0.1` | 1 | K2 REQUEST | GPIO4 / D2 |
| `Q_PASS_ALLOWED` | `%QX0.2` | 2 | K3 PASS_ALLOWED | GPIO14 / D5 |
| `Q_EMERGENCY` | `%QX0.3` | 3 | K4 EMERGENCY | GPIO12 / D6 |

> Bu coil'ler active-low mantığı yüzünden ters okumak gerekir. K1 READY aktifken `Q_READY` coil'inin değeri **FALSE**'tur. GUI bu değerleri `NOT(bit)` ile gösterir.

### Status Bitleri (Doğrudan Okunabilir)

| Değişken | IEC Adresi | Coil | Anlam |
|---|---|---|---|
| `STATUS_READY` | `%QX0.4` | 4 | Sistem READY durumunda |
| `STATUS_REQUEST` | `%QX0.5` | 5 | Robot geçiş bekliyor |
| `STATUS_PASS_ALLOWED` | `%QX0.6` | 6 | Geçiş izni verildi |
| `STATUS_EMERGENCY` | `%QX0.7` | 7 | Acil durum aktif |

> GUI ve Jülide durumu okumak için bu 4-7 arası coil'leri kullanır; active-low dönüşümü gerekmez.

### Komut Bitleri (Pulse Mantığı)

| Değişken | IEC Adresi | Coil | Kim Gönderir | Açıklama |
|---|---|---|---|---|
| `CMD_ROBOT_REQUEST` | `%QX1.0` | 8 | Jülide / GUI | Robot geçiş istiyor |
| `CMD_HMI_ALLOW` | `%QX1.1` | 9 | GUI | Operatör geçiş izni verdi |
| `CMD_ROBOT_PASSED` | `%QX1.2` | 10 | Jülide / GUI | Robot geçişi tamamladı |
| `CMD_EMERGENCY` | `%QX1.3` | 11 | GUI / Jülide | Acil durum tetikle |
| `CMD_RESET` | `%QX1.4` | 12 | GUI | Sistemi READY'ye sıfırla |

### Pulse Kullanımı

Komut bitleri sürekli yüksek tutulmaz; kısa pulse gönderilir:

```
1. Coil → TRUE yaz
2. ~300 ms bekle
3. Coil → FALSE yaz
```

PLC, 20 ms scan döngüsünde bu biti görüp state geçişini yapar. TRUE'da kalırsa her scan'de tekrar tetikler — istenmeyen durum.

Örnek pulse süreleri:
- `CMD_ROBOT_REQUEST` → 200 ms
- `CMD_HMI_ALLOW` → 1000 ms (Allow kesin okunmalı)
- `CMD_ROBOT_PASSED` → 300 ms
- `CMD_EMERGENCY` → 300 ms
- `CMD_RESET` → 300 ms

### Pymodbus ile Kullanım Örneği

```python
from pymodbus.client import ModbusTcpClient
import time

client = ModbusTcpClient("192.168.137.218", port=502, timeout=3.0)
client.connect()

# Robot Request pulse
client.write_coil(address=8, value=True, device_id=0)
time.sleep(0.3)
client.write_coil(address=8, value=False, device_id=0)

# Status oku
result = client.read_coils(address=4, count=4, device_id=0)
bits = result.bits
print(f"READY={bits[0]}  REQUEST={bits[1]}  PASS_ALLOWED={bits[2]}  EMERGENCY={bits[3]}")

client.close()
```

---

## 7. Servo Kontrol Mantığı

### Neden Normal Digital Output Yetmez?

SG90 servo motoru **50 Hz PWM** sinyali ister. Pulse genişliği ile konum belirlenir:

| Durum | Duty Cycle | Pulse Genişliği |
|---|---|---|
| Kapalı (CLOSED) | ~5.0% | ~1.0 ms |
| Açık (OPEN) | ~7.5% | ~1.5 ms |

Ladder'da normal bir `%QX` çıkışı dijital ON/OFF üretir; servo bu sinyal tipini anlayamaz.

### OpenPLC PWM_CONTROLLER Bloğu

OpenPLC Editor'ün Arduino Function Blocks kategorisinde `PWM_CONTROLLER` function block'u bulunur:

```
PWM_CONTROLLER
  EN      : BOOL   — etkinleştir
  CHANNEL : SINT   — GPIO numarası
  FREQ    : REAL   — frekans (Hz)
  DUTY    : REAL   — duty cycle (%)
  ─────────────────
  ENO     : BOOL   — çıkış aktif
  SUCCESS : BOOL   — başarı bayrağı
```

### Derleme Hatası ve Çözümü

İlk compile denemesinde şu hata alındı:

```
undefined reference to `set_hardware_pwm`
```

Bu, `PWM_CONTROLLER` bloğunun çağırdığı `set_hardware_pwm()` fonksiyonunun ESP8266 Arduino core'da tanımlı olmadığını gösterdi. Standart Arduino target (Uno, Mega) için olan implementasyon ESP8266'ya geçişte eksik kaldı.

**Çözüm:** OpenPLC build klasörüne özel bir patch dosyası eklendi:

**`gate/build/ESP8266 NodeMCU/examples/Baremetal/openplc_esp8266_pwm_patch.cpp`**

```cpp
extern "C" uint8_t set_hardware_pwm(uint8_t channel, float freq, float duty)
{
    // ESP8266 Arduino core PWM API
    analogWriteRange(100);                     // duty 0-100 arası
    analogWriteFreq((uint32_t)freq);           // 50 Hz servo için
    uint32_t duty_int = (uint32_t)(duty);      // örn. 5 veya 7 (%)
    analogWrite(channel, duty_int);
    return 1;  // SUCCESS
}
```

Bu patch `Baremetal.ino` ile aynı klasörde bulunduğundan Arduino IDE otomatik olarak derlemeye dahil eder.

### Ladder'daki Üç PWM Komutu

```
M_READY (BOOL)
  └─► PWM_CONTROLLER0 ─► EN=M_READY
                          CHANNEL=13, FREQ=50.0, DUTY=5.0  (CLOSED)

M_PASS_ALLOWED (BOOL)
  └─► PWM_CONTROLLER1 ─► EN=M_PASS_ALLOWED
                          CHANNEL=13, FREQ=50.0, DUTY=7.5  (OPEN)

CMD_ROBOT_PASSED (BOOL)
  └─► PWM_CONTROLLER2 ─► EN=CMD_ROBOT_PASSED
                          CHANNEL=13, FREQ=50.0, DUTY=5.0  (CLOSED)
```

### Neden Üç Ayrı PWM Komutu?

İlk denemede yalnızca şu mantık kurulmuştu:
- `M_PASS_ALLOWED = TRUE` → servo aç
- `M_PASS_ALLOWED = FALSE` → servo kapat

Bu yaklaşımda, `M_PASS_ALLOWED` FALSE'a döndükten sonra servo için hiçbir aktif PWM sinyali üretilmedi. Bazı servo modelleri son alınan konumda kaldı; bazıları sinyalsiz kaldığında titreşti.

Çalışan çözüm: geçiş tamamlanır tamamlanmaz `CMD_ROBOT_PASSED` pulse'u sırasında servo'ya açıkça CLOSED komutu verilmesi.

```
Sistem başlangıcı / READY  →  SERVO CLOSED  (M_READY aktifken)
PASS_ALLOWED               →  SERVO OPEN    (M_PASS_ALLOWED aktifken)
CMD_ROBOT_PASSED gelince   →  SERVO CLOSED  (CMD_ROBOT_PASSED pulse'u sırasında)
```

---

## 8. Jülide Robot Çalışma Mantığı

### Başlangıç

1. ESP8266 açılır, `PLC_GATE_CTRL` Wi-Fi ağına bağlanır.
2. Serial Monitor'da Jülide'nin aldığı IP adresi görüntülenir.
3. HTTP web sunucusu başlatılır — tarayıcıdan `http://<JULIDE_IP>/` ile açılır.
4. Gate modu varsayılan olarak **kapalı** başlar (güvenli başlangıç).

### Web Joystick Arayüzü

Jülide, kendi HTTP web sunucusu üzerinden bir joystick arayüzü sunar:

| Endpoint | Metot | Açıklama |
|---|---|---|
| `/` | GET | Ana joystick sayfası (HTML) |
| `/api/move?cmd=f` | GET | İleri |
| `/api/move?cmd=b` | GET | Geri |
| `/api/move?cmd=l` | GET | Sol dön |
| `/api/move?cmd=r` | GET | Sağ dön |
| `/api/move?cmd=s` | GET | Dur |
| `/api/status` | GET | Jülide durumu (JSON) |
| `/api/gate_mode?enabled=1` | GET | Gate modu aç |
| `/api/gate_mode?enabled=0` | GET | Gate modu kapat |

### Motor Kontrolü

L298N motor sürücü üzerinden 4 TT motor kontrol edilir. PWM hız kontrolü ENA/ENB pinleri üzerinden yapılır.

```
forward()   → IN1=HIGH, IN2=LOW, IN3=HIGH, IN4=LOW
backward()  → IN1=LOW,  IN2=HIGH, IN3=LOW,  IN4=HIGH
turnLeft()  → sol motorlar geri, sağ motorlar ileri
turnRight() → sol motorlar ileri, sağ motorlar geri
stopMotors()→ tüm IN'ler LOW
```

### HC-SR04 Mesafe Mantığı

| Mesafe | Eylem |
|---|---|
| > 10 cm | Normal hız, gate olmadan git |
| 10 cm - 5 cm | Hız düşürülür (yavaş yaklaşım) |
| < 5 cm | Dur, gate request tetikle |

### Gate Geçiş Akışı

```
1. Kullanıcı Jülide'yi ileri sürer (joystick veya otonom)
2. HC-SR04 → 10 cm altı: hız düşür
3. HC-SR04 → 5 cm altı: dur
4. Gate Mode açıksa:
   a. OpenPLC'ye CMD_ROBOT_REQUEST (coil 8) pulse gönder
   b. K2 REQUEST rölesi aktif (GUI'de REQUEST gösterir)
5. PLC poll döngüsünde (800 ms aralık) STATUS_PASS_ALLOWED (coil 6) okunur
6. STATUS_PASS_ALLOWED = TRUE olunca:
   a. Servo açılmıştır
   b. Jülide ileri gider (3000 ms)
7. Geçiş süresi dolunca CMD_ROBOT_PASSED (coil 10) pulse gönder
8. Servo kapanır, sistem READY'ye döner
```

### Jülide'nin Kullandığı Coil'ler

| Coil | Numara | Amaç |
|---|---|---|
| `CMD_ROBOT_REQUEST` | 8 | Gate'e geçiş isteği gönder |
| `STATUS_PASS_ALLOWED` | 6 | Geçiş izni var mı? (poll) |
| `STATUS_EMERGENCY` | 7 | Emergency aktif mi? (poll) |
| `CMD_ROBOT_PASSED` | 10 | Geçiş tamamlandı bildir |

### Jülide'nin Modbus İletişimi

Jülide, harici Modbus kütüphanesi kullanmaz. Raw TCP soketi üzerinden Modbus TCP paketleri elle oluşturulur:

```cpp
// Function Code 01 — Read Coils
// Function Code 05 — Write Single Coil

WiFiClient modbusClient;
modbusClient.connect(PLC_IP, PLC_PORT);

// FC05 Write coil 8 = TRUE
byte request[] = {
  0x00, 0x01,  // Transaction ID
  0x00, 0x00,  // Protocol ID
  0x00, 0x06,  // Length
  0x00,        // Unit ID
  0x05,        // FC05
  0x00, 0x08,  // Coil address 8
  0xFF, 0x00   // Value TRUE
};
modbusClient.write(request, sizeof(request));
```

---

## 9. GUI / HMI Çalışma Mantığı

### Teknoloji

- **Python 3.10+**
- **PySide6** — Qt6 tabanlı GUI framework
- **pymodbus** — Modbus TCP client
- **QTimer** — non-blocking polling ve pulse kontrolü

### Arayüz Bileşenleri

```
┌────────────────────────────────────────────────────┐
│  OpenPLC Factory Gate HMI — Jülide Robot           │
│  [Gate IP: 192.168.137.218:502]   [CONNECTED]      │
├────────────────────────────────────────────────────┤
│  DURUM: READY │ K1●  K2○  K3○  K4○               │
│  [====Barrier Widget====]                          │
├────────────────────────────────────────────────────┤
│  [ALLOW]  [EMERGENCY]  [RESET]                     │
│  [Sim: Robot Request]  [Sim: Robot Passed]          │
├────────────────────────────────────────────────────┤
│  Log:                                              │
│  12:34:01  STATE: READY                            │
│  12:34:05  CMD: ALLOW sent                         │
│  12:34:05  STATE: PASS_ALLOWED                     │
└────────────────────────────────────────────────────┘
```

### GUI'nin Gönderdiği Komutlar

| Buton | Coil | Pulse Süresi |
|---|---|---|
| Allow | 9 (`CMD_HMI_ALLOW`) | 1000 ms |
| Emergency | 11 (`CMD_EMERGENCY`) | 300 ms |
| Reset | 12 (`CMD_RESET`) | 300 ms |
| Sim: Robot Request | 8 (`CMD_ROBOT_REQUEST`) | 300 ms |
| Sim: Robot Passed | 10 (`CMD_ROBOT_PASSED`) | 300 ms |

### GUI'nin Okuduğu Statuslar

| Coil | Numara | GUI'de Gösterimi |
|---|---|---|
| `STATUS_READY` | 4 | Yeşil READY etiketi |
| `STATUS_REQUEST` | 5 | Sarı REQUEST etiketi |
| `STATUS_PASS_ALLOWED` | 6 | Mavi PASS_ALLOWED etiketi |
| `STATUS_EMERGENCY` | 7 | Kırmızı EMERGENCY etiketi |

### Polling Döngüsü

GUI, `QTimer` ile 500 ms aralıkla status coil'lerini okur:

```python
self.poll_timer = QTimer(self)
self.poll_timer.setInterval(500)  # ms
self.poll_timer.timeout.connect(self._on_poll)
```

Her 10 tick'te (5 saniyede) bir yeniden bağlantı denemesi yapılır.

### Non-Blocking Pulse Gönderimi

GUI'de komut butonuna basınca bloklama olmaması için `QTimer.singleShot` kullanılır:

```python
def _send_allow(self):
    self.client.write_coil(COIL_CMD_HMI_ALLOW, True)
    QTimer.singleShot(1000, lambda: self.client.write_coil(COIL_CMD_HMI_ALLOW, False))
```

### Bağlantı Yönetimi

GUI, Modbus bağlantısını her komut işlemi için kısa tutacak şekilde tasarlanmıştır:

```
connect → read/write → close
```

Bu yöntem şu sorunu çözdü: GUI OpenPLC soketi uzun süre açık tuttuğunda, Jülide'nin aynı OpenPLC'ye bağlantı açması başarısız oluyordu. Kısa bağlantı sayesinde hem GUI hem de Jülide aynı Modbus TCP server'a erişebilir.

---

## 10. Karşılaşılan Hatalar ve Çözümler

### Sorun 1: Gate ESP Arduino HTTP tabanlıydı — Ladder değil

**Belirti:** Gate ESP HTTP endpoint ile çalışıyordu (`/robot/request`, `/hmi/allow`). Bu yapı endüstriyel PLC mantığından uzak ve proje kapsamına uygun değil.

**Çözüm:** Gate ESP tamamen OpenPLC Editor ile yeniden tasarlandı. HTTP endpoint'ler kaldırıldı. Ladder Diagram yazıldı. Haberleşme Modbus TCP coil tabanlı hale getirildi.

---

### Sorun 2: Röleler ters çalışıyordu

**Belirti:** READY durumunda K1 yerine K2, K3, K4 yanıyordu. Beklenen röle aktif değildi.

**Sebep:** Kullanılan 4 kanal röle modülü active-low çalışıyor. GPIO LOW olunca röle çeker.

**Çözüm:** Ladder'da tüm fiziksel Q çıkışları terslenmiş contact ile kuruldu:

```pascal
Q_READY        := NOT(M_READY);
Q_REQUEST      := NOT(M_REQUEST);
Q_PASS_ALLOWED := NOT(M_PASS_ALLOWED);
Q_EMERGENCY    := NOT(M_EMERGENCY);
```

---

### Sorun 3: Modbus adresleri 640/648 çalışmadı

**Belirti:** Python test scriptinde `exception_code=2` (Illegal Data Address) hatası.

**Sebep:** OpenPLC varsayılan değişken adres aralığı `%QX80.0` → coil 640 gibi yüksek adreslere işaret ediyordu. ESP8266 OpenPLC target bu adresleri register'larda tutmuyor ya da mapping farklıydı.

**Çözüm:** Düşük adres aralığı (`%QX0.0` başlangıcı) kullanıldı. Gerçek donanım üzerinde test yapılarak çalışan coil numaraları belirlendi: Q çıkışları 0-3, status 4-7, command 8-12.

---

### Sorun 4: pymodbus Unit ID uyuşmazlığı

**Belirti:**
```
request ask for id=1 but got id=0
```

**Sebep:** OpenPLC ESP8266 Modbus slave'i Unit ID 0 ile yanıt veriyor. Python client varsayılan olarak device_id=1 gönderiyordu.

**Çözüm:**

```python
client = ModbusTcpClient("192.168.137.218", port=502)
result = client.read_coils(address=4, count=4, device_id=0)  # device_id=0
```

---

### Sorun 5: Jülide Modbus kütüphanesi bağlantısı kararsızdı

**Belirti:** Arduino için `ModbusIP_ESP8266` veya benzeri kütüphaneler ile bağlantı kurulamıyordu ya da paket formatı tutarsızdı.

**Çözüm:** Harici Modbus kütüphanesi tamamen kaldırıldı. Raw TCP soket üzerinden Modbus Application Protocol (MBAP) header ve FC01/FC05 paketleri elle yazıldı. Bu sayede bağımlılık ortadan kalktı ve davranış öngörülebilir hale geldi.

---

### Sorun 6: Web joystick otomatik duruyordu — kötü sürüş hissi

**Belirti:** Joystick butonu bırakılınca veya belirli timeout sonrasında motor duruyordu. Operatör sürekli buton tutmak zorunda kalıyordu.

**Çözüm:** Otomatik motor durdurma timeout kaldırıldı. Eski davranış geri getirildi: yön komutu verilince motor o yönde devam eder, Stop komutuna kadar çalışır.

---

### Sorun 7: GUI Modbus bağlantısını sürekli tutunca Jülide bağlanamıyordu

**Belirti:** GUI çalışırken Jülide'nin OpenPLC'ye Modbus bağlantısı açılmıyordu. "Socket could not be opened" hatası alınıyordu.

**Sebep:** OpenPLC ESP8266, aynı anda çok sayıda TCP bağlantısını yönetmekte zorlandı. GUI soketi açık tuttuğunda yeni bağlantı için kaynak kalmıyordu.

**Çözüm:** GUI tarafında her işlemden sonra bağlantı kapatıldı:

```python
client.connect()
client.read_status()
client.disconnect()  # hemen kapat
```

Ayrıca polling aralığı artırıldı, gereksiz sürekli okuma ortadan kalktı.

---

### Sorun 8: Servo hiç çalışmıyordu

**Belirti:** State'ler doğru değişiyor, röleler doğru yanıp sönüyor, ama servo motor hiç hareket etmiyordu.

**Sebep:** Ladder programında servo için PWM komutu yoktu. Sadece röle dijital çıkışları vardı.

**Çözüm:** OpenPLC Editor'de Arduino Function Blocks altındaki `PWM_CONTROLLER` function block'u Ladder'a eklendi. CHANNEL=13 (GPIO13/D7), FREQ=50.0, DUTY değişkenlerine bağlandı.

---

### Sorun 9: PWM_CONTROLLER derleme hatası

**Belirti:**

```
undefined reference to `set_hardware_pwm`
```

**Sebep:** `PWM_CONTROLLER` bloğu ESP8266 Arduino core'da tanımlı olmayan `set_hardware_pwm()` fonksiyonunu çağırıyordu.

**Çözüm:** Build klasörüne `openplc_esp8266_pwm_patch.cpp` adlı dosya eklendi. Bu dosyada `set_hardware_pwm()` fonksiyonu ESP8266 Arduino API'leri (`analogWriteRange`, `analogWriteFreq`, `analogWrite`) kullanılarak tanımlandı. Arduino IDE bu dosyayı otomatik derlemeye dahil etti.

---

### Sorun 10: Servo geçiş sonrası kapanmıyordu

**Belirti:** Robot geçtikten sonra servo açık pozisyonda kaldı.

**Sebep:** `NOT(M_PASS_ALLOWED)` ile servo kapatma mantığı kurulmuştu. Ancak `M_PASS_ALLOWED` FALSE olunca hiçbir aktif PWM komutu üretilmedi; servo önceki konumunda kaldı.

**Çözüm:** Üç ayrı PWM komutu ile açık, kapalı ve geçiş sonrası kapalı durumları ayrıca tanımlandı. `CMD_ROBOT_PASSED` pulse'u sırasında servo'ya açıkça CLOSED komutu gönderildi.

---

## 11. Kurulum ve Çalıştırma

### A. PC Hotspot Hazırlığı

1. Windows Ayarları → Ağ → Mobil Hotspot.
2. SSID: `PLC_GATE_CTRL`
3. Şifre: `12345678`
4. Hotspot'u aç.

### B. Gate ESP8266 / OpenPLC Kurulumu

```
1. OpenPLC Editor'ü yükle (openplcproject.com).
2. gate/ klasöründeki projeyi aç (project.json).
3. Target: ESP8266 NodeMCU seç.
4. Modbus TCP: Enable.
5. Wi-Fi SSID = "PLC_GATE_CTRL", Password = "12345678" gir.
6. Pin mapping:
     D1 (GPIO5)  → Q_READY        (coil 0)
     D2 (GPIO4)  → Q_REQUEST      (coil 1)
     D5 (GPIO14) → Q_PASS_ALLOWED (coil 2)
     D6 (GPIO12) → Q_EMERGENCY    (coil 3)
     D7 (GPIO13) → Servo Signal (PWM)
7. openplc_esp8266_pwm_patch.cpp dosyasının
   gate/build/ESP8266 NodeMCU/examples/Baremetal/ klasöründe
   olduğunu kontrol et.
8. Compile + Upload yap.
9. Serial Monitor'da "OpenPLC Started" ve IP adresini gör.
10. Başlangıçta K1 READY yanmalı, servo kapalı olmalı.
```

### C. Jülide Robot Kurulumu

```
1. Arduino IDE'yi aç. Board: LOLIN(WEMOS) D1 R2 & mini
   veya NodeMCU 1.0 (ESP-12E Module).
2. Arduino-ide/julide.ino dosyasını aç.
3. Şu sabitleri kontrol et / güncelle:
     const char* WIFI_SSID = "PLC_GATE_CTRL";
     const char* WIFI_PASS = "12345678";
     IPAddress PLC_IP(192, 168, 137, 218);  // Gate ESP IP'si
4. Upload et.
5. Serial Monitor (115200 baud) açık, Jülide'nin IP adresini al.
6. Tarayıcıdan http://<JULIDE_IP>/ adresini aç.
7. Joystick arayüzü yüklenmeli.
```

### D. PC GUI Kurulumu

```bash
# Python 3.10+ gerekli
cd c:\plc_gui

pip install PySide6 pymodbus

# Gate IP'yi güncelle (app/modbus_client.py veya main_window.py)
# host = "192.168.137.218"  ← Gate ESP IP

python main.py
```

GUI açılınca:
- Gate IP / port alanını güncelle.
- Connect butonu ile bağlan.
- READY durumu görünmeli.

---

## 12. Test Senaryosu

Tam sistem testi için adım adım prosedür:

### Adım 1 — Gate Başlatma
- Gate ESP güç verilir.
- K1 READY rölesi aktif olur (LED yanar).
- Servo kapalı konumda.
- GUI'de `STATUS_READY = TRUE` görünür.

### Adım 2 — Jülide Başlatma
- Jülide ESP güç verilir.
- `PLC_GATE_CTRL` ağına bağlanır.
- Web joystick tarayıcıdan erişilebilir olur.
- GUI bağlantı bilgisini loglar.

### Adım 3 — Robot Kapıya Yaklaşma
- Joystick ile Jülide ileri yönlendirilir.
- HC-SR04 10 cm altında hızı düşürür.
- HC-SR04 5 cm altında durur.
- Gate Mode açıksa `CMD_ROBOT_REQUEST` (coil 8) pulse gönderilir.
- K2 REQUEST rölesi aktif.
- GUI'de `STATUS_REQUEST = TRUE`, durum REQUEST.

### Adım 4 — Operatör İzin Verme
- GUI'de **ALLOW** butonuna basılır.
- `CMD_HMI_ALLOW` (coil 9) 1000 ms pulse.
- K3 PASS_ALLOWED rölesi aktif.
- Servo açılır.
- GUI'de `STATUS_PASS_ALLOWED = TRUE`.

### Adım 5 — Robot Geçişi
- Jülide `STATUS_PASS_ALLOWED` TRUE görür.
- Motor ileri kalkar, robot kapıdan geçer (~3 sn).
- Geçiş tamamlanınca `CMD_ROBOT_PASSED` (coil 10) pulse.
- K1 READY rölesi aktif.
- Servo kapanır.
- Sistem READY'ye döner.

### Adım 6 — Emergency Testi
- GUI'de **EMERGENCY** butonuna basılır.
- K4 EMERGENCY rölesi aktif.
- `STATUS_EMERGENCY = TRUE`.
- Jülide `STATUS_EMERGENCY` TRUE görünce durur.

### Adım 7 — Reset Testi
- GUI'de **RESET** butonuna basılır.
- `CMD_RESET` (coil 12) pulse.
- Sistem READY'ye döner.
- K1 READY tekrar aktif.

### Adım 8 — GUI Simülasyon Testi
GUI üzerindeki "Sim: Robot Request" ve "Sim: Robot Passed" butonları, Jülide olmadan tam akışı test etmek için kullanılır:

```
[Sim: Robot Request] → coil 8 pulse → REQUEST durumu
[ALLOW]              → coil 9 pulse → PASS_ALLOWED, servo açılır
[Sim: Robot Passed]  → coil 10 pulse → READY, servo kapanır
```

---

## 13. Repo Klasör Yapısı

```
c:\plc_gui\
│
├── gate/                          # OpenPLC gate projesi
│   ├── project.json               # OpenPLC Editor proje konfigürasyonu
│   └── build/
│       ├── ESP8266 NodeMCU/       # ESP8266 hedef için derleme çıktıları
│       │   ├── examples/Baremetal/
│       │   │   ├── Baremetal.ino             # Ana Arduino giriş noktası
│       │   │   ├── c_blocks_code.cpp         # Ladder ST → C++ çevirisi
│       │   │   └── openplc_esp8266_pwm_patch.cpp  # Servo PWM patch (!)
│       │   └── src/
│       │       └── program.st                # Ladder kaynak kodu (ST)
│       └── OpenPLC Simulator/     # PC simülatör için derleme çıktıları
│
├── Arduino-ide/                   # Jülide robot firmware
│   └── julide.ino                 # ESP8266 Arduino C++ robot kodu
│
├── app/                           # PySide6 GUI uygulaması
│   ├── modbus_client.py           # OpenPLCModbusClient — tüm Modbus işlemleri
│   ├── config.py                  # Uygulama konfigürasyonu
│   ├── styles.py                  # Qt stylesheet
│   ├── state_model.py             # State model
│   ├── plc_client.py              # PLC client wrapper
│   ├── ui/
│   │   ├── main_window.py         # Ana pencere — polling, butonlar, log
│   │   ├── control_panel.py       # Kontrol paneli
│   │   ├── dashboard.py           # Dashboard görünümü
│   │   ├── widgets.py             # BarrierWidget, StatusCard
│   │   ├── alarm_panel.py         # Alarm paneli
│   │   ├── log_panel.py           # Log paneli
│   │   ├── ladder_view.py         # Ladder diagram görünümü
│   │   ├── io_panel.py            # I/O panel
│   │   ├── process_view.py        # Proses görünümü
│   │   ├── settings_panel.py      # Ayarlar paneli
│   │   └── diagnostics_panel.py   # Diagnostics paneli
│   └── core/
│       ├── plc_engine.py          # PLC motor mantığı
│       ├── state_machine.py       # State machine
│       ├── protocol.py            # Protokol tanımları
│       ├── io_model.py            # I/O modeli
│       ├── event_logger.py        # Olay kayıt sistemi
│       ├── serial_client.py       # Seri port client (opsiyonel)
│       └── simulator.py           # Simülasyon modu
│
├── tools/                         # Test ve yardımcı araçlar
│   └── fake_esp_plc_serial.py     # Sahte ESP PLC seri port simülatörü
│
├── main.py                        # GUI giriş noktası
├── test_openplc_modbus.py         # Modbus bağlantı test scripti
└── README.md                      # Bu dosya
```

---

## 14. Güvenlik Notları

- **Motor testi:** İlk testlerde robot tekerlekleri yerden kaldırılarak havada test yapılmalıdır. Beklenmedik motor davranışlarında kaza riski azalır.

- **Ortak GND:** ESP8266 GND, L298N motor sürücü GND, servo GND ve röle modülü GND aynı hatta bağlanmalıdır. Farklı GND referansı iletişim hatalarına ve hasar riskine yol açar.

- **Güç hattı ayrımı:** Servo ve motor L298N'den aynı güç hattından besleniyorsa voltaj düşümü yaşanabilir. Motor ani yük çekişi ESP8266'yı resetleyebilir. Mümkünse servo için ayrı güç hattı kullanılmalıdır.

- **Active-low röle mantığı:** Röle modülünün active-low olduğu her zaman akılda tutulmalıdır. Program başlarken veya ESP resetlendiğinde GPIO'lar pull-up durumuna geçebilir; bu durumda tüm röleler kapanır (pasif). Bu davranış için fail-safe varsayılan değerler Ladder'da ayarlanmıştır.

- **Emergency komutu:** Jülide'nin `STATUS_EMERGENCY` değerini düzenli poll etmesi gerekir. Emergency aktifken robot her durumda durmalıdır. Bağlantı kesilirse robot da durmalıdır (fail-safe).

- **Ağ güvenliği:** Modbus TCP, kimlik doğrulama veya şifreleme içermez. Bu sistem yalnızca izole yerel ağ (`PLC_GATE_CTRL`) üzerinde çalışır. İnternet erişimi olan ağlarda veya üretim ortamında VPN, güvenlik duvarı veya Modbus güvenlik katmanı eklenmelidir.

- **Tek Modbus client varsayımı:** OpenPLC ESP8266 aynı anda çok sayıda eş zamanlı Modbus bağlantısını yönetemez. GUI ve Jülide'nin aynı anda bağlantı açmaması için kısa bağlantı (connect/write/close) modeli kullanılmıştır. Eş zamanlı erişim gerekirse bağlantı arbitrasyon mekanizması eklenmelidir.

---

## 15. Lessons Learned

Bu proje boyunca karşılaşılan teknik sorunlar ve kazanılan deneyimler:

### 1. OpenPLC'de Adres Aralığı Platformdan Platforma Değişir

Yüksek `%QX80.x` adreslerinin desktop target'ta çalışması, ESP8266 target'ta çalışacağı anlamına gelmez. Her target için gerçek donanım üzerinde test yapılmalıdır. Simülatör ve fiziksel ESP'nin Modbus haritaları uyuşmayabilir.

### 2. Active-Low Çıkışlar Ladder Tasarımını Doğrudan Etkiler

Donanımın active-low olduğu Ladder tasarım aşamasında göz önünde bulundurulmazsa, tüm çıkışlar ters çalışır. Fiziksel Q çıkışları `NOT()` ile çevrilmek yerine durum bitleri (`STATUS_*`) doğrudan okunarak bu karmaşıklık yönetilebilir.

### 3. OpenPLC PWM Desteği Platforma Özgüdür

`PWM_CONTROLLER` function block'u standart OpenPLC kütüphanesinde bulunmasına rağmen, ESP8266 target için gerekli hardware abstraction function'ı eksikti. Kaynak kodunu incelemek ve patch yazmak gerekti. Benzer durumlar diğer target platformlarda da yaşanabilir.

### 4. ESP8266 Tek TCP Bağlantı Kapasitesi Sınırlıdır

ESP8266 üzerinde çalışan OpenPLC, çok sayıda eş zamanlı TCP bağlantısı altında stabil değildir. GUI tasarımında bu kısıt göz önünde bulundurulmazsa, hem GUI hem de robot'un aynı PLC'ye bağlanması çok zor hale gelir. Short-lived connection modeli bu kısıtı aşmak için etkili bir çözümdür.

### 5. Raw Modbus TCP Kütüphane Bağımlılığını Ortadan Kaldırır

Arduino için Modbus kütüphaneleri ESP8266 ile tutarsız davranabilir. MBAP header formatı ve function code'ları anlaşıldığında, raw TCP üzerinden Modbus yazmak beklenenden basittir ve güvenilirliği artırır.

### 6. Pulse Süresi State Machine Stabilitesini Etkiler

Çok kısa pulse (< 100 ms) PLC scan döngüsünde (20 ms) okunmayabilir. Çok uzun pulse ise state'in aynı anda birden fazla kez tetiklenmesine yol açabilir. Özellikle `CMD_HMI_ALLOW` için 1000 ms pulse gerekti — çünkü GUI poll döngüsü ve PLC scan zamanlaması uyuşmazlığı kısa pulse'larda sorun yaratıyordu.

### 7. Servo Kontrolü Aktif Sinyal Gerektirir

Servo motoru belirli bir pozisyonda tutmak için sürekli PWM sinyali gönderilmesi gerekir. "Sinyali kes, konumda kal" mantığı servo türüne göre değişir; bazı servolar sinyalsiz kaldığında titreşir veya pozisyonu kaybeder. Ladder'da her state geçişine servo konum komutu açıkça yazılmalıdır.

---

## 16. Teknik Özet

Bu proje üç katmanlı bir entegrasyon örneği sunar:

**Katman 1 — PLC / Saha:** OpenPLC Editor ile Ladder Diagram olarak programlanmış ESP8266 gate kontrolcüsü. IEC 61131-3 uyumlu state machine, active-low röle çıkışları ve `PWM_CONTROLLER` function block'u ile servo kontrolü. Modbus TCP slave olarak çalışır.

**Katman 2 — Robot:** Arduino IDE ile Arduino C++ olarak yazılmış Jülide mobile robot. L298N üzerinden 4 TT motor, HC-SR04 mesafe sensörü. Gate ESP'ye raw Modbus TCP client olarak bağlanır. Aynı zamanda HTTP web joystick sunucusu çalıştırır.

**Katman 3 — HMI:** PySide6 ile geliştirilmiş operatör arayüzü. pymodbus üzerinden Gate ESP'ye bağlanır. Non-blocking QTimer pulse'ları ile komut gönderir. 500 ms polling ile state gösterir.

Tüm bileşenler Windows Mobile Hotspot üzerinde oluşturulan ortak Wi-Fi ağında haberleşir. Sistem; bir mobile robotun kapıya yaklaşma, geçiş izni isteme, operatör onayı alma, kapıdan geçme ve sistemi bırakma akışını uçtan uca gerçekleştirir.

---

*Geliştirme: VS Code / Cursor — Python + PySide6*
*Gate Firmware: OpenPLC Editor — Ladder Diagram / IEC 61131-3*
*Robot Firmware: Arduino IDE — ESP8266 Arduino C++*
