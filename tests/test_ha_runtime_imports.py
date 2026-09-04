import importlib.util
import sys
import types
from pathlib import Path


COMPONENT_DIR = (
    Path(__file__).resolve().parents[1] / "custom_components" / "eufymake_e1"
)


def test_coordinator_imports_without_vendored_pyeufymake_package() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()
    sys.modules.pop("custom_components.eufymake_e1.pyeufymake", None)

    spec = importlib.util.spec_from_file_location(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.EufyMakeE1Coordinator is not None


def test_coordinator_live_data_includes_ink_attributes() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()

    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    data = coordinator._data_from_live_result(
        runtime.InkStatus(
            channels=(
                runtime.InkChannel(
                    channel="C",
                    remaining_percent=76.56,
                    status=1,
                    manufacture_timestamp=1756396800,
                    expiration_timestamp=1787932800,
                    distance_expiration_days=10,
                    expired=False,
                ),
            ),
            waste_tank=runtime.WasteInkTank(
                remaining_percent=20.0,
                status=1,
                expiration_timestamp=1803657600,
                distance_expiration_days=192,
                expired=False,
            ),
        ),
        decoded_messages=(
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1153, "attType": 4, "version": "V1.3.3"},
                command_type=1153,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1118, "plateType": 3},
                command_type=1118,
            ),
        ),
        firmware_version="4.0.2",
        mqtt_online=True,
        p2p_online=None,
    )

    assert data["ink"]["C"] == 76.56
    assert data["ink_details"]["C"]["manufacture_date"] == "2025-08-28"
    assert data["ink_details"]["C"]["expiration_date"] == "2026-08-28"
    assert data["ink_details"]["C"]["days_until_expiration"] == 10
    assert data["ink_details"]["C"]["expired"] is False
    assert data["waste_ink_details"]["expiration_date"] == "2027-02-26"
    assert data["current_accessory"] == "Rotary Printing Attachment"
    assert data["current_accessory_details"] == {
        "attachment_type": 4,
        "plate_type": 3,
        "version": "V1.3.3",
    }


def test_coordinator_live_data_exposes_ink_injection_progress() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()

    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    data = coordinator._data_from_live_result(
        None,
        decoded_messages=(
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 5,
                        "step": 3,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1136, "value": 1, "progress": 49},
                command_type=1136,
            ),
        ),
        firmware_version="4.0.2",
        mqtt_online=True,
        p2p_online=None,
    )

    assert data["availability"] == "online"
    assert data["print_status"] == "Injecting ink"
    assert data["print_status_details"]["state"] == 5
    assert data["print_status_details"]["step"] == 3
    assert data["ink_injection"] == {
        "active": True,
        "progress": 49,
    }


def test_coordinator_live_data_exposes_white_ink_recovery_progress() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()

    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    data = coordinator._data_from_live_result(
        None,
        decoded_messages=(
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 5,
                        "step": 17,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1188, "value": 1, "progress": 47},
                command_type=1188,
            ),
        ),
        firmware_version="4.0.2",
        mqtt_online=True,
        p2p_online=None,
    )

    assert data["availability"] == "online"
    assert data["print_status"] == "White ink recovery"
    assert data["print_status_details"]["state"] == 5
    assert data["print_status_details"]["step"] == 17
    assert data["white_ink_recovery"] == {
        "active": True,
        "progress": 47,
    }


def test_coordinator_live_data_exposes_status_check_progress() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()

    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    data = coordinator._data_from_live_result(
        None,
        decoded_messages=(
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 8,
                        "step": 2,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1131,
                    "qrcode": 0,
                    "cail_file": 1,
                    "zero_file": 0,
                    "value": 1,
                    "progress": 40,
                },
                command_type=1131,
            ),
        ),
        firmware_version="4.0.2",
        mqtt_online=True,
        p2p_online=None,
    )

    assert data["availability"] == "online"
    assert data["print_status"] == "Checking status"
    assert data["print_status_details"]["state"] == 8
    assert data["print_status_details"]["step"] == 2
    assert data["status_check"] == {
        "active": True,
        "progress": 40,
    }


