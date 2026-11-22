#!/usr/bin/env python3
"""kit/FoamyClipboard.qml in Quickshell (tests/qml/Clipboard.qml), against
hostenv.clipboard_fakes(): the read and failed signals for every stand-in
mode, the primary selection, one read at a time, cancel() (nothing
follows, the reader stays busy until the stopped read exits, which happens
at once, producer included, while a "loaded" paste's 2.5 s producer would
still run) and a reader destroyed mid-read (its read ends at once too,
although Quickshell kills clipboard.sh with SIGKILL then). The scene checks
the producers through /proc."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import hostenv  # noqa: E402


def run(host):
    plugin = synced_demo()
    r = harness.Run(
        host,
        (KIT_ROOT / "tests/qml/Clipboard.qml").read_text(),
        plugin=plugin,
        prefix=f"foamy-kit-clipboard-{host}-",
    )
    r.env.update(hostenv.clipboard_fakes(r.base / "clipboard", r.env))
    r.env["QML_XHR_ALLOW_FILE_READ"] = "1"
    r.run(timeout=90)
    detail = next((line.split("qml: ", 1)[-1] for line in r.log.splitlines() if "FOAMY RESULT" in line), "no result")
    ok = report(f"FoamyClipboard {host}", r.ok, detail)
    if not ok:
        print("\n".join("    " + line for line in (r.failures() or r.log.splitlines()[-30:])))
    r.cleanup()
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return ok


def main():
    harness.install_signal_cleanup()
    results = [run(host) for host in harness.available_hosts(what="clipboard reader")]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
