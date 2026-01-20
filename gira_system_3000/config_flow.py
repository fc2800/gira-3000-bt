from __future__ import annotations
"""Config flow for Gira 3000 BT System integration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.device_registry import format_mac
from bleak import BleakClient, BleakError

from .const import DOMAIN
from .gira_ble import GiraBLEClient

_LOGGER = logging.getLogger(__name__)

# Supported device types. Used to select the correct command set/platform.
DEVICE_TYPES = {
    "shutter": "Shutter / Jalousie",
    "thermostat": "Thermostat",
    "sensor": "Sensor (read-only)",
}

class GiraSystem3000ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gira 3000 BT System."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_device_info: BluetoothServiceInfoBleak | None = None
        self._discovered_address: str | None = None
        self._discovered_name: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        _LOGGER.debug("Bluetooth discovery_info: %s", discovery_info)

        address = discovery_info.address
        # Create a more descriptive name for the discovery card
        name = f"{discovery_info.name} ({address[-5:].replace(':', '')})"

        unique_id = format_mac(address)
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        self._discovered_address = address
        self._discovered_name = name

        # Redirect to the new `name` step to allow the user to change the name
        self.context["title_placeholders"] = {"name": name}
        return await self.async_step_name()

    async def async_step_name(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Allow the user to name the discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # User submitted the form, validate and create the entry
            address = user_input["address"]
            name = user_input.get("name", self._discovered_name)

            unique_id = format_mac(address)
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=name,
                data={
                    "address": address,
                    "name": name,
                    "device_type": user_input["device_type"],
                }, 
            )
        
        # Show the form
        return self.async_show_form(
            step_id="name",
            data_schema=vol.Schema({
                vol.Required("address", default=self._discovered_address): str,
                vol.Required("name", default=self._discovered_name): str,
                vol.Required("device_type", default="shutter"): vol.In(DEVICE_TYPES),
            }),
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step when user manually adds the integration."""
        # This step remains for manual setup and does not change.
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input["address"]
            name = user_input.get("name")
            
            unique_id = format_mac(address)
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=name or f"Gira Shutter {address[-5:].replace(':', '')}",
                data={
                    "address": address,
                    "name": name,
                    "device_type": user_input["device_type"],
                },
            )

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({
                vol.Required("address"): str,
                vol.Required("name"): str,
                vol.Required("device_type", default="shutter"): 
                    vol.In(DEVICE_TYPES),
            }), errors=errors
        )

    @callback
    def _async_abort_if_device_already_configured(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> None:
        """Abort if the device is already configured."""
        pass
