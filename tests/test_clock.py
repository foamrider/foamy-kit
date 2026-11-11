#!/usr/bin/env python3
"""Epoch scheduling through DST fallback, ticking, pause, and resume on 4.5."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import harness, run_shell, synced_demo

plugin = synced_demo(["FoamyWallClock"])
try:
    results = [
        run_shell("WallClock.qml", host, plugin, host, env={"TZ": "Europe/Oslo"})
        for host in harness.available_hosts(what="wall clock")
    ]
finally:
    shutil.rmtree(plugin.parent)
raise SystemExit(0 if all(results) else 1)
