"""Device scanning orchestration.

Owns the decision of *how* to enumerate devices (real USB host on Android, mock
fixtures on desktop) and turns failures into data instead of exceptions, so the
view never has to wrap anything in try/except.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mobi_tool.core import usb_bridge
from mobi_tool.core.mock_devices import MOCK_DEVICES
from mobi_tool.core.usb_bridge import UsbDeviceInfo

SOURCE_USB = "usb"
SOURCE_MOCK = "mock"


@dataclass
class ScanResult:
    """Outcome of one scan. Always usable, even when it failed."""

    devices: list[UsbDeviceInfo] = field(default_factory=list)
    source: str = SOURCE_USB
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    @property
    def count(self) -> int:
        return len(self.devices)

    @property
    def recognised(self) -> list[UsbDeviceInfo]:
        return [d for d in self.devices if d.mode is not None]

    @property
    def unrecognised(self) -> list[UsbDeviceInfo]:
        return [d for d in self.devices if d.mode is None]

    def by_transport(self) -> dict[str, int]:
        """Count recognised devices per transport, e.g. {"edl": 1, "brom": 1}."""
        counts: dict[str, int] = {}
        for device in self.recognised:
            key = device.mode.transport
            counts[key] = counts.get(key, 0) + 1
        return counts


class DeviceService:
    """Enumerates attached devices and reports what it thinks they are."""

    def __init__(self, host=None) -> None:
        # Injectable for tests; built lazily otherwise so nothing touches the
        # platform USB stack on import.
        self._host = host

    def _get_host(self):
        if self._host is None:
            self._host = usb_bridge.UsbHost()
        return self._host

    def scan(self) -> ScanResult:
        if not usb_bridge.is_android():
            return ScanResult(devices=list(MOCK_DEVICES), source=SOURCE_MOCK)

        try:
            devices = self._get_host().list_devices()
        except Exception as exc:
            return ScanResult(devices=[], source=SOURCE_USB, error=str(exc))

        return ScanResult(devices=devices, source=SOURCE_USB)
