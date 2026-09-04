"""Runtime MQTT helpers used directly by the Home Assistant integration."""

from __future__ import annotations

import json
import secrets
import ssl
import struct
import tempfile
import time
from dataclasses import dataclass, field
from threading import Event
from typing import Any
from urllib.parse import unquote
from uuid import uuid4

MQTT_PORT = 8789
FIXED_IV = b"3DPrintAnkerMake"
GCM_FIXED_NONCE = b"3DPrintAnker"
APP_HEADER_SIZE = 64
DEVICE_HEADER_SIZE = 24
PACKET_TYPE_SINGLE = 0xC0
STATUS_QUERY_COMMAND = {"commandType": 1027, "value": 0}
ACCESSORY_INFO_COMMAND = 1153
PLATE_INFO_COMMAND = 1118
ACCESSORY_QUERY_COMMANDS = (
    {"commandType": PLATE_INFO_COMMAND},
    {"commandType": ACCESSORY_INFO_COMMAND},
)
PLATE_TYPE_NAMES = {
    0: "None",
    1: "Standard Flatbed",
    2: "Mini Flatbed",
    3: "Rotary Printing Attachment",
    4: "Roll-to-Film Attachment",
}
ATTACHMENT_TYPE_NAMES = {
    0: "None",
    1: "Mini Flatbed",
    2: "Standard Flatbed",
    3: "Roll-to-Film Attachment",
    4: "Rotary Printing Attachment",
}
PRINTER_STATE_NAMES = {
    0: "Idle",
    2: "Printing",
    4: "Printing",
    5: "Performing maintenance",
    6: "Firmware updating",
    8: "Checking status",
    9: "Calibrating",
    10: "Unavailable",
    13: "Maintenance",
}
PRINTER_STEP_STATE_NAMES = {
    (2, 1): "Sending file to device",
    (2, 2): "Ready to print",
    (2, 4): "Printing",
    (2, 5): "Preparing print",
    (2, 6): "Priming print head",
}
INK_INJECTION_COMMAND = 1136
WHITE_INK_RECOVERY_COMMAND = 1188
STATUS_CHECK_COMMAND = 1131
TEST_PRINT_COMMAND = 1064
TEST_PRINT_MODE = 4
PRINT_JOB_STATUS_COMMAND = 1001
DESIGN_PREPARATION_COMMAND = 1105
FILE_TRANSFER_COMMAND = 1053
SELF_CHECK_COMMAND = 1123
FIRMWARE_INFO_COMMAND = 1002
FIRMWARE_UPDATE_PROGRESS_COMMAND = 1047
FIRMWARE_UPDATE_NOTICE_COMMAND = 1048
FIRMWARE_UPDATE_RESULT_COMMAND = 1054
NOTIFICATION_SOUND_COMMAND = 1045
FILL_LIGHT_COMMAND = 1133
E1_READ_ONLY_SETTINGS_QUERY_COMMANDS: tuple[dict[str, int], ...] = (
    {"commandType": FIRMWARE_INFO_COMMAND},
)

MQTT_CA_PEM = """-----BEGIN CERTIFICATE-----
MIIDwTCCAqmgAwIBAgIJAKrbZvWARI3BMA0GCSqGSIb3DQEBCwUAMHUxCzAJBgNV
BAYTAkNOMREwDwYDVQQIDAhTaGVuemhlbjERMA8GA1UEBwwIU2hlbnpoZW4xEjAQ
BgNVBAoMCWFua2VybWFrZTESMBAGA1UECwwJYW5rZXJtYWtlMRgwFgYDVQQDDA8q
LmFua2VybWFrZS5jb20wIBcNMjIwNjE3MDMwNzU5WhgPMjEyMjA1MjQwMzA3NTla
MHUxCzAJBgNVBAYTAkNOMREwDwYDVQQIDAhTaGVuemhlbjERMA8GA1UEBwwIU2hl
bnpoZW4xEjAQBgNVBAoMCWFua2VybWFrZTESMBAGA1UECwwJYW5rZXJtYWtlMRgw
FgYDVQQDDA8qLmFua2VybWFrZS5jb20wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw
ggEKAoIBAQC8JWJzdVJFqrarK5oMCF8nI5QZ2nebs9df6CQHuSZCOmGCav5sDDFt
5IGhQ6G44++YNexC10kwxy10fOzIT6cZWnQrYQPBfS0y7G+yu/GPe9vXMWwkIcWv
hg8xAO+/m5C/QAj4BOVTXVl5spuBGX644P3eErV+tUDwb1U2K6mMzmaJ7SZqkmiw
QKfTK1KxH7oczcxjDtdbNdtpa1Rm3IUCCI2eAOQTlDHlKGGM2T+e6qQRCUQYqkiY
jG+3ugTzHMe6FMzOB1EjG0bZDemQwgUdBJexLgxrJe4jsVcuP75DfrV0NL/Drrmt
uJax3V4tu5Yx1RQCWqGTNPOahpS+qD+NAgMBAAGjUjBQMA4GA1UdDwEB/wQEAwID
iDATBgNVHSUEDDAKBggrBgEFBQcDATApBgNVHREEIjAggg1hbmtlcm1ha2UuY29t
gg8qLmFua2VybWFrZS5jb20wDQYJKoZIhvcNAQELBQADggEBALF/VDyZ21IdFejE
awLriK+Xo78k1yqf2YKWYSDMEJPXXHfbkHZTU0IL+K9kToN19sObuWPA1oE2iyKp
h4nKVDjy56Ntgt5lXeSTN08jlD0PzuuGfzPVxMrky8sp14pFT+Kw2HOEMLU6Hxj0
WjpprKRbl1oI8JoksYNzCSelIItokA8CI3/p1j5FyWxok99sVvNUfjG9iaV74Nuh
kY/1nm0T0aMPZKpcS0xS0JwA0tsySdDJP5t1KgmDa5D0hIhXuAJWGwUvg15vSyme
bk3IO48Nh8QOG8PwGebPus1nnvKCbG6+iJaWp/PqSqNCzx/Nht+Tfi413dIc3exF
LX0ZR20=
-----END CERTIFICATE-----"""


