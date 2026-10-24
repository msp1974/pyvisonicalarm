"""Control and access to alrm info."""

from typing import Any

from .classes import (
    Alarm,
    Camera,
    Event,
    FeatureSet,
    Location,
    Panel,
    PanelInfo,
    Process,
    Status,
    Trouble,
    User,
    WakeupSMS,
)
from .const import JsonData
from .core import API
from .device_definitions import DEVICE_SUBTYPES, DEVICE_TYPES
from .devices import Device, GenericDevice


class AlarmSystem:
    """Class definition of the main alarm system."""

    def __init__(self, new_api: API) -> None:
        """Alarm system initialisation."""
        self.__api = new_api
        self.user_code: str = ""

    @staticmethod
    def _get_token(data: JsonData, key: str) -> str | None:
        if isinstance(data, dict):
            value = data.get(key)
            if isinstance(value, str):
                return value
        return None

    # System properties
    @property
    def api(self) -> API:
        """Return the API for direct access."""
        return self.__api

    @property
    async def connected(self) -> bool | None:
        """Check if the API server is connected to the alarm panel."""
        st: Status | None = await self.get_status()
        if st is None:
            return None
        return st.connected

    def get_user_code(self) -> str:
        """Get the user code."""
        return self.user_code

    async def access_grant(self, user_id: int, email: str) -> JsonData:
        """Grant a user access to the alarm panel via the API."""
        return await self.__api.access_grant(user_id, email)

    async def access_revoke(self, user_id: int) -> JsonData:
        """Revoke access to the alarm panel via the API for a user."""
        return await self.__api.access_revoke(user_id)

    async def activate_siren(self, mode: str) -> str | None:
        """Activate the siren (sound the alarm)."""
        cmd = await self.__api.activate_siren(mode)
        return self._get_token(cmd, "process_token")

    async def disable_siren(self, mode: str = "all") -> str | None:
        """Disable the siren (mute the alarm)."""
        cmd = await self.__api.disable_siren(mode=mode)
        return self._get_token(cmd, "process_token")

    async def arm_home(self, partition:int = -1, user_code : str | None = None) -> str | None:
        """Send Arm Home command to the alarm system."""
        cmd = await self.__api.arm_home(partition, user_code)
        return self._get_token(cmd, "process_token")

    async def arm_away(self, partition:int = -1, user_code : str | None = None) -> str | None:
        """Send Arm Away command to the alarm system."""
        cmd = await self.__api.arm_away(partition, user_code)
        return self._get_token(cmd, "process_token")

    async def arm_home_instant(self, partition:int = -1, user_code : str | None = None) -> str | None:
        """Send Arm Home command to the alarm system."""
        cmd = await self.__api.arm_home_instant(partition, user_code)
        return self._get_token(cmd, "process_token")

    async def arm_away_instant(self, partition:int = -1, user_code : str | None = None) -> str | None:
        """Send Arm Away command to the alarm system."""
        cmd = await self.__api.arm_away_instant(partition, user_code)
        return self._get_token(cmd, "process_token")

    async def disarm(self, partition:int = -1, user_code : str | None = None) -> str | None:
        """Send Disarm command to the alarm system."""
        cmd = await self.__api.disarm(partition, user_code)
        return self._get_token(cmd, "process_token")

    async def get_alarms(self) -> list[Alarm]:
        """Return alarms."""
        alarms = await self.__api.get_alarms()
        return [Alarm(alarm) for alarm in alarms] if isinstance(alarms, list) else []

    async def get_smart_devices(self) -> JsonData:
        """Return alarms."""
        return await self.__api.get_smart_devices()

    async def get_smart_devices_settings(self) -> JsonData:
        """Return alarms."""
        return await self.__api.get_smart_devices_settings()

    async def get_alerts(self) -> JsonData:
        """Return alerts."""
        return await self.__api.get_alerts()

    async def get_cameras(self) -> list[Camera]:
        """Fetch all the devices that are available."""
        cameras = await self.__api.get_cameras()
        return [Camera(camera) for camera in cameras] if isinstance(cameras, list) else []

    async def make_video(self, device: int) -> str | None:
        """Make a video."""
        cmd = await self.__api.make_video(device)
        return self._get_token(cmd, "process_token")

    def _get_data_from_warnings(self, warnings: list[dict[str,str]] | None) -> tuple[bool, str | None , bool , bool , bool]:
        # set default values
        low_battery = False
        trouble = None
        tamper = False
        state = False
        bypass = False
        if warnings is not None:
            for warning in warnings:
                # dict with 3 entries
                t = warning.get("type", "")
                s = warning.get("severity", "")
                _m = warning.get("in_memory", "")
                if t == "BYPASS":
                    bypass = True
                elif t == "LOW_BATTERY":
                    low_battery = True
                #elif t == "1_WAY":
                #    zone_one_way = True
                elif t == "OPENED":
                    state = True
                elif t in ("TAMPER_MEMORY", "TAMPER"):
                    tamper = True
                elif s == "TROUBLE":
                    # if Trouble and the type is none of the above, then report it as the trouble
                    trouble = None if len(t) == 0 else t.lower()
        return low_battery, trouble, tamper, state, bypass

    async def get_devices(self) -> list[Device]:
        """Fetch all the devices that are available."""
        device_list: list[Device] = []
        devices: dict[str, Any] | list[dict[str, Any]] = await self.__api.get_devices()
        if isinstance(devices, dict):
            devices = [devices] # if a single dict then make it a list of 1
        for device in devices:
            low_battery, trouble, tamper, state, _bypass = self._get_data_from_warnings(device.get("warnings"))
            # bypass not used as it's in the "traits", but is here to stop it being tagged as a "trouble"
            device["low_battery"] = low_battery
            device["trouble"] = trouble
            device["tamper"] = tamper
            device["state"] = state
            if (device_class := DEVICE_SUBTYPES.get(device["subtype"])) or (device_class := DEVICE_TYPES.get(device["device_type"])):
                device["sensor_group"] = device_class.sensor_group
                device_list.append(device_class.device(device))
            else:
                device_list.append(GenericDevice(device))
        return device_list

    async def get_events(self, timestamp_hour_offset: int = 2) -> list[Event]:
        """Get the last couple of events (60 events on my system)."""
        events = await self.__api.get_events()
        return [Event(event) for event in events] if isinstance(events, list) else []

    async def get_feature_set(self) -> FeatureSet | None:
        """Fetch the get_feature_set associated with the alarm system."""
        feature_set = await self.__api.get_feature_set()
        return FeatureSet(feature_set) if isinstance(feature_set, dict) else None

    async def get_locations(self) -> list[Location]:
        """Fetch the locations associated with the alarm system."""
        locations = await self.__api.get_locations()
        return [Location(location) for location in locations] if isinstance(locations, list) else []

    async def get_panel_info(self) -> PanelInfo | None:
        """Fetch basic information about the alarm system."""
        gpi = await self.__api.get_panel_info()
        return PanelInfo(gpi) if isinstance(gpi, dict) else None

    async def get_panels(self) -> list[Panel]:
        """Fetch a list of panels associated with the user."""
        panels = await self.__api.get_panels()
        return [Panel(panel) for panel in panels] if isinstance(panels, list) else []

    async def get_process_status(self, process_token: str) -> list[Process]:
        """Fetch the status information associated with a process token."""
        processes = await self.__api.get_process_status(process_token)
        return [Process(process) for process in processes] if isinstance(processes, list) else []

    async def get_rest_versions(self) -> list[str]:
        """Fetch the supported API versions."""
        dt: JsonData = await self.__api.get_version_info()
        if isinstance(dt, dict):
            versions = dt.get("rest_versions", [])
            if isinstance(versions, list) and all(
                isinstance(item, str) for item in versions
            ):
                return [item for item in versions if isinstance(item, str)]
        return []

    async def get_status(self) -> Status | None:
        """Fetch the current state of the alarm system."""
        status = await self.__api.get_status()
        return Status(status) if isinstance(status, dict) else None

    async def get_troubles(self) -> list[Trouble]:
        """Fetch all the troubles that are available."""
        troubles = await self.__api.get_troubles()
        return [Trouble(trouble) for trouble in troubles] if isinstance(troubles, list) else []

    async def get_auto_devices(self) -> JsonData:
        """Fetch all the automation devices that are available."""
        auto_devices = await self.__api.get_auto_devices()
        # Need to create a class that accesses the returned dict as properties
        return auto_devices  # noqa: RET504

    async def get_users(self) -> list[User]:
        """Fetch a list of users in the alarm system."""
        users = await self.__api.get_users()
        return [User(user) for user in users["users"]] if isinstance(users, dict) else []

    async def get_wakeup_sms(self) -> WakeupSMS | None:
        """Fetch a list of users in the alarm system."""
        wakeup_sms = await self.__api.get_wakeup_sms()
        return WakeupSMS(wakeup_sms) if isinstance(wakeup_sms, dict) else None

    async def panel_add(self, alias: str, panel_serial: str, master_user_code: str, access_proof: str | None = None) -> JsonData:
        """Add a new alarm panel to the user account. A master user code is required."""
        return await self.__api.panel_add(alias, panel_serial, access_proof, master_user_code)

    async def panel_login(self, panel_serial: str, user_code: str) -> bool:
        """Establish a connection between the alarm panel and the API server."""
        self.user_code = user_code
        return await self.__api.panel_login(panel_serial, user_code)

    async def panel_logout(self) -> bool:
        """Logout for a specific panel."""
        return await self.__api.panel_logout()

    async def panel_rename(self, alias: str, panel_serial: str) -> JsonData:
        """Rename an alarm panel."""
        return await self.__api.panel_rename(alias, panel_serial)

    async def panel_unlink(self, panel_serial: str, password: str, app_id: str) -> JsonData:
        """Unlink an alarm panel from the user account."""
        return await self.__api.panel_unlink(panel_serial, password, app_id)

    async def password_reset(self, email: str) -> JsonData:
        """Send a password reset link to the email address provided in the email argument."""
        return await self.__api.password_reset(email)

    async def password_reset_complete(self, reset_password_code: str, new_password: str) -> str | None:
        """Complete the password reset by entering the reset code received in the email and a new password."""
        dt: JsonData = await self.__api.password_reset_complete(reset_password_code, new_password)
        return self._get_token(dt, "user_token")

    async def set_bypass_zone(self, zone: int, set_enabled: bool) -> str | None:
        """Enabled or disable zone bypassing (for example, bypass a sensor to disable it)."""
        dt: JsonData = await self.__api.set_bypass_zone(zone, set_enabled)
        return self._get_token(dt, "process_token")

    async def set_name_user(self, user_id: int, name: str) -> str | None:
        """Set the name of a user by user ID."""
        dt: JsonData = await self.__api.set_name("USER", user_id, name)
        return self._get_token(dt, "process_token")

    async def set_rest_version(self, version: str="latest") -> None:
        """Set the REST version."""
        await self.__api.set_rest_version(version)

    async def set_user_code(self, user_id: int, user_code: str) -> str | None:
        """Set the code of a user by user ID."""
        dt: JsonData = await self.__api.set_user_code(user_code, user_id)
        return self._get_token(dt, "process_token")
