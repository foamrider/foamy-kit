#!/bin/bash
# Commit PNG screenshots to a plugin repo's orphan `pr-assets` branch and
# print raw.githubusercontent.com URLs for a PR description.
#
#   preview/publish-screenshots.sh [-m message] <plugin-repo> <png-dir> <subdir>
#
# Works in a temporary git worktree, so the plugin's working tree, index and
# current branch are never touched. Creates `pr-assets` as an orphan branch
# (empty history, screenshots only) unless it exists locally or on origin.
# Never pushes: it prints the push command for you to run.
set -euo pipefail

message=""
if [[ ${1:-} == -m ]]; then
  message=${2:?-m needs a message}
  shift 2
fi
[[ $# == 3 ]] || { echo "usage: $0 [-m message] <plugin-repo> <png-dir> <subdir>" >&2; exit 2; }

repo=$(git -C "$1" rev-parse --show-toplevel)
png_dir=$(cd "$2" && pwd)
subdir=${3%/}
branch=pr-assets

[[ -n $subdir && $subdir != /* && $subdir != *..* && $subdir =~ ^[A-Za-z0-9._/-]+$ ]] \
  || { echo "subdir must be a relative path of letters, digits, . _ - /: $subdir" >&2; exit 2; }
shopt -s nullglob
pngs=("$png_dir"/*.png)
(( ${#pngs[@]} > 0 )) || { echo "no PNGs in $png_dir" >&2; exit 1; }

worktree=$(mktemp -d "${TMPDIR:-/tmp}/foamy-pr-assets.XXXXXX")
cleanup() {
  git -C "$repo" worktree remove --force "$worktree" >/dev/null 2>&1 || rm -rf "$worktree"
  git -C "$repo" worktree prune >/dev/null 2>&1 || true
}
trap cleanup EXIT

if git -C "$repo" show-ref --verify --quiet "refs/heads/$branch"; then
  git -C "$repo" worktree add --quiet "$worktree" "$branch"
elif git -C "$repo" show-ref --verify --quiet "refs/remotes/origin/$branch"; then
  git -C "$repo" worktree add --quiet -b "$branch" "$worktree" "origin/$branch"
else
  git -C "$repo" worktree add --quiet --orphan -b "$branch" "$worktree"
fi

mkdir -p "$worktree/$subdir"
cp -- "${pngs[@]}" "$worktree/$subdir/"
git -C "$worktree" add -- "$subdir"
if git -C "$worktree" diff --cached --quiet; then
  echo "pr-assets: $subdir is already up to date"
else
  git -C "$worktree" commit --quiet -m "${message:-chore(assets): screenshots for $subdir}"
  echo "pr-assets: committed ${#pngs[@]} file(s) to $branch:$subdir ($(git -C "$worktree" rev-parse --short HEAD))"
fi

remote=$(git -C "$repo" remote get-url origin 2>/dev/null || true)
slug=$(sed -E -n 's#^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^/]+/[^/]+)$#\2#p' <<<"$remote")
slug=${slug%.git}
if [[ -z $slug ]]; then
  echo "origin is not a GitHub remote ($remote); URLs use OWNER/REPO" >&2
  slug="OWNER/REPO"
fi
echo
for png in "${pngs[@]}"; do
  echo "https://raw.githubusercontent.com/$slug/$branch/$subdir/$(basename "$png")"
done
echo
echo "Not pushed. Publish with:"
echo "  git -C $repo push origin $branch"
