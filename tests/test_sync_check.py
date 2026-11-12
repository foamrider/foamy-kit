#!/usr/bin/env python3
"""sync.sh / check.sh / design lint, on throwaway plugin copies in /tmp."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FIXTURES, KIT_ROOT, PLUGINS, copy_kit, foamykit, report  # noqa: E402

SYNC = str(KIT_ROOT / "sync.sh")
CHECK = str(KIT_ROOT / "check.sh")
VALIDATE = shutil.which("omarchy-plugin-validate") or "/usr/share/omarchy/bin/omarchy-plugin-validate"


def sh(*args, cwd=None):
    result = subprocess.run(list(args), capture_output=True, text=True, timeout=120, cwd=cwd)
    return result.returncode, result.stdout + result.stderr


def snapshot(plugin):
    return {
        str(p.relative_to(plugin)): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in sorted(plugin.rglob("*"))
        if p.is_file() and ".git" not in p.parts
    }


def stamped_intact(path):
    info = foamykit.read_stamp(path.read_bytes())
    return info is not None and foamykit.sha256(info[2]) == info[1]


def tooling_tests(a, base):
    """The tooling (tests/validate.sh and its configuration) in every plugin."""
    ok = True
    lock = foamykit.read_lock(a)
    tooling = foamykit.TOOLING_FILES
    ok &= report(
        "sync writes every tooling file, stamped and locked, even with a component subset",
        all(stamped_intact(a / rel) and rel in lock["files"] for rel in tooling),
        f"{sorted(set(tooling) - set(lock['files']))}",
    )
    ok &= report(
        "tooling bodies are the kit's own files",
        all(
            foamykit.read_stamp((a / rel).read_bytes())[2] == (KIT_ROOT / src).read_bytes()
            for rel, src in tooling.items()
        ),
    )
    ok &= report(
        "tests/validate.sh is executable; the configs are not",
        os.access(a / "tests/validate.sh", os.X_OK) and not os.access(a / "mise.toml", os.X_OK),
    )
    first = (a / "kit/tooling/validate.py").read_text().splitlines()
    ok &= report(
        "validate.py keeps its shebang, stamp on line 2",
        first[0].startswith("#!") and first[1].startswith("# foamy-kit "),
    )
    ok &= report(
        "lock_path_ok accepts the tooling paths (sync and the bundled build tool)",
        all(foamykit.lock_path_ok(rel) and foamykit.native.lock_path_ok(rel) for rel in tooling),
    )
    code, out = sh("bash", str(a / "tests/validate.sh"), "--list")
    ok &= report(
        "the plugin's tests/validate.sh runs from its stamped copy",
        code == 0 and "qmllint" in out and "suite" in out,
        out.strip()[-200:],
    )
    code, out = sh("bash", str(a / "tests/validate.sh"), "--only", "kit-check")
    ok &= report(
        "tests/validate.sh --only kit-check passes on the synced plugin",
        code == 0 and "PASS  kit-check" in out,
        out.strip()[-300:],
    )
    ruff = a / "ruff.toml"
    data = ruff.read_bytes()
    ruff.write_bytes(data.replace(b"max-complexity = 15", b"max-complexity = 99"))
    code, out = sh("bash", str(a / "tests/kit-check.sh"))
    code2, out2 = sh(SYNC, str(a))
    ok &= report(
        "an edited shared config fails kit-check and blocks sync",
        code != 0 and "ruff.toml was edited locally" in out and code2 != 0 and "ruff.toml was edited locally" in out2,
        (out + out2).strip()[-300:],
    )
    ruff.write_bytes(data)
    own = base / "own-tooling"
    shutil.copytree(FIXTURES / "demo-plugin", own)
    (own / "mise.toml").write_text('[tools]\nshellcheck = "0.9.0"\n')
    before = snapshot(own)
    code, out = sh(SYNC, str(own))
    ok &= report(
        "a plugin's own mise.toml is preserved before any writes",
        code != 0 and "mise.toml is not a foamy-kit file" in out and snapshot(own) == before,
        out.strip()[-200:],
    )
    return ok


def git(repo, *args):
    # Throwaway repos: commits need no signature or user identity.
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "user.name=test", "-c", "user.email=test@invalid", "-C", str(repo)]
        + list(args),
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    ).stdout.strip()


def lock_source(plugin):
    lines = (plugin / foamykit.LOCK_NAME).read_text().splitlines()
    return next((line.split()[1] for line in lines if line.startswith("source ")), None)


def lock_source_tests(base):
    """The lock's source line names the full kit commit, and sync refreshes it
    when every file is already current (checks.yml checks the kit out there)."""
    ok = True
    kit = copy_kit(base / "source-kit")
    git(kit, "init", "-q")
    git(kit, "add", "-A")
    git(kit, "commit", "-q", "-m", "kit")
    first = git(kit, "rev-parse", "HEAD")
    plugin = base / "source-plugin"
    shutil.copytree(FIXTURES / "demo-plugin", plugin)
    code, out = sh(str(kit / "sync.sh"), str(plugin))
    ok &= report(
        "the lock's source is the full commit id sync copied from",
        code == 0 and lock_source(plugin) == first and len(first) == 40,
        f"{lock_source(plugin)} vs {first}",
    )
    # A kit commit that changes nothing sync copies (README.md is not synced).
    with open(kit / "README.md", "a") as readme:
        readme.write("\nA later kit commit.\n")
    git(kit, "commit", "-q", "-am", "docs")
    second = git(kit, "rev-parse", "HEAD")
    before = snapshot(plugin)
    code, out = sh(str(kit / "sync.sh"), str(plugin))
    after = snapshot(plugin)
    changed = sorted(
        rel for rel in set(before) | set(after) if before.get(rel, (None,))[0] != after.get(rel, (None,))[0]
    )
    ok &= report(
        "sync refreshes the source line when every file is up to date",
        code == 0 and lock_source(plugin) == second and changed == [foamykit.LOCK_NAME] and "foamy-kit.lock" in out,
        f"{changed} {out.strip()}",
    )
    before = snapshot(plugin)
    code, out = sh(str(kit / "sync.sh"), str(plugin))
    ok &= report(
        "a second sync from the same commit is a no-op",
        code == 0 and "up to date" in out and snapshot(plugin) == before,
        out.strip(),
    )
    (kit / "kit/FoamyStyle.qml").write_text((kit / "kit/FoamyStyle.qml").read_text() + "// uncommitted\n")
    sh(str(kit / "sync.sh"), str(plugin))
    ok &= report(
        "a sync from uncommitted kit changes marks the source +dirty",
        lock_source(plugin) == second + "+dirty",
        str(lock_source(plugin)),
    )
    git(kit, "checkout", "-q", "--", "kit/FoamyStyle.qml")
    sh(str(kit / "sync.sh"), str(plugin))
    ok &= workflow_kit_tests(base, kit, plugin, second)
    return ok


def workflow_kit_tests(base, kit, plugin, commit):
    """checks.yml's kit checkout step, run as the runner would (bash, a clean
    environment), against a local remote in place of github.com."""
    ok = True
    script = workflow_step_script(KIT_ROOT / ".github/workflows/checks.yml", "Check out foamy-kit")
    remote = base / "remote-kit.git"
    git(base, "clone", "-q", "--bare", str(kit), str(remote))

    def step(cwd, case):
        runner = base / f"runner-{case}"
        runner.mkdir()
        github_env = runner / "env"
        github_env.write_text("")
        env = {
            "PATH": os.environ["PATH"],
            "HOME": str(runner),
            "RUNNER_TEMP": str(runner),
            "GITHUB_ENV": str(github_env),
            "FOAMY_KIT_URL": f"file://{remote}",
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode, result.stdout + result.stderr, github_env.read_text(), runner / "foamy-kit"

    code, out, github_env, checkout = step(plugin, "ok")
    head = git(checkout, "rev-parse", "HEAD") if (checkout / ".git").is_dir() else ""
    ok &= report(
        "checks.yml checks out the lock's kit commit and exports FOAMY_KIT",
        code == 0 and github_env == f"FOAMY_KIT={checkout}\n" and head == commit and (checkout / "check.sh").is_file(),
        out.strip()[-300:],
    )
    lock = plugin / foamykit.LOCK_NAME
    original = lock.read_text()
    cases = [
        ("unpushed", commit, "f" * 40, "could not fetch foamy-kit commit " + "f" * 40),
        ("dirty", commit, commit + "+dirty", "not a full foamy-kit commit id"),
        ("short", commit, commit[:12], "not a full foamy-kit commit id"),
    ]
    for case, old, new, message in cases:
        lock.write_text(original.replace(f"source {old}\n", f"source {new}\n"))
        code, out, github_env, _ = step(plugin, case)
        ok &= report(
            f"checks.yml fails a {case} source and exports nothing",
            code != 0 and message in out and github_env == "",
            out.strip()[-300:],
        )
    lock.write_text(original)
    code, out, github_env, checkout = step(kit, "kit")
    ok &= report(
        "in foamy-kit itself the step fetches nothing",
        code == 0 and github_env == "" and not checkout.exists(),
        out.strip()[-300:],
    )
    return ok


def workflow_step_script(workflow, name):
    """The `run: |` block of the step whose name starts with `name` (stdlib
    only: no YAML parser), dedented."""
    lines = workflow.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().startswith(f"- name: {name}"))
    run = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "run: |")
    indent = len(lines[run]) - len(lines[run].lstrip()) + 2
    body = []
    for line in lines[run + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) < indent:
            break
        body.append(line[indent:])
    return "\n".join(body) + "\n"


def main():
    ok = True
    base = Path(tempfile.mkdtemp(prefix="foamy-kit-sync-"))
    sources = [PLUGINS / "foamy-bolt", PLUGINS / "foamy-tray"]
    sources = [s for s in sources if (s / "manifest.json").is_file()] or [FIXTURES / "demo-plugin"]
    plugins = []
    for source in sources:
        target = base / source.name
        # Start from a plugin without the shared guide, whatever its checkout holds.
        shutil.copytree(source, target, ignore=shutil.ignore_patterns(".git", "__pycache__", "REVIEW.md"))
        plugins.append(target)
    a = plugins[0]
    b = plugins[-1] if len(plugins) > 1 else None

    # 1. First sync: requested components plus their dependencies.
    code, out = sh(SYNC, str(a), "--components", "FoamyPopup,SafeTextField")
    files = sorted(p.name for p in (a / "kit").iterdir())
    ok &= report(
        "sync adds the components and their dependencies",
        code == 0
        and files
        == sorted(
            [
                "FoamyI18n.qml",
                "FoamyI18nText.js",
                "FoamyPalette.qml",
                "FoamyPopup.qml",
                "FoamyStyle.qml",
                "SafeTextField.qml",
                "clipboard.sh",
                "node-loader.cjs",
                "qmldir",
                "tooling",
            ]
        ),
        f"{code} {files}",
    )
    qmldir = (a / "kit/qmldir").read_text()
    ok &= report(
        "generated qmldir registers singletons",
        "singleton FoamyStyle 1.0 FoamyStyle.qml" in qmldir and "\nFoamyPopup 1.0 FoamyPopup.qml" in qmldir,
    )
    first = (a / "kit/FoamyStyle.qml").read_text().splitlines()
    ok &= report(
        "stamp sits after `pragma Singleton`",
        first[0] == "pragma Singleton"
        and first[1].startswith("// foamy-kit ")
        and first[1].endswith(foamykit.STAMP_TAIL),
    )
    shell_lines = (a / "kit/clipboard.sh").read_text().splitlines()
    ok &= report(
        "stamp sits after the shebang in scripts",
        shell_lines[0].startswith("#!") and shell_lines[1].startswith("# foamy-kit "),
    )
    ok &= report(
        "scripts stay executable",
        os.access(a / "kit/clipboard.sh", os.X_OK) and os.access(a / "tests/kit-check.sh", os.X_OK),
    )
    ok &= report("kit files are regular files (no symlinks)", not any(p.is_symlink() for p in a.rglob("*")))
    if os.access(VALIDATE, os.X_OK):
        code, out = sh(VALIDATE, str(a))
        ok &= report("omarchy-plugin-validate accepts the synced plugin", code == 0, out.strip())
    else:
        print("SKIP omarchy-plugin-validate: not installed (an Omarchy host tool)")
    code, out = sh("env", "-i", "PATH=/usr/bin:/bin", "bash", str(a / "tests/kit-check.sh"))
    ok &= report("generated tests/kit-check.sh passes (clean environment)", code == 0 and "OK" in out, out.strip())

    ok &= tooling_tests(a, base)

    # 2. Idempotent: nothing rewritten on a second run.
    before = snapshot(a)
    code, out = sh(SYNC, str(a))
    ok &= report(
        "second sync is a no-op and keeps the component set",
        code == 0 and "up to date" in out and snapshot(a) == before,
        out.strip(),
    )

    # The shared guide is always present, including with a component subset.
    review = a / "REVIEW.md"
    guide = (KIT_ROOT / "REVIEW.md").read_bytes()
    ok &= report(
        "review guide is copied verbatim and locked",
        review.read_bytes() == guide and foamykit.read_lock(a)["files"]["REVIEW.md"] == foamykit.sha256(guide),
    )
    review.write_bytes(guide + b"\nLocal review rule.\n")
    before = snapshot(a)
    code, out = sh(SYNC, str(a))
    code2, out2 = sh("bash", str(a / "tests/kit-check.sh"))
    code3, out3 = sh(CHECK, "--no-lint", str(a))
    ok &= report(
        "edited review guide blocks sync and both integrity checks",
        code != 0
        and snapshot(a) == before
        and code2 != 0
        and "REVIEW.md was edited" in out2
        and code3 != 0
        and "REVIEW.md was edited" in out3,
    )
    review.unlink()
    code, out = sh("bash", str(a / "tests/kit-check.sh"))
    code2, out2 = sh(CHECK, "--no-lint", str(a))
    ok &= report(
        "missing review guide fails both integrity checks",
        code != 0 and "REVIEW.md" in out and code2 != 0 and "REVIEW.md" in out2,
    )
    outside_review = base / "outside-review.md"
    outside_review.write_bytes(guide)
    review.symlink_to(outside_review)
    code, out = sh(SYNC, str(a), "--force")
    ok &= report(
        "review symlink is refused even with force",
        code != 0 and "REVIEW.md is a symlink" in out and review.is_symlink() and outside_review.read_bytes() == guide,
    )
    review.unlink()
    code, out = sh(SYNC, str(a))
    ok &= report("sync restores a missing guide", code == 0 and review.read_bytes() == guide)

    fresh = base / "review-conflict"
    shutil.copytree(FIXTURES / "demo-plugin", fresh)
    (fresh / "REVIEW.md").write_text("Plugin-owned review instructions.\n")
    before = snapshot(fresh)
    code, out = sh(SYNC, str(fresh))
    ok &= report(
        "unowned review guide is preserved before any writes",
        code != 0 and "REVIEW.md" in out and snapshot(fresh) == before,
    )
    (fresh / "REVIEW.md").write_bytes(guide)
    before = snapshot(fresh)
    code, out = sh(SYNC, str(fresh), "--dry-run")
    ok &= report("dry-run does not adopt or rewrite an identical guide", code == 0 and snapshot(fresh) == before)
    code, out = sh(SYNC, str(fresh))
    ok &= report(
        "identical unowned guide is safely adopted",
        code == 0 and foamykit.read_lock(fresh)["files"]["REVIEW.md"] == foamykit.sha256(guide),
    )

    # AGENTS.md: the plugin owns the file; sync manages one review block in it.
    block = foamykit.AGENTS_BLOCK
    kit_agents = (KIT_ROOT / "AGENTS.md").read_bytes()
    ok &= report(
        "foamy-kit's own AGENTS.md carries the current review block",
        foamykit.agents_with_review(kit_agents) == kit_agents,
    )
    agents = a / "AGENTS.md"
    ok &= report(
        "sync creates AGENTS.md with the review block when it is absent",
        agents.read_text() == "# Notes for coding agents\n\n" + block and "[REVIEW.md](REVIEW.md)" in block,
    )
    own = "# Plugin rules\n\nKeep the queue bounded.\n"
    agents.write_text(own)
    agents.chmod(0o600)
    code, out = sh(SYNC, str(a))
    ok &= report(
        "sync appends the block to an existing AGENTS.md, keeping its text and mode",
        code == 0 and agents.read_text() == own + "\n" + block and agents.stat().st_mode & 0o777 == 0o600,
        out.strip(),
    )
    before = snapshot(a)
    code, out = sh(SYNC, str(a))
    ok &= report("a current block is a no-op", code == 0 and "up to date" in out and snapshot(a) == before, out.strip())
    tail = "\n## Later rules\n\nStay plain.\n"
    agents.write_text(own + "\n" + block.replace("Follow [REVIEW.md]", "Ignore [REVIEW.md]") + tail)
    code, out = sh("bash", str(a / "tests/kit-check.sh"))
    code2, out2 = sh(CHECK, "--no-lint", str(a))
    ok &= report(
        "an edited block fails both integrity checks",
        code != 0 and "AGENTS.md lacks" in out and code2 != 0 and "AGENTS.md lacks" in out2,
        (out + out2).strip(),
    )
    code, out = sh(SYNC, str(a))
    ok &= report(
        "sync refreshes only the block, keeping text on both sides",
        code == 0 and agents.read_text() == own + "\n" + block + tail,
        out.strip(),
    )
    code, out = sh("bash", str(a / "tests/kit-check.sh"))
    ok &= report("kit-check accepts the refreshed block", code == 0, out.strip())
    for label, damaged in (
        ("a lone begin marker", own + foamykit.AGENTS_BEGIN + "\n"),
        ("a repeated block", own + block + block),
        ("an end marker before the begin", own + foamykit.AGENTS_END + "\n" + foamykit.AGENTS_BEGIN + "\n"),
        ("an edited marker", own + block.replace(" end -->", " stop -->")),
    ):
        agents.write_text(damaged)
        before = snapshot(a)
        code, out = sh(SYNC, str(a), "--force")
        code2, out2 = sh(CHECK, "--no-lint", str(a))
        ok &= report(
            f"sync refuses {label} without writing, even with --force; check.sh reports it",
            code != 0
            and "review block is damaged" in out
            and snapshot(a) == before
            and code2 != 0
            and "damaged" in out2,
            out.strip(),
        )
    agents.write_bytes(b"# Rules\n\xff\n")
    code, out = sh(SYNC, str(a))
    ok &= report(
        "sync refuses a non-UTF-8 AGENTS.md",
        code != 0 and "not UTF-8" in out and agents.read_bytes() == b"# Rules\n\xff\n",
    )
    agents.write_text("No trailing newline")
    code, out = sh(SYNC, str(a), "--dry-run")
    ok &= report(
        "dry-run reports AGENTS.md without writing it",
        code == 0 and "AGENTS.md" in out and agents.read_text() == "No trailing newline",
        out.strip(),
    )
    code, out = sh(SYNC, str(a))
    ok &= report(
        "text without a final newline is kept and separated by a blank line",
        code == 0 and agents.read_text() == "No trailing newline\n\n" + block,
    )
    agents.unlink()
    code, out = sh("bash", str(a / "tests/kit-check.sh"))
    code2, out2 = sh(CHECK, "--no-lint", str(a))
    ok &= report(
        "a missing AGENTS.md fails both integrity checks",
        code != 0 and "AGENTS.md is missing" in out and code2 != 0 and "AGENTS.md is missing" in out2,
    )
    outside_agents = base / "outside-agents.md"
    outside_agents.write_text(own)
    agents.symlink_to(outside_agents)
    code, out = sh(SYNC, str(a))
    ok &= report(
        "an AGENTS.md symlink is refused and its target untouched",
        code != 0 and "AGENTS.md is a symlink" in out and outside_agents.read_text() == own,
    )
    agents.unlink()
    code, out = sh(SYNC, str(a))
    ok &= report(
        "sync recreates a missing AGENTS.md",
        code == 0 and agents.read_text().endswith(block) and not list(a.glob(".AGENTS.md.*")),
    )

    # 3. Local edits are detected and never overwritten.
    edited = a / "kit/FoamyPopup.qml"
    edited.write_text(edited.read_text().replace("property bool wide: false", "property bool wide: true"))
    code, out = sh("bash", str(a / "tests/kit-check.sh"))
    ok &= report(
        "kit-check fails on a locally edited copy",
        code != 0 and "edited locally" in out,
        out.strip().splitlines()[0] if out.strip() else "",
    )
    code, out = sh(SYNC, str(a))
    ok &= report(
        "sync refuses to overwrite a local edit",
        code != 0 and "edited locally" in out and "wide: true" in edited.read_text(),
    )
    code, out = sh(CHECK, "--no-lint", str(a))
    ok &= report("check.sh reports the edit", code != 0 and "edited locally" in out)
    code, out = sh(SYNC, str(a), "--force")
    ok &= report("--force restores the kit copy", code == 0 and "wide: false" in edited.read_text())

    # 4. Unknown files and symlinks in kit/ are refused.
    stray = a / "kit/Mine.qml"
    stray.write_text("import QtQuick\nItem {}\n")
    code, out = sh(SYNC, str(a))
    code2, out2 = sh("bash", str(a / "tests/kit-check.sh"))
    ok &= report(
        "a plugin file inside kit/ is refused",
        code != 0 and "not a foamy-kit file" in out and code2 != 0 and "not part of foamy-kit" in out2,
    )
    stray.unlink()
    link = a / "kit/Link.qml"
    link.symlink_to(a / "kit/FoamyStyle.qml")
    code, out = sh(SYNC, str(a))
    ok &= report("a symlink inside kit/ is refused", code != 0 and "symlink" in out)
    link.unlink()

    # 5. Changing the component set removes files no longer needed.
    code, out = sh(SYNC, str(a), "--components", "FoamyI18n")
    files = sorted(p.name for p in (a / "kit").iterdir())
    ok &= report(
        "narrowing the components removes unneeded files",
        code == 0 and files == ["FoamyI18n.qml", "FoamyI18nText.js", "node-loader.cjs", "qmldir", "tooling"],
        f"{files}",
    )
    code, out = sh(SYNC, str(a), "--add", "FoamyPeerIpc")
    files = sorted(p.name for p in (a / "kit").iterdir())
    lock = foamykit.read_lock(a)
    ok &= report(
        "--add extends the plugin's component set",
        code == 0
        and "FoamyPeerIpc.qml" in files
        and "FoamyI18n.qml" in files
        and lock["components"] == ["FoamyI18n", "FoamyIpc", "FoamyPeerIpc"],
        f"{lock['components']}",
    )
    code, out = sh(SYNC, str(a), "--components", "FoamyPopup,Nope")
    ok &= report("unknown components are rejected", code != 0 and "unknown component" in out)

    # 5b. The lock is plugin content: paths outside what foamy-kit owns are refused
    # before sync reads, overwrites or deletes anything (traversal via a crafted lock).
    victim = base / "victim.txt"
    victim.write_text("keep me\n")
    lock_path = a / foamykit.LOCK_NAME
    clean_lock = lock_path.read_text()
    digest = foamykit.sha256(victim.read_bytes())
    for bad in ("../victim.txt", str(victim), "kit/../../victim.txt", "manifest.json"):
        lock_path.write_text(clean_lock + f"{digest}  {bad}\n")
        code, out = sh(SYNC, str(a))
        code_f, out_f = sh(SYNC, str(a), "--force")
        code_c, out_c = sh("bash", str(a / "tests/kit-check.sh"))
        ok &= report(
            f"a lock path {bad!r} is refused (sync, --force, kit-check)",
            code != 0
            and code_f != 0
            and "not a path foamy-kit owns" in out + out_f
            and code_c != 0
            and victim.read_text() == "keep me\n"
            and (a / "manifest.json").exists(),
            (out + out_f + out_c).strip()[-300:],
        )
    # check.sh reports a crafted lock as that plugin's problem and goes on to
    # the next plugin; --lint-only doesn't need the lock at all.
    lock_path.write_text(clean_lock + f"{digest}  ../victim.txt\n")
    others = [str(b)] if b is not None else []
    code, out = sh(CHECK, "--no-lint", str(a), *others)
    _, out_l = sh(CHECK, "--lint-only", "--quiet", str(a))
    ok &= report(
        "check.sh reports a lock path outside the plugin and checks the other plugins",
        code != 0
        and f"{a.name}: kit: " in out
        and "not a path foamy-kit owns" in out
        and "Traceback" not in out + out_l
        and all(f"{Path(o).name}: " in out for o in others)
        and "not a path foamy-kit owns" not in out_l,
        (out + out_l).strip()[-300:],
    )
    lock_path.write_text(clean_lock)
    template = (KIT_ROOT / "tools/kit-check.sh.in").read_text()
    roots = sorted({dest for spec in foamykit.load_components().values() for dest in spec.get("rootFiles", {})})
    ok &= report(
        "kit-check.sh.in allows every component root file",
        all(f"$rel != {dest}" in template for dest in roots),
        f"{roots}",
    )
    tests_dir = a / "tests"
    moved = base / "tests-elsewhere"
    shutil.move(tests_dir, moved)
    tests_dir.symlink_to(moved)
    code, out = sh(SYNC, str(a), "--force")
    ok &= report(
        "sync refuses a symlinked parent directory (tests/ -> elsewhere)",
        code != 0 and "outside the plugin" in out,
        out.strip()[-200:],
    )
    tests_dir.unlink()
    shutil.move(moved, tests_dir)
    code, out = sh(SYNC, str(a))
    ok &= report("sync works again on the restored plugin", code == 0, out.strip())

    # 6. Version drift across plugins fails check.sh.
    if b is not None:
        old_kit = base / "old-kit"
        copy_kit(old_kit)
        (old_kit / "VERSION").write_text("0.0.9\n")
        (old_kit / "REVIEW.md").write_bytes(guide + b"\nPrevious shared guide.\n")
        code, out = sh(str(old_kit / "sync.sh"), str(b), "--components", "FoamyPopupCard")
        sh(SYNC, str(a), "--components", "FoamyPopup")
        code, out = sh(CHECK, "--no-lint", str(a), str(b))
        ok &= report(
            "check.sh fails when plugins are on different kit versions",
            code != 0 and "kit versions differ" in out,
            out.strip().splitlines()[-1],
        )
        sh(SYNC, str(b))
        ok &= report("sync refreshes an unchanged older guide", (b / "REVIEW.md").read_bytes() == guide)
        code, out = sh(CHECK, "--no-lint", str(a), str(b))
        ok &= report("check.sh passes once every plugin is on one version", code == 0, out.strip())

    # 7. The lock's source line and checks.yml's kit checkout.
    ok &= lock_source_tests(base)

    # 8. Design lint.
    code, out = sh(
        "python3", "-I", str(KIT_ROOT / "tools/foamykit.py"), "lint", str(KIT_ROOT / "tests/lint-cases/Bad.qml")
    )
    rules = {line.split(": ")[1] for line in out.splitlines() if ": " in line}
    expected = {
        "unqualified-color",
        "radius-x2",
        "hex-colour",
        "sans-serif",
        "bare-duration",
        "unguarded-loop",
        "raw-ipc",
        "opt-out-reason",
        "empty-glyph",
    }
    ok &= report("lint catches every rule", code != 0 and expected <= rules, f"missing {sorted(expected - rules)}")
    code, out = sh(
        "python3", "-I", str(KIT_ROOT / "tools/foamykit.py"), "lint", str(KIT_ROOT / "tests/lint-cases/Good.qml")
    )
    ok &= report("lint allows qualified colours, guarded loops and reasoned opt-outs", code == 0, out.strip())
    warn = str(KIT_ROOT / "tests/lint-cases/Warn.qml")
    code, out = sh("python3", "-I", str(KIT_ROOT / "tools/foamykit.py"), "lint", warn)
    code2, out2 = sh("python3", "-I", str(KIT_ROOT / "tools/foamykit.py"), "lint", "--warn-pua", warn)
    ok &= report(
        "literal private-use glyphs fail by default (and only warn with --warn-pua)",
        code != 0
        and out.count(": pua-literal") == 2
        and "warning:" not in out
        and code2 == 0
        and out2.count("warning: pua-literal") == 2,
        out.strip(),
    )
    pua_plugin = base / "pua"
    shutil.copytree(FIXTURES / "demo-plugin", pua_plugin)
    sh(SYNC, str(pua_plugin))
    (pua_plugin / "Glyphs.qml").write_text('import QtQuick\nText { text: "\uf0e7" }\n')
    code, out = sh(CHECK, str(pua_plugin))
    code2, out2 = sh(CHECK, "--warn-pua", str(pua_plugin))
    ok &= report(
        "check.sh fails on pua-literal by default; --warn-pua opts out",
        code != 0 and "pua-literal" in out and code2 == 0 and "with warnings" in out2,
        out.strip().splitlines()[0] if out.strip() else "",
    )
    kit_sources = [str(p) for p in sorted((KIT_ROOT / "kit").glob("*")) if p.suffix in (".qml", ".js")]
    code, out = sh("python3", "-I", str(KIT_ROOT / "tools/foamykit.py"), "lint", *kit_sources)
    ok &= report("the kit itself passes the lint", code == 0, out.strip())
    demo = base / "demo"
    shutil.copytree(FIXTURES / "demo-plugin", demo)
    sh(SYNC, str(demo))
    code, out = sh(CHECK, str(demo))
    ok &= report("check.sh passes on the demo plugin (kit + lint)", code == 0, out.strip())
    code, out = sh(
        "node",
        "-e",
        'const P = require(process.argv[1]).load("FoamyPrefs"); '
        'process.stdout.write(String(P.valid([{key: "x", type: "array"}], "x", [1])))',
        str(demo / "kit/node-loader.cjs"),
    )
    ok &= report(
        "a plugin's stamped kit/node-loader.cjs loads FoamyPrefs in node",
        code == 0 and out.strip() == "true",
        out.strip(),
    )
    unmigrated = base / "unmigrated"
    shutil.copytree(FIXTURES / "demo-plugin", unmigrated)
    shutil.copyfile(KIT_ROOT / "tests/fixtures/old-fork/BoltPopup.qml", unmigrated / "BoltPopup.qml")
    code, out = sh(CHECK, "--lint-only", str(unmigrated))
    ok &= report(
        "check.sh --lint-only flags pre-kit code (the old popup fork)", code != 0 and "unqualified-color" in out
    )

    if ok:
        shutil.rmtree(base, ignore_errors=True)
    else:
        print(f"    kept {base}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
