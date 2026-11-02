"""Track trigger transitions observed in successive cloud polls."""

from collections.abc import Sequence

from .devices import Device, SensorDevice
from .sensor_types import SensorCapability


class SensorStateTracker:
    """Keep trigger counters across polling and authentication sessions."""

    def __init__(self) -> None:
        """Initialize counters and observed baselines."""
        self._states: dict[int, tuple[bool | None, int]] = {}

    def reset_baselines(self) -> None:
        """Retain counters while discarding observations across connection gaps."""
        self._states = {
            key: (None, count) for key, (_active, count) in self._states.items()
        }

    def update(self, devices: Sequence[Device]) -> None:
        """Count observed inactive-to-active transitions, never sustained activity."""
        observed: set[int] = set()
        for device in devices:
            if not isinstance(device, SensorDevice):
                continue
            observed.add(device.id)
            previous, count = self._states.get(device.id, (None, 0))
            active = (
                device.is_open
                if device.enrolled and SensorCapability.TRIGGER in device.capabilities
                else None
            )
            if previous is False and active is True:
                count = (count + 1) % 100
            device.triggered = count
            self._states[device.id] = (active, count)
        for key in self._states.keys() - observed:
            _previous, count = self._states[key]
            self._states[key] = (None, count)
