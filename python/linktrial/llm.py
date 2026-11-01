"""LLM providers for criterion evaluation. Only structured JSON in/out; the decision is made elsewhere."""
import hashlib
import json
import shutil
import subprocess
import threading


class LLMError(RuntimeError):
    pass


class ClaudeCLI:
    """Uses the locally logged-in Claude Code CLI in a stripped-down headless mode (~3k tokens/call)."""

    def __init__(self, model="haiku", timeout=180):
        self.model = model
        self.timeout = timeout
        self.exe = shutil.which("claude")
        if not self.exe:
            raise LLMError("claude CLI not found in PATH")

    @property
    def name(self):
        return f"claude-cli:{self.model}"

    def complete_json(self, system, user, schema):
        cmd = [self.exe, "-p", "--output-format", "json", "--model", self.model,
               "--system-prompt", system, "--tools", "", "--strict-mcp-config", "--setting-sources", "",
               "--no-session-persistence", "--exclude-dynamic-system-prompt-sections",
               "--json-schema", json.dumps(schema)]
        p = subprocess.run(cmd, input=user, capture_output=True, text=True, encoding="utf-8",
                           timeout=self.timeout)
        if p.returncode != 0:
            raise LLMError(p.stderr[-500:] or p.stdout[-500:])
        out = json.loads(p.stdout)
        if out.get("is_error") or "structured_output" not in out:
            raise LLMError(str(out.get("result"))[:500])
        return out["structured_output"]


class FakeLLM:
    """Test double: returns a canned verdict per criterion id (default UNKNOWN)."""

    name = "fake"

    def __init__(self, verdicts=None, cohorts=None):
        self.verdicts = verdicts or {}
        self.cohorts = cohorts or {}
        self.calls = 0

    def complete_json(self, system, user, schema):
        self.calls += 1
        ids = [line.split(":", 1)[0].strip("[] ") for line in user.splitlines() if line.startswith("[")]
        crit = []
        for cid in ids:
            verdict, evidence = self.verdicts.get(cid, ("UNKNOWN", ""))
            crit.append({"id": cid, "verdict": verdict, "evidence": evidence,
                         "missing_data": "" if verdict != "UNKNOWN" else f"dado para {cid}", "rationale": "",
                         "cohort": self.cohorts.get(cid, "")})
        return {"criteria": crit}


class CachedLLM:
    """Wraps a provider with a SQLite cache keyed by (provider, prompt). Study or patient change => new key."""

    def __init__(self, inner, conn):
        self.inner = inner
        self.conn = conn
        conn.execute("create table if not exists llm_cache(key text primary key, response text, created_at text"
                     " default current_timestamp)")
        self.hits = 0
        self.lock = threading.Lock()

    @property
    def name(self):
        return self.inner.name

    def complete_json(self, system, user, schema):
        key = hashlib.sha256(f"{self.inner.name}\n{system}\n{user}".encode()).hexdigest()
        with self.lock:
            row = self.conn.execute("select response from llm_cache where key=?", (key,)).fetchone()
        if row:
            self.hits += 1
            return json.loads(row[0])
        out = self.inner.complete_json(system, user, schema)
        with self.lock:
            self.conn.execute("insert or replace into llm_cache(key, response) values (?,?)",
                              (key, json.dumps(out, ensure_ascii=False)))
            self.conn.commit()
        return out
