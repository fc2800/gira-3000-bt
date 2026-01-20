# Gira System 3000 – Bluetooth Low Energy (BLE)

Reverse-engineering documentation and tooling for **Gira System 3000**
Bluetooth Low Energy devices.

This repository focuses on understanding and documenting the BLE protocol
used by Gira System 3000 actuators and sensors in order to enable **local,
cloud-free control** via ESP32 and Home Assistant.

---

## Scope and Goals

- Document BLE advertisement and GATT behavior
- Identify command and notification formats
- Enable deterministic control of actuators (e.g. shutters)
- Support local integrations (ESP32 → MQTT → Home Assistant)
- Avoid cloud services and vendor lock-in

This project is **documentation-driven**. Code exists to validate protocol
findings, not as a consumer product.

---

## Supported Devices

| Device | Category | Communication | Status |
|------|---------|--------------|--------|
| Gira System 3000 Shutter | Actuator | GATT + Notifications | Tested |
| Gira System 3000 Thermostat | Control / Sensor | GATT + Notifications | Tested |
| Gira System 3000 Sensors | Sensor | BLE Advertisements | Observed |

---

## Architecture

```
Gira System 3000 Device
        │
        │ BLE (Advertisements + GATT)
        ▼
ESP32 (ESP-IDF + NimBLE)
        │
        │ MQTT
        ▼
Home Assistant
```

Key properties:
- Event-driven (no polling)
- Devices report state autonomously
- Commands are sent only once per action

---

## Repository Structure

```
.
├── README.md
├── docs
│   └── protocol.md
├── examples
│   ├── mqtt_commands
│   └── esp32
└── tools
```

---

## Pairing and Security Overview

- BLE pairing method: **Just Works**
- Bonding is required for stable operation
- Encrypted communication is enabled after pairing
- Incomplete SMP bonding leads to connection or encryption timeouts

Detailed security behavior is documented in `docs/protocol.md`.

---

## ESP32 Integration

Recommended setup:
- ESP32-S3
- ESP-IDF ≥ 5.x
- NimBLE BLE stack
- Runtime control via MQTT commands

Pairing, command execution, and disconnect behavior are all handled
at runtime and do not require firmware recompilation.

---

## Home Assistant Integration

- MQTT-based
- Fully local
- State derived from BLE notifications and advertisements
- No polling, no cloud dependency

This repository does **not** ship a Home Assistant integration.
It documents the protocol required to build one.

---

## Known Limitations

- Devices emit valid sensor frames only every 2–5 minutes
- Some BLE advertisements are malformed and must be filtered
- No official documentation exists from the manufacturer

---

## Development Status

This project is under active reverse-engineering.
Protocol details may evolve as new observations are made.

---

## Legal Disclaimer

This project is not affiliated with Gira.
All trademarks and product names are the property of their respective owners.

Reverse-engineering is performed solely for interoperability and research
purposes.


# Bluetooth

•	Uses Home Assistant Bluetooth stack

•	Works with multiple ESPHome Bluetooth proxies

•	Lazy pairing (only when needed

•	Idle disconnect to free BLE slots

•	No BLE connection during setup

# Installation
1.	Copy the integration folder to:
/config/custom_components/gira_system_3000/
2.	Ensure the folder contains at least:
__init__.py
manifest.json
config_flow.py
gira_ble.py
cover.py
climate.py
sensor.py
const.py
(Optional: logo.png, icon.png)
3.	Restart Home Assistant.
# Adding Devices
1.	Settings → Devices & Services
2.	Add Integration → Gira System 3000
3.	Select device type:
o	Shutter
o	Thermostat
o	Sensor
4.	Enter or select the device MAC address
No BLE connection is attempted during setup.
This avoids BLE slot exhaustion and allows adding many devices.
# Pairing Behavior
•	Devices are not paired during setup

•	Pairing happens automatically on first command

•	Pairing is handled by BlueZ (Home Assistant OS)

•	Sensors never pair (passive only)

This design is essential for scalable BLE setups.

# Bluetooth Proxies
•	Multiple ESPHome Bluetooth proxies supported

•	Home Assistant automatically selects the best proxy (RSSI-based)

•	Reduce proxy overlap for best reliability

# Practical limits
•	BLE GATT connections are limited (≈3 per proxy)

•	Passive sensors scale without limits

•	Idle disconnect frees slots automatically

# Configuration Files Overview
File	Purpose

config_flow.py	Device setup (no BLE connect)

gira_ble.py	BLE protocol handling

cover.py	Shutter entity

climate.py	Thermostat entity

sensor.py	Sensor entities

const.py	All protocol constants

# Known Limitations
•	BLE connection slots are hardware-limited

•	Thermostat step commands are unreliable on GIRA devices

•	Integration logo may not appear for custom integrations
