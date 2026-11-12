#!/usr/bin/env python3
"""preview/i18n_runtime.py, the shared catalog check that replaces the
plugins' tests/i18n-runtime.py copies: the demo plugin passes (da, ar with
its own catalog, en), a FoamyI18n that ignores the language fails, a plugin
with only English checks English, and an English plural fallback under a
language without the entry."""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import i18n_runtime  # noqa: E402


def main():
    harness.install_signal_cleanup()
    ok = True
    plugin = synced_demo()
    try:
        key, plural, steps = i18n_runtime.plan(i18n_runtime.catalogs(plugin))
        ok &= report(
            "the plan follows the catalogs: da first, then ar and en",
            [s["language"] for s in steps] == ["da", "ar", "en"]
            and key == "Devices"
            and plural == "%1 devices"
            and steps[0]["text"] == "Enheder"
            and steps[0]["plural"] == "%1 enhed"
            and steps[1]["rtl"]
            and not steps[0]["rtl"],
            json.dumps(steps, ensure_ascii=False),
        )
        ok &= report("the demo's catalogs pass live", i18n_runtime.run(plugin))

        broken = plugin.parent / "broken" / plugin.name
        shutil.copytree(plugin, broken)
        i18n = broken / "kit/FoamyI18n.qml"
        text = i18n.read_text()
        i18n.write_text(
            text.replace("return substitute(backend.t(key, key), values)", "return substitute(key, values)")
        )
        ok &= report("a FoamyI18n that ignores the language fails", not i18n_runtime.run(broken, quiet=True))

        english = plugin.parent / "english" / plugin.name
        shutil.copytree(plugin, english)
        for path in (english / "i18n").glob("*.json"):
            if path.stem != "en":
                path.unlink()
        key, plural, steps = i18n_runtime.plan(i18n_runtime.catalogs(english))
        ok &= report(
            "an English-only plugin checks Arabic fallback and English",
            [s["language"] for s in steps] == ["ar", "en"]
            and steps[0]["text"] == key
            and steps[0]["plural"] == "%1 device",
            json.dumps(steps, ensure_ascii=False),
        )
        ok &= report("and passes live", i18n_runtime.run(english))
    finally:
        shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
