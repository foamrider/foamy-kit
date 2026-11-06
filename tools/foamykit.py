#!/usr/bin/env python3
"""foamy-kit: copy stamped kit files into plugins, verify them, lint designs.

Used through ../sync.sh, ../check.sh and build-native.sh; see README.md.
Standard library only.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import tomllib
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
    return "#" if name.endswith((".sh", ".toml")) or Path(name).name == "qmldir" else "//"


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
            matches = sorted(p for p in KIT_DIR.glob(pattern)
                             if p.is_file() and "target" not in p.relative_to(KIT_DIR).parts)
            if not matches:
                raise KitError(f"components.json: {name}: {pattern} matches no file")
            out += [(f"kit/{p.relative_to(KIT_DIR).as_posix()}", p) for p in matches]
        else:
            out.append((f"kit/{pattern}", KIT_DIR / pattern))
    for dest, source in sorted(spec.get("rootFiles", {}).items()):
        parts = Path(dest).parts
        if Path(dest).is_absolute() or ".." in parts or not parts or parts[0] == "kit" or dest in (LOCK_NAME, CHECK_NAME):
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
    tests/kit-check.sh, or a component's rootFiles destination. The lock is
    plugin content, so anything else (`../x`, `/etc/x`, `kit/../x`) is refused
    before sync reads, overwrites or deletes it."""
    parts = rel.split("/")
    if rel.startswith("/") or "\\" in rel or any(part in ("", ".", "..") for part in parts):
        return False
    if parts[0] == "kit" and len(parts) > 1:
        return True
    if rel == CHECK_NAME:
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
                raise KitError(f"{LOCK_NAME} lists {parts[1]!r}, which is not a path foamy-kit owns "
                               "(only kit/…, tests/kit-check.sh and component root files); fix or delete the lock")
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
    # Components' rootFiles (rust-toolchain.toml), owned now or planned.
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
    if not dry_run and kit_dir.is_dir():
        # Directories of removed subdirectory components (kit/rust/…).
        for path in sorted(kit_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir() and not path.is_symlink() and not any(path.iterdir()):
                path.rmdir()
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
    if native:
        problems += verify_native(plugin, lock)
    return problems


# ------------------------------------------------------------- native helpers

NATIVE_COMPONENT = "FoamyNative"
PIN_NAME = "native.pin"
TOOLCHAIN_FILE = "rust-toolchain.toml"
RELEASE_PROFILE = "kit/rust/release.toml"
ROOT_SOURCES = ("Cargo.lock", "Cargo.toml", TOOLCHAIN_FILE)
ARCHES = {"x86_64": "x86_64-unknown-linux-musl", "aarch64": "aarch64-unknown-linux-musl"}
ELF_MACHINES = {"x86_64": 62, "aarch64": 183}
FILE_ARCH = {"x86_64": "x86-64", "aarch64": "ARM aarch64"}
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
SHA_RE = re.compile(r"[0-9a-f]{64}")


def native_pins(plugin):
    """<crate>/native.pin files directly under the plugin root."""
    return sorted(p for p in Path(plugin).glob(f"*/{PIN_NAME}") if p.is_file() and not p.is_symlink())


def read_pin(path):
    info = {"files": {}}
    for line in Path(path).read_text(errors="replace").splitlines():
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        if len(parts) == 2 and SHA_RE.fullmatch(parts[0]):
            info["files"][parts[1]] = parts[0]
        elif len(parts) == 2:
            info[parts[0]] = parts[1]
    return info


def unstamped(data):
    """A file's bytes without its foamy-kit stamp line (as sed deletes it in
    tests/kit-check.sh: lines split on \\n only)."""
    lines = data.split(b"\n")
    for index in (0, 1):
        if index < len(lines) and STAMP_RE.match(lines[index].decode("utf-8", errors="replace")):
            return b"\n".join(lines[:index] + lines[index + 1:])
    return data


def native_sources(plugin, crate):
    """Plugin-relative paths of everything a native build reads: the crate
    (minus native.pin and target/), the vendored kit/rust, the toolchain file
    and the workspace's Cargo.toml and Cargo.lock at the plugin root."""
    plugin = Path(plugin)
    found = set()
    for top in (plugin / crate, plugin / "kit/rust"):
        for dirpath, dirnames, filenames in os.walk(top):
            current = Path(dirpath)
            if current == plugin / crate:
                dirnames[:] = [d for d in dirnames if d != "target"]
            for filename in filenames:
                path = current / filename
                rel = path.relative_to(plugin).as_posix()
                if path.is_symlink() or not path.is_file() or rel == f"{crate}/{PIN_NAME}":
                    continue
                found.add(rel)
    for rel in ROOT_SOURCES:
        if (plugin / rel).is_file() and not (plugin / rel).is_symlink():
            found.add(rel)
    return sorted(found)


def native_source_hash(plugin, crate):
    """sha256 over "<sha256 of body>  <path>\\n" lines, sorted by path; kit files
    are hashed without their stamp, so a kit version bump alone never makes a
    binary stale."""
    plugin = Path(plugin)
    lines = "".join(f"{sha256(unstamped((plugin / rel).read_bytes()))}  {rel}\n" for rel in native_sources(plugin, crate))
    return sha256(lines.encode())


def elf_problem(data, arch):
    """None for a static 64-bit little-endian ELF executable for `arch`."""
    if data[:4] != b"\x7fELF":
        return "is not an ELF executable"
    if len(data) < 64 or data[4] != 2 or data[5] != 1:
        return "is not a 64-bit little-endian ELF"
    e_type, e_machine = struct.unpack_from("<HH", data, 16)
    if e_machine != ELF_MACHINES[arch]:
        return f"is not a 64-bit {arch} ELF (ELF machine {e_machine})"
    entry, phoff = struct.unpack_from("<QQ", data, 24)
    phentsize, phnum = struct.unpack_from("<HH", data, 54)
    if e_type not in (2, 3) or entry == 0:
        return "is not an executable"
    for index in range(phnum):
        offset = phoff + index * phentsize
        if offset + 4 > len(data):
            return "has a truncated program header table"
        if struct.unpack_from("<I", data, offset)[0] == 3:  # PT_INTERP
            return "is dynamically linked (it names an ELF interpreter)"
    return None


def file_problem(path, arch):
    """`file`'s view (static ELF of the right arch), when file(1) exists."""
    tool = shutil.which("file")
    if not tool:
        return None
    out = subprocess.run([tool, "-b", str(path)], capture_output=True, text=True, timeout=30).stdout
    if "ELF 64-bit LSB" not in out or FILE_ARCH[arch] not in out:
        return f"is not a 64-bit {arch} ELF according to file(1): {out.strip()}"
    if "statically linked" not in out and "static-pie linked" not in out:
        return f"is not statically linked according to file(1): {out.strip()}"
    return None


def binary_problems(plugin, rel, arch, expected):
    path = Path(plugin) / rel
    if path.is_symlink() or not path.is_file():
        return [f"{rel} is missing or not a regular file"]
    problems = []
    if not path.stat().st_mode & stat.S_IXUSR:
        problems.append(f"{rel} is not executable")
    data = path.read_bytes()
    if sha256(data) != expected:
        problems.append(f"{rel} checksum differs from native.pin")
    reason = elf_problem(data, arch) or file_problem(path, arch)
    if reason:
        problems.append(f"{rel} {reason}")
    return problems


def verify_native(plugin, lock):
    plugin = Path(plugin)
    problems = []
    pins = native_pins(plugin)
    synced = bool(lock) and NATIVE_COMPONENT in lock["components"]
    if synced and not pins:
        problems.append(f"{NATIVE_COMPONENT} is synced but no <crate>/{PIN_NAME} exists (run tools/build-native.sh)")
    for pin_path in pins:
        crate = pin_path.parent.name
        label = f"{crate}/{PIN_NAME}"
        pin = read_pin(pin_path)
        if not synced:
            problems.append(f"{label} exists but {NATIVE_COMPONENT} is not synced (sync.sh --add {NATIVE_COMPONENT})")
        if pin.get("crate") != crate:
            problems.append(f"{label} names crate {pin.get('crate')!r}, expected {crate!r}")
        binary = pin.get("binary", "")
        if not NAME_RE.fullmatch(binary):
            problems.append(f"{label} has no valid binary name")
            continue
        wanted = {f"bin/{arch}/{binary}": arch for arch in ARCHES}
        for rel, arch in wanted.items():
            if rel not in pin["files"]:
                problems.append(f"{label} has no checksum for {rel}")
            else:
                problems += binary_problems(plugin, rel, arch, pin["files"][rel])
        for rel in sorted(set(pin["files"]) - set(wanted)):
            problems.append(f"{label} lists unexpected file {rel}")
        if native_source_hash(plugin, crate) != pin.get("source"):
            problems.append(f"{binary} is stale: {crate}/, kit/rust, Cargo.toml, Cargo.lock or {TOOLCHAIN_FILE} "
                            f"changed since it was built (run tools/build-native.sh)")
    return problems


# --------------------------------------------------------------- native build

def plugin_short_name(plugin):
    """`power` for a plugin whose manifest id is `foamy.power`."""
    plugin_id = json.loads((Path(plugin) / "manifest.json").read_text()).get("id", "")
    match = re.fullmatch(r"foamy\.([a-z0-9][a-z0-9-]*)", plugin_id)
    if not match:
        raise KitError(f"manifest id {plugin_id!r} is not foamy.<name>")
    return match.group(1)


def native_cache():
    base = os.environ.get("FOAMY_NATIVE_CACHE") or os.path.join(
        os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "foamy-native")
    return Path(base).resolve()


def resolve_native(plugin, crate=None, binary=None):
    """(crate dir, binary name) from the options, an existing native.pin, or
    the defaults `native/` and `foamy-<plugin>-helper`."""
    plugin = Path(plugin)
    pins = native_pins(plugin)
    if crate is None:
        if len(pins) > 1:
            raise KitError("several crates have a native.pin (" + ", ".join(p.parent.name for p in pins) + "); pass --crate")
        crate = pins[0].parent.name if pins else "native"
    crate = crate.strip("/")
    if not NAME_RE.fullmatch(crate) or crate in ("kit", "bin", "tests"):
        raise KitError(f"invalid crate directory {crate!r} (one directory directly under the plugin)")
    pin = read_pin(plugin / crate / PIN_NAME) if (plugin / crate / PIN_NAME).is_file() else {}
    binary = binary or pin.get("binary") or f"foamy-{plugin_short_name(plugin)}-helper"
    if not NAME_RE.fullmatch(binary):
        raise KitError(f"invalid binary name {binary!r}")
    return crate, binary


def toolchain_channel(plugin):
    path = Path(plugin) / TOOLCHAIN_FILE
    try:
        channel = tomllib.loads(path.read_text())["toolchain"]["channel"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as error:
        raise KitError(f"{TOOLCHAIN_FILE}: no toolchain channel ({error}); run sync.sh --add {NATIVE_COMPONENT}")
    return channel


WORKSPACE_EXAMPLE = '[workspace]\nmembers = ["{crate}"]\nexclude = ["kit"]\nresolver = "3"'


def read_toml(path):
    try:
        return tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise KitError(f"{path.name}: {error}")


def native_preflight(plugin, crate):
    """Refuse a build that couldn't be reproduced: kit files edited or not
    synced, no workspace at the plugin root, no Cargo.lock, or a [profile]
    outside the kit's release profile."""
    lock = read_lock(plugin)
    if not lock or NATIVE_COMPONENT not in lock["components"]:
        raise KitError(f"{NATIVE_COMPONENT} is not synced; run sync.sh {plugin} --add {NATIVE_COMPONENT}")
    problems = verify_plugin(plugin, native=False)
    if problems:
        raise KitError("kit files are not intact (run sync.sh):\n  " + "\n  ".join(problems))
    if not (plugin / crate / "Cargo.toml").is_file():
        raise KitError(f"{crate}/Cargo.toml not found")
    # The workspace root is the plugin root, so cargo hashes the vendored
    # kit/rust crate by its path relative to the plugin, not its absolute
    # path: every checkout then builds the same bytes.
    example = WORKSPACE_EXAMPLE.format(crate=crate)
    if not (plugin / "Cargo.toml").is_file():
        raise KitError(f"no Cargo.toml at the plugin root; create it with:\n{example}")
    root = read_toml(plugin / "Cargo.toml")
    workspace = root.get("workspace")
    if not isinstance(workspace, dict) or "package" in root:
        raise KitError(f"the plugin's Cargo.toml must be a virtual workspace manifest:\n{example}")
    if crate not in workspace.get("members", []) or "kit" not in workspace.get("exclude", []):
        raise KitError(f"the plugin's Cargo.toml must list {crate!r} in members and 'kit' in exclude:\n{example}")
    for rel in ("Cargo.toml", f"{crate}/Cargo.toml"):
        if "profile" in read_toml(plugin / rel):
            raise KitError(f"{rel} declares [profile]; remove it, the kit's {RELEASE_PROFILE} is the release profile")
    if "workspace" in read_toml(plugin / crate / "Cargo.toml"):
        raise KitError(f"{crate}/Cargo.toml declares [workspace]; the workspace is the plugin's root Cargo.toml")
    outside = path_dependencies_outside(plugin, crate)
    if outside:
        raise KitError("path dependencies outside the hashed sources (the crate dir and kit/rust), so native.pin "
                       "couldn't tell when they change; move them into " + crate + "/ or use a published crate:\n  "
                       + "\n  ".join(outside))
    if not (plugin / "Cargo.lock").is_file():
        raise KitError("Cargo.lock is missing at the plugin root; run `cargo generate-lockfile` there and commit it")
    if (plugin / crate / "Cargo.lock").exists():
        raise KitError(f"{crate}/Cargo.lock is unused (the lock file lives at the plugin root); remove it")


def path_dependencies_outside(plugin, crate):
    """`path = …` dependencies (any table: dependencies, dev-, build-,
    target-specific, workspace.dependencies, patch, replace) in the root and
    crate manifests that resolve outside the crate dir and kit/rust, which
    native_source_hash covers. ["<manifest>: <name> = <path>", …]."""
    plugin = Path(plugin).resolve()
    allowed = [(plugin / crate).resolve(), (plugin / "kit/rust").resolve()]
    found = []

    def walk(table, base, manifest, name=""):
        if not isinstance(table, dict):
            return
        path = table.get("path")
        if isinstance(path, str) and name:
            target = (base / path).resolve()
            if not any(target == root or root in target.parents for root in allowed):
                found.append(f"{manifest}: {name} = {path!r}")
        for key, value in table.items():
            if isinstance(value, dict):
                walk(value, base, manifest, key)

    for rel in ("Cargo.toml", f"{crate}/Cargo.toml"):
        manifest = plugin / rel
        data = read_toml(manifest)
        # [workspace] members/exclude are not dependencies.
        tables = {k: v for k, v in data.items() if k not in ("package", "workspace", "lib", "bin", "profile")}
        if isinstance(data.get("workspace"), dict):
            tables["workspace.dependencies"] = data["workspace"].get("dependencies", {})
        for key, value in tables.items():
            walk(value, manifest.parent, rel, key if isinstance(value, dict) and "path" in value else "")
    return found


def cargo_env(target_dir, channel, flags=None, linker_triples=()):
    """The environment for cargo: the pinned toolchain, our target dir, and
    nothing from the caller that changes code generation."""
    env = {key: value for key, value in os.environ.items()
           if key not in ("RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_BUILD_RUSTFLAGS", "RUSTC", "RUSTC_WRAPPER",
                          "RUSTC_WORKSPACE_WRAPPER", "CARGO_BUILD_TARGET", "CARGO_BUILD_TARGET_DIR", "CARGO_INCREMENTAL",
                          "CARGO_BUILD_RUSTC", "CARGO_BUILD_RUSTC_WRAPPER", "CARGO_BUILD_RUSTC_WORKSPACE_WRAPPER")
           and not key.startswith(("CARGO_PROFILE_", "CARGO_TARGET_"))}
    env.update(RUSTUP_TOOLCHAIN=channel, CARGO_TARGET_DIR=str(target_dir), CARGO_INCREMENTAL="0")
    if flags is not None:
        env["CARGO_ENCODED_RUSTFLAGS"] = "\x1f".join(flags)
    for triple in linker_triples:
        env[f"CARGO_TARGET_{triple.upper().replace('-', '_')}_LINKER"] = "rust-lld"
    return env


def check_toolchain(env, channel, cwd):
    try:
        out = subprocess.run(["rustc", "--version"], env=env, cwd=cwd, capture_output=True, text=True, timeout=60)
    except OSError:
        raise KitError("rustc not found; install rustup (see README.md, Native helpers)")
    if out.returncode != 0 or not out.stdout.startswith(f"rustc {channel} "):
        raise KitError(f"rustc is {out.stdout.strip() or out.stderr.strip()!r}, expected {channel} "
                       f"(rustup toolchain install {channel}, with the musl targets from {TOOLCHAIN_FILE})")
    return out.stdout.strip()


def build_native(plugin, crate, binary, channel, target_dir):
    """Builds both arches into target_dir; {arch: bytes}."""
    plugin = Path(plugin)
    crate_dir = plugin / crate
    home = Path.home()
    cargo_home = Path(os.environ.get("CARGO_HOME") or home / ".cargo").resolve()
    rustup_home = Path(os.environ.get("RUSTUP_HOME") or home / ".rustup").resolve()
    # Later remaps win: general prefixes first. Paths end up relative to the
    # plugin, so any checkout (live, worktree, another machine) builds the
    # same bytes.
    flags = [
        "-C", "link-self-contained=yes",
        "-C", "link-arg=--build-id=none",
        f"--remap-path-prefix={cargo_home}=/cargo",
        f"--remap-path-prefix={rustup_home}=/rustup",
        f"--remap-path-prefix={target_dir}=/target",
        f"--remap-path-prefix={plugin}=.",
        f"--remap-path-prefix={plugin / 'kit/rust'}=kit/rust",
        f"--remap-path-prefix={crate_dir}=.",
    ]
    env = cargo_env(target_dir, channel, flags, ARCHES.values())
    check_toolchain(env, channel, crate_dir)
    built = {}
    for arch, triple in ARCHES.items():
        command = ["cargo", "build", "--locked", "--release", "--target", triple, "--bin", binary,
                   "--manifest-path", str(crate_dir / "Cargo.toml"), "--config", str(plugin / RELEASE_PROFILE)]
        result = subprocess.run(command, env=env, cwd=crate_dir)
        if result.returncode != 0:
            raise KitError(f"cargo build for {triple} failed (exit {result.returncode})")
        data = (Path(target_dir) / triple / "release" / binary).read_bytes()
        reason = elf_problem(data, arch)
        if reason:
            raise KitError(f"the {arch} build {reason}")
        built[arch] = data
    return built


def install_atomic(path, data, mode):
    """Writes data to path through a temp file in the same directory and a
    rename, so the running shell never sees a partial file. No-op when equal."""
    path = Path(path)
    if path.is_file() and not path.is_symlink() and path.read_bytes() == data and stat.S_IMODE(path.stat().st_mode) == mode:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise
    return True


def pin_bytes(crate, binary, channel, source, built):
    lines = [
        f"# {PIN_NAME}: written by foamy-kit tools/build-native.sh; do not edit.",
        "# check.sh and tests/kit-check.sh verify bin/<arch>/<binary> against it and",
        "# report the binaries stale when `source` no longer matches the crate, kit/rust,",
        f"# Cargo.toml, Cargo.lock and {TOOLCHAIN_FILE}. Rebuild: foamy-kit tools/build-native.sh <plugin>.",
        f"crate {crate}",
        f"binary {binary}",
        f"toolchain {channel}",
        f"kit {kit_version()}",
        f"source {source}",
    ]
    lines += [f"{sha256(built[arch])}  bin/{arch}/{binary}" for arch in sorted(built)]
    return ("\n".join(lines) + "\n").encode()


def cmd_native(args):
    plugin = Path(args.plugin).resolve()
    try:
        if not (plugin / "manifest.json").is_file():
            raise KitError(f"{plugin}: not a plugin (no manifest.json)")
        name = plugin_short_name(plugin)
        crate, binary = resolve_native(plugin, args.crate, args.bin)
        native_preflight(plugin, crate)
        channel = toolchain_channel(plugin)
        cache = native_cache()
        if cache == plugin or plugin in cache.parents:
            raise KitError(f"the cargo cache {cache} is inside the plugin; cargo output never goes into a plugin folder")
        target_dir = cache / f"foamy-{name}"
        crate_dir = plugin / crate
        if args.test:
            env = cargo_env(target_dir, channel)
            check_toolchain(env, channel, crate_dir)
            manifest = ["--manifest-path", str(crate_dir / "Cargo.toml")]
            for step in (["cargo", "fmt", "--check", *manifest],
                         ["cargo", "clippy", "--locked", "--all-targets", *manifest, "--", "-D", "warnings"],
                         ["cargo", "test", "--locked", *manifest]):
                print("+ " + " ".join(step[:3]), flush=True)
                if subprocess.run(step, env=env, cwd=crate_dir).returncode != 0:
                    raise KitError(f"{' '.join(step[:2])} failed")
            print(f"{plugin.name}: {crate}/ fmt, clippy and tests OK")
            return 0
        if args.verify:
            pin_path = crate_dir / PIN_NAME
            if not pin_path.is_file():
                raise KitError(f"no {crate}/{PIN_NAME}; build first")
            pin = read_pin(pin_path)
            problems = verify_native(plugin, read_lock(plugin))
            source = native_source_hash(plugin, crate)
            cache.mkdir(parents=True, exist_ok=True)
            fresh = Path(tempfile.mkdtemp(prefix=f"foamy-{name}-verify-", dir=cache))
            try:
                built = build_native(plugin, crate, binary, channel, fresh)
            finally:
                shutil.rmtree(fresh, ignore_errors=True)
            if native_source_hash(plugin, crate) != source:
                raise KitError(f"{crate}/, kit/rust or the workspace files changed during the verify build; re-run it")
            for arch, data in sorted(built.items()):
                rel = f"bin/{arch}/{binary}"
                committed = (plugin / rel).read_bytes() if (plugin / rel).is_file() else b""
                if data != committed:
                    problems.append(f"{rel}: a clean rebuild differs from the committed binary ({sha256(data)[:16]}… vs {sha256(committed)[:16]}…)")
                else:
                    print(f"{rel}: byte-identical to a clean rebuild ({len(data)} bytes, sha256 {sha256(data)[:16]}…)")
            if pin.get("toolchain") != channel:
                problems.append(f"{crate}/{PIN_NAME} says toolchain {pin.get('toolchain')}, {TOOLCHAIN_FILE} says {channel}")
            if pin.get("source") != source:
                problems.append(f"{crate}/{PIN_NAME} source hash is stale")
            if problems:
                raise KitError("verify failed:\n  " + "\n  ".join(dict.fromkeys(problems)))
            print(f"{plugin.name}: verify OK ({binary}, {channel}, both arches reproducible)")
            return 0
        # Hash before and after: an edit while cargo runs (or between the two
        # arches) would otherwise pin binaries to sources they weren't built from.
        source = native_source_hash(plugin, crate)
        built = build_native(plugin, crate, binary, channel, target_dir)
        if native_source_hash(plugin, crate) != source:
            raise KitError(f"{crate}/, kit/rust or the workspace files changed during the build; "
                           "nothing was installed, re-run the build")
        changed = [f"bin/{arch}/{binary}" for arch, data in sorted(built.items())
                   if install_atomic(plugin / "bin" / arch / binary, data, 0o755)]
        if install_atomic(crate_dir / PIN_NAME, pin_bytes(crate, binary, channel, source, built), 0o644):
            changed.append(f"{crate}/{PIN_NAME}")
        sizes = ", ".join(f"{arch} {len(data)} bytes" for arch, data in sorted(built.items()))
        print(f"{plugin.name}: {binary} ({channel}): {sizes}; " + (f"updated {', '.join(changed)}" if changed else "up to date"))
        return 0
    except KitError as error:
        print(f"build-native: {error}", file=sys.stderr)
        return 1


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


def cargo_target_dirs(plugin):
    """Cargo target dirs inside a plugin (`<plugin>/target`,
    `<plugin>/<crate>/target`), found by cargo's CACHEDIR.TAG."""
    plugin = Path(plugin)
    found = [plugin / "target"] + [d / "target" for d in sorted(plugin.iterdir()) if d.is_dir() and not d.name.startswith(".")]
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
        if not args.lint_only:
            for target in cargo_target_dirs(plugin):
                print(f"{name}: warning: {target}/ is a cargo target dir inside the plugin; remove it and "
                      f"export CARGO_TARGET_DIR=~/.cache/foamy-native/{name} before any cargo command")
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
    check.add_argument("--warn-pua", action="store_true",
                       help="report pua-literal (literal icon-font characters) as a warning instead of failing")
    check.add_argument("--strict", action="store_true", help=argparse.SUPPRESS)  # the default since 0.3.4 tooling
    check.set_defaults(func=cmd_check)
    native = sub.add_parser("native", help="build a plugin's native helper for both arches (build-native.sh)")
    native.add_argument("plugin")
    mode = native.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true", help="rebuild in a fresh target dir and compare with the committed binaries")
    mode.add_argument("--test", action="store_true", help="cargo fmt --check, clippy -D warnings and test for the crate")
    native.add_argument("--crate", help="crate directory (default: the one with a native.pin, else native)")
    native.add_argument("--bin", help="binary name (default: native.pin's, else foamy-<plugin>-helper)")
    native.set_defaults(func=cmd_native)
    lint = sub.add_parser("lint", help="lint individual files")
    lint.add_argument("files", nargs="+")
    lint.add_argument("--warn-pua", action="store_true")
    lint.add_argument("--strict", action="store_true", help=argparse.SUPPRESS)
    lint.set_defaults(func=cmd_lint_text)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
