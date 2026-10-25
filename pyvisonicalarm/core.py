"""API for Visonic Alarm Core cloud connection."""

import asyncio
import json
import logging
from typing import Any

import aiohttp
from aiohttp import ClientTimeout

from .const import (
    DEFAULT_INSTALLER_VERSION,
    DEFAULT_REST_VERSION,
    TEXT_STATUS_AWAY,
    TEXT_STATUS_DISARM,
    TEXT_STATUS_HOME,
    JsonData,
    RequestType,
    VisonicURL,
)
from .exceptions import (
    AlreadyGrantedError,
    AlreadyLinkedError,
    AppIDRequiredError,
    BadRequestPanelIsArmedError,
    ConnectionTimeoutError,
    EmailRequiredError,
    InternalServerError,
    InvalidUserCodeError,
    LoginAttemptsLimitReachedError,
    LoginTemporaryBlockedError,
    NewPasswordStrengthError,
    NotAllowedError,
    NotFoundError,
    NotSupportedError,
    PanelNotConnectedError,
    PanelSerialIncorrectError,
    PanelSerialRequiredError,
    PasswordRequiredError,
    ResetPasswordCodeIncorrectError,
    SessionTokenError,
    UnauthorizedError,
    UndefinedBadRequestError,
    UndefinedForbiddenError,
    UnsupportedRestAPIVersionError,
    UserAuthRequiredError,
    UserCodeIncorrectError,
    UserCodeRequiredError,
    WrongPanelSerialOrMasterUserCodeError,
    WrongUsernameOrPasswordError,
)

_LOGGER = logging.getLogger(__name__)

APP_TYPE = "com.visonic.powermaxapp"
USER_AGENT = "Dart/2.10 (dart:io)"

class API:
    """Class used for communication with the Visonic API."""

    def __init__(self, session: aiohttp.ClientSession, hostname: str, app_id: str, timeout: int = 8) -> None:
        """Initialise the Async API class."""
        self._timeout: int = timeout
        self._session: aiohttp.ClientSession = session
        self._hostname: str = hostname.rstrip("/")
        self._app_id: str = app_id
        self._user_token: str | None = None
        self._session_token: str | None = None
        self._rest_version: str = DEFAULT_REST_VERSION
        self._installer_version: str = DEFAULT_INSTALLER_VERSION
        self.user_code: str = ""

    async def close_session(self) -> None:
        """Close the session."""
        await self._session.close()

