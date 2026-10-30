#!/usr/bin/env python3
"""Why FoamyPrefs sends arrays to setBarWidget with a leading space: probe how
`qs ipc call --` (the path omarchy-shell takes on 4.0, and on 4.5 when the
socket is down) passes JSON arguments to a setBarWidget-shaped handler."""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import harness, report  # noqa: E402

SHELL = """import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
  IpcHandler {
    target: "shell"
    function setBarWidget(id: string, key: string, valueJson: string, selectorJson: string): string {
      try { return JSON.stringify({ id: id, key: key, value: JSON.parse(valueJson), selector: JSON.parse(selectorJson) }) }
      catch (e) { return "invalid widget setting: " + e }
    }
  }
  Component.onCompleted: console.log("FOAMY UP")
}
"""


def main():
    ok = True
    with harness.Run("4.0", SHELL, prefix="foamy-kit-ipc-cli-") as run:
        run.start()
        by_id = Path(run.env["XDG_RUNTIME_DIR"]) / "quickshell/by-id"
        for _ in range(100):
            if by_id.is_dir() and any(by_id.iterdir()) and "FOAMY UP" in (run.base / "qs.log").read_text(errors="replace"):
                break
            time.sleep(0.1)
        instance = next(by_id.iterdir()).name

        def call(value):
            result = subprocess.run(["qs", "ipc", "-i", instance, "call", "--", "shell", "setBarWidget", "foamy.x", "k", value, "{}"],
                                    env=run.env, capture_output=True, text=True, timeout=10)
            return result.stdout.strip()

        bare = call("[1,2]")
        ok &= report("qs ipc rejects a bare JSON array argument (the reason for the workaround)", not bare.startswith("{"), bare.splitlines()[0] if bare else "")
        spaced = call(" [1,2]")
        try:
            ok &= report("a leading space carries the array through qs ipc", json.loads(spaced)["value"] == [1, 2], spaced)
        except ValueError:
            ok &= report("a leading space carries the array through qs ipc", False, spaced)
        for value, expected in (('{"a":[1]}', {"a": [1]}), ("-5", -5), ("true", True), ('"[x]"', "[x]")):
            out = call(value)
            try:
                ok &= report(f"qs ipc passes {value} unchanged", json.loads(out)["value"] == expected, out)
            except ValueError:
                ok &= report(f"qs ipc passes {value} unchanged", False, out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
