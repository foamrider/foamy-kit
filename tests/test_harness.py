#!/usr/bin/env python3
"""The harness never leaks: a timed-out run and a killed parent leave no qs or
dbus-daemon behind, and cleanup removes the temp dir."""
import os
import shutil
import signal
import subprocess
import sys
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
sys.path.insert(0, {str(KIT_ROOT / 'preview')!r})
import harness
run = harness.Run("4.0", {HANG!r}, prefix="foamy-kit-orphan-")
run.start()
print(run.base, flush=True)
time.sleep(120)
"""


def gone(base, seconds=5):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if not harness.processes_under(base):
            return True
        time.sleep(0.1)
    return False


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
    time.sleep(1.5)
    alive_before = bool(harness.processes_under(base))
    child.send_signal(signal.SIGKILL)
    child.wait()
    ok &= report("a killed parent takes qs and its bus with it", alive_before and gone(base),
                 f"before={alive_before} after={harness.processes_under(base)}")
    shutil.rmtree(base, ignore_errors=True)

    # 3. Context manager.
    with harness.Run("4.0", HANG, prefix="foamy-kit-ctx-") as ctx:
        ctx.start()
        base = ctx.base
        time.sleep(1)
    ok &= report("Run as a context manager stops and removes everything", gone(base) and not base.exists())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
