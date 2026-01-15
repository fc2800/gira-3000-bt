"""Bluetooth LE communication for Gira System 3000 BT devices."""
import asyncio
import logging
from typing import Any, cast, Optional

from bleak import BleakClient, BleakError, BLEDevice
from bleak_retry_connector import establish_connection

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothDataUpdateCoordinator,
)
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DOMAIN, LOGGER

from .const import (
    LOGGER,
    GIRA_MANUFACTURER_ID,
    GIRA_SERVICE_UUID,
    GIRA_WRITE_CHAR_UUID,
    # Shutter constants
    SHUTTER_COMMAND_PREFIX,
    SHUTTER_COMMAND_SUFFIX,
    SHUTTER_PROPERTY_ID_MOVE,
    SHUTTER_PROPERTY_ID_STOP,
    SHUTTER_PROPERTY_ID_STEP,
    SHUTTER_PROPERTY_ID_SET_POSITION,
    SHUTTER_VALUE_UP,
    SHUTTER_VALUE_DOWN,
    SHUTTER_VALUE_STOP,
    SHUTTER_POS_PREFIX,
    SHUTTER_POS_LENGTH_BYTES,
    SHUTTER_INVERT_POSITION,
    # Thermostat constants
    THERMO_COMMAND_PREFIX,
    THERMO_COMMAND_SUFFIX,
    THERMO_PROPERTY_ID_TIMER_HEAT,
    THERMO_PROPERTY_ID_TARGET_TEMP,
    THERMO_PROPERTY_ID_STEP,
    THERMO_VALUE_START,
    THERMO_VALUE_STOP,
    THERMO_CURRENT_TEMP_PREFIX,
    THERMO_TARGET_TEMP_PREFIX,
    THERMO_TEMPERATURE_LENGTH_BYTES,
    # Sensor constants
    SENSOR_TEMPERATURE_PREFIX,
    SENSOR_BRIGHTNESS_PREFIX,
    SENSOR_LENGTH_BYTES,
    SENSOR_TEMPERATURE_SCALE,
    SENSOR_BRIGHTNESS_SCALE,
    SENSOR_FRAME_LENGTH,
    SENSOR_SUFFIX_0,
    SENSOR_SUFFIX_1,
    SENSOR_CMD_TEMPERATURE,
    SENSOR_CMD_BRIGHTNESS,
    SENSOR_TEMP_SIGN_THRESHOLD,
    SENSOR_TEMP_NEG_BASE,
    SENSOR_TEMP_DIVISOR,
    SENSOR_LUX_A,
    SENSOR_LUX_B,
)

def _thermo_decode_temp_u16(raw: int) -> float:
    """Decode Gira thermostat temperature from u16.

    Read rules (per your reverse engineering):
    - temp <= 21.0°C : raw / 100
    - temp > 21.0°C  : raw / 100 - 10
    """
    temp = raw / 100.0
    if raw > 2100:  # 21.0°C threshold
        temp -= 10.0
    return temp

# -----------------------------------------------------------------------------
# Passive coordinator (advertisements) - parses based on device_type
# -----------------------------------------------------------------------------

