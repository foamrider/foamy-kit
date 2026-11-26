#!/usr/bin/env python3
"""Demo preview render on 4.5 (a preview that logs an error fails the
render; the mock bar's colours are the theme's bar colours, dark and
light; a card holding an opaque rectangle keeps transparent corners and
a direct grab's pixels, at scale 1 and 1.25), plus publish-screenshots.sh on a throwaway git repository with an
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
from common import KIT_ROOT, harness, read_png, report, synced_demo  # noqa: E402

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
    for index in range(y + 1):
        start = index * (stride + 1)
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
        ok &= bar_colour_test(plugin, host, out_root / host / "bar-colours")
        ok &= card_corner_test(plugin, host, out_root / host / "card-corners")
        ok &= card_corner_test(plugin, host, out_root / host / "card-corners-1.25", scale=1.25)
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return ok


# A rounded card that holds an opaque rectangle without radius, as FoamyTabs'
# open-tab underline (in the card's left half, so a mirrored picture shows),
# and a line of text. 82 high: at scale 1.25 it covers 102.5 device rows.
CORNER_CARD = """import QtQuick
Rectangle {
  width: 120
  height: 82
  radius: 12
  color: "#336699"
  Rectangle {
    x: 10
    y: 40
    width: 60
    height: 2
    color: "#ff0000"
  }
  Text {
    x: 10
    y: 12
    text: "Card"
    color: "#ffffff"
  }
}
"""
CARD_CORNERS = """import QtQuick
Item {
  id: preview
  required property QtObject bar
  required property Item anchorItem
  property var previewStates: ["opaque"]
  property string previewState: ""
  readonly property var popup: holder
  Item {
    id: holder
    readonly property Item cardItem: card
    CornerCard {
      id: card
      x: 100
      y: 100
    }
  }
}
"""
# The same card in a shell of its own, grabbed directly (Item.grabToImage).
DIRECT_GRAB = """import QtQuick
import Quickshell
import "harness"
import "plugin/preview"
ShellRoot {
  FloatingWindow {
    implicitWidth: 400
    implicitHeight: 300
    color: "black"
    CornerCard {
      id: card
      x: 100
      y: 100
    }
  }
  FoamyWait {
    id: wait
  }
  Component.onCompleted: wait.waitFor(function () {
    return card.Window.window !== null
  }, 10000, function () {
    var started = card.grabToImage(function (result) {
      console.log(result.saveToFile(Quickshell.env("FOAMY_CARD_PNG")) ? "FOAMY DONE" : "FOAMY FAIL SAVE FAILED")
      Qt.quit()
    })
    if (!started) {
      console.log("FOAMY FAIL the direct grab did not start")
      Qt.quit()
    }
  }, "the card is in its window")
}
"""


def direct_grab(plugin, host, path, scale):
    """Write the card's direct grab at `scale` to `path`; a run that fails
    writes nothing there."""
    run = harness.Run(host, DIRECT_GRAB, plugin=plugin, scale=scale, prefix=f"foamy-kit-direct-grab-{host}-")
    run.env["FOAMY_CARD_PNG"] = str(path)
    run.run(timeout=60)
    run.cleanup()
    if not run.ok:
        path.unlink(missing_ok=True)


def card_corner_test(plugin, host, out, scale=1.0):
    """The card picture of a card that holds a fully opaque rectangle
    without radius keeps its alpha channel: transparent corners outside
    the rounded card, and every pixel the card fully covers the one a
    direct grab of the card has. The software renderer took such a grab
    for opaque and wrote it RGB with black corners. At scale 1 the card
    covers whole device pixels, and the reference is its region of the
    screen picture, itself a direct grab. At 1.25 it covers 102.5 device
    rows, which a direct grab of the card resamples to 103, so there the
    reference is a direct grab of the same card at the same scale."""
    label = f"preview {host} at scale {scale}"
    (plugin / "preview/CornerCard.qml").write_text(CORNER_CARD)
    preview = plugin / "preview/CardCorners.qml"
    preview.write_text(CARD_CORNERS)
    shots = render.render(plugin, host, out, preview=preview, scale=scale)
    if scale == 1.0:
        reference_png, origin = out / "opaque-screen.png", 100
    else:
        reference_png, origin = out / "direct.png", 0
        direct_grab(plugin, host, reference_png, scale)
    preview.unlink()
    (plugin / "preview/CornerCard.qml").unlink()
    if shots is None or not reference_png.is_file():
        return report(f"{label}: a card holding an opaque rectangle renders, and its reference", False)
    _, _, reference = read_png(reference_png)
    width, height, card = read_png(out / "opaque.png")
    corners = [card(0, 0), card(width - 1, 0), card(0, height - 1), card(width - 1, height - 1)]
    # Qt rounds the size to device pixels half up (QSizeF::toSize()).
    expected = (int(120 * scale + 0.5), int(82 * scale + 0.5))
    ok = report(
        f"{label}: a card holding an opaque rectangle has transparent corners",
        (width, height) == expected and all(pixel[3] == 0 for pixel in corners),
        f"{width}x{height}, expected {expected}; corners {corners}",
    )
    covered = [(x, y) for y in range(height) for x in range(width) if card(x, y)[3] == 255]
    differ = [(x, y) for x, y in covered if card(x, y)[:3] != reference(origin + x, origin + y)[:3]]
    bar = card(round(20 * scale), round(41 * scale))
    ok &= report(
        f"{label}: every pixel the card fully covers is the direct grab's, the rectangle included",
        len(covered) > width * height // 2 and not differ and bar == (255, 0, 0, 255),
        f"{len(differ)} of {len(covered)} differ, first {differ[:3]}; rectangle pixel {bar}",
    )
    return ok


# A card of four swatches, each drawn in one colour the preview's `bar`
# hands a plugin, as the host's bar API hands them to host parts a popup
# shows (PanelSlider's track, fill and knob).
BAR_SWATCHES = """import QtQuick
Item {
  id: preview
  required property QtObject bar
  required property Item anchorItem
  property var previewStates: ["bar"]
  property string previewState: ""
  readonly property var popup: card
  Item {
    id: card
    readonly property Item cardItem: swatches
    Row {
      id: swatches
      x: 100
      y: 100
      Repeater {
        model: [preview.bar.foreground, preview.bar.barForeground, preview.bar.background, preview.bar.urgent]
        Rectangle {
          required property color modelData
          width: 20
          height: 20
          color: modelData
        }
      }
    }
  }
}
"""


def bar_colour_test(plugin, host, out):
    """The preview's bar hands a plugin the theme's bar colours, as the host
    bar does (Bar.qml: foreground and barForeground from the bar text,
    background from the bar background, urgent from the bar's active
    colour, here the theme's red), in the dark and the light theme. A light
    picture of a bar-coloured host part (foamy-monitor's brightness slider)
    then shows it as the host does, not white."""
    preview = plugin / "preview/BarColours.qml"
    preview.write_text(BAR_SWATCHES)
    ok = True
    for theme in ("dark", "light"):
        toml = (KIT_ROOT / f"preview/themes/{theme}.toml").read_text()
        colour = {
            key: re.search(rf'^{key} = "#([0-9a-f]{{6}})"$', toml, re.M).group(1)
            for key in ("foreground", "background", "red")
        }
        expected = [colour["foreground"], colour["foreground"], colour["background"], colour["red"]]
        shots = render.render(plugin, host, out / theme, preview=preview, theme=theme)
        got = []
        if shots is not None:
            width, height, pixel = read_png(out / theme / "bar.png")
            got = ["%02x%02x%02x" % pixel(i * 20 + 10, 10)[:3] for i in range(4)] if (width, height) == (80, 20) else []
        ok &= report(
            f"preview {host} {theme}: the bar's foreground, barForeground, background and urgent are the theme's bar colours",
            got == expected,
            f"got {got}, expected {expected}",
        )
    preview.unlink()
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
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-publish-"))
    try:
        return publish_cases(base)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def publish_cases(base):
    ok = True
    env = git_env(base)
    repo = base / "foamy-example"
    repo.mkdir()
    remote = base / "remote.git"
    pngs = base / "pngs"
    pngs.mkdir()
    for name in ("devices.png", "empty.png"):
        tiny_png(pngs / name)
    script = KIT_ROOT / "preview/publish-screenshots.sh"

    def git(*a, cwd=repo, check=True):
        """stdout of git. A setup step stops the file at once; a query that a
        check reads (check=False) gives "" on failure, so one broken publish
        fails its own checks and the render and language checks still run."""
        return subprocess.run(
            ["git", "-C", str(cwd), *a], capture_output=True, text=True, check=check, env=env, timeout=60
        ).stdout

    def query(*a, cwd=repo):
        return git(*a, cwd=cwd, check=False)

    def pr_assets():
        return query("rev-parse", "--verify", "-q", "refs/heads/pr-assets").strip()

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
    # Each case compares pr-assets with its own start, so a subdir that gets
    # through fails only its own check.
    for subdir in ("/abs", "a/../../x", "a b", "$(id)", ""):
        before, branch = tree(base), pr_assets()
        result = publish(pngs, subdir)
        ok &= report(
            f"publish-screenshots refuses the subdir {subdir!r} and writes nothing",
            result.returncode == 2
            and "subdir must be a relative path" in result.stderr
            and pr_assets() == branch
            and query("worktree", "list").count("\n") == 1
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
        and query("rev-list", "--count", "pr-assets").strip() == "1"
        and "fix-omarchy-45/demo/devices.png" in query("ls-tree", "-r", "--name-only", "pr-assets"),
        result.stderr.strip(),
    )
    ok &= report(
        "publish-screenshots leaves the working tree and branch alone",
        query("status", "--porcelain") == status_before
        and query("branch", "--show-current").strip() == "dev"
        and "README.md" not in query("ls-tree", "-r", "--name-only", "pr-assets"),
    )
    ok &= report(
        "publish-screenshots prints raw URLs and the push command, without pushing",
        "https://raw.githubusercontent.com/foamrider/foamy-example/pr-assets/fix-omarchy-45/demo/devices.png"
        in result.stdout
        and f"git -C {repo} push origin pr-assets" in result.stdout
        # Strict: an unreadable remote must not look like an empty one.
        and git("for-each-ref", cwd=remote) == ""
        and not query("worktree", "list").count("\n") > 1,
        result.stdout.strip()[-300:],
    )
    again = publish(pngs, "fix-omarchy-45/demo")
    ok &= report(
        "publish-screenshots is idempotent",
        again.returncode == 0
        and "already up to date" in again.stdout
        and query("rev-list", "--count", "pr-assets").strip() == "1",
    )
    return ok


def main():
    ok = publish_tests()
    ok &= languages()
    ok &= render_tests()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
