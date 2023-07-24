"""Device type definitions"""

from .devices import (
    CameraDevice,
    ContactDevice,
    GSMDevice,
    GenericDevice,
    KeyFobDevice,
    MotionDevice,
    PGMDevice,
    SmokeDevice,
    TagDevice,
)


DEVICE_TYPES = {
    "GSM": GSMDevice,
    "PGM": PGMDevice,
}

DEVICE_SUBTYPES = {
    "CONTACT": ContactDevice,
    "CONTACT_AUX": ContactDevice,
    "MC303_VANISH": ContactDevice,
    "MOTION_CAMERA": CameraDevice,
    "SMOKE": SmokeDevice,
    "BASIC_KEYFOB": KeyFobDevice,
    "KEYFOB_ARM_LED": KeyFobDevice,
    "GENERIC_PROXY_TAG": TagDevice,
    "FLAT_PIR_SMART": MotionDevice,
    "WL_SIREN": GenericDevice,
}
