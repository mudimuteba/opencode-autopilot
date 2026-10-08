#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# ─── How to run ───
# python3 board/render.py --in board/todos.jsonl --out dist/board.html

"""Render the board JSONL store as a self-contained static HTML report."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Final, TypeAlias

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

COLUMNS: Final[tuple[tuple[str, str], ...]] = (
    ("backlog", "Backlog"),
    ("ready", "Ready"),
    ("building", "Building"),
    ("qa", "QA"),
    ("review", "Review"),
    ("blocked", "Blocked"),
    ("done", "Done"),
)
STATUS_KEYS: Final[frozenset[str]] = frozenset(key for key, _ in COLUMNS)


@dataclass(frozen=True, slots=True)
class Todo:
    card_id: str
    title: str
    status: str
    lane: str
    evidence: str
    head_sha: str
    created: str
    closed: str
    bounce_count: int


@dataclass(frozen=True, slots=True)
class BoardData:
    todos: tuple[Todo, ...]
    warnings: tuple[str, ...]


def text_field(record: dict[str, JsonValue], name: str) -> str:
    value = record.get(name, "")
    match value:
        case str() as text:
            return text
        case int() | float() as number:
            return str(number)
        case bool() as flag:
            return str(flag).lower()
        case None:
            return ""
        case list() | dict():
            return ""


def parse_todo(record: dict[str, JsonValue], line_number: int) -> Todo | None:
    card_id = text_field(record, "id").strip()
    if not card_id:
        return None
    raw_status = text_field(record, "status").strip().lower()
    status = raw_status if raw_status in STATUS_KEYS else "backlog"
    raw_bounces = record.get("bounce_count", record.get("bounces", 0))
    bounce_count = raw_bounces if isinstance(raw_bounces, int) and not isinstance(raw_bounces, bool) else 0
    return Todo(
        card_id=card_id,
        title=text_field(record, "title") or f"Untitled item on line {line_number}",
        status=status,
        lane=text_field(record, "lane"),
        evidence=text_field(record, "evidence"),
        head_sha=text_field(record, "head_sha"),
        created=text_field(record, "created"),
        closed=text_field(record, "closed"),
        bounce_count=max(0, bounce_count),
    )


def load_todos(path: Path) -> BoardData:
    if not path.exists():
        return BoardData((), (f"Input file not found: {path}",))
    todos: list[Todo] = []
    warnings: list[str] = []
    with path.open(encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, start=1):
            if not raw_line.strip():
                continue
            try:
                parsed: JsonValue = json.loads(raw_line)
            except json.JSONDecodeError as error:
                warnings.append(f"Skipped malformed JSON on line {line_number}: {error.msg}")
                continue
            match parsed:
                case dict() as record:
                    todo = parse_todo(record, line_number)
                    if todo is None:
                        warnings.append(f"Skipped line {line_number}: missing id")
                    else:
                        todos.append(todo)
                case _:
                    warnings.append(f"Skipped line {line_number}: expected a JSON object")
    return BoardData(tuple(todos), tuple(warnings))


def load_title(path: Path) -> str:
    if not path.exists():
        return "Delivery Board"
    try:
        parsed: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "Delivery Board"
    match parsed:
        case {"title": str(title)} if title.strip():
            return title.strip()
        case _:
            return "Delivery Board"


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def render_card(todo: Todo) -> str:
    fields = (
        ("Lane", todo.lane or "—"),
        ("Evidence", todo.evidence or "—"),
        ("Head", todo.head_sha or "—"),
    )
    details = "".join(
        f'<div class="field"><span>{label}</span><b>{escape(value, quote=True)}</b></div>'
        for label, value in fields
    )
    return (
        f'<article class="card"><div class="card-id">{escape(todo.card_id, quote=True)}</div>'
        f'<h3>{escape(todo.title, quote=True)}</h3>{details}</article>'
    )


def render_html(data: BoardData, title: str) -> str:
    counts = {key: sum(todo.status == key for todo in data.todos) for key, _ in COLUMNS}
    closed_durations = [
        (closed - created).total_seconds() / 86_400
        for todo in data.todos
        if (created := parse_timestamp(todo.created)) is not None
        and (closed := parse_timestamp(todo.closed)) is not None
        and closed >= created
    ]
    lead_time = sum(closed_durations) / len(closed_durations) if closed_durations else 0.0
    bounce_count = sum(todo.bounce_count for todo in data.todos)
    empty = '<div class="empty">No work items yet.<small>Add JSON objects to board/todos.jsonl, one per line.</small></div>'
    columns = "".join(
        f'<section class="column"><header><h2>{label}</h2><span>{counts[key]}</span></header>'
        f'<div class="cards">{"".join(render_card(todo) for todo in data.todos if todo.status == key) or empty}</div></section>'
        for key, label in COLUMNS
    )
    count_rows = "".join(
        f'<tr><th>{label}</th><td>{counts[key]}</td></tr>' for key, label in COLUMNS
    )
    warning_html = "".join(f"<li>{escape(item, quote=True)}</li>" for item in data.warnings)
    warnings = f'<aside class="warnings"><strong>Input notes</strong><ul>{warning_html}</ul></aside>' if warning_html else ""
    generated = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    safe_title = escape(title, quote=True)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title}</title>
<style>
:root{{--ink:#17212b;--muted:#657180;--paper:#f4f1ea;--panel:#fff;--line:#d9d5cb;--accent:#176b5b;--accent2:#d8efe7;--shadow:0 10px 30px rgba(33,42,48,.08)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:14px/1.45 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}button{{font:inherit}}.shell{{min-height:100vh;padding:28px}}.masthead{{display:flex;align-items:end;justify-content:space-between;gap:24px;border-bottom:2px solid var(--ink);padding:0 0 18px}}.eyebrow{{color:var(--accent);font-size:11px;font-weight:800;letter-spacing:.16em;text-transform:uppercase}}h1{{font:700 clamp(30px,4vw,56px)/1.02 Georgia,serif;margin:5px 0 0;letter-spacing:-.035em}}.meta{{color:var(--muted);text-align:right}}.tabs{{display:flex;gap:8px;margin:20px 0}}.tab{{border:1px solid var(--line);border-radius:999px;background:transparent;color:var(--muted);cursor:pointer;padding:9px 18px;font-weight:700}}.tab.active{{background:var(--ink);border-color:var(--ink);color:#fff}}.view[hidden]{{display:none}}.board{{display:grid;grid-template-columns:repeat(7,minmax(210px,1fr));gap:12px;overflow-x:auto;padding:2px 2px 24px}}.column{{background:rgba(255,255,255,.42);border:1px solid var(--line);border-radius:14px;min-height:430px;padding:12px}}.column>header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;padding:2px 3px 10px;border-bottom:1px solid var(--line)}}.column h2{{font-size:13px;letter-spacing:.04em;margin:0;text-transform:uppercase}}.column header span{{display:grid;place-items:center;background:var(--accent2);border-radius:999px;color:var(--accent);font-weight:800;min-width:27px;height:27px}}.cards{{display:grid;gap:10px}}.card{{background:var(--panel);border:1px solid #e2ded5;border-radius:11px;box-shadow:var(--shadow);padding:14px}}.card-id{{color:var(--accent);font:800 10px/1.2 ui-monospace,SFMono-Regular,monospace;letter-spacing:.08em;text-transform:uppercase}}.card h3{{font:700 17px/1.22 Georgia,serif;margin:7px 0 14px;overflow-wrap:anywhere}}.field{{border-top:1px solid #eeebe4;display:grid;gap:2px;padding:7px 0 0;margin-top:7px}}.field span{{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.08em}}.field b{{font:600 11px/1.35 ui-monospace,SFMono-Regular,monospace;overflow-wrap:anywhere}}.empty{{color:var(--muted);border:1px dashed var(--line);border-radius:10px;padding:18px 12px;text-align:center}}.empty small{{display:block;margin-top:6px}}.report{{display:grid;grid-template-columns:minmax(260px,1fr) 2fr;gap:18px;max-width:1000px}}.metrics{{display:grid;grid-template-columns:repeat(2,minmax(150px,1fr));gap:12px}}.metric,.report-card,.warnings{{background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);padding:20px}}.metric strong{{display:block;font:700 34px/1 Georgia,serif}}.metric span{{color:var(--muted);display:block;margin-top:7px}}.report-card h2{{font:700 24px/1.1 Georgia,serif;margin:0 0 14px}}table{{border-collapse:collapse;width:100%}}th,td{{border-top:1px solid var(--line);padding:9px;text-align:left}}td{{font-weight:800;text-align:right}}.warnings{{margin-top:16px;border-left:4px solid #c7812c}}.warnings ul{{margin-bottom:0;padding-left:20px}}footer{{color:var(--muted);font-size:12px;margin-top:18px}}@media(max-width:760px){{.shell{{padding:18px}}.masthead{{align-items:start;flex-direction:column}}.meta{{text-align:left}}.report{{grid-template-columns:1fr}}.metrics{{grid-template-columns:1fr 1fr}}}}
</style></head><body><main class="shell">
<header class="masthead"><div><div class="eyebrow">Static delivery overview</div><h1>{safe_title}</h1></div><div class="meta">{len(data.todos)} cards<br>Generated {generated}</div></header>
<nav class="tabs" aria-label="Board views"><button class="tab active" data-view="board-view" type="button">Kanban</button><button class="tab" data-view="report-view" type="button">Report</button></nav>
<section class="view" id="board-view"><div class="board">{columns}</div>{warnings}</section>
<section class="view" id="report-view" hidden><div class="report"><div class="metrics"><div class="metric"><strong>{len(data.todos)}</strong><span>Total cards</span></div><div class="metric"><strong>{bounce_count}</strong><span>Bounce count</span></div><div class="metric"><strong>{lead_time:.1f}d</strong><span>Average lead time</span></div><div class="metric"><strong>{counts['done']}</strong><span>Completed</span></div></div><article class="report-card"><h2>Cards by status</h2><table><tbody>{count_rows}</tbody></table></article></div></section>
<footer>Lead time is measured from <code>created</code> to <code>closed</code> for cards with valid timestamps. Bounce count sums optional <code>bounce_count</code> or <code>bounces</code> values.</footer>
</main><script>document.querySelectorAll('.tab').forEach(function(tab){{tab.addEventListener('click',function(){{document.querySelectorAll('.tab').forEach(function(item){{item.classList.toggle('active',item===tab)}});document.querySelectorAll('.view').forEach(function(view){{view.hidden=view.id!==tab.dataset.view}})}})}});</script></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="input_path", default="board/todos.jsonl")
    parser.add_argument("--out", dest="output_path", default="dist/board.html")
    parser.add_argument("--config", default="board/config.json")
    args = parser.parse_args()
    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_html(load_todos(input_path), load_title(Path(args.config))),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
