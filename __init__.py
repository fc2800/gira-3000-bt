"""The Gira System 3000 integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, LOGGER
from .gira_ble import GiraBLEClient, GiraPassiveBluetoothDataUpdateCoordinator


def _platforms_for_device_type(device_type: str) -> list[str]:
    """Map device_type to HA platforms."""
    if device_type == "shutter":
        return ["cover"]
    if device_type == "thermostat":
        return ["climate"]
    if device_type == "sensor":
        return ["sensor"]
    # Safe default
    return ["cover"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gira System 3000 from a config entry."""
    address: str = entry.data["address"]
    name: str = entry.data.get("name", f"Gira {address[-5:].replace(':', '')}")

    # Backward compatible: if the field is missing, treat as shutter.
    device_type: str = entry.data.get("device_type", "shutter")
    platforms = _platforms_for_device_type(device_type)

    # Coordinator (passive broadcasts)
    coordinator = GiraPassiveBluetoothDataUpdateCoordinator(
        hass,
        address=address,
        name=name,
        device_type=device_type,
    )

    # Client (active command sender)
    client = GiraBLEClient(hass, address, name)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
        "device_type": device_type,
    }

    # Forward only the platform(s) for this device type.
    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    # Start listening only after entities are set up and subscribed.
    entry.async_on_unload(coordinator.async_start())

    LOGGER.debug("Setup complete: %s (%s) type=%s platforms=%s", name, address, device_type, platforms)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    device_type: str = data.get("device_type", entry.data.get("device_type", "shutter"))
    platforms = _platforms_for_device_type(device_type)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if not unload_ok:
        return False

    # Best-effort cleanup
    client = data.get("client")
    if client is not None:
        try:
            await client.async_close()
        except Exception:
            LOGGER.debug("BLE client close raised (ignored)", exc_info=True)

    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True
