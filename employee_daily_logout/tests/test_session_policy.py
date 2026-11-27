from datetime import datetime, timezone

from odoo.tests import TransactionCase, tagged

from ..session_policy import cutoff_bounds


def timestamp(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()


@tagged('post_install', '-at_install')
class TestDailyCutoff(TransactionCase):

    def test_winter_cutoff(self):
        before, after = cutoff_bounds(timestamp('2026-11-27T23:29:59'))
        self.assertEqual(before, timestamp('2026-11-26T23:30:00'))
        self.assertEqual(after, timestamp('2026-11-27T23:30:00'))
        before, after = cutoff_bounds(timestamp('2026-11-27T23:30:00'))
        self.assertEqual(before, timestamp('2026-11-27T23:30:00'))
        self.assertEqual(after, timestamp('2026-11-28T23:30:00'))

    def test_summer_cutoff(self):
        before, after = cutoff_bounds(timestamp('2026-07-10T22:30:00'))
        self.assertEqual(before, timestamp('2026-07-10T22:30:00'))
        self.assertEqual(after, timestamp('2026-07-11T22:30:00'))

    def test_spring_day_is_23_hours(self):
        before, after = cutoff_bounds(timestamp('2026-03-08T16:00:00'))
        self.assertEqual(before, timestamp('2026-03-07T23:30:00'))
        self.assertEqual(after, timestamp('2026-03-08T22:30:00'))
        self.assertEqual(after - before, 23 * 3600)

    def test_autumn_day_is_25_hours(self):
        before, after = cutoff_bounds(timestamp('2026-11-01T17:00:00'))
        self.assertEqual(before, timestamp('2026-10-31T22:30:00'))
        self.assertEqual(after, timestamp('2026-11-01T23:30:00'))
        self.assertEqual(after - before, 25 * 3600)

    def test_weekends_and_year_boundary(self):
        before, after = cutoff_bounds(timestamp('2027-01-01T00:00:00'))
        self.assertEqual(before, timestamp('2026-12-31T23:30:00'))
        self.assertEqual(after, timestamp('2027-01-01T23:30:00'))
