"""SQLite store for LinkTrial with CRUD sync job: create / update / soft-delete / reactivate + audit trail."""
import hashlib
import json
import sqlite3

SCHEMA = """
create table if not exists studies (
  nct_id text primary key,
  record text not null,
  content_hash text not null,
  overall_status text,
  last_update text,
  active integer not null default 1,
  first_seen text not null,
  last_seen text not null,
  deactivated_at text,
  deactivation_reason text
);
create table if not exists sync_runs (
  id integer primary key autoincrement,
  started_at text, finished_at text, status text,
  fetched integer default 0, created integer default 0, updated integer default 0,
  unchanged integer default 0, deactivated integer default 0, reactivated integer default 0,
  error text
);
create table if not exists study_events (
  id integer primary key autoincrement,
  run_id integer, nct_id text, event text, detail text, at text
);
create index if not exists ix_events_nct on study_events(nct_id);
"""

# A full snapshot smaller than this fraction of currently active studies is treated as an API problem.
MIN_SNAPSHOT_RATIO = 0.5


class SyncAborted(RuntimeError):
    pass


def connect(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    init(conn)
    return conn


def init(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def content_hash(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _changed_keys(old, new):
    return sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))


def _event(conn, run_id, nct, event, detail, at):
    conn.execute("insert into study_events(run_id, nct_id, event, detail, at) values (?,?,?,?,?)",
                 (run_id, nct, event, detail, at))


def sync(conn, records, now, lookup_status):
    """Reconcile a FULL snapshot of open studies with the DB.

    records: normalized study dicts currently open in Brazil.
    lookup_status(nct_id) -> str: real reason a study left the snapshot (e.g. COMPLETED, REMOVIDO_DO_REGISTRO).
    """
    cur = conn.execute("insert into sync_runs(started_at, status, fetched) values (?,?,?)",
                       (now, "RUNNING", len(records)))
    run_id = cur.lastrowid
    active_before = {r[0] for r in conn.execute("select nct_id from studies where active=1")}
    if active_before and len(records) < MIN_SNAPSHOT_RATIO * len(active_before):
        msg = f"snapshot {len(records)} < {MIN_SNAPSHOT_RATIO:.0%} of {len(active_before)} active; nothing changed"
        conn.execute("update sync_runs set status='ABORTED', finished_at=?, error=? where id=?", (now, msg, run_id))
        conn.commit()
        raise SyncAborted(msg)

    stats = dict(created=0, updated=0, unchanged=0, deactivated=0, reactivated=0)
    seen = set()
    for rec in records:
        nct = rec["nct_id"]
        seen.add(nct)
        h = content_hash(rec)
        row = conn.execute("select record, content_hash, active from studies where nct_id=?", (nct,)).fetchone()
        blob = json.dumps(rec, ensure_ascii=False)
        if row is None:
            conn.execute("insert into studies(nct_id, record, content_hash, overall_status, last_update, active,"
                         " first_seen, last_seen) values (?,?,?,?,?,1,?,?)",
                         (nct, blob, h, rec.get("overall_status"), rec.get("last_update"), now, now))
            _event(conn, run_id, nct, "CREATED", rec.get("brief_title", ""), now)
            stats["created"] += 1
            continue
        old_rec, old_hash, active = json.loads(row[0]), row[1], row[2]
        if not active:
            _event(conn, run_id, nct, "REACTIVATED", "", now)
            stats["reactivated"] += 1
        if old_hash != h:
            if active:
                _event(conn, run_id, nct, "UPDATED", ", ".join(_changed_keys(old_rec, rec)), now)
                stats["updated"] += 1
        elif active:
            stats["unchanged"] += 1
        conn.execute("update studies set record=?, content_hash=?, overall_status=?, last_update=?, active=1,"
                     " last_seen=?, deactivated_at=null, deactivation_reason=null where nct_id=?",
                     (blob, h, rec.get("overall_status"), rec.get("last_update"), now, nct))

    for nct in sorted(active_before - seen):
        reason = lookup_status(nct)
        conn.execute("update studies set active=0, deactivated_at=?, deactivation_reason=? where nct_id=?",
                     (now, reason, nct))
        _event(conn, run_id, nct, "DEACTIVATED", reason, now)
        stats["deactivated"] += 1

    conn.execute("update sync_runs set status='OK', finished_at=?, created=?, updated=?, unchanged=?,"
                 " deactivated=?, reactivated=? where id=?",
                 (now, stats["created"], stats["updated"], stats["unchanged"], stats["deactivated"],
                  stats["reactivated"], run_id))
    conn.commit()
    return {"run_id": run_id, "fetched": len(records), **stats}


def active_records(conn):
    return [json.loads(r[0]) for r in conn.execute("select record from studies where active=1 order by nct_id")]


def events(conn, nct_id=None, run_id=None):
    q, args = "select run_id, nct_id, event, detail, at from study_events where 1=1", []
    if nct_id:
        q += " and nct_id=?"
        args.append(nct_id)
    if run_id:
        q += " and run_id=?"
        args.append(run_id)
    cols = ["run_id", "nct_id", "event", "detail", "at"]
    return [dict(zip(cols, r)) for r in conn.execute(q + " order by id", args)]
