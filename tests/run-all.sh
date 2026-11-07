#!/bin/bash
# Run every foamy-kit test. Needs qs (Quickshell), node, python3, git, and
# the Omarchy 4.5 shell at /usr/share/omarchy/shell (override with
# FOAMY_HOST_45). 4.0 is opt-in: set FOAMY_HOST_40 to a 4.0 shell directory,
# else every 4.0 run prints a SKIP line.
# test_native.py also needs rustup with the toolchain in
# kit/rust/rust-toolchain.toml, file(1), and qemu-aarch64 binfmt for the
# aarch64 runs (each skipped with a SKIP line when missing).
set -uo pipefail
cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
status=0
run() {
  echo "== $*"
  "$@" || status=1
}
run node prefs.test.cjs
run node native.test.cjs
run python3 -I test_sync_check.py
run python3 -I test_native.py
run python3 -I test_geometry.py
run python3 -I test_runtime.py
run python3 -I test_features.py
run python3 -I test_ipc_cli.py
run python3 -I test_compare.py
run python3 -I test_harness.py
run python3 -I test_band.py
run python3 -I test_menu.py
run python3 -I test_components.py
run python3 -I test_rows.py
run python3 -I test_wheel.py
run python3 -I test_preview.py
run python3 -I test_trio.py
echo
if (( status == 0 )); then echo "ALL TESTS PASSED"; else echo "SOME TESTS FAILED"; fi
exit $status
