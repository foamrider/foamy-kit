#!/usr/bin/env python3
"""kit 0.4.0 components (tests/qml/Components.qml) on 4.5, LTR
and RTL, at display scale 1.0 and 1.25 (dark), and LTR at 1.0 in the light
theme and a dark theme with a dim red: centred hero band, FoamyPanelFooter,
FoamyButton, FoamyAction, FoamyInfoNote, status and error colours,
FoamyPopupCard's height following the screen.
Card screenshots: tests/out/components/."""

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
    for host in harness.available_hosts(what="components"):
        for rtl in (False, True):
            for scale in (1.0, 1.25):
                direction = "rtl" if rtl else "ltr"
                results.append(
                    run_shell(
                        "Components.qml",
                        host,
                        plugin,
                        f"{host}/{direction}@{scale}",
                        {"FOAMY_RTL": "1" if rtl else "0"},
                        scale=scale,
                        keep_pngs_to=out,
                        suffix=f"{host}-{direction}-{scale}",
                    )
                )
        # Status colours in the light theme and in a dark theme with a dim
        # red (2.70:1 on its background), where they must lighten.
        for theme, source in (("light", "light"), ("dim-red", KIT_ROOT / "tests/fixtures/themes/dim-red.toml")):
            results.append(
                run_shell(
                    "Components.qml",
                    host,
                    plugin,
                    f"{host}/{theme}/ltr@1.0",
                    {"FOAMY_RTL": "0"},
                    keep_pngs_to=out,
                    suffix=f"{host}-{theme}-ltr-1.0",
                    theme=source,
                )
            )
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
