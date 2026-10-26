"""Tests for partition selection and current cloud alarm interpretation."""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from pyvisonicalarm.alarm import AlarmSystem, PanelState
from pyvisonicalarm.classes import Alarm, PanelInfo, Status
from pyvisonicalarm.core import API
from pyvisonicalarm.devices import PanelDevice

pytestmark = pytest.mark.asyncio


async def fetch_panel_state(
    status: Status, panel_info: PanelInfo | None, alarms: list[Alarm]
) -> PanelState:
    system = AlarmSystem(MagicMock(spec=API))
    with (
        patch.object(system, "get_status", return_value=status),
        patch.object(system, "get_panel_info", return_value=panel_info),
        patch.object(system, "get_devices", return_value=[]),
        patch.object(system, "get_alarms", return_value=alarms),
    ):
        return await system.get_panel_state()


@pytest.mark.parametrize(
    ("panel_info", "expected_ids"),
    [
        pytest.param(None, (1, 3, 5), id="unknown-partition-configuration"),
        pytest.param(PanelInfo({}), (1,), id="missing-partition-configuration"),
        pytest.param(PanelInfo({"partitions": []}), (1,), id="empty-configuration"),
        pytest.param(
            PanelInfo({"partitions": [{"id": 1}]}), (1,), id="single-partition"
        ),
        pytest.param(
            PanelInfo(
                {"partitions": [{"id": 1, "active": False}, {"id": 5, "active": True}]}
            ),
            (5,),
            id="sparse-active-partition",
        ),
        pytest.param(
            PanelInfo({"partitions": [{"id": 1}, {"id": 5}]}),
            (),
            id="no-active-partitions",
        ),
    ],
)
async def test_partition_selection(
    panel_info: PanelInfo | None, expected_ids: tuple[int, ...]
) -> None:
    status = Status(
        {
            "connected": True,
            "partitions": [
                {"id": 1, "state": "DISARM", "status": "", "ready": False},
                {"id": 3, "state": "HOME", "status": "", "ready": True},
                {"id": 5, "state": "AWAY", "status": "EXIT", "ready": None},
            ],
        }
    )

    summary = await fetch_panel_state(status, panel_info, [])

    assert tuple(part.id for part in summary.partitions) == expected_ids
    assert not summary.alarm_active
    assert status.partitions[2].state == "AWAY"
    assert status.partitions[2].status == "EXIT"
    assert status.partitions[2].ready is None


@pytest.mark.parametrize(
    ("state", "status_value", "expected"),
    [
        pytest.param("AWAY", "", True, id="armed-away"),
        pytest.param("HOME", "", True, id="armed-home"),
        pytest.param("DISARM", "", False, id="disarmed"),
        pytest.param("AWAY", "EXIT", False, id="arming-away"),
        pytest.param("HOME", "EXIT", False, id="arming-home"),
        pytest.param("ENTRY_DELAY", "", False, id="entry-delay"),
        pytest.param("PROGRAMMING", "", False, id="programming"),
        pytest.param("ALARM", "", False, id="alarm-state"),
        pytest.param("UNKNOWN", "", False, id="unknown-state"),
        pytest.param(None, "", False, id="missing-state"),
        pytest.param("AWAY", None, False, id="missing-status"),
        pytest.param("AWAY", "UNKNOWN", False, id="unknown-status"),
    ],
)
async def test_alarm_memory(
    state: str | None, status_value: str | None, expected: bool
) -> None:
    status = Status(
        {"connected": True, "partitions": [{"state": state, "status": status_value}]}
    )

    summary = await fetch_panel_state(
        status, None, [Alarm({"alarm_type": "ALARM_IN_MEMORY"})]
    )

    assert summary.alarm_active is expected


@pytest.mark.parametrize(
    "alarm_type",
    [
        pytest.param("FIRE", id="fire"),
        pytest.param("PANIC", id="panic"),
        pytest.param("EMERGENCY", id="emergency"),
    ],
)
@pytest.mark.parametrize(
    "alarm_order",
    [pytest.param((0, 1), id="oldest-first"), pytest.param((1, 0), id="newest-first")],
)
@pytest.mark.parametrize(
    "alarm_date",
    [pytest.param("2026-10-19T10:00:00", id="dated"), pytest.param(None, id="undated")],
)
@pytest.mark.parametrize(
    ("partition_id", "expected"),
    [
        pytest.param(1, True, id="active-partition"),
        pytest.param(2, False, id="inactive-partition"),
        pytest.param(3, False, id="unrelated-partition"),
    ],
)
async def test_all_current_alarms(
    alarm_type: str,
    alarm_order: tuple[int, int],
    alarm_date: str | None,
    partition_id: int,
    expected: bool,
) -> None:
    status = Status(
        {
            "connected": True,
            "partitions": [{"id": 1, "state": "DISARM", "status": ""}, {"id": 2}],
        }
    )
    panel_info = PanelInfo(
        {"partitions": [{"id": 1, "active": True}, {"id": 2, "active": False}]}
    )
    alarms = [
        Alarm(
            {
                "alarm_type": alarm_type,
                "partitions": [partition_id],
                "datetime": alarm_date,
            }
        ),
        Alarm(
            {
                "alarm_type": "ALARM_IN_MEMORY",
                "partitions": [1],
                "datetime": "2026-10-19T10:01:00",
            }
        ),
    ]

    summary = await fetch_panel_state(
        status, panel_info, [alarms[index] for index in alarm_order]
    )

    assert summary.alarm_active is expected


