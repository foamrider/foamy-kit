#!/usr/bin/env python3
"""What a harness run's processes can reach, from inside qs: no Omarchy bin
directory or omarchy command (a stub refuses and logs it; a fakebin wins),
no AppImage libraries or binaries ($APPDIR), no audio server, no system bus
by default (system_bus="private" and an explicit address opt in), and the
private session bus. The caller's environment names all of them."""

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import harness, report  # noqa: E402

SHELL = """import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
  Process {
    running: true
    command: ["sh", "-c", Quickshell.env("FOAMY_PROBE")]
    onExited: { console.log("FOAMY DONE"); Qt.quit() }
  }
}
"""

PROBE = r"""{
echo "LD=${LD_LIBRARY_PATH-unset}"
echo "PATH=$PATH"
echo "PULSE=$PULSE_SERVER"
echo "PIPEWIRE=$PIPEWIRE_REMOTE"
echo "SYSTEM=$DBUS_SYSTEM_BUS_ADDRESS"
echo "SESSION=$DBUS_SESSION_BUS_ADDRESS"
omarchy bar set foamy.probe key 1 --json; echo "omarchy=$?"
omarchy-probe-tool; echo "omarchy-probe-tool=$?"
omarchy-shell shell ping; echo "omarchy-shell=$?"
appimage-tool; echo "appimage-tool=$?"
dbus-send --system --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames >/dev/null 2>&1
echo "system-bus=$?"
dbus-send --session --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames >/dev/null 2>&1
echo "session-bus=$?"
} > "$FOAMY_OUT/probe.txt" 2>&1
"""


def probe(**options):
    run = harness.Run("4.5", SHELL, prefix="foamy-kit-isolation-", **options)
    run.env["FOAMY_PROBE"] = PROBE
    run.run(timeout=30)
    path = run.out / "probe.txt"
    lines = path.read_text(errors="replace").splitlines() if path.exists() else []
    values = dict(line.split("=", 1) for line in lines if "=" in line and not line.startswith(" "))
    return run, values, lines


