"""Climate platform for Gira 3000 BT System thermostats."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import time
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    PRESET_BOOST,
    PRESET_NONE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LOGGER, THERMO_BOOST_DURATION_SECONDS
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
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = [PRESET_NONE, PRESET_BOOST]
    # HEAT denotes setpoint regulation, not a command to start the boost timer.
    # No real device OFF command has been implemented by this integration.
    _attr_hvac_modes = [HVACMode.HEAT]
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

        self._attr_preset_mode: str | None = None
        self._preset_lock = asyncio.Lock()
        self._boost_timer: asyncio.TimerHandle | None = None
        self._boost_generation = 0
        self._boost_deadline: float | None = None
        self._boost_ends_at: str | None = None
        self._boost_status_source = "unknown"
        self._last_boost_report_id = 0
        self._last_boost_seconds: int | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._client.async_add_thermostat_listener(
            self.coordinator.async_handle_thermostat_data
        ))
        self.async_on_remove(self._cancel_boost_timer)
        self._consume_boost_report()

    def _cancel_boost_timer(self) -> None:
        self._boost_generation += 1
        if self._boost_timer is not None:
            self._boost_timer.cancel()
            self._boost_timer = None

    def _set_boost_state(self, active: bool, deadline: float | None, source: str) -> None:
        self._cancel_boost_timer()
        self._attr_preset_mode = PRESET_BOOST if active else PRESET_NONE
        self._boost_status_source = source
        self._boost_deadline = deadline if active else None
        self._boost_ends_at = None
        if active and deadline is not None:
            remaining = max(0.0, deadline - time.monotonic())
            self._boost_ends_at = (
                datetime.now(timezone.utc) + timedelta(seconds=remaining)
            ).isoformat()
            self._boost_timer = self.hass.loop.call_later(
                remaining, self._boost_expired, self._boost_generation
            )

    def _boost_expired(self, generation: int) -> None:
        if generation != self._boost_generation:
            return
        # This changes only the displayed estimate. The device owns its timer;
        # do not send a late stop that could cancel a separately started boost.
        self._boost_timer = None
        self._set_boost_state(False, None, "estimated_expiry")
        self.async_write_ha_state()

    def _consume_boost_report(self) -> None:
        data = self.coordinator.data or {}
        report_id = data.get("boost_report_id", 0)
        if report_id == self._last_boost_report_id:
            return
        self._last_boost_report_id = report_id
        if not data["boost_active"]:
            self._last_boost_seconds = 0
            self._set_boost_state(False, None, "device")
            return
        seconds = data.get("boost_remaining_seconds")
        deadline = data["boost_report_received_at"] + (
            seconds if seconds is not None else THERMO_BOOST_DURATION_SECONDS
        )
        if self._boost_deadline is not None and (
            seconds is None or (
                self._last_boost_seconds is not None and seconds <= self._last_boost_seconds
            )
        ):
            # Repeated state/temperature broadcasts must not restart a timer.
            deadline = min(deadline, self._boost_deadline)
        if seconds is not None:
            self._last_boost_seconds = seconds
        self._set_boost_state(True, deadline, "device")

    def _handle_coordinator_update(self) -> None:
        self._consume_boost_report()
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Use the device's Quick-Heat timer independently of HVAC mode."""
        if preset_mode not in self._attr_preset_modes:
            raise ServiceValidationError(f"Gira preset {preset_mode!r} is not supported.")
        async with self._preset_lock:
            previous_report = (self.coordinator.data or {}).get("boost_report_id", 0)
            start = preset_mode == PRESET_BOOST
            await self._client.send_thermostat_timer_heat(start=start)
            feedback = self.coordinator.data or {}
            if (feedback.get("boost_report_id", 0) != previous_report
                    and feedback.get("boost_active") == start):
                # Keep matching feedback arriving during the write. A newly
                # subscribed connection may first report the pre-command state.
                self._consume_boost_report()
            else:
                self._last_boost_seconds = None
                self._set_boost_state(
                    start,
                    time.monotonic() + THERMO_BOOST_DURATION_SECONDS if start else None,
                    "command",
                )
            self.async_write_ha_state()

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
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Expose the temperature comparison separately from actual activity.

        BLE currently provides temperatures but no relay/valve feedback. Leave
        hvac_action unset rather than report this estimate as device activity.
        """
        cur = self.current_temperature
        tgt = self.target_temperature
        if cur is None or tgt is None:
            demand = None
        else:
            demand = "heating" if cur < (tgt - 0.2) else "idle"
        return {
            "estimated_heating_demand": demand,
            "boost_status_source": self._boost_status_source,
            "boost_ends_at": self._boost_ends_at,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Accept setpoint regulation without sending a timer command."""
        if hvac_mode != HVACMode.HEAT:
            raise ServiceValidationError(
                f"Gira HVAC mode {hvac_mode!r} is not supported. "
                "Use a lower target temperature for setback."
            )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        # Also guard mode requests supplied through climate.set_temperature.
        if (hvac_mode := kwargs.get("hvac_mode")) is not None:
            await self.async_set_hvac_mode(hvac_mode)

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
