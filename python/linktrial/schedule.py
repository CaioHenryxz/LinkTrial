"""Daily-sync helpers: next run time, human summary, optional Telegram notification, single-run lock."""
import datetime
import json
import os
import pathlib
import time
import urllib.parse
import urllib.request

ICONS = {"CREATED": "🆕", "UPDATED": "✏️", "DEACTIVATED": "⛔", "REACTIVATED": "♻️"}


def next_run(now, hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"invalid time {hhmm!r}")
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return target if target > now else target + datetime.timedelta(days=1)


def format_sync_message(stats, active, changes, max_lines=15):
    head = f"LinkTrial sync #{stats['run_id']}: {active} estudos ativos"
    if not any(stats[k] for k in ("created", "updated", "deactivated", "reactivated")):
        return head + " — sem mudanças."
    lines = [head, f"+{stats['created']} novos · ~{stats['updated']} atualizados · "
                   f"-{stats['deactivated']} encerrados · {stats['reactivated']} reativados"]
    important = [c for c in changes if c["event"] != "UPDATED"] + [c for c in changes if c["event"] == "UPDATED"]
    for c in important[:max_lines]:
        lines.append(f"{ICONS.get(c['event'], '•')} {c['nct_id']} {c['detail'][:80]}")
    if len(changes) > max_lines:
        lines.append(f"… e mais {len(changes) - max_lines}")
    return "\n".join(lines)


def notify(text):
    """Send to Telegram if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set; otherwise no-op. Never raises."""
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text[:4000]}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=20)
        return True
    except Exception:
        return False


class RunLock:
    """File lock so a scheduled run never overlaps a manual one. Stale after `stale_s`."""

    def __init__(self, path, stale_s=3600):
        self.path = pathlib.Path(path)
        self.stale_s = stale_s

    def __enter__(self):
        if self.path.exists() and time.time() - self.path.stat().st_mtime < self.stale_s:
            raise RuntimeError(f"another sync is running ({self.path})")
        self.path.write_text(json.dumps({"pid": os.getpid(), "at": time.time()}))
        return self

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)
