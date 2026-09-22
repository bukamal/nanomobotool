#!/usr/bin/env python3
"""Standalone device-detection smoke test.

Runs without pytest and without a device. Useful on an Android handset where
installing the dev toolchain is inconvenient:

    python tools/device_detection_smoke_test.py

Exits non-zero on the first failure so it can gate a release build.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mobi_tool.core import device_db  # noqa: E402
from mobi_tool.core import usb_bridge  # noqa: E402
from mobi_tool.core.mock_devices import MOCK_DEVICES  # noqa: E402
from mobi_tool.protocols import ProtocolRegistry  # noqa: E402
from mobi_tool.services.device_service import DeviceService  # noqa: E402

checks_run = 0


def check(label: str, condition: bool) -> None:
    global checks_run
    checks_run += 1
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise SystemExit(1)


def main() -> int:
    print(f"platform: {'android' if usb_bridge.is_android() else 'desktop'}")
    print()

    # --- detection table -------------------------------------------------
    edl = device_db.identify(0x05C6, 0x9008)
    check("Qualcomm EDL is recognised", edl is not None and edl.key == "edl")

    brom = device_db.identify(0x0E8D, 0x0003)
    check("MediaTek BROM is recognised", brom is not None and brom.transport == "brom")

    adb = device_db.identify(0x1234, 0x5678, [(0xFF, 0x42, 0x01)])
    check("ADB interface signature is recognised", adb is not None and adb.key == "adb")

    check("unknown device stays unidentified", device_db.identify(0x1234, 0x5678) is None)

    # --- service ---------------------------------------------------------
    result = DeviceService().scan()
    print(f"  scan source: {result.source}, devices: {result.count}, error: {result.error!r}")
    check("scan always returns a usable result", result.source in ("usb", "mock"))
    if result.source == "mock":
        check("desktop scan returns the fixtures", result.count == len(MOCK_DEVICES))
        check("transport breakdown is populated", bool(result.by_transport()))
    else:
        check("android scan did not fail", result.ok)

    # --- registry --------------------------------------------------------
    registry = ProtocolRegistry()
    check("empty registry resolves nothing", registry.resolve(MOCK_DEVICES[0]) is None)

    print()
    print(f"{checks_run} checks passed")

    if usb_bridge.is_android():
        print()
        print("NOTE: this ran on Android. To exercise the real USB layer, plug in")
        print("      a target over OTG and confirm list_devices() returns it.")
    else:
        print()
        print("NOTE: desktop run - the USB bridge itself was NOT exercised.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
