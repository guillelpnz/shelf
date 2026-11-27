import json
import unittest
from datetime import date

from shelf.commands.stats import summarize
from shelf.models import Book
from tests.support import ShelfTestCase


def book(id, status, finished_at=None):
    return Book(
        id=id,
        title=f"Book {id}",
        author="Someone",
        status=status,
        added_at="2000-01-01T00:00:00+00:00",
        finished_at=finished_at,
    )


class SummarizeTest(unittest.TestCase):
    def test_counts_each_status_and_books_finished_this_year(self):
        books = [
            book(1, "to-read"),
            book(2, "to-read"),
            book(3, "reading"),
            book(4, "done", "2026-03-10T12:00:00+00:00"),
            book(5, "done", "2026-11-01T08:30:00+00:00"),
            book(6, "done", "2025-12-31T23:59:59+00:00"),
            book(7, "paused"),
        ]

        lines = summarize(books, today=date(2026, 11, 27))

        self.assertEqual(lines, [
            "to-read: 2",
            "reading: 1",
            "done: 3",
            "finished this year: 2",
        ])

    def test_an_empty_shelf_shows_every_line_with_zero(self):
        self.assertEqual(summarize([], today=date(2026, 11, 27)), [
            "to-read: 0",
            "reading: 0",
            "done: 0",
            "finished this year: 0",
        ])

    def test_the_year_changes_at_midnight_utc_on_new_year(self):
        books = [
            book(1, "done", "2025-12-31T23:59:59+00:00"),
            book(2, "done", "2026-01-01T00:00:00+00:00"),
            book(3, "done", "2026-01-01T00:00:01+00:00"),
        ]

        self.assertEqual(summarize(books, today=date(2025, 12, 31))[-1], "finished this year: 1")
        self.assertEqual(summarize(books, today=date(2026, 1, 1))[-1], "finished this year: 2")

    def test_the_year_is_taken_in_utc(self):
        # 00:30 at +01:00 on 1 January is still 31 December 2025 in UTC.
        books = [book(1, "done", "2026-01-01T00:30:00+01:00")]

        self.assertEqual(summarize(books, today=date(2026, 1, 1))[-1], "finished this year: 0")
        self.assertEqual(summarize(books, today=date(2025, 12, 31))[-1], "finished this year: 1")

    def test_a_timestamp_without_offset_is_taken_as_utc(self):
        # Read as local time, one of these two would land in the other year
        # on any machine whose time zone is not UTC.
        books = [
            book(1, "done", "2025-12-31T23:30:00"),
            book(2, "done", "2026-01-01T00:30:00"),
        ]

        self.assertEqual(summarize(books, today=date(2025, 12, 31))[-1], "finished this year: 1")
        self.assertEqual(summarize(books, today=date(2026, 1, 1))[-1], "finished this year: 1")

    def test_a_done_book_without_finished_at_counts_as_done_only(self):
        lines = summarize([book(1, "done")], today=date(2026, 11, 27))

        self.assertEqual(lines[2:], ["done: 1", "finished this year: 0"])


class StatsCommandTest(ShelfTestCase):
    def write_shelf(self, books):
        self.shelf_path.write_text(
            json.dumps([b.to_dict() for b in books], indent=2) + "\n", encoding="utf-8"
        )

    def test_stats_prints_the_four_lines(self):
        # Fixed dates in 2000, so the test passes whatever year it runs in.
        self.write_shelf([
            book(1, "to-read"),
            book(2, "to-read"),
            book(3, "reading"),
            book(4, "done", "2000-03-10T12:00:00+00:00"),
            book(5, "done", "2000-11-01T08:30:00+00:00"),
            book(6, "done", "1999-12-31T23:59:59+00:00"),
        ])

        result = self.shelf("stats")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "to-read: 2\nreading: 1\ndone: 3\nfinished this year: 0\n",
        )

    def test_stats_does_not_modify_the_shelf_file(self):
        self.write_shelf([book(1, "done", "2000-03-10T12:00:00+00:00"), book(2, "reading")])
        before = self.shelf_path.read_bytes()

        result = self.shelf("stats")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.shelf_path.read_bytes(), before)

    def test_an_unreadable_finished_at_is_an_error_not_a_traceback(self):
        self.write_shelf([book(1, "done", "yesterday")])

        result = self.shelf("stats")

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stderr,
            "shelf: error: book #1 has an invalid finished_at: 'yesterday'\n",
        )

    def test_stats_on_an_empty_shelf_shows_zeros_and_creates_no_file(self):
        result = self.shelf("stats")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "to-read: 0\nreading: 0\ndone: 0\nfinished this year: 0\n",
        )
        self.assertFalse(self.shelf_path.exists())
