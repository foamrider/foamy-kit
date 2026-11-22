#!/usr/bin/env python3
"""tests/validate.sh (kit/tooling/validate.py) on a synced copy of the demo
plugin: QML-loaded JavaScript is linted, not skipped; baselines fail only on
new findings (and on grown complexity); kit-owned files (kit/ and the root
files foamy-kit.lock lists) are never linted or reformatted; a missing or
mismatched pinned tool, an unreasoned exclusion, a local lint config that
does not extend the kit's, a misspelt check name or a missing suite hook
fails; --ci skips the host checks with a reason; --fast reaches the suite.

Needs the tools mise.toml pins (`mise install`); Qt 6 qmllint and the Omarchy
shell for the qmllint part (SKIP without them)."""

import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, report, synced_demo  # noqa: E402


def validate(plugin, *args, env=None, kit=KIT_ROOT):
    env = dict(env or os.environ, FOAMY_KIT=str(kit))
    if kit is None:
        del env["FOAMY_KIT"]
    result = subprocess.run(
        ["bash", str(plugin / "tests/validate.sh"), *args],
        cwd=plugin,
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )
    return result.returncode, result.stdout + result.stderr


def summary(out):
    return out[out.find("validate summary:") :].strip() if "validate summary:" in out else out.strip()[-400:]


