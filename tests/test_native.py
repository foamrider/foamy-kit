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
                       "kit/native/native.py", "kit/native/build-native.sh", ".github/workflows/verify-native.yml",
                       "kit/rust/foamy-helper/Cargo.toml", "rust-toolchain.toml", "tests/kit-check.sh"] + rust_sources)
    lock = foamykit.read_lock(plugin)
    ok &= report("sync copies the FoamyNative tree (subdirectories, build tool, root rust-toolchain.toml and CI workflow)",
                 code == 0 and sorted(lock["files"]) == expected and lock["components"] == ["FoamyNative"],
                 out.strip() if code else f"{len(expected)} files")
    ok &= report("the kit crate's own Cargo.lock is not vendored", not (plugin / "kit/rust/foamy-helper/Cargo.lock").exists())
    lib = (plugin / "kit/rust/foamy-helper/src/lib.rs").read_text().splitlines()
    toolchain = (plugin / "rust-toolchain.toml").read_text().splitlines()
    cargo = (plugin / "kit/rust/foamy-helper/Cargo.toml").read_text().splitlines()
    ok &= report("Rust and TOML files are stamped on line 1 with their comment syntax",
                 lib[0].startswith("// foamy-kit ") and toolchain[0].startswith("# foamy-kit ")
                 and cargo[0].startswith("# foamy-kit ") and lib[1].startswith("//!"))
    tool = (plugin / "kit/native/native.py").read_text().splitlines()
    wrapper = (plugin / "kit/native/build-native.sh")
    workflow = (plugin / ".github/workflows/verify-native.yml").read_text().splitlines()
    ok &= report("the build tool keeps its shebang, the wrapper is executable, the workflow is stamped on line 1",
                 tool[0].startswith("#!") and tool[1].startswith("# foamy-kit ") and wrapper.stat().st_mode & 0o111
                 and wrapper.read_text().splitlines()[1].startswith("# foamy-kit ") and workflow[0].startswith("# foamy-kit "))
    root_files = sorted({dest for spec in foamykit.load_components().values() for dest in spec.get("rootFiles", {})})
    template = (KIT_ROOT / "tools/kit-check.sh.in").read_text()
    ok &= report("the build tool's ROOT_FILES, components.json rootFiles and kit-check.sh agree",
                 sorted(foamykit.ROOT_FILES) == root_files and all(f"$rel != {rel}" in template for rel in root_files),
                 f"{root_files}")
    attribute = foamykit.stamped("kit/x.rs", b"#![forbid(unsafe_code)]\nfn main() {}\n", "0.5.0").decode().splitlines()
    ok &= report("a leading #![attribute] is not taken for a shebang", attribute[0].startswith("// foamy-kit 0.5.0 "))
    native = foamykit.native
    ok &= report("the build tool's copy of foamy-kit's LICENSE (for kit/rust in the notices) equals LICENSE",
                 native.KIT_LICENSE == (KIT_ROOT / "LICENSE").read_text())
    ok &= report("the embedded musl COPYRIGHT is the v1.2.5 file",
                 foamykit.sha256(native.MUSL_COPYRIGHT.encode()) == "f9bc4423732350eb0b3f7ed7e91d530298476f8fec0c6c427a1c04ade22655af")
    files = [("LICENSE-MIT", b"MIT text\r\n"), ("licenses/ISC.txt", b"ISC"), ("third_party/fiat/LICENSE", b"fiat"),
             ("tests/LICENSE", b"test data"), ("license.rs", b"code"), ("src/a.rs", b"// Copyright 2020 A\n// SPDX-License-Identifier: MIT OR Apache-2.0\n"),
             ("src/b.rs", b"//! The above copyright notice and this permission notice shall be included\n"),
             ("benches/c.rs", b"// Copyright 1999 B\n")]
    shipped = native.license_files(files, {})
    ok &= report("license files: root, LICENSES/ and vendored dirs, not tests or code",
                 shipped == [("LICENSE-MIT", "MIT text"), ("licenses/ISC.txt", "ISC"), ("third_party/fiat/LICENSE", "fiat")], f"{shipped}")
    ok &= report("source headers: copyright lines and SPDX ids, not license boilerplate or benches",
                 native.header_notices(files) == (["Copyright 2020 A"], ["Apache-2.0", "MIT"]), f"{native.header_notices(files)}")
    elf = (b"\0/cargo/registry/src/index.crates.io-1949cf8c6b5b557f/rustls-webpki-0.103.16/src/crl/types.rs\0"
           b"/rust/deps/wasip2-1.0.2+wasi-0.2.9/src/lib.rs\0/rustc/" + b"a" * 40 + b"/library/std/src/io.rs\0")
    ok &= report("the binary's embedded source paths name the linked crates and versions",
                 native.elf_sources(elf) == {"crates": {("rustls-webpki", "0.103.16")}, "std_deps": {("wasip2", "1.0.2+wasi-0.2.9")},
                                             "std": {"std"}}, f"{native.elf_sources(elf)}")
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
    ok &= report("dropping FoamyNative removes kit/rust, kit/native, rust-toolchain.toml and .github (no empty dirs)",
                 code == 0 and not (plugin / "rust-toolchain.toml").exists() and not (plugin / ".github").exists()
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
    ok &= report("the build adds only the binaries, native.pin and THIRD_PARTY_NOTICES.md (cargo output stays in the cache)",
                 added == ["THIRD_PARTY_NOTICES.md", f"bin/aarch64/{BINARY}", f"bin/x86_64/{BINARY}", "native/native.pin"]
                 and not changed and (cache / "foamy-native-demo").is_dir(), f"added {added}, changed {changed}")
    ok &= notices_tests(plugin, base, env)
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
    # The plugin on its own: a copy with no foamy-kit next to it, verified with
    # its vendored tool from its root, the way the README and CI run it.
    alone = base / "alone" / "foamy-native-demo"
    shutil.copytree(plugin, alone)
    out_dir = base / "alone-rebuilt"
    code, out = sh("bash", "kit/native/build-native.sh", ".", "--verify", "--out", out_dir, env=env, cwd=alone)
    kept = {arch: (out_dir / arch / BINARY).read_bytes() if (out_dir / arch / BINARY).is_file() else b"" for arch in foamykit.ARCHES}
    ok &= report("the plugin's own kit/native/build-native.sh verifies it without foamy-kit; --out keeps the identical rebuild",
                 code == 0 and "verify OK" in out
                 and all(kept[arch] == (plugin / "bin" / arch / BINARY).read_bytes() for arch in kept)
                 and all((out_dir / arch / BINARY).stat().st_mode & 0o111 for arch in kept), last(out))
    code, out = sh("bash", "kit/native/build-native.sh", ".", "--verify", "--out", alone / "rebuilt", env=env, cwd=alone)
    code2, out2 = sh("bash", "kit/native/build-native.sh", ".", "--out", out_dir, env=env, cwd=alone)
    ok &= report("--out inside the plugin, or without --verify, is refused",
                 code != 0 and "inside the plugin" in out and not (alone / "rebuilt").exists()
                 and code2 != 0 and "--out goes with --verify" in out2, (out + out2).strip())
    # A symlink inside --out (an arch dir into the plugin's bin/) must not let
    # the export overwrite the binaries being verified; an existing file is refused.
    linked_out = base / "linked-out"
    linked_out.mkdir()
    (linked_out / "x86_64").symlink_to(alone / "bin/x86_64")
    saved = {arch: (alone / "bin" / arch / BINARY).read_bytes() for arch in foamykit.ARCHES}
    (alone / "bin/x86_64" / BINARY).write_bytes(b"tampered")
    code, out = sh("bash", "kit/native/build-native.sh", ".", "--verify", "--out", linked_out, env=env, cwd=alone)
    ok &= report("--verify --out refuses a symlinked arch dir and still reports the tampered binary",
                 code != 0 and (alone / "bin/x86_64" / BINARY).read_bytes() == b"tampered" and "verify OK" not in out,
                 last(out))
    (alone / "bin/x86_64" / BINARY).write_bytes(saved["x86_64"])
    code, out = sh("bash", "kit/native/build-native.sh", ".", "--verify", "--out", out_dir, env=env, cwd=alone)
    ok &= report("--out refuses to replace an earlier export", code != 0 and "already exists" in out, last(out))
    shutil.rmtree(alone.parent)
    shutil.rmtree(out_dir)
    shutil.rmtree(linked_out)
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

    for host in harness.available_hosts(what="native", require=False):
        ok &= run_shell("Native.qml", host, plugin, host)

    ok &= tamper_tests(plugin, base)
    ok &= racing_edit_test(plugin, base, env)
    ok &= two_helpers_test(base, env)
    ok &= symlinked_bin_test(plugin, base, env)

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
            ("no-lock", lambda p: (p / "Cargo.lock").unlink(), "Cargo.lock is missing"),
            ("symlinked-source", lambda p: ((p / "native/src/real.rs").write_text((p / "native/src/main.rs").read_text()),
                                             (p / "native/src/main.rs").unlink(), (p / "native/src/main.rs").symlink_to("real.rs")),
             "symlinked build inputs"),
            ("cargo-config", lambda p: ((p / ".cargo").mkdir(), (p / ".cargo/config.toml").write_text('[build]\nrustc-wrapper = "/bin/true"\n')),
             "Cargo configuration inside the plugin"),
            ("crate-cargo-config", lambda p: ((p / "native/.cargo").mkdir(), (p / "native/.cargo/config").write_text('[build]\n')),
             "native/.cargo/config"),
            ("outside-path-dep", lambda p: open(p / "native/Cargo.toml", "a").write('\n[dev-dependencies]\ncommon = { path = "../common" }\n'),
             "path dependencies outside the hashed sources")):
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


