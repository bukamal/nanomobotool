"""Integration tests for the devices screen.

These build the real Flet control tree (no server, no window, no device) so
they catch both logic regressions and Flet API drift on upgrade.
"""

from __future__ import annotations

from unittest import mock

import flet as ft

from mobi_tool.components.device_card import device_card, interface_summary
from mobi_tool.components.theme import DEFAULT_ACCENT, accent_for
from mobi_tool.core import usb_bridge
from mobi_tool.core.mock_devices import MOCK_DEVICES
from mobi_tool.core.usb_bridge import Interface, UsbDeviceInfo
from mobi_tool.services.device_service import SOURCE_MOCK, DeviceService
from mobi_tool.views.devices_view import DevicesView


class StubPage:
    """Minimal stand-in: records that the view asked for a repaint."""

    def __init__(self) -> None:
        self.updates = 0

    def update(self) -> None:
        self.updates += 1


class FakeHost:
    def __init__(self, devices=None, error: Exception | None = None) -> None:
        self._devices = devices or []
        self._error = error

    def list_devices(self):
        if self._error is not None:
            raise self._error
        return list(self._devices)


def _android_view(host) -> tuple[DevicesView, StubPage]:
    page = StubPage()
    with mock.patch.object(usb_bridge, "is_android", return_value=True):
        view = DevicesView(page, DeviceService(host=host))
        view.attach()
    return view, page


def test_attach_renders_mock_devices_and_repaints():
    page = StubPage()
    view = DevicesView(page, DeviceService())
    view.attach()

    assert page.updates >= 1
    assert len(view.list_holder.controls) == 1
    assert "تجريبي" in view.status.value
    assert view.transport_summary.value != ""


def test_view_reports_recognised_transports():
    view, _ = _android_view(FakeHost(devices=MOCK_DEVICES))

    assert "4 جهاز موصول" in view.status.value
    assert "تم التعرّف عليه" in view.status.value
    summary = view.transport_summary.value
    assert "sahara+firehose: 1" in summary
    assert "adb: 1" in summary


def test_view_shows_empty_state_when_nothing_is_plugged_in():
    view, _ = _android_view(FakeHost(devices=[]))

    assert view.list_holder.controls
    assert view.transport_summary.value == ""


def test_view_surfaces_a_usb_failure_instead_of_crashing():
    view, page = _android_view(FakeHost(error=RuntimeError("permission denied")))

    assert "فشل" in view.status.value
    assert page.updates >= 1
    assert view.list_holder.controls


def test_manual_refresh_repaints_again():
    page = StubPage()
    view = DevicesView(page, DeviceService())
    view.attach()
    before = page.updates
    view.refresh()
    assert page.updates > before


def test_device_card_builds_for_an_unknown_device():
    info = UsbDeviceInfo(
        device_name="/dev/bus/usb/001/099",
        vendor_id=0x1234,
        product_id=0x5678,
        device_class=0x00,
    )
    card = device_card(info)
    assert isinstance(card, ft.Container)


def test_device_card_builds_for_a_device_with_interfaces():
    info = UsbDeviceInfo(
        device_name="/dev/bus/usb/001/100",
        vendor_id=0x0E8D,
        product_id=0x0003,
        device_class=0x00,
        interfaces=[Interface(0, 0xFF, 0x00, 0x00)],
    )
    assert isinstance(device_card(info), ft.Container)


def test_interface_summary_handles_no_interfaces():
    info = UsbDeviceInfo(
        device_name="x",
        vendor_id=0x1111,
        product_id=0x2222,
        device_class=0x00,
    )
    assert interface_summary(info) == "لا توجد واجهات معلنة"


def test_accent_falls_back_for_unknown_mode():
    assert accent_for(None) == DEFAULT_ACCENT
    assert accent_for("not-a-real-mode") == DEFAULT_ACCENT
    assert accent_for("edl") != DEFAULT_ACCENT


def test_mock_source_constant_is_stable():
    assert DeviceService().scan().source == SOURCE_MOCK
