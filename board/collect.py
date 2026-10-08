#!/usr/bin/env python3
import argparse
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

from store import STATUSES, make_card

DEFAULT_TARGET = Path(__file__).with_name("todos.jsonl")
SECTION_RE = re.compile(r"^##\s+(?:(\d+)\.\s+)?(.*\S)\s*$")
EFFORT_RE = re.compile(r"\s+[—-]\s+`([SML])`\s*$")


def parse_todo(path: Path) -> List[Tuple[str, str]]:
    found: List[Tuple[str, str]] = []
    order = 0
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            match = SECTION_RE.match(raw.rstrip("\n"))
            if not match:
                continue
            order += 1
            number, heading = match.group(1), match.group(2)
            effort = ""
            effort_match = EFFORT_RE.search(heading)
            if effort_match:
                effort = effort_match.group(1)
                heading = heading[: effort_match.start()].rstrip()
            label = "section {}".format(number) if number else "item {}".format(order)
            evidence = "TODO.md {} ({})".format(label, effort) if effort else "TODO.md {}".format(label)
            found.append((heading, evidence))
    return found


def existing_titles(path: Path) -> set:
    titles = set()
    if not path.exists():
        return titles
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                card = json.loads(line)
            except json.JSONDecodeError:
                continue
            title = card.get("title") if isinstance(card, dict) else None
            if isinstance(title, str):
                titles.add(title.strip().lower())
    return titles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect TODO.md sections as board cards")
    parser.add_argument("--from", dest="source", required=True)
    parser.add_argument("--to", dest="target", default=str(DEFAULT_TARGET))
    parser.add_argument("--status", choices=STATUSES, default="Backlog")
    parser.add_argument("--lane", default="General")
    parser.add_argument("--apply", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source = Path(args.source)
    if not source.is_file():
        print("error: no such file: {}".format(source), file=sys.stderr)
        return 1
    sections = parse_todo(source)
    if not sections:
        print("error: no ## sections in {}".format(source), file=sys.stderr)
        return 1
    target = Path(args.target)
    known = existing_titles(target)
    fresh = [(t, e) for t, e in sections if t.strip().lower() not in known]
    skipped = len(sections) - len(fresh)
    if not args.apply:
        for title, evidence in fresh:
            print("WOULD-ADD {} [{}]".format(title, evidence))
        print("DRY-RUN ADDED=0 SKIPPED={}".format(skipped), file=sys.stderr)
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    source_tag = "" if source.name == "TODO.md" else " [{}]".format(source.name)
    added = 0
    with target.open("a", encoding="utf-8") as handle:
        for title, evidence in fresh:
            card: Dict[str, Any] = make_card(
                card_id=uuid.uuid4().hex[:12],
                title=title,
                status=args.status,
                lane=args.lane,
                evidence="{}{}".format(evidence, source_tag),
                head_sha="",
            )
            handle.write(json.dumps(card, sort_keys=True) + "\n")
            print(json.dumps(card, sort_keys=True))
            added += 1
    print("APPLIED ADDED={} SKIPPED={}".format(added, skipped), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
