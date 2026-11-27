"""shelf add TITLE AUTHOR [--status STATUS]"""

from __future__ import annotations

import argparse

from shelf.models import STATUSES
from shelf.store import Store


def register(subparsers) -> None:
    parser = subparsers.add_parser("add", help="add a book to your shelf")
    parser.add_argument("title")
    parser.add_argument("author")
    parser.add_argument("--status", default="to-read", help="to-read (default), reading or done")
    parser.set_defaults(handler=run, parser=parser)


def run(args: argparse.Namespace, store: Store) -> int:
    # parser.error prints the usage line and the message, then exits with 2,
    # before anything is saved.
    if not args.title.strip():
        args.parser.error("title must not be empty")
    if args.status not in STATUSES:
        args.parser.error(f"unknown status {args.status!r} (use to-read, reading or done)")
    book = store.add(args.title, args.author, args.status)
    print(f"Added {book}")
    return 0
