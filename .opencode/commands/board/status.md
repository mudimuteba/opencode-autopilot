---
description: Show the current board and summarize actionable work.
agent: build
---

Load the `board` skill. Apply any user focus from `$ARGUMENTS`.

Current board:

!`python3 board/store.py list`

Dependency freshness (written at session start by the board plugin):

!`cat dist/.freshness 2>/dev/null || echo "freshness unknown — run bash board/sync-deps.sh --check"`

Render a concise status summary from the interpolated board above. Group cards by
column, call out Ready cards that can start now, and identify blocked cards with
their blockers. Do not change board state or product code.
