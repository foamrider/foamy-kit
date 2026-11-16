#!/usr/bin/env python3
"""FoamyTabs (tests/qml/Tabs.qml) on 4.5 under a FoamyPopup's hero band:
LTR and RTL, the standard and the wide popup (a full-width row, 420 and 560
at scale 1.0), scale 1.0 and 1.25 in the dark theme, and both widths in the
light theme. Content-width tabs from the reading start, the first icon
on the rows' content inset, the underline and the hairline, icons, counts
and the urgent colour, labels eliding from the last tab, a press, hover and
←/→ + Enter/Space through PanelKeyCatcher, accessibility. Card screenshots:
tests/out/tabs/ (FOAMY_TABS_OUT overrides)."""

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, run_shell, synced_demo  # noqa: E402

# (theme, rtl, wide, scale)
CASES = [("dark", rtl, wide, scale) for rtl in (False, True) for wide in (False, True) for scale in (1.0, 1.25)]
CASES += [("light", rtl, wide, 1.0) for rtl in (False, True) for wide in (False, True)]


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    out = Path(os.environ.get("FOAMY_TABS_OUT") or KIT_ROOT / "tests/out/tabs")
    results = []
    for host in harness.available_hosts(what="tabs"):
        for theme, rtl, wide, scale in CASES:
            name = f"{theme}-{'rtl' if rtl else 'ltr'}-{'560' if wide else '420'}-{scale}"
            results.append(
                run_shell(
                    "Tabs.qml",
                    host,
                    plugin,
                    f"{host}/{name}",
                    {"FOAMY_RTL": "1" if rtl else "0", "FOAMY_WIDE": "1" if wide else "0"},
                    scale=scale,
                    keep_pngs_to=out,
                    suffix=f"{host}-{name}",
                    theme=theme,
                )
            )
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
