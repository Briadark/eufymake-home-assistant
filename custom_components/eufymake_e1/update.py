"""Update platform for eufyMake E1."""

from __future__ import annotations

from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityFeature,
)
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
    """Set up eufyMake update entities."""
    coordinator: EufyMakeE1Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EufyMakeE1FirmwareUpdate(coordinator, entry)])


class EufyMakeE1FirmwareUpdate(
    CoordinatorEntity[EufyMakeE1Coordinator],
    UpdateEntity,
):
    """Read-only firmware update entity for a eufyMake E1."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_has_entity_name = True
    _attr_name = "Firmware"
    _attr_translation_key = "firmware"
    _attr_supported_features = UpdateEntityFeature.PROGRESS

    def __init__(self, coordinator: EufyMakeE1Coordinator, entry: ConfigEntry) -> None:
        """Initialize the firmware update entity."""
        super().__init__(coordinator)
        device_sn = entry.data[CONF_DEVICE_SN]
        self._attr_unique_id = f"{device_sn}_firmware_update"
        self._attr_device_info = e1_device_info(entry, coordinator.data)

    @property
    def title(self) -> str:
        """Return the update title."""
        return "eufyMake E1 firmware"

    @property
    def installed_version(self) -> str | None:
        """Return the installed firmware version."""
        update = _firmware_update(self.coordinator.data or {})
        return _string_or_none(
            update.get("current_version")
            or (self.coordinator.data or {}).get("firmware_version")
        )

    @property
    def latest_version(self) -> str | None:
        """Return the latest available firmware version."""
        update = _firmware_update(self.coordinator.data or {})
        target = _string_or_none(update.get("target_version"))
        if target:
            return target
        return self.installed_version

    @property
    def in_progress(self) -> bool | None:
        """Return whether a firmware update is in progress."""
        value = _firmware_update(self.coordinator.data or {}).get("active")
        return value if isinstance(value, bool) else None

    @property
    def update_percentage(self) -> int | None:
        """Return firmware update progress percentage."""
        update = _firmware_update(self.coordinator.data or {})
        progress = update.get("upgrade_progress")
        if progress is None:
            progress = update.get("download_progress")
        return _progress_or_none(progress)

    @property
    def release_summary(self) -> str | None:
        """Return a short release summary."""
        note = _string_or_none(
            _firmware_update(self.coordinator.data or {}).get("release_note")
        )
        if note is None:
            return None
        summary = " ".join(note.split())
        if len(summary) <= 255:
            return summary
        return f"{summary[:252]}..."

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra firmware update attributes."""
        update = _firmware_update(self.coordinator.data or {})
        return _clean_attributes(
            {
                "available": update.get("available"),
                "forced": update.get("forced"),
                "upgrade_flag": update.get("upgrade_flag"),
                "download_progress": update.get("download_progress"),
                "upgrade_progress": update.get("upgrade_progress"),
                "speed": update.get("speed"),
                "file_size": update.get("file_size"),
                "upgrade_result": update.get("upgrade_result"),
                "error_code": update.get("error_code"),
                "reply": update.get("reply"),
                "release_note": update.get("release_note"),
            }
        )


def _firmware_update(data: dict[str, Any]) -> dict[str, Any]:
    update = data.get("firmware_update", {})
    return update if isinstance(update, dict) else {}


def _progress_or_none(value: Any) -> int | None:
    try:
        progress = int(value)
    except (TypeError, ValueError):
        return None
    return max(0, min(100, progress))


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    string = str(value)
    return string if string else None


def _clean_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in attributes.items()
        if value is not None
    }