class EufyMakeRuntimeError(Exception):
    """Raised when live eufyMake communication fails."""


@dataclass(frozen=True, kw_only=True)
class Device:
    """A eufyMake device needed for runtime MQTT."""

    serial_number: str
    secret_key: str | None
    firmware_version: str | None


@dataclass(frozen=True, kw_only=True)
class MqttCredentials:
    """MQTT CONNECT credentials."""

    username: str
    password: str
    client_id: str


@dataclass(frozen=True, kw_only=True)
class MqttTopics:
    """MQTT topics used for one eufyMake E1 device."""

    notice: str
    command_reply: str
    query_reply: str
    maker_change_notice: str
    user_change_notice: str
    command: str
    query: str

    @property
    def subscriptions(self) -> tuple[str, ...]:
        """Return exact non-wildcard subscriptions."""
        return (
            self.notice,
            self.command_reply,
            self.query_reply,
            self.maker_change_notice,
            self.user_change_notice,
        )


@dataclass(frozen=True, kw_only=True)
class MqttProbePlan:
    """Inputs for one live MQTT status probe."""

    host: str
    port: int
    credentials: MqttCredentials
    topics: MqttTopics
    device: Device
    status_query: dict[str, int]


@dataclass(frozen=True, kw_only=True)
class InkChannel:
    """One E1 ink channel."""

    channel: str
    remaining_percent: float | None
    status: int | None
    manufacture_timestamp: int | None
    expiration_timestamp: int | None
    distance_expiration_days: int | None
    expired: bool | None


@dataclass(frozen=True, kw_only=True)
class WasteInkTank:
    """E1 waste ink tank status."""

    remaining_percent: float | None
    status: int | None
    expiration_timestamp: int | None
    distance_expiration_days: int | None
    expired: bool | None


@dataclass(frozen=True, kw_only=True)
class InkStatus:
    """Parsed E1 ink and waste tank status."""

    channels: tuple[InkChannel, ...]
    waste_tank: WasteInkTank | None


@dataclass(frozen=True, kw_only=True)
class AccessoryStatus:
    """Parsed E1 accessory or plate status."""

    name: str | None
    attachment_type: int | None
    plate_type: int | None
    version: str | None


@dataclass(frozen=True, kw_only=True)
class PrinterStatus:
    """Parsed E1 printer status."""

    name: str | None
    state: int | None
    step: int | None
    maintainable: bool | None
    error_codes: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class InkInjectionStatus:
    """Parsed E1 ink injection status."""

    active: bool | None
    progress: int | None


@dataclass(frozen=True, kw_only=True)
class WhiteInkRecoveryStatus:
    """Parsed E1 white ink recovery status."""

    active: bool | None
    progress: int | None


@dataclass(frozen=True, kw_only=True)
class StatusCheckStatus:
    """Parsed E1 pre-print status check status."""

    active: bool | None
    progress: int | None


@dataclass(frozen=True, kw_only=True)
class TestPrintStatus:
    """Parsed E1 test print status."""

    active: bool | None
    progress: int | None


@dataclass(frozen=True, kw_only=True)
class PrintJobStatus:
    """Parsed E1 normal print job status."""

    active: bool | None
    progress: int | None
    remaining_time: int | None
    elapsed_time: int | None


@dataclass(frozen=True, kw_only=True)
class DesignPreparationStatus:
    """Parsed E1 design preparation status."""

    name: str | None
    active: bool | None
    progress: int | None
    height: float | None
    plate_type: int | None
    plate_print_width: int | None
    plate_print_height: int | None


@dataclass(frozen=True, kw_only=True)
class FileTransferStatus:
    """Parsed E1 print file transfer status."""

    active: bool | None
    progress: int | None
    result: int | None


@dataclass(frozen=True, kw_only=True)
class SelfCheckStatus:
    """Parsed E1 self-check or calibration status."""

    active: bool | None
    progress: int | None
    status: int | None
    error_count: int | None


@dataclass(frozen=True, kw_only=True)
class FirmwareUpdateStatus:
    """Parsed E1 firmware update state."""

    available: bool | None
    current_version: str | None
    target_version: str | None
    forced: bool | None
    upgrade_flag: int | None
    release_note: str | None
    reply: int | None
    active: bool | None
    download_progress: int | None
    upgrade_progress: int | None
    speed: int | None
    file_size: int | None
    upgrade_result: int | None
    error_code: int | None


@dataclass(frozen=True, kw_only=True)
class NotificationSoundStatus:
    """Parsed E1 notification sound settings."""

    enabled: bool | None
    level: int | None


@dataclass(frozen=True, kw_only=True)
class FillLightStatus:
    """Parsed E1 fill-in light settings."""

    enabled: bool | None
    level: int | None


@dataclass(frozen=True, kw_only=True)
class DecodedMqttMessage:
    """A decoded MQTT message."""

    topic: str
    variant: str
    payload: Any
    command_type: int | None


@dataclass(frozen=True, kw_only=True)
class MqttStatusResult:
    """Result from one MQTT status probe."""

    messages: int
    decoded: int
    undecoded: int
    ink_status: InkStatus | None
    decoded_messages: tuple[DecodedMqttMessage, ...] = field(default_factory=tuple)


