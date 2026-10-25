"""Regression tests for public type contracts."""

from importlib.resources import files
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pyvisonicalarm.alarm import AlarmSystem
from pyvisonicalarm.classes import (
    Camera,
    FeatureSet,
    Location,
    PanelInfo,
    Partition,
    title_case,
)
from pyvisonicalarm.core import API
from pyvisonicalarm.device_definitions import DEVICE_TYPES
from pyvisonicalarm.devices import Device, SirenDevice
from pyvisonicalarm.exceptions import NotSupportedError


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param({}, None, id="missing"),
        pytest.param({"partitions": None}, None, id="null"),
        pytest.param({"partitions": []}, False, id="empty"),
        pytest.param({"partitions": [{"id": 1}]}, False, id="single"),
        pytest.param({"partitions": [{"id": 1}, {"id": 2}]}, True, id="multiple"),
    ],
)
def test_multi_partitions(data: dict[str, object], expected: bool | None) -> None:
    assert PanelInfo(data).multi_partitions is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="missing"),
        pytest.param(True, True, id="enabled"),
        pytest.param(False, False, id="disabled"),
        pytest.param("false", None, id="invalid"),
    ],
)
def test_feature_flags(value: object, expected: bool | None) -> None:
    assert FeatureSet({"events": {"is_enabled": value}}).events_enabled is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="missing"),
        pytest.param(3, 3, id="count"),
        pytest.param("3", None, id="invalid"),
    ],
)
def test_partition_count(value: object, expected: int | None) -> None:
    assert (
        FeatureSet({"partitions": {"max_partitions": value}}).partitions_max_count
        == expected
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="missing"),
        pytest.param("AWAY", "AWAY", id="state"),
        pytest.param(1, None, id="invalid"),
    ],
)
def test_partition_state(value: object, expected: str | None) -> None:
    assert Partition({"state": value}).state == expected


def test_location() -> None:
    location = Location({"hel_id": 1, "name": "front door", "is_editable": True})
    assert location.id == 1
    assert location.name == "Front Door"
    assert location.is_editable is True
    assert Location({}).name is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("front door", "Front Door", id="string"),
        pytest.param(None, None, id="none"),
    ],
)
def test_title_case(value: str | None, expected: str | None) -> None:
    @title_case
    def label(prefix: str, *, suffix: str | None) -> str | None:
        return prefix + suffix if suffix is not None else None

    assert label("", suffix=value) == expected


def test_device_locations() -> None:
    assert (
        Device({"traits": {"location": {"name": "front door"}}}).location
        == "Front Door"
    )
    assert SirenDevice({"location": "outside siren"}).location == "Outside Siren"
    assert Device({}).location == "Unknown"
    assert issubclass(DEVICE_TYPES["CONTROL_PANEL"].device, Device)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, [], id="missing"),
        pytest.param([], [], id="empty"),
        pytest.param([1, 2], [1, 2], id="identifiers"),
    ],
)
def test_camera_partitions(value: object, expected: list[int]) -> None:
    assert Camera({"partitions": value}).partitions == expected


def test_invalid_partitions() -> None:
    with pytest.raises(ValueError, match="list of integers"):
        Camera({"partitions": ["1"]}).partitions


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        pytest.param({"process_token": "token"}, "token", id="token"),
        pytest.param({}, None, id="missing"),
        pytest.param({"process_token": 1}, None, id="invalid"),
        pytest.param([], None, id="array"),
    ],
)
async def test_command_tokens(response: object, expected: str | None) -> None:
    api = AsyncMock(spec=API)
    api.arm_away.return_value = response
    alarm = AlarmSystem(api)
    assert await alarm.arm_away() == expected
    api.arm_away.assert_awaited_once_with(-1, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        pytest.param(
            {"rest_versions": ["9.0", "14.0"]}, ["9.0", "14.0"], id="versions"
        ),
        pytest.param({}, [], id="missing"),
        pytest.param({"rest_versions": [9]}, [], id="invalid"),
    ],
)
async def test_rest_versions(response: object, expected: list[str]) -> None:
    api = AsyncMock(spec=API)
    api.get_version_info.return_value = response
    assert await AlarmSystem(api).get_rest_versions() == expected


def test_typing_marker() -> None:
    assert files("pyvisonicalarm").joinpath("py.typed").read_bytes() == b""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        pytest.param({"user_token": "user-token"}, True, id="token"),
        pytest.param({}, False, id="missing"),
    ],
)
async def test_authentication_tokens(response: object, expected: bool) -> None:
    api = API(MagicMock(), "example.com", "app-id")
    with patch.object(api, "_send_request", new=AsyncMock(return_value=response)):
        assert await api.authenticate_user("user@example.com", "password") is expected


@pytest.mark.asyncio
async def test_invalid_authentication_token() -> None:
    api = API(MagicMock(), "example.com", "app-id")
    with patch.object(
        api, "_send_request", new=AsyncMock(return_value={"user_token": 1})
    ):
        with pytest.raises(ValueError, match="string user token"):
            await api.authenticate_user("user@example.com", "password")
    assert api.user_token is None


@pytest.mark.asyncio
async def test_panel_login_token() -> None:
    api = API(MagicMock(), "example.com", "app-id")
    with patch.object(
        api, "_send_request", new=AsyncMock(return_value={"session_token": "session"})
    ):
        assert await api.panel_login("123ABC", "1234") is True
    assert api.session_token == "session"


@pytest.mark.asyncio
async def test_invalid_panel_login_token() -> None:
    api = API(MagicMock(), "example.com", "app-id")
    with patch.object(
        api, "_send_request", new=AsyncMock(return_value={"session_token": 1})
    ):
        with pytest.raises(ValueError, match="string session token"):
            await api.panel_login("123ABC", "1234")
    assert api.session_token is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        pytest.param(
            [{"panel_serial": "123ABC"}], [{"panel_serial": "123ABC"}], id="panels"
        ),
        pytest.param({}, [], id="object"),
    ],
)
async def test_panel_list(response: object, expected: list[dict[str, str]]) -> None:
    api = API(MagicMock(), "example.com", "app-id")
    with patch.object(api, "_send_request", new=AsyncMock(return_value=response)):
        assert await api.get_panels() == expected


@pytest.mark.asyncio
async def test_invalid_panel_list() -> None:
    api = API(MagicMock(), "example.com", "app-id")
    with patch.object(api, "_send_request", new=AsyncMock(return_value=[1])):
        with pytest.raises(ValueError, match="list of panels"):
            await api.get_panels()


@pytest.mark.asyncio
async def test_unhandled_http_status() -> None:
    session = MagicMock()
    response = session.request.return_value.__aenter__.return_value
    response.raise_for_status = MagicMock()
    response.status = 202
    response.read.return_value = b"{}"
    api = API(session, "example.com", "app-id")
    with pytest.raises(NotSupportedError):
        await api.send_get("https://example.com", None)
    response.raise_for_status.assert_called_once_with()
