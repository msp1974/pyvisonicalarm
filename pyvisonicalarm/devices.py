"""DeviceStrState type classes."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .classes import BaseClass, title_case
from .const import TEXT_OPENED, TEXT_UNKNOWN, SensorGroup


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
class CameraDevice(DeviceStrState):
    """Camera device class definition."""

    @property
    def vod(self) -> str:
        """Returns the current vod."""
        return self._get_nested_key_str("traits.vod", TEXT_UNKNOWN)


@dataclass
class ContactDevice(DeviceStrState):
    """Contact device class definition."""

@dataclass
class ShockDevice(DeviceStrState):
    """Contact device class definition."""

@dataclass
class MotionDevice(DeviceStrState):
    """Motion sensor device class definition."""

    @property
    def brightness(self) -> int:
        """Get brightness level."""
        return self._get_nested_key_int("traits.meteo_info.brightness.value", 0)

    @property
    def brightness_last_updated(self) -> datetime | None:
        """Get brightness last updated."""
        val = self._get_nested_key("traits.meteo_info.brightness.date", None)
        if val is None or isinstance(val, datetime):
            return val
        return None

    @property
    def temperature(self) -> float | None:
        """Get temperature."""
        val = self._get_nested_key("traits.meteo_info.temperature.value", None)
        if val is None or isinstance(val, float):
            return val
        return None

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
class SmokeDevice(DeviceStrState):
    """Smoke device class definition."""