def build_probe_plan(
    *,
    host: str,
    station_sn: str,
    user_id: str,
    email: str,
    secret_key: str,
    firmware_version: str | None,
) -> MqttProbePlan:
    """Build a live MQTT probe plan from a Home Assistant config entry."""
    device = Device(
        serial_number=station_sn,
        secret_key=secret_key,
        firmware_version=firmware_version,
    )
    return MqttProbePlan(
        host=host,
        port=MQTT_PORT,
        credentials=MqttCredentials(
            username=f"eufy_{user_id}",
            password=unquote(email),
            client_id=build_client_id(user_id),
        ),
        topics=build_topics(station_sn, user_id),
        device=device,
        status_query=dict(STATUS_QUERY_COMMAND),
    )


def build_client_id(user_id: str) -> str:
    """Build a desktop-style MQTT client id."""
    random_hex = secrets.token_hex(6)
    timestamp_ms = int(time.time() * 1000)
    return f"pc_windows_AnkerMakeStudio_direct_{user_id}_{random_hex}_{timestamp_ms}"


def build_topics(station_sn: str, user_id: str) -> MqttTopics:
    """Build exact MQTT topics for a station/user pair."""
    return MqttTopics(
        notice=f"/phone/maker/{station_sn}/notice",
        command_reply=f"/phone/maker/{station_sn}/command/reply",
        query_reply=f"/phone/maker/{station_sn}/query/reply",
        maker_change_notice=f"/phone/maker/{station_sn}/change_notice",
        user_change_notice=f"/phone/user/{user_id}/change_notice",
        command=f"/device/maker/{station_sn}/command",
        query=f"/device/maker/{station_sn}/query",
    )


class EufyMakeMqttStatusClient:
    """Fetch one live E1 status snapshot through eufyMake MQTT."""

    def __init__(self, plan: MqttProbePlan) -> None:
        """Initialize the MQTT status client."""
        if not plan.device.secret_key:
            raise EufyMakeRuntimeError("Cached E1 secret key is unavailable")
        self.plan = plan

    def fetch_once(
        self,
        *,
        timeout: float = 25,
        listen_after_ink: float = 0,
        query_payloads: tuple[dict[str, Any], ...] | None = None,
    ) -> MqttStatusResult:
        """Connect, request status, and wait for an ink status message."""
        try:
            import paho.mqtt.client as mqtt
        except ImportError as err:
            raise EufyMakeRuntimeError("paho-mqtt is not installed") from err

        done = Event()
        decoded_messages: list[DecodedMqttMessage] = []
        state: dict[str, Any] = {
            "messages": 0,
            "decoded": 0,
            "undecoded": 0,
            "ink_status": None,
            "ink_seen_at": None,
            "error": None,
        }

        client = _build_client(mqtt, self.plan.credentials.client_id)
        client.username_pw_set(
            self.plan.credentials.username,
            password=self.plan.credentials.password,
        )
        _set_tls(client)

        def on_connect(
            client: Any,
            userdata: Any,
            flags: Any,
            rc: Any,
            *extra: Any,
        ) -> None:
            code = _reason_code_value(rc)
            if code != 0:
                state["error"] = f"MQTT connect failed with code {code}"
                done.set()
                return
            for topic in self.plan.topics.subscriptions:
                client.subscribe(topic, qos=0)
            payloads = query_payloads or (self.plan.status_query,)
            for payload in payloads:
                client.publish(
                    self.plan.topics.query,
                    build_app_frame(payload, self.plan.device.secret_key),
                    qos=0,
                )

        def on_message(client: Any, userdata: Any, message: Any) -> None:
            state["messages"] += 1
            decoded = self._try_decode(message.payload)
            if decoded is None:
                state["undecoded"] += 1
                return

            variant, payload = decoded
            state["decoded"] += 1
            decoded_message = DecodedMqttMessage(
                topic=message.topic,
                variant=variant,
                payload=payload,
                command_type=_command_type(payload),
            )
            decoded_messages.append(decoded_message)

            ink_status = find_ink_status(payload)
            if ink_status is not None:
                state["ink_status"] = ink_status
                if state["ink_seen_at"] is None:
                    state["ink_seen_at"] = time.monotonic()
                if listen_after_ink <= 0:
                    done.set()

            if (
                listen_after_ink <= 0
                and state["ink_status"] is not None
                and _has_accessory_status(tuple(decoded_messages))
            ):
                done.set()

        def on_disconnect(
            client: Any,
            userdata: Any,
            disconnect_flags: Any,
            reason_code: Any,
            *extra: Any,
        ) -> None:
            code = _reason_code_value(reason_code)
            if code != 0 and not done.is_set():
                state["error"] = f"MQTT disconnected with code {code}"
                done.set()

        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect

        try:
            client.connect(self.plan.host, self.plan.port, keepalive=30)
            client.loop_start()
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if done.wait(0.2):
                    break
                ink_seen_at = state["ink_seen_at"]
                if (
                    ink_seen_at is not None
                    and listen_after_ink > 0
                    and time.monotonic() - float(ink_seen_at) >= listen_after_ink
                ):
                    break
        except Exception as err:
            raise EufyMakeRuntimeError(f"MQTT probe failed: {err}") from err
        finally:
            client.loop_stop()
            client.disconnect()

        if state["error"]:
            raise EufyMakeRuntimeError(str(state["error"]))

        return MqttStatusResult(
            messages=int(state["messages"]),
            decoded=int(state["decoded"]),
            undecoded=int(state["undecoded"]),
            ink_status=state["ink_status"],
            decoded_messages=tuple(decoded_messages),
        )

    def _try_decode(self, payload: bytes) -> tuple[str, Any] | None:
        secret_key = self.plan.device.secret_key
        if secret_key is None:
            return None
        decoders = (
            ("cbc", decrypt_json_frame),
            ("gcm", decrypt_json_gcm_payload),
        )
        for variant, decoder in decoders:
            try:
                return variant, decoder(payload, secret_key)
            except EufyMakeRuntimeError:
                pass
        return None