def main():
    ok = True
    plugin = synced_demo()
    code, out = validate(plugin, "--only", "oxlint")
    if "mise install" in out:
        print(f"FAIL the pinned tools are not installed; run `mise install` in foamy-kit: {summary(out)}")
        return 1
    # Adopt the demo plugin's own findings, as a plugin does when it adopts the checks.
    validate(plugin, "--update-baseline")

    # JavaScript: QML directives are read as comments, the code is still linted.
    (plugin / "Model.js").write_text(
        '.pragma library\n.import "Preferences.js" as Prefs\n\n'
        "function label(value) {\n  return Prefs.fields.length + value\n}\n"
    )
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report(
        "a .pragma/.import file parses and passes oxlint", code == 0 and "2 QML directive line(s)" in out, summary(out)
    )
    (plugin / "Model.js").write_text(
        ".pragma library\n\nfunction label(value) {\n  var unused = 1\n  return value\n}\n"
    )
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report(
        "a finding in a QML-loaded file fails",
        code != 0 and "new: Model.js: eslint(no-unused-vars)" in out,
        summary(out),
    )
    code, out = validate(plugin, "--update-baseline", "oxlint")
    baseline = plugin / "tests/lint/oxlint-baseline.txt"
    ok &= report(
        "--update-baseline writes a reviewed baseline",
        code == 0
        and baseline.is_file()
        and "Model.js: eslint(no-unused-vars)" in baseline.read_text()
        and "1 added" in out,
        summary(out),
    )
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report("a baselined finding passes", code == 0 and "1 baselined finding" in out, summary(out))
    (plugin / "Model.js").write_text(
        ".pragma library\n\n// moved down\nfunction label(value) {\n  var unused = 1\n"
        "  return value\n}\nfunction other(a) {\n  var spare = a\n  return 1\n}\n"
    )
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report(
        "the baseline survives line shifts; a new finding still fails",
        code != 0 and "1 baselined finding" in out and "spare" in out and "'unused'" not in out.split("new:", 1)[-1],
        summary(out),
    )
    (plugin / "Model.js").write_text(".pragma library\n\nfunction label(value) {\n  return value\n}\n")
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report(
        "a fixed finding passes and asks to shrink the baseline", code == 0 and "fixed; shrink" in out, summary(out)
    )

    # Python: complexity is measured; kit-owned files are left alone.
    branches = "".join(f"    if x == {i}:\n        return {i}\n" for i in range(16))
    (plugin / "tool.py").write_text(f"def pick(x):\n{branches}    return -1\n")
    code, out = validate(plugin, "--only", "ruff,ruff-format")
    ok &= report("C901 above 15 fails ruff", code != 0 and "C901" in out and "too complex (> 15)" in out, summary(out))
    validate(plugin, "--update-baseline", "ruff")
    entry = (plugin / "tests/lint/ruff-baseline.txt").read_text()
    code, out = validate(plugin, "--only", "ruff")
    ok &= report(
        "the baseline records the complexity; unchanged passes", code == 0 and "[17]" in entry, entry.strip()[-200:]
    )
    branches = "".join(f"    if x == {i}:\n        return {i}\n" for i in range(18))
    (plugin / "tool.py").write_text(f"def pick(x):\n{branches}    return -1\n")
    code, out = validate(plugin, "--only", "ruff")
    ok &= report(
        "a baselined function that grew more complex fails",
        code != 0 and "grew:" in out and "now 19, baseline 17" in out,
        summary(out),
    )
    (plugin / "tool.py").unlink()
    (plugin / "kit/stray.py").write_text("import os\nx=( 1,\n2 )\n")
    code, out = validate(plugin, "--only", "ruff-format,vulture")
    ok &= report("kit-owned files are neither formatted nor linted", code == 0, summary(out))
    (plugin / "kit/stray.py").unlink()
    (plugin / "tool.py").write_text("x=( 1,\n2 )\n")
    code, out = validate(plugin, "--only", "ruff-format")
    ok &= report(
        "an unformatted repository file fails ruff format --check", code != 0 and "tool.py" in out, summary(out)
    )
    (plugin / "tool.py").write_text("import json\n\n\ndef handler():\n    return 1\n")
    code, out = validate(plugin, "--only", "vulture")
    ok &= report(
        "vulture reports an unused import and function",
        code != 0 and "unused import 'json'" in out and "unused function 'handler'" in out,
        summary(out),
    )
    lint = plugin / "tests/lint"
    (lint / "vulture-ignore.txt").write_text("handler\n")
    code, out = validate(plugin, "--only", "vulture")
    ok &= report("a vulture entry point without a reason fails", code != 0 and "needs a reason" in out, summary(out))
    (lint / "vulture-ignore.txt").write_text("handler  # called by name from the QML side\n")
    (plugin / "tool.py").write_text("def handler():\n    return 1\n")
    code, out = validate(plugin, "--only", "vulture")
    ok &= report("a reasoned entry point is accepted", code == 0 and "1 reviewed entry point" in out, summary(out))
    (plugin / "tool.py").unlink()

    # Shell: bash -n, shellcheck and shfmt on repository scripts only.
    (plugin / "run.sh").write_text('#!/bin/bash\nif [ -n "$1" ]; then\n    echo $1\nfi\n')
    code, out = validate(plugin, "--only", "shellcheck,shfmt")
    ok &= report(
        "shellcheck and shfmt check repository scripts",
        code != 0 and "SC2086" in out and "FAIL  shfmt" in out,
        summary(out),
    )
    (plugin / "run.sh").write_text('#!/bin/bash\nif [ -n "$1" ]; then\n  echo "$1"\nfi\n')
    code, out = validate(plugin, "--only", "shellcheck,shfmt")
    ok &= report("a clean script passes", code == 0, summary(out))
    # A root script that foamy-kit.lock lists (not under kit/) is the kit's:
    # the same findings in it fail nothing. run.sh stays, so the checks run.
    kit_check = plugin / "tests/kit-check.sh"
    synced = kit_check.read_bytes()
    with kit_check.open("a") as script:
        script.write('if [ -n "$1" ]; then\n    echo $1\nfi\n')
    code, out = validate(plugin, "--only", "shellcheck,shfmt")
    ok &= report(
        "lock-listed root scripts are neither linted nor formatted",
        code == 0 and "PASS  shellcheck" in out and "PASS  shfmt" in out,
        summary(out),
    )
    kit_check.write_bytes(synced)
    (plugin / "run.sh").unlink()

    # Exclusions need a reason and a known check.
    (lint / "exclude.txt").write_text("preview/*\n")
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report("an exclusion without a reason fails", code != 0 and "needs a reason" in out, summary(out))
    (lint / "exclude.txt").write_text("preview/*  qmlfmt  # typo\n")
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report("an exclusion naming an unknown check fails", code != 0 and "unknown check" in out, summary(out))
    (lint / "exclude.txt").unlink()

    # A local lint config may add to the kit's, never replace it.
    (plugin / ".ruff.toml").write_text("line-length = 200\n")
    (plugin / "tool.py").write_text("x = 1\n")
    code, out = validate(plugin, "--only", "ruff")
    ok &= report(
        "a .ruff.toml that does not extend the kit's config fails",
        code != 0 and "must extend the kit's config" in out,
        summary(out),
    )
    (plugin / ".ruff.toml").unlink()
    (plugin / "tool.py").unlink()
    # Only an "extends" list that names the kit's config counts; the name
    # elsewhere in the text (another key, a comment, a string) does not.
    extend = "must extend the kit's config"
    for name, text, expected in (
        ("has no extends", '{"rules": {}}\n', extend),
        (
            "names the kit's config in ignorePatterns",
            '{"extends": [], "ignorePatterns": ["../../.oxlintrc.json"]}\n',
            extend,
        ),
        ("names it only in a comment", '{\n  // "extends": ["../../.oxlintrc.json"],\n  "rules": {}\n}\n', extend),
        ("has extends as a string", '{"extends": "../../.oxlintrc.json"}\n', extend),
        ("is not a JSON object", '["../../.oxlintrc.json"]\n', extend),
        ("is not JSON", '{"extends": ["../../.oxlintrc.json"]\n', "oxlintrc.json is not JSON"),
        (
            "extends it, with comments and trailing commas",
            '// Plugin rules.\n{\n  "extends": ["../../.oxlintrc.json",],\n  /* why */ "rules": {"no-console": "off",},\n}\n',
            None,
        ),
    ):
        (lint / "oxlintrc.json").write_text(text)
        code, out = validate(plugin, "--only", "oxlint")
        passed = code == 0 and "PASS  oxlint" in out if expected is None else code != 0 and expected in out
        ok &= report(
            f"a tests/lint/oxlintrc.json that {name} {'passes' if expected is None else 'fails'}", passed, summary(out)
        )
    (lint / "oxlintrc.json").unlink()

    # A missing pinned tool is a failure that says what to do.
    empty = Path(tempfile.mkdtemp(prefix="foamy-kit-nomise-"))
    for tool in ("bash", "python3", "git", "dirname", "readlink"):
        (empty / tool).symlink_to(shutil.which(tool))
    env = dict(os.environ, PATH=str(empty))
    code, out = validate(plugin, "--only", "oxlint", env=env)
    ok &= report(
        "a missing pinned tool fails and says to run mise install", code != 0 and "mise install" in out, summary(out)
    )
    # A tool on PATH at another version (a system package) is no stand-in.
    (empty / "oxlint").write_text('#!/bin/sh\necho "Version: 0.0.1"\n')
    (empty / "oxlint").chmod(0o755)
    code, out = validate(plugin, "--only", "oxlint", env=env)
    ok &= report(
        "a pinned tool at another version fails and says to run mise install",
        code != 0 and "mise.toml pins oxlint" in out and "run `mise install`" in out,
        summary(out),
    )
    # A linter that ends without its JSON report (killed, out of memory)
    # fails with its exit code, as qmllint does.
    pins = tomllib.loads((KIT_ROOT / "mise.toml").read_text())["tools"]
    (plugin / "probe.py").write_text("x = 1\n")
    (plugin / "probe.sh").write_text("#!/bin/bash\necho ok\n")
    for tool, label in (("oxlint", "oxlint"), ("ruff", "ruff check"), ("shellcheck", "shellcheck")):
        version = next(v for k, v in pins.items() if k.rsplit("/", 1)[-1] == tool)
        (empty / tool).unlink(missing_ok=True)
        (empty / tool).write_text(f'#!/bin/sh\n[ "$1" = --version ] && echo "{tool} {version}" && exit 0\nexit 9\n')
        (empty / tool).chmod(0o755)
        code, out = validate(plugin, "--only", tool, env=env)
        ok &= report(
            f"{label} with no JSON report fails with its exit code",
            code != 0 and f"{label} produced no JSON report (exit 9)" in out,
            summary(out),
        )
    (plugin / "probe.py").unlink()
    (plugin / "probe.sh").unlink()
    shutil.rmtree(empty, ignore_errors=True)

    # The suite hook, and --ci.
    code, out = validate(plugin, "--ci", "--skip", "oxlint,ruff,ruff-format,vulture,shellcheck,shfmt")
    ok &= report(
        "a missing tests/suite.sh fails", code != 0 and "FAIL  suite: tests/suite.sh is missing" in out, summary(out)
    )
    (plugin / "tests/suite.sh").write_text('#!/bin/bash\necho "suite args: $*; FOAMY_VALIDATE=$FOAMY_VALIDATE"\n')
    code, out = validate(plugin, "--ci")
    ok &= report(
        "--ci: host checks are SKIPs with a reason; the suite gets --ci",
        code == 0
        and "SKIP  qmllint: --ci" in out
        and "SKIP  qmlformat: --ci" in out
        and "SKIP  plugin-validate: --ci" in out
        and "suite args: --ci; FOAMY_VALIDATE=ci" in out
        and "PASS  kit-check" in out,
        summary(out),
    )
    ok &= report("--ci with FOAMY_KIT runs the design lint", "PASS  design-lint" in out, summary(out))
    code, out = validate(plugin, "--only", "oxlnt")
    ok &= report(
        "a misspelt check name fails instead of running nothing",
        code != 0 and "unknown check(s): oxlnt" in out,
        summary(out),
    )
    code, out = validate(plugin, "--fast", "--only", "suite")
    ok &= report(
        "--fast reaches the suite", code == 0 and "suite args: --fast; FOAMY_VALIDATE=fast" in out, summary(out)
    )
    code, out = validate(plugin, "--ci", "--only", "design-lint", kit=None)
    ok &= report(
        "--ci without FOAMY_KIT skips the design lint and says why",
        code == 0 and "SKIP  design-lint: --ci: FOAMY_KIT is unset (checks.yml sets it" in out,
        summary(out),
    )
    code, out = validate(plugin, "--ci", "--only", "design-lint", kit=plugin)
    ok &= report(
        "a FOAMY_KIT that is not a foamy-kit checkout fails the design lint",
        code != 0 and f"FAIL  design-lint: FOAMY_KIT={plugin} is not a foamy-kit checkout" in out,
        summary(out),
    )
    (plugin / "tests/suite.sh").write_text("#!/bin/bash\nexit 3\n")
    code, out = validate(plugin, "--ci", "--only", "suite")
    ok &= report("a failing suite fails validate", code != 0 and "exit 3" in out, summary(out))

    # A qmllint that leaves no readable report: the failure names its exit
    # code and why the report could not be read (a full disk looks the same).
    fake = Path(tempfile.mkdtemp(prefix="foamy-kit-fakeqt-"))
    (fake / "bin").mkdir()
    (fake / "shell/Commons").mkdir(parents=True)
    qt_env = dict(os.environ, FOAMY_QT_BIN=str(fake / "bin"), FOAMY_HOST_45=str(fake / "shell"))
    for name, script, expected in (
        ("no report", "#!/bin/sh\nexit 5\n", ("exit 5", "No such file or directory")),
        (
            "a report that is not JSON",
            '#!/bin/sh\nwhile [ "$1" != --json ]; do shift; done\necho broken >"$2"\nexit 0\n',
            ("exit 0", "Expecting value"),
        ),
    ):
        (fake / "bin/qmllint").write_text(script)
        (fake / "bin/qmllint").chmod(0o755)
        code, out = validate(plugin, "--only", "qmllint", env=qt_env)
        ok &= report(
            f"qmllint with {name} fails with its exit code and the read error",
            code != 0 and "qmllint wrote no JSON report" in out and all(part in out for part in expected),
            summary(out),
        )
    shutil.rmtree(fake, ignore_errors=True)

    # qmllint on the host: the real imports, unused imports are errors.
    if os.access("/usr/lib/qt6/bin/qmllint", os.X_OK) and Path("/usr/share/omarchy/shell/Commons").is_dir():
        (plugin / "Extra.qml").write_text(
            'import QtQuick\nimport qs.Commons\nimport "kit"\n\nItem { width: FoamyStyle.gap }\n'
        )
        code, out = validate(plugin, "--only", "qmllint")
        ok &= report(
            "qmllint resolves qs.* and kit/, and fails on an unused import",
            code != 0
            and "Extra.qml: unused-imports" in out
            and "import qs.Commons" in out
            and "FoamyStyle" not in out.split("new:", 1)[-1],
            summary(out),
        )
        code, out = validate(plugin, "--only", "qmlformat")
        ok &= report(
            "qmlformat --check reports an unformatted file",
            code != 0 and "+++ -" in out and "Extra.qml" in out,
            summary(out),
        )
        (plugin / "Extra.qml").unlink()

        # QML run from a root assembled at run time (Lock Studio's) imports
        # what that root links in beside it: tests/lint/qmllint-links.txt
        # gives qmllint's staged copy the same links. FoamyStyle.font is a
        # typed object, so its members resolve too.
        (plugin / "app").mkdir()
        (plugin / "app/Panel.qml").write_text(
            'import QtQuick\nimport "kit"\n\nItem {\n  width: FoamyStyle.font.body\n}\n'
        )
        code, out = validate(plugin, "--only", "qmllint")
        ok &= report(
            "without its links, an assembled root's import does not resolve",
            code != 0 and "app/Panel.qml: import" in out,
            summary(out),
        )
        links = plugin / "tests/lint/qmllint-links.txt"
        links.write_text(
            "app/kit  kit  # the app's root links the kit beside it\n"
            "app/Commons  @shell/Commons  # and the shell's Commons\n"
        )
        code, out = validate(plugin, "--only", "qmllint")
        ok &= report(
            "with them it resolves, FoamyStyle.font.body included, and the links stay out of the repository",
            code == 0 and "app/Panel.qml" not in out and not (plugin / "app/kit").exists(),
            summary(out),
        )
        for line, expected in (
            ("app/kit  kit\n", "needs a reason"),
            ("../app/kit  kit  # outside\n", "plain relative path"),
            ("/tmp/kit  kit  # absolute\n", "plain relative path"),
            ("app/Panel.qml  kit  # an existing file\n", "already exists"),
            ("app/kit  nowhere  # a missing target\n", "does not exist"),
            ("app/kit  ../outside  # a target outside the repository\n", "does not exist"),
            ("app/kit  # no target\n", "expected `<link> <target>"),
            ("app/i18n  i18n  # a directory\napp/i18n/sub  kit  # inside it\n", "overlap"),
        ):
            links.write_text(line)
            code, out = validate(plugin, "--only", "qmllint")
            ok &= report(f"a bad link is refused ({expected})", code != 0 and expected in out, summary(out))
        links.unlink()
        shutil.rmtree(plugin / "app")
    else:
        print("SKIP qmllint/qmlformat: no Qt 6 qmllint or Omarchy shell")

    if ok:
        shutil.rmtree(plugin.parent, ignore_errors=True)
    else:
        print(f"    kept {plugin}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
