"""Nano Mobi Tool - application entry point.

Kept deliberately thin: it builds the page chrome and hands control to the
view. All behaviour lives in the `mobi_tool` package so it stays testable
without a running Flet server.
"""

from __future__ import annotations

import flet as ft

from mobi_tool.components.theme import PAGE_BG
from mobi_tool.services.device_service import DeviceService
from mobi_tool.views.devices_view import DevicesView


def main(page: ft.Page) -> None:
    page.title = "Nano Mobi Tool"
    page.bgcolor = PAGE_BG
    page.padding = 16
    page.scroll = ft.ScrollMode.AUTO

    view = DevicesView(page, DeviceService())
    page.add(view.root)
    view.attach()


if __name__ == "__main__":
    ft.run(main)
