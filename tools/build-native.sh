#!/bin/bash
# Build a plugin's native helper with the plugin's own copy of the build tool
# (kit/native/build-native.sh, synced by FoamyNative):
#   tools/build-native.sh <plugin-dir> [--verify [--out DIR] | --test] [--crate DIR] [--bin NAME]
# The plugin's copy is the one its README, CI and native.pin name, so this is
# only a shortcut from the foamy-kit checkout. See README.md, "Native helpers".
set -euo pipefail
plugin=${1:?usage: tools/build-native.sh <plugin-dir> [--verify [--out DIR] | --test] [--crate DIR] [--bin NAME]}
tool="$plugin/kit/native/build-native.sh"
if [[ ! -f $tool || -L $tool ]]; then
  echo "build-native: $plugin has no kit/native/build-native.sh; sync it first (sync.sh $plugin --add FoamyNative)" >&2
  exit 1
fi
exec bash "$tool" "$@"
