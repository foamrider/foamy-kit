#!/usr/bin/env python3
"""Demo preview render on 4.5 (a preview that logs an error fails the
render), plus publish-screenshots.sh on a throwaway git repository with an
isolated Git config: orphan branch, untouched working tree, nothing pushed
to a local push remote, unsafe subdirs and an empty PNG dir refused."""

import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import render  # noqa: E402

STATES = ["devices", "empty", "artwork", "settings", "settings-error"]


def size(png):
    data = png.read_bytes()
    return struct.unpack(">II", data[16:24]) if data[:8] == b"\x89PNG\r\n\x1a\n" else None


def row(png, y):
    """Row y of an 8-bit RGB or RGBA PNG as a list of pixel tuples. Decodes
    only the rows up to y: common.read_png takes seconds on a whole screen."""
    data = png.read_bytes()
    width, _ = struct.unpack(">II", data[16:24])
    colour = data[25]
    offset, chunks = 8, b""
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        if kind == b"IDAT":
            chunks += data[offset + 8 : offset + 8 + length]
        offset += 12 + length
    raw = zlib.decompress(chunks)
    channels = {6: 4, 2: 3}[colour]
    stride = width * channels
    previous = bytearray(stride)
    for row in range(y + 1):
        start = row * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1 : start + 1 + stride])
        for i in range(stride):
            left = line[i - channels] if i >= channels else 0
            up = previous[i]
            corner = previous[i - channels] if i >= channels else 0
            if kind == 1:
                line[i] = (line[i] + left) & 255
            elif kind == 2:
                line[i] = (line[i] + up) & 255
            elif kind == 3:
                line[i] = (line[i] + (left + up) // 2) & 255
            elif kind == 4:
                p = left + up - corner
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - corner)
                line[i] = (line[i] + (left if pa <= pb and pa <= pc else up if pb <= pc else corner)) & 255
        previous = line
    return [tuple(previous[x : x + channels]) for x in range(0, stride, channels)]


def card_on_screen(screen, card, x, y, line=20):
    """(ok, detail): row `line` of the card PNG appears on the screen PNG at
    (x, y + line), every opaque card pixel with the same RGB; a decode error
    is a failure."""
    try:
        wanted = row(card, line)
        shown = row(screen, y + line)[x : x + len(wanted)]
    except (OSError, KeyError, ValueError, IndexError, struct.error, zlib.error) as error:
        return False, f"cannot decode: {error!r}"
    opaque = [i for i, px in enumerate(wanted) if len(px) == 3 or px[3] == 255]
    wrong = [i for i in opaque if i >= len(shown) or shown[i][:3] != wanted[i][:3]]
    detail = f"{len(opaque)} opaque pixels, {len(wrong)} differ"
    if wrong:
        i = wrong[0]
        detail += f", first at {i}: {shown[i] if i < len(shown) else None} vs {wanted[i]}"
    return len(opaque) > len(wanted) // 2 and not wrong, detail


def tiny_png(path):
    """A valid 1x1 RGBA PNG."""

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\0\x10\x20\x30\xff"))
        + chunk(b"IEND", b"")
    )


