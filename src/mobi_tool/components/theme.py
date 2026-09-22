"""Central colour palette.

Plain hex strings on purpose: this keeps the app independent of Flet's colour
enum layout, which has been renamed between releases.
"""

from __future__ import annotations

PAGE_BG = "#0b1120"
CARD_BG = "#111827"
BORDER = "#1f2937"
TEXT = "#f8fafc"
TEXT_BODY = "#e2e8f0"
TEXT_MUTED = "#94a3b8"
ACCENT = "#0f766e"

# Accent per detected transport mode. Unknown modes fall back to DEFAULT_ACCENT.
MODE_ACCENT: dict[str, str] = {
    "edl": "#f59e0b",
    "diag": "#fb923c",
    "brom": "#ef4444",
    "preloader": "#ef4444",
    "fastboot": "#22c55e",
    "adb": "#3b82f6",
    "odin": "#a855f7",
    "dfu": "#6b7280",
    "recovery": "#6b7280",
}
DEFAULT_ACCENT = "#64748b"


def accent_for(mode_key: str | None) -> str:
    return MODE_ACCENT.get(mode_key or "", DEFAULT_ACCENT)
