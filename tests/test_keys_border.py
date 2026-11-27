#!/usr/bin/env python3
"""The keys' cursor border (tests/qml/KeysBorder.qml) on 4.5, in the
preview's dark and light themes, LTR at scale 1.0, read from the card's
pixels. For every kit control that takes the cursor (FoamyAction and
FoamyButton of each kind, active, inert and disabled; FoamyToggle,
FoamyDropdown, FoamyNumberField, FoamyTextSettingField, SafeTextField,
SafeTextArea) and the buttons FoamyHeroBand, FoamyHeader, FoamyPanelFooter
and FoamyInfoNote own (`cursorByKeys` on the component):

- with the cursor and `cursorByKeys`, the control's outline is drawn in the
  stated colour (the accent; the text colour on a primary button's accent
  fill) at the control's strength, and differs from the fill inside it
  (the contrast is printed: the text colour on a dark theme's light accent
  is the weakest, 1.23:1 in the dark preview);
- with the cursor and no flag (the pointer's cursor), or the flag and no
  cursor, the outline is not that colour; the flag without the cursor
  draws exactly the rest look;
- the keys' border changes only the outline: inside it, the pixels are the
  pointer cursor's, and every control keeps its place and size;
- an inert or disabled control shows the keys' border, but the cursor
  gives it no hover fill: inside the outline it is drawn as at rest;
- the pointer (in the QML, its own FOAMY FAIL checks), for every control
  that reports it, FoamyCursorSurface and FoamyTabs too: with the pointer
  resting inside and the keys' look on, the pointer reported again at the
  same place and the body moving under the still pointer report nothing,
  a real move inside reports the pointer (which clears the look, as a
  panel's cursor.hover(i) does), and with the pointer's look a move
  reports nothing.

Card screenshots: tests/out/keys-border/ (FOAMY_KEYS_BORDER_OUT overrides)."""

import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, read_png, report, synced_demo  # noqa: E402

THEMES = ("dark", "light")
MODES = ("rest", "elsewhere", "pointer", "keys")
# The outline's pixel is the stated colour over what is under the control,
# within the renderer's rounding (8 bits a channel).
NEAR = 3
# Told apart, 8 bits a channel in one channel: without the keys' border the
# outline is at least this far from the keys' colour, and the keys' border
# at least this far from the fill just inside it.
APART = 24


