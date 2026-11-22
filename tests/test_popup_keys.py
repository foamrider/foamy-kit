#!/usr/bin/env python3
"""FoamyPopup gives the keys back to its body when Settings hides
(tests/qml/PopupKeys.qml) on 4.5: a popup closed on Settings and opened
again closes on Esc; Esc on Settings goes back and the next Esc closes; a
field focused on the page when it hides; a plugin's own refocus in
onHidden still wins. Real keys through the host's KeyboardPanel."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import harness, run_shell, synced_demo  # noqa: E402


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    results = [
        run_shell("PopupKeys.qml", host, plugin, host, env={"FOAMY_TAG": host})
        for host in harness.available_hosts(what="popup keys")
    ]
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