def test_coordinator_live_data_exposes_test_print_progress() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()

    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    data = coordinator._data_from_live_result(
        None,
        decoded_messages=(
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 4,
                        "step": 1,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1064, "value": 0, "mode": 4, "progress": 66},
                command_type=1064,
            ),
        ),
        firmware_version="4.0.2",
        mqtt_online=True,
        p2p_online=None,
    )

    assert data["availability"] == "online"
    assert data["print_status"] == "Test printing"
    assert data["print_status_details"]["state"] == 4
    assert data["print_status_details"]["step"] == 1
    assert data["test_print"] == {
        "active": True,
        "progress": 66,
    }


def test_coordinator_live_data_exposes_regular_print_progress() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()

    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    data = coordinator._data_from_live_result(
        None,
        decoded_messages=(
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 2,
                        "step": 4,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1001,
                    "time": 65,
                    "progress": 8500,
                    "totalTime": 293,
                },
                command_type=1001,
            ),
        ),
        firmware_version="4.0.2",
        mqtt_online=True,
        p2p_online=None,
    )

    assert data["availability"] == "online"
    assert data["print_status"] == "Printing"
    assert data["print_status_details"]["state"] == 2
    assert data["print_status_details"]["step"] == 4
    assert data["print_job"] == {
        "active": True,
        "progress": 85,
        "remaining_time": 65,
        "elapsed_time": 293,
    }


def test_coordinator_live_data_exposes_design_preparation_progress() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()

    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    data = coordinator._data_from_live_result(
        None,
        decoded_messages=(
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 8,
                        "step": 0,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1105,
                    "value": 1,
                    "step": 1,
                    "height": 8.755,
                    "plate_type": 2,
                    "plate_print_width": 335,
                    "plate_print_height": 90,
                    "progress": 69,
                },
                command_type=1105,
            ),
        ),
        firmware_version="4.0.2",
        mqtt_online=True,
        p2p_online=None,
    )

    assert data["print_status"] == "Taking snapshots"
    assert data["design_preparation"] == {
        "name": "Taking snapshots",
        "active": True,
        "progress": 69,
        "height": 8.755,
        "plate_type": 2,
        "plate_print_width": 335,
        "plate_print_height": 90,
    }


def test_coordinator_live_data_exposes_file_transfer_progress() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()

    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    data = coordinator._data_from_live_result(
        None,
        decoded_messages=(
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 2,
                        "step": 1,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1053,
                    "downloadFileProgress": 42,
                    "result": 0,
                },
                command_type=1053,
            ),
        ),
        firmware_version="4.0.2",
        mqtt_online=True,
        p2p_online=None,
    )

    assert data["print_status"] == "Sending file to device"
    assert data["file_transfer"] == {
        "active": True,
        "progress": 42,
        "result": 0,
    }


def test_coordinator_live_data_exposes_firmware_update_progress() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()

    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    data = coordinator._data_from_live_result(
        None,
        decoded_messages=(
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 6,
                        "step": 1,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/command/reply",
                variant="cbc",
                payload={
                    "commandType": 1002,
                    "currVer": "4.0.2",
                    "isUpgrade": 1,
                    "upgradeFlag": 1,
                    "tagerVer": "4.0.7",
                    "releaseNote": "New firmware",
                    "full_package": {"file_size": 373628832},
                    "reply": 0,
                },
                command_type=1002,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1047,
                    "download": 100,
                    "upgrade": 43,
                    "speed": 0,
                    "forceUpgrade": 0,
                    "file_size": 0,
                },
                command_type=1047,
            ),
        ),
        firmware_version="4.0.2",
        mqtt_online=True,
        p2p_online=None,
    )

    assert data["print_status"] == "Firmware updating"
    assert data["firmware_version"] == "4.0.2"
    assert data["firmware_update"] == {
        "available": True,
        "current_version": "4.0.2",
        "target_version": "4.0.7",
        "forced": False,
        "upgrade_flag": 1,
        "release_note": "New firmware",
        "reply": 0,
        "active": True,
        "download_progress": 100,
        "upgrade_progress": 43,
        "speed": 0,
        "file_size": 373628832,
        "upgrade_result": None,
        "error_code": None,
    }


