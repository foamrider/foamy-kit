#!/usr/bin/env python3
"""The kit's UI font (tests/qml/UiFont.qml) on 4.5, as Qt resolves it
through fontconfig:

- with Adwaita Sans installed, FoamyStyle.fontFamily is "Adwaita Sans", a
  FoamyHeroBand's DemiBold title draws with its SemiBold face (weight 600),
  and DemiBold text is wider than Normal and narrower than Bold: a real
  semi-bold, not Bold drawn for it (as Liberation Sans, the usual
  "sans-serif", does);
- with Adwaita Sans hidden (a FONTCONFIG_FILE that includes the system's
  /etc/fonts/fonts.conf and rejects the family), FoamyStyle.fontFamily is
  "sans-serif" and the kit's text draws exactly as the system's sans-serif
  does: the same face and widths at each weight and the same pixels.

The ratio of the kit's width to the system sans-serif's is printed. Without
Adwaita Sans on this machine the first part is skipped (SKIP line)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, read_png, report, synced_demo  # noqa: E402

FAMILY = "Adwaita Sans"
SYSTEM_FONTS_CONF = Path("/etc/fonts/fonts.conf")
HIDE = f"""<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <include ignore_missing="no">{SYSTEM_FONTS_CONF}</include>
  <selectfont><rejectfont><pattern>
    <patelt name="family"><string>{FAMILY}</string></patelt>
  </pattern></rejectfont></selectfont>
</fontconfig>
"""


def installed(env=None):
    """Whether fontconfig (under `env`'s FONTCONFIG_FILE) lists FAMILY."""
    result = subprocess.run(
        ["fc-list", FAMILY, "family"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
        env=env,
    )
    return bool(result.stdout.strip())


def measure(plugin, tag, fontconfig=None):
    """(FOAMY FONT data, {name: pixel reader}) of one run, or None if it failed."""
    r = harness.Run("4.5", (KIT_ROOT / "tests/qml/UiFont.qml").read_text(), plugin=plugin, prefix="foamy-kit-uifont-")
    try:
        r.env["FOAMY_TAG"] = tag
        if fontconfig:
            r.env["FONTCONFIG_FILE"] = str(fontconfig)
        r.run(timeout=60)
        line = next((ln for ln in r.log.splitlines() if "FOAMY FONT " in ln), None)
        if not r.ok or line is None:
            report(f"ui-font {tag} run", False, "\n".join(r.failures() or r.log.splitlines()[-20:]))
            return None
        shots = {name: read_png(r.out / f"{name}.png") for name in ("kit", "system")}
        return json.loads(line.split("FOAMY FONT ", 1)[1]), shots
    finally:
        r.cleanup()


def same_pixels(a, b):
    (wa, ha, pa), (wb, hb, pb) = a, b
    return (wa, ha) == (wb, hb) and all(pa(x, y) == pb(x, y) for y in range(ha) for x in range(wa))


def check_installed(plugin):
    measured = measure(plugin, "installed")
    if measured is None:
        return False
    data, _ = measured
    title, (normal, demi, bold) = data["title"], data["kit"]
    ratio = normal["width"] / data["system"][0]["width"]
    print(f"    {FAMILY} regular is {ratio:.3f}x the system sans-serif's width")
    return all(
        [
            report(
                "ui-font installed: the kit asks for Adwaita Sans", data["fontFamily"] == FAMILY, data["fontFamily"]
            ),
            report(
                "ui-font installed: a band's DemiBold title draws Adwaita Sans SemiBold",
                data["titleWeight"] == 600 and title["family"] == FAMILY and title["style"] == "SemiBold",
                json.dumps(title),
            ),
            report(
                "ui-font installed: DemiBold is a weight of its own (Normal < DemiBold < Bold)",
                normal["width"] < demi["width"] < bold["width"] and demi["style"] != bold["style"],
                f"{normal['width']} {demi['style']} {demi['width']} {bold['style']} {bold['width']}",
            ),
        ]
    )


def check_hidden(plugin, base):
    conf = base / "fonts.conf"
    conf.write_text(HIDE)
    env = dict(os.environ, FONTCONFIG_FILE=str(conf))
    if not report("ui-font hidden: fontconfig lists no Adwaita Sans", not installed(env)):
        return False
    measured = measure(plugin, "hidden", conf)
    if measured is None:
        return False
    data, shots = measured
    return all(
        [
            report(
                "ui-font hidden: the kit falls back to sans-serif",
                data["fontFamily"] == "sans-serif",
                data["fontFamily"],
            ),
            report(
                "ui-font hidden: the kit's text has the system sans-serif's face and widths",
                data["kit"] == data["system"],
                json.dumps(data["kit"]) + " vs " + json.dumps(data["system"]),
            ),
            report("ui-font hidden: the kit's text draws the same pixels", same_pixels(shots["kit"], shots["system"])),
        ]
    )


def main():
    harness.install_signal_cleanup()
    if not SYSTEM_FONTS_CONF.is_file() or not shutil.which("fc-list"):
        print(f"SKIP ui-font: needs fontconfig ({SYSTEM_FONTS_CONF} and fc-list)")
        return 0
    plugin = synced_demo()
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-uifont-conf-"))
    try:
        ok = True
        if installed():
            ok = check_installed(plugin) and ok
        else:
            print(f"SKIP ui-font installed: {FAMILY} is not installed (package adwaita-fonts)")
        ok = check_hidden(plugin, base) and ok
        return 0 if ok else 1
    finally:
        shutil.rmtree(base, ignore_errors=True)
        shutil.rmtree(plugin.parent, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
