#!/bin/bash
# board/sync-deps.sh --check | --apply [--yes]
# Keeps opencode-board on the latest versions recorded in board/versions.json.
# --check is read-only and advisory: it never fails on missing tools or
# network (prints WARN, exits 0) so board/validate.sh can call it safely.
# --apply refreshes the opencode plugin cache for oh-my-openagent so the next
# opencode start re-resolves `latest`. Requires --yes. The cache regenerates
# automatically; rollback is "restart opencode".
# Written for bash 3.2 (stock macOS).

set -euo pipefail

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

CACHE_DIR="$HOME/.cache/opencode/packages/oh-my-openagent@latest"
CACHED_PKG="$CACHE_DIR/node_modules/oh-my-openagent/package.json"

installed_version() {
  if [ -f "$CACHED_PKG" ]; then
    python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "$CACHED_PKG" 2>/dev/null || echo UNKNOWN
  else
    echo MISSING
  fi
}

latest_version() {
  if command -v npm >/dev/null 2>&1; then
    npm view oh-my-openagent version 2>/dev/null || echo UNKNOWN
  else
    echo UNKNOWN
  fi
}

verified_version() {
  python3 -c 'import json; print(json.load(open("board/versions.json", encoding="utf-8"))["deps"]["oh-my-openagent"]["verified"])' 2>/dev/null || echo UNKNOWN
}

cmd_check() {
  local installed latest verified
  installed="$(installed_version)"
  latest="$(latest_version)"
  verified="$(verified_version)"
  printf 'CURRENT: %s\n' "$installed"
  printf 'VERIFIED: %s\n' "$verified"
  printf 'LATEST: %s\n' "$latest"
  if [ "$latest" = UNKNOWN ]; then
    printf 'WARN: registry unreachable — cannot confirm latest (offline-safe, not a failure)\n'
  elif [ "$installed" = "$latest" ]; then
    printf 'OK: plugin cache matches registry latest\n'
  else
    printf 'WARN: drift detected — run `bash board/sync-deps.sh --apply --yes` then restart opencode\n'
  fi
}

cmd_apply() {
  if [ "${1:-}" != "--yes" ]; then
    printf 'REFUSED: --apply needs --yes (would remove %s)\n' "$CACHE_DIR" >&2
    exit 1
  fi
  rm -rf "$CACHE_DIR"
  printf 'OK: plugin cache cleared — restart opencode to re-resolve latest, then run --check\n'
}

case "${1:-}" in
  --check) cmd_check ;;
  --apply) cmd_apply "${2:-}" ;;
  *) printf 'usage: board/sync-deps.sh --check | --apply [--yes]\n' >&2; exit 1 ;;
esac
