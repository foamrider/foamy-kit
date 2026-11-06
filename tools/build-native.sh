#!/bin/bash
# Build a plugin's native helper for x86_64 and aarch64 (static musl), install
# it atomically as bin/<arch>/<binary> and write <crate>/native.pin.
#   tools/build-native.sh <plugin-dir> [--verify | --test] [--crate DIR] [--bin NAME]
# --verify rebuilds in a fresh target dir and compares bytes with the committed
# binaries; --test runs cargo fmt --check, clippy -D warnings and test. Cargo
# output goes to ${FOAMY_NATIVE_CACHE:-~/.cache/foamy-native}/foamy-<plugin>,
# never into the plugin. See README.md, "Native helpers".
set -euo pipefail
exec python3 -I "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/foamykit.py" native "$@"