def test_coordinator_live_data_exposes_reboot_calibration_state() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()

    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    data = coordinator._data_from_live_result(
        None,
        decoded_messages=(
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 9,
                        "step": 0,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1123,
                    "status": 0,
                    "progress": 72,
                    "result": {},
                },
                command_type=1123,
            ),
        ),
        firmware_version="4.0.7",
        mqtt_online=True,
        p2p_online=None,
    )

    assert data["print_status"] == "Calibrating"
    assert data["print_status_details"]["state"] == 9
    assert data["print_status_details"]["step"] == 0
    assert data["self_check"] == {
        "active": True,
        "progress": 72,
        "status": 0,
        "error_count": None,
    }


def test_coordinator_live_data_exposes_e1_sound_and_light_settings() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()

    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    data = coordinator._data_from_live_result(
        None,
        decoded_messages=(
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1045,
                    "beep": 1,
                    "beep_level": 2,
                    "light": 1,
                },
                command_type=1045,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1133, "light": 1, "light_level": 1},
                command_type=1133,
            ),
        ),
        firmware_version="4.0.2",
        mqtt_online=True,
        p2p_online=None,
    )

    assert data["e1_controls"] == {
        "notification_sound": {
            "enabled": True,
            "level": 2,
        },
        "fill_light": {
            "enabled": True,
            "level": 1,
        },
    }


def test_runtime_accessory_status_uses_latest_plate_message() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_accessory_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1153, "attType": 0, "version": ""},
                command_type=1153,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1118, "plateType": 0},
                command_type=1118,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1153, "attType": 4, "version": "V1.3.3"},
                command_type=1153,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1118, "plateType": 3},
                command_type=1118,
            ),
        )
    )

    assert status.name == "Rotary Printing Attachment"
    assert status.attachment_type == 4
    assert status.plate_type == 3
    assert status.version == "V1.3.3"


def test_runtime_accessory_status_maps_standard_flatbed() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_accessory_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1118, "plateType": 1},
                command_type=1118,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1153, "attType": 2, "version": "V1.2.1"},
                command_type=1153,
            ),
        )
    )

    assert status.name == "Standard Flatbed"
    assert status.attachment_type == 2
    assert status.plate_type == 1
    assert status.version == "V1.2.1"


def test_runtime_accessory_status_maps_mini_flatbed() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_accessory_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1118, "plateType": 2},
                command_type=1118,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1153, "attType": 1, "version": ""},
                command_type=1153,
            ),
        )
    )

    assert status.name == "Mini Flatbed"
    assert status.attachment_type == 1
    assert status.plate_type == 2
    assert status.version == ""


def test_runtime_accessory_status_maps_none() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_accessory_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1118, "plateType": 0},
                command_type=1118,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1153, "attType": 0, "version": ""},
                command_type=1153,
            ),
        )
    )

    assert status.name == "None"
    assert status.attachment_type == 0
    assert status.plate_type == 0
    assert status.version == ""


def test_runtime_accessory_status_maps_roll_to_film() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_accessory_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1153, "attType": 3, "version": "V1.1.16"},
                command_type=1153,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1118, "plateType": 4},
                command_type=1118,
            ),
        )
    )

    assert status.name == "Roll-to-Film Attachment"
    assert status.attachment_type == 3
    assert status.plate_type == 4
    assert status.version == "V1.1.16"


def test_runtime_printer_status_maps_maintenance() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_printer_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 13,
                        "step": 0,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
        )
    )

    assert status.name == "Maintenance"
    assert status.state == 13
    assert status.step == 0
    assert status.maintainable is True
    assert status.error_codes == ()


def test_runtime_printer_status_maps_printing() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_printer_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 2,
                        "step": 4,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
        )
    )

    assert status.name == "Printing"
    assert status.state == 2
    assert status.step == 4


