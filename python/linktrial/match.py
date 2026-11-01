"""Patient <-> trial matching: deterministic prefilter -> LLM per-criterion review -> rule-based decision."""
from concurrent.futures import ThreadPoolExecutor

from linktrial.decision import decide_with_cohorts, validate_evidence
from linktrial.jev import consensus, jev_rank_key, triage

SYSTEM_PROMPT = """Você é um assistente de PRÉ-TRIAGEM de elegibilidade para ensaios clínicos oncológicos.
Para CADA critério listado (ids I* = inclusão, E* = exclusão), classifique usando SOMENTE o PRONTUÁRIO fornecido:
- MET: o prontuário mostra que o critério é verdadeiro para o paciente.
- NOT_MET: o prontuário mostra que o critério é falso para o paciente.
- UNKNOWN: o prontuário não traz a informação necessária. NUNCA presuma; na dúvida, UNKNOWN.
- NOT_APPLICABLE: o critério não se aplica a este paciente (ex.: braço/coorte de outro tumor, critério só para mulheres em idade fértil num homem).
Regras:
1. "evidence" deve ser uma CÓPIA LITERAL de um trecho do PRONTUÁRIO (copie a linha inteira, ex.: "ECOG: 1"). Não parafraseie, não explique, não copie o texto do critério. Para UNKNOWN deixe "".
2. Para critérios de EXCLUSÃO: MET significa que o paciente TEM a condição de exclusão.
3. "missing_data": para UNKNOWN, diga em português curto qual dado falta (ex.: "Clearance de creatinina"). Senão "".
4. "rationale": no máximo 20 palavras.
5. "cohort": se o critério vale só para uma parte/coorte/braço/subgrupo ALTERNATIVO do estudo (ex.: "Part A", "Part C", "Coorte metástase cerebral", "Braço pós-operatório"), escreva um rótulo curto e CONSISTENTE para essa coorte (o mesmo rótulo em todos os critérios dela). Critérios que valem para todos: "".
   Ex.: "Part A: PD-L1 ≥50%" e "Part C: PD-L1 <50%" são coortes diferentes; "Untreated brain metastases" e "Previously treated brain metastases" listados como alternativas são coortes diferentes.
   Subcoortes usam rótulo hierárquico "Pai > Filho" (ex.: "Fase 3 > metástase cerebral tratada"); critérios da coorte-pai levam só "Fase 3".
   Listas DENTRO de um critério ("(1) ...; (2) ...") seguem a lógica do texto que as introduz: "any of / one of / defined as ... any" = OU (basta uma); "all of" = E (todas).
6. Critérios PERMISSIVOS ("are eligible if", "may have received", "is allowed", "permitido") nunca excluem: use MET se o paciente se enquadra ou NOT_APPLICABLE se não.
7. Responda todos os ids, na ordem."""

SCHEMA = {
    "type": "object",
    "properties": {"criteria": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "verdict": {"type": "string", "enum": ["MET", "NOT_MET", "UNKNOWN", "NOT_APPLICABLE"]},
            "evidence": {"type": "string"},
            "missing_data": {"type": "string"},
            "rationale": {"type": "string"},
            "cohort": {"type": "string"},
        },
        "required": ["id", "verdict", "evidence", "missing_data", "rationale", "cohort"]}}},
    "required": ["criteria"],
}

SOLID_EXCLUDED = {"Hematológico"}


def patient_text(p):
    """Render the patient as stable 'Campo: valor' lines; evidence must be a verbatim span of this text."""
    lines = [f"Idade: {p['age']} anos", f"Sexo: {'feminino' if p['sex'] == 'FEMALE' else 'masculino'}",
             f"UF de residência: {p.get('uf', '')}", f"Diagnóstico: {p['diagnosis']}",
             f"ECOG: {p['ecog'] if p.get('ecog') is not None else 'não informado'}"]
    for k, v in (p.get("biomarkers") or {}).items():
        lines.append(f"{k}: {v}")
    for k, v in (p.get("clinical") or {}).items():
        lines.append(f"{k}: {v}")
    for k, v in (p.get("labs") or {}).items():
        lines.append(f"Laboratório - {k}: {v}")
    if p.get("prior_therapies"):
        lines.append("Tratamentos prévios: " + "; ".join(p["prior_therapies"]))
    else:
        lines.append("Tratamentos prévios: nenhum tratamento sistêmico prévio")
    if p.get("notes"):
        lines.append(f"Nota clínica: {p['notes']}")
    return "\n".join(lines)


