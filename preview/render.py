#!/usr/bin/env python3
"""Render a foamy plugin's popup states to PNGs in an isolated offscreen shell.

  preview/render.py <plugin-dir> [--host 4.5|4.0|both] [--out DIR]
                    [--preview FILE] [--states a,b] [--theme dark|light|FILE]
                    [--language da] [--position top|bottom|left|right] [--rounding 6]

The plugin supplies <plugin>/preview/Preview.qml (see README.md, "Preview"):
an Item with `required property QtObject bar`, `required property Item
anchorItem`, `property var previewStates`, `property string previewState`
and `readonly property Item popup` (its FoamyPopup, fed mock data). For each
state the harness writes <state>-screen.png (1920x1080: bar strip plus the
popup where FoamyPopup's real geometry puts it) and <state>.png (the card).
`popup` may be a FoamyPopup, a FoamyPopupCard (declare it `var`; its card is
copied onto the screen at its anchor), or for service plugins any Item with a
`cardItem`, drawn in screen coordinates. Without a cardItem only the screen
is captured.

Nothing touches ~/.config, the live session or its D-Bus: see preview/harness.py.
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402


def render(plugin, host, out, preview=None, states=None, theme="dark", language=None, position="top", rounding=6, keep=False,
           timeout=120, bus="private", lenient=False):
    plugin = Path(plugin).resolve()
    preview = Path(preview).resolve() if preview else plugin / "preview/Preview.qml"
    if not preview.is_file():
        raise SystemExit(f"no preview file: {preview}")
    try:
        relative = preview.relative_to(plugin)
    except ValueError:
        raise SystemExit("the preview file must live inside the plugin directory")
    shell = (Path(__file__).resolve().parent / "PreviewShell.qml.in").read_text().replace("@PREVIEW@", relative.as_posix())
    run = harness.Run(host, shell, plugin=plugin, theme=theme, language=language, prefix=f"foamy-kit-preview-{host}-",
                      bus=bus)
    run.env.update({"FOAMY_POSITION": position, "FOAMY_ROUNDING": str(rounding), "FOAMY_STATES": ",".join(states or [])})
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    shots = []
    try:
        run.run(timeout=timeout)
        for line in run.log.splitlines():
            if "FOAMY SHOT " in line:
                path = Path(line.split("FOAMY SHOT ", 1)[1].split()[0])
                target = out / path.name
                shutil.copyfile(path, target)
                shots.append((target, line.split("FOAMY SHOT ", 1)[1][len(str(path)):].strip()))
        (out / "render.log").write_text(run.log)
        if lenient and not run.ok and shots and "FOAMY DONE" in run.log and "FOAMY FAIL" not in run.log:
            print(f"note: {host} render finished with {len(run.failures())} QML error line(s) (old code); see {out / 'render.log'}",
                  file=sys.stderr)
            return shots
        if not run.ok:
            print("\n".join(run.failures() or run.log.splitlines()[-40:]), file=sys.stderr)
            print(f"render failed on {host}; log at {out / 'render.log'}", file=sys.stderr)
            return None
        return shots
    finally:
        if keep:
            run.stop()
            print(f"kept {run.base}", file=sys.stderr)
        else:
            run.cleanup()


HOST_LABEL = {"4.0": "4.0.6", "4.5": "4.5"}


def dev_copy(plugin, ref, before_preview):
    """Extract `ref` of the plugin repo (git archive: the repo is not touched)
    into a temp dir and make it renderable offscreen. Returns the copy, or
    None when the ref doesn't exist."""
    try:
        data = subprocess.run(["git", "-C", str(plugin), "archive", "--format=tar", ref],
                              capture_output=True, check=True, timeout=60).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    base = Path(tempfile.mkdtemp(prefix=f"foamy-kit-dev-{os.getpid()}-"))
    copy = base / plugin.name
    copy.mkdir()
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(copy, filter="data")
    if before_preview is not None:
        (copy / "preview").mkdir(exist_ok=True)
        shutil.copyfile(before_preview, copy / "preview/Before.qml")
    if not (copy / "kit").exists() and (plugin / "kit").is_dir():
        shutil.copytree(plugin / "kit", copy / "kit")       # helpers for the Before preview
    for qml in copy.rglob("*.qml"):
        text = qml.read_text(errors="replace")
        original = text
        # Pre-kit popups fork KeyboardPanel (a PanelWindow), and some panels
        # own overlay windows: swap only the windows (and their own anchors
        # blocks) for the offscreen stand-in; everything else stays as written.
        if re.search(r"\bPanelWindow\s*\{|WlrLayershell\.", text):
            text = harness.transform_panel_windows(text, qualified=True)
        # Qt 6.12 shadows a bare `Color` with QtQuick's: qualify it so the dev
        # UI looks the way it did when it was written.
        if re.search(r"(?<![\w.$])Color\.[a-z]", text):
            text = re.sub(r"(?<![\w.$])Color\.(?=[a-z])", "Commons.Color.", text)
            if "import qs.Commons as Commons" not in text:
                text = re.sub(r"^(import QtQuick\s*\n)", r"\1import qs.Commons as Commons\n", text, count=1, flags=re.M)
        if text != original:
            qml.write_text(text)
    return copy


