"""Sensor reporting capabilities and cloud value normalization."""

from enum import StrEnum
from math import isfinite


class SensorCapability(StrEnum):
    """Reports supported by a sensor independently of current readings."""

    STATE = "state"
    TRIGGER = "trigger"
    BATTERY = "battery"
    TAMPER = "tamper"
    PROBLEM = "problem"
    TEMPERATURE = "temperature"
    ILLUMINANCE = "illuminance"


def parse_boolean(value: object) -> bool | None:
    """Normalize cloud flags without interpreting unknown strings as true."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value) if value in (0, 1) else None
    if isinstance(value, str):
        token = value.strip().lower()
        if token in ("true", "yes", "1"):
            return True
        if token in ("false", "no", "0"):
            return False
    return None


def parse_zone_state(value: object) -> bool | None:
    """Normalize the cloud's open/closed or boolean zone state."""
    if isinstance(value, str):
        token = value.strip().lower()
        if token in ("opened", "open"):
            return True
        if token in ("closed", "close"):
            return False
    return parse_boolean(value)


def parse_number(value: object) -> float | None:
    """Return a finite numeric reading, keeping absence distinct from zero."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if isfinite(value) else None
