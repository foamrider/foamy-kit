"""Shared helpers for foamy-kit tests."""

import shutil
import sys
import tempfile
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT_ROOT / "tools"))
sys.path.insert(0, str(KIT_ROOT / "preview"))
import compare
import foamykit  # noqa: E402
import harness  # noqa: E402

FIXTURES = KIT_ROOT / "tests/fixtures"
PLUGINS = KIT_ROOT.parent


def copy_kit(target):
    """A copy of foamy-kit without its tests and preview, as an older or newer
    kit to sync from. tests/validate.sh stays: sync copies it into plugins."""

    def ignore(directory, names):
        if Path(directory) == KIT_ROOT / "tests":
            return [n for n in names if n != "validate.sh"]
        return [n for n in names if n in (".git", "preview") or (n == "tests" and Path(directory) != KIT_ROOT)]

    shutil.copytree(KIT_ROOT, target, ignore=ignore)
    return target


def synced_demo(components=None):
    """A temporary copy of the demo plugin with the kit synced into it."""
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-demo-"))
    plugin = base / "foamy-kit-demo"
    shutil.copytree(FIXTURES / "demo-plugin", plugin)
    foamykit.sync_plugin(plugin, components, out=lambda *_: None)
    return plugin


def report(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}")
    return ok


def read_png(path):
    """(width, height, pixel(x, y) -> (r, g, b, a)) for an 8-bit PNG. It uses
    preview/compare.py's decoder, the one plugins and --trio compare with, so
    every pixel test also decodes real Qt-written PNGs through it."""
    width, height, rows = compare.read_png(path)
    return width, height, lambda x, y: rows[y][x]


def run_shell(
    qml_name,
    host,
    plugin,
    tag,
    env=None,
    scale=1.0,
    timeout=60,
    keep_pngs_to=None,
    suffix="",
    notes=False,
    theme="dark",
):
    """Run tests/qml/<qml_name> under `host`; report PASS/FAIL with the
    shell's FOAMY RESULT line; copy its PNGs to keep_pngs_to as
    <name>-<suffix>.png. `theme` is a preview/themes name or a colors.toml
    path. Returns True when it passed."""
    r = harness.Run(
        host,
        (KIT_ROOT / "tests/qml" / qml_name).read_text(),
        plugin=plugin,
        scale=scale,
        theme=theme,
        prefix=f"foamy-kit-{Path(qml_name).stem.lower()}-{host}-",
    )
    r.env.update(env or {})
    r.run(timeout=timeout)
    detail = next((line.split("qml: ", 1)[-1] for line in r.log.splitlines() if "FOAMY RESULT" in line), "no result")
    # A layout that never settles (an Image in a Layout without preferred size…).
    loops = [line for line in r.log.splitlines() if "polish() loop" in line]
    ok = report(
        f"{Path(qml_name).stem.lower()} {tag}",
        r.ok and not loops,
        detail + (f"; {len(loops)} polish-loop warnings" if loops else ""),
    )
    if notes:
        for line in r.log.splitlines():
            if "FOAMY NOTE" in line:
                print("    " + line.split("FOAMY NOTE ", 1)[1])
    if not ok:
        print("\n".join("    " + line for line in (r.failures() or loops[:3] or r.log.splitlines()[-30:])))
    if keep_pngs_to:
        keep_pngs_to = Path(keep_pngs_to)
        keep_pngs_to.mkdir(parents=True, exist_ok=True)
        for png in r.out.glob("*.png"):
            shutil.copyfile(png, keep_pngs_to / f"{png.stem}{'-' + suffix if suffix else ''}.png")
    r.cleanup()
    return ok
