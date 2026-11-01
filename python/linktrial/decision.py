"""Decision layer: turns per-criterion LLM verdicts into an auditable pre-screening decision.

The LLM only labels criteria. Deterministic rules here decide, so every outcome can be traced
to a criterion id and a verbatim evidence span from the patient record.
"""
import re

VERDICTS = {"MET", "NOT_MET", "UNKNOWN", "NOT_APPLICABLE"}
MAX_PENDING_FOR_POSSIBLE = 4

TIERS = {"MATCH_PROVAVEL": 0, "MATCH_POSSIVEL": 1, "REVISAO_NECESSARIA": 2, "INELEGIVEL": 3}
LABELS = {
    "MATCH_PROVAVEL": "Match provável",
    "MATCH_POSSIVEL": "Match possível — confirmar pendências",
    "REVISAO_NECESSARIA": "Revisão necessária — muitos dados faltando",
    "INELEGIVEL": "Inelegível na pré-triagem",
}


def _norm(t):
    return re.sub(r"\s+", " ", (t or "").lower()).strip(" .;:\"'")


def validate_evidence(verdicts, patient_text):
    """Downgrade MET/NOT_MET whose evidence is not a verbatim span of the patient record (anti-hallucination)."""
    hay = _norm(patient_text)
    out = []
    for v in verdicts:
        v = dict(v)
        verdict = v.get("verdict") if v.get("verdict") in VERDICTS else "UNKNOWN"
        v["evidence_rejected"] = False
        if verdict in ("MET", "NOT_MET"):
            ev = _norm(v.get("evidence"))
            if not ev or ev not in hay:
                v["evidence_rejected"] = bool(ev)
                if not v.get("missing_data"):
                    v["missing_data"] = "confirmar: " + (v.get("criterion") or v.get("id", ""))[:120]
                verdict = "UNKNOWN"
        v["verdict"] = verdict
        out.append(v)
    return out


def decide(inclusion, exclusion):
    """inclusion/exclusion: validated verdict dicts. Returns decision dict."""
    blocking = [v["id"] for v in inclusion if v["verdict"] == "NOT_MET"]
    blocking += [v["id"] for v in exclusion if v["verdict"] == "MET"]
    unknown = [v for v in inclusion + exclusion if v["verdict"] == "UNKNOWN"]
    pending = list(dict.fromkeys(v.get("missing_data") or v["id"] for v in unknown))
    met = sum(v["verdict"] == "MET" for v in inclusion)
    evaluable_inc = sum(v["verdict"] != "NOT_APPLICABLE" for v in inclusion)

    if blocking:
        decision = "INELEGIVEL"
    elif not unknown:
        decision = "MATCH_PROVAVEL"
    elif len(pending) <= MAX_PENDING_FOR_POSSIBLE:
        decision = "MATCH_POSSIVEL"
    else:
        decision = "REVISAO_NECESSARIA"

    return {
        "decision": decision,
        "label": LABELS[decision],
        "blocking": blocking,
        "pending": pending,
        "inclusion_met": met,
        "inclusion_evaluable": evaluable_inc,
        "rank_key": (TIERS[decision], len(pending), -met),
    }


_SEPS = (" > ", " - ", " – ", ": ")


def _is_ancestor(parent, child):
    return any(child.startswith(parent + sep) for sep in _SEPS)


def decide_with_cohorts(inclusion, exclusion):
    """Criteria tagged with a cohort/part/arm are alternatives (OR): evaluate general + each LEAF cohort
    (inheriting its ancestors' criteria, e.g. "Fase 3" -> "Fase 3 > sem metástase cerebral"), keep the best.

    A study is blocked only if general criteria block, or every leaf cohort is blocked.
    """
    def coh(x):
        return (x.get("cohort") or "").strip()

    cohorts = list(dict.fromkeys(coh(x) for x in inclusion + exclusion if coh(x)))
    if not cohorts:
        return {**decide(inclusion, exclusion), "cohort": "", "cohorts": [], "cohorts_evaluated": []}
    leaves = [c for c in cohorts if not any(_is_ancestor(c, o) for o in cohorts if o != c)]

    def applies(x, leaf):
        k = coh(x)
        return k == "" or k == leaf or _is_ancestor(k, leaf)

    best = None
    for leaf in leaves:
        d = {**decide([x for x in inclusion if applies(x, leaf)], [x for x in exclusion if applies(x, leaf)]),
             "cohort": leaf}
        if best is None or d["rank_key"] < best["rank_key"]:
            best = d
    best["cohorts"] = cohorts
    best["cohorts_evaluated"] = leaves
    return best
