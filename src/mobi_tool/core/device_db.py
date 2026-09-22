"""USB VID/PID identification tables.

Deliberately free of any Android dependency so the whole detection logic can be
unit-tested on a plain desktop (see tests/unit/test_device_db.py).

A "mode" here means: which low-level transport the target device is currently
speaking, and therefore which protocol driver the app should attach.
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------
# USB constants (mirror android.hardware.usb.UsbConstants)
# --------------------------------------------------------------------------
USB_DIR_IN = 0x80

XFER_CONTROL = 0
XFER_ISOC = 1
XFER_BULK = 2
XFER_INT = 3

IFACE_VENDOR_SPECIFIC = 0xFF

# The Android Debug Bridge interface signature. Any device exposing an
# interface with this class/subclass/protocol triple is in ADB mode.
ADB_SIGNATURE = (IFACE_VENDOR_SPECIFIC, 0x42, 0x01)


# --------------------------------------------------------------------------
# Vendor names, for display only. Extend as needed.
# --------------------------------------------------------------------------
VENDORS: dict[int, str] = {
    0x04E8: "Samsung",
    0x0421: "Nokia",
    0x05AC: "Apple",
    0x05C6: "Qualcomm",
    0x0B05: "ASUS",
    0x0BB4: "HTC",
    0x0E8D: "MediaTek",
    0x0FCE: "Sony",
    0x1004: "LG",
    0x12D1: "Huawei / Honor",
    0x1782: "Unisoc (Spreadtrum)",
    0x18D1: "Google / Android",
    0x22B8: "Motorola",
    0x22D9: "OPPO",
    0x2717: "Xiaomi",
    0x2A70: "OnePlus",
    0x2D95: "vivo",
}


@dataclass(frozen=True)
class ModeInfo:
    """What we believe the connected device is doing right now.

    key:        short machine name ("edl", "brom", "fastboot", ...)
    label:      human-readable name for the UI
    soc_family: Sahara / Firehose / BROM / fastboot / Odin ...
    transport:  which protocol driver should be attached to talk to it
    risky:      acting on this mode needs extra care or authorisation
    """

    key: str
    label: str
    soc_family: str
    transport: str
    risky: bool = False
    notes: str = ""


# --------------------------------------------------------------------------
# Known (vendor_id, product_id) -> mode map. This is the table you keep
# growing as you add device support; nothing else in the codebase needs to
# change to recognise a new device.
# --------------------------------------------------------------------------
USB_MODES: dict[tuple[int, int], ModeInfo] = {
    # ---- Qualcomm: Emergency Download (the classic "9008" port) ----
    (0x05C6, 0x9008): ModeInfo(
        key="edl",
        label="Qualcomm EDL (9008)",
        soc_family="Qualcomm Snapdragon",
        transport="sahara+firehose",
        notes="Firehose programmer (.mbn/.elf) must match the SoC.",
    ),
    (0x05C6, 0x900E): ModeInfo(
        key="edl",
        label="Qualcomm EDL (alternate)",
        soc_family="Qualcomm Snapdragon",
        transport="sahara+firehose",
    ),
    (0x05C6, 0x901D): ModeInfo(
        key="edl",
        label="Qualcomm EDL (alternate)",
        soc_family="Qualcomm Snapdragon",
        transport="sahara+firehose",
    ),
    (0x05C6, 0x9091): ModeInfo(
        key="diag",
        label="Qualcomm Diagnostic",
        soc_family="Qualcomm",
        transport="diag",
    ),
    # ---- MediaTek: BootROM handshake and preloader ----
    (0x0E8D, 0x0003): ModeInfo(
        key="brom",
        label="MediaTek BROM (BootROM)",
        soc_family="MediaTek",
        transport="brom",
        notes="Tight handshake timing: keep this path fully on-device.",
    ),
    (0x0E8D, 0x2000): ModeInfo(
        key="preloader",
        label="MediaTek Preloader",
        soc_family="MediaTek",
        transport="brom",
    ),
    (0x0E8D, 0x2001): ModeInfo(
        key="preloader",
        label="MediaTek Preloader (VCOM)",
        soc_family="MediaTek",
        transport="brom",
    ),
    # ---- Android / Google ----
    (0x18D1, 0xD00D): ModeInfo(
        key="fastboot",
        label="Fastboot",
        soc_family="Generic",
        transport="fastboot",
    ),
    # ---- Samsung download mode (Odin / Loke protocol) ----
    (0x04E8, 0x685D): ModeInfo(
        key="odin",
        label="Samsung Download Mode",
        soc_family="Exynos / Snapdragon",
        transport="odin",
        risky=True,
    ),
    (0x04E8, 0x6860): ModeInfo(
        key="odin",
        label="Samsung Download Mode (modem)",
        soc_family="Exynos / Snapdragon",
        transport="odin",
        risky=True,
    ),
    # ---- Apple (informational only: not a supported servicing target) ----
    (0x05AC, 0x1227): ModeInfo(
        key="dfu",
        label="Apple DFU",
        soc_family="Apple",
        transport="none",
        risky=True,
        notes="Out of scope: no supported servicing workflow.",
    ),
    (0x05AC, 0x1281): ModeInfo(
        key="recovery",
        label="Apple Recovery",
        soc_family="Apple",
        transport="none",
        risky=True,
        notes="Out of scope: no supported servicing workflow.",
    ),
}


# Google/Android ADB PIDs - a contiguous, well-known range.
for _pid in range(0x4EE0, 0x4EE9):
    USB_MODES[(0x18D1, _pid)] = ModeInfo(
        key="adb",
        label="Android (ADB)",
        soc_family="Generic",
        transport="adb",
    )
del _pid


def vendor_name(vendor_id: int) -> str:
    return VENDORS.get(vendor_id, f"Unknown ({vendor_id:#06x})")


def identify(
    vendor_id: int,
    product_id: int,
    interfaces: list[tuple[int, int, int]] | None = None,
) -> ModeInfo | None:
    """Best-effort guess at what mode a connected device is in.

    The VID/PID table is consulted first. If that misses, we fall back to the
    interface signature, which is how ADB and MTP are detected reliably.
    """
    known = USB_MODES.get((vendor_id, product_id))
    if known is not None:
        return known

    for iface_class, subclass, protocol in interfaces or ():
        if (iface_class, subclass, protocol) == ADB_SIGNATURE:
            return ModeInfo(
                key="adb",
                label="Android (ADB)",
                soc_family="Generic",
                transport="adb",
                notes="Recognised by interface class 0xff/0x42/0x01.",
            )

    return None


def describe(vendor_id: int, product_id: int) -> str:
    return f"{vendor_name(vendor_id)} {vendor_id:#06x}:{product_id:#06x}"
