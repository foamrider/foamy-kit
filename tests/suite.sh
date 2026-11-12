#!/bin/bash
# foamy-kit's own tests, run by tests/validate.sh after the linters.
#   tests/suite.sh          every test: tests/run-all.sh (needs qs, the Omarchy
#                           4.5 shell, rustup; see run-all.sh)
#   tests/suite.sh --ci     the tests that need neither Quickshell nor the
#   tests/suite.sh --fast   Omarchy host: node, sync/check, image compare
set -uo pipefail
cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" || exit 1
if [[ $# -eq 0 ]]; then
  exec bash run-all.sh
fi
for arg in "$@"; do
  [[ $arg == --ci || $arg == --fast ]] || {
    echo "suite.sh: unknown argument $arg" >&2
    exit 2
  }
done
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
run python3 -I test_validate.py
run python3 -I test_compare.py
run python3 -I test_clipboard.py
echo "SKIP the Quickshell, Omarchy host and Rust tests (run tests/validate.sh without --ci/--fast)"
exit $status
