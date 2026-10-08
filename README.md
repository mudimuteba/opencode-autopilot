# opencode-autopilot

**Add tasks, walk away, get merged PRs with proof — native to opencode.**

Inspired by [super-board](https://github.com/EricTechPro/super-board), the autonomous
build → QA → review loop for Claude Code, and worked with the discipline of
[OhMyOpenCode's Sisyphus](https://github.com/code-yeongyu/oh-my-openagent):
intent-gated, delegated, todo-driven, verified. This repo ports that idea to opencode
as four layers that run — and maintain — themselves.

## The four layers

1. **Board.** `board/todos.jsonl` holds one complete card per line
   (`Backlog → Ready → Building → QA → Review → Blocked → Done`).
   `board/store.py` edits it atomically; `board/render.py` renders the
   self-contained kanban at `dist/board.html`.
2. **Runner.** `/board run` drains `Ready` through isolated build → QA → review
   lanes (`.opencode/commands/board/`, `board/lanes/`), merging only through
   `board/merge-gate.sh` — locked, re-verified, pinned to the reviewed commit.
3. **Worker.** Sisyphus, provided by the `oh-my-openagent` plugin declared in
   `opencode.json`. `.opencode/agents/ultraworker.md` records the working
   contract and defers to the plugin — the prompt is never forked here, so the
   worker cannot go stale.
4. **Self-maintenance.** `board/versions.json` pins last-verified dependency
   versions under a `latest` policy; `sync-deps.sh` reports drift and refreshes;
   a launchd agent refreshes weekly; a native plugin writes a freshness marker
   at every session start and enforces the Bash guards.

## Install

Requirements are Python 3.9+ and opencode. Everything else is standard library
or OS-provided — no packages to install.

```sh
git clone https://github.com/mudimuteba/opencode-autopilot.git
cd opencode-autopilot
opencode
```

Restart opencode after changing `opencode.json` or files under `.opencode/`
because configuration is loaded at startup.

## Quickstart

```sh
python3 board/store.py list
python3 board/store.py add "Document release checks" --status Ready --lane Quality
python3 board/store.py show sample-001
python3 board/store.py move sample-001 Building --lane Product
```

Then open `dist/board.html`, or run `/board status` and `/board run` inside opencode.

## How it works

`board/todos.jsonl` stores one complete card per line. `add` appends a record.
`list` and `show` read without changing. `move` updates a card and rewrites the
file through `todos.jsonl.tmp` followed by an atomic rename. Moving a card to
`Done` records its `closed` timestamp; moving it elsewhere clears it.

If `board/todos.jsonl` is missing, the first store command seeds three sample
cards. Merge defaults live in `board/config.json`. Lane contracts live in
`board/lanes/`; the orchestrator contract in `.opencode/skills/board/`.

## Worker

The project's worker is **Sisyphus**, provided by the `oh-my-openagent`
plugin declared in `opencode.json` (upstream
`code-yeongyu/oh-my-openagent`). `.opencode/agents/ultraworker.md` records
the working contract and defers to the plugin — the prompt is never forked
here, so the worker cannot go stale.

## Dependency freshness

`board/versions.json` records the last verified version of every dependency
with policy `latest`:

```sh
bash board/sync-deps.sh --check   # read-only drift report (offline-safe)
bash board/sync-deps.sh --apply --yes  # refresh plugin cache, then restart opencode
```

`board/validate.sh` runs the check on every pass and warns on drift without
failing. After `--apply`, update the `verified` pin in `board/versions.json`.

## Automation

Three pieces keep the repo on latest without hand-holding:

```sh
bash board/install-launchd.sh            # weekly refresh, Sundays 04:00 (macOS)
bash board/install-launchd.sh --uninstall
```

- **Weekly refresh.** The launchd agent runs `sync-deps.sh --apply --yes`
  outside sessions. `--apply` refuses while opencode processes run (pgrep
  guard), so a scheduled refresh only takes effect on the next opencode start.
- **Startup marker.** `.opencode/plugin/board.js` (native, auto-discovered —
  no extra dependency) compares the cached worker against the verified pin at
  session start and writes `dist/.freshness`, which `/board status` prints.
- **Native guards.** The same plugin enforces the three Bash guards
  (`rm` outside the repo, force-push to `main`, `.env` reads) by throwing in
  `tool.execute.before`, and `opencode.json` declares the `.env` read deny in
  `permission`.
