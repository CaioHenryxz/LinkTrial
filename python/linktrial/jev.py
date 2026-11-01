"""TypeSafe Jev ("System One" decision model) integration.

Jev returns calibrated typed answers (no text). In LinkTrial it does:
  1. fast triage of EVERY prefiltered study: one `choice` question per criterion -> ranking;
  2. a second, independent opinion: a block is only accepted when the LLM (with verbatim evidence)
     and Jev (confident) agree.
Docs: https://docs.typesafe.ai  (POST https://api.typesafe.ai/v1/systemone, Bearer TYPESAFE_API_KEY).
Known Jev limits (TypeSafe/Pydantic docs): literal reading, weak at arithmetic/dates, accuracy drops with
irrelevant state, steerable by adversarial text -> keep state compact and keep deterministic checks.
"""
import hashlib
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.14.0"  # pinned: aliases move and would shift thresholds silently
BLOCK_P = 0.7  # Jev probability needed to confirm a block (TypeSafe suggests 0.7 yes / 0.3 no as start)

OPTIONS = {
    "MET": "o prontuário mostra que o critério é verdadeiro para o paciente",
    "NOT_MET": "o prontuário mostra que o critério é falso para o paciente",
    "UNKNOWN": "o prontuário não traz a informação necessária para decidir",
    "NOT_APPLICABLE": "o critério não se aplica a este paciente (coorte/braço de outro perfil ou critério permissivo)",
}
Q_INC = ("Critério de INCLUSÃO do estudo em `criterion`. O paciente descrito em `prontuario` atende a ele? "
         "Use apenas o prontuário; se a informação não estiver lá, UNKNOWN.")
Q_EXC = ("Critério de EXCLUSÃO do estudo em `criterion`. MET significa que o paciente descrito em `prontuario` "
         "TEM esta condição de exclusão. Use apenas o prontuário; se a informação não estiver lá, UNKNOWN.")


# Jev has no notion of alternative cohorts; criteria scoped to one ("Part C: ...") must not count as study blocks.
COHORT_PREFIX = re.compile(r"^\s*(?:part|cohort|arm|phase|stage\s+\d\s*:|sub-?study|group|coorte|braço|parte|fase)"
                           r"\s*[\w.\-/, ]{0,20}?\s*[:\-–]", re.I)


class JevError(RuntimeError):
    pass


class JevClient:
    def __init__(self, api_key=None, model=MODEL, conn=None, transport=None, timeout=60):
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY")
        if not self.api_key:
            raise JevError("TYPESAFE_API_KEY not set")
        self.model = model
        self.conn = conn
        self.transport = transport or self._http
        self.timeout = timeout
        self.hits = 0
        self.lock = threading.Lock()
        if conn is not None:
            conn.execute("create table if not exists jev_cache(key text primary key, response text,"
                         " created_at text default current_timestamp)")

    @property
    def name(self):
        return f"typesafe:{self.model}"

    def _http(self, body):
        req = urllib.request.Request(API_URL, data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {self.api_key}",
                                              "Content-Type": "application/json"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503) and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise JevError(f"HTTP {e.code}: {e.read()[:300]!r}")
            except urllib.error.URLError:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        raise JevError("unreachable")

    def decide(self, state, questions):
        body = {"model": self.model, "state": state, "questions": questions}
        key = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if self.conn is not None:
            with self.lock:
                row = self.conn.execute("select response from jev_cache where key=?", (key,)).fetchone()
            if row:
                self.hits += 1
                return json.loads(row[0])
        out = self.transport(body)
        if self.conn is not None:
            with self.lock:
                self.conn.execute("insert or replace into jev_cache(key, response) values (?,?)",
                                  (key, json.dumps(out, ensure_ascii=False)))
                self.conn.commit()
        return out


class FakeJev:
    name = "fake-jev"

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = 0

    def decide(self, state, questions):
        self.calls += 1
        default = {"type": "choice", "choice": "UNKNOWN", "confidence": 1.0,
                   "probabilities": {"MET": 0, "NOT_MET": 0, "UNKNOWN": 1.0, "NOT_APPLICABLE": 0}}
        return {"model": "fake", "answers": {q: self.answers.get(q, default) for q in questions}}


def build_questions(study):
    qs = {}
    for prefix, texts, q in (("I", study["inclusion_criteria"], Q_INC), ("E", study["exclusion_criteria"], Q_EXC)):
        for i, t in enumerate(texts, 1):
            qs[f"{prefix}{i}"] = {"type": "choice",
                                  "instructions": {"question": q, "criterion": t, "estudo": study["brief_title"]},
                                  "criteria": OPTIONS}
    return qs


def _blocking_prob(cid, a):
    p = a.get("probabilities", {})
    return p.get("NOT_MET", 0.0) if cid.startswith("I") else p.get("MET", 0.0)


def triage(patient, study, jev):
    from linktrial.match import patient_text  # local import avoids a cycle

    questions = build_questions(study)
    if not questions:
        return {"answers": {}, "confident_blocks": [], "cohort_scoped_blocks": [], "jev_score": 0.0, "model": None}
    out = jev.decide({"prontuario": patient_text(patient)}, questions)
    answers = out.get("answers", {})
    block_p = {cid: _blocking_prob(cid, a) for cid, a in answers.items()}
    texts = {f"I{i}": t for i, t in enumerate(study["inclusion_criteria"], 1)}
    texts.update({f"E{i}": t for i, t in enumerate(study["exclusion_criteria"], 1)})
    scoped = {c for c in block_p if COHORT_PREFIX.match(texts.get(c, ""))}
    unknown_p = [a.get("probabilities", {}).get("UNKNOWN", 0.0) for a in answers.values()]
    return {
        "answers": answers,
        "model": out.get("model"),
        "confident_blocks": sorted(c for c, p in block_p.items() if p >= BLOCK_P and c not in scoped),
        "cohort_scoped_blocks": sorted(c for c, p in block_p.items() if p >= BLOCK_P and c in scoped),
        # mean probability that a criterion does NOT block (higher = better fit); unknowns lower it a little
        "jev_score": round(sum(1 - p for p in block_p.values()) / len(block_p)
                           - 0.25 * (sum(unknown_p) / len(unknown_p)), 4),
    }


def jev_rank_key(t):
    return (len(t["confident_blocks"]), -t["jev_score"])


def consensus(rows, answers, block_p=BLOCK_P):
    """A blocking LLM verdict survives only if Jev agrees (top choice is the blocking one, or p_block >= block_p);
    otherwise -> UNKNOWN (human review). Wrongly excluding a patient is the costly error."""
    out = []
    for r in rows:
        r = dict(r)
        a = answers.get(r["id"])
        if a is None:
            out.append(r)
            continue
        r["jev"] = {"choice": a.get("choice"), "p_block": round(_blocking_prob(r["id"], a), 3),
                    "confidence": a.get("confidence")}
        llm_blocks = (r["id"].startswith("I") and r["verdict"] == "NOT_MET") or \
                     (r["id"].startswith("E") and r["verdict"] == "MET")
        blocking_choice = "NOT_MET" if r["id"].startswith("I") else "MET"
        jev_agrees = a.get("choice") == blocking_choice or _blocking_prob(r["id"], a) >= block_p
        if llm_blocks and not jev_agrees:
            r["llm_verdict"] = r["verdict"]
            r["verdict"] = "UNKNOWN"
            r["missing_data"] = (f"divergência LLM×Jev em {r['id']} (Jev: {a.get('choice')}, "
                                 f"p_bloqueio={_blocking_prob(r['id'], a):.2f}): revisão humana")
        out.append(r)
    return out