class GiraPassiveBluetoothDataUpdateCoordinator(PassiveBluetoothDataUpdateCoordinator):
    """Coordinator for receiving passive BLE broadcasts from Gira 3000 BT"""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        name: str,
        device_type: str,
    ):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            address=address,
            mode=bluetooth.BluetoothScanningMode.PASSIVE,
            connectable=False,
        )
        self._device_name = name
        self._device_type = device_type
        self.data = {}
        
        LOGGER.debug(
            "Created coordinator instance for %s (%s) type=%s",
            name,
            address,
            device_type,
        )

    def _async_handle_unavailable(
        self, service_info: BluetoothServiceInfoBleak
    ) -> None:
        """Handle the device going unavailable."""
        LOGGER.debug("Handle unavailable for %s (%s)", self._device_name, self.address)
        self.last_update_success = False
        self.async_update_listeners()

    def _async_handle_bluetooth_event(
        self,
        service_info: BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> Optional[dict]:
        """Handle incoming BLE advertisements for this device."""
        
        # Check if this event is for our device
        if service_info.device.address.upper() != self.address.upper():
            return None

        manufacturer_data = service_info.manufacturer_data.get(GIRA_MANUFACTURER_ID)
        if not manufacturer_data:
            return None

        # ---------------------------
        # SHUTTER
        # ---------------------------
        if self._device_type == "shutter":
            prefix_index = manufacturer_data.find(SHUTTER_POS_PREFIX)
            # Ensure enough bytes after prefix to read position
            if prefix_index == -1:
                return None
            if len(manufacturer_data) < prefix_index + len(SHUTTER_POS_PREFIX) + 1:
                return None

            # Extract position byte, 1 byte after prefix
            position_byte = manufacturer_data[prefix_index + len(SHUTTER_POS_PREFIX)]
            ha_position = round(100 * (255 - position_byte) / 255)

            # Return dictionary containing new data.
            self.data = {"position": ha_position}
            self.async_update_listeners()         
            return self.data

        # ---------------------------
        # THERMOSTAT
        # ---------------------------
        if self._device_type == "thermostat":
            # MERGE partial broadcasts (do NOT overwrite)
            data: dict[str, Any] = dict(getattr(self, "data", {}) or {})

            idx = manufacturer_data.find(THERMO_CURRENT_TEMP_PREFIX)
            if idx != -1 and len(manufacturer_data) >= idx + len(THERMO_CURRENT_TEMP_PREFIX) + 2:
                raw = int.from_bytes(
                    manufacturer_data[
                        idx + len(THERMO_CURRENT_TEMP_PREFIX)
                        : idx + len(THERMO_CURRENT_TEMP_PREFIX) + 2
                    ],
                    "big",
                )
                data["current_temperature"] = _thermo_decode_temp_u16(raw)

            idx = manufacturer_data.find(THERMO_TARGET_TEMP_PREFIX)
            if idx != -1 and len(manufacturer_data) >= idx + len(THERMO_TARGET_TEMP_PREFIX) + 2:
                raw = int.from_bytes(
                    manufacturer_data[
                        idx + len(THERMO_TARGET_TEMP_PREFIX)
                        : idx + len(THERMO_TARGET_TEMP_PREFIX) + 2
                    ],
                    "big",
                )
                data["target_temperature"] = _thermo_decode_temp_u16(raw)

            if data:
                self.data = data
                self.async_update_listeners()
                return data

        # ---------------------------
        # SENSOR
        # ---------------------------
        if self._device_type == "sensor":
            # ESPHome-equivalent parsing (13-byte manufacturer frame)
            if len(manufacturer_data) != SENSOR_FRAME_LENGTH:
                return None

            if not (manufacturer_data[9] == SENSOR_SUFFIX_0 and manufacturer_data[10] == SENSOR_SUFFIX_1):
                return None

            cmd = manufacturer_data[8]
            if cmd not in (SENSOR_CMD_TEMPERATURE, SENSOR_CMD_BRIGHTNESS):
                return None

            hi = manufacturer_data[11]
            lo = manufacturer_data[12]
            raw = (lo | (hi << 8)) & 0xFFFF

            data: dict[str, Any] = dict(getattr(self, "data", {}) or {})

            if cmd == SENSOR_CMD_TEMPERATURE:
                # Signed temperature conversion like ESPHome lambda
                if raw > SENSOR_TEMP_SIGN_THRESHOLD:
                    temp_raw = SENSOR_TEMP_NEG_BASE - raw
                else:
                    temp_raw = raw
                data["sensor_temperature"] = float(temp_raw) / SENSOR_TEMP_DIVISOR

            else:
                # Log lux conversion like ESPHome lambda
                lux = 10 ** (SENSOR_LUX_A * float(raw) + SENSOR_LUX_B)
                if lux < 0:
                    lux = 0.0
                data["sensor_brightness"] = float(lux)

            self.data = data
            self.async_update_listeners()
            return data

# ---------------------------
# SHUTER
# ---------------------------
def _generate_command(property_id: int, value: int) -> bytearray:
    """Generates the full command byte array from its parts."""
    return (
        SHUTTER_COMMAND_PREFIX
        + property_id.to_bytes(1, 'big')
        + SHUTTER_COMMAND_SUFFIX
        + value.to_bytes(1, 'big')
    )

def generate_position_command(percentage: int) -> bytearray:
    """Generates the command for setting absolute blinds position."""
    if not 0 <= percentage <= 100:
        raise ValueError("Percentage must be between 0 and 100.")
    return _generate_command(SHUTTER_PROPERTY_ID_SET_POSITION, percentage)

# ---------------------------
# THERMOSTAT
# ---------------------------
def _generate_thermo_u8_command(property_id: int, value_u8: int) -> bytearray:
    """Generate thermostat command with a single u8 value."""
    v = int(value_u8) & 0xFF
    return (
        THERMO_COMMAND_PREFIX
        + property_id.to_bytes(1, "big")
        + THERMO_COMMAND_SUFFIX
        + v.to_bytes(1, "big")
    )

def _generate_thermo_u16_command(property_id: int, value_u16: int) -> bytearray:
    """Generate thermostat command with a uint16 value (big-endian)."""
    v = int(value_u16)
    if v < 0:
        v = 0
    if v > 0xFFFF:
        v = 0xFFFF
    return (
        THERMO_COMMAND_PREFIX
        + property_id.to_bytes(1, "big")
        + THERMO_COMMAND_SUFFIX
        + v.to_bytes(2, "big", signed=False)
    )


class GiraBLEClient:
    """Manages the Bluetooth LE connection and command sending for a Gira device."""

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        """Initialize the client."""
        self.hass = hass
        self.address = address
        self.name = name
        
        self._client: BleakClient | None = None
        self._is_connecting = asyncio.Lock()

        self._idle_disconnect_handle = None
        self._idle_disconnect_s = 15.0      # seconds to keep connection open
        self._write_timeout_s = 2.0         # seconds for write_gatt_char
    
        LOGGER.debug("GiraBLEClient initialized for %s (%s)", name, address)
    
    # -------------------------------------------------------------------------
    # Idle disconnect helpers
    # -------------------------------------------------------------------------
    def _cancel_idle_disconnect(self) -> None:
        if self._idle_disconnect_handle is not None:
            try:
                self._idle_disconnect_handle.cancel()
            except Exception:
                pass
            self._idle_disconnect_handle = None

    def _schedule_idle_disconnect(self) -> None:
        self._cancel_idle_disconnect()

        def _cb() -> None:
            self.hass.async_create_task(self._disconnect_now())

        self._idle_disconnect_handle = self.hass.loop.call_later(self._idle_disconnect_s, _cb)

    async def _disconnect_now(self) -> None:
        async with self._is_connecting:
            self._cancel_idle_disconnect()
            if self._client and self._client.is_connected:
                try:
                    await self._client.disconnect()
                finally:
                    self._client = None

    # -------------------------------------------------------------------------
    # Core send path
    # -------------------------------------------------------------------------
    async def send_command(self, command: bytearray, *, response: bool = True) -> None:
        """Send a command using a short-lived persistent connection (idle disconnect)."""
        async with self._is_connecting:
            # If already connected, reuse it and cancel pending idle disconnect.
            if self._client and self._client.is_connected:
                self._cancel_idle_disconnect()
                LOGGER.debug("Client already connected, sending command directly.")
                try:
                    LOGGER.debug("Sending command: %s", command.hex())
                    await asyncio.wait_for(
                        self._client.write_gatt_char(GIRA_WRITE_CHAR_UUID, command, response=response),
                        timeout=self._write_timeout_s,
                    )
                    self._schedule_idle_disconnect()
                    return
                except (BleakError, asyncio.TimeoutError) as e:
                    LOGGER.warning("Failed to send command to connected device: %s", e)
                    # Force a clean reconnect
                    try:
                        await self._client.disconnect()
                    except Exception:
                        pass
                    self._client = None

            # Not connected -> connect
            LOGGER.debug("Attempting to connect to %s (%s) to send command.", self.name, self.address)

            device = bluetooth.async_ble_device_from_address(self.hass, self.address)
            if not device:
                LOGGER.error("Device %s (%s) not found in Bluetooth registry.", self.name, self.address)
                raise UpdateFailed(f"Device {self.name} not found.")

            try:
                client = await establish_connection(
                    BleakClient,
                    device,
                    self.name,
                    pair=True,
                    timeout=5,
                    max_attempts=3,
                )
                self._client = client
                LOGGER.info("Successfully connected to %s (%s).", self.name, self.address)

                LOGGER.debug("Sending command: %s", command.hex())
                await asyncio.wait_for(
                    client.write_gatt_char(GIRA_WRITE_CHAR_UUID, command, response=response),
                    timeout=self._write_timeout_s,
                )
                LOGGER.info("Command sent successfully to %s.", self.name)

                # Keep link open briefly for rapid successive commands
                self._schedule_idle_disconnect()

            except (BleakError, asyncio.TimeoutError) as e:
                LOGGER.error("Failed to connect or send command to %s (%s): %s", self.name, self.address, e)
                # Clean up
                try:
                    if self._client and self._client.is_connected:
                        await self._client.disconnect()
                except Exception:
                    pass
                self._client = None
                raise UpdateFailed(f"Failed to connect and send command to {self.name}: {e}") from e

    async def send_set_position_command(self, position_u8: int) -> None:
        """Send absolute position command to the shutter. The device expects one byte 0x00..0xFF (mapped from 0..100% in the cover entity)."""
        pos = int(position_u8)
        if pos < 0:
            pos = 0
        if pos > 0xFF:
            pos = 0xFF
        await self.send_command(_generate_command(SHUTTER_PROPERTY_ID_SET_POSITION, pos))

    async def send_shutter_up_command(self) -> None:
        """Send the command to raise the shutter."""
        await self.send_command(_generate_command(SHUTTER_PROPERTY_ID_MOVE, SHUTTER_VALUE_UP))

    async def send_shutter_down_command(self) -> None:
        """Send the command to lower the shutter."""
        await self.send_command(_generate_command(SHUTTER_PROPERTY_ID_MOVE, SHUTTER_VALUE_DOWN))

    async def send_shutter_stop_command(self) -> None:
        """Stop shutter movement (property 0xFD, value 0x00)."""
        cmd = _generate_command(SHUTTER_PROPERTY_ID_STOP, SHUTTER_VALUE_STOP)
        await self.send_command(cmd, response=True)

    async def send_thermostat_set_target_temperature(self, temp_c: float) -> None:
        """Set thermostat target temperature (°C) using device-specific WRITE encoding.

        raw_u16 = round((21 + temp_c) * 50 + 1000)
        """
        raw = int(round((21.0 + float(temp_c)) * 50.0 + 1000.0))

        if raw < 0:
            raw = 0
        if raw > 0xFFFF:
            raw = 0xFFFF

        hi = (raw >> 8) & 0xFF
        lo = raw & 0xFF

        cmd = bytearray([
            0xF6, 0x00, 0x65, 0x01,
            THERMO_PROPERTY_ID_TARGET_TEMP,  # 0xF5
            0x10, 0x01,
            hi, lo
        ])

        await self.send_command(cmd, response=True)


    async def send_thermostat_timer_heat(self, start: bool) -> None:
        """Start/stop heating timer (property 0xFE)."""
        cmd = _generate_thermo_u8_command(
            THERMO_PROPERTY_ID_TIMER_HEAT,
            THERMO_VALUE_START if start else THERMO_VALUE_STOP,
        )
        await self.send_command(cmd, response=False)

    async def send_thermostat_step(self, up: bool) -> None:
        """Step target temperature by ±0.5°C (property 0xF6)."""
        cmd = _generate_thermo_u8_command(
            THERMO_PROPERTY_ID_STEP,
            0x01 if up else 0x00,
        )
        await self.send_command(cmd, response=False)
        
    async def async_close(self) -> None:
        """Close/disconnect the BLE client."""
        await self._disconnect_now()
        