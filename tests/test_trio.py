#!/usr/bin/env python3
"""render.py --trio on a throwaway git repo: `dev` holds a pre-kit popup (the
old KeyboardPanel fork, bare Color), the working tree the kit demo. Before
renders from `git archive dev` (the repo is not touched), with fallback to
the 4.0.6 host when dev won't render on 4.5, and a missing ref."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIXTURES, KIT_ROOT, foamykit, report  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import harness  # noqa: E402
import render  # noqa: E402

DEV_PREVIEW = """import QtQuick
import Quickshell
import ".." as Dev

Item {
  id: preview
  required property QtObject bar
  required property Item anchorItem
  property var previewStates: ["devices", "settings"]
  property string previewState: "devices"
  readonly property Item popup: popup
  Component.onCompleted: if (Quickshell.env("FOAMY_HOST") === "4.5" && Quickshell.env("FOAMY_DEV_FAIL_45") === "1")
    console.log("FOAMY FAIL this dev tree does not render on 4.5")
  Dev.OldPopup {
    id: popup
    anchorItem: preview.anchorItem
    bar: preview.bar
    open: true
    contentWidth: 400
    contentHeight: 160
    Rectangle {
      anchors.fill: parent
      color: Color.popups.background
      Text { anchors.centerIn: parent; text: "dev " + preview.previewState; color: Color.popups.text }
    }
  }
}
"""


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def make_repo(base, fail_on_45=False):
    repo = base / "foamy-kit-demo"
    shutil.copytree(FIXTURES / "demo-plugin", repo)
    git(repo, "init", "-q", "-b", "dev")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "foamy-kit test")
    shutil.copyfile(KIT_ROOT / "tests/fixtures/old-fork/BoltPopup.qml", repo / "OldPopup.qml")
    with (repo / "qmldir").open("a") as qmldir:
        qmldir.write("OldPopup 1.0 OldPopup.qml\n")
    text = DEV_PREVIEW.replace('Quickshell.env("FOAMY_DEV_FAIL_45") === "1"', "true" if fail_on_45 else "false")
    (repo / "preview/Preview.qml").write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "dev")
    git(repo, "checkout", "-q", "-b", "fix")
    git(repo, "rm", "-q", "OldPopup.qml")
    shutil.copyfile(FIXTURES / "demo-plugin/qmldir", repo / "qmldir")
    shutil.copyfile(FIXTURES / "demo-plugin/preview/Preview.qml", repo / "preview/Preview.qml")
    foamykit.sync_plugin(repo, None, out=lambda *_: None)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fix")
    return repo


def main():
    harness.install_signal_cleanup()
    ok = True
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-trio-test-"))
    try:
        repo = make_repo(base / "a")
        status = git(repo, "status", "--porcelain")
        worktrees = git(repo, "worktree", "list")
        out = base / "out"
        lines, label = render.trio(repo, out, dev_ref="dev", url_prefix="https://example.invalid/assets")
        names = sorted(p.name for p in out.glob("*.png"))
        ok &= report("a pre-kit fork clipped on 4.5 falls back to the 4.0.6 host, labelled",
                     label == "Before (dev, 4.0.6 host; popup fork clipped on 4.5)", label)
        for view in ("devices", "settings"):
            ok &= report(f"trio {view}: before, after 4.0, after 4.5",
                         {f"{view}-before.png", f"{view}-after-4.0.png", f"{view}-after-4.5.png"} <= set(names))
        ok &= report("trio covers every after view", {"empty-after-4.5.png", "artwork-after-4.0.png"} <= set(names))
        table = (out / "trio.md").read_text()
        ok &= report("trio.md is a PR table with prefixed image URLs",
                     table.startswith("| View | Before (dev, 4.0.6 host; popup fork clipped on 4.5) | After 4.0.6 | After 4.5 |")
                     and "![devices before](https://example.invalid/assets/devices-before.png)" in table
                     and "| empty | — |" in table, table.splitlines()[2] if len(table.splitlines()) > 2 else table)
        ok &= report("the plugin repo is untouched (no worktree, clean tree)",
                     git(repo, "status", "--porcelain") == status and git(repo, "worktree", "list") == worktrees)
        from common import read_png
        width, height, _ = read_png(out / "devices-before.png")
        ok &= report("the dev fork's card is captured", (width, height) == (400, 160), f"{width}x{height}")

        lines, label = render.trio(repo, base / "out-45", dev_ref="dev", before_hosts=("4.5",), states=["devices"])
        ok &= report("--before-host 4.5 alone renders dev on 4.5 as it is", label == "Before (dev, 4.5 host)"
                     and (base / "out-45/devices-before.png").is_file(), label)

        repo = make_repo(base / "b", fail_on_45=True)
        out = base / "out-b"
        lines, label = render.trio(repo, out, dev_ref="dev", states=["devices"])
        ok &= report("dev that won't render on 4.5 falls back to the 4.0.6 host, labelled",
                     label == "Before (dev, 4.0.6 host; did not render on 4.5)" and (out / "devices-before.png").is_file(), label)

        lines, label = render.trio(repo, base / "out-c", dev_ref="no-such-ref", states=["devices"])
        ok &= report("a missing dev ref still renders After, labelled",
                     "not found" in label and (base / "out-c/devices-after-4.5.png").is_file() and "| devices | — |" in lines[2], label)
        alive = [pid for pid in harness.STARTED if Path(f"/proc/{pid}").exists() and "zombie" not in Path(f"/proc/{pid}/status").read_text().lower()]
        ok &= report("no qs or dbus-daemon from these renders is left", harness.STARTED and not alive, f"{len(harness.STARTED)} started, alive {alive}")
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
