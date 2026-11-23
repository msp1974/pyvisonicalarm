"""Tests for converting cloud subtypes to concrete device classes."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pyvisonicalarm.alarm import AlarmSystem
from pyvisonicalarm.const import SensorGroup
from pyvisonicalarm.core import API
from pyvisonicalarm.device_definitions import get_device_definition
from pyvisonicalarm.devices import (
    Device,
    FloodDevice,
    KeypadDevice,
    MotionDevice,
    RepeaterDevice,
    SmokeDevice,
    TagDevice,
)


@pytest.mark.parametrize(
    ("subtype", "device_class", "sensor_group"),
    [
        pytest.param("FLOOD", FloodDevice, SensorGroup.FLOOD, id="flood"),
        pytest.param(
            "BASIC_REPEATER", RepeaterDevice, SensorGroup.COMMS, id="repeater"
        ),
        pytest.param(
            "PROXIMITY_KEYPAD", KeypadDevice, SensorGroup.TOKEN, id="keypad"
        ),
    ],
)
async def test_get_devices_maps_supported_subtypes(
    subtype: str, device_class: type[Device], sensor_group: SensorGroup
) -> None:
    """Return typed device objects for the supported cloud subtypes."""
    api = MagicMock(spec=API)
    api.get_devices = AsyncMock(
        return_value=[
            {
                "id": 1,
                "device_number": 1,
                "device_type": "ZONE",
                "subtype": subtype,
                "state": False,
                "enrollment_id": "enrolled",
                "warnings": [],
            }
        ]
    )

    (device,) = await AlarmSystem(api).get_devices()

    assert isinstance(device, device_class)
    assert device.sensor_group is sensor_group


def test_get_device_definition_uses_subtype_then_device_type() -> None:
    """Prefer a subtype mapping and return None for unknown pairs."""
    subtype_definition = get_device_definition("ZONE", "FLOOD")
    type_definition = get_device_definition("CONTROL_PANEL", "UNSEEN")

    assert subtype_definition is not None
    assert subtype_definition.device is FloodDevice
    assert type_definition is not None
    assert get_device_definition("UNSEEN", "UNSEEN") is None


@pytest.mark.parametrize(
    ("device_type", "subtype", "expected_class"),
    [
        pytest.param("ZONE", "S_OUT_CURTAIN", MotionDevice, id="curtain"),
        pytest.param("ZONE", "S_SMOKE_AND_HEAT", SmokeDevice, id="smoke-heat"),
        pytest.param(
            "WIRELESS_COMMANDER", "PROXIMITY_KEYPAD", KeypadDevice, id="keypad"
        ),
        pytest.param("REPEATER", "BASIC_REPEATER", RepeaterDevice, id="repeater"),
        pytest.param("PROXY_TAG", "GENERIC_PROXY_TAG", TagDevice, id="proxy-tag"),
        pytest.param("WL_SIREN", "OUTDOOR", None, id="unmapped-siren"),
    ],
)
def test_issue_291_observed_pairs_have_expected_mappings(
    device_type: str, subtype: str, expected_class: type[Device] | None
) -> None:
    """Keep the issue 291 observed cloud pairs in the mapping test suite."""
    definition = get_device_definition(device_type, subtype)

    assert (definition.device if definition is not None else None) is expected_class
