#!/usr/bin/env python3
"""kit 0.4.0 header overflow menu (tests/qml/Menu.qml) on 4.0.6 and 4.5-rc2,
LTR and RTL, at display scale 1.0 and 1.25: at most three buttons top
right, Settings in the ⋯ menu when overflowing, the in-card menu anchored to
the ⋯ button's trailing edge, keyboard (single cursor, submenu, Esc), press
outside, focus restore. Screenshots of the open menu: tests/out/menu/."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, read_png, report, run_shell, synced_demo  # noqa: E402


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    out = KIT_ROOT / "tests/out/menu"
    results = []
    for host in ("4.0", "4.5"):
        for rtl in (False, True):
            for scale in (1.0, 1.25):
                tag = f"{host}/{'rtl' if rtl else 'ltr'}@{scale}"
                suffix = f"{host}-{'rtl' if rtl else 'ltr'}-{scale}"
                results.append(run_shell("Menu.qml", host, plugin, tag, {"FOAMY_RTL": "1" if rtl else "0"}, scale=scale,
                                         keep_pngs_to=out, suffix=suffix))
                # The action hidden and shown again is drawn (icon strokes on its button).
                png = out / f"check-search-{suffix}.png"
                drawn = 0
                if png.is_file():
                    w, h, px = read_png(png)
                    base = px(0, 0)
                    drawn = sum(1 for x in range(w) for y in range(h) if sum(abs(a - b) for a, b in zip(px(x, y)[:3], base[:3])) > 60)
                results.append(report(f"menu {tag}: re-shown action is drawn", drawn > 10, f"{drawn} icon pixels"))
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
