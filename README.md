# OpenPLC Factory Gate HMI

PySide6 tabanli bu arayuz, ESP8266 OpenPLC kapı kontrolcusunun HMI/SCADA panelidir.
GUI robotu direkt kontrol etmez; sadece OpenPLC kapı kontrol API endpointlerini kullanır.

## Teknoloji

- Python 3.10+
- PySide6
- requests

## Kurulum

```bash
pip install -r requirements.txt
python main.py
```

## OpenPLC ESP Endpointleri

Temel IP: `http://192.168.4.1`

- `GET /status`
- `GET /hmi/allow`
- `GET /hmi/emergency_on`
- `GET /hmi/reset`
- `GET /hmi/manual/open`
- `GET /hmi/manual/close`

## GUI Davranisi

- Polling: her 1000 ms'de `/status` okunur.
- Timeout: HTTP isteklerinde timeout kullanilir (1.0s).
- GUI donmaz: polling QTimer ile, istekler kisa timeout ile yapilir.
- REQUEST durumunda "Geçiş İzni Ver" butonu aktif olur.
- EMERGENCY durumunda izin ver / manuel aç pasif olur, reset aktif kalır.
- Log paneli su olaylari kaydeder:
  - PLC baglandi/koptu
  - state degisimi
  - robot id
  - allow/emergency/reset/manual komutlari
  - HTTP hata/timeout

## Test Sirasi

1. OpenPLC ESP calistirilir.
2. Bilgisayar `PLC_GATE_CTRL` WiFi agina baglanir.
3. GUI acilir.
4. PLC IP `http://192.168.4.1` olarak ayarlanir.
5. Julide robot kapıya gelir ve `/robot/request` gonderir.
6. GUI `REQUEST` durumunu gosterir.
7. Operator `Geçiş İzni Ver` butonuna basar.
8. PLC `PASS_ALLOWED` moduna gecer.
9. Robot gecer ve `/robot/passed` gonderir.
10. PLC `READY` moduna doner.
