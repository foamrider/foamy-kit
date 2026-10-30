#!/bin/bash
# Run every foamy-kit test. Needs qs (Quickshell), node, python3, git, and
# the hosts: 4.0.6 at /usr/share/omarchy/shell and 4.5-rc2 at
# /tmp/omarchy-ref/v45/shell (override with FOAMY_HOST_40 / FOAMY_HOST_45).
set -uo pipefail
cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
status=0
run() {
  echo "== $*"
  "$@" || status=1
}
run node prefs.test.cjs
run python3 -I test_sync_check.py
run python3 -I test_geometry.py
run python3 -I test_runtime.py
run python3 -I test_features.py
run python3 -I test_ipc_cli.py
run python3 -I test_harness.py
run python3 -I test_band.py
run python3 -I test_preview.py
run python3 -I test_trio.py
echo
if (( status == 0 )); then echo "ALL TESTS PASSED"; else echo "SOME TESTS FAILED"; fi
exit $status