def notices_tests(plugin, base, env):
    """THIRD_PARTY_NOTICES.md for the fixture: the crates linked for both
    musl targets with their Cargo.lock checksums and shipped license texts,
    nothing that is only on the build host, the toolchain's code; byte-stable;
    --verify and the checks catch an edited, mismatched or missing file."""
    ok = True
    path = plugin / "THIRD_PARTY_NOTICES.md"
    text = path.read_text()
    lock = foamykit.native.lock_packages(plugin)
    table = text.split("### Toolchain code")[0]
    rows = {line.split(" | ")[0][2:]: line for line in table.splitlines() if line.startswith("| ") and " | " in line}
    linked = {"serde", "serde_core", "serde_json", "rustix", "linux-raw-sys", "libc", "landlock", "seccompiler",
              "thiserror", "enumflags2", "bitflags", "itoa", "memchr", "zmij"}
    host_only = {"serde_derive", "thiserror-impl", "enumflags2_derive", "syn", "quote", "proc-macro2", "unicode-ident",
                 "windows-sys", "windows-link", "errno"}
    checksums = all(f"`{lock[(name, rows[name].split(' | ')[1])]['checksum']}`" in rows[name] for name in linked if name in rows)
    ok &= report("notices list the crates linked into both arches, with version, SPDX license and Cargo.lock checksum",
                 linked <= set(rows) and checksums and all(" | both | " in rows[name] for name in linked),
                 f"missing {sorted(linked - set(rows))}")
    ok &= report("proc-macro crates, their dependencies and other-platform crates are not listed",
                 not host_only & set(rows), f"{sorted(host_only & set(rows))}")
    serde_json = rows.get("serde_json", "")
    ids = [ref.split("](")[0].lstrip("[") for ref in serde_json.split(" | ")[-1].split(", ")]
    bodies = {ident: text.split(f"### {ident}\n", 1)[1].split("\n### ", 1)[0] for ident in ids if f"### {ident}\n" in text}
    ok &= report("a crate's shipped license files are reproduced (serde_json: LICENSE-MIT and LICENSE-APACHE)",
                 any("Permission is hereby granted" in b and "serde_json 1.0.154: `LICENSE-MIT`" in b for b in bodies.values())
                 and any("Apache License" in b and "serde_json 1.0.154: `LICENSE-APACHE`" in b for b in bodies.values()),
                 serde_json)
    ok &= report("the first-party crates, the standard library, musl and LLVM are covered",
                 "`kit/rust/foamy-helper/` (foamy-kit, vendored)" in text and foamykit.native.KIT_LICENSE.strip() in text
                 and "| Rust standard library (" in text and "Copyright © 2005-2020 Rich Felker, et al." in text
                 and "src/llvm-project" in text and f"- `native/native.pin`: source `{foamykit.read_pin(plugin / 'native/native.pin')['source']}`" in text)
    code, out = sh(BUILD, plugin, "--notices", env=env)
    ok &= report("--notices regenerates the same bytes", code == 0 and "up to date" in out and path.read_text() == text, last(out))

    saved = path.read_bytes()
    path.write_bytes(saved.replace(b"Rich Felker, et al.", b"someone else", 1))
    code, out = sh(BUILD, plugin, "--verify", env=env)
    code2, out2 = kit_check(plugin)
    ok &= report("--verify fails on an edited notices file (kit-check, without cargo, cannot see the text)",
                 code != 0 and "THIRD_PARTY_NOTICES.md: a fresh generation differs" in out and code2 == 0, last(out))
    path.write_bytes(saved.replace(b"sha256 `", b"sha256 `0", 1))
    code, out = kit_check(plugin)
    code2, out2 = sh(CHECK, "--no-lint", plugin)
    ok &= report("kit-check and check.sh fail when the notices name other binaries than native.pin",
                 code != 0 and "THIRD_PARTY_NOTICES.md does not match native/native.pin" in out
                 and code2 != 0 and "does not match native/native.pin" in out2, (out + out2).strip())
    path.unlink()
    code, out = kit_check(plugin)
    code2, out2 = sh(CHECK, "--no-lint", plugin)
    ok &= report("kit-check and check.sh fail when the notices file is missing",
                 code != 0 and "THIRD_PARTY_NOTICES.md is missing" in out and code2 != 0 and "THIRD_PARTY_NOTICES.md is missing" in out2,
                 (out + out2).strip())
    code, out = sh(BUILD, plugin, "--notices", env=env)
    ok &= report("--notices writes it again, byte-identical", code == 0 and path.read_bytes() == saved, last(out))

    main = plugin / "native/src/main.rs"
    source = main.read_bytes()
    main.write_bytes(source + b"// changed\n")
    code, out = sh(BUILD, plugin, "--notices", env=env)
    main.write_bytes(source)
    ok &= report("--notices refuses stale binaries (it never pins notices to sources the binaries weren't built from)",
                 code != 0 and "is stale" in out and path.read_bytes() == saved, out.strip()[-300:])
    ok &= isc_notice_test(plugin, base, env)
    ok &= std_notice_tests(plugin, base, env, text)
    return ok


