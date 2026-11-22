#!/usr/bin/env python3
"""FoamyBoundedCollector (tests/qml/Collector.qml) on 4.5, on a real
child's stdout and stderr: kept whole under the bound, cut to the bound's
start past it (4 MiB, many pipe reads) with `truncated`, kept in order
across reads, never half a surrogate pair, cleared per run."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import harness, run_shell, synced_demo  # noqa: E402


def main():
    harness.install_signal_cleanup()
    plugin = synced_demo(["FoamyBoundedCollector"])
    results = [run_shell("Collector.qml", host, plugin, host) for host in harness.available_hosts(what="collector")]
    shutil.rmtree(plugin.parent, ignore_errors=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