def languages():
    """--language names a catalog the plugin has: nb (no such Omarchy code)
    is read as no when only no.json exists, and a language without a
    catalog stops the render instead of silently rendering English."""
    ok = True
    with tempfile.TemporaryDirectory(prefix="foamy-kit-language-") as work:
        plugin = Path(work) / "foamy-norsk"
        (plugin / "i18n").mkdir(parents=True)
        for name in ("en", "no", "pt"):
            (plugin / "i18n" / f"{name}.json").write_text("{}")
        cases = (
            (None, None),
            ("en", "en"),
            ("no", "no"),
            ("nb", "no"),
            ("pt-BR", "pt-BR"),
            ("da", "render: --language da: foamy-norsk has no i18n/da.json"),
        )
        for asked, expected in cases:
            try:
                got = render.catalog_language(plugin, asked)
            except SystemExit as error:
                got = str(error)
            ok &= report(
                f"--language {asked}: {expected}",
                got == expected or (expected and str(got).startswith(expected)),
                str(got),
            )
        (plugin / "i18n/nb.json").write_text("{}")
        ok &= report("--language nb stays nb when nb.json exists", render.catalog_language(plugin, "nb") == "nb")
        cli = subprocess.run(
            [sys.executable, "-I", str(KIT_ROOT / "preview/render.py"), str(plugin), "--language", "da"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        ok &= report(
            "render.py --language da on a plugin without da.json fails before rendering",
            cli.returncode != 0 and "has no i18n/da.json" in cli.stderr and "PNGs" not in cli.stdout,
            cli.stderr.strip()[-200:],
        )
    return ok


def render_tests():
    ok = True
    out_root = KIT_ROOT / "tests/out/preview"
    plugin = synced_demo()
    for host in harness.available_hosts(what="preview render"):
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
        ok &= report(
            f"preview render {host}: screen 1920x1080, card 420 wide",
            screen == (1920, 1080) and card and card[0] == 420,
            f"{screen} {card}",
        )
        log = (out / "render.log").read_text()
        # The view really uses a type from components/, which has no qmldir;
        # "is not a type" is no harness failure marker, so check the log.
        ok &= report(
            f"preview render {host}: plugin subdirectory types load without a qmldir",
            "DemoTag {" in (plugin / "DemoView.qml").read_text()
            and (plugin / "components/DemoTag.qml").is_file()
            and not (plugin / "components/qmldir").exists()
            and "is not a type" not in log,
        )

        # A FoamyPopupCard menu: its card is copied onto the screen at its anchor.
        card_out = out_root / host / "menu"
        shots = render.render(plugin, host, card_out, preview=plugin / "preview/MenuPreview.qml")
        info = dict((p.name, i) for p, i in shots or [])
        at = info.get("menu.png", "")
        found = re.search(r" at (-?\d+),(-?\d+)", at)
        x, y = (int(found.group(1)), int(found.group(2))) if found else (-1, -1)
        # PopupCard hangs from the anchor item (stock geometry), not the strip edge.
        ok &= report(
            f"card preview {host}: menu card captured and placed below the bar button",
            shots is not None and size(card_out / "menu.png") is not None and 1300 < x < 1700 and 28 < y < 80,
            at,
        )
        shown, detail = card_on_screen(card_out / "menu-screen.png", card_out / "menu.png", x, y)
        ok &= report(
            f"card preview {host}: the screen shot shows the card's own pixels where it is placed",
            shots is not None and shown,
            detail,
        )

        # A service-only preview: no bar or anchor declared, toast in screen coordinates.
        service_out = out_root / host / "service"
        shots = render.render(plugin, host, service_out, preview=plugin / "preview/ServicePreview.qml")
        ok &= report(
            f"service preview {host}: toast captured",
            shots is not None and size(service_out / "toast.png") == (420, 72),
        )
        ok &= broken_preview_test(plugin, out_root / host / "broken")
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return ok


def broken_preview_test(plugin, out):
    """A preview that throws a TypeError fails the render: render.py names
    the error and exits 1 instead of publishing a half-drawn shot."""
    broken = plugin / "preview/Broken.qml"
    service = (plugin / "preview/ServicePreview.qml").read_text()
    anchor = "  readonly property Item popup: toast\n"
    throw = "  Component.onCompleted: {\n    var missing = null\n    missing.x = 1\n  }\n"
    broken.write_text(service.replace(anchor, anchor + throw))
    cli = subprocess.run(
        [sys.executable, "-I", str(KIT_ROOT / "preview/render.py"), plugin, "--preview", broken, "--out", out],
        capture_output=True,
        text=True,
        timeout=300,
    )
    broken.unlink()
    return report(
        "render.py fails on a preview that logs a TypeError and prints the error",
        anchor in service and cli.returncode == 1 and "TypeError" in cli.stderr and "render failed on" in cli.stderr,
        f"exit {cli.returncode}: {cli.stderr.strip()[-300:]}",
    )


def git_env(base):
    """The environment for git and publish-screenshots.sh: a config of the
    test's own (no signing key, hooks or user settings of the person running
    it) and a temporary dir inside `base`."""
    config = base / "gitconfig"
    config.write_text(
        "[user]\n\tname = Foamy Test\n\temail = foamy-test@example.invalid\n"
        "[commit]\n\tgpgsign = false\n[init]\n\tdefaultBranch = dev\n"
    )
    (base / "tmp").mkdir()
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=str(config), GIT_CONFIG_NOSYSTEM="1", TMPDIR=str(base / "tmp"))
    return env


def tree(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


def publish_tests():
    """publish-screenshots.sh on a throwaway repo with PNGs of its own. Its
    origin is a GitHub URL (the script builds the raw URLs from it), but the
    push URL is a local bare repository, so a push could not leave the machine."""
    ok = True
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-publish-"))
    env = git_env(base)
    repo = base / "foamy-example"
    repo.mkdir()
    remote = base / "remote.git"
    pngs = base / "pngs"
    pngs.mkdir()
    for name in ("devices.png", "empty.png"):
        tiny_png(pngs / name)
    script = KIT_ROOT / "preview/publish-screenshots.sh"

    def git(*a, cwd=repo):
        return subprocess.run(
            ["git", "-C", str(cwd), *a], capture_output=True, text=True, check=True, env=env, timeout=60
        ).stdout

    def publish(png_dir, subdir):
        return subprocess.run(
            ["bash", str(script), str(repo), str(png_dir), subdir], capture_output=True, text=True, env=env, timeout=60
        )

    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, env=env, timeout=60)
    git("init", "-q", "-b", "dev")
    (repo / "README.md").write_text("example\n")
    git("add", "README.md")
    git("commit", "-q", "-m", "init")
    git("remote", "add", "origin", "git@github.com:foamrider/foamy-example.git")
    git("config", "remote.origin.pushurl", str(remote))
    (repo / "dirty.txt").write_text("uncommitted\n")
    status_before = git("status", "--porcelain")

    # Refused before anything is written: a subdir that could leave the
    # worktree (mkdir -p and cp would follow "..") or is not a plain path.
    for subdir in ("/abs", "a/../../x", "a b", "$(id)", ""):
        before = tree(base)
        result = publish(pngs, subdir)
        branch = subprocess.run(
            ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", "refs/heads/pr-assets"], env=env, timeout=60
        )
        ok &= report(
            f"publish-screenshots refuses the subdir {subdir!r} and writes nothing",
            result.returncode == 2
            and "subdir must be a relative path" in result.stderr
            and branch.returncode != 0
            and git("worktree", "list").count("\n") == 1
            and tree(base) == before,
            f"exit {result.returncode}: {result.stderr.strip()}",
        )
    empty = base / "no-pngs"
    empty.mkdir()
    result = publish(empty, "fix-omarchy-45/demo")
    ok &= report(
        "publish-screenshots fails on a dir without PNGs",
        result.returncode == 1 and "no PNGs in" in result.stderr,
        f"exit {result.returncode}: {result.stderr.strip()}",
    )

    result = publish(pngs, "fix-omarchy-45/demo")
    ok &= report(
        "publish-screenshots commits to an orphan pr-assets branch",
        result.returncode == 0
        and git("rev-list", "--count", "pr-assets").strip() == "1"
        and "fix-omarchy-45/demo/devices.png" in git("ls-tree", "-r", "--name-only", "pr-assets"),
        result.stderr.strip(),
    )
    ok &= report(
        "publish-screenshots leaves the working tree and branch alone",
        git("status", "--porcelain") == status_before
        and git("branch", "--show-current").strip() == "dev"
        and "README.md" not in git("ls-tree", "-r", "--name-only", "pr-assets"),
    )
    ok &= report(
        "publish-screenshots prints raw URLs and the push command, without pushing",
        "https://raw.githubusercontent.com/foamrider/foamy-example/pr-assets/fix-omarchy-45/demo/devices.png"
        in result.stdout
        and f"git -C {repo} push origin pr-assets" in result.stdout
        and git("for-each-ref", cwd=remote) == ""
        and not git("worktree", "list").count("\n") > 1,
        result.stdout.strip()[-300:],
    )
    again = publish(pngs, "fix-omarchy-45/demo")
    ok &= report(
        "publish-screenshots is idempotent",
        again.returncode == 0
        and "already up to date" in again.stdout
        and git("rev-list", "--count", "pr-assets").strip() == "1",
    )
    shutil.rmtree(base, ignore_errors=True)
    return ok


def main():
    ok = publish_tests()
    ok &= languages()
    ok &= render_tests()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
