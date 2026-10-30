#!/usr/bin/env python3
"""Add or refresh FoamyIcon entries from a lucide-static package.

  npm pack lucide-static@latest            # in an empty directory
  tar -xzf lucide-static-*.tgz
  tools/update-icons.py package/icons info bell search …
  tools/update-icons.py --as github=github <old-package>/icons github

Reads only the SVG files (never runs anything from the package), keeps the
inner elements (path, circle, rect, line, polyline, polygon, ellipse), and
rewrites the `paths` table in kit/FoamyIcon.qml sorted by name. Record the
Lucide version in the FoamyIcon header and CHANGELOG.md.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ICON_QML = Path(__file__).resolve().parents[1] / "kit/FoamyIcon.qml"
ELEMENT = re.compile(r"<(path|circle|rect|line|polyline|polygon|ellipse)\b([^>]*?)\s*/>", re.S)


def inner(svg_text):
    parts = []
    for tag, attrs in ELEMENT.findall(svg_text):
        attrs = " ".join(attrs.split())
        parts.append(f"<{tag} {attrs}/>")
    if not parts:
        raise SystemExit("no drawable elements found")
    return "".join(parts)


def read_table(text):
    start = text.index("readonly property var paths: ({") + len("readonly property var paths: ({")
    end = text.index("\n  })", start)
    table = {}
    for line in text[start:end].strip().splitlines():
        match = re.match(r'\s*("(?:[^"\\]|\\.)*")\s*:\s*("(?:[^"\\]|\\.)*"),?\s*$', line)
        if not match:
            raise SystemExit(f"unexpected icon table line: {line!r}")
        table[json.loads(match.group(1))] = json.loads(match.group(2))
    return start, end, table


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("icons_dir")
    parser.add_argument("names", nargs="+", help="Lucide icon file names (without .svg)")
    parser.add_argument("--as", dest="aliases", action="append", default=[], help="kit-name=lucide-name")
    args = parser.parse_args()
    icons = Path(args.icons_dir)
    aliases = dict(a.split("=", 1) for a in args.aliases)
    reverse = {lucide: kit for kit, lucide in aliases.items()}
    text = ICON_QML.read_text()
    start, end, table = read_table(text)
    for name in args.names:
        svg = icons / f"{name}.svg"
        if not svg.is_file():
            raise SystemExit(f"missing {svg}")
        table[reverse.get(name, name)] = inner(svg.read_text())
    body = "\n" + ",\n".join(f"    {json.dumps(k)}: {json.dumps(v)}" for k, v in sorted(table.items()))
    ICON_QML.write_text(text[:start] + body + text[end:])
    print(f"{len(table)} icons in {ICON_QML}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
