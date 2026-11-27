#!/usr/bin/env python3
"""FoamyButton's states as drawn (tests/qml/ButtonStates.qml) on 4.5, in the
preview's dark and light themes and three dark fixtures (a dim red, a mid
accent, an accent near the background): for each kind (primary,
secondary, destructive), the label's colour on the fill, both read from
the card's pixels. Inert (actionEnabled: false) reads at 4.5:1 or more,
disabled (enabled: false) at 3:1 or more, and the states stay apart: the
fill moves toward the surface from active to inert to disabled, each step
is weaker by a clear margin, and a disabled label reads less than an
inert one; where the accent's own ink reads by .8, an inert primary keeps
the active ink. The QML side checks the icon's colour, the pointer on an
inert or busy button, busy starting and ending under the pointer, the
border and focus ring, the label on the fill through each change of
state, also under the pointer, and the hover animation. An inert and a disabled button of each kind on a tinted surface
show its colour through their fill. Card screenshots:
tests/out/button-states/ (FOAMY_BUTTON_STATES_OUT overrides)."""

import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, read_png, report, synced_demo  # noqa: E402

THEMES = {
    "dark": "dark",
    "light": "light",
    # A dim red (2.70:1 on the background): the destructive ink lightens.
    "dim-red": KIT_ROOT / "tests/fixtures/themes/dim-red.toml",
    # A mid accent (Tokyo Night): the dark ink falls short at .7, the inert
    # fill steps up.
    "mid-accent": KIT_ROOT / "tests/fixtures/themes/mid-accent.toml",
    # An accent near the background: no ink reads on it, the fills step down.
    "dim-accent": KIT_ROOT / "tests/fixtures/themes/dim-accent.toml",
}
KINDS = ("primary", "secondary", "destructive")
# The least contrast a label must have on its fill, per state.
FLOORS = {"inert": 4.5, "disabled": 3.0}
# Themes whose accent's own ink reads at a mix from .7 to .8: an inert
# primary keeps the active one's look, a dimmer accent with the same ink
# (dark or light), instead of turning to the text's.
KEEPS_INK = {"dark", "dim-red", "mid-accent"}
# A weaker state differs from the stronger one by at least this factor in
# the fill's contrast on the surface or the label's on the fill.
MARGIN = 1.1
# An inert or disabled fill's pixel on the tinted test surface (a green far
# from every popup background) differs from its pixel on the card by at
# least this much in one channel, 8 bits; an opaque fill differs by the
# renderer's rounding, 0 or 1. The nearest: an inert primary, mix up to .8.
TINT_APART = 16


