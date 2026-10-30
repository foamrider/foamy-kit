#!/usr/bin/env python3
"""FoamyHeroBand on 4.0.6 and 4.5-rc2, dark and light themes, LTR and RTL:
geometry inside a real FoamyPopup card, and pixels of the captured card
(rounded transparent corners, tinted band vs body, hairline edge, glow on the
trailing side, clipped picture)."""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, read_png, report, synced_demo  # noqa: E402


def luminance(p):
    return 0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]


def distance(a, b):
    return sum(abs(x - y) for x, y in zip(a[:3], b[:3]))


def run(host, theme, rtl, plugin, out_dir):
    tag = f"{host}/{theme}/{'rtl' if rtl else 'ltr'}"
    r = harness.Run(host, (KIT_ROOT / "tests/qml/Band.qml").read_text(), plugin=plugin, theme=theme,
                    prefix=f"foamy-kit-band-{host}-")
    r.env.update({"FOAMY_RTL": "1" if rtl else "0", "FOAMY_TAG": tag})
    r.run(timeout=40)
    ok = r.ok
    detail = next((l.split("qml: ", 1)[-1] for l in r.log.splitlines() if "FOAMY RESULT" in l), "no result")
    if not ok:
        report(f"band {tag}", False, detail)
        print("\n".join("    " + l for l in (r.failures() or r.log.splitlines()[-20:])))
        r.cleanup()
        return False
    info = json.loads(next(l.split("FOAMY BAND ", 1)[1] for l in r.log.splitlines() if "FOAMY BAND " in l))
    png = out_dir / f"band-{host}-{theme}-{'rtl' if rtl else 'ltr'}.png"
    shutil.copyfile(r.out / "band.png", png)
    only = out_dir / f"band-only-{host}-{theme}-{'rtl' if rtl else 'ltr'}.png"
    shutil.copyfile(r.out / "band-only.png", only)
    r.cleanup()
    ow, oh, opx = read_png(only)
    only_checks = [
        ("band-only card: bottom corners stay rounded (transparent)", opx(1, oh - 2)[3] < 40 and opx(ow - 2, oh - 2)[3] < 40),
        ("band-only card: band reaches the bottom border", opx(ow // 2, oh - 3)[3] == 255 and distance(opx(ow // 2, oh - 3), opx(ow // 2, oh // 2)) < 40),
    ]
    width, height, px = read_png(png)
    band_mid = px(width // 2, info["height"] // 2)
    body = px(width // 2, info["height"] + 60)
    checks = [
        ("top corners are rounded (transparent outside the radius)", px(1, 1)[3] < 40 and px(width - 2, 1)[3] < 40),
        ("band is tinted against the body", distance(band_mid, body) >= 6),
        ("dark theme: band lighter than the body" if theme == "dark" else "light theme: band tinted, not lighter",
         luminance(band_mid) > luminance(body) if theme == "dark" else distance(band_mid, body) >= 6),
        ("hairline edge into the body", distance(px(width // 2, info["height"]), body) >= 3),
        ("glow on the trailing top side (more tint there)",
         (distance(px(width - 30, 6), body) > distance(px(30, 6), body)) != rtl),
        ("picture band is clipped to the card too", px(width // 2, info["pictureY"] + 20)[3] == 255),
    ]
    ok = report(f"band {tag}", True, detail)
    for label, passed in checks + only_checks:
        ok &= report(f"band {tag}: {label}", passed)
    return ok


def main():
    harness.install_signal_cleanup()
    out_dir = KIT_ROOT / "tests/out/band"
    out_dir.mkdir(parents=True, exist_ok=True)
    plugin = synced_demo()
    results = [run(host, theme, rtl, plugin, out_dir)
               for host in ("4.0", "4.5") for theme in ("dark", "light") for rtl in (False, True)]
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
