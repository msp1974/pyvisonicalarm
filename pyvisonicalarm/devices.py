"""DeviceStrState type classes."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, override

from .classes import BaseClass, title_case
from .const import TEXT_OPENED, TEXT_UNKNOWN, SensorGroup
from .sensor_types import SensorCapability, parse_boolean, parse_number, parse_zone_state


@dataclass
class Device(BaseClass):
    """Base class definition of a device in the alarm system."""

    @property
    def bypass(self) -> bool | None:
        """Get if bypass enabled."""
        return self._get_nested_key_bool("traits.bypass.enabled", None)

    @property
    def sensor_group(self) -> SensorGroup:
        """Get sensor_group."""
        return SensorGroup(self._get_key_int("sensor_group", 1))

    @property
    def device_number(self) -> int:
        """Get device number."""
        return self._get_key_int("device_number")

    @property
    def device_type(self) -> str:
        """Get device type."""
        return self._get_key_str("device_type")

    @property
    def enrollment_id(self) -> str:
        """Get enrollment id."""
        return self._get_key_str("enrollment_id")

    @property
    def id(self) -> int:
        """Get device id."""
        return self._get_key_int("id")

    @property
    @title_case
    def location(self) -> str:
        """Get device location."""
        return self._get_nested_key_str("traits.location.name", TEXT_UNKNOWN)

    @property
    def name(self) -> str:
        """Get device name."""
        return self._get_key_str("name", TEXT_UNKNOWN)

    @property
    def partitions(self) -> list[int]:
        """Get device partitions."""
        val = self._data.get("partitions", [])
        if isinstance(val, list):
            return val
        return []

    @property
    def preenroll(self) -> bool:
        """Get if device in preenroll."""
        return self._get_key_bool("preenroll", False)

    @property
    def removable(self) -> bool:
        """Get if device removeable."""
        return self._get_key_bool("removable", False)

    @property
    def renamable(self) -> bool:
        """Get if device renameable."""
        return self._get_key_bool("renamable", False)

    @property
    def soak(self) -> bool | None:
        """Get if device part of soak test."""
        return self._get_nested_key_bool("traits.soak.enabled", False)

    @property
    def subtype(self) -> str:
        """Get device subtype."""
        return self._get_key_str("subtype", TEXT_UNKNOWN)

    @property
    def warnings(self) -> dict[str, Any]:
        """Get device warnings."""
        val = self._data.get("warnings", {})
        if isinstance(val, dict):
            return val
        return {}

    @property
    def zone_type_name(self) -> str:
        """Get device zone type."""
        return self._get_key_str("zone_type", TEXT_UNKNOWN)

    @property
    def low_battery(self) -> str:
        """Get device zone type."""
        return self._get_key_str("low_battery", TEXT_UNKNOWN)

    @property
    def trouble(self) -> str:
        """Get device zone type."""
        return self._get_key_str("trouble", TEXT_UNKNOWN)

    @property
    def tamper(self) -> str:
        """Get device zone type."""
        return self._get_key_str("tamper", TEXT_UNKNOWN)

@dataclass
class DeviceStrState(Device):
    """DeviceStrState with string state."""

    @property
    def state(self) -> str:
        """Returns the current state of the contact."""
        return self._get_key_str("state", TEXT_UNKNOWN)

@dataclass
class SensorDevice(DeviceStrState):
    """A zone sensor with normalized readings and reporting capabilities."""

    triggered: int = field(default=0, init=False)
    _model: ClassVar[str] = "Unknown"
    _sensor_type: ClassVar[SensorGroup] = SensorGroup.UNKNOWN
    _capabilities: ClassVar[frozenset[SensorCapability]] = frozenset({
        SensorCapability.TAMPER, SensorCapability.PROBLEM,
    })

    @property
    def model(self) -> str:
        """Return the model category identified by the cloud device class."""
        return self._model

    @property
    def sensor_type(self) -> SensorGroup:
        """Return the sensor's physical category."""
        return self._sensor_type

    @property
    def capabilities(self) -> frozenset[SensorCapability]:
        """Return reporting supported by this sensor."""
        return self._capabilities

    @property
    def enrolled(self) -> bool:
        """Require completed enrollment and a nonempty enrollment identifier."""
        identifier = self._data.get("enrollment_id")
        return (
            parse_boolean(self._data.get("preenroll", False)) is False
            and isinstance(identifier, str)
            and identifier.strip().lower() not in ("", "0", "none", "unknown")
        )

    @property
    def is_open(self) -> bool | None:
        """Return the current zone state, or None when unknown."""
        return parse_zone_state(self._data.get("state"))

    @property
    def low_battery_active(self) -> bool | None:
        """Return the normalized low-battery flag."""
        return parse_boolean(self._data.get("low_battery"))

    @property
    def tamper_active(self) -> bool | None:
        """Return the normalized tamper flag."""
        return parse_boolean(self._data.get("tamper"))

    @property
    def bypassed(self) -> bool | None:
        """Return the normalized bypass flag."""
        return parse_boolean(self._get_nested_key("traits.bypass.enabled"))

    @property
    def trouble_status(self) -> str | None:
        """Distinguish explicitly clear trouble from unavailable trouble data."""
        if "trouble" not in self._data:
            return None
        value = self._data["trouble"]
        if value is None:
            return "none"
        if isinstance(value, str):
            token = value.strip().lower()
            return token if token not in ("", "unknown") else None
        return None

    @property
    def temperature(self) -> float | None:
        """Return temperature when reported by this sensor."""
        return None

    @property
    def lux(self) -> float | None:
        """Return illuminance when reported by this sensor."""
        return None