def fake_crate(home, name, version, files):
    """A .crate archive in a fake CARGO_HOME's registry cache; its sha256."""
    import io
    import tarfile
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for rel, data in sorted(files.items()):
            info = tarfile.TarInfo(f"{name}-{version}/{rel}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    path = home / "registry/cache/index.crates.io-0000000000000000" / f"{name}-{version}.crate"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(buffer.getvalue())
    return foamykit.sha256(buffer.getvalue())


WEBPKI_LICENSE = b"""Except as otherwise noted, this project is licensed under the following
(ISC-style) terms:

Copyright 2015 Brian Smith.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.
"""


def isc_notice_test(plugin, base, env):
    """The rustls-webpki case: an ISC crate whose LICENSE carries the
    copyright line ends up in the notices with its text; a crate with no
    license file gets the standard texts of its SPDX ids; an archive that
    doesn't match its Cargo.lock checksum is refused."""
    native = foamykit.native
    home = base / "fake-cargo-home"
    isc = fake_crate(home, "fake-webpki", "0.103.16", {
        "Cargo.toml": b'[package]\nname = "fake-webpki"\nversion = "0.103.16"\nlicense = "ISC"\n',
        "LICENSE": WEBPKI_LICENSE,
        "src/lib.rs": b"// Copyright 2015-2021 Brian Smith.\n// SPDX-License-Identifier: ISC\npub fn f() {}\n",
        "tests/vectors.rs": b"// Copyright 1999 Not Linked\n"})
    bare = fake_crate(home, "fake-graviola", "0.4.4", {
        "Cargo.toml": b'[package]\nname = "fake-graviola"\nversion = "0.4.4"\nlicense = "Apache-2.0 OR ISC OR MIT-0"\n',
        "src/lib.rs": b"// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.\n"})
    legal_only = fake_crate(home, "fake-legal", "1.0.0", {
        "Cargo.toml": b'[package]\nname = "fake-legal"\nversion = "1.0.0"\nlicense-file = "legal.txt"\n',
        "legal.txt": b"Fake Legal terms. Copyright 2024 Legal Only Ltd.\n"})
    legal_spdx = fake_crate(home, "fake-legal-spdx", "2.0.0", {
        "Cargo.toml": b'[package]\nname = "fake-legal-spdx"\nversion = "2.0.0"\nlicense = "MIT"\nlicense-file = "./docs/legal.txt"\n',
        "docs/legal.txt": b"MIT terms as shipped. Copyright 2024 Spdx And File Ltd.\n"})
    real_linked, real_lock, real_home = native.linked_packages, native.lock_packages, native.cargo_home
    fakes = {("fake-webpki", "0.103.16"): isc, ("fake-graviola", "0.4.4"): bare, ("fake-legal", "1.0.0"): legal_only,
             ("fake-legal-spdx", "2.0.0"): legal_spdx}

    def linked(plugin_dir, crate, triple, cargo_env_):
        found = real_linked(plugin_dir, crate, triple, cargo_env_)
        found.update({key: None for key in fakes})
        return found

    def lock(plugin_dir):
        packages = real_lock(plugin_dir)
        for (name, version), checksum in fakes.items():
            packages[(name, version)] = {"name": name, "version": version, "checksum": checksum,
                                         "source": "registry+https://github.com/rust-lang/crates.io-index"}
        return packages

    def cargo_home():
        return home if fake_home[0] else real_home()

    fake_home = [False]
    channel = native.toolchain_channel(plugin)
    pin = foamykit.read_pin(plugin / "native/native.pin")
    entry = {"crate": "native", "binary": BINARY, "source": pin["source"],
             "files": {arch: (plugin / "bin" / arch / BINARY).read_bytes() for arch in foamykit.ARCHES}}
    cargo = native.notices_env(plugin, "native", channel, base / "cache")
    native.linked_packages, native.lock_packages, native.cargo_home = linked, lock, cargo_home
    try:
        # Real crates from the real registry, the fakes from the fake home.
        real_files = native.crate_files

        def crate_files(name, version, checksum, fetch=None):
            fake_home[0] = (name, version) in fakes
            try:
                return real_files(name, version, checksum, fetch)
            finally:
                fake_home[0] = False

        native.crate_files = crate_files
        text = native.notices_bytes(plugin, channel, [entry], cargo, plugin / "native").decode()
        row = next((line for line in text.splitlines() if line.startswith("| fake-webpki | 0.103.16 | ISC | ")), "")
        isc_body = next((part for part in text.split("\n### N") if "fake-webpki 0.103.16: `LICENSE`" in part), "")
        headers = next((part for part in text.split("\n### N") if "fake-webpki 0.103.16: source file headers" in part), "")
        bare_ids = [p for p in text.split("\n### N") if "fake-graviola 0.4.4: standard" in p]
        ok = report("an ISC crate's LICENSE with its copyright line is reproduced (the rustls-webpki case)",
                    bool(row) and f"`{isc}`" in row and "Copyright 2015 Brian Smith." in isc_body
                    and "Permission to use, copy, modify" in isc_body and "Copyright 2015-2021 Brian Smith." in headers
                    and "Not Linked" not in text, row)
        ok &= report("a crate with no license file gets the standard text of each SPDX id, marked as such",
                     len(bare_ids) == 3 and any("MIT No Attribution" in p for p in bare_ids)
                     and any("Apache License" in p for p in bare_ids) and "Copyright Amazon.com, Inc." in text,
                     f"{len(bare_ids)} standard texts")
        legal = next((part for part in text.split("\n### N") if "fake-legal 1.0.0: `legal.txt`" in part), "")
        legal_spdx_part = next((part for part in text.split("\n### N") if "fake-legal-spdx 2.0.0: `docs/legal.txt`" in part), "")
        ok &= report("a nonstandard license-file is reproduced, alone or next to an SPDX license (no boilerplate instead)",
                     "Copyright 2024 Legal Only Ltd." in legal and "Copyright 2024 Spdx And File Ltd." in legal_spdx_part
                     and "fake-legal-spdx 2.0.0: standard" not in text and "fake-legal 1.0.0: standard" not in text,
                     next((line for line in text.splitlines() if line.startswith("| fake-legal")), ""))
        fakes[("fake-webpki", "0.103.16")] = "0" * 64
        try:
            native.notices_bytes(plugin, channel, [entry], cargo, plugin / "native")
            refused = ""
        except native.KitError as error:
            refused = str(error)
        ok &= report("a crate archive that doesn't match its Cargo.lock checksum is refused",
                     "does not match the Cargo.lock checksum of fake-webpki" in refused, refused)
    finally:
        native.linked_packages, native.lock_packages, native.cargo_home = real_linked, real_lock, real_home
        native.crate_files = real_files
    return ok


def std_notice_tests(plugin, base, env, text):
    """The standard library's crates.io dependencies in the fixture's
    notices: each at the version of the toolchain's library/Cargo.lock, with
    its own texts (from the checksum-verified .crate where the toolchain's
    notice file has no entry: addr2line, miniz_oxide, ...); generation fails
    when a detected dependency can't be matched or has no text."""
    native = foamykit.native
    ok = True
    rows = {line.split("`")[1]: line for line in text.split("### Toolchain code", 1)[1].splitlines()
            if line.startswith("| `") and "a dependency of the standard library" in line}
    locked = {name: version for name, version, _ in native.STD_LOCKS["1.99.1"]}
    seen = native.elf_sources((plugin / "bin/x86_64" / BINARY).read_bytes())["std_deps"]
    ok &= report("every standard library dependency the binary names is listed at its library/Cargo.lock version",
                 seen and all(name in rows and f"| {version} |" in rows[name] and locked[name] == version for name, version in seen),
                 f"{sorted(seen)}")
    texts = {name: [p for p in text.split("\n### N") if f"standard library dependency {name} {locked[name]}: `" in p]
             for name in ("addr2line", "miniz_oxide", "adler2", "object")}
    ok &= report("addr2line, miniz_oxide, adler2 and object ship their own texts, from the verified crates.io archives",
                 all(texts.values()) and all("notices from the crates.io archive, sha256 `" in rows.get(n, "") for n in texts)
                 and any("Permission is hereby granted" in p for p in texts["addr2line"])
                 and any("zlib" in p.lower() for p in texts["miniz_oxide"])
                 and "has no entry for these standard library dependencies" not in text, f"{ {n: len(t) for n, t in texts.items()} }")
    channel = native.toolchain_channel(plugin)
    pin = foamykit.read_pin(plugin / "native/native.pin")
    entry = {"crate": "native", "binary": BINARY, "source": pin["source"],
             "files": {arch: (plugin / "bin" / arch / BINARY).read_bytes() for arch in foamykit.ARCHES}}
    cargo = native.notices_env(plugin, "native", channel, base / "cache")
    real_lock, real_files = native.std_lock, native.std_crate_files

    def generate():
        try:
            native.notices_bytes(plugin, channel, [entry], cargo, plugin / "native")
            return ""
        except native.KitError as error:
            return str(error)

    detected = sorted(seen)[0] if seen else ("addr2line", "0.27.1")
    try:
        native.std_lock = lambda sysroot, ch: {n: ({"0.0.1": c} if n == detected[0] else {v: c})
                                               for n, v, c in native.STD_LOCKS["1.99.1"]}
        error = generate()
        ok &= report(f"a detected standard library dependency without a matching locked version fails ({detected[0]})",
                     f"the binaries contain {detected[0]} {detected[1]}" in error, error)
        native.std_lock = lambda sysroot, ch: {n: {v: c} for n, v, c in native.STD_LOCKS["1.99.1"] if n != "miniz_oxide"}
        error = generate()
        ok &= report("a sysroot crate missing from the standard library's lock fails (no notice, no file)",
                     "miniz_oxide is neither in the Rust repository nor in the standard library's Cargo.lock" in error, error)
        native.std_lock = real_lock
        native.std_crate_files = lambda n, v, c: [("Cargo.toml", b'[package]\nname = "x"\n')] if n == "addr2line" else real_files(n, v, c)
        error = generate()
        ok &= report("a standard library dependency with no notice text fails generation",
                     "addr2line 0.27.1 has neither a license file nor a license" in error, error)
    finally:
        native.std_lock, native.std_crate_files = real_lock, real_files
    saved = (plugin / "THIRD_PARTY_NOTICES.md").read_bytes()
    ok &= report("the committed notices are untouched by the failed generations", saved == text.encode())
    return ok


def std_archive_tests(base):
    """std_crate_files: the .crate with the standard library lock's checksum,
    from cargo's cache, the foamy-native cache or crates.io (then cached);
    a mismatching archive is refused wherever it comes from; offline without
    a cached copy is an error. std_lock: rust-src's lock must agree with the
    embedded table; no lock for a channel is an error. No cargo or network."""
    native = foamykit.native
    ok = True
    home = base / "std-home"
    (home / "registry/cache").mkdir(parents=True)
    cache = base / "std-cache"
    good = {"Cargo.toml": b'[package]\nname = "fake-addr2line"\nversion = "0.27.1"\nlicense = "Apache-2.0 OR MIT"\n',
            "LICENSE-MIT": b"Copyright (c) 2016-2018 The gimli Developers\n"}
    source = base / "std-source"
    checksum = fake_crate(source, "fake-addr2line", "0.27.1", good)
    data = (source / "registry/cache/index.crates.io-0000000000000000/fake-addr2line-0.27.1.crate").read_bytes()
    downloads = []
    real = (native.cargo_home, native.download_crate)
    saved_env = dict(os.environ)
    native.cargo_home = lambda: home
    os.environ["FOAMY_NATIVE_CACHE"] = str(cache)
    os.environ.pop("CARGO_NET_OFFLINE", None)

    def attempt():
        try:
            return dict(native.license_files(native.std_crate_files("fake-addr2line", "0.27.1", checksum), {})), ""
        except native.KitError as error:
            return None, str(error)

    try:
        native.download_crate = lambda n, v: (downloads.append(v), data[:-8] + b"tampered")[1]
        files, error = attempt()
        cached = cache / "crates/fake-addr2line-0.27.1.crate"
        ok &= report("a downloaded standard library archive that doesn't match the lock is refused, and not cached",
                     files is None and "does not match the standard library's Cargo.lock checksum" in error
                     and not cached.exists() and downloads == ["0.27.1"], error)
        native.download_crate = lambda n, v: (downloads.append(v), data)[1]
        files, error = attempt()
        ok &= report("a matching download is used and cached", files == {"LICENSE-MIT": "Copyright (c) 2016-2018 The gimli Developers"}
                     and cached.read_bytes() == data and len(downloads) == 2, error)
        files, error = attempt()
        ok &= report("the cached archive is reused (no second download)", files is not None and len(downloads) == 2, error)
        cached.write_bytes(data[:-8] + b"tampered")
        files, error = attempt()
        ok &= report("a tampered cached archive is refused", files is None and "does not match" in error and len(downloads) == 2, error)
        cached.unlink()
        os.environ["CARGO_NET_OFFLINE"] = "true"
        files, error = attempt()
        ok &= report("offline without a cached archive fails (no download)", files is None and "CARGO_NET_OFFLINE" in error
                     and len(downloads) == 2, error)
        locked = native.std_lock(base / "no-sysroot", "1.99.1")
        ok &= report("the embedded standard library lock for 1.99.1 pins addr2line and miniz_oxide",
                     locked.get("addr2line") == {"0.27.1": "e567177890eb1617b1f774005b66b26b2377afd138a2ca37aae7d8f0c81429d4"}
                     and "0.9.1" in locked.get("miniz_oxide", {}), f"{sorted(locked)}")
        sysroot = base / "fake-sysroot"
        lock = sysroot / "lib/rustlib/src/rust/library/Cargo.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text('version = 4\n[[package]]\nname = "addr2line"\nversion = "0.27.1"\n'
                        'source = "registry+https://github.com/rust-lang/crates.io-index"\nchecksum = "' + "0" * 64 + '"\n')
        errors = []
        for channel in ("1.99.1", "9.9.9"):
            try:
                native.std_lock(sysroot if channel == "1.99.1" else base / "no-sysroot", channel)
                errors.append("")
            except native.KitError as failure:
                errors.append(str(failure))
        ok &= report("rust-src's library/Cargo.lock must agree with the embedded table; no lock for a channel is an error",
                     "disagrees with native.py's STD_LOCKS" in errors[0] and "install rust-src" in errors[1], f"{errors}")
    finally:
        native.cargo_home, native.download_crate = real
        os.environ.clear()
        os.environ.update(saved_env)
    return ok


