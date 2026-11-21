#!/usr/bin/env python3
"""kit 0.2.0 features on 4.5 (tests/qml/Features.qml): icons, textKey
arity, SafeTextField.maximumLength, FoamyPrefsQueue inline and CLI (fake
omarchy / omarchy-shell on PATH, never the real ones), IPC
prefer/others/call, FoamyIpcPreference, FoamyPeerIpc (with its failures:
a missing target, the process limit) and FoamySettingsState, plus the
expiry of a pending value the host never reflects."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo  # noqa: E402

FAKE_OMARCHY = """#!/bin/bash
printf '%s\\n' "omarchy $*" >> "$FOAMY_CALLS"
sleep 0.3
exit 0
"""
FAKE_OMARCHY_SHELL = """#!/bin/bash
case "${1:-}" in
  foamy.gone) echo "Target not found: $1"; exit 0 ;;
  foamy.slow) printf '%s\\n' "omarchy-shell $*" >> "$FOAMY_CALLS" ;;
esac
echo "cli: $*"
"""
PROBE = """import QtQuick
// Reads the fake CLIs' call log synchronously (QML_XHR_ALLOW_FILE_READ=1).
QtObject {
  property string path: ""
  function lines() {
    var request = new XMLHttpRequest()
    request.open("GET", "file://" + path, false)
    request.send(null)
    return String(request.responseText || "").split("\\n").filter(function(line) { return line !== "" })
  }
}
"""


def run(host):
    plugin = synced_demo()
    covers = plugin / "preview/covers"
    covers.mkdir()
    for i in range(3):
        shutil.copyfile(plugin / "preview/artwork.png", covers / f"cover-{i}.png")
    shell = (KIT_ROOT / "tests/qml/Features.qml").read_text()
    r = harness.Run(
        host,
        shell,
        plugin=plugin,
        extra={"FileViewProbe.qml": PROBE},
        prefix=f"foamy-kit-features-{host}-",
        fakebin={"omarchy": FAKE_OMARCHY, "omarchy-shell": FAKE_OMARCHY_SHELL},
    )
    calls = r.base / "calls.log"
    calls.write_text("")
    r.env.update(
        {
            "FOAMY_CALLS": str(calls),
            "QML_XHR_ALLOW_FILE_READ": "1",
        }
    )
    r.run(timeout=60)
    detail = next((line.split("qml: ", 1)[-1] for line in r.log.splitlines() if "FOAMY RESULT" in line), "no result")
    ok = report(f"features {host}", r.ok, detail)
    if not ok:
        print("\n".join("    " + line for line in (r.failures() or r.log.splitlines()[-30:])))
    r.cleanup()
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return ok


def main():
    harness.install_signal_cleanup()
    results = [run(host) for host in harness.available_hosts(what="features")]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
