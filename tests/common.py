"""Shared helpers for foamy-kit tests."""
import shutil
import sys
import tempfile
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT_ROOT / "tools"))
sys.path.insert(0, str(KIT_ROOT / "preview"))
import foamykit  # noqa: E402
import harness  # noqa: E402

FIXTURES = KIT_ROOT / "tests/fixtures"
PLUGINS = KIT_ROOT.parent


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
