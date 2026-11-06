"""Exercise allowlisted cloud diagnostics without contacting a server."""

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import pytest_asyncio

from pyvisonicalarm.classes import Status
from pyvisonicalarm.core import API
from pyvisonicalarm.exceptions import ConnectionTimeoutError

LOGGER = "pyvisonicalarm.core"
PANEL_IDENT = "AB12CD"
SENSITIVE_URL = f"https://private-{PANEL_IDENT.lower()}.example.invalid/panel/{PANEL_IDENT}/operation?token=secret-session-token"
SECRETS = (
    PANEL_IDENT,
    "private-",
    "secret-user-token",
    "secret-session-token",
    "secret-password",
    "secret@example.invalid",
    "7391",
    "raw-response-marker",
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(True, True, id="connected"),
        pytest.param(False, False, id="disconnected"),
        pytest.param(None, None, id="missing"),
        pytest.param("false", None, id="string"),
        pytest.param(1, None, id="integer"),
    ],
)
def test_connection_diagnostics_preserve_unknown_flags(
    value: object, expected: bool | None
) -> None:
    status = Status(
        {
            "connected": value,
            "connected_status": {
                "bba": {"is_connected": value},
                "gprs": {"is_connected": value},
            },
        }
    )
    assert status.connection_diagnostics == {
        "panel_connected": expected,
        "broadband_connected": expected,
        "broadband_state": None,
        "cellular_connected": expected,
        "cellular_state": None,
    }


def test_absent_connection_data_remains_unknown() -> None:
    assert Status({}).connection_diagnostics == {
        "panel_connected": None,
        "broadband_connected": None,
        "broadband_state": None,
        "cellular_connected": None,
        "cellular_state": None,
    }


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        pytest.param("ONLINE", "online", id="online"),
        pytest.param("offline", "offline", id="offline"),
        pytest.param("connected", "connected", id="connected"),
        pytest.param("disconnected", "disconnected", id="disconnected"),
        pytest.param("unknown", "unknown", id="unknown"),
        pytest.param("connecting", "connecting", id="connecting"),
        pytest.param("initializing", "initializing", id="initializing"),
        pytest.param("disabled", "disabled", id="disabled"),
        pytest.param("not_connected", "not_connected", id="not-connected"),
        pytest.param(SENSITIVE_URL, "unrecognized", id="sensitive-state"),
        pytest.param({"nested": SENSITIVE_URL}, None, id="nested-value"),
        pytest.param(1, None, id="non-string"),
    ],
)
def test_transport_states_are_allowlisted(state: object, expected: str | None) -> None:
    status = Status(
        {"connected_status": {"bba": {"state": state}, "gprs": {"state": state}}}
    )
    assert status.connection_diagnostics["broadband_state"] == expected
    assert status.connection_diagnostics["cellular_state"] == expected


def test_diagnostics_exclude_embedded_identifiers_and_nested_payloads() -> None:
    status = Status(
        {
            "connected": True,
            "panel_serial": PANEL_IDENT,
            "password": "secret-password",
            "connected_status": {
                "bba": {
                    "is_connected": True,
                    "state": SENSITIVE_URL,
                    "token": "secret-session-token",
                },
                "gprs": {
                    "is_connected": False,
                    "state": "OFFLINE",
                    "nested": {"identifier": PANEL_IDENT},
                },
                "grps": {"is_connected": True, "state": "online"},
            },
        }
    )
    diagnostics = status.connection_diagnostics
    assert diagnostics == {
        "panel_connected": True,
        "broadband_connected": True,
        "broadband_state": "unrecognized",
        "cellular_connected": False,
        "cellular_state": "offline",
    }
    assert PANEL_IDENT.casefold() not in json.dumps(diagnostics).casefold()


