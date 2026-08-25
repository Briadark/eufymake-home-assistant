"""Sensor platform for eufyMake E1."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_SN, DOMAIN
from .coordinator import EufyMakeE1Coordinator
from .device_info import e1_device_info, p1_device_info


@dataclass(frozen=True, kw_only=True)
class EufyMakeSensorDescription(SensorEntityDescription):
    """Describe a eufyMake E1 sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _ink_value(data: dict[str, Any], channel: str) -> Any:
    ink = data.get("ink", {})
    if not isinstance(ink, dict):
        return None
    return ink.get(channel)


def _ink_value_fn(channel: str) -> Callable[[dict[str, Any]], Any]:
    return lambda data: _ink_value(data, channel)


def _ink_attributes_fn(channel: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    return lambda data: _ink_attributes(data, channel)


def _ink_detail_value_fn(channel: str, key: str) -> Callable[[dict[str, Any]], Any]:
    return lambda data: _ink_attributes(data, channel).get(key)


def _ink_status_value_fn(channel: str) -> Callable[[dict[str, Any]], str | None]:
    return lambda data: _map_ink_status(_ink_attributes(data, channel))


def _ink_status_attributes_fn(channel: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    return lambda data: {
        "raw_status": _ink_attributes(data, channel).get("status"),
        "expired": _ink_attributes(data, channel).get("expired"),
    }


def _ink_date_fn(channel: str, key: str) -> Callable[[dict[str, Any]], date | None]:
    return lambda data: _date_value(_ink_attributes(data, channel), key)


def _ink_attributes(data: dict[str, Any], channel: str) -> dict[str, Any]:
    details = data.get("ink_details", {})
    if not isinstance(details, dict):
        return {}
    attributes = details.get(channel, {})
    return attributes if isinstance(attributes, dict) else {}


def _waste_ink_attributes(data: dict[str, Any]) -> dict[str, Any]:
    attributes = data.get("waste_ink_details", {})
    return attributes if isinstance(attributes, dict) else {}


def _accessory_attributes(data: dict[str, Any]) -> dict[str, Any]:
    attributes = data.get("current_accessory_details", {})
    return attributes if isinstance(attributes, dict) else {}


def _print_status_attributes(data: dict[str, Any]) -> dict[str, Any]:
    attributes = data.get("print_status_details", {})
    if not isinstance(attributes, dict):
        attributes = {}
    design_preparation = _design_preparation(data)
    file_transfer = _file_transfer(data)
    injection = _ink_injection(data)
    recovery = _white_ink_recovery(data)
    status_check = _status_check(data)
    test_print = _test_print(data)
    print_job = _print_job(data)
    return {
        **attributes,
        "design_preparation_active": design_preparation.get("active"),
        "design_preparation_progress": design_preparation.get("progress"),
        "design_preparation_height": design_preparation.get("height"),
        "design_preparation_plate_type": design_preparation.get("plate_type"),
        "design_preparation_plate_print_width": design_preparation.get(
            "plate_print_width"
        ),
        "design_preparation_plate_print_height": design_preparation.get(
            "plate_print_height"
        ),
        "file_transfer_active": file_transfer.get("active"),
        "file_transfer_progress": file_transfer.get("progress"),
        "file_transfer_result": file_transfer.get("result"),
        "ink_injection_active": injection.get("active"),
        "ink_injection_progress": injection.get("progress"),
        "white_ink_recovery_active": recovery.get("active"),
        "white_ink_recovery_progress": recovery.get("progress"),
        "status_check_active": status_check.get("active"),
        "status_check_progress": status_check.get("progress"),
        "test_print_active": test_print.get("active"),
        "test_print_progress": test_print.get("progress"),
        "print_job_active": print_job.get("active"),
        "print_job_progress": print_job.get("progress"),
        "print_job_remaining_time": print_job.get("remaining_time"),
        "print_job_elapsed_time": print_job.get("elapsed_time"),
    }


def _print_progress(data: dict[str, Any]) -> Any:
    for action in (
        _design_preparation(data),
        _file_transfer(data),
        _ink_injection(data),
        _white_ink_recovery(data),
        _status_check(data),
        _test_print(data),
        _print_job(data),
    ):
        if action.get("active"):
            return action.get("progress")
    return None


def _design_preparation(data: dict[str, Any]) -> dict[str, Any]:
    design_preparation = data.get("design_preparation", {})
    return design_preparation if isinstance(design_preparation, dict) else {}


def _file_transfer(data: dict[str, Any]) -> dict[str, Any]:
    file_transfer = data.get("file_transfer", {})
    return file_transfer if isinstance(file_transfer, dict) else {}


def _ink_injection(data: dict[str, Any]) -> dict[str, Any]:
    injection = data.get("ink_injection", {})
    return injection if isinstance(injection, dict) else {}


def _white_ink_recovery(data: dict[str, Any]) -> dict[str, Any]:
    recovery = data.get("white_ink_recovery", {})
    return recovery if isinstance(recovery, dict) else {}


def _status_check(data: dict[str, Any]) -> dict[str, Any]:
    status_check = data.get("status_check", {})
    return status_check if isinstance(status_check, dict) else {}


def _test_print(data: dict[str, Any]) -> dict[str, Any]:
    test_print = data.get("test_print", {})
    return test_print if isinstance(test_print, dict) else {}


def _print_job(data: dict[str, Any]) -> dict[str, Any]:
    print_job = data.get("print_job", {})
    return print_job if isinstance(print_job, dict) else {}


def _purifier(data: dict[str, Any]) -> dict[str, Any]:
    purifier = data.get("purifier", {})
    return purifier if isinstance(purifier, dict) else {}


def _purifier_state(data: dict[str, Any]) -> dict[str, Any]:
    state = _purifier(data).get("state", {})
    return state if isinstance(state, dict) else {}


def _purifier_value_fn(key: str) -> Callable[[dict[str, Any]], Any]:
    return lambda data: _purifier(data).get(key)


def _purifier_state_value_fn(key: str) -> Callable[[dict[str, Any]], Any]:
    return lambda data: _purifier_state(data).get(key)


def _e1_control_state(data: dict[str, Any], key: str) -> dict[str, Any]:
    controls = data.get("e1_controls", {})
    if not isinstance(controls, dict):
        return {}
    state = controls.get(key, {})
    return state if isinstance(state, dict) else {}


def _purifier_mode(data: dict[str, Any]) -> str | None:
    return _map_purifier_mode(_purifier_state(data).get("work_mode"))


def _purifier_work_status(data: dict[str, Any]) -> str | None:
    return _map_purifier_work_status(_purifier_state(data).get("work_status"))


def _purifier_filter_status(data: dict[str, Any]) -> str | None:
    return _map_purifier_filter_status(_purifier_state(data).get("filter_status"))


def _date_value(attributes: dict[str, Any], key: str) -> date | None:
    value = attributes.get(key)
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


INK_CHANNELS: tuple[tuple[str, str], ...] = (
    ("C", "Cyan"),
    ("M", "Magenta"),
    ("Y", "Yellow"),
    ("K", "Black"),
    ("W", "White"),
    ("G", "Gloss"),
)


BASE_SENSORS: tuple[EufyMakeSensorDescription, ...] = (
    EufyMakeSensorDescription(
        key="availability",
        name="Availability",
        translation_key="availability",
        value_fn=lambda data: data.get("availability"),
    ),
    EufyMakeSensorDescription(
        key="print_status",
        name="Print status",
        translation_key="print_status",
        value_fn=lambda data: data.get("print_status"),
        attributes_fn=_print_status_attributes,
    ),
    EufyMakeSensorDescription(
        key="firmware_version",
        name="Firmware version",
        translation_key="firmware_version",
        value_fn=lambda data: data.get("firmware_version"),
    ),
    EufyMakeSensorDescription(
        key="current_accessory",
        name="Current accessory",
        translation_key="current_accessory",
        value_fn=lambda data: data.get("current_accessory"),
        attributes_fn=_accessory_attributes,
    ),
    EufyMakeSensorDescription(
        key="print_progress",
        name="Print progress",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_print_progress,
    ),
)


INK_SENSORS: tuple[EufyMakeSensorDescription, ...] = tuple(
    description
    for channel, name in INK_CHANNELS
    for description in (
        EufyMakeSensorDescription(
            key=f"ink_{channel.lower()}",
            name=f"{name} ink",
            translation_key=f"ink_{channel.lower()}",
            native_unit_of_measurement=PERCENTAGE,
            value_fn=_ink_value_fn(channel),
            attributes_fn=_ink_attributes_fn(channel),
        ),
        EufyMakeSensorDescription(
            key=f"ink_{channel.lower()}_expiration_date",
            name=f"{name} ink expiration date",
            device_class=SensorDeviceClass.DATE,
            value_fn=_ink_date_fn(channel, "expiration_date"),
        ),
        EufyMakeSensorDescription(
            key=f"ink_{channel.lower()}_days_until_expiration",
            name=f"{name} ink days until expiration",
            native_unit_of_measurement="d",
            value_fn=_ink_detail_value_fn(channel, "days_until_expiration"),
        ),
        EufyMakeSensorDescription(
            key=f"ink_{channel.lower()}_manufacture_date",
            name=f"{name} ink manufacture date",
            device_class=SensorDeviceClass.DATE,
            value_fn=_ink_date_fn(channel, "manufacture_date"),
        ),
        EufyMakeSensorDescription(
            key=f"ink_{channel.lower()}_status",
            name=f"{name} ink status",
            value_fn=_ink_status_value_fn(channel),
            attributes_fn=_ink_status_attributes_fn(channel),
        ),
    )
)


WASTE_SENSORS: tuple[EufyMakeSensorDescription, ...] = (
    EufyMakeSensorDescription(
        key="waste_ink",
        name="Waste ink",
        translation_key="waste_ink",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: data.get("waste_ink"),
        attributes_fn=lambda data: _waste_ink_attributes(data),
    ),
    EufyMakeSensorDescription(
        key="waste_ink_expiration_date",
        name="Waste ink expiration date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda data: _date_value(
            _waste_ink_attributes(data),
            "expiration_date",
        ),
    ),
    EufyMakeSensorDescription(
        key="waste_ink_days_until_expiration",
        name="Waste ink days until expiration",
        native_unit_of_measurement="d",
        value_fn=lambda data: _waste_ink_attributes(data).get(
            "days_until_expiration"
        ),
    ),
    EufyMakeSensorDescription(
        key="waste_ink_status",
        name="Waste ink status",
        value_fn=lambda data: _map_ink_status(_waste_ink_attributes(data)),
        attributes_fn=lambda data: {
            "raw_status": _waste_ink_attributes(data).get("status"),
            "expired": _waste_ink_attributes(data).get("expired"),
        },
    ),
)


CONNECTIVITY_SENSORS: tuple[EufyMakeSensorDescription, ...] = (
    EufyMakeSensorDescription(
        key="mqtt_online",
        name="MQTT online",
        translation_key="mqtt_online",
        value_fn=lambda data: data.get("mqtt_online"),
    ),
    EufyMakeSensorDescription(
        key="p2p_online",
        name="P2P online",
        translation_key="p2p_online",
        value_fn=lambda data: data.get("p2p_online"),
    ),
)


PURIFIER_SENSORS: tuple[EufyMakeSensorDescription, ...] = (
    EufyMakeSensorDescription(
        key="purifier_online",
        name="Purifier online",
        value_fn=_purifier_value_fn("online"),
    ),
    EufyMakeSensorDescription(
        key="purifier_firmware_version",
        name="Purifier firmware version",
        value_fn=_purifier_value_fn("firmware_version"),
    ),
    EufyMakeSensorDescription(
        key="purifier_filter_health",
        name="Purifier filter health",
        native_unit_of_measurement=PERCENTAGE,
        value_fn=_purifier_state_value_fn("filter_health"),
    ),
    EufyMakeSensorDescription(
        key="purifier_filter_lifetime",
        name="Purifier filter lifetime",
        native_unit_of_measurement="h",
        value_fn=_purifier_state_value_fn("filter_lifeTime"),
    ),
    EufyMakeSensorDescription(
        key="purifier_filter_status",
        name="Purifier filter status",
        value_fn=_purifier_filter_status,
        attributes_fn=lambda data: {
            "raw_filter_status": _purifier_state(data).get("filter_status")
        },
    ),
    EufyMakeSensorDescription(
        key="purifier_work_mode",
        name="Purifier mode",
        value_fn=_purifier_mode,
        attributes_fn=lambda data: {
            "raw_work_mode": _purifier_state(data).get("work_mode")
        },
    ),
    EufyMakeSensorDescription(
        key="purifier_work_status",
        name="Purifier work status",
        value_fn=_purifier_work_status,
        attributes_fn=lambda data: {
            "raw_work_status": _purifier_state(data).get("work_status")
        },
    ),
)


SENSORS: tuple[EufyMakeSensorDescription, ...] = (
    *BASE_SENSORS,
    *INK_SENSORS,
    *WASTE_SENSORS,
    *CONNECTIVITY_SENSORS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eufyMake E1 sensors."""
    coordinator: EufyMakeE1Coordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        EufyMakeE1Sensor(coordinator, entry, description) for description in SENSORS
    ]
    if _purifier(coordinator.data or {}):
        entities.extend(
            EufyMakeP1Sensor(coordinator, entry, description)
            for description in PURIFIER_SENSORS
        )
    entities.extend(
        EufyMakeE1PartSensor(coordinator, entry, part)
        for part in _parts(coordinator)
    )
    async_add_entities(entities)


class EufyMakeE1Sensor(CoordinatorEntity[EufyMakeE1Coordinator], SensorEntity):
    """Representation of a eufyMake E1 sensor."""

    entity_description: EufyMakeSensorDescription

    def __init__(
        self,
        coordinator: EufyMakeE1Coordinator,
        entry: ConfigEntry,
        description: EufyMakeSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        device_sn = entry.data[CONF_DEVICE_SN]
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{device_sn}_{description.key}"
        self._attr_device_info = e1_device_info(entry, coordinator.data)

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes."""
        if self.entity_description.attributes_fn is None:
            return {}
        return _clean_attributes(
            self.entity_description.attributes_fn(self.coordinator.data or {})
        )


class EufyMakeE1PartSensor(CoordinatorEntity[EufyMakeE1Coordinator], SensorEntity):
    """Representation of a eufyMake E1 consumable or service part."""

    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        coordinator: EufyMakeE1Coordinator,
        entry: ConfigEntry,
        part: dict[str, Any],
    ) -> None:
        """Initialize the part sensor."""
        super().__init__(coordinator)
        device_sn = entry.data[CONF_DEVICE_SN]
        key = part.get("key") or _slug(str(part.get("name") or "part"))
        name = part.get("name") or key
        self._part_key = key
        self._attr_has_entity_name = True
        self._attr_name = name
        self._attr_unique_id = f"{device_sn}_part_{key}"
        self._attr_device_info = e1_device_info(entry, coordinator.data)

    @property
    def native_value(self) -> Any:
        """Return the part remaining percentage."""
        for part in _parts(self.coordinator):
            if part.get("key") == self._part_key:
                return part.get("remaining_percent")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional part attributes."""
        for part in _parts(self.coordinator):
            if part.get("key") == self._part_key:
                return {
                    "remaining_work_life": part.get("remaining_work_life"),
                    "maintenance_required": part.get("maintenance_required"),
                    "support_reset": part.get("support_reset"),
                }
        return {}


class EufyMakeP1Sensor(CoordinatorEntity[EufyMakeE1Coordinator], SensorEntity):
    """Representation of a linked eufyMake Purifier P1 sensor."""

    entity_description: EufyMakeSensorDescription

    def __init__(
        self,
        coordinator: EufyMakeE1Coordinator,
        entry: ConfigEntry,
        description: EufyMakeSensorDescription,
    ) -> None:
        """Initialize the P1 sensor."""
        super().__init__(coordinator)
        e1_sn = entry.data[CONF_DEVICE_SN]
        purifier = _purifier(coordinator.data or {})
        purifier_sn = purifier.get("serial_number") or f"{e1_sn}_purifier_p1"
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{purifier_sn}_{description.key}"
        self._attr_device_info = p1_device_info(purifier, fallback_e1_sn=e1_sn)

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes."""
        if self.entity_description.attributes_fn is None:
            return {}
        return _clean_attributes(
            self.entity_description.attributes_fn(self.coordinator.data or {})
        )


def _parts(coordinator: EufyMakeE1Coordinator) -> list[dict[str, Any]]:
    """Return coordinator part data."""
    data = coordinator.data or {}
    parts = data.get("parts", [])
    return parts if isinstance(parts, list) else []


def _clean_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in attributes.items()
        if value is not None
    }


