import datetime
import unittest

from linktrial.schedule import format_sync_message, next_run


class NextRun(unittest.TestCase):
    def test_later_today(self):
        now = datetime.datetime(2026, 10, 31, 5, 0)
        self.assertEqual(next_run(now, "06:00"), datetime.datetime(2026, 10, 31, 6, 0))

    def test_tomorrow_when_passed(self):
        now = datetime.datetime(2026, 10, 31, 6, 0, 1)
        self.assertEqual(next_run(now, "06:00"), datetime.datetime(2026, 11, 1, 6, 0))

    def test_bad_time(self):
        with self.assertRaises(ValueError):
            next_run(datetime.datetime(2026, 1, 1), "25:00")


class Message(unittest.TestCase):
    def test_summary_lists_changes(self):
        stats = {"run_id": 7, "created": 2, "updated": 1, "deactivated": 1, "reactivated": 0, "unchanged": 355}
        changes = [{"event": "CREATED", "nct_id": "NCT1", "detail": "Novo estudo A"},
                   {"event": "DEACTIVATED", "nct_id": "NCT9", "detail": "COMPLETED"}]
        msg = format_sync_message(stats, 358, changes)
        self.assertIn("358 estudos ativos", msg)
        self.assertIn("+2 novos", msg)
        self.assertIn("NCT9", msg)
        self.assertIn("COMPLETED", msg)

    def test_quiet_when_nothing_changed(self):
        stats = {"run_id": 8, "created": 0, "updated": 0, "deactivated": 0, "reactivated": 0, "unchanged": 359}
        self.assertIn("sem mudanças", format_sync_message(stats, 359, []))


if __name__ == "__main__":
    unittest.main()
