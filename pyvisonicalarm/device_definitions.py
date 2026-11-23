"""Device type definitions."""

from typing import NamedTuple

from .const import SensorGroup
from .devices import (
    CameraDevice,
    ContactDevice,
    Device,
    FloodDevice,
    GenericDevice,
    GSMDevice,
    KeypadDevice,
    KeyFobDevice,
    MotionDevice,
    PanelDevice,
    PGMDevice,
    RepeaterDevice,
    ShockDevice,
    SirenDevice,
    SmokeDevice,
    TagDevice,
)


class device_type(NamedTuple):
    """Visonic Command Structure."""
    device: type[Device]
    sensor_group: SensorGroup

# The panel is a CONTROL_PANEL device and VISONIC_PANEL subtype, include in both lists to make sure
# The powerlink is a POWER_LINK in both device and subtype, include in both lists to make sure
# The pgm is a PGM device and PGM_ON_PANEL subtype, include in both lists to make sure

DEVICE_TYPES: dict[str, device_type] = {
    "CONTROL_PANEL": device_type(PanelDevice, SensorGroup.PANEL),
    "POWER_LINK": device_type(GenericDevice, SensorGroup.COMMS),
    "GSM": device_type(GSMDevice, SensorGroup.COMMS),
    "PGM": device_type(PGMDevice, SensorGroup.SWITCH),
}

DEVICE_SUBTYPES: dict[str, device_type] = {
    "VISONIC_PANEL": device_type(PanelDevice, SensorGroup.PANEL),
    "POWER_LINK": device_type(GenericDevice, SensorGroup.COMMS),
    "PGM_ON_PANEL": device_type(PGMDevice, SensorGroup.SWITCH),
    "FLOOD": device_type(FloodDevice, SensorGroup.FLOOD),
    "BASIC_REPEATER": device_type(RepeaterDevice, SensorGroup.COMMS),
    "PROXIMITY_KEYPAD": device_type(KeypadDevice, SensorGroup.TOKEN),
    "CONTACT": device_type(ContactDevice, SensorGroup.MAGNET),
    "CONTACT_AUX": device_type(ContactDevice, SensorGroup.MAGNET),
    "CONTACT_V": device_type(ContactDevice, SensorGroup.MAGNET),
    "MC303_VANISH": device_type(ContactDevice, SensorGroup.MAGNET),
    "MOTION_CAMERA": device_type(CameraDevice, SensorGroup.MOTION),
    "SMOKE": device_type(SmokeDevice, SensorGroup.SMOKE),
    "BASIC_KEYFOB": device_type(KeyFobDevice, SensorGroup.TOKEN),
    "KEYFOB_ARM_LED": device_type(KeyFobDevice, SensorGroup.TOKEN),
    "GENERIC_PROXY_TAG": device_type(TagDevice, SensorGroup.TOKEN),
    "FLAT_PIR_SMART": device_type(MotionDevice, SensorGroup.MOTION),
    "CURTAIN": device_type(MotionDevice, SensorGroup.MOTION),
    "S_OUT_CURTAIN": device_type(MotionDevice, SensorGroup.MOTION),
    "S_SMOKE_AND_HEAT": device_type(SmokeDevice, SensorGroup.SMOKE),
    "WL_SIREN": device_type(SirenDevice, SensorGroup.SIREN),
    "SHOCK_CONTACT_AUX_ANTIMASK": device_type(ShockDevice, SensorGroup.SHOCK),
    "HW_ZONE_CONNECTED_DIRECTLY_TO_THE_PANEL": device_type(ContactDevice, SensorGroup.WIRED),
}


def get_device_definition(
    device_type_name: str, subtype: str
) -> device_type | None:
    """Return the most specific definition for a cloud device."""
    return DEVICE_SUBTYPES.get(subtype) or DEVICE_TYPES.get(device_type_name)
