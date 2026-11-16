#!/usr/bin/env python3
"""kit/FoamyClipboard.qml in Quickshell (tests/qml/Clipboard.qml), against
hostenv.clipboard_fakes(): the read and failed signals for every stand-in
mode, the primary selection, one read at a time, and cancel() (nothing
follows, the reader stays busy until the stopped read exits, and its
wl-paste, which ignores TERM, is gone)."""

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo  # noqa: E402

sys.path.insert(0, str(KIT_ROOT / "preview"))
import hostenv  # noqa: E402


def gone(pid):
    """True once `pid` is gone or a zombie (bounded wait)."""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        except (OSError, IndexError):
            return True
        if state == "Z":
            return True
        time.sleep(0.05)
    return False


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
    pids = [line.split("FOAMY PASTE PID ", 1)[1].strip() for line in r.log.splitlines() if "FOAMY PASTE PID " in line]
    ok = report(f"FoamyClipboard {host}", r.ok, detail)
    ok &= report(
        f"FoamyClipboard {host}: a cancelled read's wl-paste is gone",
        len(pids) == 1 and pids[0].isdigit() and gone(pids[0]),
        str(pids),
    )
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
