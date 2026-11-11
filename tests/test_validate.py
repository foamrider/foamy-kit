#!/usr/bin/env python3
"""tests/validate.sh (kit/tooling/validate.py) on a synced copy of the demo
plugin: QML-loaded JavaScript is linted, not skipped; baselines fail only on
new findings (and on grown complexity); kit-owned files are never linted or
reformatted; a missing pinned tool, an unreasoned exclusion or a missing
suite hook fails; --ci skips the host checks with a reason.

Needs the tools mise.toml pins (`mise install`); Qt 6 qmllint and the Omarchy
shell for the qmllint part (SKIP without them)."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, report, synced_demo  # noqa: E402


def validate(plugin, *args, env=None):
    env = dict(env or os.environ, FOAMY_KIT=str(KIT_ROOT))
    result = subprocess.run(["bash", str(plugin / "tests/validate.sh"), *args], cwd=plugin, capture_output=True,
                            text=True, timeout=600, env=env)
    return result.returncode, result.stdout + result.stderr


def summary(out):
    return out[out.find("validate summary:"):].strip() if "validate summary:" in out else out.strip()[-400:]


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
    (plugin / "Model.js").write_text('.pragma library\n.import "Preferences.js" as Prefs\n\n'
                                     "function label(value) {\n  return Prefs.fields.length + value\n}\n")
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report("a .pragma/.import file parses and passes oxlint", code == 0 and "2 QML directive line(s)" in out, summary(out))
    (plugin / "Model.js").write_text('.pragma library\n\nfunction label(value) {\n  var unused = 1\n  return value\n}\n')
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report("a finding in a QML-loaded file fails", code != 0 and "new: Model.js: eslint(no-unused-vars)" in out, summary(out))
    code, out = validate(plugin, "--update-baseline", "oxlint")
    baseline = plugin / "tests/lint/oxlint-baseline.txt"
    ok &= report("--update-baseline writes a reviewed baseline", code == 0 and baseline.is_file()
                 and "Model.js: eslint(no-unused-vars)" in baseline.read_text() and "1 added" in out, summary(out))
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report("a baselined finding passes", code == 0 and "1 baselined finding" in out, summary(out))
    (plugin / "Model.js").write_text('.pragma library\n\n// moved down\nfunction label(value) {\n  var unused = 1\n'
                                     "  return value\n}\nfunction other(a) {\n  var spare = a\n  return 1\n}\n")
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report("the baseline survives line shifts; a new finding still fails",
                 code != 0 and "1 baselined finding" in out and "spare" in out and "'unused'" not in out.split("new:", 1)[-1],
                 summary(out))
    (plugin / "Model.js").write_text(".pragma library\n\nfunction label(value) {\n  return value\n}\n")
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report("a fixed finding passes and asks to shrink the baseline", code == 0 and "fixed; shrink" in out, summary(out))

    # Python: complexity is measured; kit-owned files are left alone.
    branches = "".join(f"    if x == {i}:\n        return {i}\n" for i in range(16))
    (plugin / "tool.py").write_text(f"def pick(x):\n{branches}    return -1\n")
    code, out = validate(plugin, "--only", "ruff,ruff-format")
    ok &= report("C901 above 15 fails ruff", code != 0 and "C901" in out and "too complex (> 15)" in out, summary(out))
    validate(plugin, "--update-baseline", "ruff")
    entry = (plugin / "tests/lint/ruff-baseline.txt").read_text()
    code, out = validate(plugin, "--only", "ruff")
    ok &= report("the baseline records the complexity; unchanged passes", code == 0 and "[17]" in entry, entry.strip()[-200:])
    branches = "".join(f"    if x == {i}:\n        return {i}\n" for i in range(18))
    (plugin / "tool.py").write_text(f"def pick(x):\n{branches}    return -1\n")
    code, out = validate(plugin, "--only", "ruff")
    ok &= report("a baselined function that grew more complex fails", code != 0 and "grew:" in out and "now 19, baseline 17" in out,
                 summary(out))
    (plugin / "tool.py").write_text("def pick(x):\n    return x\n")
    (plugin / "tool.py").unlink()
    (plugin / "kit/stray.py").write_text("import os\nx=( 1,\n2 )\n")
    code, out = validate(plugin, "--only", "ruff-format,vulture")
    ok &= report("kit-owned files are neither formatted nor linted", code == 0, summary(out))
    (plugin / "kit/stray.py").unlink()
    (plugin / "tool.py").write_text("x=( 1,\n2 )\n")
    code, out = validate(plugin, "--only", "ruff-format")
    ok &= report("an unformatted repository file fails ruff format --check", code != 0 and "tool.py" in out, summary(out))
    (plugin / "tool.py").write_text("import json\n\n\ndef handler():\n    return 1\n")
    code, out = validate(plugin, "--only", "vulture")
    ok &= report("vulture reports an unused import and function", code != 0 and "unused import 'json'" in out
                 and "unused function 'handler'" in out, summary(out))
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
    ok &= report("shellcheck and shfmt check repository scripts", code != 0 and "SC2086" in out
                 and "FAIL  shfmt" in out and "kit-check.sh" not in out, summary(out))
    (plugin / "run.sh").write_text('#!/bin/bash\nif [ -n "$1" ]; then\n  echo "$1"\nfi\n')
    code, out = validate(plugin, "--only", "shellcheck,shfmt")
    ok &= report("a clean script passes", code == 0, summary(out))
    (plugin / "run.sh").unlink()

    # Exclusions need a reason and a known check.
    (lint / "exclude.txt").write_text("preview/*\n")
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report("an exclusion without a reason fails", code != 0 and "needs a reason" in out, summary(out))
    (lint / "exclude.txt").write_text("preview/*  qmlfmt  # typo\n")
    code, out = validate(plugin, "--only", "oxlint")
    ok &= report("an exclusion naming an unknown check fails", code != 0 and "unknown check" in out, summary(out))
    (lint / "exclude.txt").unlink()

    # A missing pinned tool is a failure that says what to do.
    empty = Path(tempfile.mkdtemp(prefix="foamy-kit-nomise-"))
    for tool in ("bash", "python3", "git", "dirname", "readlink"):
        (empty / tool).symlink_to(shutil.which(tool))
    env = dict(os.environ, PATH=str(empty))
    code, out = validate(plugin, "--only", "oxlint", env=env)
    ok &= report("a missing pinned tool fails and says to run mise install", code != 0 and "mise install" in out, summary(out))
    shutil.rmtree(empty, ignore_errors=True)

    # The suite hook, and --ci.
    code, out = validate(plugin, "--ci", "--skip", "oxlint,ruff,ruff-format,vulture,shellcheck,shfmt")
    ok &= report("a missing tests/suite.sh fails", code != 0 and "FAIL  suite: tests/suite.sh is missing" in out, summary(out))
    (plugin / "tests/suite.sh").write_text('#!/bin/bash\necho "suite args: $*; FOAMY_VALIDATE=$FOAMY_VALIDATE"\n')
    code, out = validate(plugin, "--ci")
    ok &= report("--ci: host checks are SKIPs with a reason; the suite gets --ci", code == 0
                 and "SKIP  qmllint: --ci" in out and "SKIP  qmlformat: --ci" in out and "SKIP  plugin-validate: --ci" in out
                 and "suite args: --ci; FOAMY_VALIDATE=ci" in out and "PASS  kit-check" in out, summary(out))
    (plugin / "tests/suite.sh").write_text("#!/bin/bash\nexit 3\n")
    code, out = validate(plugin, "--ci", "--only", "suite")
    ok &= report("a failing suite fails validate", code != 0 and "exit 3" in out, summary(out))

    # qmllint on the host: the real imports, unused imports are errors.
    if os.access("/usr/lib/qt6/bin/qmllint", os.X_OK) and Path("/usr/share/omarchy/shell/Commons").is_dir():
        (plugin / "Extra.qml").write_text('import QtQuick\nimport qs.Commons\nimport "kit"\n\nItem { width: FoamyStyle.gap }\n')
        code, out = validate(plugin, "--only", "qmllint")
        ok &= report("qmllint resolves qs.* and kit/, and fails on an unused import",
                     code != 0 and "Extra.qml: unused-imports" in out and "import qs.Commons" in out
                     and "FoamyStyle" not in out.split("new:", 1)[-1], summary(out))
        code, out = validate(plugin, "--only", "qmlformat")
        ok &= report("qmlformat --check reports an unformatted file", code != 0 and "+++ -" in out and "Extra.qml" in out,
                     summary(out))
        (plugin / "Extra.qml").unlink()
    else:
        print("SKIP qmllint/qmlformat: no Qt 6 qmllint or Omarchy shell")

    if ok:
        shutil.rmtree(plugin.parent, ignore_errors=True)
    else:
        print(f"    kept {plugin}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
