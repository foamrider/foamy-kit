#!/usr/bin/env python3
"""FoamyNative: syncing a subdirectory component with Rust/TOML stamps, the
shared foamy-helper crate (fmt, clippy, tests), and the fixture plugin
tests/fixtures/native-plugin built for x86_64 and aarch64 with
tools/build-native.sh: reproducible (--verify, another checkout path),
checked by check.sh and its own tests/kit-check.sh (pin, checksums, static
ELF, stale sources), run on both arches (aarch64 through qemu binfmt), and
launched through FoamyNative.command from node and from Quickshell.

Cargo output goes to a temporary FOAMY_NATIVE_CACHE; the Rust part is skipped
(SKIP) without cargo/rustup."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIXTURES, KIT_ROOT, foamykit, harness, report, run_shell  # noqa: E402

SYNC = str(KIT_ROOT / "sync.sh")
CHECK = str(KIT_ROOT / "check.sh")
BUILD = str(KIT_ROOT / "tools/build-native.sh")
FIXTURE = FIXTURES / "native-plugin"
BINARY = "foamy-native-demo-helper"
CHANNEL = "1.99.1"


def sh(*args, env=None, cwd=None, timeout=900, stdin=None):
    full = dict(os.environ, **(env or {}))
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout, env=full,
                            cwd=cwd, input=stdin)
    return result.returncode, result.stdout + result.stderr


def snapshot(root):
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mode) for p in sorted(Path(root).rglob("*"))
            if p.is_file()}


def fresh(base, name):
    target = base / name
    shutil.copytree(FIXTURE, target)
    return target


def kit_check(plugin):
    return sh("env", "-i", "PATH=/usr/bin:/bin", "bash", plugin / "tests/kit-check.sh")


def sync_tests(base):
    ok = True
    plugin = fresh(base, "sync")
    code, out = sh(SYNC, plugin, "--components", "FoamyNative")
    rust_sources = sorted(f"kit/{p.relative_to(KIT_ROOT / 'kit').as_posix()}"
                          for p in (KIT_ROOT / "kit/rust/foamy-helper/src").rglob("*.rs"))
    expected = sorted(["kit/FoamyNative.js", "kit/node-loader.cjs", "kit/qmldir", "kit/rust/release.toml",
                       "kit/rust/foamy-helper/Cargo.toml", "rust-toolchain.toml", "tests/kit-check.sh"] + rust_sources)
    lock = foamykit.read_lock(plugin)
    ok &= report("sync copies the FoamyNative tree (subdirectories, root rust-toolchain.toml)",
                 code == 0 and sorted(lock["files"]) == expected and lock["components"] == ["FoamyNative"],
                 out.strip() if code else f"{len(expected)} files")
    ok &= report("the kit crate's own Cargo.lock is not vendored", not (plugin / "kit/rust/foamy-helper/Cargo.lock").exists())
    lib = (plugin / "kit/rust/foamy-helper/src/lib.rs").read_text().splitlines()
    toolchain = (plugin / "rust-toolchain.toml").read_text().splitlines()
    cargo = (plugin / "kit/rust/foamy-helper/Cargo.toml").read_text().splitlines()
    ok &= report("Rust and TOML files are stamped on line 1 with their comment syntax",
                 lib[0].startswith("// foamy-kit ") and toolchain[0].startswith("# foamy-kit ")
                 and cargo[0].startswith("# foamy-kit ") and lib[1].startswith("//!"))
    attribute = foamykit.stamped("kit/x.rs", b"#![forbid(unsafe_code)]\nfn main() {}\n", "0.5.0").decode().splitlines()
    ok &= report("a leading #![attribute] is not taken for a shebang", attribute[0].startswith("// foamy-kit 0.5.0 "))
    short = foamykit.stamped("kit/x.rs", b"//! a\nfn f() {}\n", "0.5.0").decode().splitlines()
    long = foamykit.stamped("kit/x.rs", b"//! a\nfn f() {}\n", "10.200.3000").decode().splitlines()
    ok &= report("the stamp line is fixed: a version change shifts no line", len(short) == len(long) and short[1:] == long[1:])
    code, out = kit_check(plugin)
    code2, out2 = sh(CHECK, "--no-lint", plugin)
    ok &= report("kit-check and check.sh fail while FoamyNative has no native.pin",
                 code != 0 and "no <crate>/native.pin" in out and code2 != 0 and "no <crate>/native.pin" in out2, out.strip())
    io_rs = plugin / "kit/rust/foamy-helper/src/io.rs"
    io_rs.write_text(io_rs.read_text().replace("limit.saturating_add(1)", "limit"))
    code, out = kit_check(plugin)
    code2, out2 = sh(SYNC, plugin)
    ok &= report("an edit in the vendored crate is detected and never overwritten",
                 code != 0 and "kit/rust/foamy-helper/src/io.rs was edited locally" in out and code2 != 0 and "edited locally" in out2)
    sh(SYNC, plugin, "--force")
    ok &= report("--force restores the vendored crate", "limit.saturating_add(1)" in io_rs.read_text())
    code, out = sh(SYNC, plugin, "--components", "FoamyPrefs")
    leftovers = sorted(p.relative_to(plugin).as_posix() for p in (plugin / "kit").rglob("*"))
    ok &= report("dropping FoamyNative removes kit/rust (no empty dirs) and rust-toolchain.toml",
                 code == 0 and not (plugin / "rust-toolchain.toml").exists()
                 and leftovers == ["kit/FoamyPrefs.js", "kit/FoamyPrefsQueue.qml", "kit/node-loader.cjs", "kit/qmldir"], f"{leftovers}")
    own = fresh(base, "own-toolchain")
    (own / "rust-toolchain.toml").write_text('[toolchain]\nchannel = "stable"\n')
    code, out = sh(SYNC, own, "--components", "FoamyNative")
    ok &= report("sync refuses to replace a plugin's own rust-toolchain.toml", code != 0 and "rust-toolchain.toml is not a foamy-kit file" in out
                 and "stable" in (own / "rust-toolchain.toml").read_text(), out.strip())
    demo = base / "demo"
    shutil.copytree(FIXTURES / "demo-plugin", demo)
    code, out = sh(SYNC, demo)
    ok &= report("FoamyNative is opt-in: a first sync without --components leaves it out",
                 code == 0 and "FoamyNative" not in foamykit.read_lock(demo)["components"] and not (demo / "kit/rust").exists())
    return ok


def run_helper(binary, *args, stdin=None, env=None):
    code, out = sh(binary, *args, stdin=stdin, env=env, timeout=60)
    lines = [line for line in out.splitlines() if line.startswith("{")]
    try:
        return code, [json.loads(line) for line in lines], out
    except ValueError:
        return code, [], out


def helper_tests(plugin, arch, base):
    """The fixture helper's contract on one arch (exercises foamy-helper)."""
    ok = True
    binary = plugin / "bin" / arch / BINARY
    tag = f"({arch})"
    code, replies, out = run_helper(binary, "version")
    ok &= report(f"helper runs {tag}", code == 0 and replies == [{"ok": True, "helper": BINARY, "arch": arch}], out.strip())
    args = ["two words", "", "$HOME", "ünï", "-n", "a\nb"]
    code, replies, out = run_helper(binary, "args", *args)
    ok &= report(f"arguments arrive verbatim {tag}", code == 0 and replies and replies[0]["args"] == args, out.strip())
    code, replies, out = run_helper(binary, "echo", stdin="x" * 65536)
    code2, replies2, out2 = run_helper(binary, "echo", stdin="x" * 65537)
    ok &= report(f"bounded stdin: 64 KiB accepted, one byte more refused {tag}",
                 code == 0 and replies[0]["bytes"] == 65536 and code2 == 1 and replies2[0]["code"] == "INPUT_TOO_LARGE", out2.strip()[:200])
    lines = '{"id":1,"text":"héllo"}\nnot json\n{"id":2,"text":"' + "y" * 2000 + '"}\n\n{"id":3,"text":""}\n'
    code, replies, out = run_helper(binary, "serve", stdin=lines)
    ok &= report(f"JSON lines: replies per line, bad and overlong lines answered, loop goes on {tag}",
                 code == 0 and replies == [{"id": 1, "length": 5}, {"error": "INVALID_REQUEST", "message": replies[1].get("message")},
                                           {"error": "INVALID_REQUEST", "message": "line is longer than 1024 bytes"},
                                           {"id": 3, "length": 0}], out.strip()[:300])
    state = base / f"state-{arch}"
    state.mkdir(mode=0o700)
    target = state / "default"
    code, replies, out = run_helper(binary, "write", target, "balanced")
    code2, _, _ = run_helper(binary, "write", target, "performance")
    ok &= report(f"atomic write: content, mode 0600, no temp file left {tag}",
                 code == 0 and code2 == 0 and target.read_text() == "performance\n" and (target.stat().st_mode & 0o777) == 0o600
                 and [p.name for p in state.iterdir()] == ["default"], out.strip())
    (state / "link").symlink_to(target)
    code, replies, out = run_helper(binary, "write", state / "link", "evil")
    ok &= report(f"atomic write refuses a symlink {tag}", code == 1 and replies[0]["ok"] is False and target.read_text() == "performance\n", out.strip())
    runtime = base / f"runtime-{arch}"
    runtime.mkdir(mode=0o700)
    env = {"XDG_RUNTIME_DIR": str(runtime)}
    holder = subprocess.Popen([str(binary), "lock", "4000"], env=dict(os.environ, **env), stdout=subprocess.PIPE, text=True)
    lock_file = runtime / "foamy-native-demo/action.lock"
    for _ in range(200):
        if lock_file.exists():
            break
        time.sleep(0.02)
    time.sleep(0.5)
    code, replies, out = run_helper(binary, "lock", "0", env=env)
    holder_out = holder.communicate(timeout=30)[0]
    code2, replies2, _ = run_helper(binary, "lock", "0", env=env)
    ok &= report(f"runtime lock: BUSY while held, free afterwards, dir 0700 {tag}",
                 code == 1 and replies and replies[0]["code"] == "BUSY" and '"ok":true' in holder_out and code2 == 0
                 and (lock_file.parent.stat().st_mode & 0o777) == 0o700, out.strip())
    start = time.monotonic()
    code, replies, out = run_helper(binary, "run", "300", "100000", "sh", "-c", "echo started; sleep 20")
    elapsed = time.monotonic() - start
    ok &= report(f"bounded child: killed at the deadline {tag}",
                 code == 0 and replies[0]["timed_out"] is True and replies[0]["stdout"] == "started\n" and elapsed < 10, f"{elapsed:.1f}s {out.strip()}")
    code, replies, out = run_helper(binary, "run", "5000", "1000", "sh", "-c", "yes")
    ok &= report(f"bounded child: killed past the output cap {tag}",
                 code == 0 and replies[0]["overflowed"] is True and len(replies[0]["stdout"]) == 1000, out.strip()[:200])
    code, replies, out = run_helper(binary, "run", "5000", "1000", "sh", "-c", 'printf "%s" "${HOME-unset}"; exit 4')
    ok &= report(f"bounded child: environment limited to PATH, exit code kept {tag}",
                 code == 0 and replies[0]["stdout"] == "unset" and replies[0]["code"] == 4, out.strip())
    code, replies, out = run_helper(binary, "fail")
    code2, replies2, out2 = run_helper(binary, "nope")
    ok &= report(f"failures print JSON with their exit code {tag}",
                 code == 3 and replies == [{"ok": False, "code": "DEMO_FAILURE", "error": "failed on purpose"}]
                 and code2 == 2 and replies2[0]["code"] == "INVALID_ARGUMENT", out.strip())
    code, replies, out = run_helper(binary, "panic")
    ok &= report(f"a panic still prints JSON and exits 101, without abort {tag}",
                 code == 101 and replies == [{"ok": False, "code": "INTERNAL", "error": "internal error"}]
                 and "panicked on purpose" in out, out.strip())
    raw = subprocess.run([bytes(binary), b"args", b"caf\xe9"], capture_output=True, timeout=60)
    ok &= report(f"a non-UTF-8 argument is an INVALID_ARGUMENT reply, not a panic {tag}",
                 raw.returncode == 2 and json.loads(raw.stdout)["code"] == "INVALID_ARGUMENT" and b"panicked" not in raw.stderr,
                 (raw.stdout + raw.stderr).decode(errors="replace").strip())
    ok &= favicon_tests(binary, tag, base / f"favicon-{arch}")
    ok &= sandbox_tests(binary, arch, tag)
    return ok