def test_runtime_printer_status_maps_ready_to_print_and_priming() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    ready = runtime.find_printer_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 2,
                        "step": 2,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
        )
    )
    priming = runtime.find_printer_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 2,
                        "step": 6,
                        "ext": {"maintainable": 1},
                    },
                },
                command_type=1000,
            ),
        )
    )

    assert ready.name == "Ready to print"
    assert priming.name == "Priming print head"


def test_runtime_printer_status_maps_unavailable_with_error_codes() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_printer_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1000,
                    "status": {
                        "state": 10,
                        "step": 0,
                        "ext": {
                            "maintainable": 1,
                            "errorCodes": ["0xFD...0008"],
                        },
                    },
                },
                command_type=1000,
            ),
        )
    )

    assert status.name == "Unavailable"
    assert status.state == 10
    assert status.step == 0
    assert status.maintainable is True
    assert status.error_codes == ("0xFD...0008",)


def test_runtime_ink_injection_status_maps_active_progress() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_ink_injection_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1136, "value": 1, "progress": 49},
                command_type=1136,
            ),
        )
    )

    assert status.active is True
    assert status.progress == 49


def test_runtime_ink_injection_status_maps_completed_progress() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_ink_injection_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1136, "value": 1, "progress": 100},
                command_type=1136,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1136, "value": 0, "progress": 100},
                command_type=1136,
            ),
        )
    )

    assert status.active is False
    assert status.progress == 100


def test_runtime_white_ink_recovery_status_maps_active_progress() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_white_ink_recovery_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1188, "value": 1, "progress": 47},
                command_type=1188,
            ),
        )
    )

    assert status.active is True
    assert status.progress == 47


def test_runtime_white_ink_recovery_status_maps_completed_progress() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_white_ink_recovery_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1188, "value": 1, "progress": 100},
                command_type=1188,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1188, "value": 0, "progress": 100},
                command_type=1188,
            ),
        )
    )

    assert status.active is False
    assert status.progress == 100


def test_runtime_status_check_status_maps_active_progress() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_status_check_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1131,
                    "qrcode": 0,
                    "cail_file": 1,
                    "zero_file": 0,
                    "value": 1,
                    "progress": 40,
                },
                command_type=1131,
            ),
        )
    )

    assert status.active is True
    assert status.progress == 40


def test_runtime_status_check_status_maps_completed_progress() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_status_check_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1131, "value": 1, "progress": 60},
                command_type=1131,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1131, "value": 0, "progress": 100},
                command_type=1131,
            ),
        )
    )

    assert status.active is False
    assert status.progress == 100


def test_runtime_test_print_status_maps_active_progress() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_test_print_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1064, "value": 0, "mode": 4, "progress": 66},
                command_type=1064,
            ),
        )
    )

    assert status.active is True
    assert status.progress == 66


def test_runtime_test_print_status_maps_completed_progress() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_test_print_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1064,
                    "value": 1,
                    "mode": 4,
                    "progress": 100,
                    "image_url": "http...image",
                },
                command_type=1064,
            ),
        )
    )

    assert status.active is False
    assert status.progress == 100


def test_runtime_print_job_status_maps_active_progress() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_print_job_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1001,
                    "time": 65,
                    "progress": 8500,
                    "totalTime": 293,
                },
                command_type=1001,
            ),
        )
    )

    assert status.active is True
    assert status.progress == 85
    assert status.remaining_time == 65
    assert status.elapsed_time == 293


def test_runtime_print_job_status_maps_completed_progress() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_print_job_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1001,
                    "time": 17,
                    "progress": 10000,
                    "totalTime": 329,
                },
                command_type=1001,
            ),
        )
    )

    assert status.active is False
    assert status.progress == 100
    assert status.remaining_time == 17
    assert status.elapsed_time == 329


def test_runtime_design_preparation_status_maps_latest_step() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_design_preparation_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1105,
                    "value": 1,
                    "step": 0,
                    "progress": 37,
                },
                command_type=1105,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1105,
                    "value": 1,
                    "step": 1,
                    "height": 8.755,
                    "plate_type": 2,
                    "plate_print_width": 335,
                    "plate_print_height": 90,
                    "progress": 69,
                },
                command_type=1105,
            ),
        )
    )

    assert status.name == "Taking snapshots"
    assert status.active is True
    assert status.progress == 69
    assert status.height == 8.755
    assert status.plate_type == 2
    assert status.plate_print_width == 335
    assert status.plate_print_height == 90


