# Gira 3000 BT System

Local Home Assistant integration for Gira System 3000 Bluetooth devices.
This integration supports shutters  "Jal+Schaltuhr", thermostats "Thermostat" , and passive sensors "Sensor Temp/Brightness" using the Home Assistant Bluetooth stack and ESPHome Bluetooth proxies.
It is fully local, scales to many devices, and correctly implements GIRA’s undocumented BLE protocol quirks.

# Shutters ("Jal+Schaltuhr")
•  Open / Close / Stop buttons

•  Absolute position control (0–100 %)

•  Live position updates via BLE advertisements

•  No polling, no permanent connection

# Thermostats ("Thermostat")

•	Native Home Assistant climate entity

•	Correct GIRA dual-scale temperature decoding

•	Absolute setpoint control

•	Lazy pairing on first use

# Sensors ("Sensor Temp/Brightness")

•	Temperature sensor

•	Brightness (lux) sensor

•	Passive BLE only (no pairing, no connects)

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