#    def _require_session(self):
#        if not self._session_token:
#            raise SessionTokenError

    def _decode_json(self, body_bytes: bytes) -> JsonData:
        result = json.loads(body_bytes.decode("utf-8"))
        if result is None:
            return {}
        if isinstance(result, (dict, list)):
            return result
        raise ValueError(f"Unexpected JSON type: {type(result).__name__}")

    async def _send_request_url(self, url: str,
                             data: dict[str, Any] | None = None,
                             params: dict[str, Any] | None = None,
                             request_type: RequestType = RequestType.GET,
                             with_user: bool = True, with_session: bool = True
    ) -> JsonData:
        headers: dict[str, str] = {
            "Host": self._hostname,
            "Connection": "keep-alive",
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
        }

        if request_type == RequestType.POST and data is not None:
            headers["Content-Type"] = "application/json"
        if with_user and self._user_token:
            headers["User-Token"] = self._user_token
        if with_session and self._session_token:
            headers["Session-Token"] = self._session_token

        try:
            # Use a timeout context manager for the request
            async with self._session.request(method=request_type, url=url, headers=headers, params=params, json=data, timeout=ClientTimeout(total=self._timeout)) as resp:

                # Await the response body immediately so we can parse it in catch blocks
                body_bytes = await resp.read()
                match resp.status:
                    case 200:
                        return self._decode_json(body_bytes)
                    case 400:
                        self._raise_on_bad_request(body_bytes)
                    case 401:
                        self._raise_on_unauthorized(body_bytes)
                    case 403:
                        self._raise_on_forbidden(body_bytes)
                    case 500:
                        self._raise_on_internal_server_error()
                    case 404:
                        raise NotFoundError
                    case 420:
                        # 'LoginTemporaryBlocked'
                        error_data: JsonData = self._decode_json(body_bytes) if body_bytes else {}
                        seconds = -1
                        if isinstance(error_data, dict):
                            seconds = error_data.get('extras', [{}])[0].get('value', '??')
                        raise LoginTemporaryBlockedError(
                            f"Login temporarily blocked. ({seconds} seconds remaining)."
                        )
                    case 440:
                        raise SessionTokenError
                    case 442:
                        raise LoginAttemptsLimitReachedError("Login attempts limit reached.")
                    case 444:
                        raise InvalidUserCodeError("Wrong user code.")
                    case _:
                        error_data_again: JsonData = self._decode_json(body_bytes) if body_bytes else {}
                        if isinstance(error_data_again, dict):
                            _LOGGER.error("Unhandled HTTP Error %s: %s", resp.status, error_data_again)
                        resp.raise_for_status()

        except asyncio.TimeoutError as exc:  # noqa: UP041
            raise ConnectionTimeoutError(
                f"Connection to '{self._hostname}' timed out after {self._timeout} seconds."
            ) from exc
        except aiohttp.ClientError as exc:
            # Catch-all for aiohttp connection issues
            raise ConnectionTimeoutError(f"Network error: {exc!s}") from exc

        raise NotSupportedError

    async def get_version_info(self) -> JsonData:
        """Find out which REST API versions are supported."""
        # The one function that does not incorporate self._rest_version in the URL
        url = f"https://{self._hostname}/rest_api/version"
        return await self._send_request_url(url, with_session=False, with_user=False)

    async def do_testing(self, panel_serial: str) -> JsonData:
        """do_testing."""
        #return await self._send_request("devices")
        url = f"https://{self._hostname}/rest_api/installer/{self._installer_version}/groups"
        return await self._send_request_url(url, with_session=True, with_user=True)

    async def _send_request(self, req: str,
                             data: dict[str, Any] | None = None,
                             params: dict[str, Any] | None = None,
                             request_type: RequestType = RequestType.GET,
                             with_user: bool = True, with_session: bool = True
    ) -> JsonData:
        """Send an async GET or POST request to the server."""
        url = f"https://{self._hostname}/rest_api/{self._rest_version}/{req}"
        return await self._send_request_url(
            url,
            data=data,
            params=params,
            request_type=request_type,
            with_user=with_user,
            with_session=with_session
        )

    def _parse_error(self, body: bytes) -> JsonData:
        """Helper to parse JSON error bodies."""
        try:
            return self._decode_json(body)
        except (ValueError, AttributeError):
            return {"error": 0, "error_message": "Unknown error"}

    def _raise_on_bad_request(self, error: bytes) -> None:
        """Raise an exception when the API returns a bad request."""
        api = self._parse_error(error)

        if isinstance(api, dict):
            if api["error"] == 10001:  # BadRequestParams
                for pair in api.get("extras", []):
                    if pair["value"] == "incorrect":
                        if pair["key"] == "panel_serial":
                            raise PanelSerialIncorrectError
                        if pair["key"] == "reset_password_code":
                            raise ResetPasswordCodeIncorrectError
                    if pair["value"] == "required":
                        if pair["key"] == "panel_serial":
                            raise PanelSerialRequiredError
                        if pair["key"] == "email":
                            raise EmailRequiredError
                        if pair["key"] == "password":
                            raise PasswordRequiredError
                        if pair["key"] == "app_id":
                            raise AppIDRequiredError
                        if pair["key"] == "user_code":
                            raise UserCodeRequiredError
                        if pair["key"] == "new_password":
                            raise PasswordRequiredError
                    if pair["value"] == "already_granted":
                        raise AlreadyGrantedError
                    if pair["value"] == "already_linked":
                        raise AlreadyLinkedError
                    if pair["key"] == "new_password":
                        raise NewPasswordStrengthError
            elif api["error"] == 10004:  # WrongCombination
                for pair in api.get("extras", []):
                    if pair["value"] == "wrong_combination":
                        if pair["key"] == "email" or pair["key"] == "password":
                            raise WrongUsernameOrPasswordError
                        if pair["key"] == "panel_serial" or pair["key"] == "master_user_code":
                            raise WrongPanelSerialOrMasterUserCodeError
            elif api["error"] == 10039:  # Cannot complete command as panel is armed (usually from a bypass sensor command)
                raise BadRequestPanelIsArmedError
            elif api["error"] == 10021:  # WrongUserCode
                raise UserCodeIncorrectError
            elif api["error"] == 400 and api["error_reason_code"] == "PanelNotConnected":
                raise PanelNotConnectedError

        # Raise a generic error when the library has no
        # specific exception implemented yet.
        raise UndefinedBadRequestError(str(api))

    def _raise_on_forbidden(self, error: bytes) -> None:
        """Raise an exception when the API returns a forbidden error."""
        api: JsonData = self._decode_json(error)

        if isinstance(api, dict):
            if api["error"] == 10010:  # NotAllowed
                raise NotAllowedError
            if api["error"] == 10002:  # UserAuthRequired
                raise UserAuthRequiredError

        # Raise a generic error when the library has no
        # specific exception implemented yet.
        raise UndefinedForbiddenError(str(api))

    def _raise_on_unauthorized(self, error: bytes) -> None:
        """Raise an exception when the API returns a unauthorized error."""
        api = self._decode_json(error)
        # Raise an exception when we are not authorized to access the endpoint
        raise UnauthorizedError(str(api))

    def _raise_on_internal_server_error(self) -> None:
        """Raise an exception when the API returns a unauthorized error."""
        # Raise an exception when we are not authorized to access the endpoint
        raise InternalServerError


    ######################
    # Public API methods #
    ######################

    async def authenticate_user(self, email: str, password: str) -> bool:
        """Stage 1: Authenticate user to get User-Token."""
        data = {
            "email": email,
            "password": password,
            "app_id": self._app_id
        }

        res: JsonData = await self._send_request("auth", data=data, request_type=RequestType.POST, with_user=False, with_session=False)
        if res and isinstance(res, dict) and "user_token" in res:
            token = res["user_token"]
            if not isinstance(token, str):
                raise ValueError("Expected a string user token")
            self._user_token = token
            return True
        return False

    async def panel_login(self, panel_serial: str, user_code: str) -> bool:
        """Stage 2: Link to specific panel to get Session-Token."""
        self.user_code = user_code
        data = {
            "user_code": user_code,
            "app_type": APP_TYPE,
            "app_id": self._app_id,
            "panel_serial": panel_serial
        }

        # User-Token is required for this call
        res: JsonData = await self._send_request("panel/login", data=data, request_type=RequestType.POST, with_user=True, with_session=False)
        if res and isinstance(res, dict) and "session_token" in res:
            token = res["session_token"]
            if not isinstance(token, str):
                raise ValueError("Expected a string session token")
            self._session_token = token
            return True
        return False

    async def panel_logout(self) -> bool:
        """Explicitly logout from the panel to free up a session slot."""
        if not self._session_token:
            return True
        try:
            # Most Visonic APIs use a DELETE or POST to /panel/logout
            # If VisonicURL.LOGOUT isn't in your constants, it's usually 'panel/logout'
            await self._send_request("panel/logout", request_type=RequestType.POST)
            self._session_token = None
        except (UnauthorizedError, SessionTokenError, ConnectionTimeoutError, aiohttp.ClientError) as exc:
            _LOGGER.debug("Logout failed: %s", exc)
            return False
        return True

    async def set_rest_version(self, version: str = "latest") -> None:
        """Set the rest api version.

        Fetch the supported versions from the API server and if "latest" then automatically
        configure the library to use the latest version supported by the server,
        otherwise set the version by the version parameter.
        """
        rv = await self.get_version_info()
        if not rv or not isinstance(rv, dict) or "rest_versions" not in rv:
            raise UnsupportedRestAPIVersionError("Could not fetch REST versions")

        iv = rv.get('installer_versions')
        if iv is not None and isinstance(iv, list):
            installer_versions: list[str] = iv
            installer_versions.sort(key=float)
            if len(installer_versions) > 0 and version == "latest":
                self._installer_version = installer_versions[-1]

        rest_versions: list[str] = rv['rest_versions']
        rest_versions.sort(key=float)
        if len(rest_versions) > 0 and version == "latest":
            self._rest_version = rest_versions[-1]
        elif version in rest_versions:
            self._rest_version = version
        else:
            raise UnsupportedRestAPIVersionError(f'Rest API version {version} is not supported by server.')

    @property
    def session_token(self) -> str | None:
        """Property to keep track of the session token."""
        return self._session_token

    @property
    def hostname(self) -> str:
        """Property to keep track of the API servers hostname."""
        return self._hostname

    @property
    def user_token(self) -> str | None:
        """Property to keep track of the user token being assigned during authentication."""
        return self._user_token

    @property
    def app_id(self) -> str:
        """Property to keep track of the user id (UUID) being used."""
        return self._app_id

    async def restore_session(self, user_token: str, session_token: str, uuid_key: str) -> None:
        """Bypass login by injecting saved tokens."""
        self._user_token = user_token
        self._session_token = session_token
        self._app_id = uuid_key

    async def get_status(self) -> JsonData:
        """Fetch the current state (polling-friendly)."""
        return await self._send_request("status", request_type=RequestType.GET, with_user=True, with_session=True)

    async def is_logged_in(self) -> bool:
        """Check if the session token is still valid."""
        if not self._session_token:
            return False

        try:
            # If get_status succeeds (returns a dict), we are logged in
            await self.get_status()
        except (UnauthorizedError, SessionTokenError):
            # These indicate the token is expired or rejected
            return False
        except (ConnectionTimeoutError, aiohttp.ClientError) as err:
            # For other errors (like timeouts), you might want to log it
            # but usually, we only return False if the AUTH specifically failed
            _LOGGER.debug("is_logged_in check failed due to connection: %s", err)
            return False
        return True

    async def access_grant(self, user_id: int, email: str) -> JsonData:
        """Grant a user access to the alarm panel via the API."""
        user_data = {"user": user_id, "email": email}
        return await self._send_request(VisonicURL.ACCESS_GRANT, data=user_data, request_type=RequestType.POST)

    async def access_revoke(self, user_id: int) -> JsonData:
        """Revoke access to the alarm panel via the API for a user."""
        user_data = {"user": user_id}
        return await self._send_request(VisonicURL.ACCESS_REVOKE, data=user_data, request_type=RequestType.POST)

    async def activate_siren(self, mode: str = "trigger") -> JsonData:
        """Activate the siren (sound the alarm)."""
        siren_data: dict[str, Any] = {"mode": mode}
        return await self._send_request(
            VisonicURL.ACTIVATE_SIREN,
            data=siren_data,
            request_type=RequestType.POST,
        )

    async def disable_siren(self, mode: str) -> JsonData:
        """Disable the siren (mute the alarm)."""
        siren_data: dict[str, Any] = {"mode": mode}
        return await self._send_request(
            VisonicURL.DISABLE_SIREN,
            data=siren_data,
            request_type=RequestType.POST,
        )

    async def get_alarms(self) -> JsonData:
        """Get the current alarms."""
        return await self._send_request(VisonicURL.ALARMS)

    async def get_alerts(self) -> JsonData:
        """Get the current alerts."""
        return await self._send_request(VisonicURL.ALERTS)

    async def get_cameras(self) -> JsonData:
        """Get the cameras in the system."""
        return await self._send_request(VisonicURL.CAMERAS)

    async def get_devices(self) -> JsonData:
        """Get all device specific information."""
        return await self._send_request(VisonicURL.DEVICES)

    async def get_email_notifications(self) -> JsonData:
        """Get settings for the email notifications."""
        return await self._send_request(VisonicURL.NOTIFICATIONS_EMAIL)

    async def get_events(self) -> JsonData:
        """Get the alarm panel events."""
        return await self._send_request(VisonicURL.EVENTS)

    async def get_feature_set(self) -> JsonData:
        """Get the alarm panel feature set."""
        return await self._send_request(VisonicURL.FEATURE_SET)

    async def get_locations(self) -> JsonData:
        """Get all locations in the alarm system."""
        return await self._send_request(VisonicURL.LOCATIONS)

    async def get_panel_access_info(self, panel_serial: str) -> JsonData:
        """get_panel_access_info."""
        params = {
            "app_type": self._app_id,
            "panel_web_name": panel_serial
        }
        return await self._send_request(VisonicURL.PANEL_ACCESS_INFO, params=params, request_type=RequestType.GET, with_session=False)

    async def get_panel_info(self) -> JsonData:
        """The general panel information is only supported in version 4.0."""
        return await self._send_request(VisonicURL.PANEL_INFO)

    async def get_panels(self) -> list[dict[str, Any]]:
        """Get a list of panels."""
        dt: JsonData = await self._send_request(VisonicURL.PANELS, with_session = False)
        if isinstance(dt, list):
            if any(not isinstance(panel, dict) for panel in dt):
                raise ValueError("Expected a list of panels")
            return [panel for panel in dt if isinstance(panel, dict)]
        return []

    async def get_preview_image(self, image_path: str)-> JsonData | None:
        """Get preview image for camera."""
        if image_path:
            return await self._send_request(image_path.replace("/rest_api", ""))
        return None

    async def get_process_status(self, process_token: str) -> JsonData:
        """Get the current status of a process running on API server."""
        return await self._send_request(VisonicURL.PROCESS_STATUS.format(process_token))

    async def get_smart_devices(self) -> JsonData:
        """Get a list of smart devices."""
        return await self._send_request(VisonicURL.SMART_DEVICES)

    async def get_smart_devices_settings(self) -> JsonData:
        """Get a list of smart devices settings."""
        return await self._send_request(VisonicURL.SMART_DEVICES_SETTINGS)

    async def get_troubles(self) -> JsonData:
        """Get the current troubles."""
        return await self._send_request(VisonicURL.TROUBLES)

    async def get_auto_devices(self) -> JsonData:
        """Get the current automation devices."""
        return await self._send_request(VisonicURL.HOME_AUTOMATION_DEVICES)

    async def get_users(self) -> JsonData | None:
        """Get information about the active users.

        Note: Only master users can see the active_user_ids!
        """
        return await self._send_request(VisonicURL.USERS)

    async def get_wakeup_sms(self) -> JsonData:
        """Get the settings needed to wake up the alarm panel via SMS."""
        return await self._send_request(VisonicURL.WAKEUP_SMS)

    async def panel_add(self, alias: str, panel_serial: str, access_proof: str | None, master_user_code: str) -> JsonData:
        """Add a new alarm panel to the user account. A master user code is required."""
        if access_proof is None:
            panel_data = {
                "alias": alias,
                "panel_serial": panel_serial,
                "master_user_code": master_user_code,
            }
        else:
            panel_data = {
                "alias": alias,
                "panel_serial": panel_serial,
                "access_proof": access_proof,
                "master_user_code": master_user_code,
            }
        return await self._send_request(VisonicURL.PANEL_ADD, data=panel_data, request_type=RequestType.POST)

    async def panel_rename(self, alias: str, panel_serial: str) -> JsonData:
        """Rename an alarm panel."""
        panel_data = {
            "panel_serial": panel_serial,
            "alias": alias,
        }
        return await self._send_request(VisonicURL.PANEL_RENAME, data=panel_data, request_type=RequestType.POST)

    async def panel_unlink(self, panel_serial: str, password: str, app_id: str) -> JsonData:
        """Unlink an alarm panel from the user account."""
        panel_data = {
            "panel_serial": panel_serial,
            "password": password,
            "app_id": app_id,
        }
        return await self._send_request(VisonicURL.PANEL_UNLINK, data=panel_data, request_type=RequestType.POST)

    async def password_reset(self, email: str) -> JsonData:
        """Request a password reset email. An email will be sent to the email address provided."""
        reset_data = {"email": email}
        return await self._send_request(
            VisonicURL.PASSWORD_RESET,
            data=reset_data,
            request_type=RequestType.POST,
        )

    async def password_reset_complete(self, reset_password_code: str, new_password: str) -> JsonData:
        """Complete the password reset request."""
        reset_data = {
            "reset_password_code": reset_password_code,
            "new_password": new_password,
            "app_id": self._app_id,
        }
        return await self._send_request(
            VisonicURL.PASSWORD_RESET_COMPLETE,
            data=reset_data,
            request_type=RequestType.POST,
        )

    async def set_email_notifications(self, mode: str) -> JsonData:
        """Set settings for the email notifications."""
        notification_data = {"mode": mode}
        return await self._send_request(
            VisonicURL.NOTIFICATIONS_EMAIL,
            data=notification_data,
            request_type=RequestType.POST,
        )

    async def set_bypass_zone(self, zone: int, set_enabled: bool) -> JsonData:
        """Enable or disable bypass mode for a zone."""
        bypass_data: dict[str, Any] = {"zone": zone, "set": set_enabled}
        return await self._send_request(
            VisonicURL.SET_BYPASS_ZONE,
            data=bypass_data,
            request_type=RequestType.POST,
        )

    async def make_video(self, device: int) -> JsonData:
        """Make a video."""
        data = {
            "camera_id": 1,
        }

        return await self._send_request(
            VisonicURL.MAKE_VIDEO,
            data=data,
            request_type=RequestType.POST,
        )

    async def set_name(self, object_class: str, device_id: int, name: str) -> JsonData:
        """Set the name of any type of object in the alarm system."""
        name_data: dict[str, Any] = {"class": object_class, "id": device_id, "name": name}
        return await self._send_request(VisonicURL.SET_NAME, data=name_data, request_type=RequestType.POST)

    async def set_user_code(self, user_code: str, user_id: int) -> JsonData:
        """Set the code of a user in the alarm system."""
        code_data = {"user_code": user_code, "user_id": user_id}
        return await self._send_request(VisonicURL.SET_USER_CODE, data=code_data, request_type=RequestType.POST)

    async def _set_arm_state(self, partition: int, state: str, user_code: str | None) -> JsonData:
        uc = self.user_code if user_code is None or len(user_code) != 4 else user_code
        data: dict[str, Any] = {"partition": partition, "state": state, "user_code": uc}
        return await self._send_request(VisonicURL.SET_STATE, data=data, request_type=RequestType.POST)

    async def arm_home(self, partition: int, user_code : str | None = None) -> JsonData:
        """Arm in Home mode."""
        return await self._set_arm_state(partition, TEXT_STATUS_HOME, user_code)

    async def arm_away(self, partition: int, user_code : str | None = None) -> JsonData:
        """Arm in Away mode."""
        return await self._set_arm_state(partition, TEXT_STATUS_AWAY, user_code)

    async def arm_home_instant(self, partition: int, user_code : str | None = None) -> JsonData:
        """Arm in Home Instant mode."""
        return await self._set_arm_state(partition, TEXT_STATUS_HOME, user_code)  # Cannot set instant

    async def arm_away_instant(self, partition: int, user_code : str | None = None) -> JsonData:
        """Arm in Away Instant mode."""
        return await self._set_arm_state(partition, TEXT_STATUS_AWAY, user_code)  # Cannot set instant

    async def disarm(self, partition: int, user_code : str | None = None) -> JsonData:
        """Disarm the alarm system."""
        return await self._set_arm_state(partition, TEXT_STATUS_DISARM, user_code)

    async def send_get(self, url: str, data: dict[str, Any] | None) -> JsonData:
        """Send a custom GET request."""
        return await self._send_request_url(url=url, data=data)

    async def send_post(self, url: str, data: dict[str, Any] | None) -> JsonData:
        """Send a custom POST request."""
        return await self._send_request_url(url=url, data=data, request_type=RequestType.POST)
