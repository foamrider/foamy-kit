#!/usr/bin/env python3
"""sync.sh / check.sh / design lint, on throwaway plugin copies in /tmp."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIXTURES, KIT_ROOT, PLUGINS, foamykit, report  # noqa: E402

SYNC = str(KIT_ROOT / "sync.sh")
CHECK = str(KIT_ROOT / "check.sh")
VALIDATE = shutil.which("omarchy-plugin-validate") or "/usr/share/omarchy/bin/omarchy-plugin-validate"


def sh(*args, cwd=None):
    result = subprocess.run(list(args), capture_output=True, text=True, timeout=120, cwd=cwd)
    return result.returncode, result.stdout + result.stderr


def snapshot(plugin):
    return {str(p.relative_to(plugin)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(plugin.rglob("*")) if p.is_file() and ".git" not in p.parts}


def main():
    ok = True
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-sync-"))
    sources = [PLUGINS / "foamy-bolt", PLUGINS / "foamy-tray"]
    sources = [s for s in sources if (s / "manifest.json").is_file()] or [FIXTURES / "demo-plugin"]
    plugins = []
    for source in sources:
        target = base / source.name
        shutil.copytree(source, target, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        plugins.append(target)
    a = plugins[0]
    b = plugins[-1] if len(plugins) > 1 else None

    # 1. First sync: requested components plus their dependencies.
    code, out = sh(SYNC, str(a), "--components", "FoamyPopup,SafeTextField")
    files = sorted(p.name for p in (a / "kit").iterdir())
    ok &= report("sync adds the components and their dependencies", code == 0 and files == sorted([
        "FoamyI18n.qml", "FoamyPalette.qml", "FoamyPopup.qml", "FoamyStyle.qml", "SafeTextField.qml", "clipboard.sh", "qmldir"]), f"{code} {files}")
    qmldir = (a / "kit/qmldir").read_text()
    ok &= report("generated qmldir registers singletons", "singleton FoamyStyle 1.0 FoamyStyle.qml" in qmldir and "\nFoamyPopup 1.0 FoamyPopup.qml" in qmldir)
    first = (a / "kit/FoamyStyle.qml").read_text().splitlines()
    ok &= report("stamp sits after `pragma Singleton`", first[0] == "pragma Singleton" and first[1].startswith("// foamy-kit ") and first[1].endswith(foamykit.STAMP_TAIL))
    shell_lines = (a / "kit/clipboard.sh").read_text().splitlines()
    ok &= report("stamp sits after the shebang in scripts", shell_lines[0].startswith("#!") and shell_lines[1].startswith("# foamy-kit "))
    ok &= report("scripts stay executable", os.access(a / "kit/clipboard.sh", os.X_OK) and os.access(a / "tests/kit-check.sh", os.X_OK))
    ok &= report("kit files are regular files (no symlinks)", not any(p.is_symlink() for p in a.rglob("*")))
    code, out = sh(VALIDATE, str(a))
    ok &= report("omarchy-plugin-validate accepts the synced plugin", code == 0, out.strip())
    code, out = sh("env", "-i", "PATH=/usr/bin:/bin", "bash", str(a / "tests/kit-check.sh"))
    ok &= report("generated tests/kit-check.sh passes (clean environment)", code == 0 and "OK" in out, out.strip())

    # 2. Idempotent: nothing rewritten on a second run.
    before = snapshot(a)
    code, out = sh(SYNC, str(a))
    ok &= report("second sync is a no-op and keeps the component set", code == 0 and "up to date" in out and snapshot(a) == before, out.strip())

    # 3. Local edits are detected and never overwritten.
    edited = a / "kit/FoamyPopup.qml"
    edited.write_text(edited.read_text().replace("property bool wide: false", "property bool wide: true"))
    code, out = sh("bash", str(a / "tests/kit-check.sh"))
    ok &= report("kit-check fails on a locally edited copy", code != 0 and "edited locally" in out, out.strip().splitlines()[0] if out.strip() else "")
    code, out = sh(SYNC, str(a))
    ok &= report("sync refuses to overwrite a local edit", code != 0 and "edited locally" in out and "wide: true" in edited.read_text())
    code, out = sh(CHECK, "--no-lint", str(a))
    ok &= report("check.sh reports the edit", code != 0 and "edited locally" in out)
    code, out = sh(SYNC, str(a), "--force")
    ok &= report("--force restores the kit copy", code == 0 and "wide: false" in edited.read_text())

    # 4. Unknown files and symlinks in kit/ are refused.
    stray = a / "kit/Mine.qml"
    stray.write_text("import QtQuick\nItem {}\n")
    code, out = sh(SYNC, str(a))
    code2, out2 = sh("bash", str(a / "tests/kit-check.sh"))
    ok &= report("a plugin file inside kit/ is refused", code != 0 and "not a foamy-kit file" in out and code2 != 0 and "not part of foamy-kit" in out2)
    stray.unlink()
    link = a / "kit/Link.qml"
    link.symlink_to(a / "kit/FoamyStyle.qml")
    code, out = sh(SYNC, str(a))
    ok &= report("a symlink inside kit/ is refused", code != 0 and "symlink" in out)
    link.unlink()

    # 5. Changing the component set removes files no longer needed.
    code, out = sh(SYNC, str(a), "--components", "FoamyI18n")
    files = sorted(p.name for p in (a / "kit").iterdir())
    ok &= report("narrowing the components removes unneeded files", code == 0 and files == ["FoamyI18n.qml", "qmldir"], f"{files}")
    code, out = sh(SYNC, str(a), "--add", "FoamyPeerIpc")
    files = sorted(p.name for p in (a / "kit").iterdir())
    lock = foamykit.read_lock(a)
    ok &= report("--add extends the plugin's component set", code == 0 and "FoamyPeerIpc.qml" in files and "FoamyI18n.qml" in files
                 and lock["components"] == ["FoamyI18n", "FoamyIpc", "FoamyPeerIpc"], f"{lock['components']}")
    code, out = sh(SYNC, str(a), "--components", "FoamyPopup,Nope")
    ok &= report("unknown components are rejected", code != 0 and "unknown component" in out)

    # 6. Version drift across plugins fails check.sh.
    if b is not None:
        old_kit = base / "old-kit"
        shutil.copytree(KIT_ROOT, old_kit, ignore=shutil.ignore_patterns(".git", "tests", "preview"))
        (old_kit / "VERSION").write_text("0.0.9\n")
        code, out = sh(str(old_kit / "sync.sh"), str(b), "--components", "FoamyPopupCard")
        sh(SYNC, str(a), "--components", "FoamyPopup")
        code, out = sh(CHECK, "--no-lint", str(a), str(b))
        ok &= report("check.sh fails when plugins are on different kit versions", code != 0 and "kit versions differ" in out, out.strip().splitlines()[-1])
        sh(SYNC, str(b))
        code, out = sh(CHECK, "--no-lint", str(a), str(b))
        ok &= report("check.sh passes once every plugin is on one version", code == 0, out.strip())

    # 7. Design lint.
    code, out = sh("python3", "-I", str(KIT_ROOT / "tools/foamykit.py"), "lint", str(KIT_ROOT / "tests/lint-cases/Bad.qml"))
    rules = {line.split(": ")[1] for line in out.splitlines() if ": " in line}
    expected = {"unqualified-color", "radius-x2", "hex-colour", "sans-serif", "bare-duration", "unguarded-loop", "raw-ipc", "opt-out-reason",
                "empty-glyph"}
    ok &= report("lint catches every rule", code != 0 and expected <= rules, f"missing {sorted(expected - rules)}")
    code, out = sh("python3", "-I", str(KIT_ROOT / "tools/foamykit.py"), "lint", str(KIT_ROOT / "tests/lint-cases/Good.qml"))
    ok &= report("lint allows qualified colours, guarded loops and reasoned opt-outs", code == 0, out.strip())
    warn = str(KIT_ROOT / "tests/lint-cases/Warn.qml")
    code, out = sh("python3", "-I", str(KIT_ROOT / "tools/foamykit.py"), "lint", warn)
    code2, out2 = sh("python3", "-I", str(KIT_ROOT / "tools/foamykit.py"), "lint", "--strict", warn)
    ok &= report("literal private-use glyphs warn (and fail with --strict)", code == 0 and out.count("warning: pua-literal") == 2
                 and code2 != 0, out.strip())
    kit_sources = [str(p) for p in sorted((KIT_ROOT / "kit").glob("*")) if p.suffix in (".qml", ".js")]
    code, out = sh("python3", "-I", str(KIT_ROOT / "tools/foamykit.py"), "lint", *kit_sources)
    ok &= report("the kit itself passes the lint", code == 0, out.strip())
    demo = base / "demo"
    shutil.copytree(FIXTURES / "demo-plugin", demo)
    sh(SYNC, str(demo))
    code, out = sh(CHECK, str(demo))
    ok &= report("check.sh passes on the demo plugin (kit + lint)", code == 0, out.strip())
    code, out = sh("node", "-e", 'const P = require(process.argv[1]).load("FoamyPrefs"); '
                   'process.stdout.write(String(P.valid([{key: "x", type: "array"}], "x", [1])))', str(demo / "kit/node-loader.cjs"))
    ok &= report("a plugin's stamped kit/node-loader.cjs loads FoamyPrefs in node", code == 0 and out.strip() == "true", out.strip())
    unmigrated = base / "unmigrated"
    shutil.copytree(FIXTURES / "demo-plugin", unmigrated)
    shutil.copyfile(KIT_ROOT / "tests/fixtures/old-fork/BoltPopup.qml", unmigrated / "BoltPopup.qml")
    code, out = sh(CHECK, "--lint-only", str(unmigrated))
    ok &= report("check.sh --lint-only flags pre-kit code (the old popup fork)", code != 0 and "unqualified-color" in out)

    if ok:
        shutil.rmtree(base, ignore_errors=True)
    else:
        print(f"    kept {base}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
