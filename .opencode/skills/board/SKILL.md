---
name: board
description: Use when orchestrating board kanban todos Ready Building merge workflows, including dependency waves, isolated lanes, QA, and review.
---

# Board Orchestrator

Operate the board as a coordinator. Read card state and dependencies, plan safe
waves, route each card through independent lanes, and preserve an auditable trail
from Ready to merge.

## Orchestration loop

1. Read the full board before dispatching work.
2. Validate each candidate has testable acceptance criteria and readable
   `Blocked-by` references.
3. Select cards in Ready whose blockers are complete.
4. Partition selected cards into a wave with no shared files, state, or ordering
   hazards. Defer conflicts to a later wave.
5. Dispatch the wave, monitor lane results, and update the board after every
   verified transition.
6. Re-read the board and plan the next wave. Stop when Ready has no eligible
   cards; report remaining blockers rather than spinning.

## Lane routing

Use `task(category=deep)` for every lane. Give each lane the card ID, acceptance
criteria, blocker context, assigned worktree, and required evidence.

- **board-build**: owns implementation in one isolated worktree below
  `.opencode/worktrees/`. It returns the diff and focused verification evidence.
- **board-qa**: owns acceptance testing. It evaluates each criterion as pass or
  fail and returns reproducible evidence; it does not repair failures.
- **board-review**: owns independent review of the diff, acceptance evidence,
  scope, and integration risk. It either approves or returns actionable findings.

Route a failed QA or review result back to `board-build`, then repeat QA and
review. Merge only after both lanes pass and only through the repository merge
gate.

## State discipline

- Move a card to Building only after its build lane has an assigned worktree.
- Keep Blocked-by edges authoritative; never dispatch around an unresolved edge.
- Record lane ownership and evidence before advancing state.
- Keep independent cards parallel and dependent or overlapping cards sequential.
- Preserve failed evidence alongside the corrective cycle.

## Hard boundary

The board orchestrator never writes product code. It may inspect the board,
plan waves, dispatch lanes, update board metadata, and summarize evidence. All
product-code edits belong exclusively to the `board-build` lane in its assigned
worktree.
