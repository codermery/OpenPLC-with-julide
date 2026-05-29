import time
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException

PLC_IP = "192.168.137.209"
PLC_PORT = 502
DEVICE_ID = 0

# Mevcut OpenPLC tablo düzenine göre:
# Q çıkışları     %QX0.0 - %QX0.3  -> coil 0-3
# Status bitleri %QX0.4 - %QX0.7  -> coil 4-7
# Command bitleri %QX1.0 - %QX1.4 -> coil 8-12

Q_READY = 0
Q_REQUEST = 1
Q_PASS_ALLOWED = 2
Q_EMERGENCY = 3

STATUS_READY = 4
STATUS_REQUEST = 5
STATUS_PASS_ALLOWED = 6
STATUS_EMERGENCY = 7

CMD_ROBOT_REQUEST = 8
CMD_HMI_ALLOW = 9
CMD_ROBOT_PASSED = 10
CMD_EMERGENCY = 11
CMD_RESET = 12


def read_coils(client, start, count, title):
    try:
        result = client.read_coils(
            address=start,
            count=count,
            device_id=DEVICE_ID
        )

        if result.isError():
            print(f"[ERROR] {title} okunamadı:", result)
            return None

        values = result.bits[:count]

        print(f"\n--- {title} ---")
        for i, value in enumerate(values):
            print(f"coil {start + i:02d}: {value}")
        print("----------------")

        return values

    except ModbusIOException as e:
        print(f"[MODBUS IO ERROR] {title} okunamadı:", e)
        return None

    except Exception as e:
        print(f"[ERROR] {title} okunurken hata:", e)
        return None


def read_state(client):
    q = read_coils(client, 0, 4, "Q / Fiziksel röle coilleri")
    s = read_coils(client, 4, 4, "STATUS coilleri")

    if q is not None:
        print("\n--- Röle yorumu ---")
        print("K1 READY aktif        :", q[0] is False)
        print("K2 REQUEST aktif      :", q[1] is False)
        print("K3 PASS_ALLOWED aktif :", q[2] is False)
        print("K4 EMERGENCY aktif    :", q[3] is False)
        print("--------------------")

    if s is not None:
        print("\n--- Status yorumu ---")
        print("STATUS_READY        :", s[0])
        print("STATUS_REQUEST      :", s[1])
        print("STATUS_PASS_ALLOWED :", s[2])
        print("STATUS_EMERGENCY    :", s[3])
        print("---------------------")


def write_coil(client, address, value, name):
    try:
        result = client.write_coil(
            address=address,
            value=value,
            device_id=DEVICE_ID
        )

        if result.isError():
            print(f"[ERROR] {name} yazılamadı. coil={address}, value={value}, result={result}")
            return False

        print(f"[OK] {name} coil {address} = {value}")
        return True

    except ModbusIOException as e:
        print(f"[MODBUS IO ERROR] {name} yazılamadı:", e)
        return False

    except Exception as e:
        print(f"[ERROR] {name} yazılırken hata:", e)
        return False


def pulse(client, address, name, duration=0.3):
    print(f"\n[PULSE] {name}")

    if not write_coil(client, address, True, name):
        return False

    time.sleep(duration)

    if not write_coil(client, address, False, name):
        return False

    time.sleep(0.7)
    return True


def wait(msg):
    input(f"\n{msg}\nDevam etmek için Enter'a bas...")


def main():
    print("===================================")
    print("OpenPLC ESP8266 Modbus Test")
    print("===================================")
    print(f"PLC IP    : {PLC_IP}")
    print(f"Port      : {PLC_PORT}")
    print(f"Device ID : {DEVICE_ID}")
    print("===================================")

    client = ModbusTcpClient(PLC_IP, port=PLC_PORT, timeout=5)

    print("\nBağlanılıyor...")

    if not client.connect():
        print("[ERROR] Bağlanamadı.")
        return

    print("[OK] Bağlandı.")

    print("\nİlk durum okunuyor. Beklenen fiziksel durum: sadece K1 yanık.")
    read_state(client)

    wait("1) RESET gönderilecek. Beklenen: K1 yanık kalmalı.")
    pulse(client, CMD_RESET, "CMD_RESET")
    read_state(client)

    wait("2) ROBOT_REQUEST gönderilecek. Beklenen: K1 söner, K2 yanar.")
    pulse(client, CMD_ROBOT_REQUEST, "CMD_ROBOT_REQUEST")
    read_state(client)

    wait("3) HMI_ALLOW gönderilecek. Beklenen: K2 söner, K3 yanar.")
    pulse(client, CMD_HMI_ALLOW, "CMD_HMI_ALLOW")
    read_state(client)

    wait("4) ROBOT_PASSED gönderilecek. Beklenen: K3 söner, K1 yanar.")
    pulse(client, CMD_ROBOT_PASSED, "CMD_ROBOT_PASSED")
    read_state(client)

    wait("5) EMERGENCY gönderilecek. Beklenen: K1 söner, K4 yanar.")
    pulse(client, CMD_EMERGENCY, "CMD_EMERGENCY")
    read_state(client)

    wait("6) RESET gönderilecek. Beklenen: K4 söner, K1 yanar.")
    pulse(client, CMD_RESET, "CMD_RESET")
    read_state(client)

    client.close()
    print("\nTest bitti.")


if __name__ == "__main__":
    main()