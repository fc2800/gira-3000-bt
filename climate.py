"""Climate platform for Gira 3000 BT System thermostats."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER
from .gira_ble import GiraBLEClient, GiraPassiveBluetoothDataUpdateCoordinator


@dataclass(frozen=True)
class _Runtime:
    client: GiraBLEClient
    coordinator: GiraPassiveBluetoothDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up thermostat entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    runtime = _Runtime(client=data["client"], coordinator=data["coordinator"])
    async_add_entities([GiraThermostat(runtime, entry)])


class GiraThermostat(CoordinatorEntity[GiraPassiveBluetoothDataUpdateCoordinator], ClimateEntity):
    """Gira thermostat (setpoint control)."""

    _attr_has_entity_name = True
    _attr_supported_features = (ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON)
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_temperature_unit = "°C"

    def __init__(self, runtime: _Runtime, entry: ConfigEntry) -> None:
        super().__init__(runtime.coordinator)
        self._client = runtime.client
        self._entry = entry

        self._attr_unique_id = entry.unique_id
        self._attr_name = entry.data.get("name", "Gira Thermostat")

        self._attr_min_temp = 5.0
        self._attr_max_temp = 30.0
        self._attr_target_temperature_step = 0.5

    @property
    def device_info(self) -> DeviceInfo:
        """Return device metadata for the HA device registry."""
        # Use the config entry unique_id (MAC formatted) as stable identifier
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.unique_id or self._entry.entry_id)},
            name=self._attr_name,
            manufacturer="Gira",
            model="System 3000 BT Thermostat",
        )

    @property
    def available(self) -> bool:
        # Consider available when we have at least one parsed value
        return True

    @property
    def current_temperature(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("current_temperature")

    @property
    def target_temperature(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("target_temperature")

    @property
    def hvac_action(self) -> HVACAction | None:
        # Display "Idle"/"Heating" similar to your 3rd screenshot.
        cur = self.current_temperature
        tgt = self.target_temperature
        if cur is None or tgt is None:
            return None
        # simple hysteresis to avoid flicker
        if cur < (tgt - 0.2):
            return HVACAction.HEATING
        return HVACAction.IDLE

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode (best-effort).

        Mapping:
        - HEAT: start heating timer
        - OFF:  stop heating timer
        """
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

        if hvac_mode == HVACMode.HEAT:
            await self._client.send_thermostat_timer_heat(start=True)
        elif hvac_mode == HVACMode.OFF:
            await self._client.send_thermostat_timer_heat(start=False)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get("temperature")
        if temp is None:
            return
        try:
            temp_c = float(temp)
        except (TypeError, ValueError):
            return

        if temp_c < self._attr_min_temp:
            temp_c = self._attr_min_temp
        if temp_c > self._attr_max_temp:
            temp_c = self._attr_max_temp

        LOGGER.debug("Thermostat setpoint request: %.2f°C (%s)", temp_c, self._attr_name)

        current_target = self.target_temperature
        if current_target is not None:
            delta = round(temp_c - float(current_target), 2)
            if delta == 0.5:
                data = dict(self.coordinator.data or {})
                data["target_temperature"] = temp_c
                self.coordinator.data = data
                self.coordinator.async_update_listeners()
                await self._client.send_thermostat_step(up=True)
                return
            if delta == -0.5:
                data = dict(self.coordinator.data or {})
                data["target_temperature"] = temp_c
                self.coordinator.data = data
                self.coordinator.async_update_listeners()
                await self._client.send_thermostat_step(up=False)
                return

        data = dict(self.coordinator.data or {})
        data["target_temperature"] = temp_c
        self.coordinator.data = data
        self.coordinator.async_update_listeners()

        await self._client.send_thermostat_set_target_temperature(temp_c)
