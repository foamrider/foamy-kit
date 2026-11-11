#!/bin/bash
# Run every foamy-kit test. Needs qs (Quickshell), node, python3, git, and
# the Omarchy 4.5 shell at /usr/share/omarchy/shell (override with
# FOAMY_HOST_45). Omarchy 4.0 is not supported (kit 0.9.0).
# test_native.py also needs rustup with the toolchain in
# kit/rust/rust-toolchain.toml, file(1), and qemu-aarch64 binfmt for the
# aarch64 runs (each skipped with a SKIP line when missing).
set -uo pipefail
cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" || exit 1
status=0
run() {
  echo "== $*"
  "$@" || status=1
}
run node prefs.test.cjs
run node native.test.cjs
run node text.test.cjs
run node schedule.test.cjs
run node i18n.test.cjs
run python3 -I test_sync_check.py
run python3 -I test_native.py
run python3 -I test_geometry.py
run python3 -I test_runtime.py
run python3 -I test_features.py
run python3 -I test_lifecycle.py
run python3 -I test_ipc_cli.py
run python3 -I test_compare.py
run python3 -I test_harness.py
run python3 -I test_isolation.py
run python3 -I test_helpers.py
run python3 -I test_i18n_runtime.py
run python3 -I test_band.py
run python3 -I test_menu.py
run python3 -I test_components.py
run python3 -I test_rows.py
run python3 -I test_schedule.py
run python3 -I test_wheel.py
run python3 -I test_preview.py
run python3 -I test_trio.py
echo
if (( status == 0 )); then echo "ALL TESTS PASSED"; else echo "SOME TESTS FAILED"; fi
exit $status
