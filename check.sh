#!/bin/bash
# Verify plugins: one kit version everywhere, unedited stamped files, and the
# foamy design lint (see DESIGN.md "Lint").
#   ./check.sh ../foamy-*            [--lint-only] [--no-lint] [--allow-unsynced]
set -euo pipefail
exec python3 -I "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/tools/foamykit.py" check "$@"
