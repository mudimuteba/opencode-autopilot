---
description: Audit board cards for actionable acceptance criteria and dependencies.
agent: build
---

Load the `board` skill. Audit the board using `$ARGUMENTS` as an optional card or
column filter.

Flag every card with vague or missing acceptance criteria. Acceptance criteria
must be observable and sufficient for QA to return pass or fail. Also flag every
`Blocked-by` value that is absent, ambiguous, malformed, or unreadable as a card
reference. Report card IDs, exact defects, and the smallest correction. Do not
change board state or product code.
