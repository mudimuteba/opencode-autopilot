#!/usr/bin/env python3
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


STORE_PATH = Path(__file__).with_name("todos.jsonl")
STATUSES = ("Backlog", "Ready", "Building", "QA", "Review", "Blocked", "Done")


class StoreError(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sample_cards() -> List[Dict[str, Any]]:
    created = "2026-01-01T00:00:00+00:00"
    return [
        make_card(
            card_id="sample-001",
            title="Define the first board milestone",
            status="Backlog",
            lane="Product",
            evidence="README.md",
            head_sha="",
            created=created,
        ),
        make_card(
            card_id="sample-002",
            title="Implement the JSONL todo store",
            status="Building",
            lane="Engineering",
            evidence="board/store.py",
            head_sha="",
            created=created,
        ),
        make_card(
            card_id="sample-003",
            title="Verify the seeded board",
            status="Ready",
            lane="Quality",
            evidence="python3 board/store.py list",
            head_sha="",
            created=created,
        ),
    ]


def make_card(
    card_id: str,
    title: str,
    status: str,
    lane: str,
    evidence: str,
    head_sha: str,
    created: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": card_id,
        "title": title,
        "status": status,
        "lane": lane,
        "evidence": evidence,
        "head_sha": head_sha,
        "created": created or utc_now(),
        "closed": None,
    }


def append_card(card: Dict[str, Any]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STORE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(card, sort_keys=True) + "\n")


def seed_if_missing() -> None:
    if STORE_PATH.exists():
        return
    for card in sample_cards():
        append_card(card)


def load_cards() -> List[Dict[str, Any]]:
    seed_if_missing()
    cards: List[Dict[str, Any]] = []
    with STORE_PATH.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                card = json.loads(line)
            except json.JSONDecodeError as exc:
                raise StoreError(
                    "Invalid JSON on line {}: {}".format(line_number, exc.msg)
                ) from exc
            if not isinstance(card, dict):
                raise StoreError("Line {} is not a JSON object".format(line_number))
            cards.append(card)
    return cards


def write_cards_atomic(cards: Iterable[Dict[str, Any]]) -> None:
    temporary_path = STORE_PATH.with_name(STORE_PATH.name + ".tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as handle:
            for card in cards:
                handle.write(json.dumps(card, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary_path), str(STORE_PATH))
    except OSError:
        if temporary_path.exists():
            temporary_path.unlink()
        raise


def find_card(cards: Iterable[Dict[str, Any]], card_id: str) -> Dict[str, Any]:
    for card in cards:
        if card.get("id") == card_id:
            return card
    raise StoreError("Card not found: {}".format(card_id))


def print_card(card: Dict[str, Any]) -> None:
    print(json.dumps(card, sort_keys=True))


def command_add(args: argparse.Namespace) -> int:
    seed_if_missing()
    card = make_card(
        card_id=uuid.uuid4().hex[:12],
        title=args.title,
        status=args.status,
        lane=args.lane,
        evidence=args.evidence,
        head_sha=args.head_sha,
    )
    append_card(card)
    print_card(card)
    return 0


def command_list(args: argparse.Namespace) -> int:
    cards = load_cards()
    for card in cards:
        if args.status and card.get("status") != args.status:
            continue
        if args.lane and card.get("lane") != args.lane:
            continue
        print_card(card)
    return 0


def command_show(args: argparse.Namespace) -> int:
    print_card(find_card(load_cards(), args.id))
    return 0


def command_move(args: argparse.Namespace) -> int:
    cards = load_cards()
    card = find_card(cards, args.id)
    card["status"] = args.status
    if args.lane is not None:
        card["lane"] = args.lane
    if args.evidence is not None:
        card["evidence"] = args.evidence
    if args.head_sha is not None:
        card["head_sha"] = args.head_sha
    card["closed"] = utc_now() if args.status == "Done" else None
    write_cards_atomic(cards)
    print_card(card)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JSONL-backed todo board store")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="append a card")
    add_parser.add_argument("title")
    add_parser.add_argument("--status", choices=STATUSES, default="Backlog")
    add_parser.add_argument("--lane", default="General")
    add_parser.add_argument("--evidence", default="")
    add_parser.add_argument("--head-sha", default="")
    add_parser.set_defaults(handler=command_add)

    list_parser = subparsers.add_parser("list", help="list cards")
    list_parser.add_argument("--status", choices=STATUSES)
    list_parser.add_argument("--lane")
    list_parser.set_defaults(handler=command_list)

    move_parser = subparsers.add_parser("move", help="move a card")
    move_parser.add_argument("id")
    move_parser.add_argument("status", choices=STATUSES)
    move_parser.add_argument("--lane")
    move_parser.add_argument("--evidence")
    move_parser.add_argument("--head-sha")
    move_parser.set_defaults(handler=command_move)

    show_parser = subparsers.add_parser("show", help="show one card")
    show_parser.add_argument("id")
    show_parser.set_defaults(handler=command_show)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (OSError, StoreError) as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
