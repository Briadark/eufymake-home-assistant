"""The eufyMake E1 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_AUTH_TOKEN, CONF_DEVICE_SN, DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SELECT, Platform.UPDATE]
STALE_E1_CONTROL_ENTITIES: tuple[tuple[Platform, str], ...] = (
    (Platform.SENSOR, "notification_sound"),
    (Platform.SENSOR, "notification_sound_level"),
    (Platform.SENSOR, "fill_light"),
    (Platform.SENSOR, "fill_light_level"),
    (Platform.SWITCH, "notification_sound"),
    (Platform.SWITCH, "fill_light"),
    (Platform.SELECT, "notification_sound_level"),
    (Platform.SELECT, "fill_light_level"),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eufyMake E1 from a config entry."""
    from .coordinator import EufyMakeE1Coordinator

    _async_start_cloud_auth_reauth_if_needed(hass, entry)
    _async_remove_stale_e1_control_entities(hass, entry)

    coordinator = EufyMakeE1Coordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


def _async_start_cloud_auth_reauth_if_needed(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Start Home Assistant's normal reauth flow for legacy config entries."""
    if not entry.data.get(CONF_AUTH_TOKEN):
        entry.async_start_reauth(hass)


def _async_remove_stale_e1_control_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Remove experimental E1 control entities from older installs."""
    device_sn = entry.data.get(CONF_DEVICE_SN)
    if not device_sn:
        return

    registry = er.async_get(hass)
    for platform, suffix in STALE_E1_CONTROL_ENTITIES:
        entity_id = registry.async_get_entity_id(
            platform,
            DOMAIN,
            f"{device_sn}_{suffix}",
        )
        if entity_id is not None:
            registry.async_remove(entity_id)
