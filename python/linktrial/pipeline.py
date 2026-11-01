"""Pipeline glue: fetch open oncology studies in Brazil, reconcile with the DB, export files for slides/demo."""
import collections
import csv
import datetime
import json
import urllib.error
import urllib.request

from linktrial import db
from linktrial.ctgov import BASE, fetch_studies, normalize_study

OPEN = {"RECRUITING", "NOT_YET_RECRUITING", ""}


def is_open_in_brazil(study):
    return study["is_oncology"] and any(site["status"] in OPEN for site in study["sites_br"])


def fetch_open_br():
    raw = list(fetch_studies())
    studies = [normalize_study(r) for r in raw]
    return raw, [s for s in studies if is_open_in_brazil(s)]


def lookup_status(nct_id):
    """Why did a study leave the open snapshot? Returns a short reason code."""
    try:
        with urllib.request.urlopen(f"{BASE}/{nct_id}", timeout=60) as r:
            s = normalize_study(json.load(r))
    except urllib.error.HTTPError as e:
        return "REMOVIDO_DO_REGISTRO" if e.code == 404 else f"ERRO_HTTP_{e.code}"
    if s["overall_status"] not in OPEN:
        return s["overall_status"]  # COMPLETED, ACTIVE_NOT_RECRUITING, TERMINATED, WITHDRAWN, SUSPENDED...
    if not s["sites_br"]:
        return "SEM_CENTRO_NO_BRASIL"
    if not any(x["status"] in OPEN for x in s["sites_br"]):
        return "CENTROS_BR_FECHADOS"
    if not s["is_oncology"]:
        return "FORA_DO_ESCOPO"
    return "AUSENTE_DA_BUSCA"


def _open_writable(path, warnings):
    """Open for writing; if locked (e.g. CSV open in Excel), write a sibling '<name>.novo<ext>' instead."""
    try:
        return open(path, "w", newline="", encoding="utf-8-sig")
    except PermissionError:
        alt = path.with_name(f"{path.stem}.novo{path.suffix}")
        warnings.append(f"{path.name} bloqueado (aberto em outro programa) -> gravado em {alt.name}")
        return open(alt, "w", newline="", encoding="utf-8-sig")


def export(studies, data_dir, raw_count=None):
    warnings = []
    studies = sorted(studies, key=lambda s: (-s["n_sites_br_recruiting"], s["nct_id"]))
    (data_dir / "studies_br.json").write_text(json.dumps(studies, ensure_ascii=False, indent=1), encoding="utf-8")
    cols = ["nct_id", "brief_title", "acronym", "overall_status", "phases", "study_type", "lead_sponsor",
            "sponsor_class", "tumor_groups", "conditions", "sex", "min_age_years", "max_age_years",
            "ecog_max", "kps_min", "biomarkers_inclusion", "biomarkers_exclusion", "disease_setting",
            "requires_measurable_disease", "excludes_brain_mets", "n_inclusion", "n_exclusion",
            "n_sites_br", "n_sites_br_recruiting", "states_br", "enrollment", "start_date", "last_update", "url"]
    with _open_writable(data_dir / "studies_br.csv", warnings) as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for s in studies:
            row = {**s, **s["features"]}
            w.writerow({c: "; ".join(map(str, row[c])) if isinstance(row[c], list) else row[c] for c in cols})
    with _open_writable(data_dir / "criteria_br.csv", warnings) as f:
        w = csv.writer(f)
        w.writerow(["nct_id", "type", "order", "criterion"])
        for s in studies:
            for kind in ("inclusion", "exclusion"):
                for i, c in enumerate(s[f"{kind}_criteria"], 1):
                    w.writerow([s["nct_id"], kind, i, c])
    count = collections.Counter
    summary = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": "ClinicalTrials.gov API v2 (query.locn=Brazil, status RECRUITING|NOT_YET_RECRUITING)",
        "raw_studies": raw_count,
        "studies_with_open_br_site": len(studies),
        "recruitment_points_study_x_site": sum(s["n_sites_br"] for s in studies),
        "by_tumor_group": count(g for s in studies for g in s["tumor_groups"]).most_common(),
        "by_phase": count("/".join(s["phases"]) or "N/A" for s in studies).most_common(),
        "by_state": count(st for s in studies for st in s["states_br"]).most_common(),
        "by_sponsor_class": count(s["sponsor_class"] for s in studies).most_common(),
        "top_biomarkers_inclusion": count(b for s in studies for b in s["features"]["biomarkers_inclusion"]).most_common(15),
        "with_ecog_extracted": sum(s["features"]["ecog_max"] is not None for s in studies),
        "total_criteria": sum(len(s["inclusion_criteria"]) + len(s["exclusion_criteria"]) for s in studies),
        "export_warnings": warnings,
    }
    (data_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def run_sync(conn, data_dir, now=None):
    now = now or datetime.datetime.now().isoformat(timespec="seconds")
    raw, open_studies = fetch_open_br()
    (data_dir / "raw_studies.json").write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    stats = db.sync(conn, open_studies, now=now, lookup_status=lookup_status)
    summary = export(db.active_records(conn), data_dir, raw_count=len(raw))
    return stats, summary
