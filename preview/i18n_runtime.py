#!/usr/bin/env python3
"""A plugin's catalogs through the kit's FoamyI18n in a live, isolated shell.

  python3 <foamy-kit>/preview/i18n_runtime.py <plugin-dir>

Replaces the per-plugin tests/i18n-runtime.py copies. It copies the plugin's
kit/ and i18n/ into a throwaway plugin (plus an English-only entry that
exists only there), runs it under preview/harness.py (isolated: temp HOME,
private buses, no host commands) and switches the Omarchy language file
live: the plugin's first non-English catalog (no.json when there is one),
then Arabic, then English. At each step it checks, with expectations derived
from the catalogs themselves:

- a translated string follows the language without a restart, falling back
  to English (and then the key) where a catalog has no entry;
- a plural entry's `one` form for a count of 1, in the language's digits;
- right-to-left only under Arabic;
- an English-only and an unknown string, and `%1` / `{name}` values that
  stay literal (substituted once).

Exit 0 and a PASS line, or 1 with the reason. An English-only plugin checks
English alone. Plugin-specific UI under a language switch (foamy-notifications'
cards) stays in the plugin's own test.
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

ENGLISH_ONLY = "English only"
SHELL = r"""import QtQuick
import Quickshell
import Quickshell.Io
import "harness"
import "plugin/kit" as Kit

ShellRoot {
  id: shell
  readonly property var steps: JSON.parse(Quickshell.env("FOAMY_I18N_STEPS"))
  readonly property string key: Quickshell.env("FOAMY_I18N_KEY")
  readonly property string pluralKey: Quickshell.env("FOAMY_I18N_PLURAL")
  property var translator: Kit.FoamyI18n
  property string rendered: key ? translator.t(key) : ""
  property int failures: 0
  function fail(text) { failures++; console.log("FOAMY FAIL " + text) }
  FileView { id: choice; path: Quickshell.env("OMARCHY_LANGUAGE_FILE") }
  FoamyWait { id: wait }
  Component.onCompleted: check(0)

  function plural(step) {
    return step.plural.split("%1").join(translator.number(1))
  }
  function check(index) {
    var step = steps[index]
    wait.waitFor(function() { return translator.language === step.language && (!key || rendered === step.text) }, 10000, function(ok) {
      if (!ok) fail(step.language + ": " + JSON.stringify(key) + " reads " + JSON.stringify(rendered) + ", expected " + JSON.stringify(step.text)
                    + " (language " + translator.language + ")")
      if (pluralKey && translator.tn(pluralKey, 1) !== plural(step))
        fail(step.language + ": tn(" + JSON.stringify(pluralKey) + ", 1) is " + JSON.stringify(translator.tn(pluralKey, 1)) + ", expected " + JSON.stringify(plural(step)))
      if (translator.rightToLeft !== step.rtl) fail(step.language + ": rightToLeft is " + translator.rightToLeft)
      if (translator.t("ENGLISH_ONLY") !== "ENGLISH_ONLY") fail(step.language + ": an English-only string reads " + translator.t("ENGLISH_ONLY"))
      if (translator.t("Unknown label") !== "Unknown label") fail(step.language + ": an unknown string is not its key")
      if (translator.t("Name %1 {name}", ["$& %2"]) !== "Name $& %2 {name}") fail(step.language + ": a %1 value is substituted more than once")
      if (translator.t("Name {name}", { name: "$& {name}" }) !== "Name $& {name}") fail(step.language + ": a {name} value is substituted more than once")
      if (index + 1 < steps.length) {
        choice.setText(steps[index + 1].language + "\n")
        check(index + 1)
      } else {
        console.log("FOAMY RESULT " + steps.map(function(s) { return s.language }).join("/") + " failures=" + failures)
        console.log("FOAMY DONE")
        Qt.quit()
      }
    })
  }
}
""".replace("ENGLISH_ONLY", ENGLISH_ONLY)


def catalogs(plugin):
    """{language: catalog} of the plugin's i18n/*.json (each must be an object)."""
    found = {}
    for path in sorted((Path(plugin) / "i18n").glob("*.json")):
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise SystemExit(f"{path}: a catalog is a JSON object")
        found[path.stem] = data
    if "en" not in found:
        raise SystemExit(f"{plugin}: no i18n/en.json")
    return found


