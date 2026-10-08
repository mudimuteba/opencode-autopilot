---
description: Regenerate board artifacts and report a compact execution recap.
agent: build
---

Load the `board` skill and apply `$ARGUMENTS` as optional recap focus.

Regenerate the HTML board with `python3 board/render.py`. Then regenerate or
capture the terminal board snapshot at exactly 80 columns using the repository's
board tooling. Summarize completed, active, ready, and blocked cards; include the
HTML output path and the 80-column snapshot in the response. Do not alter product
code.
