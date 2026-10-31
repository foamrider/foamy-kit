#!/usr/bin/env python3
"""Wheel scrolling (tests/qml/Wheel.qml) on 4.0.6 and 4.5-rc2 at display
scale 1.0 and 1.25: why settings pages moved only a few px per notch (Qt's
Flickable loses most of a high-resolution notch; printed as NOTE lines) and
FoamyWheelScroll / FoamySettingsPage / ensureVisible / FoamyInfoNote."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import harness, run_shell, synced_demo  # noqa: E402


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    results = [run_shell("Wheel.qml", host, plugin, f"{host}@{scale}", scale=scale, notes=True)
               for host in ("4.0", "4.5") for scale in (1.0, 1.25)]
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
