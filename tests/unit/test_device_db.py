"""Detection logic tests. No Android and no USB hardware required."""

from __future__ import annotations

from mobi_tool.core import device_db


def test_known_qualcomm_edl_port():
    mode = device_db.identify(0x05C6, 0x9008)
    assert mode is not None
    assert mode.key == "edl"
    assert mode.transport == "sahara+firehose"


def test_known_mediatek_brom_port():
    mode = device_db.identify(0x0E8D, 0x0003)
    assert mode is not None
    assert mode.transport == "brom"


def test_unknown_vid_pid_falls_back_to_interface_signature():
    # Android Debug Bridge signature: class 0xff / subclass 0x42 / proto 0x01.
    mode = device_db.identify(0x1234, 0x5678, [(0xFF, 0x42, 0x01)])
    assert mode is not None
    assert mode.key == "adb"


def test_unknown_device_without_signature_is_unidentified():
    assert device_db.identify(0x1234, 0x5678, [(0x08, 0x06, 0x50)]) is None
    assert device_db.identify(0x1234, 0x5678) is None


def test_vid_pid_table_wins_over_interface_signature():
    # A device we know by VID/PID must not be re-labelled by a stray signature.
    mode = device_db.identify(0x0E8D, 0x0003, [(0xFF, 0x42, 0x01)])
    assert mode is not None
    assert mode.key == "brom"


def test_adb_pid_range_is_covered():
    for pid in range(0x4EE0, 0x4EE9):
        mode = device_db.identify(0x18D1, pid)
        assert mode is not None
        assert mode.key == "adb"


def test_vendor_name_falls_back_for_unknown_vendor():
    assert device_db.vendor_name(0x05C6) == "Qualcomm"
    assert "Unknown" in device_db.vendor_name(0xFFFF)


def test_describe_formats_vid_pid():
    assert device_db.describe(0x05C6, 0x9008) == "Qualcomm 0x05c6:0x9008"


def test_every_table_entry_is_well_formed():
    for (vendor_id, product_id), mode in device_db.USB_MODES.items():
        assert 0 <= vendor_id <= 0xFFFF
        assert 0 <= product_id <= 0xFFFF
        assert mode.key and mode.label and mode.soc_family and mode.transport