class EufyMakeMqttCommandClient:
    """Send one command to a eufyMake MQTT device and wait for a reply."""

    def __init__(
        self,
        *,
        host: str,
        station_sn: str,
        user_id: str,
        email: str,
        secret_key: str,
    ) -> None:
        """Initialize the command client."""
        self.host = host
        self.credentials = MqttCredentials(
            username=f"eufy_{user_id}",
            password=unquote(email),
            client_id=build_client_id(user_id),
        )
        self.topics = build_topics(station_sn, user_id)
        self.secret_key = secret_key

    def send(
        self,
        payload: dict[str, Any],
        *,
        expected_command_type: int,
        preflight_query_payloads: tuple[dict[str, Any], ...] = (),
        preflight_timeout: float = 2,
        timeout: float = 15,
    ) -> tuple[DecodedMqttMessage, ...]:
        """Publish a command and return decoded reply/state messages."""
        try:
            import paho.mqtt.client as mqtt
        except ImportError as err:
            raise EufyMakeRuntimeError("paho-mqtt is not installed") from err

        done = Event()
        decoded_messages: list[DecodedMqttMessage] = []
        preflight_command_types = {
            _command_type(item) for item in preflight_query_payloads
        }
        preflight_command_types.discard(None)
        state: dict[str, Any] = {
            "command_published": False,
            "error": None,
            "preflight_seen": set(),
            "preflight_started_at": None,
            "reply": None,
            "state_echo": None,
        }

        client = _build_client(mqtt, self.credentials.client_id)
        client.username_pw_set(
            self.credentials.username,
            password=self.credentials.password,
        )
        _set_tls(client)

        def on_connect(
            client: Any,
            userdata: Any,
            flags: Any,
            rc: Any,
            *extra: Any,
        ) -> None:
            code = _reason_code_value(rc)
            if code != 0:
                state["error"] = f"MQTT connect failed with code {code}"
                done.set()
                return
            for topic in self.topics.subscriptions:
                client.subscribe(topic, qos=0)
            if preflight_query_payloads:
                state["preflight_started_at"] = time.monotonic()
                for preflight_payload in preflight_query_payloads:
                    client.publish(
                        self.topics.query,
                        build_app_frame(preflight_payload, self.secret_key),
                        qos=0,
                    )
                return
            publish_command(client)

        def publish_command(client: Any) -> None:
            if state["command_published"]:
                return
            state["command_published"] = True
            client.publish(
                self.topics.command,
                build_app_frame(payload, self.secret_key),
                qos=0,
            )

        def on_message(client: Any, userdata: Any, message: Any) -> None:
            decoded = self._try_decode(message.payload)
            if decoded is None:
                return
            variant, decoded_payload = decoded
            if not isinstance(decoded_payload, dict):
                return
            decoded_message = DecodedMqttMessage(
                topic=message.topic,
                variant=variant,
                payload=decoded_payload,
                command_type=_command_type(decoded_payload),
            )
            decoded_messages.append(decoded_message)
            if (
                not state["command_published"]
                and decoded_message.command_type in preflight_command_types
            ):
                preflight_seen = state["preflight_seen"]
                if isinstance(preflight_seen, set):
                    preflight_seen.add(decoded_message.command_type)
                    if preflight_seen >= preflight_command_types:
                        publish_command(client)
                return
            if not state["command_published"]:
                return
            if decoded_message.command_type == expected_command_type:
                if "reply" in decoded_payload:
                    state["reply"] = decoded_payload
                elif _command_state_matches(payload, decoded_payload):
                    state["state_echo"] = decoded_payload
                    done.set()
            if state["reply"] is not None and _command_reply_ok(state["reply"]):
                done.set()

        def on_disconnect(
            client: Any,
            userdata: Any,
            disconnect_flags: Any,
            reason_code: Any,
            *extra: Any,
        ) -> None:
            code = _reason_code_value(reason_code)
            if code != 0 and not done.is_set():
                state["error"] = f"MQTT disconnected with code {code}"
                done.set()

        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect

        try:
            client.connect(self.host, MQTT_PORT, keepalive=30)
            client.loop_start()
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if done.wait(0.2):
                    break
                preflight_started_at = state["preflight_started_at"]
                if (
                    not state["command_published"]
                    and preflight_started_at is not None
                    and time.monotonic() - float(preflight_started_at)
                    >= preflight_timeout
                ):
                    publish_command(client)
        except Exception as err:
            raise EufyMakeRuntimeError(f"MQTT command failed: {err}") from err
        finally:
            client.loop_stop()
            client.disconnect()

        if state["error"]:
            raise EufyMakeRuntimeError(str(state["error"]))
        if state["reply"] is not None and not _command_reply_ok(state["reply"]):
            raise EufyMakeRuntimeError(f"MQTT command was rejected: {state['reply']}")
        if state["reply"] is None and state["state_echo"] is None:
            raise EufyMakeRuntimeError("No MQTT command reply received")
        return tuple(decoded_messages)

    def _try_decode(self, payload: bytes) -> tuple[str, Any] | None:
        for variant, decoder in (
            ("cbc", decrypt_json_frame),
            ("gcm", decrypt_json_gcm_payload),
        ):
            try:
                return variant, decoder(payload, self.secret_key)
            except EufyMakeRuntimeError:
                pass
        return None


