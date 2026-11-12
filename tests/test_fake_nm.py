#!/usr/bin/env python3
"""preview/fake_nm.py, the shared stand-in NetworkManager: on a run's
private system bus Quickshell's Networking reads its connectivity, follows
the state file down and up, and the service stops with its group. A bus
that isn't there fails start() with the reason."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import fake_nm  # noqa: E402

SHELL = """import QtQuick
import Quickshell
import Quickshell.Networking
ShellRoot {
  readonly property int connectivity: Networking.connectivity
  function name(value) {
    return value === NetworkConnectivity.Full ? "full" : value === NetworkConnectivity.None ? "none" : value === NetworkConnectivity.Portal ? "portal" : "other-" + value
  }
  onConnectivityChanged: console.log("FOAMY NM " + name(connectivity))
  Component.onCompleted: console.log("FOAMY NM " + name(connectivity) + " (start)")
}
"""


def main():
    ok = True
    run = harness.Run("4.5", SHELL, prefix="foamy-kit-fake-nm-", system_bus="private")
    state = run.base / "connectivity"
    try:
        # Quickshell looks for NetworkManager once, when it starts.
        run.start_buses()
        with fake_nm.start(run.system_bus_address, state) as service:
            run.start()
            full = run.wait_for_log("FOAMY NM full", 20)
            fake_nm.set_connectivity(state, fake_nm.NONE)
            offline = run.wait_for_log("FOAMY NM none", 20)
            fake_nm.set_connectivity(state, fake_nm.PORTAL)
            portal = run.wait_for_log("FOAMY NM portal", 20)
            fake_nm.set_connectivity(state, fake_nm.FULL)
            back = harness.wait_for(lambda: (run.base / "qs.log").read_text().count("FOAMY NM full") >= 2, 20)
            running = service.exit_status() is None
        pid = service.pid
    finally:
        run.stop()
    lines = [line.split("qml: ", 1)[-1] for line in run.log.splitlines() if "FOAMY NM" in line]
    ok &= report(
        "Networking.connectivity reads the fake: full, then none, portal and full again from the state file",
        bool(full and offline and portal and back and running),
        "; ".join(lines) or run.log[-600:],
    )
    ok &= report("the service stops with its group", not Path(f"/proc/{pid}").exists(), str(pid))
    run.cleanup()

    try:
        fake_nm.set_connectivity(Path(tempfile.gettempdir()) / "unused", 7)
        refused = False
    except ValueError:
        refused = True
    ok &= report("set_connectivity() refuses a value outside 0-4", refused)

    with tempfile.TemporaryDirectory(prefix="foamy-kit-fake-nm-") as work:
        try:
            fake_nm.start(f"unix:path={work}/no-bus", Path(work) / "state", timeout=10)
            message = "started"
        except RuntimeError as error:
            message = str(error)
    ok &= report(
        "start() on a bus that isn't there fails with the service's error", "did not start" in message, message[-300:]
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
