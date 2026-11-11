#!/usr/bin/env python3
"""FoamyScheduleDay (tests/qml/Schedule.qml) on 4.5: default and injected
label component, the day switch, committing, rejecting and restoring the time
fields. FoamySchedule.js itself: tests/schedule.test.cjs."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import harness, run_shell, synced_demo  # noqa: E402


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo(["FoamySchedule"])
    results = [run_shell("Schedule.qml", host, plugin, host) for host in harness.available_hosts(what="schedule")]
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
