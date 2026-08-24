"""Switch platform for eufyMake E1."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_SN, DOMAIN
from .coordinator import EufyMakeE1Coordinator
from .device_info import e1_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eufyMake E1 switch entities."""
    coordinator: EufyMakeE1Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            EufyMakeE1NotificationSoundSwitch(coordinator, entry),
            EufyMakeE1FillLightSwitch(coordinator, entry),
        ]
    )


class EufyMakeE1NotificationSoundSwitch(
    CoordinatorEntity[EufyMakeE1Coordinator],
    SwitchEntity,
):
    """Notification sound toggle for a eufyMake E1."""

    _attr_has_entity_name = True
    _attr_name = "Notification sound"

    def __init__(self, coordinator: EufyMakeE1Coordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        device_sn = entry.data[CONF_DEVICE_SN]
        self._attr_unique_id = f"{device_sn}_notification_sound"
        self._attr_device_info = e1_device_info(entry, coordinator.data)

    @property
    def is_on(self) -> bool | None:
        """Return whether notification sound is enabled."""
        return _control_state(self.coordinator.data or {}, "notification_sound").get(
            "enabled"
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn notification sound on."""
        await self.coordinator.async_set_notification_sound_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn notification sound off."""
        await self.coordinator.async_set_notification_sound_enabled(False)


class EufyMakeE1FillLightSwitch(
    CoordinatorEntity[EufyMakeE1Coordinator],
    SwitchEntity,
):
    """Fill-in light toggle for a eufyMake E1."""

    _attr_has_entity_name = True
    _attr_name = "Fill-in light"

    def __init__(self, coordinator: EufyMakeE1Coordinator, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        device_sn = entry.data[CONF_DEVICE_SN]
        self._attr_unique_id = f"{device_sn}_fill_light"
        self._attr_device_info = e1_device_info(entry, coordinator.data)

    @property
    def is_on(self) -> bool | None:
        """Return whether fill-in light is enabled."""
        return _control_state(self.coordinator.data or {}, "fill_light").get("enabled")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn fill-in light on."""
        await self.coordinator.async_set_fill_light_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn fill-in light off."""
        await self.coordinator.async_set_fill_light_enabled(False)


def _control_state(data: dict[str, Any], key: str) -> dict[str, Any]:
    controls = data.get("e1_controls", {})
    if not isinstance(controls, dict):
        return {}
    state = controls.get(key, {})
    return state if isinstance(state, dict) else {}
