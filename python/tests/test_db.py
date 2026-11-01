import sqlite3
import unittest

from linktrial import db


def rec(nct, title="T", status="RECRUITING"):
    return {"nct_id": nct, "brief_title": title, "overall_status": status, "last_update": "2026-10-01"}


class Sync(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        db.init(self.conn)
        self.lookups = {}
        self.lookup = lambda nct: self.lookups.get(nct, "REMOVIDO_DO_REGISTRO")

    def run_sync(self, records, now):
        return db.sync(self.conn, records, now=now, lookup_status=self.lookup)

    def test_create_then_unchanged(self):
        r = self.run_sync([rec("NCT1"), rec("NCT2")], "2026-10-31T06:00")
        self.assertEqual((r["created"], r["updated"], r["deactivated"]), (2, 0, 0))
        r = self.run_sync([rec("NCT1"), rec("NCT2")], "2026-11-01T06:00")
        self.assertEqual((r["created"], r["updated"], r["unchanged"]), (0, 0, 2))
        self.assertEqual(len(db.active_records(self.conn)), 2)

    def test_update_records_changed_fields(self):
        self.run_sync([rec("NCT1"), rec("NCT2")], "2026-10-31")
        r = self.run_sync([rec("NCT1", title="Novo"), rec("NCT2")], "2026-11-01")
        self.assertEqual(r["updated"], 1)
        ev = db.events(self.conn, "NCT1")
        self.assertEqual(ev[-1]["event"], "UPDATED")
        self.assertIn("brief_title", ev[-1]["detail"])

    def test_missing_study_is_soft_deleted_with_real_reason(self):
        self.run_sync([rec("NCT1"), rec("NCT2"), rec("NCT3")], "2026-10-31")
        self.lookups["NCT3"] = "COMPLETED"
        r = self.run_sync([rec("NCT1"), rec("NCT2")], "2026-11-01")
        self.assertEqual(r["deactivated"], 1)
        self.assertEqual({x["nct_id"] for x in db.active_records(self.conn)}, {"NCT1", "NCT2"})
        row = self.conn.execute("select active, deactivation_reason from studies where nct_id='NCT3'").fetchone()
        self.assertEqual(row, (0, "COMPLETED"))

    def test_reactivation(self):
        self.run_sync([rec("NCT1"), rec("NCT2"), rec("NCT3")], "2026-10-31")
        self.run_sync([rec("NCT1"), rec("NCT2")], "2026-11-01")
        r = self.run_sync([rec("NCT1"), rec("NCT2"), rec("NCT3")], "2026-11-02")
        self.assertEqual(r["reactivated"], 1)
        self.assertEqual(db.events(self.conn, "NCT3")[-1]["event"], "REACTIVATED")

    def test_guard_aborts_on_suspicious_drop(self):
        self.run_sync([rec(f"NCT{i}") for i in range(10)], "2026-10-31")
        with self.assertRaises(db.SyncAborted):
            self.run_sync([rec("NCT1")], "2026-11-01")
        self.assertEqual(len(db.active_records(self.conn)), 10)
        last = self.conn.execute("select status from sync_runs order by id desc limit 1").fetchone()[0]
        self.assertEqual(last, "ABORTED")


if __name__ == "__main__":
    unittest.main()
