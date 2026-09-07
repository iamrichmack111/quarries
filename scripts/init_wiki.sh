#!/usr/bin/env bash
set -euo pipefail
REPO="${REPO:-iamrichmack111/quarries}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v gh >/dev/null || { echo "GitHub CLI (gh) is required." >&2; exit 1; }
gh auth status >/dev/null

gh repo edit "$REPO" --enable-wiki=true
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if ! git clone "git@github.com:${REPO}.wiki.git" "$TMP/wiki" 2>/dev/null; then
  mkdir -p "$TMP/wiki"
  git -C "$TMP/wiki" init
  git -C "$TMP/wiki" remote add origin "git@github.com:${REPO}.wiki.git"
fi
rsync -a --delete "$ROOT/wiki/" "$TMP/wiki/"
cd "$TMP/wiki"
git add .
if ! git diff --cached --quiet; then
  git commit -m "docs: initialize Quarries wiki"
fi
git branch -M master
git push -u origin master

echo "Wiki initialized: https://github.com/${REPO}/wiki"