def crate_archive_tests(base):
    """crate_files reads only the checksum-verified .crate: a missing one is
    fetched once and must then exist; cargo's unpacked copy (here with a
    tampered LICENSE) is never used; a license-file outside the archive is
    an error. No cargo needed."""
    native = foamykit.native
    ok = True
    home = base / "archive-home"
    good = {"Cargo.toml": b'[package]\nname = "fake-fetched"\nversion = "0.1.0"\nlicense = "ISC"\n',
            "LICENSE": b"Genuine ISC text. Copyright 2015 Brian Smith.\n"}
    checksum = fake_crate(home, "fake-fetched", "0.1.0", good)
    archive = home / "registry/cache/index.crates.io-0000000000000000/fake-fetched-0.1.0.crate"
    data = archive.read_bytes()
    archive.unlink()
    unpacked = home / "registry/src/index.crates.io-0000000000000000/fake-fetched-0.1.0"
    unpacked.mkdir(parents=True)
    (unpacked / ".cargo-ok").write_text('{"v":1}')
    (unpacked / "Cargo.toml").write_bytes(good["Cargo.toml"])
    (unpacked / "LICENSE").write_text("Tampered text.\n")
    real_home = native.cargo_home
    native.cargo_home = lambda: home
    calls = []

    def attempt(fetch):
        try:
            return native.crate_files("fake-fetched", "0.1.0", checksum, fetch), ""
        except native.KitError as error:
            return None, str(error)

    try:
        files, error = attempt(None)
        ok &= report("a missing .crate is refused even when cargo's unpacked copy exists (never unverified bytes)",
                     files is None and "no .crate archive" in error, error)
        files, error = attempt(lambda: calls.append(1))
        ok &= report("a missing .crate is fetched once, and refused when the fetch doesn't bring it",
                     files is None and calls == [1] and "no .crate archive" in error, error)
        files, error = attempt(lambda: (calls.append(2), archive.write_bytes(data)))
        texts = dict(native.license_files(files or [], {}))
        ok &= report("after the fetch the archive's own text is used, not the tampered unpacked one",
                     calls == [1, 2] and texts.get("LICENSE") == "Genuine ISC text. Copyright 2015 Brian Smith.", f"{texts} {error}")
        archive.write_bytes(data[:-10] + b"x" * 10)
        files, error = attempt(None)
        ok &= report("an archive that doesn't match its checksum is refused", files is None and "does not match" in error, error)
        missing = fake_crate(home, "fake-missing-file", "0.1.0", {
            "Cargo.toml": b'[package]\nname = "fake-missing-file"\nversion = "0.1.0"\nlicense-file = "legal.txt"\n'})
        try:
            native.crate_files("fake-missing-file", "0.1.0", missing)
            error = ""
        except native.KitError as failure:
            error = str(failure)
        ok &= report("a license-file the archive doesn't contain is an error", "is not in the crate archive" in error, error)
    finally:
        native.cargo_home = real_home
    return ok