def text(catalog, key):
    value = catalog.get(key)
    return value if isinstance(value, str) and value else None


def expected_text(cats, language, key):
    """Commons.Translations' lookup: the language, its base language, English, the key."""
    for code in (language, language.split("-")[0], "en"):
        found = text(cats.get(code, {}), key)
        if found:
            return found
    return key


def expected_one(cats, language, key):
    for code in (language, language.split("-")[0], "en"):
        entry = cats.get(code, {}).get(key)
        if isinstance(entry, dict) and isinstance(entry.get("one"), str) and entry["one"]:
            return entry["one"]
    return key


def plan(cats):
    """(key, plural key, steps) for the plugin's catalogs."""
    # Norwegian when there is one, else another non-English catalog; Arabic
    # comes second anyway, for right-to-left.
    others = sorted((code for code in cats if code != "en"), key=lambda code: (code != "no", code == "ar", code))
    primary = others[0] if others else None
    languages = ([primary] if primary else []) + (["ar"] if primary != "ar" else []) + ["en"]
    plain = lambda k: "%" not in k and "{" not in k  # noqa: E731
    key = next((k for k, v in cats.get(primary, {}).items() if isinstance(v, str) and v and v != k and plain(k)), None)
    if key is None:
        key = next((k for k, v in cats["en"].items() if isinstance(v, str) and plain(k)), "")
    # A plural entry whose `one` forms hold no hole but %1, wherever it is translated.
    def usable(k):
        entries = [c[k] for c in cats.values() if k in c]
        return all(isinstance(e, dict) and isinstance(e.get("one"), str) and "{" not in e["one"]
                   and e["one"].replace("%1", "").find("%") < 0 for e in entries)
    plural = next((k for k, v in cats["en"].items() if isinstance(v, dict) and usable(k)), "")
    steps = [{"language": code, "text": expected_text(cats, code, key) if key else "",
              "plural": expected_one(cats, code, plural) if plural else "", "rtl": code == "ar"} for code in languages]
    return key, plural, steps


def run(plugin, timeout=90, quiet=False):
    """True when the plugin's catalogs pass; prints PASS/FAIL unless `quiet`."""
    plugin = Path(plugin).resolve()
    if not (plugin / "kit/FoamyI18n.qml").is_file():
        raise SystemExit(f"{plugin}: no kit/FoamyI18n.qml (sync the kit first)")
    cats = catalogs(plugin)
    key, plural, steps = plan(cats)
    work = Path(tempfile.mkdtemp(prefix="foamy-kit-i18n-"))
    try:
        copy = work / plugin.name
        copy.mkdir()
        shutil.copytree(plugin / "kit", copy / "kit")
        shutil.copytree(plugin / "i18n", copy / "i18n")
        english = dict(cats["en"], **{ENGLISH_ONLY: ENGLISH_ONLY})
        (copy / "i18n/en.json").write_text(json.dumps(english, ensure_ascii=False))
        r = harness.Run("4.5", SHELL, plugin=copy, language=steps[0]["language"], prefix="foamy-kit-i18n-run-")
        r.env.update(FOAMY_I18N_STEPS=json.dumps(steps), FOAMY_I18N_KEY=key, FOAMY_I18N_PLURAL=plural)
        r.run(timeout=timeout)
        result = next((l.split("FOAMY RESULT ", 1)[1] for l in r.log.splitlines() if "FOAMY RESULT" in l), "no result")
        detail = f"{result}; {json.dumps(key, ensure_ascii=False)}" + (f", plural {json.dumps(plural, ensure_ascii=False)}" if plural else ", no plural entry")
        if not quiet:
            print(f"{'PASS' if r.ok else 'FAIL'} i18n runtime {plugin.name}: {detail}")
            if not r.ok:
                print("\n".join("    " + l for l in (r.failures() or r.log.splitlines()[-30:])))
        r.cleanup()
        return r.ok
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plugins", nargs="+")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    harness.install_signal_cleanup()
    results = [run(plugin, args.timeout) for plugin in args.plugins]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