def relative(p):
    """WCAG 2 relative luminance of an 8-bit RGB pixel."""
    rgb = [v / 255 for v in p[:3]]
    rgb = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def contrast(a, b):
    """WCAG 2 contrast ratio of two 8-bit RGB pixels."""
    la, lb = relative(a), relative(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def measure(png, info):
    """{state name: (fill, label, surface)} pixels for each block button."""
    width, height, px = read_png(png)
    scale = width / info["card"][0]

    def at(x, y):
        return px(round(x * scale), round(y * scale))

    out = {}
    for name, geometry in info["buttons"].items():
        bx, by, _, bh = geometry["button"]
        lx, ly, lw, lh = geometry["label"]
        # The fill: between the leading edge and the label, clear of the
        # border; the label: the middle of its full blocks.
        fill = at(bx + (lx - bx) / 2, by + bh / 2)
        ink = at(lx + lw / 2, ly + lh / 2)
        # The surface just outside the button's leading edge, on the card.
        surface = at(bx - 3, by + bh / 2)
        out[name] = (fill, ink, surface)
    return out


def check_theme(tag, theme, drawn):
    results = []
    lines = []
    for kind in KINDS:
        ratios = {}
        for state in ("active", "inert", "disabled"):
            fill, ink, surface = drawn[f"{kind}-{state}"]
            ratios[state] = (contrast(ink, fill), contrast(fill, surface))
        lines.append(f"{kind}: " + ", ".join(f"{s} {r[0]:.2f} (fill {r[1]:.2f})" for s, r in ratios.items()))
        for state, floor in FLOORS.items():
            ratio = ratios[state][0]
            results.append(
                report(
                    f"button-states {tag} {kind} {state} label reads",
                    ratio >= floor,
                    f"{ratio:.2f}:1, at least {floor}",
                )
            )
        pairs = [("active", "inert"), ("inert", "disabled")]
        for strong, weak in pairs:
            (label_s, fill_s), (label_w, fill_w) = ratios[strong], ratios[weak]
            toward = fill_w <= fill_s + 0.01
            apart = fill_s >= fill_w * MARGIN or label_s >= label_w * MARGIN
            results.append(
                report(
                    f"button-states {tag} {kind} {weak} weaker than {strong}",
                    toward and apart,
                    f"fill {fill_s:.2f} -> {fill_w:.2f}, label {label_s:.2f} -> {label_w:.2f}",
                )
            )
        results.append(
            report(
                f"button-states {tag} {kind} disabled label reads less than inert",
                ratios["disabled"][0] < ratios["inert"][0],
                f"{ratios['inert'][0]:.2f} -> {ratios['disabled'][0]:.2f}",
            )
        )
    if theme in KEEPS_INK:
        sides = []
        for state in ("active", "inert"):
            fill, ink, _ = drawn[f"primary-{state}"]
            sides.append("dark" if relative(ink) < relative(fill) else "light")
        results.append(
            report(
                f"button-states {tag} primary inert keeps the active ink",
                sides[0] == sides[1],
                f"active {sides[0]}, inert {sides[1]} on the fill",
            )
        )
    print("    " + "\n    ".join(lines))
    return all(results)


def run(host, theme, source, plugin, out_dir):
    tag = f"{host}/{theme}"
    r = harness.Run(
        host,
        (KIT_ROOT / "tests/qml/ButtonStates.qml").read_text(),
        plugin=plugin,
        theme=source,
        prefix=f"foamy-kit-button-states-{host}-",
    )
    r.run(timeout=40)
    detail = next((line.split("qml: ", 1)[-1] for line in r.log.splitlines() if "FOAMY RESULT" in line), "no result")
    ok = report(f"button-states {tag}", r.ok, detail)
    if not ok:
        print("\n".join("    " + line for line in (r.failures() or r.log.splitlines()[-20:])))
        r.cleanup()
        return False
    info = json.loads(
        next(line.split("FOAMY BUTTONS ", 1)[1] for line in r.log.splitlines() if "FOAMY BUTTONS " in line)
    )
    tinted_info = json.loads(
        next(line.split("FOAMY TINTED ", 1)[1] for line in r.log.splitlines() if "FOAMY TINTED " in line)
    )
    png = out_dir / f"button-states-{host}-{theme}.png"
    tinted_png = out_dir / f"button-states-{host}-{theme}-tinted.png"
    shutil.copyfile(r.out / "card.png", png)
    shutil.copyfile(r.out / "tinted.png", tinted_png)
    r.cleanup()
    drawn = measure(png, info)
    tinted_info["card"] = tinted_info["size"]
    return all([check_theme(tag, theme, drawn), check_see_through(tag, drawn, measure(tinted_png, tinted_info))])


def check_see_through(tag, drawn, tinted):
    """An inert or disabled fill is see-through: on the tinted surface its
    pixel is not the one it has on the card. (An opaque fill, the popup
    background tinted with the kind's fill, drew a patch of the popup's
    colour on a hero band or a menu.)"""
    results = []
    for name, (fill, _, surface) in tinted.items():
        on_card = drawn[name][0]
        apart = max(abs(a - b) for a, b in zip(fill[:3], on_card[:3], strict=True))
        results.append(
            report(
                f"button-states {tag} {name} fill is see-through",
                apart >= TINT_APART,
                f"{fill[:3]} on {surface[:3]}, {on_card[:3]} on the card: {apart} apart, at least {TINT_APART}",
            )
        )
    return all(results)


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    out_dir = Path(os.environ.get("FOAMY_BUTTON_STATES_OUT") or KIT_ROOT / "tests/out/button-states")
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for host in harness.available_hosts(what="button states"):
        for theme, source in THEMES.items():
            results.append(run(host, theme, source, plugin, out_dir))
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
