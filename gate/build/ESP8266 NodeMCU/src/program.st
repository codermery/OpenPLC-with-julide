PROGRAM main
  VAR
    STATUS_BARRIER_OPEN : BOOL := False;
    STATUS_PASS_PERMISSION : BOOL := False;
    M_READY : BOOL := True;
    M_REQUEST : BOOL := False;
    M_PASS_ALLOWED : BOOL := False;
    M_EMERGENCY : BOOL := False;
    PWM_CONTROLLER0 : PWM_CONTROLLER;
    SERVO_CHANNEL : SINT := 13;
    SERVO_FREQ : REAL := 50.0;
    SERVO_DUTY_CLOSED : REAL := 5.0;
    SERVO_DUTY_OPEN : REAL := 7.5;
    PWM_CLOSE_OK : BOOL := False;
    PWM_OPEN_OK : BOOL := False;
  END_VAR
  VAR
    Q_READY AT %QX0.0 : BOOL := False;
    Q_REQUEST AT %QX0.1 : BOOL := False;
    Q_PASS_ALLOWED AT %QX0.2 : BOOL := False;
    Q_EMERGENCY AT %QX0.3 : BOOL := False;
    CMD_ROBOT_REQUEST AT %QX1.0 : BOOL := False;
    CMD_HMI_ALLOW AT %QX1.1 : BOOL := False;
    CMD_ROBOT_PASSED AT %QX1.2 : BOOL := False;
    CMD_EMERGENCY AT %QX1.3 : BOOL := False;
    CMD_RESET AT %QX1.4 : BOOL := False;
    STATUS_READY AT %QX0.4 : BOOL := False;
    STATUS_REQUEST AT %QX0.5 : BOOL := False;
    STATUS_PASS_ALLOWED AT %QX0.6 : BOOL := False;
    STATUS_EMERGENCY AT %QX0.7 : BOOL := False;
  END_VAR

  IF CMD_RESET THEN
    M_READY := TRUE; (*set*)
  END_IF;
  IF CMD_RESET THEN
    M_REQUEST := FALSE; (*reset*)
  END_IF;
  IF CMD_RESET THEN
    M_PASS_ALLOWED := FALSE; (*reset*)
  END_IF;
  IF CMD_RESET THEN
    M_EMERGENCY := FALSE; (*reset*)
  END_IF;
  IF CMD_EMERGENCY THEN
    M_EMERGENCY := TRUE; (*set*)
  END_IF;
  IF CMD_EMERGENCY THEN
    M_READY := FALSE; (*reset*)
  END_IF;
  IF CMD_EMERGENCY THEN
    M_REQUEST := FALSE; (*reset*)
  END_IF;
  IF CMD_EMERGENCY THEN
    M_PASS_ALLOWED := FALSE; (*reset*)
  END_IF;
  IF CMD_ROBOT_REQUEST AND M_READY THEN
    M_REQUEST := TRUE; (*set*)
  END_IF;
  IF CMD_ROBOT_REQUEST AND M_READY THEN
    M_READY := FALSE; (*reset*)
  END_IF;
  IF CMD_HMI_ALLOW AND M_REQUEST THEN
    M_PASS_ALLOWED := TRUE; (*set*)
  END_IF;
  IF CMD_HMI_ALLOW AND M_REQUEST THEN
    M_REQUEST := FALSE; (*reset*)
  END_IF;
  IF CMD_ROBOT_PASSED AND M_PASS_ALLOWED THEN
    M_READY := TRUE; (*set*)
  END_IF;
  IF CMD_ROBOT_PASSED AND M_PASS_ALLOWED THEN
    M_PASS_ALLOWED := FALSE; (*reset*)
  END_IF;
  Q_READY := NOT(M_READY);
  Q_REQUEST := NOT(M_REQUEST);
  Q_PASS_ALLOWED := NOT(M_PASS_ALLOWED);
  Q_EMERGENCY := NOT(M_EMERGENCY);
  STATUS_READY := M_READY;
  STATUS_REQUEST := M_REQUEST;
  STATUS_PASS_ALLOWED := M_PASS_ALLOWED;
  STATUS_EMERGENCY := M_EMERGENCY;
  STATUS_BARRIER_OPEN := M_PASS_ALLOWED;
  STATUS_PASS_PERMISSION := M_PASS_ALLOWED;
  PWM_CONTROLLER0(EN := M_READY, CHANNEL := SERVO_CHANNEL, FREQ := SERVO_FREQ, DUTY := SERVO_DUTY_CLOSED);
  IF PWM_CONTROLLER0.ENO THEN
      PWM_CLOSE_OK := PWM_CONTROLLER0.SUCCESS;
  END_IF;
  PWM_CONTROLLER0(EN := M_PASS_ALLOWED, CHANNEL := SERVO_CHANNEL, FREQ := SERVO_FREQ, DUTY := SERVO_DUTY_OPEN);
  IF PWM_CONTROLLER0.ENO THEN
      PWM_OPEN_OK := PWM_CONTROLLER0.SUCCESS;
  END_IF;
  PWM_CONTROLLER0(EN := CMD_ROBOT_PASSED, CHANNEL := SERVO_CHANNEL, FREQ := SERVO_FREQ, DUTY := SERVO_DUTY_CLOSED);
  IF PWM_CONTROLLER0.ENO THEN
      PWM_CLOSE_OK := PWM_CONTROLLER0.SUCCESS;
  END_IF;
