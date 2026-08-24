import importlib.util
import sys
import types
from dataclasses import dataclass
from datetime import date
from pathlib import Path


COMPONENT_DIR = (
    Path(__file__).resolve().parents[1] / "custom_components" / "eufymake_e1"
)


def test_ink_sensors_are_grouped_by_channel() -> None:
    module = _load_sensor_module()

    keys = [description.key for description in module.SENSORS]

    assert keys[:13] == [
        "availability",
        "print_status",
        "firmware_version",
        "current_accessory",
        "print_progress",
        "notification_sound",
        "notification_sound_level",
        "fill_light",
        "fill_light_level",
        "ink_c",
        "ink_c_expiration_date",
        "ink_c_days_until_expiration",
        "ink_c_manufacture_date",
    ]
    assert keys[13:21] == [
        "ink_c_status",
        "ink_m",
        "ink_m_expiration_date",
        "ink_m_days_until_expiration",
        "ink_m_manufacture_date",
        "ink_m_status",
        "ink_y",
        "ink_y_expiration_date",
    ]


def test_ink_expiration_sensor_returns_date_value() -> None:
    module = _load_sensor_module()
    data = {
        "ink_details": {
            "C": {
                "expiration_date": "2026-08-28",
                "manufacture_date": "2025-08-28",
                "days_until_expiration": 10,
                "expired": False,
                "status": 1,
            }
        }
    }

    descriptions = {description.key: description for description in module.SENSORS}

    assert descriptions["ink_c_expiration_date"].value_fn(data) == date(2026, 8, 28)
    assert descriptions["ink_c_manufacture_date"].value_fn(data) == date(2025, 8, 28)
    assert descriptions["ink_c_days_until_expiration"].value_fn(data) == 10


def test_ink_status_combines_inserted_and_expired_state() -> None:
    module = _load_sensor_module()
    descriptions = {description.key: description for description in module.SENSORS}
    status = descriptions["ink_c_status"]
    waste_status = descriptions["waste_ink_status"]

    assert (
        status.value_fn({"ink_details": {"C": {"status": 1, "expired": False}}})
        == "Inserted"
    )
    assert (
        status.value_fn({"ink_details": {"C": {"status": 1, "expired": True}}})
        == "Expired"
    )
    assert (
        status.value_fn({"ink_details": {"C": {"status": 0, "expired": True}}})
        == "Not inserted"
    )
    assert status.value_fn({"ink_details": {"C": {"status": 9}}}) == "Unknown"
    assert (
        waste_status.value_fn({"waste_ink_details": {"status": 1, "expired": True}})
        == "Expired"
    )


def test_print_progress_returns_active_operation_progress() -> None:
    module = _load_sensor_module()
    descriptions = {description.key: description for description in module.SENSORS}
    progress = descriptions["print_progress"]

    assert (
        progress.value_fn(
            {
                "ink_injection": {"active": True, "progress": 49},
                "white_ink_recovery": {"active": False, "progress": 100},
            }
        )
        == 49
    )
    assert (
        progress.value_fn(
            {
                "ink_injection": {"active": False, "progress": 100},
                "test_print": {"active": True, "progress": 66},
            }
        )
        == 66
    )
    assert progress.value_fn({"test_print": {"active": False, "progress": 100}}) is None


def test_fill_light_sensors_report_polled_state() -> None:
    module = _load_sensor_module()
    descriptions = {description.key: description for description in module.SENSORS}

    data = {
        "e1_controls": {
            "fill_light": {
                "enabled": True,
                "level": 2,
            }
        }
    }

    assert descriptions["fill_light"].value_fn(data) == "On"
    assert descriptions["fill_light_level"].value_fn(data) == "High"
    assert (
        descriptions["fill_light"].value_fn(
            {"e1_controls": {"fill_light": {"enabled": False, "level": 0}}}
        )
        == "Off"
    )


def test_notification_sound_sensors_report_polled_state() -> None:
    module = _load_sensor_module()
    descriptions = {description.key: description for description in module.SENSORS}

    data = {
        "e1_controls": {
            "notification_sound": {
                "enabled": True,
                "level": 1,
            }
        }
    }

    assert descriptions["notification_sound"].value_fn(data) == "On"
    assert descriptions["notification_sound_level"].value_fn(data) == "Medium"
    assert (
        descriptions["notification_sound"].value_fn(
            {"e1_controls": {"notification_sound": {"enabled": False, "level": 2}}}
        )
        == "Off"
    )


def _load_sensor_module():
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_module(
        "custom_components.eufymake_e1.const",
        COMPONENT_DIR / "const.py",
    )

    return _load_module(
        "custom_components.eufymake_e1.sensor",
        COMPONENT_DIR / "sensor.py",
    )


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _stub_homeassistant() -> None:
    homeassistant = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    sensor = types.ModuleType("homeassistant.components.sensor")
    config_entries = types.ModuleType("homeassistant.config_entries")
    const = types.ModuleType("homeassistant.const")
    core = types.ModuleType("homeassistant.core")
    exceptions = types.ModuleType("homeassistant.exceptions")
    helpers = types.ModuleType("homeassistant.helpers")
    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
    update_coordinator = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )

    class SensorDeviceClass:
        DATE = "date"

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription:
        key: str
        name: str | None = None
        translation_key: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: str | None = None

    class SensorEntity:
        pass

    class ConfigEntry:
        pass

    class HomeAssistant:
        pass

    class ConfigEntryAuthFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

    class UpdateFailed(Exception):
        pass

    class CoordinatorEntity:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, *args, **kwargs):
            pass

    sensor.SensorDeviceClass = SensorDeviceClass
    sensor.SensorEntity = SensorEntity
    sensor.SensorEntityDescription = SensorEntityDescription
    config_entries.ConfigEntry = ConfigEntry
    const.PERCENTAGE = "%"
    core.HomeAssistant = HomeAssistant
    exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    entity_platform.AddEntitiesCallback = object
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.CoordinatorEntity = CoordinatorEntity
    update_coordinator.UpdateFailed = UpdateFailed
    components.sensor = sensor
    helpers.entity_platform = entity_platform
    helpers.update_coordinator = update_coordinator
    homeassistant.components = components
    homeassistant.config_entries = config_entries
    homeassistant.const = const
    homeassistant.core = core
    homeassistant.exceptions = exceptions
    homeassistant.helpers = helpers

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.sensor"] = sensor
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.const"] = const
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.exceptions"] = exceptions
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator
