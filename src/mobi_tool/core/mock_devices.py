"""Development fixtures.

Used when the app runs on a desktop, so the whole UI can be built and reviewed
without a phone and an OTG cable. Never referenced from the Android code path.
"""

from __future__ import annotations

from mobi_tool.core.usb_bridge import Interface, UsbDeviceInfo

MOCK_DEVICES: list[UsbDeviceInfo] = [
    UsbDeviceInfo(
        device_name="/dev/bus/usb/001/002",
        vendor_id=0x05C6,
        product_id=0x9008,
        device_class=0x00,
        manufacturer="Qualcomm Incorporated",
        product="Qualcomm HS-USB QDLoader 9008",
    ),
    UsbDeviceInfo(
        device_name="/dev/bus/usb/001/003",
        vendor_id=0x0E8D,
        product_id=0x0003,
        device_class=0x00,
        manufacturer="MediaTek Inc",
        product="MTK USB Port",
    ),
    UsbDeviceInfo(
        device_name="/dev/bus/usb/001/004",
        vendor_id=0x18D1,
        product_id=0xD00D,
        device_class=0x00,
        manufacturer="Google Inc.",
        product="Android Fastboot",
    ),
    UsbDeviceInfo(
        device_name="/dev/bus/usb/001/005",
        vendor_id=0x2717,
        product_id=0xABCD,
        device_class=0x00,
        manufacturer="Xiaomi Inc.",
        product="Xiaomi ADB Device",
        interfaces=[
            Interface(
                index=0,
                interface_class=0xFF,
                subclass=0x42,
                protocol=0x01,
            )
        ],
    ),
]
