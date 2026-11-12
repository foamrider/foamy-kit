#!/usr/bin/env python3
"""The harness never leaks: a timed-out run and a killed parent leave no qs or
dbus-daemon behind, and cleanup removes the temp dir."""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report  # noqa: E402

HANG = """import QtQuick
import Quickshell
ShellRoot { Component.onCompleted: console.log("FOAMY UP") }
"""

CHILD = f"""
import sys, time
sys.path.insert(0, {str(KIT_ROOT / "preview")!r})
import harness
run = harness.Run("4.5", {HANG!r}, prefix="foamy-kit-orphan-")
run.start()
print(run.base, flush=True)
print(run.sockets, flush=True)
time.sleep(120)
"""


def gone(base, seconds=5):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if not harness.processes_under(base):
            return True
        time.sleep(0.1)
    return False


def ipc_reachable(run):
    """The instance id once qs's IPC socket answers `qs ipc show`, else None."""
    by_id = Path(run.env["XDG_RUNTIME_DIR"]) / "quickshell/by-id"
    if not run.wait_for_log("FOAMY UP", 30):
        return None
    sockets = harness.wait_for(lambda: sorted(by_id.glob("*/ipc.sock")), 10)
    if not sockets:
        return None
    instance = sockets[0].parent.name
    shown = subprocess.run(
        ["qs", "ipc", "-i", instance, "show"], env=run.env, capture_output=True, text=True, timeout=10
    )
    return instance if shown.returncode == 0 else None


def long_tmpdir():
    ok = True
    parent = Path(tempfile.mkdtemp(prefix="foamy-kit-long-tmp-"))
    long_tmp = parent / ("t" * (harness.SOCKET_PATH_MAX - len(str(parent))))
    long_tmp.mkdir()
    saved = tempfile.tempdir
    tempfile.tempdir = str(long_tmp)
    try:
        run = harness.Run("4.5", HANG, prefix="foamy-kit-long-tmpdir-run-")
        try:
            run.start()
            instance = ipc_reachable(run)
        finally:
            run.stop()
        ok &= report(
            "a TMPDIR longer than the socket limit still gives qs a working IPC socket",
            run.base.parent == long_tmp and instance is not None and "Failed to start IPC server" not in run.log,
            f"TMPDIR {len(str(long_tmp))} bytes, runtime {run.env['XDG_RUNTIME_DIR']}, instance {instance}; "
            + "; ".join(run.log.splitlines()[-3:]),
        )
        run.cleanup()
        ok &= report(
            "cleanup removes the run's socket dir too",
            not Path(run.env["XDG_RUNTIME_DIR"]).exists() and not run.base.exists(),
        )
    finally:
        tempfile.tempdir = saved
        shutil.rmtree(parent, ignore_errors=True)

    # A runtime dir a test made too long stops start() with the reason,
    # before qs or a bus runs.
    run = harness.Run("4.5", HANG, prefix="foamy-kit-long-runtime-")
    run.env["XDG_RUNTIME_DIR"] = str(run.base / ("r" * harness.SOCKET_PATH_MAX))
    try:
        run.start()
        message = "started"
    except SystemExit as error:
        message = str(error)
    ok &= report(
        "start() refuses a runtime dir whose IPC socket path is too long",
        "past the unix limit of 107" in message and run.process is None and run.bus_process is None,
        message,
    )
    run.cleanup()

    # A socket limit no temp dir can meet: Run() stops with the reason and
    # leaves nothing behind.
    before = set(Path(tempfile.gettempdir()).glob("foamy-kit-*")) | set(Path("/tmp").glob("foamy-kit-s-*"))
    limit = harness.SOCKET_PATH_MAX
    harness.SOCKET_PATH_MAX = 40
    try:
        harness.Run("4.5", HANG, prefix="foamy-kit-no-socket-dir-")
        message = "constructed"
    except SystemExit as error:
        message = str(error)
    finally:
        harness.SOCKET_PATH_MAX = limit
    after = set(Path(tempfile.gettempdir()).glob("foamy-kit-*")) | set(Path("/tmp").glob("foamy-kit-s-*"))
    ok &= report(
        "Run() stops with the reason when no socket dir fits, creating nothing",
        "past the unix limit of 40" in message and after == before,
        f"{message}; new: {sorted(map(str, after - before))}",
    )

    # qs's own report of an unbindable socket fails a run.
    marker = harness.Run(
        "4.5",
        """import QtQuick
import Quickshell
ShellRoot { Component.onCompleted: { console.warn("Failed to start IPC server on path \\"x\\""); console.log("FOAMY DONE"); Qt.quit() } }
""",
        prefix="foamy-kit-ipc-marker-",
    ).run(timeout=20)
    ok &= report(
        '"Failed to start IPC server" fails the run',
        "FOAMY DONE" in marker.log
        and not marker.ok
        and any("Failed to start IPC server" in f for f in marker.failures()),
        "; ".join(marker.failures()),
    )
    marker.cleanup()
    return ok


