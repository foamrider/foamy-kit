#!/usr/bin/env python3
"""A stand-in NetworkManager for plugin runtime tests, on a run's private
system bus (`harness.Run(…, system_bus="private")`).

Quickshell's `Networking` (`Networking.connectivity`) reads only this
object. The fake owns org.freedesktop.NetworkManager with no devices and the
connectivity a state file names (NetworkManager's NMConnectivityState: 4
full, 3 limited, 2 portal, 1 none, 0 unknown; 4 when the file is missing,
the last value while it is empty or invalid). It re-reads the file every
100 ms and sends PropertiesChanged when the value changes, so a test takes
the network down and up by writing the file, with set_connectivity() (an
atomic replace).

The fake changes only what the shell sees. It does not cut a helper off
from the Internet: point the plugin's helpers at a loopback stand-in and
fail on any outside request (README, "Test helpers for plugins").

  import fake_nm
  run = harness.Run(host, shell, plugin=plugin, system_bus="private")
  state = run.base / "connectivity"
  run.start_buses()                                    # the fake goes on the bus before qs:
  with fake_nm.start(run.system_bus_address, state):   # Quickshell looks for NetworkManager
      run.start()                                      # once, at start
      fake_nm.set_connectivity(state, fake_nm.NONE)    # offline
      …
  run.stop()

The service runs in its own process group (hostenv.ProcessGroup), killed
with the `with` block (or `.stop()`). From the command line:
`python3 fake_nm.py <bus address> <state file>`; it prints "FAKE NM READY"
once it owns the name. It needs dbus-python and PyGObject (the system's).
Based on foamy-github's tests/fake_nm.py.
"""

import os
import select
import subprocess
import sys
import tempfile
import time
from pathlib import Path

NAME = "org.freedesktop.NetworkManager"
PATH = "/org/freedesktop/NetworkManager"
READY = "FAKE NM READY"
OUTPUT_LIMIT = 8192
UNKNOWN, NONE, PORTAL, LIMITED, FULL = range(5)


def connectivity(file, last):
    """The connectivity the state file names: FULL when it is missing, `last`
    (the value the service reports now) when it is empty, unreadable or not
    0-4. A test that writes the file in place leaves it empty or half
    written for a moment; that must not look like a change (to FULL, online)."""
    try:
        text = Path(file).read_text()
    except FileNotFoundError:
        return FULL
    except (OSError, UnicodeDecodeError):
        return last
    try:
        value = int(text.strip())
    except ValueError:
        return last
    return value if UNKNOWN <= value <= FULL else last


def set_connectivity(file, value):
    """Write `value` (UNKNOWN…FULL) to the state file in one step (a unique
    temporary file beside it, then rename), so the service never reads half
    a write."""
    if value not in range(UNKNOWN, FULL + 1):
        raise ValueError(f"connectivity must be 0-4, not {value!r}")
    file = Path(file)
    fd, partial = tempfile.mkstemp(dir=file.parent, prefix=f".{file.name}.")
    try:
        with os.fdopen(fd, "w") as out:
            out.write(f"{value}\n")
        os.replace(partial, file)
    except BaseException:
        Path(partial).unlink(missing_ok=True)
        raise


def _load_hostenv():
    import importlib.util

    module = sys.modules.get("foamy_kit_hostenv")
    if module is None:
        spec = importlib.util.spec_from_file_location("foamy_kit_hostenv", Path(__file__).with_name("hostenv.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules["foamy_kit_hostenv"] = module
        spec.loader.exec_module(module)
    return module


def start(address, state_file, timeout=10):
    """Start the fake on the bus at `address` and return its
    hostenv.ProcessGroup once it owns the name. Raises RuntimeError (with
    the service's output) when it exits or isn't ready within `timeout`
    seconds; it is stopped first."""
    hostenv = _load_hostenv()
    group = hostenv.ProcessGroup(
        [sys.executable, "-I", str(Path(__file__).resolve()), str(address), str(state_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    # Until READY: a start-up error is the output, a hung start ends at the
    # deadline, and at most OUTPUT_LIMIT bytes are kept.
    output = b""
    deadline = time.monotonic() + timeout
    fd = group.process.stdout.fileno()
    while READY.encode() not in output:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            break
        chunk = os.read(fd, 4096)
        if not chunk:
            break
        output = (output + chunk)[-OUTPUT_LIMIT:]
    if READY.encode() in output:
        return group
    group.stop()
    text = output.decode(errors="replace").strip()
    raise RuntimeError(f"fake NetworkManager did not start on {address} within {timeout} s: {text or 'no output'}")


def main():
    import dbus
    import dbus.mainloop.glib
    import dbus.service
    from gi.repository import GLib

    class NetworkManager(dbus.service.Object):
        def __init__(self, name, file):
            # The object keeps the BusName (and so the name) referenced.
            super().__init__(bus_name=name, object_path=PATH)
            self.file = file
            self.value = connectivity(file, FULL)

        def properties(self):
            # 70: NM_STATE_CONNECTED_GLOBAL, 60: CONNECTED_SITE, 50:
            # CONNECTED_LOCAL, 20: DISCONNECTED, 0: UNKNOWN.
            state = {FULL: 70, LIMITED: 60, PORTAL: 60, NONE: 20}.get(self.value, 0)
            return {
                "Connectivity": dbus.UInt32(self.value),
                "State": dbus.UInt32(state),
                "Devices": dbus.Array([], signature="o"),
                "AllDevices": dbus.Array([], signature="o"),
                "ActiveConnections": dbus.Array([], signature="o"),
                "PrimaryConnection": dbus.ObjectPath("/"),
                "NetworkingEnabled": True,
                "WirelessEnabled": False,
                "WirelessHardwareEnabled": False,
                "ConnectivityCheckAvailable": True,
                "ConnectivityCheckEnabled": True,
                "Version": "1.50.0",
            }

        @dbus.service.method(NAME, out_signature="ao")
        def GetDevices(self):
            return dbus.Array([], signature="o")

        @dbus.service.method(NAME, out_signature="ao")
        def GetAllDevices(self):
            return dbus.Array([], signature="o")

        @dbus.service.method(NAME, out_signature="u")
        def CheckConnectivity(self):
            return dbus.UInt32(self.value)

        @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="ss", out_signature="v")
        def Get(self, interface, name):
            return self.properties()[name]

        @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="s", out_signature="a{sv}")
        def GetAll(self, interface):
            return self.properties() if interface == NAME else {}

        @dbus.service.signal(dbus.PROPERTIES_IFACE, signature="sa{sv}as")
        def PropertiesChanged(self, interface, changed, _invalidated):
            pass

        def poll(self):
            value = connectivity(self.file, self.value)
            if value != self.value:
                self.value = value
                props = self.properties()
                self.PropertiesChanged(NAME, {k: props[k] for k in ("Connectivity", "State")}, [])
            return True

    if len(sys.argv) != 3:
        print("usage: fake_nm.py <bus address> <state file>", file=sys.stderr)
        return 2
    address, file = sys.argv[1:3]
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.bus.BusConnection(address)
    manager = NetworkManager(dbus.service.BusName(NAME, bus, do_not_queue=True), file)
    GLib.timeout_add(100, manager.poll)
    print(READY, flush=True)
    GLib.MainLoop().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