def last(out):
    lines = out.strip().splitlines()
    return lines[-1] if lines else ""


def harness_validator():
    return shutil.which("omarchy-plugin-validate") or "/usr/share/omarchy/bin/omarchy-plugin-validate"


def racing_edit_test(plugin, base, env):
    """A source edit while cargo runs must not be pinned to binaries built
    from the old source: build and verify refuse, and nothing is installed."""
    import argparse
    racing = base / "racing" / plugin.name
    shutil.copytree(plugin, racing)
    pin = (racing / "native/native.pin").read_bytes()
    binaries = {p: p.read_bytes() for p in (racing / "bin").rglob("*") if p.is_file()}
    real = foamykit.native.build_native

    def build_then_edit(plugin_dir, crate, binary, channel, target_dir):
        with open(plugin_dir / crate / "src/main.rs", "a") as stream:
            stream.write("// edited while cargo ran\n")
        return {arch: b"stale " + arch.encode() for arch in ("x86_64", "aarch64")}

    saved = dict(os.environ)
    os.environ.update(env or {})
    foamykit.native.build_native = build_then_edit
    try:
        codes = [foamykit.native.cmd_native(argparse.Namespace(plugin=str(racing), crate=None, bin=None, test=False,
                                                               verify=verify, out=None))
                 for verify in (False, True)]
    finally:
        foamykit.native.build_native = real
        os.environ.clear()
        os.environ.update(saved)
    unchanged = (racing / "native/native.pin").read_bytes() == pin and all(p.read_bytes() == data for p, data in binaries.items())
    shutil.rmtree(racing.parent)
    return report("build and --verify refuse when the sources change during the build (nothing installed)",
                  codes == [1, 1] and unchanged, f"{codes} unchanged={unchanged}")


