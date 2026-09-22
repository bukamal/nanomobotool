"""The device card: how one attached device is presented."""

from __future__ import annotations

import flet as ft

from mobi_tool.components.theme import (
    BORDER,
    CARD_BG,
    TEXT,
    TEXT_BODY,
    TEXT_MUTED,
    accent_for,
)
from mobi_tool.core.device_db import ModeInfo
from mobi_tool.core.usb_bridge import UsbDeviceInfo

UNKNOWN_MODE_LABEL = "وضع غير معروف"


def mode_chip(mode: ModeInfo | None) -> ft.Control:
    """Coloured pill showing the detected mode."""
    accent = accent_for(mode.key if mode else None)
    label = mode.label if mode else UNKNOWN_MODE_LABEL

    return ft.Container(
        content=ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color="#0b1120"),
        bgcolor=accent,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        border_radius=999,
    )


def _kv(key: str, value: str) -> ft.Control:
    return ft.Row(
        controls=[
            ft.Text(key, size=12, color=TEXT_MUTED, width=110),
            ft.Text(value, size=12, color=TEXT_BODY, selectable=True),
        ],
        spacing=6,
    )


def interface_summary(info: UsbDeviceInfo) -> str:
    """One-line description of the interfaces/endpoints, or a placeholder."""
    if not info.interfaces:
        return "لا توجد واجهات معلنة"

    parts: list[str] = []
    for itf in info.interfaces:
        endpoints = ", ".join(
            f"0x{ep.address:02x} {ep.transfer_type} {ep.direction}" for ep in itf.endpoints
        )
        line = (
            f"class 0x{itf.interface_class:02x} "
            f"sub 0x{itf.subclass:02x} proto 0x{itf.protocol:02x}"
        )
        if endpoints:
            line += f"  [{endpoints}]"
        parts.append(line)
    return " | ".join(parts)


def device_card(info: UsbDeviceInfo) -> ft.Control:
    """Render one attached device as a card."""
    mode = info.mode

    details: list[ft.Control] = [
        _kv("VID:PID", info.id_label),
        _kv("Vendor", info.vendor),
    ]
    if info.product:
        details.append(_kv("Product", info.product))
    if mode is not None:
        details.append(_kv("Transport", mode.transport))
        details.append(_kv("SoC", mode.soc_family))
        if mode.notes:
            details.append(_kv("Note", mode.notes))

    details.append(_kv("Interfaces", interface_summary(info)))

    header = ft.Row(
        controls=[
            ft.Column(
                controls=[
                    ft.Text(
                        info.display_name,
                        size=15,
                        weight=ft.FontWeight.BOLD,
                        color=TEXT,
                    ),
                    ft.Text(
                        f"{info.manufacturer or info.vendor} · {info.device_name}",
                        size=11,
                        color=TEXT_MUTED,
                    ),
                ],
                spacing=2,
                expand=True,
            ),
            mode_chip(mode),
        ],
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    return ft.Container(
        content=ft.Column(
            controls=[header, ft.Divider(height=12, color=BORDER)] + details,
            spacing=4,
        ),
        bgcolor=CARD_BG,
        padding=14,
        border_radius=12,
        border=ft.Border.all(1, BORDER),
    )
