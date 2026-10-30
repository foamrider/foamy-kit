#!/usr/bin/env python3
"""Demo preview render under both hosts, plus publish-screenshots.sh on a
throwaway git repository (orphan branch, untouched working tree, no push)."""
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, report, synced_demo  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import render  # noqa: E402

STATES = ["devices", "empty", "settings", "settings-error"]


def size(png):
    data = png.read_bytes()
    return struct.unpack(">II", data[16:24]) if data[:8] == b"\x89PNG\r\n\x1a\n" else None


def main():
    ok = True
    out_root = KIT_ROOT / "tests/out/preview"
    plugin = synced_demo()
    for host in ("4.0", "4.5"):
        out = out_root / host
        shutil.rmtree(out, ignore_errors=True)
        shots = render.render(plugin, host, out)
        if shots is None:
            ok &= report(f"preview render {host}", False)
            continue
        names = sorted(p.name for p, _ in shots)
        expected = sorted([f"{s}.png" for s in STATES] + [f"{s}-screen.png" for s in STATES])
        ok &= report(f"preview render {host}: all states captured", names == expected, ", ".join(names))
        screen = size(out / "devices-screen.png")
        card = size(out / "devices.png")
        ok &= report(f"preview render {host}: screen 1920x1080, card 420 wide", screen == (1920, 1080) and card and card[0] == 420, f"{screen} {card}")
        placed = dict((p.name, info) for p, info in shots)["devices.png"]
        ok &= report(f"preview render {host}: card hangs under the top bar (y = 34 + gap)", placed.endswith(",39"), placed)
    shutil.rmtree(plugin.parent, ignore_errors=True)

    # publish-screenshots.sh
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-publish-"))
    repo = base / "foamy-example"
    repo.mkdir()
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout
    git("init", "-q", "-b", "dev")
    (repo / "README.md").write_text("example\n")
    git("add", "README.md")
    git("commit", "-q", "-m", "init")
    git("remote", "add", "origin", "git@github.com:foamrider/foamy-example.git")
    (repo / "dirty.txt").write_text("uncommitted\n")
    status_before = git("status", "--porcelain")
    pngs = out_root / "4.5"
    script = KIT_ROOT / "preview/publish-screenshots.sh"
    result = subprocess.run(["bash", str(script), str(repo), str(pngs), "fix-omarchy-45/demo"], capture_output=True, text=True)
    ok &= report("publish-screenshots commits to an orphan pr-assets branch", result.returncode == 0
                 and git("rev-list", "--count", "pr-assets").strip() == "1"
                 and "fix-omarchy-45/demo/devices.png" in git("ls-tree", "-r", "--name-only", "pr-assets"), result.stderr.strip())
    ok &= report("publish-screenshots leaves the working tree and branch alone",
                 git("status", "--porcelain") == status_before and git("branch", "--show-current").strip() == "dev"
                 and "README.md" not in git("ls-tree", "-r", "--name-only", "pr-assets"))
    ok &= report("publish-screenshots prints raw URLs and the push command, without pushing",
                 "https://raw.githubusercontent.com/foamrider/foamy-example/pr-assets/fix-omarchy-45/demo/devices.png" in result.stdout
                 and f"git -C {repo} push origin pr-assets" in result.stdout and not git("worktree", "list").count("\n") > 1)
    again = subprocess.run(["bash", str(script), str(repo), str(pngs), "fix-omarchy-45/demo"], capture_output=True, text=True)
    ok &= report("publish-screenshots is idempotent", again.returncode == 0 and "already up to date" in again.stdout
                 and git("rev-list", "--count", "pr-assets").strip() == "1")
    shutil.rmtree(base, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
