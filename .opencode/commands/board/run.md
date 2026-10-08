---
description: Drain Ready board cards through isolated build, QA, and review lanes.
agent: build
---

Load the `board` skill and run the board, applying `$ARGUMENTS` as scope or
priority guidance.

Drain Ready in dependency-safe waves until no eligible Ready card remains.
Dispatch each card with `task(category=deep)` through these lanes:

1. `board-build` implements in an isolated worktree under
   `.opencode/worktrees/`.
2. `board-qa` verifies acceptance criteria and records evidence.
3. `board-review` independently reviews the diff and evidence before merge.

Keep lane ownership separate, respect Blocked-by edges, and update card state at
each transition. Merge only through the repository merge gate. The orchestrator
coordinates agents and board state; it never writes product code.