def test_runtime_file_transfer_status_maps_progress_and_completion() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_file_transfer_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1053,
                    "downloadFileProgress": 0,
                    "result": 0,
                },
                command_type=1053,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1053,
                    "downloadFileProgress": 100,
                    "result": 1,
                },
                command_type=1053,
            ),
        )
    )

    assert status.active is False
    assert status.progress == 100
    assert status.result == 1


def test_runtime_self_check_status_maps_progress_and_completion() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    active = runtime.find_self_check_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1123, "status": 0, "progress": 72},
                command_type=1123,
            ),
        )
    )
    complete = runtime.find_self_check_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1123,
                    "status": 3,
                    "progress": 100,
                    "result": {"err_cnt": 0, "err_buf": []},
                },
                command_type=1123,
            ),
        )
    )

    assert active.active is True
    assert active.progress == 72
    assert active.status == 0
    assert active.error_count is None
    assert complete.active is False
    assert complete.progress == 100
    assert complete.status == 3
    assert complete.error_count == 0


def test_runtime_firmware_update_status_maps_available_progress_and_completion() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_firmware_update_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/command/reply",
                variant="cbc",
                payload={
                    "commandType": 1002,
                    "currVer": "4.0.2",
                    "isUpgrade": 1,
                    "upgradeFlag": 1,
                    "tagerVer": "4.0.7",
                    "releaseNote": "New firmware",
                    "full_package": {"file_size": 373628832},
                    "reply": 0,
                },
                command_type=1002,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1047,
                    "download": 100,
                    "upgrade": 43,
                    "speed": 0,
                    "forceUpgrade": 0,
                    "file_size": 0,
                },
                command_type=1047,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1054,
                    "currVer": "4.0.7",
                    "upgradeResult": 1,
                    "errorCode": 0,
                },
                command_type=1054,
            ),
        )
    )

    assert status.available is False
    assert status.current_version == "4.0.7"
    assert status.target_version == "4.0.7"
    assert status.forced is False
    assert status.upgrade_flag == 1
    assert status.release_note == "New firmware"
    assert status.reply == 0
    assert status.active is False
    assert status.download_progress == 100
    assert status.upgrade_progress == 43
    assert status.speed == 0
    assert status.file_size == 373628832
    assert status.upgrade_result == 1
    assert status.error_code == 0


def test_runtime_firmware_update_status_prefers_target_version_difference() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_firmware_update_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/command/reply",
                variant="cbc",
                payload={
                    "commandType": 1002,
                    "currVer": "4.0.7",
                    "isUpgrade": 0,
                    "upgradeFlag": 1,
                    "tagerVer": "4.0.9",
                    "releaseNote": "New firmware",
                    "full_package": {"file_size": 373624224},
                    "reply": 0,
                },
                command_type=1002,
            ),
        )
    )

    assert status.available is True
    assert status.current_version == "4.0.7"
    assert status.target_version == "4.0.9"
    assert status.forced is None
    assert status.upgrade_flag == 1
    assert status.file_size == 373624224


def test_runtime_notification_sound_status_maps_toggle_and_level() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_notification_sound_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1045,
                    "beep": 0,
                    "beep_level": 2,
                    "light": 1,
                },
                command_type=1045,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={
                    "commandType": 1045,
                    "beep": 1,
                    "beep_level": 0,
                    "light": 1,
                },
                command_type=1045,
            ),
        )
    )

    assert status.enabled is True
    assert status.level == 0


def test_runtime_fill_light_status_maps_toggle_and_level() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    status = runtime.find_fill_light_status(
        (
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1133, "light": 0, "light_level": 0},
                command_type=1133,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1133, "light": 1},
                command_type=1133,
            ),
            runtime.DecodedMqttMessage(
                topic="/phone/maker/AKTEST/notice",
                variant="cbc",
                payload={"commandType": 1133, "light": 1, "light_level": 1},
                command_type=1133,
            ),
        )
    )

    assert status.enabled is True
    assert status.level == 1