def png(size, length):
    data = b"\x89PNG\r\n\x1a\n\0\0\0\x0dIHDR" + size.to_bytes(4, "big") * 2 + bytes([8, 6, 0, 0, 0, 0, 0, 0, 0])
    return data + b"B" * max(0, length - len(data))


def favicon_tests(binary, tag, root):
    """foamy_helper::favicon::run, browser-favicon.py's contract (feature `favicon`)."""
    import sqlite3
    ok = True
    profile = root / "config/vivaldi/Profile 1"
    profile.mkdir(parents=True)
    icon = png(32, 5000)
    with sqlite3.connect(profile / "Favicons") as db:
        db.executescript("CREATE TABLE icon_mapping (page_url TEXT, icon_id INTEGER); "
                         "CREATE TABLE favicon_bitmaps (icon_id INTEGER, image_data BLOB, width INTEGER, height INTEGER, last_updated INTEGER);")
        db.execute("INSERT INTO icon_mapping VALUES ('https://teams.microsoft.com/chat', 1)")
        db.execute("INSERT INTO favicon_bitmaps VALUES (1, ?, 32, 32, 100)", (icon,))
    db.close()
    env = dict(os.environ, XDG_CONFIG_HOME=str(root / "config"), XDG_CACHE_HOME=str(root / "cache"))

    def ask(request):
        result = subprocess.run([str(binary), "favicon"], input=json.dumps(request), capture_output=True, text=True,
                                env=env, timeout=60)
        return result.returncode, result.stdout, result.stderr

    code, out, err = ask({"browser": "vivaldi", "hostname": "teams.microsoft.com"})
    reply = json.loads(out) if code == 0 else {}
    path = Path(reply.get("source", "").removeprefix("file://"))
    ok &= report(f"favicon: found in a local cache, copied 0600, the Python reply format {tag}",
                 code == 0 and reply.get("status") == "found" and path.read_bytes() == icon
                 and (path.stat().st_mode & 0o777) == 0o600 and out.startswith('{"source": "file://'), out + err)
    code, out, _ = ask({"browser": "vivaldi", "hostname": "teams.microsoft.com"})
    ok &= report(f"favicon: reused from the cache {tag}", code == 0 and json.loads(out)["status"] == "cached", out)
    code, out, _ = ask({"browser": "firefox", "hostname": "example.com"})
    code2, out2, err2 = ask({"browser": "vivaldi", "hostname": "example.com:443"})
    ok &= report(f"favicon: unsupported browser; an invalid host is an error, exit 1 {tag}",
                 code == 0 and out == '{"source": "", "status": "unsupported-browser"}\n' and code2 == 1
                 and out2 == '{"source": "", "status": "error"}\n' and "Favicon lookup failed" in err2, out + out2 + err2)
    return ok


