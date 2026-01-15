"""Sensor platform for Gira System 3000 BT (read-only sensor devices)."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .gira_ble import GiraPassiveBluetoothDataUpdateCoordinator


@dataclass(frozen=True)
class _Runtime:
    coordinator: GiraPassiveBluetoothDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up read-only Gira sensors."""
    data = hass.data[DOMAIN][entry.entry_id]
    runtime = _Runtime(coordinator=data["coordinator"])

    async_add_entities(
        [
            GiraTemperatureSensor(runtime, entry),
            GiraBrightnessSensor(runtime, entry),
        ]
    )


class _Base(CoordinatorEntity[GiraPassiveBluetoothDataUpdateCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, runtime: _Runtime, entry: ConfigEntry) -> None:
        super().__init__(runtime.coordinator)
        self._entry = entry
        self._base_name = entry.data.get("name", "Gira Sensor")

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data)


class GiraTemperatureSensor(_Base):
    _attr_device_class = "temperature"
    _attr_native_unit_of_measurement = "°C"
    _attr_state_class = "measurement"

    def __init__(self, runtime: _Runtime, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.unique_id}_temp"
        self._attr_name = f"{self._base_name} Temperatur"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("sensor_temperature")


class GiraBrightnessSensor(_Base):
    _attr_device_class = "illuminance"
    _attr_native_unit_of_measurement = "lx"
    _attr_state_class = "measurement"

    def __init__(self, runtime: _Runtime, entry: ConfigEntry) -> None:
        super().__init__(runtime, entry)
        self._attr_unique_id = f"{entry.unique_id}_lux"
        self._attr_name = f"{self._base_name} Helligkeit"

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("sensor_brightness")
