"""DeviceService tests: Android vs desktop, and failure handling."""

from __future__ import annotations

from unittest import mock

from mobi_tool.core import usb_bridge
from mobi_tool.core.mock_devices import MOCK_DEVICES
from mobi_tool.services.device_service import SOURCE_MOCK, SOURCE_USB, DeviceService


class FakeHost:
    """Stands in for UsbHost without touching any platform API."""

    def __init__(self, devices=None, error: Exception | None = None) -> None:
        self._devices = devices or []
        self._error = error

    def list_devices(self):
        if self._error is not None:
            raise self._error
        return list(self._devices)


def _on_android():
    return mock.patch.object(usb_bridge, "is_android", return_value=True)


def test_desktop_scan_uses_mock_fixtures():
    result = DeviceService().scan()
    assert result.source == SOURCE_MOCK
    assert result.ok
    assert result.count == len(MOCK_DEVICES)


def test_android_scan_uses_the_host():
    host = FakeHost(devices=MOCK_DEVICES[:2])
    with _on_android():
        result = DeviceService(host=host).scan()
    assert result.source == SOURCE_USB
    assert result.count == 2
    assert result.ok


def test_android_scan_turns_a_broken_host_into_data():
    host = FakeHost(error=RuntimeError("No Android Context available"))
    with _on_android():
        result = DeviceService(host=host).scan()
    assert not result.ok
    assert result.count == 0
    assert "No Android Context" in result.error


def test_recognised_and_unrecognised_are_split():
    host = FakeHost(devices=MOCK_DEVICES)
    with _on_android():
        result = DeviceService(host=host).scan()
    # The fourth fixture is a Xiaomi ADB device recognised by interface signature.
    assert len(result.recognised) == len(MOCK_DEVICES)
    assert result.unrecognised == []


def test_by_transport_counts_each_transport():
    host = FakeHost(devices=MOCK_DEVICES)
    with _on_android():
        result = DeviceService(host=host).scan()
    counts = result.by_transport()
    assert counts["sahara+firehose"] == 1
    assert counts["brom"] == 1
    assert counts["fastboot"] == 1
    assert counts["adb"] == 1


def test_host_is_built_lazily_and_reused():
    service = DeviceService()
    assert service._host is None

    with mock.patch.object(usb_bridge, "UsbHost") as factory, _on_android():
        factory.side_effect = FakeHost
        service.scan()
        service.scan()

    # Two scans, one host: constructing it touches the platform USB stack.
    assert factory.call_count == 1
    assert service._host is not None
