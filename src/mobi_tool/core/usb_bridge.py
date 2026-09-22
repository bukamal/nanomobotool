"""Android USB Host access, bridged into Python with pyjnius.

Everything that touches the platform USB stack lives behind this module, so the
rest of the app only ever sees plain dataclasses. That keeps the UI testable on
a desktop and makes it possible to swap in a different bridge later (e.g. a
custom Kotlin/Flutter plugin under extensions/) without touching protocol code.

The module is import-safe on non-Android hosts: `is_android()` returns False and
nothing platform-specific is resolved until `UsbHost` is actually constructed.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

from mobi_tool.core.device_db import (
    USB_DIR_IN,
    XFER_BULK,
    XFER_CONTROL,
    XFER_INT,
    XFER_ISOC,
    identify,
    vendor_name,
)

# android.content.Context.USB_SERVICE
USB_SERVICE = "usb"

# PendingIntent.FLAG_IMMUTABLE - mandatory for implicit broadcasts on API 31+.
FLAG_IMMUTABLE = 0x02000000

XFER_NAMES = {
    XFER_CONTROL: "control",
    XFER_ISOC: "isochronous",
    XFER_BULK: "bulk",
    XFER_INT: "interrupt",
}


def is_android() -> bool:
    """True only when running inside the packaged Android app."""
    try:
        from jnius import autoclass

        autoclass("android.os.Build")
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# Value objects
# --------------------------------------------------------------------------
@dataclass
class Endpoint:
    address: int
    direction: str  # "in" | "out"
    transfer_type: str  # "bulk" | "control" | ...
    max_packet_size: int
    interval: int = 0


@dataclass
class Interface:
    index: int
    interface_class: int
    subclass: int
    protocol: int
    endpoints: list[Endpoint] = field(default_factory=list)


@dataclass
class UsbDeviceInfo:
    """A snapshot of one attached USB device."""

    device_name: str
    vendor_id: int
    product_id: int
    device_class: int
    manufacturer: str = ""
    product: str = ""
    interfaces: list[Interface] = field(default_factory=list)

    @property
    def vendor(self) -> str:
        return vendor_name(self.vendor_id)

    @property
    def mode(self):
        return identify(
            self.vendor_id,
            self.product_id,
            [(i.interface_class, i.subclass, i.protocol) for i in self.interfaces],
        )

    @property
    def id_label(self) -> str:
        return f"{self.vendor_id:04x}:{self.product_id:04x}"

    @property
    def display_name(self) -> str:
        return self.product or self.vendor


# --------------------------------------------------------------------------
# The bridge itself
# --------------------------------------------------------------------------
class UsbHost:
    """Thin wrapper over UsbManager / UsbDeviceConnection.

    Nothing is resolved at import time; the jnius handles are created lazily so
    this class can be constructed harmlessly on desktop.
    """

    def __init__(self) -> None:
        self._context = None
        self._manager = None
        self._connections: dict[str, object] = {}

    # -- context ---------------------------------------------------------
    def _get_context(self):
        if self._context is not None:
            return self._context

        from jnius import autoclass

        # An Application context is enough for enumerating devices, opening
        # them and calling requestPermission(). Preferring it over the Activity
        # avoids depending on Flet's internal Activity class name.
        try:
            activity_thread = autoclass("android.app.ActivityThread")
            app = activity_thread.currentApplication()
            if app is not None:
                self._context = app
                return self._context
        except Exception:
            pass

        # Fallback: the host class name Flet exports to the embedded runtime.
        host_name = os.environ.get("MAIN_ACTIVITY_HOST_CLASS_NAME")
        if host_name:
            host = autoclass(host_name)
            self._context = host.mActivity
            return self._context

        raise RuntimeError(
            "No Android Context available. If this is a packaged Flet build, "
            "check that pyjnius is declared under [tool.flet.android]."
        )

    @property
    def manager(self):
        if self._manager is None:
            from jnius import cast

            context = self._get_context()
            service = context.getSystemService(USB_SERVICE)
            self._manager = cast("android.hardware.usb.UsbManager", service)
        return self._manager

    # -- enumeration -----------------------------------------------------
    def list_devices(self) -> list[UsbDeviceInfo]:
        from jnius import cast

        raw_map = self.manager.getDeviceList()
        collection = cast("java.util.Collection", raw_map.values())
        array = collection.toArray()

        devices: list[UsbDeviceInfo] = []
        for i in range(len(array)):
            raw = cast("android.hardware.usb.UsbDevice", array[i])
            devices.append(self._describe(raw))
        return devices

    def _describe(self, raw) -> UsbDeviceInfo:
        from jnius import cast

        interfaces: list[Interface] = []
        for i in range(raw.getInterfaceCount()):
            itf = cast("android.hardware.usb.UsbInterface", raw.getInterface(i))
            endpoints: list[Endpoint] = []
            for j in range(itf.getEndpointCount()):
                ep = cast("android.hardware.usb.UsbEndpoint", itf.getEndpoint(j))
                endpoints.append(
                    Endpoint(
                        address=ep.getAddress(),
                        direction="in" if ep.getDirection() == USB_DIR_IN else "out",
                        transfer_type=XFER_NAMES.get(ep.getType(), "unknown"),
                        max_packet_size=ep.getMaxPacketSize(),
                        interval=ep.getInterval(),
                    )
                )
            interfaces.append(
                Interface(
                    index=i,
                    interface_class=itf.getInterfaceClass(),
                    subclass=itf.getInterfaceSubclass(),
                    protocol=itf.getInterfaceProtocol(),
                    endpoints=endpoints,
                )
            )

        return UsbDeviceInfo(
            device_name=str(raw.getDeviceName()),
            vendor_id=int(raw.getVendorId()),
            product_id=int(raw.getProductId()),
            device_class=int(raw.getDeviceClass()),
            manufacturer=_safe_str(raw, "getManufacturerName"),
            product=_safe_str(raw, "getProductName"),
            interfaces=interfaces,
        )

    # -- permissions -----------------------------------------------------
    def has_permission(self, raw) -> bool:
        return bool(self.manager.hasPermission(raw))

    def request_permission(self, raw, timeout: float = 20.0) -> bool:
        """Ask the OS for access and wait for the user's answer.

        We poll hasPermission() instead of registering a BroadcastReceiver:
        registering one from a non-Activity context has extra API-level rules,
        and polling gives identical results for a fraction of the complexity.
        """
        if self.has_permission(raw):
            return True

        self.manager.requestPermission(raw, self._permission_intent())

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.has_permission(raw):
                return True
            time.sleep(0.25)
        return False

    def _permission_intent(self):
        from jnius import autoclass

        context = self._get_context()
        Intent = autoclass("android.content.Intent")
        PendingIntent = autoclass("android.app.PendingIntent")
        version = autoclass("android.os.Build$VERSION")

        package = str(context.getPackageName())
        intent = Intent(package + ".USB_PERMISSION")
        intent.setPackage(package)

        flags = int(PendingIntent.FLAG_UPDATE_CURRENT)
        if int(version.SDK_INT) >= 31:
            flags |= FLAG_IMMUTABLE
        return PendingIntent.getBroadcast(context, 0, intent, flags)

    # -- I/O -------------------------------------------------------------
    def open(self, raw):
        """Open a device that has already been granted permission."""
        name = str(raw.getDeviceName())
        if name in self._connections:
            return self._connections[name]

        connection = self.manager.openDevice(raw)
        if connection is None:
            raise RuntimeError(
                "openDevice() returned null - permission was not granted, or "
                "another process already holds the device."
            )
        self._connections[name] = connection
        return connection

    def claim(self, connection, raw_interface, force: bool = True) -> bool:
        """Claim an interface so we can issue transfers on it.

        `force=True` is required when a kernel driver already owns the
        interface; on a stock device that usually needs root.
        """
        return bool(connection.claimInterface(raw_interface, bool(force)))

    def release(self, connection, raw_interface) -> bool:
        return bool(connection.releaseInterface(raw_interface))

    def close(self, raw) -> None:
        name = str(raw.getDeviceName())
        connection = self._connections.pop(name, None)
        if connection is not None:
            connection.close()

    def bulk_write(self, connection, endpoint, payload: bytes, timeout_ms: int = 5000) -> int:
        buffer = _new_byte_array(len(payload))
        for index, value in enumerate(payload):
            buffer[index] = value & 0xFF
        return int(connection.bulkTransfer(endpoint, buffer, 0, len(payload), timeout_ms))

    def bulk_read(self, connection, endpoint, length: int, timeout_ms: int = 5000) -> bytes:
        buffer = _new_byte_array(length)
        count = int(connection.bulkTransfer(endpoint, buffer, 0, length, timeout_ms))
        if count < 0:
            return b""
        return _read_byte_array(buffer, count)

    def control_read(
        self,
        connection,
        request: int,
        value: int,
        index: int,
        length: int,
        timeout_ms: int = 1000,
    ) -> bytes:
        """Standard device-to-host control transfer (bmRequestType 0x80)."""
        buffer = _new_byte_array(length)
        count = int(
            connection.controlTransfer(0x80, request, value, index, buffer, 0, length, timeout_ms)
        )
        if count < 0:
            return b""
        return _read_byte_array(buffer, count)

    def read_device_descriptor(self, connection) -> dict:
        """Read the raw 18-byte device descriptor.

        This is the smallest useful end-to-end proof that control transfers
        work against the target device.
        """
        raw = self.control_read(connection, request=0x06, value=0x0100, index=0, length=18)
        if len(raw) < 18:
            return {}
        return {
            "bcd_usb": f"{raw[3]:02x}{raw[2]:02x}",
            "class": raw[4],
            "subclass": raw[5],
            "protocol": raw[6],
            "max_packet_size_0": raw[7],
            "vendor_id": raw[9] << 8 | raw[8],
            "product_id": raw[11] << 8 | raw[10],
            "num_configurations": raw[17],
        }


# --------------------------------------------------------------------------
# jnius byte[] helpers
# --------------------------------------------------------------------------
def _new_byte_array(size: int):
    from jnius import autoclass

    return autoclass("[B")(size)


def _read_byte_array(buffer, count: int) -> bytes:
    # Java bytes are signed; mask back to unsigned.
    return bytes(int(buffer[i]) & 0xFF for i in range(count))


def _safe_str(raw, getter: str) -> str:
    """Some devices throw or return null for the name getters."""
    try:
        value = getattr(raw, getter)()
        return str(value) if value is not None else ""
    except Exception:
        return ""
