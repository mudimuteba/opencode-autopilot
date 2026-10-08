#!/bin/bash

set -euo pipefail

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

pass() {
  printf 'PASS: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

check_store() {
  python3 -m py_compile board/store.py board/render.py board/collect.py &&
    python3 board/store.py list >/dev/null
}

check_render() {
  python3 board/render.py &&
    test -f dist/board.html
}

check_commands() {
  test -f .opencode/skills/board/SKILL.md || return 1
  test -f .opencode/agents/ultraworker.md || return 1

  for command in status run lint recap; do
    test -f ".opencode/commands/board/$command.md" || return 1
  done
}

check_gate() {
  bash -n board/merge-gate.sh
}

check_hooks() {
  test -f .opencode/plugin/board.js || return 1
  grep -q 'tool.execute.before' .opencode/plugin/board.js || return 1
  node --check .opencode/plugin/board.js || return 1
  grep -qF '"*.env": "deny"' opencode.json || return 1
}

check_configs() {
  python3 -c 'import json, sys; [json.load(open(path, encoding="utf-8")) for path in sys.argv[1:]]' \
    opencode.json board/config.json board/versions.json
}

check_deps() {
  # Advisory only: sync-deps.sh --check always exits 0 (offline-safe).
  bash board/sync-deps.sh --check || true
}

if check_store; then pass store; else fail store; fi
if check_render; then pass render; else fail render; fi
if check_commands; then pass commands; else fail commands; fi
if check_gate; then pass gate; else fail gate; fi
if check_hooks; then pass hooks; else fail hooks; fi
if check_configs; then pass configs; else fail configs; fi
if check_deps; then pass deps; else fail deps; fi
