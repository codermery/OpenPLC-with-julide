/*
  OpenPLC ESP8266 PWM patch for PWM_CONTROLLER
  Purpose:
  - Defines set_hardware_pwm() required by OpenPLC PWM_CONTROLLER block.
  - Uses ESP8266 Arduino core analogWriteFreq() + analogWrite().
  - Intended for SG90 servo test on GPIO13 / D7.

  Put this file in:
  C:\Users\merye\OneDrive\Belgeler\gate\build\ESP8266 NodeMCU\libraries\src\openplc_esp8266_pwm_patch.cpp

  Ladder values:
  SERVO_CHANNEL = 13
  SERVO_FREQ = 50.0
  SERVO_DUTY_CLOSED = 5.0
  SERVO_DUTY_OPEN = 7.5 or 10.0
*/

#include <Arduino.h>

extern "C" uint8_t set_hardware_pwm(uint8_t ch, float freq, float duty)
{
    // Channel mapping:
    // 13 -> GPIO13 / D7 on NodeMCU / Wemos style ESP8266 boards.
    // 7  -> also accepted as D7 label and mapped to GPIO13.
    uint8_t pin = ch;

    if (ch == 7) {
        pin = 13;
    }

    // For this project, protect against accidental wrong channel values.
    // We only want to drive the gate servo on GPIO13 / D7.
    if (pin != 13) {
        return 0;
    }

    if (freq < 1.0f) {
        freq = 50.0f;
    }

    if (duty < 0.0f) {
        duty = 0.0f;
    }

    if (duty > 100.0f) {
        duty = 100.0f;
    }

    pinMode(pin, OUTPUT);

    // ESP8266 Arduino PWM setup.
    analogWriteRange(1023);
    analogWriteFreq((uint32_t)freq);

    uint16_t pwmValue = (uint16_t)((1023.0f * duty / 100.0f) + 0.5f);
    analogWrite(pin, pwmValue);

    return 1;
}