def _command_reply_ok(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    try:
        return int(payload.get("reply")) == 0
    except (TypeError, ValueError):
        return False


def _command_state_matches(command: dict[str, Any], state: dict[str, Any]) -> bool:
    """Return whether a command-shaped state echo confirms the requested command."""
    matched_state_fields = 0
    for key, value in state.items():
        if key in {"commandType", "reply"}:
            continue
        if key not in command:
            continue
        if command[key] != value:
            return False
        matched_state_fields += 1
    return matched_state_fields > 0


def _set_tls(client: Any) -> None:
    """Configure TLS with the bundled eufyMake MQTT trust anchor."""
    context = ssl.create_default_context(cadata=MQTT_CA_PEM)
    try:
        client.tls_set_context(context)
        return
    except AttributeError:
        pass

    with tempfile.NamedTemporaryFile("w", encoding="ascii", suffix=".pem") as handle:
        handle.write(MQTT_CA_PEM)
        handle.flush()
        client.tls_set(ca_certs=handle.name, tls_version=ssl.PROTOCOL_TLS_CLIENT)


def build_app_frame(payload: dict[str, Any], secret_key_hex: str) -> bytes:
    """Encrypt a JSON payload and wrap it in an app-to-printer MQTT frame."""
    ciphertext = encrypt_json_payload(payload, secret_key_hex)
    guid = str(uuid4()).encode("ascii").ljust(37, b"\x00")
    header = bytearray(APP_HEADER_SIZE)
    total_size = len(header) + len(ciphertext) + 1

    header[0:2] = b"MA"
    struct.pack_into("<H", header, 2, total_size)
    header[4] = 0x05
    header[5] = 0x01
    header[6] = 0x02
    header[7] = 0x05
    header[8] = 0x46
    header[9] = PACKET_TYPE_SINGLE
    struct.pack_into("<H", header, 10, 0)
    header[16:53] = guid

    frame_without_checksum = bytes(header) + ciphertext
    return frame_without_checksum + bytes([xor_checksum(frame_without_checksum)])


def decrypt_json_frame(frame: bytes, secret_key_hex: str) -> Any:
    """Decrypt an MQTT CBC frame and parse its JSON payload."""
    if len(frame) < DEVICE_HEADER_SIZE + 1 or frame[:2] != b"MA":
        raise EufyMakeRuntimeError("Invalid MA frame")

    total_size = struct.unpack_from("<H", frame, 2)[0]
    if total_size != len(frame) or frame[-1] != xor_checksum(frame[:-1]):
        raise EufyMakeRuntimeError("Invalid MA frame checksum or size")

    header_size = APP_HEADER_SIZE if frame[6] == 0x02 else DEVICE_HEADER_SIZE
    ciphertext = frame[header_size:-1]
    if len(ciphertext) == 0 or len(ciphertext) % 16 != 0:
        raise EufyMakeRuntimeError("Invalid MA ciphertext")
    return parse_json_payload(decrypt_payload(ciphertext, secret_key_hex))


def decrypt_json_gcm_payload(payload: bytes, secret_key_hex: str) -> Any:
    """Decrypt the alternate GCM MQTT payload shape and parse JSON."""
    if len(payload) < 21:
        raise EufyMakeRuntimeError("GCM payload is too short")
    tag = payload[4:20]
    ciphertext = payload[20:]
    return parse_json_payload(decrypt_gcm_payload(ciphertext, tag, secret_key_hex))


def encrypt_json_payload(payload: dict[str, Any], secret_key_hex: str) -> bytes:
    """Serialize and encrypt a JSON payload."""
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return encrypt_payload(plaintext, secret_key_hex)


def encrypt_payload(plaintext: bytes, secret_key_hex: str) -> bytes:
    """Encrypt payload bytes with the E1 AES-CBC MQTT frame key."""
    key = _secret_key_bytes(secret_key_hex)
    try:
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except ImportError as err:
        raise EufyMakeRuntimeError("cryptography is not installed") from err

    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(FIXED_IV)).encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def decrypt_payload(ciphertext: bytes, secret_key_hex: str) -> bytes:
    """Decrypt payload bytes with the E1 AES-CBC MQTT frame key."""
    key = _secret_key_bytes(secret_key_hex)
    try:
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except ImportError as err:
        raise EufyMakeRuntimeError("cryptography is not installed") from err

    decryptor = Cipher(algorithms.AES(key), modes.CBC(FIXED_IV)).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def decrypt_gcm_payload(
    ciphertext: bytes,
    tag: bytes,
    secret_key_hex: str,
) -> bytes:
    """Decrypt payload bytes with the alternate AES-GCM frame key."""
    key = _secret_key_bytes(secret_key_hex)
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as err:
        raise EufyMakeRuntimeError("cryptography is not installed") from err

    return AESGCM(key).decrypt(GCM_FIXED_NONCE, ciphertext + tag, None)


