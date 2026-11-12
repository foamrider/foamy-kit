#!/usr/bin/env python3
"""The shared test helpers plugins import from the kit checkout: FoamyWait
(harness/FoamyWait.qml: waitFor/after in qs), harness.wait_for and
Run.wait_for_log, and preview/hostenv.py (isolate, make with an
omarchy-shell that reaches only the test's own shell, calls, check,
fake_helper_plugin, ProcessGroup)."""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIXTURES, KIT_ROOT, harness, report  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import hostenv  # noqa: E402

WAIT = """import QtQuick
import Quickshell
import "harness"
ShellRoot {
  id: shell
  property bool flag: false
  property int failures: 0
  property var started: Date.now()
  function check(ok, label) { if (!ok) { failures++; console.log("FOAMY FAIL " + label) } }
  FoamyWait { id: wait; interval: 20 }
  Timer { interval: 300; running: true; onTriggered: shell.flag = true }
  Component.onCompleted: {
    var sync = true
    wait.waitFor(function() { return true }, 1000, function(ok) {
      check(!sync, "then() runs later, never inside waitFor()")
      check(ok, "an already-true condition passes")
    })
    sync = false
    check(wait.pending === 1, "pending counts the wait in flight: " + wait.pending)
    wait.waitFor(function() { return shell.flag }, 5000, function(ok) {
      var waited = Date.now() - shell.started
      check(ok && waited >= 250 && waited < 3000, "waits for the condition, not a fixed delay: " + ok + " " + waited + " ms")
      wait.waitFor(function() { return false }, 200, function(ok) {
        check(!ok && Date.now() - shell.started - waited >= 180, "a condition that never holds times out: " + ok)
        wait.waitFor(function() { throw new Error("boom") }, 100, function(ok) {
          check(!ok, "a throwing condition counts as false")
          wait.after(100, function() {
            check(wait.pending === 0, "no wait left pending: " + wait.pending)
            console.log("FOAMY RESULT failures=" + failures)
            if (Quickshell.env("FOAMY_LABELLED") === "1")
              wait.waitFor(function() { return false }, 100, function() { console.log("FOAMY DONE"); Qt.quit() }, "the labelled step")
            else { console.log("FOAMY DONE"); Qt.quit() }
          })
        })
      })
    })
  }
}
"""

IPC = """import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
  IpcHandler { target: "foamy.helpers"; function ping(word: string): string { return "pong " + word } }
  Timer { interval: 600; running: true; onTriggered: console.log("FOAMY UP") }
}
"""

# What a plugin's Process runs: a shell whose own child outlives the shell
# unless the whole process group goes.
GROUP_SHELL = """import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
  Process {
    running: true
    command: ["sh", "-c", "sleep 300 & echo $! > \\"$FOAMY_CHILD\\"; wait"]
  }
}
"""


def alive(pid):
    """True while `pid` runs (a zombie counts as gone)."""
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    # ProcessLookupError: it went between open() and read().
    except (FileNotFoundError, ProcessLookupError, IndexError):
        return False


def child_pid(file, timeout=20):
    text = harness.wait_for(lambda: file.read_text().strip() if file.exists() else "", timeout)
    return int(text) if text else None


