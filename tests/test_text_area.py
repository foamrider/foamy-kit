#!/usr/bin/env python3
"""SafeTextArea (tests/qml/TextArea.qml) on 4.5, LTR and RTL, dark and light:
newlines, the key hook, focus, paste through kit/clipboard.sh `multiline`
with the hostenv.clipboard_fakes() wl-paste (never the real clipboard):
line breaks kept, NUL and oversized text refused, maximumLength, late
results dropped; the height between minimumHeight and maximumHeight, and
scrolling to the caret; `quiet` on SafeTextArea and SafeTextField.
Field shots: tests/out/text-area/."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import hostenv  # noqa: E402


def run(host, plugin, theme, rtl, out):
    name = f"{theme}-{'rtl' if rtl else 'ltr'}"
    r = harness.Run(
        host,
        (KIT_ROOT / "tests/qml/TextArea.qml").read_text(),
        plugin=plugin,
        theme=theme,
        prefix=f"foamy-kit-text-area-{host}-",
    )
    r.env.update(hostenv.clipboard_fakes(r.base / "clipboard", env=r.env))
    # The test reads the stand-in's argv file synchronously.
    r.env.update({"FOAMY_RTL": "1" if rtl else "0", "FOAMY_THEME": theme, "QML_XHR_ALLOW_FILE_READ": "1"})
    r.run(timeout=90)
    detail = next((line.split("qml: ", 1)[-1] for line in r.log.splitlines() if "FOAMY RESULT" in line), "no result")
    ok = report(f"text area {host}/{name}", r.ok, detail)
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
    out = KIT_ROOT / "tests/out/text-area"
    results = [
        run(host, plugin, theme, rtl, out)
        for host in harness.available_hosts(what="text area")
        for theme in ("dark", "light")
        for rtl in (False, True)
    ]
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
