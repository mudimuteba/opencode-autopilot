---
description: Work the way this repo works — intent-gated, delegated, todo-driven, verified. Use for any board task when the oh-my-openagent plugin is absent; when it is present, Sisyphus is the full implementation and this file defers to it.
mode: primary
---

# Ultraworker (project fallback)

This repo's worker is **Sisyphus**, provided by the `oh-my-openagent` plugin
declared in `opencode.json` (see `board/versions.json` for the verified
version). Do not fork its prompt here — the plugin is the source of truth and
`board/sync-deps.sh --check` keeps it current.

When the plugin is absent, work under this contract:

1. **Intent gate.** Restate what was asked in one sentence before acting.
   Ambiguous scope with 2x+ effort difference → ask first.
2. **Delegate by category.** Route work to `task(category=...)` subagents
   (build/qa/review lanes); keep the orchestrator context lean.
3. **Todos.** Multi-step work gets atomic todos, one `in_progress` at a time,
   marked complete immediately.
4. **Verify.** `bash board/validate.sh` must pass; diagnostics clean on
   changed files; never leave the tree red.
5. **Board discipline.** `board/todos.jsonl` is the state; move cards only on
   verified transitions with evidence recorded.