END_PROGRAM


CONFIGURATION Config0

  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#20ms,PRIORITY := 1);
    PROGRAM instance0 WITH task0 : main;
  END_RESOURCE
END_CONFIGURATION

(*DBG:char md5[] = "ef2df8eafba75bfadd009ed3909d09cf";*)
(*DBG:/**)
(*DBG: * This file is part of OpenPLC Runtime*)
(*DBG: **)
(*DBG: * Copyright (C) 2023 Autonomy, GP Orcullo*)
(*DBG: * Based on the work by GP Orcullo on Beremiz for uC*)
(*DBG: **)
(*DBG: * This program is free software; you can redistribute it and/or*)
(*DBG: * modify it under the terms of the GNU General Public License*)
(*DBG: * as published by the Free Software Foundation; either version 2*)
(*DBG: * of the License, or (at your option) any later version.*)
(*DBG: **)
(*DBG: * This program is distributed in the hope that it will be useful,*)
(*DBG: * but WITHOUT ANY WARRANTY; without even the implied warranty of*)
(*DBG: * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the*)
(*DBG: * GNU General Public License for more details.*)
(*DBG: **)
(*DBG: * You should have received a copy of the GNU General Public License*)
(*DBG: * along with this program; If not, see <http://www.gnu.org/licenses/>.*)
(*DBG: **)
(*DBG: */*)
(*DBG:*)
(*DBG:#include <stdbool.h>*)
(*DBG:*)
(*DBG:// Include defines.h first for Arduino builds to set USE_*_BLOCKS macros*)
(*DBG:// before iec_std_FB.h processes its conditional includes*)
(*DBG:#ifdef ARDUINO*)
(*DBG:#include "../examples/Baremetal/defines.h"*)
(*DBG:#endif*)
(*DBG:*)
(*DBG:#include "iec_types_all.h"*)
(*DBG:#include "POUS.h"*)
(*DBG:*)
(*DBG:#define SAME_ENDIANNESS      0*)
(*DBG:#define REVERSE_ENDIANNESS   1*)
(*DBG:*)
(*DBG:char plc_program_md5[] = "ef2df8eafba75bfadd009ed3909d09cf";*)
(*DBG:*)
(*DBG:uint8_t endianness;*)
(*DBG:*)
(*DBG:*)
(*DBG:extern MAIN RES0__INSTANCE0;*)
(*DBG:*)
(*DBG:static const struct {*)
(*DBG:    void *ptr;*)
(*DBG:    __IEC_types_enum type;*)
(*DBG:} debug_vars[] = {*)
(*DBG:    {&(RES0__INSTANCE0.STATUS_BARRIER_OPEN), BOOL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.STATUS_PASS_PERMISSION), BOOL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.M_READY), BOOL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.M_REQUEST), BOOL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.M_PASS_ALLOWED), BOOL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.M_EMERGENCY), BOOL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PWM_CONTROLLER0.EN), BOOL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PWM_CONTROLLER0.ENO), BOOL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PWM_CONTROLLER0.CHANNEL), SINT_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PWM_CONTROLLER0.FREQ), REAL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PWM_CONTROLLER0.DUTY), REAL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PWM_CONTROLLER0.SUCCESS), BOOL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PWM_CONTROLLER0.INTERNAL_CH), SINT_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PWM_CONTROLLER0.INTERNAL_FREQ), REAL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PWM_CONTROLLER0.INTERNAL_DUTY), REAL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.SERVO_CHANNEL), SINT_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.SERVO_FREQ), REAL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.SERVO_DUTY_CLOSED), REAL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.SERVO_DUTY_OPEN), REAL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PWM_CLOSE_OK), BOOL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.PWM_OPEN_OK), BOOL_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.Q_READY), BOOL_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.Q_REQUEST), BOOL_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.Q_PASS_ALLOWED), BOOL_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.Q_EMERGENCY), BOOL_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.CMD_ROBOT_REQUEST), BOOL_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.CMD_HMI_ALLOW), BOOL_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.CMD_ROBOT_PASSED), BOOL_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.CMD_EMERGENCY), BOOL_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.CMD_RESET), BOOL_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.STATUS_READY), BOOL_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.STATUS_REQUEST), BOOL_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.STATUS_PASS_ALLOWED), BOOL_O_ENUM},*)
(*DBG:    {&(RES0__INSTANCE0.STATUS_EMERGENCY), BOOL_O_ENUM},*)
(*DBG:};*)
(*DBG:*)
(*DBG:#define VAR_COUNT               34*)
(*DBG:*)
(*DBG:uint16_t get_var_count(void)*)
(*DBG:{*)
(*DBG:    return VAR_COUNT;*)
(*DBG:}*)
(*DBG:*)
(*DBG:size_t get_var_size(size_t idx)*)
(*DBG:{*)
(*DBG:    if (idx >= VAR_COUNT)*)
(*DBG:    {*)
(*DBG:        return 0;*)
(*DBG:    }*)
(*DBG:    switch (debug_vars[idx].type) {*)
(*DBG:    case BOOL_ENUM:*)
(*DBG:    case BOOL_O_ENUM:*)
(*DBG:        return sizeof(BOOL);*)
(*DBG:    case SINT_ENUM:*)
(*DBG:        return sizeof(SINT);*)
(*DBG:    case REAL_ENUM:*)
(*DBG:        return sizeof(REAL);*)
(*DBG:    default:*)
(*DBG:        return 0;*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)
(*DBG:void *get_var_addr(size_t idx)*)
(*DBG:{*)
(*DBG:    void *ptr = debug_vars[idx].ptr;*)
(*DBG:*)
(*DBG:    switch (debug_vars[idx].type) {*)
(*DBG:    case BOOL_ENUM:*)
(*DBG:        return (void *)&((__IEC_BOOL_t *) ptr)->value;*)
(*DBG:    case BOOL_O_ENUM:*)
(*DBG:        return (void *)((((__IEC_BOOL_p *) ptr)->flags & __IEC_FORCE_FLAG)*)
(*DBG:                        ? &(((__IEC_BOOL_p *) ptr)->fvalue)*)
(*DBG:                        : ((__IEC_BOOL_p *) ptr)->value);*)
(*DBG:    case SINT_ENUM:*)
(*DBG:        return (void *)&((__IEC_SINT_t *) ptr)->value;*)
(*DBG:    case REAL_ENUM:*)
(*DBG:        return (void *)&((__IEC_REAL_t *) ptr)->value;*)
(*DBG:    default:*)
(*DBG:        return 0;*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)
(*DBG:void force_var(size_t idx, bool forced, void *val)*)
(*DBG:{*)
(*DBG:    void *ptr = debug_vars[idx].ptr;*)
(*DBG:*)
(*DBG:    if (forced) {*)
(*DBG:        size_t var_size = get_var_size(idx);*)
(*DBG:        switch (debug_vars[idx].type) {*)
(*DBG:        case BOOL_ENUM: {*)
(*DBG:            memcpy(&((__IEC_BOOL_t *) ptr)->value, val, var_size);*)
(*DBG:            ((__IEC_BOOL_t *) ptr)->flags |= __IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        }*)
(*DBG:    *)
(*DBG:        case BOOL_O_ENUM: {*)
(*DBG:            memcpy((((__IEC_BOOL_p *) ptr)->value), val, var_size);*)
(*DBG:            memcpy(&((__IEC_BOOL_p *) ptr)->fvalue, val, var_size);*)
(*DBG:            ((__IEC_BOOL_p *) ptr)->flags |= __IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        }*)
(*DBG:        case SINT_ENUM: {*)
(*DBG:            memcpy(&((__IEC_SINT_t *) ptr)->value, val, var_size);*)
(*DBG:            ((__IEC_SINT_t *) ptr)->flags |= __IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        }*)
(*DBG:    *)
(*DBG:        case REAL_ENUM: {*)
(*DBG:            memcpy(&((__IEC_REAL_t *) ptr)->value, val, var_size);*)
(*DBG:            ((__IEC_REAL_t *) ptr)->flags |= __IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        }*)
(*DBG:    *)
(*DBG:        default:*)
(*DBG:            break;*)
(*DBG:        }*)
(*DBG:    } else {*)
(*DBG:        switch (debug_vars[idx].type) {*)
(*DBG:        case BOOL_ENUM:*)
(*DBG:            ((__IEC_BOOL_t *) ptr)->flags &= ~__IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        case BOOL_O_ENUM:*)
(*DBG:            ((__IEC_BOOL_p *) ptr)->flags &= ~__IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        case SINT_ENUM:*)
(*DBG:            ((__IEC_SINT_t *) ptr)->flags &= ~__IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        case REAL_ENUM:*)
(*DBG:            ((__IEC_REAL_t *) ptr)->flags &= ~__IEC_FORCE_FLAG;*)
(*DBG:            break;*)
(*DBG:        default:*)
(*DBG:            break;*)
(*DBG:        }*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)
(*DBG:void swap_bytes(void *ptr, size_t size)*)
(*DBG:{*)
(*DBG:    uint8_t *bytePtr = (uint8_t *)ptr;*)
(*DBG:    size_t i;*)
(*DBG:    for (i = 0; i < size / 2; ++i)*)
(*DBG:    {*)
(*DBG:        uint8_t temp = bytePtr[i];*)
(*DBG:        bytePtr[i] = bytePtr[size - 1 - i];*)
(*DBG:        bytePtr[size - 1 - i] = temp;*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)
(*DBG:void trace_reset(void)*)
(*DBG:{*)
(*DBG:    for (size_t i=0; i < VAR_COUNT; i++)*)
(*DBG:    {*)
(*DBG:        force_var(i, false, 0);*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)
(*DBG:void set_trace(size_t idx, bool forced, void *val)*)
(*DBG:{*)
(*DBG:    if (idx >= 0 && idx < VAR_COUNT)*)
(*DBG:    {*)
(*DBG:        if (endianness == REVERSE_ENDIANNESS)*)
(*DBG:        {*)
(*DBG:            // Prevent swapping for STRING type*)
(*DBG:            if (debug_vars[idx].type == STRING_ENUM)*)
(*DBG:            {*)
(*DBG:                // Do nothing*)
(*DBG:                ;*)
(*DBG:            }*)
(*DBG:            else*)
(*DBG:            {*)
(*DBG:                swap_bytes(val, get_var_size(idx));*)
(*DBG:            }*)
(*DBG:        }*)
(*DBG:*)
(*DBG:        force_var(idx, forced, val);*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)
(*DBG:void set_endianness(uint8_t value)*)
(*DBG:{*)
(*DBG:    if (value == SAME_ENDIANNESS || value == REVERSE_ENDIANNESS)*)
(*DBG:    {*)
(*DBG:        endianness = value;*)
(*DBG:    }*)
(*DBG:}*)
(*DBG:*)