def prefilter(patient, studies, limit=15):
    """Hard filters (age, sex, tumor group, ECOG) + heuristic score for ordering. Returns [(score, study, why)]."""
    out = []
    pg = patient["tumor_group"]
    positives = {b for b, v in (patient.get("biomarkers") or {}).items()
                 if not any(n in str(v).lower() for n in ("negativ", "selvagem", "wild", "ausente", "não detect"))}
    for s in studies:
        groups = s["tumor_groups"]
        basket = "Tumores sólidos (geral)" in groups and pg not in SOLID_EXCLUDED
        if pg not in groups and not basket:
            continue
        if s.get("healthy_volunteers"):
            continue
        a = patient["age"]
        if s["min_age_years"] is not None and a < s["min_age_years"]:
            continue
        if s["max_age_years"] is not None and a > s["max_age_years"]:
            continue
        if s["sex"] != "ALL" and s["sex"] != patient["sex"]:
            continue
        f = s["features"]
        if patient.get("ecog") is not None and f["ecog_max"] is not None and patient["ecog"] > f["ecog_max"]:
            continue
        score, why = 0, []
        if pg in groups:
            score += 20
        hits = positives & set(f["biomarkers_inclusion"])
        if hits:
            score += 15 * len(hits)
            why.append("biomarcador citado: " + ", ".join(sorted(hits)))
        if patient.get("uf") in s["states_br"]:
            score += 15
            why.append(f"centro em {patient['uf']}")
        for st in patient.get("settings", []):
            if st in f["disease_setting"]:
                score += 5
        if "Suporte/Qualidade de vida" in groups:
            score -= 10
        score += min(5, s["n_sites_br_recruiting"])
        out.append((score, s, why))
    out.sort(key=lambda x: (-x[0], x[1]["nct_id"]))
    return out[:limit]


def study_prompt(patient, study, only_ids=None):
    crit = [f"[I{i}]: {c}" for i, c in enumerate(study["inclusion_criteria"], 1)]
    crit += [f"[E{i}]: {c}" for i, c in enumerate(study["exclusion_criteria"], 1)]
    if only_ids is not None:
        crit = [c for c in crit if c[1:].split("]", 1)[0] in only_ids]
    return (f"ESTUDO {study['nct_id']} — {study['brief_title']}\nCondições: {', '.join(study['conditions'])}\n\n"
            f"CRITÉRIOS:\n" + "\n".join(crit) + f"\n\nPRONTUÁRIO:\n{patient_text(patient)}\n")


VERIFIER_NOTE = ("\n\nVOCÊ É O SEGUNDO AVALIADOR (verificação de exclusão). Outro avaliador concluiu que estes critérios "
                 "EXCLUEM o paciente. Reavalie de forma independente e rigorosa; só confirme se o prontuário "
                 "demonstrar inequivocamente. Na dúvida, UNKNOWN.")


def verify_blockers(patient, study, rows, d, verifier):
    """Second, stronger model must independently confirm every blocking verdict; disagreement -> UNKNOWN."""
    ids = set(d["blocking"])
    out = verifier.complete_json(SYSTEM_PROMPT + VERIFIER_NOTE, study_prompt(patient, study, ids), SCHEMA)
    second = {c["id"].strip("[] "): c for c in out.get("criteria", [])}
    ptext = patient_text(patient)
    changed = []
    for r in rows:
        if r["id"] not in ids:
            continue
        s = validate_evidence([{**r, "verdict": second.get(r["id"], {}).get("verdict", "UNKNOWN"),
                                "evidence": second.get(r["id"], {}).get("evidence", "")}], ptext)[0]
        if s["verdict"] == r["verdict"]:
            r["verified_by"] = verifier.name
        else:
            changed.append(r["id"])
            r.update(verdict="UNKNOWN", verifier_verdict=s["verdict"],
                     missing_data=f"divergência entre avaliadores em {r['id']}: revisão humana")
    return changed


