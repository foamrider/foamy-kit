#!/usr/bin/env python3
"""foamy-kit: copy stamped kit files into plugins, verify them, lint designs.

Used through ../sync.sh and ../check.sh; see README.md. Standard library only.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
KIT_DIR = KIT_ROOT / "kit"
STAMP_TAIL = "— do not edit; change foamy-kit and run sync"
STAMP_RE = re.compile(r"^(//|#) foamy-kit (\S+) ([0-9a-f]{64}) ")
LOCK_NAME = "foamy-kit.lock"
CHECK_NAME = "tests/kit-check.sh"


class KitError(Exception):
    pass


# --------------------------------------------------------------------- stamps

def kit_version():
    return (KIT_ROOT / "VERSION").read_text().strip()


def kit_revision():
    try:
        out = subprocess.run(["git", "-C", str(KIT_ROOT), "rev-parse", "--short=12", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        rev = out.stdout.strip() if out.returncode == 0 else ""
        dirty = subprocess.run(["git", "-C", str(KIT_ROOT), "status", "--porcelain", "--", "kit", "VERSION", "tools"],
                               capture_output=True, text=True, timeout=10).stdout.strip()
        return (rev or "unknown") + ("+dirty" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def comment_prefix(name):
    return "#" if name.endswith(".sh") or name == "qmldir" else "//"


def stamp_index(lines):
    """Line index for the stamp: after a pragma or shebang, else first."""
    if lines and (lines[0].startswith("pragma ") or lines[0].startswith(".pragma ") or lines[0].startswith("#!")):
        return 1
    return 0


def stamped(name, body, version):
    if not body.endswith(b"\n"):
        raise KitError(f"{name}: kit sources must end with a newline")
    text = body.decode("utf-8")
    lines = text.splitlines(keepends=True)
    stamp = f"{comment_prefix(name)} foamy-kit {version} {sha256(body)} {STAMP_TAIL}\n"
    index = stamp_index(lines)
    return "".join(lines[:index] + [stamp] + lines[index:]).encode("utf-8")


def read_stamp(data):
    """(version, hash, body) for a stamped file, or None."""
    lines = data.decode("utf-8", errors="replace").splitlines(keepends=True)
    for index in (0, 1):
        if index < len(lines):
            match = STAMP_RE.match(lines[index])
            if match:
                body = "".join(lines[:index] + lines[index + 1:]).encode("utf-8")
                return match.group(2), match.group(3), body
    return None


def verify_file(path):
    """None if intact, else a reason."""
    data = path.read_bytes()
    info = read_stamp(data)
    if info is None:
        return "not stamped"
    _, expected, body = info
    if sha256(body) != expected:
        return "edited locally (body no longer matches its stamp)"
    return None


# ----------------------------------------------------------------- components

def load_components():
    return json.loads((KIT_DIR / "components.json").read_text())


def resolve(names, components):
    unknown = [n for n in names if n not in components]
    if unknown:
        raise KitError("unknown component(s): " + ", ".join(unknown) + "; known: " + ", ".join(sorted(components)))
    seen = []

    def visit(name):
        if name in seen:
            return
        seen.append(name)
        for dep in components[name].get("deps", []):
            visit(dep)

    for name in names:
        visit(name)
    return sorted(seen)


def qmldir_for(selected, components):
    lines = []
    for name in selected:
        spec = components[name]
        singletons = set(spec.get("singletons", []))
        for file in spec["files"]:
            if file.endswith(".qml"):
                type_name = file[:-4]
                prefix = "singleton " if type_name in singletons else ""
                lines.append(f"{prefix}{type_name} 1.0 {file}")
    return ("\n".join(sorted(lines, key=lambda l: l.split()[-1])) + "\n").encode()


def read_lock(plugin):
    lock = plugin / LOCK_NAME
    if not lock.is_file():
        return None
    info = {"version": None, "components": [], "files": {}}
    for line in lock.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "version":
            info["version"] = parts[1]
        elif len(parts) == 2 and parts[0] == "components":
            info["components"] = [c for c in parts[1].split(",") if c]
        elif len(parts) == 2 and re.fullmatch(r"[0-9a-f]{64}", parts[0]):
            info["files"][parts[1]] = parts[0]
    return info


# ----------------------------------------------------------------------- sync

def planned_files(selected, components, version):
    """{relative path: bytes} for everything sync owns in a plugin."""
    files = {}
    notices = set()
    for name in selected:
        for file in components[name]["files"]:
            body = (KIT_DIR / file).read_bytes()
            files[f"kit/{file}"] = stamped(file, body, version)
        notices.update(components[name].get("notices", []))
    files["kit/qmldir"] = stamped("qmldir", qmldir_for(selected, components), version)
    for notice in sorted(notices):
        files[f"kit/{notice}"] = (KIT_ROOT / notice).read_bytes()
    template = (KIT_ROOT / "tools/kit-check.sh.in").read_bytes()
    files[CHECK_NAME] = stamped("kit-check.sh", template, version)
    return files


def lock_bytes(version, selected, files):
    lines = [
        "# foamy-kit.lock: written by foamy-kit sync.sh; do not edit.",
        "# Hashes are of each file's body (the file without its stamp line);",
        "# notices are hashed whole. tests/kit-check.sh verifies them.",
        f"version {version}",
        f"source {kit_revision()}",
        "components " + ",".join(selected),
    ]
    for rel in sorted(files):
        info = read_stamp(files[rel])
        lines.append(f"{info[1] if info else sha256(files[rel])}  {rel}")
    return ("\n".join(lines) + "\n").encode()


def lock_core(data):
    """Lock content minus the source line (which changes with every kit commit)."""
    return b"\n".join(l for l in data.split(b"\n") if not l.startswith(b"source "))


def sync_plugin(plugin, names, force=False, dry_run=False, validate=True, out=print, add=None):
    plugin = Path(plugin).resolve()
    if not (plugin / "manifest.json").is_file():
        raise KitError(f"{plugin}: not a plugin (no manifest.json)")
    components = load_components()
    lock = read_lock(plugin)
    if names is None:
        names = lock["components"] if lock and lock["components"] else sorted(components)
    if add:
        names = sorted(set(names) | set(add))
    selected = resolve(names, components)
    version = kit_version()
    files = planned_files(selected, components, version)

    # Preflight: refuse before writing anything.
    problems = []
    owned = set(lock["files"]) if lock else set()
    kit_dir = plugin / "kit"
    if kit_dir.is_symlink():
        problems.append("kit/ is a symlink")
    existing = []
    if kit_dir.is_dir():
        for path in sorted(kit_dir.rglob("*")):
            if path.is_symlink():
                problems.append(f"{path.relative_to(plugin)} is a symlink (the validator rejects symlinks)")
            elif path.is_file():
                existing.append(str(path.relative_to(plugin)))
    check_path = plugin / CHECK_NAME
    if check_path.exists() or check_path.is_symlink():
        existing.append(CHECK_NAME)
    removals = []
    for rel in existing:
        path = plugin / rel
        if path.is_symlink():
            continue
        data = path.read_bytes()
        info = read_stamp(data)
        if info is None:
            if rel in owned and sha256(data) == lock["files"][rel]:
                pass  # an unmodified notice
            elif rel in files and data == files[rel]:
                pass
            elif not force:
                problems.append(f"{rel} is not a foamy-kit file (or a notice was edited); move it out of kit/ or use --force")
                continue
        else:
            if sha256(info[2]) != info[1] and not force:
                problems.append(f"{rel} was edited locally; move the change into foamy-kit, then re-run (or --force to discard it)")
                continue
        if rel not in files:
            removals.append(rel)
    if problems:
        raise KitError(f"{plugin.name}: refusing to sync:\n  " + "\n  ".join(problems))

    changed = []
    for rel, data in sorted(files.items()):
        path = plugin / rel
        if path.is_file() and not path.is_symlink() and path.read_bytes() == data:
            continue
        changed.append(rel)
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_symlink():
                path.unlink()
            path.write_bytes(data)
            if rel.endswith(".sh"):
                path.chmod(0o755)
            else:
                path.chmod(0o644)
    for rel in removals:
        changed.append(f"-{rel}")
        if not dry_run:
            (plugin / rel).unlink()
    new_lock = lock_bytes(version, selected, files)
    lock_path = plugin / LOCK_NAME
    old_lock = lock_path.read_bytes() if lock_path.is_file() else b""
    if lock_core(old_lock) != lock_core(new_lock):
        changed.append(LOCK_NAME)
        if not dry_run:
            lock_path.write_bytes(new_lock)

    verb = "would update" if dry_run else "updated"
    if changed:
        out(f"{plugin.name}: foamy-kit {version}: {verb} {len(changed)} file(s): " + ", ".join(changed))
    else:
        out(f"{plugin.name}: foamy-kit {version}: up to date ({len(files)} files)")

    if validate and not dry_run:
        validator = shutil.which("omarchy-plugin-validate") or "/usr/share/omarchy/bin/omarchy-plugin-validate"
        if os.access(validator, os.X_OK):
            result = subprocess.run([validator, str(plugin)], capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise KitError(f"{plugin.name}: omarchy-plugin-validate failed after sync:\n{result.stderr or result.stdout}")
    return changed


# ---------------------------------------------------------------------- check

def verify_plugin(plugin):
    """List of integrity problems (empty when intact)."""
    plugin = Path(plugin)
    lock = read_lock(plugin)
    if lock is None:
        return [f"no {LOCK_NAME} (run sync.sh)"]
    problems = []
    if not lock["version"]:
        problems.append(f"{LOCK_NAME} has no version")
    for rel, expected in sorted(lock["files"].items()):
        path = plugin / rel
        if path.is_symlink() or not path.is_file():
            problems.append(f"{rel} is missing or not a regular file")
            continue
        data = path.read_bytes()
        info = read_stamp(data)
        if info is None:
            if sha256(data) != expected:
                problems.append(f"{rel} was edited (hash differs from the lock)")
            continue
        version, stamp_hash, body = info
        if sha256(body) != stamp_hash:
            problems.append(f"{rel} was edited locally")
        if stamp_hash != expected:
            problems.append(f"{rel} stamp differs from the lock")
        if version != lock["version"]:
            problems.append(f"{rel} is stamped {version}, lock says {lock['version']}")
    kit_dir = plugin / "kit"
    if kit_dir.is_dir():
        for path in sorted(kit_dir.rglob("*")):
            rel = str(path.relative_to(plugin))
            if (path.is_file() or path.is_symlink()) and rel not in lock["files"]:
                problems.append(f"{rel} is not part of foamy-kit")
    return problems


# ----------------------------------------------------------------------- lint

RULES = {
    "unqualified-color": "use Commons.Color.* (Qt 6.12's QtQuick Color type shadows a bare Color)",
    "bare-duration": "durations go through FoamyMotion (honours reduced motion)",
    "sans-serif": "use FoamyStyle.fontFamily",
    "radius-x2": "use FoamyStyle.radius",
    "hex-colour": "use Commons.Color or FoamyPalette (theme colours), not a hex literal",
    "unguarded-loop": "infinite animations need `running: … && !FoamyMotion.reduceMotion`",
    "raw-ipc": "use FoamyIpc (4.5 socket fast path, 4.0 fallback)",
    "opt-out-reason": "a foamy-lint opt-out needs a reason: // foamy-lint: allow <rule> — <why>",
    "empty-glyph": "a glyph's text is empty (an icon character was lost); write it as an escape like \"\\u{f0e7}\"",
    "pua-literal": "private-use (icon font) character written literally; editors and tools strip them, use an escape like \"\\u{f0e7}\"",
}
# Reported, but don't fail check.sh (use --strict to fail on them too).
WARNINGS = {"pua-literal"}
EXEMPT = {
    "bare-duration": {"FoamyMotion.qml"},
    "sans-serif": {"FoamyStyle.qml"},
    "radius-x2": {"FoamyStyle.qml"},
    "hex-colour": {"FoamyPalette.qml"},
    "raw-ipc": {"FoamyIpc.qml"},
}
OPT_OUT_RE = re.compile(r"foamy-lint:\s*allow\s+([\w,-]+)(?:\s+(?:—|–|--|-)\s*(\S.*))?")
HEX_RE = re.compile(r"""(["'])#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\1""")
COLOR_RE = re.compile(r"(?<![\w.$])Color\.[a-z]")
DURATION_RE = re.compile(r"\bduration\s*:\s*\d")
SANS_RE = re.compile(r"""["']sans-serif["']""")
RADIUS_RE = re.compile(r"Style\.cornerRadius\s*\*\s*2(?![\d.])")
IPC_RE = re.compile(r"(?<![\w.])(IpcHandler|ShellIpc)\s*\{")
LOOP_RE = re.compile(r"\bloops\s*:\s*(Animation\.Infinite|-1)\b")
GLYPH_OPEN_RE = re.compile(r"\b\w*Glyph\s*\{")
EMPTY_TEXT_RE = re.compile(r"(?<![\w.])text\s*:\s*(\"\"|'')")
PUA_RE = re.compile("[\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd]")


def split_line(line, state):
    """(code with strings kept, code with strings blanked, comment) for one line.

    `state` carries an open /* block comment across lines."""
    code, blank, comment = [], [], ""
    i, quote = 0, None
    while i < len(line):
        ch = line[i]
        nxt = line[i + 1] if i + 1 < len(line) else ""
        if state["block"]:
            if ch == "*" and nxt == "/":
                state["block"] = False
                i += 2
            else:
                i += 1
            continue
        if quote:
            code.append(ch)
            blank.append(" " if ch != quote else ch)
            if ch == "\\" and nxt:
                code.append(nxt)
                blank.append(" ")
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'`":
            quote = ch
            code.append(ch)
            blank.append(ch)
        elif ch == "/" and nxt == "/":
            comment = line[i + 2:]
            break
        elif ch == "/" and nxt == "*":
            state["block"] = True
            i += 2
            continue
        else:
            code.append(ch)
            blank.append(ch)
        i += 1
    return "".join(code), "".join(blank), comment


def lint_text(name, text):
    """List of (line number, rule, excerpt)."""
    base = os.path.basename(name)
    is_qml = name.endswith(".qml")
    state = {"block": False}
    rows = [split_line(l, state) for l in text.splitlines()]
    findings = []

    def allowed(index, rule):
        for j in (index, index - 1):
            if j < 0:
                continue
            code, _, comment = rows[j]
            if j == index - 1 and code.strip():
                continue
            match = OPT_OUT_RE.search(comment)
            if match and rule in match.group(1).split(","):
                return True
        return False

    for index, (code, blank, comment) in enumerate(rows):
        match = OPT_OUT_RE.search(comment)
        if match and not match.group(2):
            findings.append((index + 1, "opt-out-reason", text.splitlines()[index].strip()))
        checks = []
        if is_qml and COLOR_RE.search(blank):
            checks.append("unqualified-color")
        if is_qml and DURATION_RE.search(blank):
            checks.append("bare-duration")
        if SANS_RE.search(code):
            checks.append("sans-serif")
        if RADIUS_RE.search(blank):
            checks.append("radius-x2")
        if HEX_RE.search(code):
            checks.append("hex-colour")
        if is_qml and IPC_RE.search(blank):
            checks.append("raw-ipc")
        if LOOP_RE.search(blank) and not loop_guarded(rows, index):
            checks.append("unguarded-loop")
        if PUA_RE.search(code):
            checks.append("pua-literal")
        for match in GLYPH_OPEN_RE.finditer(blank):
            if glyph_text_empty(rows, index, match.end() - 1):
                checks.append("empty-glyph")
                break
        for rule in checks:
            if base in EXEMPT.get(rule, ()) or allowed(index, rule):
                continue
            findings.append((index + 1, rule, text.splitlines()[index].strip()))
    return findings


def loop_guarded(rows, index):
    """Whether the object block enclosing the `loops:` on rows[index] mentions
    reduceMotion (or FoamyMotion.loopAllowed)."""
    column = LOOP_RE.search(rows[index][1]).start()
    # Walk back from the match to the unmatched "{" that opens its block.
    depth, open_line = 0, None
    for j in range(index, -1, -1):
        text = rows[j][1] if j != index else rows[j][1][:column]
        for ch in reversed(text):
            if ch == "}":
                depth += 1
            elif ch == "{":
                if depth == 0:
                    open_line = j
                    break
                depth -= 1
        if open_line is not None:
            break
    if open_line is None:
        return False
    # Walk forward to its matching "}".
    depth = 0
    for j in range(open_line, len(rows)):
        text = rows[j][1]
        if j == open_line:
            text = text[text.rfind("{", 0, column if j == index else len(text)):]
        if "reduceMotion" in text or "loopAllowed" in text:
            return True
        for ch in text:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return False
    return False


def glyph_text_empty(rows, line, column):
    """Whether the *Glyph { … } block opening at rows[line][column] sets
    `text` to an empty literal (directly, not in a nested object)."""
    depth, buffer = 0, []
    for j in range(line, len(rows)):
        text = rows[j][1][column:] if j == line else rows[j][1]
        for ch in text:
            if ch == "{":
                depth += 1
                if depth > 1:
                    buffer.append("\0")
                continue
            if ch == "}":
                depth -= 1
                if depth == 0:
                    return bool(EMPTY_TEXT_RE.search("".join(buffer)))
                continue
            if depth == 1:
                buffer.append(ch)
        buffer.append("\n")
    return False


def lint_files(plugin):
    plugin = Path(plugin)
    files = []
    try:
        result = subprocess.run(["git", "-C", str(plugin), "ls-files", "-co", "--exclude-standard"],
                                capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            files = [plugin / f for f in result.stdout.splitlines()]
    except (OSError, subprocess.SubprocessError):
        files = []
    if not files:
        files = [p for p in plugin.rglob("*") if p.is_file()]
    keep = []
    for path in files:
        rel = path.relative_to(plugin)
        if path.suffix not in (".qml", ".js") or not path.is_file():
            continue
        if rel.parts[0] in ("tests", "test", "preview", "node_modules") or ".git" in rel.parts:
            continue
        keep.append(path)
    return sorted(keep)


def lint_plugin(plugin):
    findings = []
    for path in lint_files(plugin):
        for line, rule, excerpt in lint_text(str(path), path.read_text(errors="replace")):
            findings.append((str(path.relative_to(plugin)), line, rule, excerpt))
    return findings


# ------------------------------------------------------------------------ cli

def cmd_sync(args):
    names = None
    if args.components:
        names = [n.strip() for n in args.components.split(",") if n.strip()]
    status = 0
    for plugin in args.plugins:
        try:
            add = [n.strip() for n in (args.add or "").split(",") if n.strip()]
            sync_plugin(plugin, names, force=args.force, dry_run=args.dry_run, validate=not args.no_validate, add=add)
        except KitError as error:
            print(f"sync: {error}", file=sys.stderr)
            status = 1
    return status


def cmd_check(args):
    status = 0
    versions = {}
    current = kit_version()
    for plugin in args.plugins:
        plugin = Path(plugin)
        if not (plugin / "manifest.json").is_file():
            continue
        name = plugin.resolve().name
        problems = []
        lock = read_lock(plugin)
        if not args.lint_only:
            if lock is None and args.allow_unsynced:
                pass
            else:
                problems += verify_plugin(plugin)
                if lock and lock["version"]:
                    versions.setdefault(lock["version"], []).append(name)
        findings = [] if args.no_lint else lint_plugin(plugin)
        for problem in problems:
            print(f"{name}: kit: {problem}")
        failing = [f for f in findings if args.strict or f[2] not in WARNINGS]
        for rel, line, rule, excerpt in findings:
            level = "warning: " if rule in WARNINGS and not args.strict else ""
            print(f"{name}/{rel}:{line}: {level}{rule}: {RULES[rule]}\n    {ascii(excerpt[:160])[1:-1]}")
        if problems or failing:
            status = 1
        elif not args.quiet:
            label = f"foamy-kit {lock['version']}" if lock else "not synced"
            print(f"{name}: OK ({label}{', with warnings' if findings else ''})")
    if len(versions) > 1:
        status = 1
        print("kit versions differ: " + "; ".join(f"{v}: {', '.join(sorted(p))}" for v, p in sorted(versions.items())))
    elif versions and current not in versions and not args.quiet:
        print(f"note: plugins are on foamy-kit {next(iter(versions))}; foamy-kit is at {current}")
    return status


def cmd_lint_text(args):
    status = 0
    for name in args.files:
        for line, rule, excerpt in lint_text(name, Path(name).read_text()):
            warning = rule in WARNINGS and not args.strict
            print(f"{name}:{line}: {'warning: ' if warning else ''}{rule}: {ascii(excerpt)[1:-1]}")
            if not warning:
                status = 1
    return status


def main(argv=None):
    parser = argparse.ArgumentParser(prog="foamykit")
    sub = parser.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync", help="copy stamped kit files into plugins")
    sync.add_argument("plugins", nargs="+")
    sync.add_argument("--components", help="comma-separated components (default: the lock's, or all)")
    sync.add_argument("--add", help="comma-separated components to add to the plugin's current set")
    sync.add_argument("--force", action="store_true", help="overwrite locally edited kit files")
    sync.add_argument("--dry-run", action="store_true")
    sync.add_argument("--no-validate", action="store_true", help="skip omarchy-plugin-validate")
    sync.set_defaults(func=cmd_sync)
    check = sub.add_parser("check", help="verify kit versions, stamps and design lint")
    check.add_argument("plugins", nargs="+")
    check.add_argument("--lint-only", action="store_true")
    check.add_argument("--no-lint", action="store_true")
    check.add_argument("--allow-unsynced", action="store_true", help="don't fail plugins without a lock")
    check.add_argument("--quiet", action="store_true")
    check.add_argument("--strict", action="store_true", help="fail on warnings (pua-literal) too")
    check.set_defaults(func=cmd_check)
    lint = sub.add_parser("lint", help="lint individual files")
    lint.add_argument("files", nargs="+")
    lint.add_argument("--strict", action="store_true")
    lint.set_defaults(func=cmd_lint_text)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
