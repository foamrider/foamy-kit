#!/usr/bin/env python3
"""SafeTextField `masked: true` (tests/qml/Masked.qml) on 4.5, LTR and RTL,
dark and light: the editor holds only the mask, typing, selection, keys and
mouse in step with a normal field, paste through kit/clipboard.sh with the
hostenv.clipboard_fakes() wl-paste (never the real clipboard), copy and cut
that leave Qt's offscreen clipboard alone, accessibility, the drawn caret.
Field shots: tests/out/masked/ (FOAMY_MASKED_OUT overrides)."""

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import hostenv  # noqa: E402

CASES = [(theme, rtl, False) for theme in ("dark", "light") for rtl in (False, True)]
# An RTL locale: the input method runs right to left (arrow keys on the mask).
CASES.append(("dark", False, True))


def run(host, plugin, theme, rtl, rtl_input, out):
    name = f"{theme}-{'rtl' if rtl else 'ltr'}" + ("-rtl-input" if rtl_input else "")
    r = harness.Run(
        host,
        (KIT_ROOT / "tests/qml/Masked.qml").read_text(),
        plugin=plugin,
        theme=theme,
        prefix=f"foamy-kit-masked-{host}-",
    )
    # The fakes go in front of the run's PATH, behind nothing the harness stubs.
    r.env.update(hostenv.clipboard_fakes(r.base / "clipboard", env=r.env))
    r.env.update({"FOAMY_RTL": "1" if rtl else "0", "FOAMY_THEME": theme})
    if rtl_input:
        # Qt takes the system locale (and the input direction) from these.
        r.env.update({"LANG": "ar_EG.UTF-8", "LC_ALL": "ar_EG.UTF-8", "FOAMY_RTL_INPUT": "1"})
    r.run(timeout=90)
    detail = next((line.split("qml: ", 1)[-1] for line in r.log.splitlines() if "FOAMY RESULT" in line), "no result")
    ok = report(f"masked {host}/{name}", r.ok, detail)
    if not ok:
        print("\n".join("    " + line for line in (r.failures() or r.log.splitlines()[-30:])))
    out.mkdir(parents=True, exist_ok=True)
    for png in r.out.glob("*.png"):
        shutil.copyfile(png, out / f"{png.stem}-{host}-{name}.png")
    r.cleanup()
    return ok


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    out = Path(os.environ.get("FOAMY_MASKED_OUT") or KIT_ROOT / "tests/out/masked")
    results = [
        run(host, plugin, theme, rtl, rtl_input, out)
        for host in harness.available_hosts(what="masked")
        for theme, rtl, rtl_input in CASES
    ]
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
