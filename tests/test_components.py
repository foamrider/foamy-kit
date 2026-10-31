#!/usr/bin/env python3
"""kit 0.4.0 components (tests/qml/Components.qml) on 4.0.6 and 4.5-rc2, LTR
and RTL, at display scale 1.0 and 1.25: centred hero band, FoamyPanelFooter,
FoamyButton, FoamyInfoNote, popup height following the screen. Card
screenshots: tests/out/components/."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, run_shell, synced_demo  # noqa: E402


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    out = KIT_ROOT / "tests/out/components"
    results = []
    for host in ("4.0", "4.5"):
        for rtl in (False, True):
            for scale in (1.0, 1.25):
                direction = "rtl" if rtl else "ltr"
                results.append(run_shell("Components.qml", host, plugin, f"{host}/{direction}@{scale}",
                                         {"FOAMY_RTL": "1" if rtl else "0"}, scale=scale, keep_pngs_to=out,
                                         suffix=f"{host}-{direction}-{scale}"))
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
