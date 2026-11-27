"""shelf stats"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone

from shelf.models import STATUSES, Book
from shelf.store import ShelfError, Store


def register(subparsers) -> None:
    parser = subparsers.add_parser("stats", help="count your books by status")
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, store: Store) -> int:
    for line in summarize(store.load()):
        print(line)
    return 0


def summarize(books: list[Book], today: date | None = None) -> list[str]:
    """One line per status, then how many books were finished this year.

    ``today`` defaults to the current date in UTC, the time zone of the stored
    timestamps. Books with a status outside ``STATUSES`` are not counted.
    """
    if today is None:
        today = datetime.now(timezone.utc).date()
    lines = [f"{status}: {sum(book.status == status for book in books)}" for status in STATUSES]
    finished = sum(
        book.status == "done"
        and book.finished_at is not None
        and finished_year(book) == today.year
        for book in books
    )
    lines.append(f"finished this year: {finished}")
    return lines


def finished_year(book: Book) -> int:
    """The UTC year of ``book.finished_at`` (a timestamp without an offset is taken as UTC)."""
    try:
        moment = datetime.fromisoformat(book.finished_at)
    except ValueError:
        raise ShelfError(f"book #{book.id} has an invalid finished_at: {book.finished_at!r}") from None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).year
