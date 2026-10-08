# opencode-board

A small, opencode-native project board backed by an append-friendly JSONL file.

## Install

Requirements are Python 3.9+ and opencode. The board store uses only the Python standard library, so there are no packages to install.

Clone or copy the repository, then open its root in opencode. Restart opencode after changing `opencode.json` or files under `.opencode/` because configuration is loaded at startup.

## Quickstart

```sh
python3 board/store.py list
python3 board/store.py add "Document release checks" --status Ready --lane Quality
python3 board/store.py show sample-001
python3 board/store.py move sample-001 Building --lane Product
```

Available statuses are `Backlog`, `Ready`, `Building`, `QA`, `Review`, `Blocked`, and `Done`.

## How it works

`board/todos.jsonl` stores one complete card per line. `add` appends a record. `list` and `show` read records without changing them. `move` updates a card and rewrites the file through `todos.jsonl.tmp` followed by an atomic rename. Moving a card to `Done` records its `closed` timestamp; moving it elsewhere clears that timestamp.

If `board/todos.jsonl` is missing, the first store command seeds three sample cards. Project verification and merge defaults live in `board/config.json`. The `.opencode/skills/board/` and `.opencode/commands/board/` directories are reserved for later board integrations.

## Install from Git

```sh
git clone https://github.com/mudimuteba/opencode-board.git
cd opencode-board
opencode
```

## Publish

Create an empty remote repository, replace the placeholder URL below, then publish the local project:

```sh
git init
git remote add origin https://github.com/mudimuteba/opencode-board.git
git add .
git commit -m "Initial publish"
git branch -M main
git push -u origin main
```