def test_runtime_e1_read_only_settings_queries_are_passive_only() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    assert runtime.E1_READ_ONLY_SETTINGS_QUERY_COMMANDS == (
        {"commandType": 1002},
    )


def test_update_entity_exposes_firmware_state() -> None:
    _stub_homeassistant()
    package = types.ModuleType("custom_components.eufymake_e1")
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules["custom_components.eufymake_e1"] = package
    sys.modules["custom_components.eufymake_e1.const"] = _load_real_const()
    sys.modules["custom_components.eufymake_e1.device_info"] = _load_module(
        "custom_components.eufymake_e1.device_info",
        COMPONENT_DIR / "device_info.py",
    )
    sys.modules["custom_components.eufymake_e1.coordinator"] = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )
    update = _load_module(
        "custom_components.eufymake_e1.update",
        COMPONENT_DIR / "update.py",
    )

    entry = types.SimpleNamespace(
        data={
            "device_sn": "AKTEST",
            "firmware_version": "4.0.2",
        }
    )
    coordinator = types.SimpleNamespace(
        data={
            "firmware_version": "4.0.2",
            "firmware_update": {
                "available": True,
                "current_version": "4.0.2",
                "target_version": "4.0.7",
                "forced": False,
                "upgrade_flag": 1,
                "release_note": "Line one\nLine two",
                "active": True,
                "download_progress": 100,
                "upgrade_progress": 76,
                "speed": 0,
                "file_size": 373628832,
                "upgrade_result": None,
                "error_code": None,
                "reply": 0,
            },
        }
    )

    entity = update.EufyMakeE1FirmwareUpdate(coordinator, entry)

    assert entity.installed_version == "4.0.2"
    assert entity.latest_version == "4.0.7"
    assert entity.in_progress is True
    assert entity.update_percentage == 76
    assert entity.release_summary == "Line one Line two"
    assert entity.extra_state_attributes["file_size"] == 373628832


def test_runtime_command_state_echo_matches_requested_payload() -> None:
    _stub_homeassistant()
    runtime = _load_module(
        "custom_components.eufymake_e1.runtime",
        COMPONENT_DIR / "runtime.py",
    )

    assert runtime._command_state_matches(
        {"commandType": 1045, "beep": 1, "beep_level": 1, "light": 1},
        {"commandType": 1045, "beep": 1, "beep_level": 1, "light": 1},
    )
    assert runtime._command_state_matches(
        {"commandType": 1133, "light": 0, "light_level": 2},
        {"commandType": 1133, "light": 0},
    )
    assert not runtime._command_state_matches(
        {"commandType": 1045, "beep": 1, "beep_level": 1, "light": 1},
        {"commandType": 1045, "beep": 1, "beep_level": 2, "light": 1},
    )
    assert not runtime._command_state_matches(
        {"commandType": 1045, "beep": 1, "beep_level": 1, "light": 1},
        {"commandType": 1045},
    )


