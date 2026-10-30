#!/usr/bin/env python3
"""FoamyPopup/FoamyPopupCard placement on 4.0.6 (strip bar window) and
4.5-rc2 (full-screen bar window), all four bar positions, plus a negative
control: the old forked 4.0 popup misplaces on the 4.5 full-screen window."""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo

FORK = KIT_ROOT / "tests/fixtures/old-fork/BoltPopup.qml"


def run(host, mode, out_dir):
    plugin = synced_demo()
    extra = {}
    has_fork = FORK.is_file()
    if has_fork:
        # The fork predates Commons qualification; qualify it so only its
        # geometry is under test.
        fork = harness.transform_keyboard_panel(FORK.read_text())
        fork = re.sub(r"(?<![\w.])Color\.", "Commons.Color.", fork).replace("import qs.Commons\n", "import qs.Commons\nimport qs.Commons as Commons\n", 1)
        extra["fork/ForkedPopup.qml"] = fork
    shell = (KIT_ROOT / "tests/qml/Geometry.qml").read_text()
    r = harness.Run(host, shell, plugin=plugin, extra=extra, prefix=f"foamy-kit-geometry-{host}-")
    r.env["FOAMY_MODE"] = mode
    r.env["FOAMY_FORK"] = "1" if has_fork else "0"
    r.run(timeout=90)
    for png in r.out.glob("*.png"):
        shutil.copyfile(png, out_dir / png.name)
    result = [l for l in r.log.splitlines() if "FOAMY RESULT" in l or "FOAMY NOTE" in l]
    ok = r.ok
    detail = "; ".join(l.split("qml: ", 1)[-1] for l in result if "RESULT" in l)
    notes = [l.split("qml: ", 1)[-1] for l in result if "NOTE" in l]
    report(f"geometry {host} {mode}", ok, detail)
    for note in notes[:2]:
        print("    " + note)
    if not ok:
        print("\n".join("    " + l for l in (r.failures() or r.log.splitlines()[-30:])))
    else:
        r.cleanup()
        shutil.rmtree(plugin.parent, ignore_errors=True)
    return ok


def main():
    out_dir = KIT_ROOT / "tests/out"
    out_dir.mkdir(exist_ok=True)
    results = [run("4.0", "strip", out_dir), run("4.5", "fullscreen", out_dir)]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