@pytest_asyncio.fixture
async def http_client() -> tuple[API, MagicMock, MagicMock]:
    session = MagicMock(spec=aiohttp.ClientSession)
    response = MagicMock(spec=aiohttp.ClientResponse)
    response.status = 200
    response.read = AsyncMock(return_value=b"{}")
    session.request.return_value.__aenter__.return_value = response
    api = API(
        session, f"private-{PANEL_IDENT.lower()}.example.invalid", "application-id"
    )
    await api.restore_session(
        "secret-user-token", "secret-session-token", "application-id"
    )
    return api, session, response


def assert_logs_exclude_secrets(caplog: pytest.LogCaptureFixture) -> None:
    output = caplog.text.casefold()
    assert all(value.casefold() not in output for value in SECRETS)
    assert "https://" not in output


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("endpoint", "label"),
    [
        pytest.param("status", "status", id="status"),
        pytest.param("panel_info", "panel_info", id="panel-info"),
        pytest.param("devices", "devices", id="devices"),
        pytest.param("alarms", "alarms", id="alarms"),
        pytest.param("login", "login", id="login"),
        pytest.param("logout", "logout", id="logout"),
        pytest.param("authenticate", "authenticate", id="authenticate"),
        pytest.param("version", "version", id="version"),
        pytest.param(PANEL_IDENT.lower(), "other", id="identifier-endpoint"),
    ],
)
async def test_http_response_logs_only_endpoint_status_and_timing(
    http_client: tuple[API, MagicMock, MagicMock],
    caplog: pytest.LogCaptureFixture,
    endpoint: str,
    label: str,
) -> None:
    api, session, response = http_client
    payload = {
        "raw-response-marker": {
            "panel_serial": PANEL_IDENT,
            "token": "secret-session-token",
        }
    }
    response.read.return_value = json.dumps(payload).encode()
    caplog.set_level(logging.DEBUG, logger=LOGGER)
    url = f"https://private-{PANEL_IDENT.lower()}.example.invalid/panel/{PANEL_IDENT}/{endpoint}?token=secret-session-token"
    with patch(f"{LOGGER}.monotonic", side_effect=[10.0, 10.25]):
        assert (
            await api.send_post(
                url,
                {
                    "password": "secret-password",
                    "email": "secret@example.invalid",
                    "user_code": "7391",
                },
            )
            == payload
        )
    assert caplog.messages == [
        f"Cloud HTTP response endpoint={label} method=POST status=200 elapsed=0.250s"
    ]
    assert (
        session.request.call_args.kwargs["headers"]["User-Token"] == "secret-user-token"
    )
    assert (
        session.request.call_args.kwargs["headers"]["Session-Token"]
        == "secret-session-token"
    )
    assert_logs_exclude_secrets(caplog)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("stage", "phase", "status"),
    [
        pytest.param("headers", "connection_or_headers", "None", id="before-response"),
        pytest.param("body", "response_body", "200", id="reading-body"),
    ],
)
async def test_http_timeout_reports_phase_without_exception_text(
    http_client: tuple[API, MagicMock, MagicMock],
    caplog: pytest.LogCaptureFixture,
    stage: str,
    phase: str,
    status: str,
) -> None:
    api, session, response = http_client
    error = TimeoutError(SENSITIVE_URL)
    failure_point = {
        "headers": session.request.return_value.__aenter__,
        "body": response.read,
    }[stage]
    failure_point.side_effect = error
    caplog.set_level(logging.DEBUG, logger=LOGGER)
    with pytest.raises(ConnectionTimeoutError) as raised:
        await api.send_get(SENSITIVE_URL, None)
    assert raised.value.__cause__ is error
    assert f"phase={phase} status={status}" in caplog.messages[-1]
    assert "type=TimeoutError" in caplog.messages[-1]
    assert "elapsed=" in caplog.messages[-1]
    assert_logs_exclude_secrets(caplog)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "category"),
    [
        pytest.param(
            aiohttp.ClientConnectorDNSError(
                MagicMock(host="private-host", port=443, ssl=True),
                OSError(SENSITIVE_URL),
            ),
            "dns",
            id="dns",
        ),
        pytest.param(
            aiohttp.ClientSSLError(
                MagicMock(host="private-host", port=443, ssl=True),
                OSError(SENSITIVE_URL),
            ),
            "tls",
            id="tls",
        ),
        pytest.param(
            aiohttp.ClientConnectionError(SENSITIVE_URL),
            "connection_or_response_read",
            id="connection",
        ),
    ],
)
async def test_network_failures_report_category_without_exception_text(
    http_client: tuple[API, MagicMock, MagicMock],
    caplog: pytest.LogCaptureFixture,
    error: aiohttp.ClientError,
    category: str,
) -> None:
    api, session, _response = http_client
    session.request.return_value.__aenter__.side_effect = error
    caplog.set_level(logging.DEBUG, logger=LOGGER)
    with pytest.raises(ConnectionTimeoutError) as raised:
        await api.send_get(SENSITIVE_URL, None)
    assert raised.value.__cause__ is error
    assert f"category={category} status=None" in caplog.messages[-1]
    assert f"type={type(error).__name__}" in caplog.messages[-1]
    assert_logs_exclude_secrets(caplog)


