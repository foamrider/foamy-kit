#!/usr/bin/env python3
"""kit 0.4.0 header overflow menu (tests/qml/Menu.qml) on 4.5,
LTR and RTL, at display scale 1.0 and 1.25: at most three buttons top
right, Settings in the ⋯ menu when overflowing, the in-card menu anchored to
the ⋯ button's trailing edge, keyboard (single cursor, submenu, Esc), press
outside, focus restore, and `raised` (a shadow under it, a clearer fill,
nothing else changed). Screenshots of the open menu: tests/out/menu/."""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, read_png, report, run_shell, synced_demo  # noqa: E402


def raised_check(tag, flat_png, raised_png, notes):
    """`raised: true` against the same menu flat: just under the panel the
    raised shot is darker (the shadow), inside it the fill differs, and
    away from it nothing changed. `notes` hold the panel's box in the card
    and the card's width (the shots are in device pixels)."""
    box = next((json.loads(note.split(" ", 1)[1]) for note in notes if note.startswith("panel ")), None)
    if box is None or not flat_png.is_file() or not raised_png.is_file():
        return report(f"menu {tag}: raised", False, "no panel box or shots")
    w, h, flat = read_png(flat_png)
    w2, h2, raised = read_png(raised_png)
    if (w, h) != (w2, h2):
        return report(f"menu {tag}: raised", False, f"shots differ in size {w}x{h} {w2}x{h2}")
    k = w / box[4]
    x0, y0, x1, y1 = (round(v * k) for v in (box[0], box[1], box[0] + box[2], box[1] + box[3]))

    def lum(px, x, y):
        r, g, b, _ = px(x, y)
        return r + g + b

    # A row 3 px under the panel, across its middle: the shadow's darkest part.
    under = [(x, y1 + 3) for x in range(x0 + 8, x1 - 8)]
    darker = sum(1 for x, y in under if lum(raised, x, y) < lum(flat, x, y) - 6)
    inside = [(x, (y0 + y1) // 2) for x in range(x0 + 4, x1 - 4)]
    filled = sum(1 for x, y in inside if flat(x, y) != raised(x, y))
    # The shadow reaches gapLarge (12) past the panel and drops 4: 40 px is clear of it.
    margin = round(40 * k)
    far = [
        (x, y)
        for x in range(w)
        for y in range(0, h, 3)
        if not (x0 - margin <= x < x1 + margin and y0 - margin <= y < y1 + margin)
    ]
    changed = sum(1 for x, y in far if flat(x, y) != raised(x, y))
    ok = darker > (x1 - x0 - 16) * 0.9 and filled > (x1 - x0) * 0.3 and changed == 0
    return report(
        f"menu {tag}: raised",
        ok,
        f"{darker}/{len(under)} darker under it, {filled}/{len(inside)} fill pixels changed, {changed} changed far away",
    )


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    out = KIT_ROOT / "tests/out/menu"
    results = []
    for host in harness.available_hosts(what="menu"):
        for rtl in (False, True):
            for scale in (1.0, 1.25):
                tag = f"{host}/{'rtl' if rtl else 'ltr'}@{scale}"
                suffix = f"{host}-{'rtl' if rtl else 'ltr'}-{scale}"
                png = out / f"check-search-{suffix}.png"
                # A shot left by an earlier run must not pass for this one.
                for old in (png, out / f"menu-{suffix}.png", out / f"menu-raised-{suffix}.png"):
                    old.unlink(missing_ok=True)
                notes = []
                results.append(
                    run_shell(
                        "Menu.qml",
                        host,
                        plugin,
                        tag,
                        {"FOAMY_RTL": "1" if rtl else "0"},
                        scale=scale,
                        keep_pngs_to=out,
                        suffix=suffix,
                        notes_to=notes,
                    )
                )
                # The action hidden and shown again is drawn (icon strokes on its button).
                drawn = 0
                if png.is_file():
                    w, h, px = read_png(png)
                    base = px(0, 0)
                    drawn = sum(
                        1
                        for x in range(w)
                        for y in range(h)
                        if sum(abs(a - b) for a, b in zip(px(x, y)[:3], base[:3], strict=False)) > 60
                    )
                results.append(report(f"menu {tag}: re-shown action is drawn", drawn > 10, f"{drawn} icon pixels"))
                results.append(raised_check(tag, out / f"menu-{suffix}.png", out / f"menu-raised-{suffix}.png", notes))
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