def parse_json_payload(plaintext: bytes) -> Any:
    """Parse decrypted JSON payload bytes."""
    try:
        return json.loads(plaintext.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise EufyMakeRuntimeError("Frame payload is not JSON") from err


def find_ink_status(payload: Any) -> InkStatus | None:
    """Find and parse the first commandType 1100 status message."""
    messages = payload if isinstance(payload, list) else [payload]
    for message in messages:
        if (
            isinstance(message, dict)
            and _optional_int(message.get("commandType")) == 1100
        ):
            return parse_ink_status(message)
    return None


def find_accessory_status(messages: tuple[DecodedMqttMessage, ...]) -> AccessoryStatus:
    """Find the latest accessory status from decoded MQTT messages."""
    attachment_type = None
    plate_type = None
    version = None

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue

        command_type = _optional_int(payload.get("commandType"))
        if command_type == ACCESSORY_INFO_COMMAND:
            attachment_type = _optional_int(payload.get("attType"))
            raw_version = payload.get("version")
            version = raw_version if isinstance(raw_version, str) else None
        elif command_type == PLATE_INFO_COMMAND:
            plate_type = _optional_int(payload.get("plateType"))

    name = _accessory_name(plate_type, attachment_type)
    return AccessoryStatus(
        name=name,
        attachment_type=attachment_type,
        plate_type=plate_type,
        version=version,
    )


def find_printer_status(messages: tuple[DecodedMqttMessage, ...]) -> PrinterStatus:
    """Find the latest printer state from decoded MQTT messages."""
    state = None
    step = None
    maintainable = None
    error_codes: tuple[str, ...] = ()

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue
        if _optional_int(payload.get("commandType")) != 1000:
            continue
        status = payload.get("status")
        if not isinstance(status, dict):
            continue

        state = _optional_int(status.get("state"))
        step = _optional_int(status.get("step"))
        ext = status.get("ext")
        if isinstance(ext, dict):
            maintainable = _optional_bool(ext.get("maintainable"))
            error_codes = tuple(
                str(code) for code in _list(ext.get("errorCodes")) if code is not None
            )
        else:
            maintainable = None
            error_codes = ()

    return PrinterStatus(
        name=_printer_state_name(state, step),
        state=state,
        step=step,
        maintainable=maintainable,
        error_codes=error_codes,
    )


def find_ink_injection_status(
    messages: tuple[DecodedMqttMessage, ...],
) -> InkInjectionStatus:
    """Find the latest ink injection state from decoded MQTT messages."""
    active = None
    progress = None

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue
        if _optional_int(payload.get("commandType")) != INK_INJECTION_COMMAND:
            continue
        active = _optional_bool(payload.get("value"))
        progress = _optional_int(payload.get("progress"))

    return InkInjectionStatus(active=active, progress=progress)


def find_white_ink_recovery_status(
    messages: tuple[DecodedMqttMessage, ...],
) -> WhiteInkRecoveryStatus:
    """Find the latest white ink recovery state from decoded MQTT messages."""
    active = None
    progress = None

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue
        if _optional_int(payload.get("commandType")) != WHITE_INK_RECOVERY_COMMAND:
            continue
        active = _optional_bool(payload.get("value"))
        progress = _optional_int(payload.get("progress"))

    return WhiteInkRecoveryStatus(active=active, progress=progress)


def find_status_check_status(
    messages: tuple[DecodedMqttMessage, ...],
) -> StatusCheckStatus:
    """Find the latest pre-print status check state from decoded MQTT messages."""
    active = None
    progress = None

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue
        if _optional_int(payload.get("commandType")) != STATUS_CHECK_COMMAND:
            continue
        active = _optional_bool(payload.get("value"))
        progress = _optional_int(payload.get("progress"))

    return StatusCheckStatus(active=active, progress=progress)


def find_test_print_status(
    messages: tuple[DecodedMqttMessage, ...],
) -> TestPrintStatus:
    """Find the latest test print state from decoded MQTT messages."""
    active = None
    progress = None

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue
        if _optional_int(payload.get("commandType")) != TEST_PRINT_COMMAND:
            continue
        if _optional_int(payload.get("mode")) != TEST_PRINT_MODE:
            continue

        progress = _optional_int(payload.get("progress"))
        if progress is not None:
            active = progress < 100

    return TestPrintStatus(
        active=active,
        progress=progress,
    )


def find_print_job_status(
    messages: tuple[DecodedMqttMessage, ...],
) -> PrintJobStatus:
    """Find the latest normal print job progress from decoded MQTT messages."""
    active = None
    progress = None
    remaining_time = None
    elapsed_time = None

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue
        if _optional_int(payload.get("commandType")) != PRINT_JOB_STATUS_COMMAND:
            continue

        progress = _hundredths_progress(payload.get("progress"))
        remaining_time = _optional_int(payload.get("time"))
        elapsed_time = _optional_int(payload.get("totalTime"))
        if progress is not None:
            active = progress < 100

    return PrintJobStatus(
        active=active,
        progress=progress,
        remaining_time=remaining_time,
        elapsed_time=elapsed_time,
    )


def find_design_preparation_status(
    messages: tuple[DecodedMqttMessage, ...],
) -> DesignPreparationStatus:
    """Find the latest design preparation progress from decoded MQTT messages."""
    active = None
    progress = None
    step = None
    height = None
    plate_type = None
    plate_print_width = None
    plate_print_height = None

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue
        if _optional_int(payload.get("commandType")) != DESIGN_PREPARATION_COMMAND:
            continue

        active = _optional_bool(payload.get("value"))
        progress = _optional_int(payload.get("progress"))
        step = _optional_int(payload.get("step"))
        height = _optional_float(payload.get("height"))
        plate_type = _optional_int(payload.get("plate_type"))
        plate_print_width = _optional_int(payload.get("plate_print_width"))
        plate_print_height = _optional_int(payload.get("plate_print_height"))

    return DesignPreparationStatus(
        name=_design_preparation_name(step),
        active=active,
        progress=progress,
        height=height,
        plate_type=plate_type,
        plate_print_width=plate_print_width,
        plate_print_height=plate_print_height,
    )


def find_file_transfer_status(
    messages: tuple[DecodedMqttMessage, ...],
) -> FileTransferStatus:
    """Find the latest print file transfer progress from decoded MQTT messages."""
    active = None
    progress = None
    result = None

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue
        if _optional_int(payload.get("commandType")) != FILE_TRANSFER_COMMAND:
            continue

        progress = _optional_int(payload.get("downloadFileProgress"))
        result = _optional_int(payload.get("result"))
        if progress is not None:
            active = progress < 100
        if result == 1:
            active = False

    return FileTransferStatus(
        active=active,
        progress=progress,
        result=result,
    )


def find_self_check_status(
    messages: tuple[DecodedMqttMessage, ...],
) -> SelfCheckStatus:
    """Find the latest self-check or calibration progress."""
    active = None
    progress = None
    status = None
    error_count = None

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue
        if _optional_int(payload.get("commandType")) != SELF_CHECK_COMMAND:
            continue

        progress = _optional_int(payload.get("progress"))
        status = _optional_int(payload.get("status"))
        result = payload.get("result")
        if isinstance(result, dict):
            error_count = _optional_int(result.get("err_cnt"))
        if progress is not None:
            active = progress < 100
        if status == 3:
            active = False

    return SelfCheckStatus(
        active=active,
        progress=progress,
        status=status,
        error_count=error_count,
    )


def find_firmware_update_status(
    messages: tuple[DecodedMqttMessage, ...],
) -> FirmwareUpdateStatus:
    """Find the latest firmware update state from decoded MQTT messages."""
    available = None
    current_version = None
    target_version = None
    forced = None
    upgrade_flag = None
    release_note = None
    reply = None
    active = None
    download_progress = None
    upgrade_progress = None
    speed = None
    file_size = None
    upgrade_result = None
    error_code = None

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue
        command_type = _optional_int(payload.get("commandType"))
        if command_type not in (
            FIRMWARE_INFO_COMMAND,
            FIRMWARE_UPDATE_PROGRESS_COMMAND,
            FIRMWARE_UPDATE_NOTICE_COMMAND,
            FIRMWARE_UPDATE_RESULT_COMMAND,
        ):
            continue

        parsed_reply = _optional_int(payload.get("reply"))
        if parsed_reply is not None:
            reply = parsed_reply
        if command_type in (FIRMWARE_INFO_COMMAND, FIRMWARE_UPDATE_NOTICE_COMMAND):
            raw_current = payload.get("currVer")
            raw_target = payload.get("tagerVer")
            raw_note = payload.get("releaseNote")
            if isinstance(raw_current, str):
                current_version = raw_current
            if isinstance(raw_target, str):
                target_version = raw_target
            if isinstance(raw_note, str):
                release_note = raw_note

            parsed_forced = _optional_bool(payload.get("forceUpgrade"))
            if parsed_forced is not None:
                forced = parsed_forced
            parsed_upgrade_flag = _optional_int(payload.get("upgradeFlag"))
            if parsed_upgrade_flag is not None:
                upgrade_flag = parsed_upgrade_flag

            parsed_available = _firmware_target_differs(
                current_version,
                target_version,
            )
            if parsed_available is False:
                parsed_available = _optional_bool(payload.get("isUpgrade"))
            if parsed_available is not None:
                available = parsed_available

            package = payload.get("full_package")
            if isinstance(package, dict):
                parsed_file_size = _optional_int(package.get("file_size"))
                if parsed_file_size:
                    file_size = parsed_file_size
            parsed_file_size = _optional_int(payload.get("file_size"))
            if parsed_file_size:
                file_size = parsed_file_size

        elif command_type == FIRMWARE_UPDATE_PROGRESS_COMMAND:
            parsed_download = _optional_int(payload.get("download"))
            parsed_upgrade = _optional_int(payload.get("upgrade"))
            if parsed_download is not None:
                download_progress = parsed_download
            if parsed_upgrade is not None:
                upgrade_progress = parsed_upgrade
                active = parsed_upgrade < 100
            parsed_speed = _optional_int(payload.get("speed"))
            if parsed_speed is not None:
                speed = parsed_speed
            parsed_file_size = _optional_int(payload.get("file_size"))
            if parsed_file_size:
                file_size = parsed_file_size
            parsed_forced = _optional_bool(payload.get("forceUpgrade"))
            if parsed_forced is not None:
                forced = parsed_forced

        elif command_type == FIRMWARE_UPDATE_RESULT_COMMAND:
            raw_current = payload.get("currVer")
            if isinstance(raw_current, str):
                current_version = raw_current
            upgrade_result = _optional_int(payload.get("upgradeResult"))
            error_code = _optional_int(payload.get("errorCode"))
            active = False
            if upgrade_result == 1 and error_code in (None, 0):
                available = False
                target_version = current_version or target_version

    return FirmwareUpdateStatus(
        available=available,
        current_version=current_version,
        target_version=target_version,
        forced=forced,
        upgrade_flag=upgrade_flag,
        release_note=release_note,
        reply=reply,
        active=active,
        download_progress=download_progress,
        upgrade_progress=upgrade_progress,
        speed=speed,
        file_size=file_size,
        upgrade_result=upgrade_result,
        error_code=error_code,
    )


def find_notification_sound_status(
    messages: tuple[DecodedMqttMessage, ...],
) -> NotificationSoundStatus:
    """Find the latest notification sound settings from decoded MQTT messages."""
    enabled = None
    level = None

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue
        if _optional_int(payload.get("commandType")) != NOTIFICATION_SOUND_COMMAND:
            continue
        enabled = _optional_bool(payload.get("beep"))
        level = _optional_int(payload.get("beep_level"))

    return NotificationSoundStatus(enabled=enabled, level=level)


def find_fill_light_status(
    messages: tuple[DecodedMqttMessage, ...],
) -> FillLightStatus:
    """Find the latest fill-in light settings from decoded MQTT messages."""
    enabled = None
    level = None

    for decoded_message in messages:
        payload = decoded_message.payload
        if not isinstance(payload, dict):
            continue
        if _optional_int(payload.get("commandType")) != FILL_LIGHT_COMMAND:
            continue
        parsed_enabled = _optional_bool(payload.get("light"))
        parsed_level = _optional_int(payload.get("light_level"))
        if parsed_enabled is not None:
            enabled = parsed_enabled
        if parsed_level is not None:
            level = parsed_level

    return FillLightStatus(enabled=enabled, level=level)


def _has_accessory_status(messages: tuple[DecodedMqttMessage, ...]) -> bool:
    status = find_accessory_status(messages)
    return status.plate_type is not None and status.attachment_type is not None


def parse_ink_status(message: dict[str, Any]) -> InkStatus:
    """Parse a commandType 1100 ink status message."""
    ink = message.get("ink")
    waste_ink = message.get("wasteInk")
    return InkStatus(
        channels=_parse_channels(ink if isinstance(ink, dict) else {}),
        waste_tank=_parse_waste_tank(waste_ink if isinstance(waste_ink, dict) else {}),
    )


def _parse_channels(ink: dict[str, Any]) -> tuple[InkChannel, ...]:
    channels = _list(ink.get("colorSort"))
    levels = _list(ink.get("leftInk"))
    statuses = _list(ink.get("status"))
    manufacture = _first_existing_list(
        ink,
        ("manufactureTimestamp", "manufactureTime"),
    )
    expiration = _list(ink.get("expirationTimestamp"))
    distance_expiration = _list(ink.get("distanceExpiration"))
    expired = _list(ink.get("expired"))
    if not channels:
        count = _optional_int(ink.get("count")) or len(levels)
        channels = [str(index + 1) for index in range(count)]
    return tuple(
        InkChannel(
            channel=str(channel),
            remaining_percent=_hundredths_percent(_at(levels, index)),
            status=_optional_int(_at(statuses, index)),
            manufacture_timestamp=_optional_int(_at(manufacture, index)),
            expiration_timestamp=_optional_int(_at(expiration, index)),
            distance_expiration_days=_optional_int(
                _at(distance_expiration, index)
            ),
            expired=_optional_bool(_at(expired, index)),
        )
        for index, channel in enumerate(channels)
    )


def _parse_waste_tank(waste_ink: dict[str, Any]) -> WasteInkTank | None:
    if not waste_ink:
        return None
    levels = _first_existing_list(
        waste_ink,
        ("leftInk", "remainingInk", "remaining", "level"),
    )
    statuses = _list(waste_ink.get("status"))
    expiration = _list(waste_ink.get("expirationTimestamp"))
    distance_expiration = _list(waste_ink.get("distanceExpiration"))
    expired = _list(waste_ink.get("expired"))
    return WasteInkTank(
        remaining_percent=_hundredths_percent(_at(levels, 0)),
        status=_optional_int(_at(statuses, 0)),
        expiration_timestamp=_optional_int(_at(expiration, 0)),
        distance_expiration_days=_optional_int(_at(distance_expiration, 0)),
        expired=_optional_bool(_at(expired, 0)),
    )


def _build_client(mqtt: Any, client_id: str) -> Any:
    try:
        return mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
        )
    except AttributeError:
        return mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)