def main():
    ok = True
    work = Path(tempfile.mkdtemp(prefix="foamy-kit-isolation-test-"))
    saved = dict(os.environ)
    try:
        # A caller environment that names everything a test must not reach.
        appdir = work / "appimage"
        (appdir / "usr/lib").mkdir(parents=True)
        (appdir / "usr/bin").mkdir()
        user_bin = work / "user-bin"
        user_bin.mkdir()
        omarchy_tree = work / "omarchy"
        (omarchy_tree / "bin").mkdir(parents=True)
        marker = work / "a host command ran"
        for folder, name in (
            (appdir / "usr/bin", "appimage-tool"),
            (user_bin, "omarchy"),
            (omarchy_tree / "bin", "omarchy-probe-tool"),
        ):
            (folder / name).write_text(f"#!/bin/sh\necho {name} >> '{marker}'\n")
            (folder / name).chmod(0o755)
        os.environ.update(
            {
                "APPDIR": str(appdir),
                "LD_LIBRARY_PATH": f"{appdir}/usr/lib:{work}/keep-lib",
                "PATH": f"{appdir}/usr/bin:{user_bin}:{omarchy_tree}/bin:/usr/share/omarchy/bin:{saved.get('PATH', '/usr/bin:/bin')}",
                "OMARCHY_PATH": str(omarchy_tree),
                "PULSE_SERVER": "unix:/run/user/%d/pulse/native" % os.getuid(),
                "PIPEWIRE_REMOTE": "pipewire-0",
                "DBUS_SYSTEM_BUS_ADDRESS": "unix:path=/run/dbus/system_bus_socket",
            }
        )

        run, got, lines = probe()
        detail = "; ".join(line for line in lines if not line.startswith("PATH="))[:600] or run.log[-400:]
        path = got.get("PATH", "").split(":")
        ok &= report("qs ran the probe", "session-bus" in got, detail)
        ok &= report(
            "an AppImage's libraries leave LD_LIBRARY_PATH, other entries stay",
            got.get("LD") == f"{work}/keep-lib",
            got.get("LD", ""),
        )
        dropped = {os.path.realpath("/usr/share/omarchy/bin"), str(omarchy_tree / "bin"), str(appdir / "usr/bin")}
        ok &= report(
            "Omarchy's bin dirs and the AppImage's leave PATH",
            bool(path) and not any(os.path.realpath(p) in dropped for p in path if p),
            ", ".join(p for p in path if os.path.realpath(p) in dropped),
        )
        ok &= report(
            "no host command ran (omarchy shadowed, omarchy-* and the AppImage tool gone)",
            not marker.exists()
            and got.get("omarchy") == "127"
            and got.get("omarchy-probe-tool") == "127"
            and got.get("omarchy-shell") == "127"
            and got.get("appimage-tool") == "127",
            marker.read_text().strip() if marker.exists() else detail,
        )
        # omarchy-shell is also in /usr/bin on Omarchy: shadowed and logged there.
        ok &= report(
            "the refused host commands are logged",
            run.host_commands()[:1] == ["omarchy bar set foamy.probe key 1 --json"]
            and set(run.host_commands()) <= {"omarchy bar set foamy.probe key 1 --json", "omarchy-shell shell ping"},
            str(run.host_commands()),
        )
        ok &= report(
            "no audio server is named",
            got.get("PULSE", "").startswith(f"unix:{run.base}/") and got.get("PIPEWIRE", "").startswith(f"{run.base}/"),
            f"{got.get('PULSE')} {got.get('PIPEWIRE')}",
        )
        ok &= report(
            "the system bus is a dead address by default",
            got.get("SYSTEM") == f"unix:path={run.base}/no-system-bus" and got.get("system-bus") not in (None, "0"),
            f"{got.get('SYSTEM')} exit {got.get('system-bus')}",
        )
        ok &= report(
            "the session bus is the run's private one",
            got.get("SESSION") == f"unix:path={run.sockets}/bus" and got.get("session-bus") == "0",
            f"{got.get('SESSION')} exit {got.get('session-bus')}",
        )
        run.cleanup()

        fake = '#!/bin/sh\necho "fake $*" >> "$FOAMY_OUT/fake.log"\nexit 0\n'
        run, got, lines = probe(system_bus="private", fakebin={"omarchy": fake})
        ok &= report(
            "system_bus='private' gives the run its own system bus",
            got.get("SYSTEM") == f"unix:path={run.sockets}/system-bus"
            and got.get("system-bus") == "0"
            and run.system_bus_address == got.get("SYSTEM"),
            f"{got.get('SYSTEM')} exit {got.get('system-bus')}",
        )
        ok &= report(
            "a fakebin stand-in wins over the host-command stub",
            got.get("omarchy") == "0"
            and not any(c.startswith("omarchy ") for c in run.host_commands())
            and (run.out / "fake.log").is_file(),
            f"exit {got.get('omarchy')}, host calls {run.host_commands()}",
        )
        run.cleanup()
        ok &= report(
            "the private system bus stops with the run",
            not harness.processes_under(run.base),
            str(harness.processes_under(run.base)),
        )

        run, got, lines = probe(system_bus="unix:path=/nonexistent/foamy-test-bus")
        ok &= report(
            "an explicit system bus address is used as given",
            got.get("SYSTEM") == "unix:path=/nonexistent/foamy-test-bus",
            got.get("SYSTEM", ""),
        )
        run.cleanup()
        try:
            harness.Run("4.5", SHELL, system_bus="host")
            refused = False
        except ValueError:
            refused = True
        ok &= report("an unknown system_bus value is refused", refused)
    finally:
        os.environ.clear()
        os.environ.update(saved)
        shutil.rmtree(work, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
