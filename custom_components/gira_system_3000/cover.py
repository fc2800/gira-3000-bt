"""Platform for the Gira 3000 BT System cover integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    UpdateFailed,
)

from .const import DOMAIN, LOGGER
from .gira_ble import GiraBLEClient, GiraPassiveBluetoothDataUpdateCoordinator
from .shutter_geometry import (
    CONF_WINDOW_HEIGHT, CONF_CORE_RADIUS, CONF_LAYER_THICKNESS,
    CONF_SLAT_HEIGHT, CONF_SLAT_GAP, GEOMETRY_OPTIONS, ShutterGeometry,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gira 3000 BT System cover from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: GiraPassiveBluetoothDataUpdateCoordinator = data["coordinator"]
    client: GiraBLEClient = data["client"]

    # Add the Gira shutter as a Home Assistant Cover entity
    cover_entity = GiraSystem3000Cover(coordinator, client, config_entry)
    async_add_entities([cover_entity])
    
    LOGGER.debug("Coordinator setup complete for %s", config_entry.title)


class GiraSystem3000Cover(
    CoordinatorEntity[GiraPassiveBluetoothDataUpdateCoordinator], CoverEntity
):
    """Representation of a Gira System 3000 Cover."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )
    _attr_assumed_state = False

    def __init__(
        self,
        coordinator: GiraPassiveBluetoothDataUpdateCoordinator,
        client: GiraBLEClient,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the cover."""
        super().__init__(coordinator)
        self._client = client
        self._config_entry = config_entry
        self._geometry = self._read_geometry()
        self._attr_unique_id = config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=client.name,
            connections={(config_entry.entry_id, client.address)},
        )
        self._attr_current_cover_position = None  # Initialize the state to None
        LOGGER.debug("Created cover entity for %s", client.name)

    def _read_geometry(self) -> ShutterGeometry | None:
        """Missing/zero/invalid height preserves the original mapping."""
        try:
            options = self._config_entry.options
            return ShutterGeometry(
                options.get(CONF_WINDOW_HEIGHT, 0),
                core_radius=options.get(CONF_CORE_RADIUS, GEOMETRY_OPTIONS[CONF_CORE_RADIUS][0]),
                layer_thickness=options.get(CONF_LAYER_THICKNESS, GEOMETRY_OPTIONS[CONF_LAYER_THICKNESS][0]),
                slat_height=options.get(CONF_SLAT_HEIGHT, GEOMETRY_OPTIONS[CONF_SLAT_HEIGHT][0]),
                slat_gap=options.get(CONF_SLAT_GAP, GEOMETRY_OPTIONS[CONF_SLAT_GAP][0]),
            )
        except (TypeError, ValueError, OverflowError):
            return None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self._config_entry.add_update_listener(self._async_options_updated)
        )

    async def _async_options_updated(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._geometry = self._read_geometry()
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        # A passive bluetooth device is always available as long as it's running
        return True

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        try:
            await self._client.send_shutter_up_command()
        except UpdateFailed:
            self._attr_available = False
            self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        try:
            await self._client.send_shutter_down_command()
        except UpdateFailed:
            self._attr_available = False
            self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        try:
            await self._client.send_shutter_stop_command()
        except UpdateFailed:
            self._attr_available = False
            self.async_write_ha_state()


    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set the cover to a specific position (0-100%)."""
        position = kwargs.get("position")
        if position is None:
            return
        try:
            position_pct = int(position)
        except (TypeError, ValueError):
            return

        if position_pct < 0:
            position_pct = 0
        if position_pct > 100:
            position_pct = 100

        if self._geometry is not None:
            position_pct = self._geometry.to_device(position_pct)

        # Map device 0..100% -> 0xFF..0x00 (closed..open)
        pos_u8 = 255 - round(position_pct * 255 / 100)

        try:
            await self._client.send_set_position_command(pos_u8)
        except UpdateFailed:
            self._attr_available = False
            self.async_write_ha_state()

    @property
    def current_cover_position(self) -> int | None:
        """Return the current position of the cover."""
        # Return the cached state attribute
        position = self._attr_current_cover_position
        if position is None or self._geometry is None:
            return position
        return round(self._geometry.to_opening(position))

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed or not."""
        # Zero free opening can still have open slat gaps. Only the device's
        # closed endpoint means fully closed.
        position = self._attr_current_cover_position
        if position is None:
            return None
        return position == 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.coordinator.data is not None:
            new_position = self.coordinator.data.get("position")
            # Only update the state if a new position is available
            if new_position is not None:
                self._attr_current_cover_position = new_position
                LOGGER.debug(
                    "Cover entity received update. New position: %s",
                    self.current_cover_position,
                )
        self.async_write_ha_state()
