"""Run LinkTrial matching for one patient against ACTIVE studies in data/linktrial.db.

Usage:  python scripts/match.py patients/SYN-001.json [--limit 12] [--model haiku] [--workers 4]
Writes reports/<patient>_<timestamp>.json and .md
"""
import argparse
import datetime
import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from linktrial import db  # noqa: E402
from linktrial.jev import JevClient  # noqa: E402
from linktrial.llm import CachedLLM, ClaudeCLI  # noqa: E402
from linktrial.match import match_patient  # noqa: E402

ICON = {"MATCH_PROVAVEL": "🟢", "MATCH_POSSIVEL": "🟡", "REVISAO_NECESSARIA": "🟠", "INELEGIVEL": "🔴"}


def to_markdown(rep, patient):
    out = [f"# LinkTrial — pré-triagem {rep['patient_id']}", "",
           f"> {patient.get('_aviso', '')}  ",
           f"> Gerado {rep['generated_at']} · LLM `{rep['llm']}` · {rep['n_studies_active']} estudos ativos → "
           f"{rep['n_prefiltered']} pré-filtrados → avaliados critério a critério. "
           "Decisão por regras auditáveis; elegibilidade final é do investigador.", "",
           "| # | Decisão | Estudo | Fase | Inclusão atendida | Pendências | Centro na UF | Jev (aderência) |",
           "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rep["results"], 1):
        out.append(f"| {i} | {ICON[r['decision']]} {r['label']} | [{r['nct_id']}]({r['url']}) {r['title'][:70]} | "
                   f"{'/'.join(r['phases'])} | {r['inclusion_met']}/{r['inclusion_evaluable']} | {len(r['pending'])} | "
                   f"{len(r['sites_in_patient_uf'])} | {r.get('jev_score', '—')} |")
    for r in rep["results"]:
        if r["decision"] == "INELEGIVEL":
            continue
        out += ["", f"## {ICON[r['decision']]} {r['nct_id']} — {r['title']}", f"*{r['sponsor']}* · {r['label']}" + (f" · coorte provável: **{r['cohort']}**" if r.get("cohort") else ""), ""]
        if r["pending"]:
            out.append("**Checklist para confirmar com a equipe do estudo:**")
            out += [f"- [ ] {p}" for p in r["pending"]]
        out.append("")
        out.append("**Critérios atendidos (evidência literal do prontuário):**")
        for v in r["inclusion"]:
            if v["verdict"] == "MET":
                out.append(f"- {v['id']}: {v['criterion'][:110]} — _\"{v['evidence']}\"_")
        if r["sites_in_patient_uf"]:
            out.append("")
            out.append("**Centros recrutando na UF do paciente:** " +
                       "; ".join(f"{s['facility']} ({s['city']})" for s in r["sites_in_patient_uf"][:5]))
    if rep.get("triage_only"):
        out += ["", "## Triagem rápida Jev (sem revisão profunda)",
                "| Estudo | Fase | Aderência Jev | Bloqueios prováveis |", "|---|---|---|---|"]
        for t in rep["triage_only"]:
            out.append(f"| [{t['nct_id']}]({t['url']}) {t['title'][:70]} | {'/'.join(t['phases'])} | "
                       f"{t['jev_score']} | {len(t['jev_confident_blocks'])} |")
    blocked = [r for r in rep["results"] if r["decision"] == "INELEGIVEL"]
    if blocked:
        out += ["", "## 🔴 Inelegíveis na pré-triagem (motivo)"]
        for r in blocked:
            crit = {v["id"]: v for v in r["inclusion"] + r["exclusion"]}
            why = "; ".join(f"{b}: {crit[b]['criterion'][:90]} — _\"{crit[b]['evidence']}\"_" for b in r["blocking"][:2])
            out.append(f"- [{r['nct_id']}]({r['url']}) {r['title'][:60]} → {why}")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("patient")
    ap.add_argument("--limit", type=int, default=40, help="candidatos após o pré-filtro (triagem Jev)")
    ap.add_argument("--deep-k", type=int, default=8, help="estudos que vão para revisão profunda do LLM")
    ap.add_argument("--no-jev", action="store_true", help="desliga o Jev (TypeSafe)")
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--verifier", default="auto",
                    help="modelo que reconfirma bloqueios; 'auto' = só sem Jev; 'none' desliga")
    a = ap.parse_args()
    patient = json.loads(pathlib.Path(a.patient).read_text(encoding="utf-8"))
    conn = db.connect(ROOT / "data" / "linktrial.db")
    studies = db.active_records(conn)
    llm = CachedLLM(ClaudeCLI(model=a.model), conn)
    t0 = time.time()
    use_jev = not a.no_jev and bool(os.environ.get("TYPESAFE_API_KEY"))
    jev = JevClient(conn=conn) if use_jev else None
    vmodel = ("none" if use_jev else "sonnet") if a.verifier == "auto" else a.verifier
    verifier = None if vmodel == "none" else CachedLLM(ClaudeCLI(model=vmodel), conn)
    rep = match_patient(patient, studies, llm, limit=a.limit if use_jev else min(a.limit, 12),
                        workers=a.workers, verifier=verifier, jev=jev, deep_k=a.deep_k)
    rep["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    rep["elapsed_s"] = round(time.time() - t0, 1)
    rep["cache_hits"] = llm.hits
    outdir = ROOT / "reports"
    outdir.mkdir(exist_ok=True)
    stem = f"{patient['id']}_{rep['generated_at'][:16].replace(':', '')}"
    (outdir / f"{stem}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    (outdir / f"{stem}.md").write_text(to_markdown(rep, patient), encoding="utf-8")
    print(f"{patient['id']}: {rep['n_studies_active']} ativos -> {rep['n_prefiltered']} triados (Jev={rep['jev']}) -> "
          f"{rep['n_deep']} revisados em {rep['elapsed_s']}s "
          f"(cache {llm.hits})")
    for r in rep["results"]:
        print(f"  {r['decision']:<19} {r['nct_id']} pend={len(r['pending']):<2} bloq={','.join(r['blocking'][:3]):<10} "
              f"jev={r.get('jev_score', '-')!s:<6} LLMxJev={','.join(r.get('llm_jev_disagreements', [])):<8} coorte={r.get('cohort','')[:18]:<18} {r['title'][:50]}")
    print("relatório:", outdir / f"{stem}.md")


if __name__ == "__main__":
    main()
