#!/bin/bash
# board/install-launchd.sh [--uninstall]
# Installs the weekly plugin-cache refresh agent (Sundays 04:00) or removes it.
# macOS only. The agent refuses to clear the cache while opencode runs
# (see the pgrep guard in sync-deps.sh --apply), so scheduled refreshes only
# take effect on the next opencode start.
# Written for bash 3.2 (stock macOS).

set -euo pipefail

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

label="com.opencode-autopilot.sync-deps"
target_dir="$HOME/Library/LaunchAgents"
target="$target_dir/$label.plist"
uid_now="$(id -u)"

if [ "${1:-}" = "--uninstall" ]; then
  launchctl bootout "gui/$uid_now" "$target" 2>/dev/null \
    || launchctl unload -w "$target" 2>/dev/null || true
  rm -f "$target"
  printf 'OK: %s uninstalled\n' "$label"
  exit 0
fi

if [ "$(uname)" != "Darwin" ]; then
  printf 'REFUSED: launchd installer is macOS-only (Linux: port the schedule to a systemd user timer)\n' >&2
  exit 1
fi

mkdir -p "$target_dir"
python3 - "$repo_root/board/com.opencode-autopilot.sync-deps.plist" "$target" "$repo_root" "$HOME" <<'EOF'
import sys
src, dest, root, home = sys.argv[1:5]
with open(src, encoding="utf-8") as handle:
    text = handle.read()
text = text.replace("__REPO_ROOT__", root).replace("__HOME__", home)
with open(dest, "w", encoding="utf-8") as handle:
    handle.write(text)
EOF

launchctl bootstrap "gui/$uid_now" "$target" 2>/dev/null \
  || launchctl load -w "$target" 2>/dev/null || true
if launchctl print "gui/$uid_now/$label" >/dev/null 2>&1; then
  printf 'OK: %s installed (Sundays 04:00)\n' "$label"
else
  printf 'FAIL: agent not listed after load\n' >&2
  exit 1
fi
