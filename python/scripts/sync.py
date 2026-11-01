"""CRUD sync job: keeps data/linktrial.db identical to the open oncology trials in Brazil on ClinicalTrials.gov.

Usage:  python scripts/sync.py            (schedule daily; safe to re-run any time)
Exit codes: 0 ok, 2 aborted by safety guard, 1 error.
Appends one JSON line per run to data/sync_log.jsonl.
"""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from linktrial import db  # noqa: E402
from linktrial.pipeline import run_sync  # noqa: E402
from linktrial.schedule import RunLock, format_sync_message, notify  # noqa: E402

DATA = ROOT / "data"


def main():
    DATA.mkdir(exist_ok=True)
    log = DATA / "sync_log.jsonl"
    try:
        with RunLock(DATA / "sync.lock"):
            conn = db.connect(DATA / "linktrial.db")
            try:
                stats, summary = run_sync(conn, DATA)
            except db.SyncAborted as e:
                print(f"ABORTADO (nada alterado): {e}")
                log.open("a", encoding="utf-8").write(json.dumps({"status": "ABORTED", "error": str(e)}) + "\n")
                notify(f"⚠️ LinkTrial sync ABORTADO pela trava de segurança (nada alterado): {e}")
                return 2
            subprocess.run([sys.executable, str(ROOT / "scripts" / "build_html.py")], check=True, capture_output=True)
            changes = db.events(conn, run_id=stats["run_id"])
    except Exception as e:  # network down, lock held, disk error...
        print(f"ERRO: {e}")
        log.open("a", encoding="utf-8").write(json.dumps({"status": "ERROR", "error": str(e)}) + "\n")
        notify(f"❌ LinkTrial sync falhou: {e}")
        return 1
    entry = {"status": "OK", **stats, "active": summary["studies_with_open_br_site"],
             "changes": [{k: c[k] for k in ("nct_id", "event", "detail")} for c in changes]}
    log.open("a", encoding="utf-8").write(json.dumps(entry, ensure_ascii=False) + "\n")
    msg = format_sync_message(stats, summary["studies_with_open_br_site"], changes)
    print(msg)
    for w in summary.get("export_warnings", []):
        print("  AVISO:", w)
    if any(stats[k] for k in ("created", "deactivated", "reactivated")) or os.environ.get("LINKTRIAL_NOTIFY_ALWAYS"):
        notify(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