def two_helpers_test(base, env):
    """Two pinned crates sharing a dependency that gets updated: both are
    stale, and rebuilding them one after the other works in either order
    (the other crate's old binary still names the old version, which must
    not block the notices). A current build's paths are still checked.
    Cargo and the builds are stubbed: the graph is `shared` 1.0.0, then 2.0.0."""
    import argparse
    native = foamykit.native
    ok = True
    home = base / "two-helpers-home"
    sums = {v: fake_crate(home, "shared", v, {"Cargo.toml": f'[package]\nname = "shared"\nversion = "{v}"\nlicense = "MIT"\n'.encode(),
                                               "LICENSE": f"shared {v}: Copyright 2024 Shared Authors\n".encode()})
            for v in ("1.0.0", "2.0.0")}
    state = {"graph": "1.0.0", "built": "1.0.0"}

    def linked(plugin_dir, crate, triple, cargo_env_):
        return {("shared", state["graph"]): None}

    def lock(plugin_dir):
        v = state["graph"]
        return {("shared", v): {"name": "shared", "version": v, "checksum": sums[v],
                                "source": "registry+https://github.com/rust-lang/crates.io-index"}}

    def build(plugin_dir, crate, binary, channel, target_dir):
        path = f"/cargo/registry/src/index.crates.io-0000000000000000/shared-{state['built']}/src/lib.rs"
        return {arch: f"\x7fELF {binary} {arch} \0{path}\0".encode() for arch in foamykit.ARCHES}

    def run(plugin_dir, crate, binary):
        return native.cmd_native(argparse.Namespace(plugin=str(plugin_dir), crate=crate, bin=binary, test=False,
                                                    verify=False, out=None, notices=False))

    crates = {"native": BINARY, "second": "foamy-native-demo-second"}
    real = (native.linked_packages, native.lock_packages, native.cargo_home, native.build_native)
    saved = dict(os.environ)
    os.environ.update(env or {})
    native.linked_packages, native.lock_packages, native.cargo_home, native.build_native = linked, lock, lambda: home, build
    try:
        for order in (["native", "second"], ["second", "native"]):
            work = fresh(base, "two-helpers-" + order[0])
            shutil.copytree(work / "native", work / "second")
            manifest = work / "second/Cargo.toml"
            manifest.write_text(manifest.read_text().replace(f'name = "{BINARY}"', 'name = "foamy-native-demo-second"'))
            workspace = work / "Cargo.toml"
            workspace.write_text(workspace.read_text().replace('members = ["native"]', 'members = ["native", "second"]'))
            sh(SYNC, work, "--components", "FoamyNative")
            state.update(graph="1.0.0", built="1.0.0")
            first = [run(work, crate, binary) for crate, binary in crates.items()]
            state.update(graph="2.0.0", built="2.0.0")
            with open(work / "Cargo.lock", "a") as stream:
                stream.write("\n# shared 2.0.0\n")
            stale = all(native.native_source_hash(work, c) != foamykit.read_pin(work / c / "native.pin")["source"] for c in crates)
            codes = [run(work, crate, crates[crate]) for crate in order]
            notices = (work / "THIRD_PARTY_NOTICES.md").read_text()
            fresh_pins = all(native.native_source_hash(work, c) == foamykit.read_pin(work / c / "native.pin")["source"] for c in crates)
            ok &= report(f"two helpers sharing an updated dependency rebuild one after the other ({' then '.join(order)})",
                         first == [0, 0] and stale and codes == [0, 0] and fresh_pins and "| shared | 2.0.0 |" in notices
                         and "| shared | 1.0.0 |" not in notices and not native.notices_problems(work, native.native_pins(work)),
                         f"initial {first}, stale {stale}, rebuilds {codes}")
            state.update(built="1.0.0")
            code = run(work, order[0], crates[order[0]])
            ok &= report(f"a current build that embeds a crate the graph doesn't list is still refused ({order[0]})",
                         code == 1 and "| shared | 2.0.0 |" in (work / "THIRD_PARTY_NOTICES.md").read_text(), f"code {code}")
            shutil.rmtree(work)
    finally:
        native.linked_packages, native.lock_packages, native.cargo_home, native.build_native = real
        os.environ.clear()
        os.environ.update(saved)
    return ok


