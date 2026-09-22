"""The devices screen.

Owns the page interaction (status text, refresh, scrolling) and composes the
components. All data comes from DeviceService, so this module never touches the
USB stack directly.
"""

from __future__ import annotations

import flet as ft

from mobi_tool.components.device_card import device_card
from mobi_tool.components.theme import (
    BORDER,
    CARD_BG,
    PAGE_BG,
    TEXT,
    TEXT_MUTED,
)
from mobi_tool.services.device_service import SOURCE_MOCK, DeviceService, ScanResult

TITLE = "Nano Mobi Tool"
FOOTER = "USB Host · البروتوكولات: EDL · BROM · Fastboot · ADB · Odin"


class DevicesView:
    """Main screen. Construct, hand `.root` to the page, then call `.attach()`."""

    def __init__(self, page, service: DeviceService) -> None:
        self.page = page
        self.service = service

        self.status = ft.Text("جاهز", size=12, color=TEXT_MUTED)
        self.transport_summary = ft.Text("", size=11, color=TEXT_MUTED)
        self.list_holder = ft.Column(expand=True)

        self.root = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(
                                    TITLE,
                                    size=22,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT,
                                ),
                                self.status,
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.ElevatedButton(
                            "تحديث",
                            icon=ft.Icons.REFRESH,
                            on_click=self.refresh,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self.transport_summary,
                ft.Container(
                    content=ft.Text(FOOTER, size=11, color=TEXT_MUTED),
                    padding=ft.Padding.only(top=4, bottom=8),
                ),
                ft.Divider(height=1, color=BORDER),
                self.list_holder,
            ],
            spacing=8,
        )

    # -- lifecycle -------------------------------------------------------
    def attach(self) -> None:
        """First load. Separated from __init__ so tests can skip it."""
        self.refresh()

    # -- rendering -------------------------------------------------------
    def refresh(self, e=None) -> None:
        self.status.value = "جارٍ الفحص..."
        self._update()

        result = self.service.scan()

        self.list_holder.controls = [self._body(result)]
        self.status.value = self._status_text(result)
        self.transport_summary.value = self._summary_text(result)
        self._update()

    def _update(self) -> None:
        # A page is not always attached (tests build the tree headlessly).
        updater = getattr(self.page, "update", None)
        if callable(updater):
            updater()

    def _body(self, result: ScanResult) -> ft.Control:
        if result.error:
            return self._message_card(
                "فشل الوصول إلى USB",
                result.error,
                accent="#ef4444",
            )
        if not result.devices:
            return self._message_card(
                "لا يوجد جهاز موصول",
                "وصّل الجهاز عبر كابل OTG ثم اضغط تحديث.",
            )
        return ft.Column(controls=[device_card(d) for d in result.devices], spacing=10)

    def _message_card(self, title: str, body: str, accent: str = BORDER) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(title, size=14, color=TEXT),
                    ft.Text(body, size=12, color=TEXT_MUTED, selectable=True),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            ),
            bgcolor=CARD_BG,
            padding=32,
            border_radius=12,
            border=ft.Border.all(1, accent),
            alignment=ft.Alignment.CENTER,
        )

    def _status_text(self, result: ScanResult) -> str:
        if result.error:
            return "فشل الفحص"
        if result.source == SOURCE_MOCK:
            return f"{result.count} جهاز تجريبي · وضع سطح المكتب"
        return f"{result.count} جهاز موصول · {len(result.recognised)} تم التعرّف عليه"

    def _summary_text(self, result: ScanResult) -> str:
        counts = result.by_transport()
        if not counts:
            return ""
        return " · ".join(f"{transport}: {count}" for transport, count in sorted(counts.items()))


def build_devices_view(page, service: DeviceService) -> DevicesView:
    """Convenience constructor used by main and by tests."""
    return DevicesView(page, service)


__all__ = ["DevicesView", "build_devices_view", "PAGE_BG"]
