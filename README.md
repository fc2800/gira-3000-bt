# Gira 3000 BT System

Local Home Assistant integration for Gira System 3000 Bluetooth devices.
This integration supports shutters  "Jal+Schaltuhr", thermostats "Thermostat" , and passive sensors "Sensor Temp/Brightness" using the Home Assistant Bluetooth stack and ESPHome Bluetooth proxies.
It is fully local, scales to many devices, and correctly implements GIRA’s undocumented BLE protocol quirks.

# Features
Shutters (Jalousie)
•	Open / Close / Stop buttons
•	Absolute position control (0–100 %)
•	Live position updates via BLE advertisements
•	No polling, no permanent connection
