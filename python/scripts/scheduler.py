"""Long-running daily scheduler for servers/containers (Dokploy, VPS, Docker).

Usage:
  python scripts/scheduler.py                 # runs sync every day at LINKTRIAL_SYNC_TIME (default 06:00, local time)
  python scripts/scheduler.py --time 05:30
  python scripts/scheduler.py --now           # run once immediately, then keep the daily schedule
On a desktop prefer the OS scheduler: scripts/install_windows_task.ps1 or deploy/linktrial-sync.cron.
"""
import argparse
import datetime
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from linktrial.schedule import next_run  # noqa: E402


def run_once():
    started = datetime.datetime.now().isoformat(timespec="seconds")
    p = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync.py")], capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    print(f"[{started}] sync exit={p.returncode}\n{p.stdout.strip()}{p.stderr.strip()}", flush=True)
    return p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", default=os.environ.get("LINKTRIAL_SYNC_TIME", "06:00"))
    ap.add_argument("--now", action="store_true")
    a = ap.parse_args()
    next_run(datetime.datetime.now(), a.time)  # validate early
    if a.now:
        run_once()
    while True:
        target = next_run(datetime.datetime.now(), a.time)
        print(f"próximo sync: {target.isoformat(timespec='minutes')}", flush=True)
        while (remaining := (target - datetime.datetime.now()).total_seconds()) > 0:
            time.sleep(min(remaining, 300))  # wake every 5 min: survives clock changes / sleep
        run_once()


if __name__ == "__main__":
    main()
