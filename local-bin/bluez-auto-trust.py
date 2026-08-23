#!/usr/bin/env python3
import logging

from gi.repository import GLib, Gio

BLUEZ = "org.bluez"
ROOT = "/"
DM_IFACE = "org.freedesktop.DBus.ObjectManager"
PROPS_IFACE = "org.freedesktop.DBus.Properties"
DEVICE_IFACE = "org.bluez.Device1"
BUS_TYPE = Gio.BusType.SYSTEM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s bluez-auto-trust: %(message)s",
    datefmt="%H:%M:%S",
)


class AutoTrust:
    def __init__(self, bus):
        self.bus = bus

    def start(self):
        self._subscribe(BLUEZ, DM_IFACE, "InterfacesAdded", ROOT, self.on_interfaces_added)
        self._subscribe(BLUEZ, PROPS_IFACE, "PropertiesChanged", None, self.on_properties_changed)
        for device_path in self.list_devices():
            self.check_and_trust(device_path)

    def _subscribe(self, name, iface, member, path, callback):
        self.bus.signal_subscribe(
            name, iface, member, path, None, Gio.DBusSignalFlags.NONE, callback
        )

    def list_devices(self):
        try:
            result = self.bus.call_sync(
                BLUEZ,
                ROOT,
                DM_IFACE,
                "GetManagedObjects",
                None,
                GLib.VariantType("(a{oa{sa{sv}}})"),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
        except GLib.Error as e:
            logging.error("GetManagedObjects failed: %s", e)
            return []
        return [
            obj_path
            for obj_path, interfaces in result.unpack()[0].items()
            if DEVICE_IFACE in interfaces
        ]

    def on_interfaces_added(self, bus, sender, path, iface, signal, params):
        obj_path, interfaces = params.unpack()
        if DEVICE_IFACE in interfaces:
            self.check_and_trust(obj_path)

    def on_properties_changed(self, bus, sender, path, iface, signal, params):
        object_iface, changed, invalidated = params.unpack()
        if object_iface == DEVICE_IFACE and changed.get("Paired") is True:
            self.check_and_trust(path)

    def check_and_trust(self, device_path):
        if not self.read_property(device_path, "Paired"):
            return
        if self.read_property(device_path, "Trusted"):
            return
        alias = self.read_property(device_path, "Alias") or device_path
        if self.set_property(device_path, "Trusted", GLib.Variant("b", True)):
            logging.info("Trusted %s (%s)", alias, device_path)

    def read_property(self, device_path, prop):
        try:
            result = self.bus.call_sync(
                BLUEZ,
                device_path,
                PROPS_IFACE,
                "Get",
                GLib.Variant("(ss)", (DEVICE_IFACE, prop)),
                GLib.VariantType("(v)"),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
            return result.unpack()[0]
        except GLib.Error as e:
            logging.warning("Get %s %s failed: %s", device_path, prop, e)
            return None

    def set_property(self, device_path, prop, value):
        try:
            self.bus.call_sync(
                BLUEZ,
                device_path,
                PROPS_IFACE,
                "Set",
                GLib.Variant("(ssv)", (DEVICE_IFACE, prop, value)),
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
            return True
        except GLib.Error as e:
            logging.error("Set %s %s failed: %s", device_path, prop, e)
            return False


def main():
    bus = Gio.bus_get_sync(BUS_TYPE, None)
    agent = AutoTrust(bus)
    agent.start()
    logging.info("Agent running")
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()