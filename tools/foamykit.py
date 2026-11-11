#!/usr/bin/env python3
"""foamy-kit: copy stamped kit files into plugins, verify them, lint designs.

Used through ../sync.sh and ../check.sh; see README.md. The native helper
build tool is kit/native/native.py (tools/build-native.sh runs a plugin's copy).
Standard library only.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
KIT_DIR = KIT_ROOT / "kit"


def _load_native():
    """kit/native/native.py, the native helper build tool FoamyNative copies
    into plugins; check.sh uses its checks (python3 -I keeps kit/ off sys.path)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("foamy_native", KIT_DIR / "native/native.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["foamy_native"] = module
    spec.loader.exec_module(module)
    return module


native = _load_native()
from foamy_native import KitError, verify_native  # noqa: E402

STAMP_TAIL = "— do not edit; change foamy-kit and run sync"
STAMP_RE = re.compile(r"^(//|#) foamy-kit (\S+) ([0-9a-f]{64}) ")
LOCK_NAME = "foamy-kit.lock"
CHECK_NAME = "tests/kit-check.sh"
REVIEW_NAME = "REVIEW.md"
# The tooling every plugin carries (README "Tooling"): the one validation
# command, its engine, the pinned tool versions and the shared linter and
# formatter configuration. {path in the plugin: source in foamy-kit}. The
# sources are the kit's own files (foamy-kit validates itself with them), so
# these are not a component: sync always writes them, stamped like kit code.
# kit/native/native.py (TOOLING_FILES) and tools/kit-check.sh.in list the
# same root paths; tests/test_native.py keeps them in step.
TOOLING_FILES = {
    ".github/workflows/checks.yml": ".github/workflows/checks.yml",
    ".oxlintrc.json": ".oxlintrc.json",
    ".qmlformat.ini": ".qmlformat.ini",
    "kit/tooling/validate.py": "kit/tooling/validate.py",
    "mise.toml": "mise.toml",
    "ruff.toml": "ruff.toml",
    "tests/validate.sh": "tests/validate.sh",
}
# AGENTS.md belongs to the plugin; sync manages only this marked block, which
# points review agents (Codex reads AGENTS.md) at the shared REVIEW.md.
AGENTS_NAME = "AGENTS.md"
AGENTS_MARK = "<!-- foamy-kit review:"
AGENTS_BEGIN = AGENTS_MARK + " begin; managed by foamy-kit sync.sh, edit outside this block -->"
AGENTS_END = AGENTS_MARK + " end -->"
AGENTS_BLOCK = f"""{AGENTS_BEGIN}
## Code review

Follow [REVIEW.md](REVIEW.md) when reviewing or preparing a change. It is the
shared Foamy review standard, synced from foamy-kit. The rest of this file
adds repository-specific rules.
{AGENTS_END}
"""
AGENTS_PLACEHOLDER = b"@AGENTS_BLOCK@"


# --------------------------------------------------------------------- stamps


def kit_version():
    return (KIT_ROOT / "VERSION").read_text().strip()


def kit_revision():
    try:
        out = subprocess.run(
            ["git", "-C", str(KIT_ROOT), "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True, timeout=10
        )
        rev = out.stdout.strip() if out.returncode == 0 else ""
        dirty = subprocess.run(
            [
                "git",
                "-C",
                str(KIT_ROOT),
                "status",
                "--porcelain",
                "--",
                "kit",
                "VERSION",
                "tools",
                REVIEW_NAME,
                *TOOLING_FILES.values(),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        return (rev or "unknown") + ("+dirty" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def comment_prefix(name):
    return "#" if name.endswith((".sh", ".toml", ".py", ".yml", ".ini")) or Path(name).name == "qmldir" else "//"


def stamp_index(name, lines):
    """Line index for the stamp: after a pragma or shebang, else first.

    Rust and TOML files always carry it on line 1: panic locations embed line
    numbers, and a fixed one-line stamp keeps them the same across kit
    versions (`#![...]` is a Rust attribute, not a shebang)."""
    if name.endswith((".rs", ".toml")):
        return 0
    if lines and (lines[0].startswith("pragma ") or lines[0].startswith(".pragma ") or lines[0].startswith("#!")):
        return 1
    return 0


def stamped(name, body, version):
    if not body.endswith(b"\n"):
        raise KitError(f"{name}: kit sources must end with a newline")
    text = body.decode("utf-8")
    lines = text.splitlines(keepends=True)
    stamp = f"{comment_prefix(name)} foamy-kit {version} {sha256(body)} {STAMP_TAIL}\n"
    index = stamp_index(name, lines)
    return "".join(lines[:index] + [stamp] + lines[index:]).encode("utf-8")


def read_stamp(data):
    """(version, hash, body) for a stamped file, or None."""
    lines = data.decode("utf-8", errors="replace").splitlines(keepends=True)
    for index in (0, 1):
        if index < len(lines):
            match = STAMP_RE.match(lines[index])
            if match:
                body = "".join(lines[:index] + lines[index + 1 :]).encode("utf-8")
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


def default_components(components):
    """The first-sync set: every component except opt-in ones (FoamyNative)."""
    return sorted(name for name, spec in components.items() if not spec.get("optIn"))


def component_files(name, spec):
    """[(path in the plugin, kit source)] for one component.

    `files` are relative to kit/ and land under kit/ (glob patterns such as
    `rust/foamy-helper/src/**/*.rs` are expanded, sorted); `rootFiles` maps a
    path in the plugin outside kit/ to its source under kit/."""
    out = []
    for pattern in spec["files"]:
        if any(ch in pattern for ch in "*?["):
            matches = sorted(
                p for p in KIT_DIR.glob(pattern) if p.is_file() and "target" not in p.relative_to(KIT_DIR).parts
            )
            if not matches:
                raise KitError(f"components.json: {name}: {pattern} matches no file")
            out += [(f"kit/{p.relative_to(KIT_DIR).as_posix()}", p) for p in matches]
        else:
            out.append((f"kit/{pattern}", KIT_DIR / pattern))
    for dest, source in sorted(spec.get("rootFiles", {}).items()):
        parts = Path(dest).parts
        if (
            Path(dest).is_absolute()
            or ".." in parts
            or not parts
            or parts[0] == "kit"
            or dest in (LOCK_NAME, CHECK_NAME, REVIEW_NAME, *TOOLING_FILES)
        ):
            raise KitError(f"components.json: {name}: invalid rootFiles path {dest}")
        out.append((dest, KIT_DIR / source))
    return out


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


def lock_path_ok(rel, components=None):
    """True for a path foamy-kit can own: a normalised relative path under kit/,
    tests/kit-check.sh, REVIEW.md, a tooling file, or a component's rootFiles destination. The lock is
    plugin content, so anything else (`../x`, `/etc/x`, `kit/../x`) is refused
    before sync reads, overwrites or deletes it."""
    parts = rel.split("/")
    if rel.startswith("/") or "\\" in rel or any(part in ("", ".", "..") for part in parts):
        return False
    if parts[0] == "kit" and len(parts) > 1:
        return True
    if rel in (CHECK_NAME, REVIEW_NAME) or rel in TOOLING_FILES:
        return True
    components = load_components() if components is None else components
    return any(rel in spec.get("rootFiles", {}) for spec in components.values())


def read_lock(plugin):
    lock = plugin / LOCK_NAME
    if not lock.is_file():
        return None
    info = {"version": None, "components": [], "files": {}}
    components = load_components()
    for line in lock.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "version":
            info["version"] = parts[1]
        elif len(parts) == 2 and parts[0] == "components":
            info["components"] = [c for c in parts[1].split(",") if c]
        elif len(parts) == 2 and re.fullmatch(r"[0-9a-f]{64}", parts[0]):
            if not lock_path_ok(parts[1], components):
                raise KitError(
                    f"{LOCK_NAME} lists {parts[1]!r}, which is not a path foamy-kit owns "
                    "(only kit/…, tests/kit-check.sh, REVIEW.md, the tooling files and component root files); "
                    "fix or delete the lock"
                )
            info["files"][parts[1]] = parts[0]
    return info


def inside(plugin, rel):
    """True when plugin/rel, with its parent directories' symlinks resolved, stays in plugin."""
    try:
        (plugin / rel).parent.resolve().relative_to(plugin.resolve())
    except ValueError:
        return False
    return True


# ----------------------------------------------------------------------- sync


def planned_files(selected, components, version):
    """{relative path: bytes} for everything sync owns in a plugin."""
    files = {}
    notices = set()
    for name in selected:
        for rel, source in component_files(name, components[name]):
            files[rel] = stamped(rel, source.read_bytes(), version)
        notices.update(components[name].get("notices", []))
    files["kit/qmldir"] = stamped("qmldir", qmldir_for(selected, components), version)
    for notice in sorted(notices):
        files[f"kit/{notice}"] = (KIT_ROOT / notice).read_bytes()
    template = (KIT_ROOT / "tools/kit-check.sh.in").read_bytes()
    if template.count(AGENTS_PLACEHOLDER) != 1:
        raise KitError("tools/kit-check.sh.in must contain @AGENTS_BLOCK@ exactly once")
    template = template.replace(AGENTS_PLACEHOLDER, AGENTS_BLOCK.rstrip("\n").encode())
    files[CHECK_NAME] = stamped("kit-check.sh", template, version)
    for rel, source in TOOLING_FILES.items():
        files[rel] = stamped(rel, (KIT_ROOT / source).read_bytes(), version)
    # Hash the guide whole, like license notices, so it stays valid Markdown.
    files[REVIEW_NAME] = (KIT_ROOT / REVIEW_NAME).read_bytes()
    return files


def lock_bytes(version, selected, files):
    lines = [
        "# foamy-kit.lock: written by foamy-kit sync.sh; do not edit.",
        "# Hashes are of each file's body (the file without its stamp line);",
        "# notices and REVIEW.md are hashed whole. tests/kit-check.sh verifies them.",
        f"version {version}",
        f"source {kit_revision()}",
        "components " + ",".join(selected),
    ]
    for rel in sorted(files):
        info = read_stamp(files[rel])
        lines.append(f"{info[1] if info else sha256(files[rel])}  {rel}")
    return ("\n".join(lines) + "\n").encode()


def agents_with_review(current):
    """AGENTS.md bytes with the managed review block added or refreshed.

    `current` is the existing file (None when absent). Text outside the block
    is the plugin's and is kept byte for byte. A damaged block (a marker
    missing, repeated, reordered or edited) raises instead of guessing."""
    if current is None:
        return ("# Notes for coding agents\n\n" + AGENTS_BLOCK).encode()
    try:
        text = current.decode("utf-8")
    except UnicodeDecodeError:
        raise KitError(f"{AGENTS_NAME} is not UTF-8 text") from None
    marks = [match.start() for match in re.finditer(re.escape(AGENTS_MARK), text)]
    if not marks:
        separator = "" if not text else "\n" if text.endswith("\n") else "\n\n"
        return (text + separator + AGENTS_BLOCK).encode()
    start, end = text.find(AGENTS_BEGIN), text.find(AGENTS_END)
    stop = end + len(AGENTS_END)
    if (
        len(marks) != 2
        or marks != [start, end]
        or (start and text[start - 1] != "\n")
        or text[stop : stop + 1] not in ("", "\n")
    ):
        raise KitError(
            f"{AGENTS_NAME}: the foamy-kit review block is damaged (expected one begin and one end "
            "marker, each on its own line); restore or delete the block, then re-run"
        )
    return (text[:start] + AGENTS_BLOCK + text[stop + 1 :]).encode()


def agents_problems(plugin):
    """Integrity problems with the plugin's AGENTS.md review block."""
    path = plugin / AGENTS_NAME
    if path.is_symlink() or not path.is_file():
        return [f"{AGENTS_NAME} is missing or not a regular file (run sync.sh)"]
    data = path.read_bytes()
    try:
        current = agents_with_review(data) == data
    except KitError as error:
        return [str(error)]
    return [] if current else [f"{AGENTS_NAME} lacks the current foamy-kit review block (run sync.sh)"]


def replace_file(path, data):
    """Atomically replace `path`, keeping its permission bits (0644 if new)."""
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


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
        names = lock["components"] if lock and lock["components"] else default_components(components)
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
    # Every path sync may write or delete must stay inside the plugin, even
    # through a symlinked parent directory (tests/ -> elsewhere).
    for rel in sorted(owned | set(files)):
        if not inside(plugin, rel):
            problems.append(f"{rel} resolves outside the plugin (a parent directory is a symlink)")
    # Root files (including the shared review guide), owned now or planned.
    for rel in sorted(rel for rel in owned | set(files) if not rel.startswith("kit/") and rel != CHECK_NAME):
        path = plugin / rel
        if path.is_symlink():
            problems.append(f"{rel} is a symlink (the validator rejects symlinks)")
        elif path.exists():
            existing.append(rel)
    removals = []
    for rel in existing:
        path = plugin / rel
        if path.is_symlink():
            continue
        data = path.read_bytes()
        info = read_stamp(data)
        if info is None:
            if rel in owned and sha256(data) == lock["files"][rel]:
                pass  # an unmodified notice or shared document
            elif rel in files and data == files[rel]:
                pass
            elif not force:
                problems.append(
                    f"{rel} is not a foamy-kit file (or a copied file was edited); preserve it elsewhere before syncing or use --force"
                )
                continue
        else:
            if sha256(info[2]) != info[1] and not force:
                problems.append(
                    f"{rel} was edited locally; move the change into foamy-kit, then re-run (or --force to discard it)"
                )
                continue
        if rel not in files:
            removals.append(rel)
    agents_path = plugin / AGENTS_NAME
    agents_old = agents_new = None
    if agents_path.is_symlink() or (agents_path.exists() and not agents_path.is_file()):
        problems.append(f"{AGENTS_NAME} is a symlink or not a regular file")
    else:
        try:
            agents_old = agents_path.read_bytes() if agents_path.exists() else None
            agents_new = agents_with_review(agents_old)
        except KitError as error:
            problems.append(str(error))
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
            # A removed root file's own directories (.github/workflows), once empty.
            parent = (plugin / rel).parent
            while (
                not rel.startswith("kit/")
                and parent != plugin
                and not parent.is_symlink()
                and not any(parent.iterdir())
            ):
                parent.rmdir()
                parent = parent.parent
    if not dry_run and kit_dir.is_dir():
        # Directories of removed subdirectory components (kit/rust/…).
        for path in sorted(kit_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir() and not path.is_symlink() and not any(path.iterdir()):
                path.rmdir()
    if agents_new != agents_old:
        changed.append(AGENTS_NAME)
        if not dry_run:
            replace_file(agents_path, agents_new)
    new_lock = lock_bytes(version, selected, files)
    lock_path = plugin / LOCK_NAME
    old_lock = lock_path.read_bytes() if lock_path.is_file() else b""
    if lock_core(old_lock) != lock_core(new_lock):
        changed.append(LOCK_NAME)
        if not dry_run:
            lock_path.write_bytes(new_lock)
    # A native.pin's `kit` line names the kit its binaries match. After the
    # files above, a pin whose source hash still matches is fresh at this
    # version: refresh only that line (never the source hash or checksums).
    # A stale pin keeps the version that built it until the rebuild.
    if "FoamyNative" in selected:
        for pin_path in native.native_pins(plugin):
            crate = pin_path.parent.name
            if not inside(plugin, f"{crate}/{native.PIN_NAME}"):
                continue
            pin = native.read_pin(pin_path)
            if not dry_run and native.native_source_hash(plugin, crate) != pin.get("source"):
                continue
            data = native.refresh_pin_kit(pin_path, version)
            if data is not None:
                changed.append(f"{crate}/{native.PIN_NAME}")
                if not dry_run:
                    replace_file(pin_path, data)

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
                raise KitError(
                    f"{plugin.name}: omarchy-plugin-validate failed after sync:\n{result.stderr or result.stdout}"
                )
    return changed


# ---------------------------------------------------------------------- check


def verify_plugin(plugin, native=True):
    """List of integrity problems (empty when intact); `native` also checks
    the native helper binaries against their native.pin."""
    plugin = Path(plugin)
    try:
        lock = read_lock(plugin)
    except KitError as error:
        return [str(error)]
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
    problems += agents_problems(plugin)
    if native:
        problems += verify_native(plugin, lock)
    return problems


# ----------------------------------------------------------------------- lint

RULES = {
    "unqualified-color": "use Commons.Color.* (Qt 6.12's QtQuick Color type shadows a bare Color)",
    "bare-duration": "durations go through FoamyMotion (honours reduced motion)",
    "sans-serif": "use FoamyStyle.fontFamily",
    "radius-x2": "use FoamyStyle.radius",
    "hex-colour": "use Commons.Color or FoamyPalette (theme colours), not a hex literal",
    "unguarded-loop": "infinite animations need `running: … && !FoamyMotion.reduceMotion`",
    "raw-ipc": "use FoamyIpc (registers with IpcRegistry for the omarchy-shell socket fast path)",
    "opt-out-reason": "a foamy-lint opt-out needs a reason: // foamy-lint: allow <rule> — <why>",
    "empty-glyph": 'a glyph\'s text is empty (an icon character was lost); write it as an escape like "\\u{f0e7}"',
    "pua-literal": 'private-use (icon font) character written literally; editors and tools strip them, use an escape like "\\u{f0e7}"',
}
# Rules that can be downgraded to warnings with --warn-pua (they fail by default).
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
            comment = line[i + 2 :]
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
            text = text[text.rfind("{", 0, column if j == index else len(text)) :]
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
        result = subprocess.run(
            ["git", "-C", str(plugin), "ls-files", "-co", "--exclude-standard"],
            capture_output=True,
            text=True,
            timeout=30,
        )
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


def cargo_target_dirs(plugin):
    """Cargo target dirs inside a plugin (`<plugin>/target`,
    `<plugin>/<crate>/target`), found by cargo's CACHEDIR.TAG."""
    plugin = Path(plugin)
    found = [plugin / "target"] + [
        d / "target" for d in sorted(plugin.iterdir()) if d.is_dir() and not d.name.startswith(".")
    ]
    return [d.relative_to(plugin).as_posix() for d in found if (d / "CACHEDIR.TAG").is_file()]


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
        # A lock that names paths foamy-kit doesn't own is this plugin's
        # problem (verify_plugin reports it), not a reason to stop checking.
        try:
            lock, lock_broken = read_lock(plugin), False
        except KitError:
            lock, lock_broken = None, True
        if not args.lint_only:
            if lock is None and args.allow_unsynced and not lock_broken:
                pass
            else:
                problems += verify_plugin(plugin)
                if lock and lock["version"]:
                    versions.setdefault(lock["version"], []).append(name)
        findings = [] if args.no_lint else lint_plugin(plugin)
        for problem in problems:
            print(f"{name}: kit: {problem}")
        if not args.lint_only:
            for target in cargo_target_dirs(plugin):
                print(
                    f"{name}: warning: {target}/ is a cargo target dir inside the plugin; remove it and "
                    f"export CARGO_TARGET_DIR=~/.cache/foamy-native/{name} before any cargo command"
                )
        failing = [f for f in findings if not args.warn_pua or f[2] not in WARNINGS]
        for rel, line, rule, excerpt in findings:
            level = "warning: " if rule in WARNINGS and args.warn_pua else ""
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
            warning = rule in WARNINGS and args.warn_pua
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
    check.add_argument(
        "--warn-pua",
        action="store_true",
        help="report pua-literal (literal icon-font characters) as a warning instead of failing",
    )
    check.add_argument("--strict", action="store_true", help=argparse.SUPPRESS)  # the default since 0.3.4 tooling
    check.set_defaults(func=cmd_check)
    lint = sub.add_parser("lint", help="lint individual files")
    lint.add_argument("files", nargs="+")
    lint.add_argument("--warn-pua", action="store_true")
    lint.add_argument("--strict", action="store_true", help=argparse.SUPPRESS)
    lint.set_defaults(func=cmd_lint_text)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
