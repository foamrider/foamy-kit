#!/usr/bin/env python3
"""kit 0.16.0 (tests/qml/SettingsHeader.qml) on 4.5, LTR and RTL, at display
scale 1.0 and 1.25: the compact band's title action (off by default: no
control, the same Tab chain and the same pixels with its other properties
set; on: mark, title, chevron, click/Enter/Space with the `keyboard`
argument, Tab order, ring and fill, role and name, a menu hanging from its
start, Esc back to it, elide with a tooltip).
Screenshots: tests/out/settings-header/."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, read_png, report, run_shell, synced_demo  # noqa: E402


def same_pixels(a, b):
    """None when the two PNGs are equal, else why not."""
    aw, ah, apx = read_png(a)
    bw, bh, bpx = read_png(b)
    if (aw, ah) != (bw, bh):
        return f"sizes {aw}x{ah} and {bw}x{bh}"
    differ = sum(1 for y in range(ah) for x in range(aw) if apx(x, y) != bpx(x, y))
    return f"{differ} pixels differ" if differ else None


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    out = KIT_ROOT / "tests/out/settings-header"
    results = []
    for host in harness.available_hosts(what="settings header"):
        for rtl in (False, True):
            for scale in (1.0, 1.25):
                tag = f"{host}/{'rtl' if rtl else 'ltr'}@{scale}"
                suffix = f"{host}-{'rtl' if rtl else 'ltr'}-{scale}"
                off, off_set = out / f"band-off-{suffix}.png", out / f"band-off-set-{suffix}.png"
                # Shots left by an earlier run must not pass for this one.
                for png in (off, off_set):
                    png.unlink(missing_ok=True)
                results.append(
                    run_shell(
                        "SettingsHeader.qml",
                        host,
                        plugin,
                        tag,
                        {"FOAMY_RTL": "1" if rtl else "0"},
                        scale=scale,
                        keep_pngs_to=out,
                        suffix=suffix,
                    )
                )
                why = same_pixels(off, off_set) if off.is_file() and off_set.is_file() else "no shots"
                results.append(
                    report(
                        f"settings header {tag}: off, its properties set draw the same pixels", why is None, why or ""
                    )
                )
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
