#!/usr/bin/env python3
"""Click-away (tests/qml/ClickAway.qml) on 4.5: a click on a
FoamyPopup body's, a Flickable's or a settings page's empty space takes the
keys from a SafeTextField or SafeTextArea and gives them to the key home;
real controls, drags and the wheel keep working."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import harness, run_shell, synced_demo  # noqa: E402


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo()
    results = [
        run_shell("ClickAway.qml", host, plugin, host, env={"FOAMY_TAG": host})
        for host in harness.available_hosts(what="click-away")
    ]
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
