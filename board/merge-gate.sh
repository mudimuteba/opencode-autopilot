#!/bin/bash

# Atomic, fail-closed squash merge gate.
# Exit codes: 0 merged, 2 stale/rebase required, 3 human intervention, 4 busy.

set -u

EXIT_REBASE=2
EXIT_HUMAN=3
EXIT_BUSY=4

usage() {
  printf '%s\n' \
    "Usage: board/merge-gate.sh (--match-head SHA | --expect-head SHA) [--message TEXT] SOURCE"
}

fail() {
  code=$1
  shift
  printf 'merge-gate: %s\n' "$*" >&2
  exit "$code"
}

expected_head=${EXPECT_HEAD:-}
commit_message=
source_ref=

while [ "$#" -gt 0 ]; do
  case "$1" in
    --match-head|--expect-head)
      [ "$#" -ge 2 ] || { usage >&2; exit "$EXIT_HUMAN"; }
      expected_head=$2
      shift 2
      ;;
    --message)
      [ "$#" -ge 2 ] || { usage >&2; exit "$EXIT_HUMAN"; }
      commit_message=$2
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --*)
      usage >&2
      fail "$EXIT_HUMAN" "unknown option: $1"
      ;;
    *)
      [ -z "$source_ref" ] || { usage >&2; fail "$EXIT_HUMAN" "only one source is allowed"; }
      source_ref=$1
      shift
      ;;
  esac
done

[ -n "$source_ref" ] || { usage >&2; fail "$EXIT_HUMAN" "SOURCE is required"; }
[ -n "$expected_head" ] || { usage >&2; fail "$EXIT_HUMAN" "--match-head or --expect-head is required"; }

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || fail "$EXIT_HUMAN" "not inside a Git repository"
cd "$repo_root" || fail "$EXIT_HUMAN" "cannot enter repository root"

git_dir=$(git rev-parse --absolute-git-dir 2>/dev/null) || fail "$EXIT_HUMAN" "cannot locate Git directory"
lock_dir="$git_dir/board-merge-gate.lock"
if ! mkdir "$lock_dir" 2>/dev/null; then
  fail "$EXIT_BUSY" "another merge gate holds $lock_dir"
fi

base_head=
gate_state=clean

cleanup() {
  status=$1
  trap - EXIT HUP INT TERM

  if [ "$gate_state" != clean ] && [ -n "$base_head" ]; then
    if git rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
      git merge --abort >/dev/null 2>&1 || true
    fi
    git reset --hard "$base_head" >/dev/null 2>&1 || true
  fi

  rm -f "$lock_dir/verify-commands" >/dev/null 2>&1 || true
  rmdir "$lock_dir" >/dev/null 2>&1 || true
  exit "$status"
}
trap 'cleanup "$?"' EXIT HUP INT TERM

base_head=$(git rev-parse HEAD 2>/dev/null) || fail "$EXIT_HUMAN" "current HEAD is not a commit"
expected_commit=$(git rev-parse "$expected_head^{commit}" 2>/dev/null) || fail "$EXIT_HUMAN" "expected head is not a commit: $expected_head"

if [ "$base_head" != "$expected_commit" ]; then
  fail "$EXIT_REBASE" "base moved: expected $expected_commit, found $base_head"
fi

if [ -n "$(git status --porcelain)" ]; then
  fail "$EXIT_HUMAN" "worktree must be clean"
fi

source_head=$(git rev-parse "$source_ref^{commit}" 2>/dev/null) || fail "$EXIT_REBASE" "source is not a commit: $source_ref"
[ "$source_head" != "$base_head" ] || fail "$EXIT_HUMAN" "source already equals current HEAD"

config_path="$repo_root/board/config.json"
[ -f "$config_path" ] || fail "$EXIT_HUMAN" "missing board/config.json"

verify_file="$lock_dir/verify-commands"
if ! python3 - "$config_path" "$verify_file" <<'PY'
import json
import sys

config_path, output_path = sys.argv[1:]
with open(config_path, encoding="utf-8") as config_file:
    config = json.load(config_file)

commands = config.get("verify_commands")
if not isinstance(commands, list) or not commands:
    raise SystemExit("verify_commands must be a non-empty array")
if any(not isinstance(command, str) or not command.strip() or "\n" in command for command in commands):
    raise SystemExit("verify_commands entries must be non-empty, single-line strings")

with open(output_path, "w", encoding="utf-8") as output_file:
    for command in commands:
        output_file.write(command + "\n")
PY
then
  fail "$EXIT_HUMAN" "invalid verify_commands in board/config.json"
fi

gate_state=merge
if ! git merge --no-commit --no-ff "$source_head"; then
  fail "$EXIT_REBASE" "source does not merge cleanly; rebase it onto $base_head"
fi

verify_failed=0
while IFS= read -r verify_command || [ -n "$verify_command" ]; do
  printf 'merge-gate: verify: %s\n' "$verify_command"
  if ! /bin/sh -c "$verify_command"; then
    verify_failed=1
    break
  fi
done < "$verify_file"

if [ "$verify_failed" -ne 0 ]; then
  fail "$EXIT_HUMAN" "verification failed"
fi

git reset --hard "$base_head" >/dev/null 2>&1 || fail "$EXIT_HUMAN" "could not restore base after verification"
gate_state=clean

current_head=$(git rev-parse HEAD 2>/dev/null) || fail "$EXIT_HUMAN" "cannot re-read current HEAD"
[ "$current_head" = "$base_head" ] || fail "$EXIT_REBASE" "base moved during verification"

current_source_head=$(git rev-parse "$source_ref^{commit}" 2>/dev/null) || fail "$EXIT_REBASE" "source disappeared during verification"
[ "$current_source_head" = "$source_head" ] || fail "$EXIT_REBASE" "source moved during verification; retry with its new head"

gate_state=squash
if ! git merge --squash "$source_head"; then
  fail "$EXIT_REBASE" "pinned source no longer squash-merges cleanly"
fi

if git diff --cached --quiet; then
  fail "$EXIT_HUMAN" "squash produced no changes"
fi

[ "$(git rev-parse HEAD 2>/dev/null)" = "$base_head" ] || fail "$EXIT_REBASE" "base moved before commit"

if [ -z "$commit_message" ]; then
  commit_message="board: squash merge $source_ref at $source_head"
fi

if ! git commit -m "$commit_message"; then
  fail "$EXIT_HUMAN" "could not create squash commit"
fi

gate_state=clean
printf 'merge-gate: merged %s at %s\n' "$source_ref" "$source_head"
exit 0
