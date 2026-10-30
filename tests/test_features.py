#!/usr/bin/env python3
"""kit 0.2.0 features under both hosts (tests/qml/Features.qml): icons,
tokens, textKey arity, SafeTextField.maximumLength, FoamyPrefsQueue inline
and CLI (fake omarchy / omarchy-shell on PATH, never the real ones), IPC
prefer/others/call, FoamyIpcPreference, FoamyPeerIpc, FoamySettingsState and
the private D-Bus session."""
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT_ROOT, harness, report, synced_demo  # noqa: E402

FAKE_OMARCHY = """#!/bin/bash
printf '%s\\n' "omarchy $*" >> "$FOAMY_CALLS"
sleep 0.3
case "$*" in *boom*) echo "fake failure" >&2; exit 1 ;; esac
exit 0
"""
FAKE_OMARCHY_SHELL = """#!/bin/bash
if [[ ${1:-} == shell && ${2:-} == setBarWidget ]]; then
  printf 'omarchy-shell %s %s %s %s |%s| %s\\n' "$1" "$2" "$3" "$4" "$5" "$6" >> "$FOAMY_CALLS"
  echo ok
  exit 0
fi
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
    for i in range(50):
        shutil.copyfile(plugin / "preview/artwork.png", covers / f"cover-{i}.png")
    shell = (KIT_ROOT / "tests/qml/Features.qml").read_text()
    r = harness.Run(host, shell, plugin=plugin, extra={"FileViewProbe.qml": PROBE}, prefix=f"foamy-kit-features-{host}-",
                    fakebin={"omarchy": FAKE_OMARCHY, "omarchy-shell": FAKE_OMARCHY_SHELL})
    calls = r.base / "calls.log"
    calls.write_text("")
    r.env.update({"FOAMY_CALLS": str(calls), "FOAMY_BASE": str(r.base),
                  "FOAMY_LIVE_BUS": os.environ.get("DBUS_SESSION_BUS_ADDRESS", ""), "QML_XHR_ALLOW_FILE_READ": "1"})
    r.run(timeout=60)
    detail = next((l.split("qml: ", 1)[-1] for l in r.log.splitlines() if "FOAMY RESULT" in l), "no result")
    ok = report(f"features {host}", r.ok, detail)
    if not ok:
        print("\n".join("    " + l for l in (r.failures() or r.log.splitlines()[-30:])))
    r.cleanup()
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return ok


def main():
    harness.install_signal_cleanup()
    results = [run("4.0"), run("4.5")]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