def relative(p):
    """WCAG 2 relative luminance of an 8-bit RGB pixel."""
    rgb = [v / 255 for v in p[:3]]
    rgb = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def contrast(a, b):
    """WCAG 2 contrast ratio of two 8-bit RGB pixels."""
    la, lb = relative(a), relative(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def rgb(name):
    """#rrggbb or #aarrggbb (Qt's colour string) as 8-bit RGB."""
    h = name.lstrip("#")[-6:]
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def over(color, under, strength):
    """`color` at `strength` over the opaque pixel `under`."""
    return tuple(round(c * strength + u * (1 - strength)) for c, u in zip(color, under[:3], strict=True))


def distance(a, b):
    return max(abs(x - y) for x, y in zip(a[:3], b[:3], strict=True))


def edges(r):
    """(outline, inside, outside) pixel positions at the middle of the top
    and the leading edge of a rect: the outline's first pixel row or column,
    2 px inside it, 2 px outside it."""
    x, y, w, h = (round(v) for v in r)
    mx, my = x + w // 2, y + h // 2
    return [((mx, y), (mx, y + 2), (mx, y - 2)), ((x, my), (x + 2, my), (x - 2, my))]


def inside(r, radius):
    """The pixels inside the outline (2 px in), less the rounded corners."""
    x, y, w, h = (round(v) for v in r)
    corner = max(2, round(radius))
    for py in range(y + 2, y + h - 2):
        for px in range(x + 2, x + w - 2):
            near_x = px < x + corner or px >= x + w - corner
            near_y = py < y + corner or py >= y + h - corner
            if not (near_x and near_y):
                yield px, py


def whole(r):
    x, y, w, h = (round(v) for v in r)
    for py in range(y - 1, y + h + 1):
        for px in range(x - 1, x + w + 1):
            yield px, py


def check_theme(tag, info, shots):
    """Every case's checks for one theme; shots: mode -> pixel(x, y)."""
    colours = {"accent": rgb(info["accent"]), "text": rgb(info["text"])}
    results = []
    for name, case in info["cases"].items():
        rects = case["rects"]
        r = rects["keys"]
        label = f"keys-border {tag} {name}"
        # Nothing moves: the same place and size in every mode.
        results.append(
            report(
                f"{label} keeps its place",
                all(rects[m] == r for m in MODES),
                ", ".join(f"{m} {rects[m]}" for m in MODES),
            )
        )
        want = colours[case["ring"]]
        lines, ok_ring, ok_reads, ok_off = [], True, True, True
        for outline, inner, outer in edges(r):
            under = shots["keys"](*outer)
            expected = over(want, under, case["strength"])
            drawn = shots["keys"](*outline)
            fill = shots["keys"](*inner)
            ok_ring &= distance(drawn, expected) <= NEAR
            ok_reads &= distance(drawn, fill) >= APART
            lines.append(
                f"{outline}: {drawn[:3]} want {expected}, {contrast(drawn, fill):.2f}:1 on the fill {fill[:3]}"
            )
            for mode in ("pointer", "elsewhere", "rest"):
                plain = shots[mode](*outline)
                ok_off &= distance(plain, expected) >= APART
                lines.append(f"  {mode} {plain[:3]}")
        results.append(report(f"{label} keys' border in the {case['ring']}", ok_ring, "; ".join(lines[::4])))
        results.append(report(f"{label} keys' border apart from the fill", ok_reads, lines[0]))
        results.append(report(f"{label} no keys' border without both", ok_off, "; ".join(lines)))
        # Only the outline changes: inside it, the keys' cursor draws the
        # pointer cursor's pixels.
        moved = [p for p in inside(r, case["radius"]) if shots["keys"](*p) != shots["pointer"](*p)]
        results.append(report(f"{label} only the outline changes", not moved, f"{len(moved)} pixels inside differ"))
        # The flag alone draws nothing: the rest look, outline and all.
        changed = [p for p in whole(r) if shots["elsewhere"](*p) != shots["rest"](*p)]
        results.append(report(f"{label} the flag alone draws nothing", not changed, f"{len(changed)} pixels differ"))
        if case["quiet"]:
            # Inert or disabled: the cursor gives no hover fill.
            hovered = [p for p in inside(r, case["radius"]) if shots["keys"](*p) != shots["rest"](*p)]
            results.append(
                report(f"{label} no hover fill while inert", not hovered, f"{len(hovered)} pixels inside differ")
            )
    return all(results)


def run(host, theme, plugin, out_dir):
    tag = f"{host}/{theme}"
    r = harness.Run(
        host,
        (KIT_ROOT / "tests/qml/KeysBorder.qml").read_text(),
        plugin=plugin,
        theme=theme,
        prefix=f"foamy-kit-keys-border-{host}-",
    )
    r.run(timeout=60)
    detail = next((line.split("qml: ", 1)[-1] for line in r.log.splitlines() if "FOAMY RESULT" in line), "no result")
    ok = report(f"keys-border {tag}", r.ok, detail)
    if not ok:
        print("\n".join("    " + line for line in (r.failures() or r.log.splitlines()[-20:])))
        r.cleanup()
        return False
    info = json.loads(next(line.split("FOAMY KEYS ", 1)[1] for line in r.log.splitlines() if "FOAMY KEYS " in line))
    shots = {}
    for mode in MODES:
        png = out_dir / f"keys-border-{host}-{theme}-{mode}.png"
        shutil.copyfile(r.out / f"{mode}.png", png)
        width, _, px = read_png(png)
        if width != round(info["card"][0]):
            r.cleanup()
            return report(f"keys-border {tag} card size", False, f"{width} px for a {info['card'][0]} card")
        shots[mode] = px
    r.cleanup()
    return check_theme(tag, info, shots)


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    out_dir = Path(os.environ.get("FOAMY_KEYS_BORDER_OUT") or KIT_ROOT / "tests/out/keys-border")
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for host in harness.available_hosts(what="keys border"):
        for theme in THEMES:
            results.append(run(host, theme, plugin, out_dir))
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