def _slug(value: str) -> str:
    """Return a simple entity-safe slug."""
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")


def _map_purifier_mode(value: Any) -> str | None:
    modes = {
        0: "Standby",
        1: "Silent",
        2: "High",
        3: "Full power",
        4: "Auto",
    }
    return _map_int(value, modes, "Unknown mode")


def _map_purifier_work_status(value: Any) -> str | None:
    statuses = {
        0: "Standby",
        1: "Running",
    }
    return _map_int(value, statuses, "Unknown status")


def _map_purifier_filter_status(value: Any) -> str | None:
    statuses = {
        0: "Normal",
        1: "Warning",
        2: "Replace",
    }
    return _map_int(value, statuses, "Unknown status")


def _map_int(value: Any, mapping: dict[int, str], fallback: str) -> str | None:
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        return None
    return mapping.get(int_value, fallback)


def _map_ink_status(attributes: dict[str, Any]) -> str | None:
    raw_status = attributes.get("status")
    try:
        status = int(raw_status)
    except (TypeError, ValueError):
        status = None

    if status == 0:
        return "Not inserted"
    if attributes.get("expired") is True:
        return "Expired"
    if status == 1:
        return "Inserted"
    if status is not None:
        return "Unknown"
    return None


def _map_enabled(value: Any) -> str | None:
    if value is True:
        return "On"
    if value is False:
        return "Off"
    return None


def _map_e1_level(value: Any) -> str | None:
    return _map_int(
        value,
        {
            0: "Low",
            1: "Medium",
            2: "High",
        },
        "Unknown",
    )
