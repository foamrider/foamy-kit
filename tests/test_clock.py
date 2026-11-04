#!/usr/bin/env python3
"""Epoch scheduling through DST fallback, ticking, pause, and resume on both hosts."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import run_shell, synced_demo

plugin = synced_demo(["FoamyWallClock"])
try:
    results = [run_shell("WallClock.qml", host, plugin, host,
                         env={"TZ": "Europe/Oslo"}) for host in ("4.0", "4.5")]
finally:
    shutil.rmtree(plugin.parent)
raise SystemExit(0 if all(results) else 1)
