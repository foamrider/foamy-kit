#!/usr/bin/env python3
"""kit 0.4.2 settings rows (tests/qml/Rows.qml) on 4.0.6 and 4.5-rc2, LTR and
RTL, at display scale 1.0 and 1.25: toggle rows, compact FoamyNumberFields
and compact FoamyDropdowns share a row height and a trailing edge; the
compact dropdown's width, cap, elision and open list; a section title with
an (i) keeps the plain title's gap to its description. Card screenshots:
tests/out/rows/ (FOAMY_ROWS_OUT overrides)."""
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, run_shell, synced_demo  # noqa: E402


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    out = Path(os.environ.get("FOAMY_ROWS_OUT") or KIT_ROOT / "tests/out/rows")
    results = []
    for host in ("4.0", "4.5"):
        for rtl in (False, True):
            for scale in (1.0, 1.25):
                direction = "rtl" if rtl else "ltr"
                results.append(run_shell("Rows.qml", host, plugin, f"{host}/{direction}@{scale}",
                                         {"FOAMY_RTL": "1" if rtl else "0"}, scale=scale, keep_pngs_to=out,
                                         suffix=f"{host}-{direction}-{scale}", notes=True))
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
