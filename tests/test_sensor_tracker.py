"""Exercise cloud trigger counters across polls, gaps and sessions."""

from unittest.mock import MagicMock

import pytest

from pyvisonicalarm.alarm import AlarmSystem
from pyvisonicalarm.core import API
from pyvisonicalarm.devices import (
    CameraDevice,
    ContactDevice,
    Device,
    MotionDevice,
    SensorDevice,
    ShockDevice,
    SmokeDevice,
)
from pyvisonicalarm.sensor_tracker import SensorStateTracker


def make_sensor(
    state: object, sensor_type: type[SensorDevice] = MotionDevice, device_id: int = 1
) -> SensorDevice:
    return sensor_type(
        {"id": device_id, "enrollment_id": "enrolled-sensor", "state": state}
    )


@pytest.mark.parametrize(
    "sensor_type",
    [
        pytest.param(MotionDevice, id="motion"),
        pytest.param(CameraDevice, id="camera"),
        pytest.param(ShockDevice, id="shock"),
        pytest.param(SmokeDevice, id="smoke"),
    ],
)
@pytest.mark.parametrize(
    ("states", "expected"),
    [
        pytest.param(
            [True, True, False, True, True], [0, 0, 0, 1, 1], id="initial-active"
        ),
        pytest.param(
            [False, True, True, False, True], [0, 1, 1, 1, 2], id="rising-edges"
        ),
        pytest.param(
            [False, None, True, False, True], [0, 0, 0, 0, 1], id="unknown-gap"
        ),
        pytest.param(
            ["closed", "opened", "open", "close", "TRUE"],
            [0, 1, 1, 1, 2],
            id="normalized-states",
        ),
    ],
)
def test_trigger_counter_observations(
    sensor_type: type[SensorDevice], states: list[object], expected: list[int]
) -> None:
    tracker = SensorStateTracker()
    observed = []
    for state in states:
        sensor = make_sensor(state, sensor_type)
        tracker.update([sensor])
        observed.append(sensor.triggered)
    assert observed == expected


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"enrollment_id": ""}, id="empty-identifier"),
        pytest.param({"enrollment_id": "0"}, id="zero-identifier"),
        pytest.param({"enrollment_id": "unknown"}, id="unknown-identifier"),
        pytest.param({"enrollment_id": None}, id="missing-identifier"),
        pytest.param({"preenroll": True}, id="preenrolled"),
        pytest.param({"preenroll": "true"}, id="preenrolled-string"),
        pytest.param({"preenroll": "unknown"}, id="unknown-enrollment"),
    ],
)
def test_unenrolled_sensors_do_not_count(changes: dict[str, object]) -> None:
    tracker = SensorStateTracker()
    sensors = [
        MotionDevice(
            {"id": 1, "enrollment_id": "enrolled-sensor", "state": state, **changes}
        )
        for state in (False, True)
    ]
    for sensor in sensors:
        tracker.update([sensor])
    assert [sensor.triggered for sensor in sensors] == [0, 0]


@pytest.mark.parametrize(
    "sensor_type",
    [
        pytest.param(ContactDevice, id="contact"),
        pytest.param(SensorDevice, id="unknown-sensor"),
    ],
)
def test_sensors_without_trigger_capability_do_not_count(
    sensor_type: type[SensorDevice],
) -> None:
    tracker = SensorStateTracker()
    sensors = [make_sensor(state, sensor_type) for state in (False, True, False, True)]
    for sensor in sensors:
        tracker.update([sensor])
    assert [sensor.triggered for sensor in sensors] == [0, 0, 0, 0]


@pytest.mark.parametrize(
    "gap",
    [
        pytest.param([], id="device-disappeared"),
        pytest.param([Device({"id": 1})], id="generic-device"),
        pytest.param([MotionDevice({"id": 1, "state": False})], id="enrollment-lost"),
    ],
)
def test_gap_retains_count_without_replaying_trigger(gap: list[Device]) -> None:
    tracker = SensorStateTracker()
    tracker.update([make_sensor(False)])
    tracker.update([make_sensor(True)])
    tracker.update([make_sensor(False)])
    tracker.update(gap)
    recovered = make_sensor(True)
    tracker.update([recovered])
    assert recovered.triggered == 1
    tracker.update([make_sensor(False)])
    triggered = make_sensor(True)
    tracker.update([triggered])
    assert triggered.triggered == 2