def sandbox_tests(binary, arch, tag):
    """foamy_helper::sandbox (feature `sandbox`). qemu-user has neither
    seccomp nor Landlock, so on aarch64 the helper must report UNSUPPORTED
    instead of running unrestricted."""
    ok = True
    _, replies, out = run_helper(binary, "seccomp", "/bin/sh", "-c", "/usr/bin/true && echo spawned; exit 0")
    _, replies2, out2 = run_helper(binary, "exec-only", os.path.realpath("/bin/sh"), "-c", "exec /usr/bin/true")
    if arch == "x86_64":
        ok &= report(f"seccomp: the decoder filter denies new processes {tag}",
                     replies and "not permitted" in replies[0].get("stderr", ""), out.strip())
        ok &= report(f"Landlock: only the program itself may execute {tag}",
                     replies2 and replies2[0].get("code") == 126, out2.strip())
    else:
        ok &= report(f"seccomp and Landlock fail closed where unsupported {tag}",
                     replies and replies[0].get("code") in ("UNSUPPORTED", "ERROR") and replies2
                     and replies2[0].get("code") in ("UNSUPPORTED", "ERROR"), (out + out2).strip())
    _, replies, out = run_helper(binary, "bwrap-argv")
    ok &= report(f"bwrap argv: github_status's namespace {tag}",
                 replies and replies[0]["argv"] == ["/usr/bin/bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--unshare-pid",
                                                    "--proc", "/proc", "--unshare-ipc", "--unshare-uts", "--die-with-parent",
                                                    "--", "git", "status"], out.strip())
    return ok