def _reason_code_value(reason_code: Any) -> int:
    return int(getattr(reason_code, "value", reason_code))


def _command_type(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None
    return _optional_int(payload.get("commandType"))


def _secret_key_bytes(secret_key_hex: str) -> bytes:
    try:
        key = bytes.fromhex(secret_key_hex)
    except ValueError as err:
        raise EufyMakeRuntimeError("Secret key must be hex encoded") from err
    if len(key) != 32:
        raise EufyMakeRuntimeError("Secret key must decode to 32 bytes")
    return key


def xor_checksum(data: bytes) -> int:
    """Return the one-byte XOR checksum used by MQTT frames."""
    checksum = 0
    for item in data:
        checksum ^= item
    return checksum


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _first_existing_list(data: dict[str, Any], keys: tuple[str, ...]) -> list[Any]:
    for key in keys:
        if key in data:
            return _list(data.get(key))
    return []


def _at(values: list[Any], index: int) -> Any:
    try:
        return values[index]
    except IndexError:
        return None


def _hundredths_percent(value: Any) -> float | None:
    parsed = _optional_int(value)
    if parsed is None:
        return None
    return parsed / 100


def _hundredths_progress(value: Any) -> int | None:
    parsed = _optional_int(value)
    if parsed is None:
        return None
    return max(0, min(100, round(parsed / 100)))


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: Any) -> bool | None:
    parsed = _optional_int(value)
    if parsed is None:
        return None
    return bool(parsed)


def _firmware_target_differs(
    current_version: str | None,
    target_version: str | None,
) -> bool | None:
    if not target_version:
        return False
    if not current_version:
        return True
    return current_version != target_version


def _accessory_name(plate_type: int | None, attachment_type: int | None) -> str | None:
    if plate_type in PLATE_TYPE_NAMES:
        return PLATE_TYPE_NAMES[plate_type]
    if attachment_type in ATTACHMENT_TYPE_NAMES:
        return ATTACHMENT_TYPE_NAMES[attachment_type]
    if plate_type is not None or attachment_type is not None:
        return "Unknown accessory"
    return None


def _printer_state_name(state: int | None, step: int | None = None) -> str | None:
    if state is None:
        return None
    if step is not None and (state, step) in PRINTER_STEP_STATE_NAMES:
        return PRINTER_STEP_STATE_NAMES[(state, step)]
    return PRINTER_STATE_NAMES.get(state, f"Unknown state {state}")


def _design_preparation_name(step: int | None) -> str | None:
    if step == 0:
        return "Measuring height"
    if step == 1:
        return "Taking snapshots"
    if step is not None:
        return "Preparing design"
    return None
