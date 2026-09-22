"""ProtocolRegistry routing tests."""

from __future__ import annotations

from mobi_tool.core.mock_devices import MOCK_DEVICES
from mobi_tool.protocols import DeviceProtocol, ProtocolRegistry


class FakeEdl(DeviceProtocol):
    transport = "sahara+firehose"
    name = "Fake EDL"

    def can_handle(self, device):
        return device.mode is not None and device.mode.transport == self.transport

    def capabilities(self):
        return {"device.info"}


class Broken(DeviceProtocol):
    transport = "broken"

    def can_handle(self, device):
        raise RuntimeError("driver bug")

    def capabilities(self):
        return set()


class CatchAll(DeviceProtocol):
    transport = "any"

    def can_handle(self, device):
        return True

    def capabilities(self):
        return set()


def test_registry_routes_by_transport():
    registry = ProtocolRegistry()
    registry.register(FakeEdl())

    matched = registry.resolve(MOCK_DEVICES[0])
    assert matched is not None
    assert matched.name == "Fake EDL"
    assert registry.resolve(MOCK_DEVICES[1]) is None


def test_registry_survives_a_broken_driver():
    registry = ProtocolRegistry()
    registry.register(Broken())
    registry.register(CatchAll())
    assert registry.resolve(MOCK_DEVICES[0]) is not None


def test_supported_transports_skips_blanks():
    registry = ProtocolRegistry()
    registry.register(FakeEdl())
    registry.register(CatchAll())
    assert registry.supported_transports() == {"sahara+firehose", "any"}


def test_empty_registry_resolves_to_none():
    assert ProtocolRegistry().resolve(MOCK_DEVICES[0]) is None


def test_drivers_property_returns_a_copy():
    registry = ProtocolRegistry()
    registry.register(FakeEdl())
    registry.drivers.clear()
    assert len(registry.drivers) == 1