def main():
    ok = True
    # 1. Timeout: the run is killed, its bus too, and cleanup removes the dir.
    run = harness.Run("4.5", HANG, prefix="foamy-kit-timeout-")
    base = run.base
    started = time.time()
    run.run(timeout=3)
    elapsed = time.time() - started
    ok &= report("a timed-out run returns on time", elapsed < 12 and "FOAMY UP" in run.log, f"{elapsed:.1f}s")
    ok &= report("a timed-out run leaves no qs or dbus-daemon", gone(base), str(harness.processes_under(base)))
    run.cleanup()
    ok &= report("cleanup removes the temp dir", not base.exists())

    # 2. The Python parent is SIGKILLed mid-run (no finally, no atexit).
    child = subprocess.Popen([sys.executable, "-I", "-c", CHILD], stdout=subprocess.PIPE, text=True)
    base = Path(child.stdout.readline().strip())
    sockets = child.stdout.readline().strip()
    time.sleep(1.5)
    alive_before = bool(harness.processes_under(base))
    child.send_signal(signal.SIGKILL)
    child.wait()
    ok &= report(
        "a killed parent takes qs and its bus with it",
        alive_before and gone(base),
        f"before={alive_before} after={harness.processes_under(base)}",
    )
    shutil.rmtree(base, ignore_errors=True)
    # Only a socket dir the child named: an empty line must not become ".".
    if Path(sockets).name.startswith("foamy-kit-s-"):
        shutil.rmtree(sockets, ignore_errors=True)

    # 3. Context manager.
    with harness.Run("4.5", HANG, prefix="foamy-kit-ctx-") as ctx:
        ctx.start()
        base = ctx.base
        time.sleep(1)
    ok &= report(
        "Run as a context manager stops and removes everything",
        gone(base) and not base.exists() and not ctx.sockets.exists(),
    )
    # 4. Temp-dir hygiene: own dir per run, PID-tagged, 0700; gc removes only dead runs' dirs.
    run = harness.Run("4.5", HANG, prefix="foamy-kit-hygiene-")
    mode = run.base.stat().st_mode & 0o777
    socket_mode = run.sockets.stat().st_mode & 0o777
    ok &= report(
        "each run owns a PID-tagged 0700 dir and socket dir",
        f"-{os.getpid()}-" in run.base.name
        and mode == 0o700
        and run.sockets.name.startswith(f"foamy-kit-s-{os.getpid()}-")
        and socket_mode == 0o700,
        f"{run.base.name} {oct(mode)} {run.sockets.name} {oct(socket_mode)}",
    )
    run.cleanup()
    tmp = Path(tempfile.mkdtemp(prefix="foamy-kit-gc-test-"))
    dead = subprocess.Popen(["true"])
    dead.wait()
    stale = tmp / f"foamy-kit-preview-4.5-{dead.pid}-abc123"
    mine = tmp / f"foamy-kit-preview-4.5-{os.getpid()}-def456"
    busy = tmp / f"foamy-kit-preview-4.5-{dead.pid}-busy99"
    legacy = tmp / "foamy-kit-preview-4.5-ky_80jw7"
    for path in (stale, mine, busy, legacy):
        path.mkdir()
    holder = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)", str(busy)])
    try:
        removed = harness.gc(tmp)
    finally:
        holder.kill()
        holder.wait()
    ok &= report(
        "gc removes only dead runs' dirs (not live, in use, or unknown)",
        removed == [stale] and mine.exists() and busy.exists() and legacy.exists() and not stale.exists(),
        str(removed),
    )
    shutil.rmtree(tmp, ignore_errors=True)
    # A long temp dir's runs keep their sockets in /tmp: gc looks there too.
    stale_sockets = Path(tempfile.mkdtemp(prefix=f"foamy-kit-s-{dead.pid}-", dir="/tmp"))
    try:
        found = harness.gc(dry_run=True)
    finally:
        shutil.rmtree(stale_sockets, ignore_errors=True)
    ok &= report("gc finds a dead run's socket dir in /tmp", stale_sockets in found, str(found))

    # 5. A long TMPDIR (an agent sandbox's) must not push qs's IPC socket
    # past the unix socket limit: qs then only logs "Failed to start IPC
    # server", and `qs ipc` finds no instance.
    ok &= long_tmpdir()

    # 6. Hosts: 4.5 only, the installed shell by default; 4.0 is retired with a clear message.
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]); import harness; "
        "print(sorted((k, str(v)) for k, v in harness.HOSTS.items())); "
        "print(harness.available_hosts(('4.0', '4.5'), require=False))\n"
        "try:\n    harness.Run('4.0', '')\nexcept SystemExit as error:\n    print('Run 4.0:', error)"
    )
    env = {k: v for k, v in os.environ.items() if k not in ("FOAMY_HOST_40", "FOAMY_HOST_45")}
    plain = subprocess.run(
        [sys.executable, "-I", "-c", probe, str(KIT_ROOT / "preview")], env=env, capture_output=True, text=True
    )
    retired = "Omarchy 4.0 is no longer supported (foamy-kit 0.9.0 tests 4.5 only"
    ok &= report(
        "4.5 defaults to /usr/share/omarchy/shell; a listed 4.0 prints SKIP and the 4.5 cases still run",
        plain.stdout.startswith("[('4.5', '/usr/share/omarchy/shell')]\n")
        and f"SKIP on 4.0: {retired}" in plain.stdout
        and "\n['4.5']\n" in plain.stdout,
        plain.stdout.strip().replace("\n", "; ") + plain.stderr[-300:],
    )
    ok &= report(
        "harness.Run('4.0') stops with the retirement message",
        f"Run 4.0: {retired}" in plain.stdout,
        "; ".join(plain.stdout.strip().splitlines()[-1:]),
    )
    fake = Path(tempfile.mkdtemp(prefix="foamy-kit-host-test-"))
    for name in ("40", "45"):
        (fake / name / "Commons").mkdir(parents=True)
        (fake / name / "Ui").mkdir()
    both = subprocess.run(
        [sys.executable, "-I", "-c", probe, str(KIT_ROOT / "preview")],
        capture_output=True,
        text=True,
        env={**env, "FOAMY_HOST_40": str(fake / "40"), "FOAMY_HOST_45": str(fake / "45")},
    )
    ok &= report(
        "FOAMY_HOST_45 overrides 4.5; FOAMY_HOST_40 is ignored",
        both.stdout.startswith(f"[('4.5', '{fake / '45'}')]\n")
        and "\n['4.5']\n" in both.stdout
        and f"SKIP on 4.0: {retired}" in both.stdout,
        both.stdout.strip().replace("\n", "; "),
    )
    shutil.rmtree(fake, ignore_errors=True)
    demo = KIT_ROOT / "tests/fixtures/demo-plugin"
    rendered = subprocess.run(
        [sys.executable, "-I", str(KIT_ROOT / "preview/render.py"), str(demo), "--host", "4.0"],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    ok &= report(
        "render.py --host 4.0 fails with the retirement message (no render)",
        rendered.returncode != 0 and retired in rendered.stderr and "Traceback" not in rendered.stderr,
        rendered.stderr.strip()[-200:],
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