@pytest.mark.asyncio
async def test_response_read_failure_retains_received_status(
    http_client: tuple[API, MagicMock, MagicMock], caplog: pytest.LogCaptureFixture
) -> None:
    api, _session, response = http_client
    error = aiohttp.ClientPayloadError(SENSITIVE_URL)
    response.read.side_effect = error
    caplog.set_level(logging.DEBUG, logger=LOGGER)
    with pytest.raises(ConnectionTimeoutError) as raised:
        await api.send_get(SENSITIVE_URL, None)
    assert raised.value.__cause__ is error
    assert "category=connection_or_response_read status=200" in caplog.messages[-1]
    assert "type=ClientPayloadError" in caplog.messages[-1]
    assert_logs_exclude_secrets(caplog)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status", [pytest.param(429, id="rate-limit"), pytest.param(503, id="unavailable")]
)
async def test_http_errors_do_not_log_response_bodies(
    http_client: tuple[API, MagicMock, MagicMock],
    caplog: pytest.LogCaptureFixture,
    status: int,
) -> None:
    api, _session, response = http_client
    response.status = status
    response.read.return_value = json.dumps(
        {"panel_serial": PANEL_IDENT, "raw-response-marker": SENSITIVE_URL}
    ).encode()
    error = aiohttp.ClientResponseError(
        MagicMock(real_url=SENSITIVE_URL), (), status=status, message=SENSITIVE_URL
    )
    response.raise_for_status.side_effect = error
    caplog.set_level(logging.DEBUG, logger=LOGGER)
    with pytest.raises(ConnectionTimeoutError) as raised:
        await api.send_get(SENSITIVE_URL, None)
    assert raised.value.__cause__ is error
    assert f"Unhandled cloud HTTP status={status} endpoint=other" in caplog.messages
    assert f"category=http_response status={status}" in caplog.messages[-1]
    assert_logs_exclude_secrets(caplog)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "request_method", "message"),
    [
        pytest.param(
            "panel_logout",
            "_send_request",
            "Logout failed (ConnectionTimeoutError)",
            id="logout",
        ),
        pytest.param(
            "is_logged_in",
            "get_status",
            "is_logged_in connection check failed (ConnectionTimeoutError)",
            id="session-check",
        ),
    ],
)
async def test_session_failure_logs_exclude_raw_exception_messages(
    http_client: tuple[API, MagicMock, MagicMock],
    caplog: pytest.LogCaptureFixture,
    method: str,
    request_method: str,
    message: str,
) -> None:
    api, _session, _response = http_client
    caplog.set_level(logging.DEBUG, logger=LOGGER)
    with patch.object(
        api,
        request_method,
        new=AsyncMock(side_effect=ConnectionTimeoutError(SENSITIVE_URL)),
    ):
        assert await getattr(api, method)() is False
    assert caplog.messages == [message]
    assert_logs_exclude_secrets(caplog)
