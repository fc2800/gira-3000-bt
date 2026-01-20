# Documentation Index

This directory contains the formal documentation for the **Gira System 3000 BLE**
reverse-engineering project.

The documents are intended to be read in the order listed below.

---

## 1. Protocol Specification

**File:** `protocol.md`

Contains the complete Bluetooth Low Energy protocol documentation derived from
empirical observation:

- Advertising behavior
- Manufacturer data layout
- Device classes
- GATT characteristics
- Command model
- Notifications and feedback
- Pairing and security behavior

Start here if you want to understand *what* the devices transmit and accept.

---

## 2. Pairing / SMP State Machine

**Files:**  
- `pairing_smp_state_machine.svg`  
- `pairing_smp_state_machine.md`

Describes the BLE security and pairing flow when an ESP32 (Central) connects to a
Gira System 3000 device (Peripheral).

Covers:
- Just Works pairing
- Bonding reuse (fast-path)
- Encryption transitions
- Common failure modes (`ENC_CHANGE timeout`, SMP retry)
- Recovery strategies

This is essential when implementing reliable runtime pairing and reconnect logic.

---

## 3. Runtime Control (MQTT)

See: `../examples/mqtt_commands/`

Documents the MQTT-driven runtime control interface used to:
- connect
- pair
- subscribe
- control actuators
- disconnect safely

---

## Reading Order Recommendation

1. `protocol.md`
2. `pairing_smp_state_machine.md`
3. `examples/mqtt_commands/00_overview.md`

---

## Status

Documentation reflects current observations and may evolve as new firmware
versions or device variants are analyzed.
