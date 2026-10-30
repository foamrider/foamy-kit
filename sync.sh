#!/bin/bash
# Copy foamy-kit components into plugins as stamped regular files.
#   ./sync.sh <plugin-dir>... [--components FoamyPopup,FoamyI18n] [--dry-run] [--force]
# Without --components a plugin keeps the set in its foamy-kit.lock (all
# components on first sync). Dependencies are added automatically.
set -euo pipefail
exec python3 -I "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/tools/foamykit.py" sync "$@"