@dataclass
class SirenDevice(DeviceStrState):
    """Siren device class definition."""

    @property
    def bypass(self) -> bool | None:
        """Get if bypass enabled."""
        return self._get_key_bool("bypass", False)
        #return self._get_nested_key_bool("bypass", None)

    @property
    @title_case
    def location(self) -> str:
        """Get device location."""
        return self._get_key_str("location")
        #return self._get_nested_key("location")

    @property
    def soak(self) -> bool:
        """Get if device part of soak test."""
        return self._get_key_bool("soak", False)
        #return self._get_nested_key("soak", False)


@dataclass
class PanelDevice(DeviceStrState):
    """Alarm Panel DeviceStrState."""


@dataclass
class CameraDevice(SensorDevice):
    """Camera device class definition."""

    _model = "Camera"
    _sensor_type = SensorGroup.CAMERA
    _capabilities = SensorDevice._capabilities | {SensorCapability.BATTERY, SensorCapability.TRIGGER}

    @property
    def vod(self) -> str:
        """Returns the current vod."""
        return self._get_nested_key_str("traits.vod", TEXT_UNKNOWN)


@dataclass
class ContactDevice(SensorDevice):
    """Contact device class definition."""

    _model = "Contact"
    _sensor_type = SensorGroup.MAGNET
    _capabilities = SensorDevice._capabilities | {SensorCapability.BATTERY, SensorCapability.STATE}


    @property
    @override
    def model(self) -> str:
        """Identify a wired contact without claiming battery support."""
        return "Wired" if self.subtype == "HW_ZONE_CONNECTED_DIRECTLY_TO_THE_PANEL" else self._model

    @property
    @override
    def sensor_type(self) -> SensorGroup:
        """Return the wired or wireless contact category."""
        return SensorGroup.WIRED if self.subtype == "HW_ZONE_CONNECTED_DIRECTLY_TO_THE_PANEL" else self._sensor_type

    @property
    @override
    def capabilities(self) -> frozenset[SensorCapability]:
        """Exclude battery reporting for contacts wired directly to the panel."""
        if self.subtype == "HW_ZONE_CONNECTED_DIRECTLY_TO_THE_PANEL":
            return self._capabilities - {SensorCapability.BATTERY}
        return self._capabilities


@dataclass
class ShockDevice(SensorDevice):
    """Contact device class definition."""

    _model = "Shock"
    _sensor_type = SensorGroup.SHOCK
    _capabilities = SensorDevice._capabilities | {SensorCapability.BATTERY, SensorCapability.TRIGGER, SensorCapability.STATE}

@dataclass
class MotionDevice(SensorDevice):
    """Motion sensor device class definition."""

    _model = "Motion"
    _sensor_type = SensorGroup.MOTION
    _capabilities = SensorDevice._capabilities | {SensorCapability.BATTERY, SensorCapability.TRIGGER}


    @property
    @override
    def capabilities(self) -> frozenset[SensorCapability]:
        """Include numeric reports advertised by meteo traits, even without a value."""
        capabilities = self._capabilities
        traits = self._get_nested_key("traits.meteo_info")
        if isinstance(traits, dict):
            if "temperature" in traits:
                capabilities = capabilities | {SensorCapability.TEMPERATURE}
            if "brightness" in traits:
                capabilities = capabilities | {SensorCapability.ILLUMINANCE}
        return capabilities

    @property
    @override
    def lux(self) -> float | None:
        """Return the reported brightness without substituting zero for absence."""
        return self.brightness

    @property
    def brightness(self) -> float | None:
        """Get brightness level."""
        return parse_number(self._get_nested_key("traits.meteo_info.brightness.value"))

    @property
    def brightness_last_updated(self) -> datetime | None:
        """Get brightness last updated."""
        val = self._get_nested_key("traits.meteo_info.brightness.date", None)
        if val is None or isinstance(val, datetime):
            return val
        return None

    @property
    @override
    def temperature(self) -> float | None:
        """Get temperature."""
        return parse_number(self._get_nested_key("traits.meteo_info.temperature.value"))

    @property
    def temperature_last_updated(self) -> datetime | None:
        """Get temperature last updated."""
        val = self._get_nested_key("traits.meteo_info.temperature.date", None)
        if val is None or isinstance(val, datetime):
            return val
        return None


@dataclass
class GenericDevice(DeviceStrState):
    """Generic device class definition."""


@dataclass
class GSMDevice(DeviceStrState):
    """GSM device class definition."""

    @property
    def signal_level(self) -> str:
        """Get signal level."""
        return self._get_nested_key_str("traits.signal_level.level", "")


@dataclass
class KeyFobDevice(Device):
    """KeyFob device class definition."""

    @property
    def owner_id(self) -> int:
        """Get owner id."""
        return self._get_nested_key_int("traits.owner.id", 0)

    @property
    def owner_name(self) -> str:
        """Get owner name."""
        return self._get_nested_key_str("traits.owner.name", TEXT_UNKNOWN)

    @property
    def state(self) -> bool:
        """Returns the current state of the keyfob."""
        if self.warnings:
            return TEXT_OPENED in str(self.warnings)
        return False


@dataclass
class TagDevice(DeviceStrState):
    """Tag device class definition."""


@dataclass
class PGMDevice(DeviceStrState):
    """PGM device class definition."""

    @property
    def parent_id(self) -> int:
        """Get parent id."""
        return self._get_nested_key_int("traits.parent.id", 0)

    @property
    def parent_port(self) -> int:
        """Get parent port."""
        return self._get_nested_key_int("traits.parent.port", 0)


@dataclass
class SmokeDevice(SensorDevice):
    """Smoke device class definition."""

    _model = "Smoke"
    _sensor_type = SensorGroup.SMOKE
    _capabilities = SensorDevice._capabilities | {SensorCapability.BATTERY, SensorCapability.TRIGGER}