@pytest.mark.parametrize(
    "alarm_type",
    [pytest.param(None, id="missing"), pytest.param("UNKNOWN", id="unknown")],
)
async def test_unrecognized_alarm_type(alarm_type: str | None) -> None:
    status = Status(
        {"connected": True, "partitions": [{"state": "AWAY", "status": ""}]}
    )

    summary = await fetch_panel_state(status, None, [Alarm({"alarm_type": alarm_type})])

    assert not summary.alarm_active


@pytest.mark.parametrize(
    ("panel_info", "expected"),
    [
        pytest.param(None, True, id="unknown-configuration"),
        pytest.param(
            PanelInfo({"partitions": [{"id": 1}]}), True, id="single-partition"
        ),
        pytest.param(
            PanelInfo(
                {"partitions": [{"id": 1, "active": True}, {"id": 2, "active": True}]}
            ),
            False,
            id="multiple-partitions",
        ),
    ],
)
async def test_alarm_without_partition_membership(
    panel_info: PanelInfo | None, expected: bool
) -> None:
    status = Status(
        {"connected": True, "partitions": [{"id": 1, "state": "DISARM", "status": ""}]}
    )

    summary = await fetch_panel_state(
        status, panel_info, [Alarm({"alarm_type": "FIRE"})]
    )

    assert summary.alarm_active is expected


async def test_no_status_partitions() -> None:
    summary = await fetch_panel_state(
        Status({"connected": True}), None, [Alarm({"alarm_type": "FIRE"})]
    )

    assert summary.partitions == ()
    assert not summary.alarm_active


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        pytest.param(None, False, id="absent-status"),
        pytest.param(Status({}), False, id="missing-connected"),
        pytest.param(Status({"connected": None}), False, id="null-connected"),
        pytest.param(Status({"connected": False}), False, id="disconnected"),
        pytest.param(Status({"connected": True}), True, id="connected"),
    ],
)
async def test_connected_flag(status: Status | None, expected: bool) -> None:
    system = AlarmSystem(MagicMock(spec=API))
    with (
        patch.object(system, "get_status", return_value=status),
        patch.object(system, "get_panel_info", return_value=None),
        patch.object(system, "get_devices", return_value=[]),
        patch.object(system, "get_alarms", return_value=[]),
    ):
        state = await system.get_panel_state()

    assert state.connected is expected
    assert state.status is status
    assert state.partitions == ()
    assert state.devices == ()
    assert not state.alarm_active


async def test_disconnected_skips_remaining_requests() -> None:
    system = AlarmSystem(MagicMock(spec=API))
    with (
        patch.object(system, "get_status", return_value=Status({"connected": False})),
        patch.object(system, "get_panel_info") as info,
        patch.object(system, "get_devices") as devices,
        patch.object(system, "get_alarms") as alarms,
    ):
        state = await system.get_panel_state()

    assert not state.connected
    info.assert_not_awaited()
    devices.assert_not_awaited()
    alarms.assert_not_awaited()


async def test_panel_state_fetches_data_in_order() -> None:
    api = AsyncMock(spec=API)
    api.get_status.return_value = {
        "connected": True,
        "partitions": [{"id": 1, "status": "", "state": "DISARM", "ready": True}],
    }
    api.get_panel_info.return_value = {"partitions": [{"id": 1}]}
    api.get_devices.return_value = [
        {"device_type": "CONTROL_PANEL", "subtype": "", "id": 1}
    ]
    api.get_alarms.return_value = [{"alarm_type": "FIRE"}]
    system = AlarmSystem(api)

    state = await system.get_panel_state()

    assert api.mock_calls == [
        call.get_status(),
        call.get_panel_info(),
        call.get_devices(),
        call.get_alarms(),
    ]
    assert state.connected
    assert state.status is not None
    assert state.status.connected is True
    assert tuple(part.id for part in state.partitions) == (1,)
    assert state.partitions[0].state == "DISARM"
    assert len(state.devices) == 1
    assert isinstance(state.devices[0], PanelDevice)
    assert state.alarm_active
