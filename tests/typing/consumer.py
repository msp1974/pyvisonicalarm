"""Check the types exposed to library consumers."""

from typing import assert_type

import aiohttp
from pyvisonicalarm.alarm import AlarmSystem, PanelState
from pyvisonicalarm.classes import (
    FeatureSet,
    Location,
    PanelInfo,
    Partition,
    Status,
    title_case,
)
from pyvisonicalarm.core import API
from pyvisonicalarm.devices import Device, SirenDevice


@title_case
def required(value: str, *, suffix: str = "") -> str:
    return value + suffix


@title_case
def optional(value: str | None) -> str | None:
    return value


async def check_consumer(session: aiohttp.ClientSession) -> None:
    api = API(session, "example.com", "app-id")
    alarm = AlarmSystem(api)
    assert_type(required("front door", suffix="!"), str)
    assert_type(optional(None), str | None)
    assert_type(Device({}).location, str)
    assert_type(SirenDevice({}).location, str)
    assert_type(FeatureSet({}).events_enabled, bool | None)
    assert_type(FeatureSet({}).partitions_max_count, int | None)
    assert_type(Location({}).id, int | None)
    assert_type(Location({}).name, str | None)
    assert_type(Partition({}).state, str | None)
    assert_type(PanelInfo({}).multi_partitions, bool | None)
    assert_type(await alarm.get_devices(), list[Device])
    assert_type(await alarm.arm_away(), str | None)
    assert_type(await alarm.connected, bool | None)
    assert_type(await alarm.get_rest_versions(), list[str])


async def check_panel_state(alarm: AlarmSystem) -> None:
    state = await alarm.get_panel_state()
    assert_type(state, PanelState)
    assert_type(state.status, Status | None)
    assert_type(state.connected, bool)
    assert_type(state.partitions, tuple[Partition, ...])
    assert_type(state.devices, tuple[Device, ...])
    assert_type(state.alarm_active, bool)
