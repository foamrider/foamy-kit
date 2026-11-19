#!/usr/bin/env python3
"""SafeTextField `runs` (tests/qml/Runs.qml) on 4.5, LTR and RTL, dark and
light. Runs in the field's own colour must give the same pixels as a plain
field with the same text: at the start, scrolled to the end, with a
selection and at a larger font; runs that don't match the text fall back to
the plain field. Coloured runs show their colour where the editor puts
their glyphs. Shots: tests/out/runs/."""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, read_png, report, synced_demo  # noqa: E402

PAIRS = ("start", "scrolled", "selected", "larger", "mismatch")


def differing(a, b, edges):
    """Pixels that differ by more than 96 (sum of RGBA) between two PNGs of
    the same size, and the total. Glyph anti-aliasing at a fractional scroll
    differs by up to ~45; a run 1 px off differs by more than 96 in over a
    thousand pixels. `edges` are the columns where the editor clips its own
    text (its paddings): it keeps or drops a whole glyph there, the runs
    are cut at the column, so those two columns are not compared."""
    wa, ha, pa = read_png(a)
    wb, hb, pb = read_png(b)
    if (wa, ha) != (wb, hb):
        return wa * ha, wa * ha
    skip = {x for edge in edges for x in (edge - 1, edge)}
    count = 0
    for y in range(ha):
        for x in range(wa):
            if x not in skip and sum(abs(p - q) for p, q in zip(pa(x, y), pb(x, y), strict=True)) > 96:
                count += 1
    return count, wa * ha


def hex_rgb(value):
    value = value.lstrip("#")
    if len(value) == 8:  # #aarrggbb
        value = value[2:]
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def coloured_in(png, span):
    """How many pixels in the span's columns are near the span's colour."""
    width, height, px = read_png(png)
    target = hex_rgb(span["color"])
    hits = 0
    for x in range(max(0, span["from"]), min(width, span["to"] + 1)):
        for y in range(height):
            if sum(abs(p - q) for p, q in zip(px(x, y)[:3], target, strict=True)) < 90:
                hits += 1
    return hits


def run(host, plugin, theme, rtl, out):
    name = f"{theme}-{'rtl' if rtl else 'ltr'}"
    r = harness.Run(
        host,
        (KIT_ROOT / "tests/qml/Runs.qml").read_text(),
        plugin=plugin,
        theme=theme,
        prefix=f"foamy-kit-runs-{host}-",
    )
    r.env.update({"FOAMY_RTL": "1" if rtl else "0", "FOAMY_THEME": theme})
    r.run(timeout=60)
    detail = next((line.split("qml: ", 1)[-1] for line in r.log.splitlines() if "FOAMY RESULT" in line), "no result")
    ok = report(f"runs {host}/{name}", r.ok, detail)
    if not ok:
        print("\n".join("    " + line for line in (r.failures() or r.log.splitlines()[-30:])))
        r.cleanup()
        return False
    out.mkdir(parents=True, exist_ok=True)
    for png in r.out.glob("*.png"):
        shutil.copyfile(png, out / f"{png.stem}-{host}-{name}.png")
    edges = json.loads(next(line.split("FOAMY EDGES ", 1)[1] for line in r.log.splitlines() if "FOAMY EDGES " in line))
    for case in PAIRS:
        count, total = differing(r.out / f"{case}-styled.png", r.out / f"{case}-plain.png", edges)
        ok &= report(
            f"runs {host}/{name} {case}: same pixels as the plain field", count == 0, f"{count} of {total} differ"
        )
    spans = json.loads(next(line.split("FOAMY SPANS ", 1)[1] for line in r.log.splitlines() if "FOAMY SPANS " in line))
    ok &= report(f"runs {host}/{name}: coloured tokens logged", len(spans) == 2, str(spans))
    for span in spans:
        hits = coloured_in(r.out / "coloured.png", span)
        ok &= report(f"runs {host}/{name}: the {span['kind']} token shows its colour", hits >= 8, f"{hits} pixels")
    r.cleanup()
    return ok


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    out = KIT_ROOT / "tests/out/runs"
    results = [
        run(host, plugin, theme, rtl, out)
        for host in harness.available_hosts(what="runs")
        for theme in ("dark", "light")
        for rtl in (False, True)
    ]
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
