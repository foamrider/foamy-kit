#!/bin/bash
# The one validation command: kit checks, linters, formatters, native helper
# tests and the repository's own tests (tests/suite.sh). Nonzero on failure.
#   tests/validate.sh [--ci] [--fast] [--only|--skip CHECKS] [--update-baseline [CHECKS]] [--list]
# Run `mise install` first (mise.toml pins the tools). kit/tooling/validate.py
# does the work; see foamy-kit's README, "Tooling".
set -euo pipefail
exec python3 -I "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../kit/tooling/validate.py" "$@"