def trio(plugin, out, dev_ref="origin/dev", before_preview=None, before_hosts=("4.5", "4.0"), states=None,
         theme="dark", url_prefix="", timeout=120):
    """Render <view>-before.png (dev), <view>-after-4.0.png, <view>-after-4.5.png
    and trio.md (a PR-body table). Returns (rows, before_label)."""
    plugin = Path(plugin).resolve()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"foamy-kit-trio-{os.getpid()}-"))
    after = {}
    try:
        for host in ("4.0", "4.5"):
            shots = render(plugin, host, work / f"after-{host}", states=states, theme=theme, timeout=timeout)
            after[host] = {}
            for path, _ in shots or []:
                if not path.name.endswith("-screen.png"):
                    target = out / f"{path.stem}-after-{host}.png"
                    shutil.copyfile(path, target)
                    after[host][path.stem] = target
        before, before_label = {}, ""
        picked = Path(before_preview).resolve() if before_preview else plugin / "preview/Before.qml"
        copy = dev_copy(plugin, dev_ref, picked if picked.is_file() else None)
        if copy is None:
            before_label = f"Before ({dev_ref}: not found)"
        else:
            preview = copy / ("preview/Before.qml" if (copy / "preview/Before.qml").is_file() else "preview/Preview.qml")
            if not preview.is_file():
                before_label = "Before (dev: no preview/Before.qml)"
            reason = ""
            for host in before_hosts if preview.is_file() else ():
                shots = render(copy, host, work / f"before-{host}", preview=preview, states=states, theme=theme,
                               timeout=timeout, lenient=True)
                # A pre-kit fork on the 4.5 full-screen bar window gets a 120 px
                # card at the wrong edge (the bug the kit fixed): that is not
                # the dev design, so try the next host.
                clipped = [info for _, info in shots or [] if re.search(r"\bavail (\d+)", info)
                           and int(re.search(r"\bavail (\d+)", info).group(1)) <= 120]
                if shots and clipped and host != before_hosts[-1]:
                    print(f"before: dev's popup is clipped on {HOST_LABEL[host]} (old fork); trying the next host", file=sys.stderr)
                    reason = "popup fork clipped on " + HOST_LABEL[host]
                    continue
                if shots:
                    for path, _ in shots:
                        if not path.name.endswith("-screen.png"):
                            target = out / f"{path.stem}-before.png"
                            shutil.copyfile(path, target)
                            before[path.stem] = target
                    fallback = host != before_hosts[0]
                    before_label = f"Before (dev, {HOST_LABEL[host]} host" + (f"; {reason})" if fallback else ")")
                    break
                print(f"before: dev did not render on {HOST_LABEL[host]}", file=sys.stderr)
                reason = f"did not render on {HOST_LABEL[host]}"
            else:
                if preview.is_file():
                    before_label = "Before (dev did not render)"
            shutil.rmtree(copy.parent, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    views = list(after.get("4.5", {}))
    views += [v for v in after.get("4.0", {}) if v not in views]
    views += [v for v in before if v not in views]
    prefix = url_prefix.rstrip("/") + "/" if url_prefix else ""
    cell = lambda files, view, alt: f"![{alt}]({prefix}{files[view].name})" if view in files else "—"
    lines = [f"| View | {before_label} | After 4.0.6 | After 4.5 |", "|---|---|---|---|"]
    for view in views:
        lines.append(f"| {view} | {cell(before, view, view + ' before')} | {cell(after.get('4.0', {}), view, view + ' after 4.0.6')}"
                     f" | {cell(after.get('4.5', {}), view, view + ' after 4.5')} |")
    (out / "trio.md").write_text("\n".join(lines) + "\n")
    return lines, before_label


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plugin")
    parser.add_argument("--host", default="4.5", choices=["4.0", "4.5", "both"])
    parser.add_argument("--out", default=None, help="output directory (default /tmp/foamy-preview-<plugin>)")
    parser.add_argument("--preview", default=None)
    parser.add_argument("--states", default="", help="comma-separated subset of previewStates")
    parser.add_argument("--theme", default="dark", help="dark, light, or a colors.toml path")
    parser.add_argument("--language", default=None, help="language code (4.5 only)")
    parser.add_argument("--position", default="top", choices=["top", "bottom", "left", "right"])
    parser.add_argument("--rounding", type=int, default=6, help="Hyprland decoration:rounding to simulate")
    parser.add_argument("--keep", action="store_true", help="keep the temporary shell root")
    parser.add_argument("--timeout", type=int, default=120, help="seconds before the render is killed")
    parser.add_argument("--bus", default="private", choices=["private", "none"],
                        help="session D-Bus: a private daemon (default) or none; never the desktop's")
    parser.add_argument("--trio", action="store_true",
                        help="Before (dev) / After 4.0.6 / After 4.5 per view, plus trio.md")
    parser.add_argument("--dev-ref", default="origin/dev", help="git ref for Before (default origin/dev)")
    parser.add_argument("--before-preview", default=None,
                        help="preview for the dev tree (default <plugin>/preview/Before.qml, else dev's preview/Preview.qml)")
    parser.add_argument("--before-host", default="4.5,4.0", help="hosts to try for Before, in order")
    parser.add_argument("--url-prefix", default="", help="image URL prefix for trio.md (e.g. the pr-assets raw URL)")
    args = parser.parse_args()
    harness.install_signal_cleanup()
    if args.trio:
        plugin = Path(args.plugin).resolve()
        out = Path(args.out or f"/tmp/foamy-trio-{plugin.name}")
        lines, label = trio(plugin, out, args.dev_ref, args.before_preview, tuple(h for h in args.before_host.split(",") if h),
                            [s for s in args.states.split(",") if s] or None, args.theme, args.url_prefix, args.timeout)
        print("\n".join(lines))
        print(f"\nPNGs and trio.md in {out}")
        return 0
    plugin = Path(args.plugin).resolve()
    out = Path(args.out or f"/tmp/foamy-preview-{plugin.name}")
    hosts = ["4.0", "4.5"] if args.host == "both" else [args.host]
    status = 0
    for host in hosts:
        target = out / host if len(hosts) > 1 else out
        shots = render(plugin, host, target, args.preview, [s for s in args.states.split(",") if s], args.theme,
                       args.language, args.position, args.rounding, args.keep, args.timeout, args.bus)
        if shots is None:
            status = 1
            continue
        print(f"{host}: {len(shots)} PNGs in {target}")
        for path, info in shots:
            print(f"  {path}{'  ' + info if info else ''}")
    return status


if __name__ == "__main__":
    sys.exit(main())
