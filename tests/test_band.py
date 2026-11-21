#!/usr/bin/env python3
"""FoamyHeroBand on 4.5, dark and light themes, LTR and RTL:
geometry inside a real FoamyPopup card, and pixels of the captured card
(rounded transparent corners, tinted band vs body, hairline edge, glow on the
trailing side, the picture drawn across the band)."""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, read_png, report, synced_demo  # noqa: E402


def luminance(p):
    return 0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]


def distance(a, b):
    return sum(abs(x - y) for x, y in zip(a[:3], b[:3], strict=False))


def run(host, theme, rtl, plugin, out_dir):
    tag = f"{host}/{theme}/{'rtl' if rtl else 'ltr'}"
    r = harness.Run(
        host,
        (KIT_ROOT / "tests/qml/Band.qml").read_text(),
        plugin=plugin,
        theme=theme,
        prefix=f"foamy-kit-band-{host}-",
    )
    r.env.update({"FOAMY_RTL": "1" if rtl else "0", "FOAMY_TAG": tag})
    r.run(timeout=40)
    ok = r.ok
    detail = next((line.split("qml: ", 1)[-1] for line in r.log.splitlines() if "FOAMY RESULT" in line), "no result")
    if not ok:
        report(f"band {tag}", False, detail)
        print("\n".join("    " + line for line in (r.failures() or r.log.splitlines()[-20:])))
        r.cleanup()
        return False
    info = json.loads(next(line.split("FOAMY BAND ", 1)[1] for line in r.log.splitlines() if "FOAMY BAND " in line))
    png = out_dir / f"band-{host}-{theme}-{'rtl' if rtl else 'ltr'}.png"
    shutil.copyfile(r.out / "band.png", png)
    only = out_dir / f"band-only-{host}-{theme}-{'rtl' if rtl else 'ltr'}.png"
    shutil.copyfile(r.out / "band-only.png", only)
    r.cleanup()
    ow, oh, opx = read_png(only)
    only_checks = [
        (
            "band-only card: bottom corners stay rounded (transparent)",
            opx(1, oh - 2)[3] < 40 and opx(ow - 2, oh - 2)[3] < 40,
        ),
        (
            "band-only card: band reaches the bottom border",
            opx(ow // 2, oh - 3)[3] == 255 and distance(opx(ow // 2, oh - 3), opx(ow // 2, oh // 2)) < 40,
        ),
    ]
    width, height, px = read_png(png)
    band_mid = px(width // 2, info["height"] // 2)
    body = px(width // 2, info["height"] + 60)
    # The artwork fixture is a horizontal gradient (red 40 at the left edge,
    # 230 at the right; not mirrored in RTL). Under the band's scrim and glow
    # its two ends still differ when it is drawn across the full width.
    picture_y = info["pictureY"] + info["pictureHeight"] // 2
    picture_left, picture_right = px(6, picture_y), px(width - 7, picture_y)
    checks = [
        ("top corners are rounded (transparent outside the radius)", px(1, 1)[3] < 40 and px(width - 2, 1)[3] < 40),
        ("band is tinted against the body", distance(band_mid, body) >= 6),
        ("hairline edge into the body", distance(px(width // 2, info["height"]), body) >= 3),
        (
            "glow on the trailing top side (more tint there)",
            (distance(px(width - 30, 6), body) > distance(px(30, 6), body)) != rtl,
        ),
    ]
    if theme == "dark":
        checks.append(("dark theme: band lighter than the body", luminance(band_mid) > luminance(body)))
    picture = f"red {picture_left[0]} at the left, {picture_right[0]} at the right"
    checks.append(
        (
            f"picture band: the artwork is drawn across the full width ({picture})",
            picture_right[0] - picture_left[0] >= 40,
        )
    )
    ok = report(f"band {tag}", True, detail)
    for label, passed in checks + only_checks:
        ok &= report(f"band {tag}: {label}", passed)
    return ok


def main():
    harness.install_signal_cleanup()
    out_dir = KIT_ROOT / "tests/out/band"
    out_dir.mkdir(parents=True, exist_ok=True)
    plugin = synced_demo()
    results = [
        run(host, theme, rtl, plugin, out_dir)
        for host in harness.available_hosts(what="band")
        for theme in ("dark", "light")
        for rtl in (False, True)
    ]
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