def symlinked_bin_test(plugin, base, env):
    """A symlinked bin/ or bin/<arch> (contributor content) must not lead the
    build's writes outside the plugin."""
    import argparse
    ok = True
    for layout in ("bin", "bin/x86_64"):
        work = base / "symlinked" / plugin.name
        shutil.copytree(plugin, work)
        outside = base / "symlinked" / "outside"
        outside.mkdir()
        victim = outside / BINARY
        victim.write_bytes(b"keep me")
        if layout == "bin":
            shutil.rmtree(work / "bin")
            for arch in ("x86_64", "aarch64"):
                (outside / arch).mkdir()
                (outside / arch / BINARY).write_bytes(b"keep me")
            (work / "bin").symlink_to(outside)
        else:
            shutil.rmtree(work / "bin/x86_64")
            (work / "bin/x86_64").symlink_to(outside)
        real = foamykit.native.build_native
        foamykit.native.build_native = lambda *a: {arch: b"new " + arch.encode() for arch in ("x86_64", "aarch64")}
        saved = dict(os.environ)
        os.environ.update(env or {})
        try:
            code = foamykit.native.cmd_native(argparse.Namespace(plugin=str(work), crate=None, bin=None, test=False,
                                                                 verify=False, out=None))
        finally:
            foamykit.native.build_native = real
            os.environ.clear()
            os.environ.update(saved)
        written = sorted(p.relative_to(outside).as_posix() for p in outside.rglob("*")
                         if p.is_file() and p.read_bytes() != b"keep me")
        ok &= report(f"build-native.sh refuses a symlinked {layout} (nothing written outside the plugin)",
                     code == 1 and not written, f"code={code} written={written}")
        shutil.rmtree(base / "symlinked")
    return ok


def main():
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-native-"))
    ok = sync_tests(base)
    ok &= crate_archive_tests(base)
    ok &= std_archive_tests(base)
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