def process_group(base):
    """hostenv.ProcessGroup against a qs the test starts itself, and its
    lifecycle on plain shells."""
    ok = True
    app = base / "group-app"
    app.mkdir()
    (app / "shell.qml").write_text(GROUP_SHELL)
    runtime = base / "group-runtime"
    runtime.mkdir(mode=0o700)
    env = hostenv.isolate(dict(os.environ), base)
    env.update(
        QT_QPA_PLATFORM="offscreen",
        QT_QPA_PLATFORMTHEME="basic",
        QT_QUICK_BACKEND="software",
        XDG_RUNTIME_DIR=str(runtime),
        XDG_STATE_HOME=str(base / "group-state"),
        XDG_CACHE_HOME=str(base / "group-cache"),
    )
    qs = ["qs", "-p", str(app), "--no-color"]

    # Why: stopping only qs leaves what its Process started running.
    env["FOAMY_CHILD"] = str(base / "child-plain")
    plain = subprocess.Popen(qs, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pid = child_pid(base / "child-plain")
    plain.terminate()
    plain.wait(10)
    left = pid is not None and harness.wait_for(lambda: not alive(pid), 1) is None
    ok &= report("stopping only qs leaves its Process's child running (why ProcessGroup exists)", left, str(pid))
    if pid is not None and alive(pid):
        os.kill(pid, signal.SIGKILL)

    env["FOAMY_CHILD"] = str(base / "child-group")
    with hostenv.ProcessGroup(qs, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as shell:
        pid = child_pid(base / "child-group")
        running = shell.wait(0.2) is None
    gone = pid is not None and harness.wait_for(lambda: not alive(pid), 5) is not None
    ok &= report("ProcessGroup.stop() takes qs's Process children with it", running and gone, f"child {pid}")

    # A group that ignores SIGTERM (its leader too) gets SIGKILL after the
    # grace period.
    marker = base / "stubborn"
    group = hostenv.ProcessGroup(["sh", "-c", f"trap '' TERM; sleep 300 & echo $! > {marker}; wait"])
    pid = child_pid(marker, 10)
    started = time.monotonic()
    status = group.stop(grace=0.5)
    elapsed = time.monotonic() - started
    ok &= report(
        "a group that ignores SIGTERM is killed after the grace period",
        pid is not None
        and status == -signal.SIGKILL
        and 0.4 <= elapsed < 5
        and harness.wait_for(lambda: not alive(pid), 5) is not None,
        f"status {status}, {elapsed:.1f}s",
    )
    ok &= report("stop() is idempotent and returns the leader's status", group.stop() == status)

    # A leader that exits by itself leaves its child in the group: stop()
    # still reaches it (the leader stays unreaped until then, so the group
    # id can't be reused).
    marker = base / "orphan"
    group = hostenv.ProcessGroup(["sh", "-c", f"sleep 300 & echo $! > {marker}"])
    pid = child_pid(marker, 10)
    exited = group.wait(10)
    group.stop()
    ok &= report(
        "wait() reports the leader's exit; stop() then kills the child it left",
        exited == 0 and pid is not None and harness.wait_for(lambda: not alive(pid), 5) is not None,
        f"exit {exited}, child {pid}",
    )
    return ok


def main():
    harness.install_signal_cleanup()
    ok = True

    # FoamyWait in qs.
    run = harness.Run("4.5", WAIT, prefix="foamy-kit-wait-")
    run.run(timeout=30)
    result = next((line.split("qml: ", 1)[-1] for line in run.log.splitlines() if "FOAMY RESULT" in line), "no result")
    ok &= report("FoamyWait.waitFor/after: later, condition-driven, timeouts, throws, pending", run.ok, result)
    if not run.ok:
        print("\n".join("    " + line for line in run.failures() or run.log.splitlines()[-20:]))
    run.cleanup()
    run = harness.Run("4.5", WAIT, prefix="foamy-kit-wait-")
    run.env["FOAMY_LABELLED"] = "1"
    run.run(timeout=30)
    ok &= report(
        "a labelled waitFor that times out fails the run",
        not run.ok and "FOAMY FAIL the labelled step: not true after 100 ms" in run.log and "FOAMY DONE" in run.log,
        "; ".join(run.failures()),
    )
    run.cleanup()

    # harness.wait_for.
    start = time.monotonic()
    value = harness.wait_for(lambda: time.monotonic() - start > 0.2 and "ready", timeout=5)
    waited = time.monotonic() - start
    ok &= report(
        "wait_for returns the condition's value once it holds",
        value == "ready" and 0.2 <= waited < 2,
        f"{value} {waited:.2f}s",
    )
    start = time.monotonic()
    value = harness.wait_for(lambda: False, timeout=0.3)
    ok &= report("wait_for gives None after its timeout", value is None and 0.3 <= time.monotonic() - start < 2)
    start = time.monotonic()
    value = harness.wait_for(lambda: False, timeout=10, stop=lambda: time.monotonic() - start > 0.2)
    ok &= report("wait_for ends early when stop() holds", value is None and time.monotonic() - start < 2)

    # hostenv: isolate().
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-hostenv-test-"))
    saved = dict(os.environ)
    try:
        appdir = base / "app"
        os.environ.update({"APPDIR": str(appdir), "OMARCHY_PATH": "/usr/share/omarchy"})
        env = hostenv.isolate(
            {
                "PATH": f"{appdir}/usr/bin:/usr/share/omarchy/bin:/usr/bin",
                "LD_LIBRARY_PATH": f"{appdir}/usr/lib",
                "PULSE_SERVER": "unix:/run/user/1000/pulse/native",
                "PIPEWIRE_RUNTIME_DIR": "/run/user/1000",
            },
            base,
        )
        ok &= report(
            "isolate() drops host bins and $APPDIR, names no audio server or system bus",
            env["PATH"] == "/usr/bin"
            and "LD_LIBRARY_PATH" not in env
            and env["PULSE_SERVER"] == f"unix:{base}/no-pulse"
            and env["PIPEWIRE_REMOTE"] == f"{base}/no-pipewire"
            and "PIPEWIRE_RUNTIME_DIR" not in env
            and env["DBUS_SYSTEM_BUS_ADDRESS"] == f"unix:path={base}/no-system-bus",
            str(env),
        )
        # The desktop's session bus and display stay out unless the test
        # names its own bus or asks for the display.
        live = {
            "PATH": "/usr/bin",
            "DBUS_SESSION_BUS_ADDRESS": os.environ.get("DBUS_SESSION_BUS_ADDRESS") or "unix:path=/run/user/1000/bus",
            "WAYLAND_DISPLAY": "wayland-1",
            "HYPRLAND_INSTANCE_SIGNATURE": "abc",
            "DISPLAY": ":0",
        }
        env = hostenv.isolate(dict(live), base)
        ok &= report(
            "isolate() names a dead session bus and drops the display by default",
            env["DBUS_SESSION_BUS_ADDRESS"] == f"unix:path={base}/no-session-bus"
            and not {"WAYLAND_DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "DISPLAY"} & set(env),
            str({k: env.get(k) for k in live}),
        )
        reach = subprocess.run(
            ["dbus-send", "--session", "--print-reply", "--dest=org.freedesktop.DBus", "/org/freedesktop/DBus"]
            + ["org.freedesktop.DBus.ListNames"],
            env=env,
            capture_output=True,
            timeout=10,
        )
        ok &= report(
            "a process with that environment reaches no session bus", reach.returncode != 0, str(reach.returncode)
        )
        unset = hostenv.isolate({"PATH": "/usr/bin"}, base)
        ok &= report(
            "an unset session bus becomes the dead address too (no fallback to the login bus)",
            unset["DBUS_SESSION_BUS_ADDRESS"] == f"unix:path={base}/no-session-bus",
        )
        own = hostenv.isolate(dict(live), base, session_bus="unix:path=/tmp/test-bus", display=True)
        ok &= report(
            "session_bus= and display=True keep what the test chose",
            own["DBUS_SESSION_BUS_ADDRESS"] == "unix:path=/tmp/test-bus"
            and all(own.get(k) == live[k] for k in ("WAYLAND_DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "DISPLAY")),
            str({k: own.get(k) for k in live}),
        )
        try:
            hostenv.isolate(dict(live), base, session_bus="tcp:host=localhost,port=1")
            refused = False
        except ValueError:
            refused = True
        ok &= report("a session_bus that isn't a unix: address is refused", refused)
        ok &= report(
            "library_path() keeps entries outside $APPDIR",
            hostenv.library_path(f"{appdir}/usr/lib:{appdir}x/lib:/opt/lib") == f"{appdir}x/lib:/opt/lib",
        )
    finally:
        os.environ.clear()
        os.environ.update(saved)

    # hostenv: make(), calls() and check() against a real harness run.
    run = harness.Run("4.5", IPC, prefix="foamy-kit-hostenv-")
    try:
        run.start()
        up = run.wait_for_log("FOAMY UP", timeout=20)
        ok &= report("Run.wait_for_log sees the shell's line", up)
        overrides = hostenv.make(
            base / "host",
            run.root,
            env=run.env,
            stubs={"omarchy-extra": hostenv.logging_stub(base / "extra.log")},
            names=("omarchy-test-only",),
        )
        env = {**run.env, **overrides}
        stub_dir = Path(overrides["PATH"].split(":")[0])
        ok &= report(
            "make(): a private OMARCHY_PATH whose bin/ and PATH stubs come first",
            overrides["OMARCHY_PATH"] == str(base / "host/omarchy-host")
            and (Path(overrides["OMARCHY_PATH"]) / "shell/Commons").is_dir()
            and (Path(overrides["OMARCHY_PATH"]) / "bin/omarchy-test-only").is_file()
            and {"omarchy-shell", "omarchy-test-only", "omarchy-extra", "omarchy-plugin-validate"}
            <= set(os.listdir(stub_dir)),
            overrides["PATH"].split(":")[0],
        )
        answer = subprocess.run(
            ["omarchy-shell", "foamy.helpers", "ping", "kit"], env=env, capture_output=True, text=True, timeout=20
        )
        ok &= report(
            "the omarchy-shell stub reaches the test's own shell only",
            answer.stdout.strip() == "pong kit",
            (answer.stdout + answer.stderr).strip()[:200],
        )
        plain = subprocess.run(
            ["omarchy-plugin-validate", "/nowhere"], env=env, capture_output=True, text=True, timeout=10
        )
        logged = hostenv.calls(base / "host")
        ok &= report(
            "other stubs log and succeed; calls() lists them",
            plain.returncode == 0
            and any(line.endswith("omarchy-shell foamy.helpers ping kit") for line in logged)
            and any(line.endswith("omarchy-plugin-validate /nowhere") for line in logged),
            str(logged),
        )
        try:
            hostenv.check(env, answer.stdout, *logged)
            checked = True
        except AssertionError:
            checked = False
        ok &= report("check() passes for the stubbed environment", checked)
        failures = 0
        for bad_env, outputs in (
            ({**env, "PATH": "/usr/share/omarchy/bin:" + env["PATH"]}, ()),
            (env, ("ran /usr/share/omarchy/bin/omarchy-shell",)),
        ):
            try:
                hostenv.check(bad_env, *outputs)
            except AssertionError:
                failures += 1
        ok &= report("check() fails when a host bin is on PATH or a host script ran", failures == 2)
    finally:
        run.cleanup()

    # hostenv: ProcessGroup().
    ok &= process_group(base)

    # hostenv: fake_helper_plugin().
    demo = base / "demo-src"
    shutil.copytree(FIXTURES / "demo-plugin", demo)
    (demo / ".git").mkdir()
    (demo / "tests").mkdir(exist_ok=True)
    plugin = hostenv.fake_helper_plugin(demo, base / "fake-plugin", "foamy-demo-helper", '#!/bin/sh\necho fake "$@"\n')
    launched = subprocess.run(
        [
            "bash",
            "-c",
            'exec -- "$1/bin/$HOSTTYPE/$2" "${@:3}"',
            "foamy-native",
            str(plugin),
            "foamy-demo-helper",
            "status",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    ok &= report(
        "fake_helper_plugin(): the copy's bundled helper is the script, for both arches",
        launched.stdout.strip() == "fake status"
        and all(os.access(plugin / "bin" / a / "foamy-demo-helper", os.X_OK) for a in hostenv.ARCHES)
        and (plugin / "manifest.json").is_file()
        and not (plugin / ".git").exists()
        and not (plugin / "tests").exists(),
        launched.stdout + launched.stderr,
    )
    shutil.rmtree(base, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
