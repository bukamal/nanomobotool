"""The protocol plugin contract.

Every SoC/vendor driver (Sahara+Firehose, MediaTek BROM, fastboot, Odin, ADB)
implements `DeviceProtocol`. The UI never talks to a protocol directly: it hands
a device to the registry, and the registry picks the driver that claims it.

This is the seam that makes "support the largest possible number of devices"
tractable - adding a device family means adding one module, not editing the app.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from mobi_tool.core.usb_bridge import UsbDeviceInfo


class DeviceProtocol(ABC):
    """A driver for one low-level transport."""

    #: Matches ModeInfo.transport from device_db. The registry routes on this.
    transport: str = ""

    #: Human-readable name shown in the UI.
    name: str = ""

    @abstractmethod
    def can_handle(self, device: UsbDeviceInfo) -> bool:
        """Cheap check, no I/O. Usually compares device.mode.transport."""

    def connect(self, device: UsbDeviceInfo) -> None:
        """Perform the handshake and put the device into a known state.

        Default no-op: protocols that need no handshake (e.g. fastboot) simply
        override nothing here.
        """

    def disconnect(self, device: UsbDeviceInfo) -> None:
        """Release interfaces, close the connection, leave the device safe."""

    @abstractmethod
    def capabilities(self) -> set[str]:
        """Advertise what this driver can actually do.

        Use a namespaced vocabulary so the UI can enable/disable actions
        honestly instead of offering operations the driver cannot perform:
        {"partition.read", "partition.write", "device.info", "firmware.flash"}
        """

    def identify(self, device: UsbDeviceInfo) -> dict:
        """Return whatever the driver learned about the target, as plain data."""
        return {}


class ProtocolRegistry:
    """Keeps the known drivers and routes a device to one of them."""

    def __init__(self) -> None:
        self._drivers: list[DeviceProtocol] = []

    def register(self, driver: DeviceProtocol) -> None:
        self._drivers.append(driver)

    @property
    def drivers(self) -> list[DeviceProtocol]:
        return list(self._drivers)

    def resolve(self, device: UsbDeviceInfo) -> DeviceProtocol | None:
        for driver in self._drivers:
            try:
                if driver.can_handle(device):
                    return driver
            except Exception:
                # A misbehaving driver must never break detection for others.
                continue
        return None

    def supported_transports(self) -> set[str]:
        return {d.transport for d in self._drivers if d.transport}
