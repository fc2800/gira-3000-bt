"""Constants for the Gira 3000 BT System integration."""

import logging

DOMAIN = "gira_system_3000"

LOGGER = logging.getLogger(__package__)

# --------------------------------------------------------------------------------------
# Manufacturer / Bluetooth identification
# --------------------------------------------------------------------------------------
GIRA_MANUFACTURER_ID = 1412
MANUFACTURER_ID      = 0x0584  # same value as above in hex

# --------------------------------------------------------------------------------------
# GATT UUIDs (service + read/write characteristics)
# --------------------------------------------------------------------------------------
GIRA_SERVICE_UUID    = "9769F147-F77A-43AE-8C35-09F0C5245308"
GIRA_WRITE_CHAR_UUID = "97696341-F77A-43AE-8C35-09F0C5245308"
GIRA_READ_CHAR_UUID  = "9769C769-F77A-43AE-8C35-09F0C5245308"

# Backwards-compatible name used in older code:
GIRA_COMMAND_CHARACTERISTIC_UUID = GIRA_WRITE_CHAR_UUID

# --------------------------------------------------------------------------------------
# JALOUSIE (shutter) command set
# --------------------------------------------------------------------------------------
SHUTTER_COMMAND_PREFIX = bytearray.fromhex("F6032001")
SHUTTER_COMMAND_SUFFIX = bytearray.fromhex("1001")

SHUTTER_PROPERTY_ID_MOVE         = 0xFF  # up/down
SHUTTER_PROPERTY_ID_STOP         = 0xFD  # stop
SHUTTER_PROPERTY_ID_STEP         = 0xFE  # step up/down
SHUTTER_PROPERTY_ID_SET_POSITION = 0xFC  # absolute position

SHUTTER_VALUE_UP   = 0x00
SHUTTER_VALUE_DOWN = 0x01
SHUTTER_VALUE_STOP = 0x00  # stop uses 0x00

# Shutter broadcasts: 1 byte position after prefix (0x00..0xFF)
SHUTTER_POS_PREFIX = bytearray.fromhex("F7032001F61001")
SHUTTER_POS_LENGTH_BYTES = 1

# If your device uses inverted semantics (common for covers), set to True.
# Existing versions of this integration used inverted mapping by default.
SHUTTER_INVERT_POSITION = True

# --------------------------------------------------------------------------------------
# THERMOSTAT command set
# --------------------------------------------------------------------------------------
THERMO_COMMAND_PREFIX = bytearray.fromhex("F6006501")
THERMO_COMMAND_SUFFIX = bytearray.fromhex("1001")

THERMO_PROPERTY_ID_TIMER_HEAT  = 0xFE  # start/stop timer
THERMO_PROPERTY_ID_TARGET_TEMP = 0xF5  # set target temperature (uint16 / 100)
THERMO_PROPERTY_ID_STEP        = 0xF6  # step +/- 0.5°C (value encoding depends on device)

THERMO_VALUE_STOP  = 0x00
THERMO_VALUE_START = 0x01

# Thermostat broadcasts
# Current temperature: (uint16 - 1000) / 100
THERMO_CURRENT_TEMP_PREFIX = bytearray.fromhex("F7014101FE1001")
# Target temperature: uint16 / 100
THERMO_TARGET_TEMP_PREFIX  = bytearray.fromhex("F7006501FF1001")
THERMO_TEMPERATURE_LENGTH_BYTES = 2

# --------------------------------------------------------------------------------------
# SENSOR (temperature / brightness) broadcasts
# --------------------------------------------------------------------------------------
SENSOR_TEMPERATURE_PREFIX = bytearray.fromhex("F7019901FF1001")
SENSOR_BRIGHTNESS_PREFIX  = bytearray.fromhex("F7019901FE1001")
SENSOR_LENGTH_BYTES = 2

SENSOR_FRAME_LENGTH = 13
SENSOR_SUFFIX_0 = 0x10
SENSOR_SUFFIX_1 = 0x01

SENSOR_CMD_TEMPERATURE = 0xFE
SENSOR_CMD_BRIGHTNESS = 0xFF

SENSOR_TEMP_NEG_BASE = 0x8000        # negative temperaure = 0x8000 - raw
SENSOR_TEMP_DIVISOR = 100.0          # raw / 100 -> °C
SENSOR_TEMP_NEG_BASE_DIVISOR = 10.0  # scale is raw/1000 additional /10 to keep logic identic

SENSOR_LUX_A = 0.00015070156043542327    #   float lux = powf(10.0f, SENSOR_LUX_A * r + SENSOR_LUX_B);
SENSOR_LUX_B = 0.9468552783240188
