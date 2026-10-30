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

Nothing touches ~/.config or the live session: see preview/harness.py.
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402


def render(plugin, host, out, preview=None, states=None, theme="dark", language=None, position="top", rounding=6, keep=False):
    plugin = Path(plugin).resolve()
    preview = Path(preview).resolve() if preview else plugin / "preview/Preview.qml"
    if not preview.is_file():
        raise SystemExit(f"no preview file: {preview}")
    try:
        relative = preview.relative_to(plugin)
    except ValueError:
        raise SystemExit("the preview file must live inside the plugin directory")
    shell = (Path(__file__).resolve().parent / "PreviewShell.qml.in").read_text().replace("@PREVIEW@", f"plugin/{relative}")
    run = harness.Run(host, shell, plugin=plugin, theme=theme, language=language, prefix=f"foamy-kit-preview-{host}-")
    run.env.update({"FOAMY_POSITION": position, "FOAMY_ROUNDING": str(rounding), "FOAMY_STATES": ",".join(states or [])})
    run.run(timeout=120)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    shots = []
    for line in run.log.splitlines():
        if "FOAMY SHOT " in line:
            path = Path(line.split("FOAMY SHOT ", 1)[1].split()[0])
            target = out / path.name
            shutil.copyfile(path, target)
            shots.append((target, line.split("FOAMY SHOT ", 1)[1][len(str(path)):].strip()))
    (out / "render.log").write_text(run.log)
    if not run.ok:
        print("\n".join(run.failures() or run.log.splitlines()[-40:]), file=sys.stderr)
        print(f"render failed on {host}; log kept at {run.base}", file=sys.stderr)
        return None
    if not keep:
        run.cleanup()
    return shots


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
    args = parser.parse_args()
    plugin = Path(args.plugin).resolve()
    out = Path(args.out or f"/tmp/foamy-preview-{plugin.name}")
    hosts = ["4.0", "4.5"] if args.host == "both" else [args.host]
    status = 0
    for host in hosts:
        target = out / host if len(hosts) > 1 else out
        shots = render(plugin, host, target, args.preview, [s for s in args.states.split(",") if s], args.theme,
                       args.language, args.position, args.rounding, args.keep)
        if shots is None:
            status = 1
            continue
        print(f"{host}: {len(shots)} PNGs in {target}")
        for path, info in shots:
            print(f"  {path}{'  ' + info if info else ''}")
    return status


if __name__ == "__main__":
    sys.exit(main())