def test_coordinator_sends_e1_sound_and_light_command_payloads(monkeypatch) -> None:
    _stub_homeassistant()
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    sent: list[dict[str, object]] = []

    class FakeCommandClient:
        def __init__(self, **kwargs):
            sent.append({"client": kwargs})

        def send(
            self,
            payload,
            *,
            expected_command_type,
            preflight_query_payloads=(),
        ):
            sent.append(
                {
                    "payload": payload,
                    "expected_command_type": expected_command_type,
                    "preflight_query_payloads": preflight_query_payloads,
                }
            )

    monkeypatch.setattr(coordinator, "EufyMakeMqttCommandClient", FakeCommandClient)

    entry = types.SimpleNamespace(
        data={
            "mqtt_host": "make-mqtt-test",
            "device_sn": "AKTEST",
            "user_id": "123",
            "email": "user@example.test",
            "secret_key": "0" * 32,
        }
    )
    instance = coordinator.EufyMakeE1Coordinator.__new__(
        coordinator.EufyMakeE1Coordinator
    )
    instance.entry = entry
    instance.data = {
        "e1_controls": {
            "notification_sound": {"enabled": True, "level": 1},
            "fill_light": {"enabled": False, "level": 0},
        }
    }

    instance._send_notification_sound_command(False, 2)
    instance._send_fill_light_command(True, 1)
    instance._send_fill_light_command(False, 2)

    assert sent == [
        {
            "client": {
                "host": "make-mqtt-test",
                "station_sn": "AKTEST",
                "user_id": "123",
                "email": "user@example.test",
                "secret_key": "0" * 32,
            }
        },
        {
            "payload": {
                "commandType": 1045,
                "beep": 0,
                "beep_level": 2,
                "light": 1,
            },
            "expected_command_type": 1045,
            "preflight_query_payloads": (),
        },
        {
            "client": {
                "host": "make-mqtt-test",
                "station_sn": "AKTEST",
                "user_id": "123",
                "email": "user@example.test",
                "secret_key": "0" * 32,
            }
        },
        {
            "payload": {
                "commandType": 1133,
                "light": 1,
                "light_level": 1,
            },
            "expected_command_type": 1133,
            "preflight_query_payloads": (),
        },
        {
            "client": {
                "host": "make-mqtt-test",
                "station_sn": "AKTEST",
                "user_id": "123",
                "email": "user@example.test",
                "secret_key": "0" * 32,
            }
        },
        {
            "payload": {
                "commandType": 1133,
                "light": 0,
                "light_level": 0,
            },
            "expected_command_type": 1133,
            "preflight_query_payloads": (),
        },
    ]


def test_coordinator_preserves_previous_accessory_when_poll_lacks_accessory_packets() -> None:
    _stub_homeassistant()
    coordinator = _load_module(
        "custom_components.eufymake_e1.coordinator",
        COMPONENT_DIR / "coordinator.py",
    )

    data = {
        "current_accessory": None,
        "current_accessory_details": {
            "attachment_type": None,
            "plate_type": None,
            "version": None,
        },
    }
    coordinator._preserve_previous_accessory(
        data,
        {
            "current_accessory": "Roll-to-Film Attachment",
            "current_accessory_details": {
                "attachment_type": 3,
                "plate_type": 4,
                "version": "V1.1.16",
            },
        },
    )

    assert data["current_accessory"] == "Roll-to-Film Attachment"
    assert data["current_accessory_details"] == {
        "attachment_type": 3,
        "plate_type": 4,
        "version": "V1.1.16",
    }


def _load_real_const():
    return _load_module(
        "custom_components.eufymake_e1.const",
        COMPONENT_DIR / "const.py",
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
    update = types.ModuleType("homeassistant.components.update")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    exceptions = types.ModuleType("homeassistant.exceptions")
    helpers = types.ModuleType("homeassistant.helpers")
    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
    update_coordinator = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )

    class UpdateDeviceClass:
        FIRMWARE = "firmware"

    class UpdateEntity:
        pass

    class UpdateEntityFeature:
        PROGRESS = 1

    class ConfigEntry:
        pass

    class HomeAssistant:
        pass

    class ConfigEntryAuthFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, *args, **kwargs):
            pass

    class UpdateFailed(Exception):
        pass

    class CoordinatorEntity:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, coordinator, *args, **kwargs):
            self.coordinator = coordinator

    update.UpdateDeviceClass = UpdateDeviceClass
    update.UpdateEntity = UpdateEntity
    update.UpdateEntityFeature = UpdateEntityFeature
    config_entries.ConfigEntry = ConfigEntry
    core.HomeAssistant = HomeAssistant
    exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    entity_platform.AddEntitiesCallback = object
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.CoordinatorEntity = CoordinatorEntity
    update_coordinator.UpdateFailed = UpdateFailed
    components.update = update
    helpers.entity_platform = entity_platform
    helpers.update_coordinator = update_coordinator
    homeassistant.components = components
    homeassistant.config_entries = config_entries
    homeassistant.core = core
    homeassistant.exceptions = exceptions
    homeassistant.helpers = helpers

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.update"] = update
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.exceptions"] = exceptions
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator
