#!/usr/bin/env python3
"""A plain SafeTextField (tests/qml/TextField.qml) on 4.5: paste races,
undo and redo, scrolling, the primary selection, maximumLength, refused
pastes, Shift+Insert, Tab and Return, through real keys, the mouse and
kit/clipboard.sh with the hostenv.clipboard_fakes() stand-ins (never the
real clipboard). The masked field: tests/test_masked.py."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import harness, run_shell, synced_demo  # noqa: E402


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo(["SafeTextField"])
    results = [
        # The scene reads the stand-in's argv file synchronously.
        run_shell(
            "TextField.qml", host, plugin, host, env={"QML_XHR_ALLOW_FILE_READ": "1"}, clipboard=True, timeout=120
        )
        for host in harness.available_hosts(what="text field")
    ]
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