def tamper_tests(plugin, base):
    ok = True
    x86 = plugin / "bin/x86_64" / BINARY
    arm = plugin / "bin/aarch64" / BINARY
    pin = plugin / "native/native.pin"
    saved = {path: path.read_bytes() for path in (x86, arm, pin)}

    def restore():
        for path, data in saved.items():
            path.write_bytes(data)
        x86.chmod(0o755)
        arm.chmod(0o755)

    def both(fragment):
        code, out = kit_check(plugin)
        code2, out2 = sh(CHECK, "--no-lint", plugin)
        return code != 0 and fragment in out and code2 != 0 and fragment in out2, (out + out2).strip()

    def pin_sha(rel, data):
        text = pin.read_text().splitlines()
        sha = foamykit.sha256(data)
        pin.write_text("\n".join(f"{sha}  {rel}" if line.endswith(f"  {rel}") else line for line in text) + "\n")

    data = bytearray(saved[x86])
    data[len(data) // 2] ^= 0xFF
    x86.write_bytes(bytes(data))
    passed, detail = both("checksum differs from native.pin")
    ok &= report("a modified binary fails the checksum (kit-check and check.sh)", passed, detail)
    restore()
    x86.chmod(0o644)
    passed, detail = both("is not executable")
    ok &= report("a binary without the executable bit fails", passed, detail)
    restore()
    dynamic = Path(shutil.which("true") or "/usr/bin/true").resolve().read_bytes()
    x86.write_bytes(dynamic)
    pin_sha(f"bin/x86_64/{BINARY}", dynamic)
    passed, detail = both("dynamically linked")
    elf = foamykit.elf_problem(dynamic, "x86_64") or ""
    ok &= report("a dynamically linked binary fails", passed and "dynamically linked" in elf, detail[:300])
    restore()
    arm.write_bytes(saved[x86])
    pin_sha(f"bin/aarch64/{BINARY}", saved[x86])
    passed, detail = both("is not a 64-bit aarch64")
    ok &= report("a binary for the wrong arch fails", passed and "ELF machine 62" in (foamykit.elf_problem(saved[x86], "aarch64") or ""), detail[:300])
    restore()
    arm.unlink()
    arm.symlink_to(x86)
    passed, detail = both("is missing or not a regular file")
    ok &= report("a symlinked binary fails", passed, detail)
    arm.unlink()
    restore()
    main = plugin / "native/src/main.rs"
    source = main.read_bytes()
    main.write_bytes(source + b"// changed\n")
    passed, detail = both(f"{BINARY} is stale")
    ok &= report("an edited crate source makes the binaries stale", passed, detail)
    main.write_bytes(source)
    (plugin / "native/src/extra.rs").write_text("// new module\n")
    passed, detail = both(f"{BINARY} is stale")
    ok &= report("a new crate file makes the binaries stale", passed, detail)
    (plugin / "native/src/extra.rs").unlink()
    lock = plugin / "Cargo.lock"
    lock_data = lock.read_bytes()
    lock.write_bytes(lock_data + b"\n")
    passed, detail = both(f"{BINARY} is stale")
    ok &= report("a changed root Cargo.lock makes the binaries stale", passed, detail)
    lock.write_bytes(lock_data)
    (plugin / "native/target").mkdir()
    (plugin / "native/target/junk").write_text("x")
    code, out = kit_check(plugin)
    ok &= report("native/target/ is not part of the source hash", code == 0, out.strip())
    (plugin / "native/target/CACHEDIR.TAG").write_text("Signature: 8a477f597d28d172789f06886806bc55\n")
    code, out = kit_check(plugin)
    code2, out2 = sh(CHECK, "--no-lint", plugin)
    ok &= report("a cargo target dir inside the plugin is a warning in kit-check and check.sh, not a failure",
                 code == 0 and "native/target/ is a cargo target dir" in out and code2 == 0
                 and "native/target/ is a cargo target dir" in out2, (out + out2).strip())
    shutil.rmtree(plugin / "native/target")
    old_kit = base / "next-kit"
    shutil.copytree(KIT_ROOT, old_kit, ignore=shutil.ignore_patterns(".git", "tests", "preview"))
    (old_kit / "VERSION").write_text("9.9.9\n")
    sh(old_kit / "sync.sh", plugin)
    code, out = kit_check(plugin)
    stamp = (plugin / "kit/rust/foamy-helper/src/lib.rs").read_text().splitlines()[0]
    ok &= report("a kit version bump alone keeps the binaries fresh (stamps are not hashed)",
                 code == 0 and "foamy-kit 9.9.9 " in stamp, out.strip())
    sh(SYNC, plugin)
    code, out = kit_check(plugin)
    ok &= report("intact again after the tamper tests", code == 0, out.strip())
    return ok


def rust_tests(base):
    ok = True
    cache = base / "cache"
    env = {"FOAMY_NATIVE_CACHE": str(cache)}
    crate_env = dict(env, CARGO_TARGET_DIR=str(cache / "foamy-kit"), RUSTUP_TOOLCHAIN=CHANNEL)
    crate = KIT_ROOT / "kit/rust/foamy-helper"
    for step in (["cargo", "fmt", "--check"],
                 ["cargo", "clippy", "--locked", "--all-targets", "--", "-D", "warnings"],
                 ["cargo", "clippy", "--locked", "--all-targets", "--features", "favicon", "--", "-D", "warnings"],
                 ["cargo", "clippy", "--locked", "--all-targets", "--features", "sandbox", "--", "-D", "warnings"],
                 ["cargo", "clippy", "--locked", "--all-targets", "--features", "tls", "--", "-D", "warnings"],
                 ["cargo", "clippy", "--locked", "--all-targets", "--all-features", "--", "-D", "warnings"],
                 ["cargo", "test", "--locked", "--all-features"]):
        code, out = sh(*step, env=crate_env, cwd=crate)
        tail = [line for line in out.splitlines() if "test result" in line or "error" in line.lower()][:4]
        features = next((s for s in step if s in ("favicon", "sandbox", "tls", "--all-features")), "default features")
        ok &= report(f"foamy-helper: {' '.join(step[:2])} ({features})", code == 0, "; ".join(tail) if tail else "")
    ok &= report("the kit's cargo commands write nothing into kit/", not (crate / "target").exists())

    plugin = fresh(base, "foamy-native-demo")
    sh(SYNC, plugin, "--components", "FoamyNative")
    before = snapshot(plugin)
    code, out = sh(BUILD, plugin, env=env)
    after = snapshot(plugin)
    added = sorted(set(after) - set(before))
    changed = sorted(rel for rel in before if after.get(rel) != before[rel])
    ok &= report("build-native.sh builds both arches", code == 0 and f"{BINARY} ({CHANNEL})" in out, last(out) if out.strip() else "")
    ok &= report("the build adds only the binaries and native.pin to the plugin (cargo output stays in the cache)",
                 added == [f"bin/aarch64/{BINARY}", f"bin/x86_64/{BINARY}", "native/native.pin"] and not changed
                 and (cache / "foamy-native-demo").is_dir(), f"added {added}, changed {changed}")
    sizes = {arch: (plugin / "bin" / arch / BINARY).stat().st_size for arch in foamykit.ARCHES}
    modes = {arch: (plugin / "bin" / arch / BINARY).stat().st_mode & 0o777 for arch in foamykit.ARCHES}
    print(f"    binary sizes: x86_64 {sizes['x86_64']} bytes, aarch64 {sizes['aarch64']} bytes")
    ok &= report("binaries are mode 0755 and under 2 MB", all(m == 0o755 for m in modes.values()) and max(sizes.values()) < 2 << 20)
    pin = foamykit.read_pin(plugin / "native/native.pin")
    ok &= report("native.pin records crate, binary, toolchain, kit version, source hash and both checksums",
                 pin.get("crate") == "native" and pin.get("binary") == BINARY and pin.get("toolchain") == CHANNEL
                 and pin.get("kit") == foamykit.kit_version() and pin.get("source") == foamykit.native_source_hash(plugin, "native")
                 and sorted(pin["files"]) == [f"bin/aarch64/{BINARY}", f"bin/x86_64/{BINARY}"])
    code, out = kit_check(plugin)
    ok &= report("generated tests/kit-check.sh passes with the native binaries (clean environment)",
                 code == 0 and f"native: {BINARY}" in out, out.strip())
    code, out = sh(CHECK, plugin)
    ok &= report("check.sh passes on the fixture plugin (kit, native pin, lint)", code == 0, out.strip())
    code, out = sh(harness_validator(), plugin)
    ok &= report("omarchy-plugin-validate accepts the built plugin", code == 0, out.strip())
    first = {rel: (plugin / rel).stat().st_mtime_ns for rel in added}
    code, out = sh(BUILD, plugin, env=env)
    ok &= report("a second build is a no-op", code == 0 and "up to date" in out
                 and first == {rel: (plugin / rel).stat().st_mtime_ns for rel in added}, last(out))
    code, out = sh(BUILD, plugin, "--verify", env=env)
    ok &= report("--verify: a clean rebuild is byte-identical for both arches",
                 code == 0 and out.count("byte-identical") == 2 and "verify OK" in out, last(out))
    leftover = sorted(p.name for p in cache.iterdir() if "verify" in p.name)
    ok &= report("--verify removes its fresh target dir", not leftover, f"{leftover}")
    elsewhere = base / "another" / "checkout" / "foamy-native-demo"
    shutil.copytree(plugin, elsewhere)
    code, out = sh(BUILD, elsewhere, "--verify", env=env)
    ok &= report("a checkout at another path rebuilds byte-identical binaries", code == 0 and "verify OK" in out,
                 last(out))
    shutil.rmtree(elsewhere.parent.parent)
    code, out = sh(BUILD, plugin, "--test", env=env)
    ok &= report("build-native.sh --test runs fmt, clippy and the crate's tests", code == 0 and "fmt, clippy and tests OK" in out,
                 last(out))

    binfmt = Path("/proc/sys/fs/binfmt_misc/qemu-aarch64").exists()
    for arch in ("x86_64", "aarch64"):
        if arch == "aarch64" and not binfmt:
            print("SKIP helper tests (aarch64): no qemu-aarch64 binfmt")
            continue
        ok &= helper_tests(plugin, arch, base)

    code, out = sh("node", "-e", 'const N = require(process.argv[1]).load("FoamyNative"); '
                   'process.stdout.write(JSON.stringify([N.command(process.argv[2], process.argv[3], ["args", "a b", ""]), '
                   'N.command(process.argv[2], "foamy-missing-helper", [])]))',
                   plugin / "kit/node-loader.cjs", plugin, BINARY)
    commands = json.loads(out) if code == 0 else [["false"], ["false"]]
    code, replies, out = run_helper(*commands[0])
    code2, _, _ = run_helper(*commands[1])
    ok &= report("FoamyNative.command (from the plugin's kit) runs the built helper; a missing one exits 127",
                 code == 0 and replies[0]["args"] == ["a b", ""] and code2 == 127, out.strip())

    hosts = [host for host, path in harness.HOSTS.items() if (path / "Commons").is_dir() and (path / "Ui").is_dir()]
    for host in harness.HOSTS:
        if host in hosts:
            ok &= run_shell("Native.qml", host, plugin, host)
        else:
            print(f"SKIP native {host}: host not found at {harness.HOSTS[host]} (set FOAMY_HOST_{host.replace('.', '')})")

    ok &= tamper_tests(plugin, base)

    profiled = fresh(base, "profiled")
    sh(SYNC, profiled, "--components", "FoamyNative")
    with open(profiled / "native/Cargo.toml", "a") as stream:
        stream.write('\n[profile.release]\nopt-level = 3\n')
    code, out = sh(BUILD, profiled, env=env)
    ok &= report("a crate-level [profile] is refused", code != 0 and "declares [profile]" in out, out.strip())
    code, out = sh(BUILD, plugin, env={"FOAMY_NATIVE_CACHE": str(plugin / "cache")})
    ok &= report("a cargo cache inside the plugin is refused", code != 0 and "inside the plugin" in out and not (plugin / "cache").exists(), out.strip())
    for name, edit, fragment in (
            ("no-workspace", lambda p: (p / "Cargo.toml").unlink(), "no Cargo.toml at the plugin root"),
            ("not-member", lambda p: (p / "Cargo.toml").write_text('[workspace]\nmembers = []\nexclude = ["kit"]\n'), "in members"),
            ("crate-lock", lambda p: shutil.copyfile(p / "Cargo.lock", p / "native/Cargo.lock"), "native/Cargo.lock is unused"),
            ("no-lock", lambda p: (p / "Cargo.lock").unlink(), "Cargo.lock is missing")):
        broken = fresh(base, name)
        sh(SYNC, broken, "--components", "FoamyNative")
        edit(broken)
        code, out = sh(BUILD, broken, env=env)
        ok &= report(f"build-native.sh refuses a broken workspace ({name})", code != 0 and fragment in out, out.strip())
    unsynced = fresh(base, "unsynced")
    code, out = sh(BUILD, unsynced, env=env)
    ok &= report("building without FoamyNative synced is refused", code != 0 and "--add FoamyNative" in out, out.strip())

    # foamy-menu's layout: crate in search/, binary foamy-<x>-search.
    menu = fresh(base, "menu-layout")
    (menu / "native").rename(menu / "search")
    for path in (menu / "search/Cargo.toml", menu / "Cargo.lock"):
        path.write_text(path.read_text().replace('name = "foamy-native-demo-helper"', 'name = "foamy-native-demo-search"'))
    workspace = menu / "Cargo.toml"
    workspace.write_text(workspace.read_text().replace('members = ["native"]', 'members = ["search"]'))
    sh(SYNC, menu, "--components", "FoamyNative")
    code, out = sh(BUILD, menu, "--crate", "search", "--bin", "foamy-native-demo-search", env=env)
    pin = foamykit.read_pin(menu / "search/native.pin")
    code2, out2 = sh(BUILD, menu, env=env)
    code3, out3 = kit_check(menu)
    ok &= report("a configured crate dir and binary name (search/, foamy-…-search) are kept in native.pin",
                 code == 0 and pin.get("crate") == "search" and pin.get("binary") == "foamy-native-demo-search"
                 and (menu / "bin/aarch64/foamy-native-demo-search").is_file() and code2 == 0 and "up to date" in out2
                 and code3 == 0 and "native: foamy-native-demo-search" in out3, (out + out2 + out3).strip().splitlines()[-1])
    return ok


def last(out):
    lines = out.strip().splitlines()
    return lines[-1] if lines else ""


def harness_validator():
    return shutil.which("omarchy-plugin-validate") or "/usr/share/omarchy/bin/omarchy-plugin-validate"


def main():
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-native-"))
    ok = sync_tests(base)
    if shutil.which("cargo") and shutil.which("rustup"):
        ok &= rust_tests(base)
    else:
        print("SKIP Rust tests: cargo/rustup not installed")
    if ok:
        shutil.rmtree(base, ignore_errors=True)
    else:
        print(f"    kept {base}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
