#!/usr/bin/env python3
"""FoamyHeroBand field mode (tests/qml/BandField.qml) on 4.5, LTR and RTL,
dark and light: the field grows from the "+" action across the title row
and back while the band keeps its height and the content under it stays,
the buttons are inert while it is open, a hero band keeps its hero, reduced
motion is instant. Shots: tests/out/band-field/."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo  # noqa: E402


def run(host, theme, rtl, plugin, out):
    tag = f"{host}/{theme}/{'rtl' if rtl else 'ltr'}"
    r = harness.Run(
        host,
        (KIT_ROOT / "tests/qml/BandField.qml").read_text(),
        plugin=plugin,
        theme=theme,
        prefix=f"foamy-kit-band-field-{host}-",
    )
    r.env.update({"FOAMY_RTL": "1" if rtl else "0", "FOAMY_TAG": tag})
    r.run(timeout=60)
    detail = next((line.split("qml: ", 1)[-1] for line in r.log.splitlines() if "FOAMY RESULT" in line), "no result")
    ok = report(f"band field {tag}", r.ok, detail)
    if not ok:
        print("\n".join("    " + line for line in (r.failures() or r.log.splitlines()[-30:])))
    out.mkdir(parents=True, exist_ok=True)
    for png in r.out.glob("*.png"):
        shutil.copyfile(png, out / f"{png.stem}-{host}-{theme}-{'rtl' if rtl else 'ltr'}.png")
    r.cleanup()
    return ok


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    out = KIT_ROOT / "tests/out/band-field"
    results = [
        run(host, theme, rtl, plugin, out)
        for host in harness.available_hosts(what="band field")
        for theme in ("dark", "light")
        for rtl in (False, True)
    ]
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