def evaluate_study(patient, study, llm, verifier=None, jev_answers=None):
    out = llm.complete_json(SYSTEM_PROMPT, study_prompt(patient, study), SCHEMA)
    by_id = {c["id"].strip("[] "): c for c in out.get("criteria", [])}
    ptext = patient_text(patient)

    def collect(prefix, texts):
        rows = []
        for i, t in enumerate(texts, 1):
            cid = f"{prefix}{i}"
            c = by_id.get(cid, {"verdict": "UNKNOWN", "evidence": "", "missing_data": f"não avaliado: {t[:80]}"})
            rows.append({"id": cid, "criterion": t, "verdict": c.get("verdict", "UNKNOWN"),
                         "evidence": c.get("evidence", ""), "missing_data": c.get("missing_data", ""),
                         "rationale": c.get("rationale", ""), "cohort": c.get("cohort", "")})
        return validate_evidence(rows, ptext)

    inc = collect("I", study["inclusion_criteria"])
    exc = collect("E", study["exclusion_criteria"])
    if jev_answers:
        inc, exc = consensus(inc, jev_answers), consensus(exc, jev_answers)
    d = decide_with_cohorts(inc, exc)
    disputed = []
    if verifier is not None and d["blocking"]:
        disputed = verify_blockers(patient, study, inc + exc, d, verifier)
        if disputed:
            d = decide_with_cohorts(inc, exc)
    sites_uf = [x for x in study["sites_br"] if x.get("uf") == patient.get("uf") and x["status"] == "RECRUITING"]
    return {"nct_id": study["nct_id"], "title": study["brief_title"], "url": study["url"],
            "phases": study["phases"], "sponsor": study["lead_sponsor"], **d,
            "inclusion": inc, "exclusion": exc,
            "evidence_rejected": sum(v["evidence_rejected"] for v in inc + exc),
            "blockers_disputed": disputed,
            "llm_jev_disagreements": [v["id"] for v in inc + exc if "llm_verdict" in v],
            "sites_in_patient_uf": sites_uf, "central_contacts": study["central_contacts"]}


def match_patient(patient, studies, llm, limit=15, workers=4, verifier=None, jev=None, deep_k=8):
    """Prefilter -> (optional) Jev triage of all candidates -> LLM deep review of the top `deep_k` -> decision."""
    candidates = prefilter(patient, studies, limit=limit)
    triages = {}
    if jev is not None:
        with ThreadPoolExecutor(max_workers=8) as ex:
            for (_, s, _), t in zip(candidates, ex.map(lambda c: triage(patient, c[1], jev), candidates)):
                triages[s["nct_id"]] = t
        candidates.sort(key=lambda c: (jev_rank_key(triages[c[1]["nct_id"]]), -c[0]))
    deep = candidates[:deep_k] if jev is not None else candidates
    rest = candidates[deep_k:] if jev is not None else []

    def run(c):
        t = triages.get(c[1]["nct_id"])
        return evaluate_study(patient, c[1], llm, verifier, t["answers"] if t else None)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(run, deep))
    for (score, s, why), r in zip(deep, results):
        r.update(prefilter_score=score, prefilter_why=why, stage="deep")
        if s["nct_id"] in triages:
            t = triages[s["nct_id"]]
            r.update(jev_score=t["jev_score"], jev_confident_blocks=t["confident_blocks"])
    results.sort(key=lambda r: (r["rank_key"], -r["prefilter_score"]))
    triage_only = []
    for score, s, why in rest:
        t = triages[s["nct_id"]]
        triage_only.append({"nct_id": s["nct_id"], "title": s["brief_title"], "url": s["url"],
                            "phases": s["phases"], "stage": "triage", "jev_score": t["jev_score"],
                            "jev_confident_blocks": t["confident_blocks"], "prefilter_score": score})
    return {"patient_id": patient["id"], "llm": llm.name, "verifier": getattr(verifier, "name", None),
            "jev": getattr(jev, "name", None), "n_studies_active": len(studies),
            "n_prefiltered": len(candidates), "n_deep": len(deep), "results": results,
            "triage_only": triage_only}