def test_reset_baselines_retains_counts() -> None:
    tracker = SensorStateTracker()
    tracker.update([make_sensor(False)])
    tracker.update([make_sensor(True)])
    tracker.update([make_sensor(False)])
    tracker.reset_baselines()
    recovered = make_sensor(True)
    tracker.update([recovered])
    assert recovered.triggered == 1
    tracker.update([make_sensor(False)])
    triggered = make_sensor(True)
    tracker.update([triggered])
    assert triggered.triggered == 2


def test_counters_follow_device_ids_across_reordered_polls() -> None:
    tracker = SensorStateTracker()
    tracker.update([make_sensor(False, device_id=1), make_sensor(True, device_id=2)])
    first = make_sensor(True, device_id=1)
    second = make_sensor(False, device_id=2)
    tracker.update([second, first])
    assert (first.triggered, second.triggered) == (1, 0)
    first = make_sensor(True, device_id=1)
    second = make_sensor(True, device_id=2)
    tracker.update([first, second])
    assert (first.triggered, second.triggered) == (1, 1)


@pytest.mark.parametrize(
    ("pulses", "expected"),
    [
        pytest.param(99, 99, id="before-wrap"),
        pytest.param(100, 0, id="wrap"),
        pytest.param(101, 1, id="after-wrap"),
    ],
)
def test_counter_wraps_after_one_hundred_triggers(pulses: int, expected: int) -> None:
    tracker = SensorStateTracker()
    triggered = make_sensor(True)
    for _ in range(pulses):
        tracker.update([make_sensor(False)])
        triggered = make_sensor(True)
        tracker.update([triggered])
    assert triggered.triggered == expected


@pytest.mark.asyncio
async def test_alarm_system_updates_tracker_across_replaced_sessions() -> None:
    api = MagicMock(spec=API)
    api.get_devices.side_effect = [
        [
            {
                "id": 1,
                "enrollment_id": "enrolled-sensor",
                "subtype": "FLAT_PIR_SMART",
                "device_type": "SENSOR",
                "warnings": [],
            }
        ],
        [
            {
                "id": 1,
                "enrollment_id": "enrolled-sensor",
                "subtype": "FLAT_PIR_SMART",
                "device_type": "SENSOR",
                "warnings": [{"type": "OPENED"}],
            }
        ],
        [
            {
                "id": 1,
                "enrollment_id": "enrolled-sensor",
                "subtype": "FLAT_PIR_SMART",
                "device_type": "SENSOR",
                "warnings": [{"type": "OPENED"}],
            }
        ],
    ]
    tracker = SensorStateTracker()
    first = AlarmSystem(api, sensor_tracker=tracker)
    initial = await first.get_devices()
    active = await first.get_devices()
    replacement = AlarmSystem(api, sensor_tracker=tracker)
    held = await replacement.get_devices()
    assert isinstance(initial[0], MotionDevice)
    assert isinstance(active[0], MotionDevice)
    assert isinstance(held[0], MotionDevice)
    assert [initial[0].triggered, active[0].triggered, held[0].triggered] == [0, 1, 1]


@pytest.mark.asyncio
async def test_disconnected_panel_resets_observation_baselines() -> None:
    api = MagicMock(spec=API)
    api.get_status.return_value = {"connected": False}
    tracker = SensorStateTracker()
    tracker.update([make_sensor(False)])
    tracker.update([make_sensor(True)])
    tracker.update([make_sensor(False)])
    panel = AlarmSystem(api, sensor_tracker=tracker)
    assert not (await panel.get_panel_state()).connected
    recovered = make_sensor(True)
    tracker.update([recovered])
    assert recovered.triggered == 1
    api.get_devices.assert_not_called()
