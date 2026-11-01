"""ClinicalTrials.gov API v2 client + normalization of oncology studies with Brazilian sites."""
import difflib
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request

from linktrial.criteria import extract_features, split_criteria

BASE = "https://clinicaltrials.gov/api/v2/studies"
ONCO_QUERY = ("cancer OR neoplasm OR carcinoma OR lymphoma OR leukemia OR myeloma OR "
              "melanoma OR sarcoma OR tumor OR glioma OR glioblastoma OR mesothelioma")
OPEN_STATUSES = "RECRUITING,NOT_YET_RECRUITING"

TUMOR_GROUPS = {
    "Mama": r"breast",
    "Pulmão": r"lung|\bNSCLC\b|\bSCLC\b|mesothelioma|thymic|thymoma",
    "Colorretal": r"colorectal|colon|rectal|rectum|\banal\b",
    "Gástrico/Esôfago": r"gastric|stomach|esophag|oesophag|gastroesophageal|GEJ|gastrointestinal (?:neoplasm|cancer|tumou?r)",
    "Pâncreas/Fígado/Vias biliares": r"pancrea|hepatocellular|liver|biliary|cholangio|gallbladder",
    "Próstata": r"prostat",
    "Urológico": r"renal|kidney|bladder|urothelial|penile|penis|upper tract",
    "Ginecológico": r"ovar|cervi|endometri|uter|vulv|gynecolog|fallopian|peritoneal",
    "Cabeça e pescoço": r"head and neck|\boral\b|oropharyn|laryn|nasopharyn|HNSCC|salivary",
    "Tireoide": r"thyroid",
    "Pele/Melanoma": r"melanoma|skin|cutaneous|merkel|basal cell",
    "SNC": r"glioma|glioblastoma|brain tumor|central nervous|medulloblastoma",
    "Neuroendócrino": r"neuroendocrine|\bNETs?\b|\bNEC\b|carcinoid|pheochromocytoma|paraganglioma",
    "Hematológico": (r"leukemia|leukaemia|lymphoma|myeloma|myelodysplas|myeloprolif|hodgkin|polycythemia|"
                     r"mastocytosis|myelofibrosis|thrombocythemia|waldenstr|macroglobulin|AL amyloidosis|"
                     r"(?-i:\b(?:AML|ALL|CLL|MDS|CML)\b)"),
    "Sarcoma": r"sarcoma|GIST|gastrointestinal stromal|ewing",
    "Pediátrico (embrionários)": r"neuroblastoma|wilms|retinoblastoma|hepatoblastoma",
    "Germinativo/Testículo": r"testic|germ cell",
    "Suporte/Qualidade de vida": (r"\bpain\b|quality of life|palliative|cardiotox|toxicit|sarcopenia|side effect|"
                                  r"nausea|mucositis|survivor|fatigue|cachexia|neuropathy|exercise|nutrition|"
                                  r"anxiety|depress|aging|older adults"),
    "Tumores sólidos (geral)": r"solid tumou?r|advanced cancer|neoplasms?(?: \||$)|malignan|(?:^|\| )cancers?(?: \||$)",
}
_GROUPS = {k: re.compile(v, re.I) for k, v in TUMOR_GROUPS.items()}
_GENERIC = {"Tumores sólidos (geral)", "Suporte/Qualidade de vida"}

_ONCO = re.compile(
    r"(?<!tumor )(?<!tumour )cancer|neoplas|carcinom|lymphoma|leuk|myelom|melanom|sarcom|tumou?r(?! necrosis)|gliom|blastoma|malignan|metasta|"
    r"oncolog|polycythemia|mastocytosis|myelofibrosis|myelodysplas|thrombocythemia|neuroendocrine|"
    r"mesothelioma|\bGIST\b|amyloidosis|chemotherap|radiotherap", re.I)


def is_oncology(conditions, title="", keywords=()):
    return bool(_ONCO.search(" | ".join([*conditions, title, *keywords])))


UF = {
    "acre": "AC", "alagoas": "AL", "amapa": "AP", "amazonas": "AM", "bahia": "BA", "ceara": "CE",
    "distrito federal": "DF", "federal district": "DF", "brasilia": "DF", "espirito santo": "ES",
    "goias": "GO", "maranhao": "MA", "mato grosso": "MT", "mato grosso do sul": "MS",
    "minas gerais": "MG", "para": "PA", "paraiba": "PB", "parana": "PR", "pernambuco": "PE",
    "piaui": "PI", "rio de janeiro": "RJ", "rio grande do norte": "RN", "rio grande do sul": "RS",
    "rondonia": "RO", "roraima": "RR", "santa catarina": "SC", "sao paulo": "SP", "sergipe": "SE",
    "tocantins": "TO",
}


CAPITALS = {
    "sao paulo": "SP", "rio de janeiro": "RJ", "belo horizonte": "MG", "porto alegre": "RS",
    "curitiba": "PR", "florianopolis": "SC", "salvador": "BA", "recife": "PE", "fortaleza": "CE",
    "natal": "RN", "brasilia": "DF", "goiania": "GO", "vitoria": "ES", "teresina": "PI",
    "belem": "PA", "manaus": "AM", "joao pessoa": "PB", "maceio": "AL", "aracaju": "SE",
    "sao luis": "MA", "cuiaba": "MT", "campo grande": "MS", "barretos": "SP", "campinas": "SP",
    "ribeirao preto": "SP", "santo andre": "SP", "sao jose do rio preto": "SP", "jau": "SP",
    "ijui": "RS", "passo fundo": "RS", "caxias do sul": "RS", "londrina": "PR", "cascavel": "PR",
    "itajai": "SC", "blumenau": "SC", "joinville": "SC", "uberlandia": "MG", "juiz de fora": "MG",
}


def _ascii(x):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower()).strip()


def normalize_state(name, city=""):
    """Map messy CT.gov state strings ('Estado de Bahia', 'Paraná (PR)', 'Sao Paula') to UF code; '' if unknown."""
    s = _ascii(name or "")
    code = re.search(r"(?:\(|\s-\s|\s|^)([a-z]{2})\)?$", s)
    if code and code.group(1).upper() in UF.values():
        return code.group(1).upper()
    s = re.sub(r"^(?:estado|state) (?:de|do|da|of) ", "", s)
    s = re.sub(r"\s*\(.*?\)\s*", "", s).strip()
    if s in UF:
        return UF[s]
    close = difflib.get_close_matches(s, UF.keys(), n=1, cutoff=0.85)
    if close:
        return UF[close[0]]
    for cand in (s, _ascii(city or "")):
        if cand in CAPITALS:
            return CAPITALS[cand]
    return ""


def _get(params) -> dict:
    url = BASE + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def fetch_studies(cond=ONCO_QUERY, country="Brazil", statuses=OPEN_STATUSES, page_size=200):
    """Yield raw study dicts (all pages)."""
    params = {"query.cond": cond, "query.locn": country, "filter.overallStatus": statuses,
              "pageSize": page_size, "countTotal": "true"}
    while True:
        data = _get(params)
        yield from data.get("studies", [])
        token = data.get("nextPageToken")
        if not token:
            return
        params["pageToken"] = token


def parse_age(v):
    if not v:
        return None
    n, unit = (v.split() + ["years"])[:2]
    n = float(n)
    u = unit.lower()
    if u.startswith("year"):
        return n
    if u.startswith("month"):
        return round(n / 12, 2)
    if u.startswith("week"):
        return round(n / 52, 2)
    return round(n / 365, 2)


def tumor_groups(conditions, title=""):
    text = " | ".join(conditions) + " | " + title
    hits = [g for g, rx in _GROUPS.items() if rx.search(text)]
    specific = [g for g in hits if g not in _GENERIC]
    if specific:
        return specific + (["Suporte/Qualidade de vida"] if "Suporte/Qualidade de vida" in hits else [])
    return hits or ["Outros"]


def normalize_study(raw, country="Brazil"):
    p = raw["protocolSection"]
    ident = p["identificationModule"]
    status = p.get("statusModule", {})
    design = p.get("designModule", {})
    elig = p.get("eligibilityModule", {})
    cl = p.get("contactsLocationsModule", {})
    sponsor = p.get("sponsorCollaboratorsModule", {})
    conds = p.get("conditionsModule", {})
    inc, exc = split_criteria(elig.get("eligibilityCriteria"))
    sites = [
        {
            "facility": l.get("facility", ""),
            "city": l.get("city", ""),
            "state": l.get("state", ""),
            "uf": normalize_state(l.get("state", ""), l.get("city", "")),
            "status": l.get("status", ""),
            "lat": l.get("geoPoint", {}).get("lat"),
            "lon": l.get("geoPoint", {}).get("lon"),
            "contacts": [{k: c.get(k) for k in ("name", "phone", "email") if c.get(k)}
                         for c in l.get("contacts", [])],
        }
        for l in cl.get("locations", [])
        if l.get("country") == country
    ]
    conditions = conds.get("conditions", [])
    title = ident.get("briefTitle", "")
    return {
        "nct_id": ident["nctId"],
        "url": f"https://clinicaltrials.gov/study/{ident['nctId']}",
        "brief_title": title,
        "official_title": ident.get("officialTitle", ""),
        "acronym": ident.get("acronym", ""),
        "overall_status": status.get("overallStatus", ""),
        "start_date": status.get("startDateStruct", {}).get("date", ""),
        "primary_completion_date": status.get("primaryCompletionDateStruct", {}).get("date", ""),
        "last_update": status.get("lastUpdatePostDateStruct", {}).get("date", ""),
        "study_type": design.get("studyType", ""),
        "phases": design.get("phases", []),
        "enrollment": design.get("enrollmentInfo", {}).get("count"),
        "allocation": design.get("designInfo", {}).get("allocation", ""),
        "lead_sponsor": sponsor.get("leadSponsor", {}).get("name", ""),
        "sponsor_class": sponsor.get("leadSponsor", {}).get("class", ""),
        "conditions": conditions,
        "keywords": conds.get("keywords", []),
        "tumor_groups": tumor_groups(conditions, title),
        "interventions": [{"type": i.get("type", ""), "name": i.get("name", "")}
                          for i in p.get("armsInterventionsModule", {}).get("interventions", [])],
        "brief_summary": p.get("descriptionModule", {}).get("briefSummary", ""),
        "sex": elig.get("sex", "ALL"),
        "min_age_years": parse_age(elig.get("minimumAge")),
        "max_age_years": parse_age(elig.get("maximumAge")),
        "healthy_volunteers": elig.get("healthyVolunteers", False),
        "inclusion_criteria": inc,
        "exclusion_criteria": exc,
        "features": extract_features(inc, exc, title),
        "central_contacts": [{k: c.get(k) for k in ("name", "phone", "email") if c.get(k)}
                             for c in cl.get("centralContacts", [])],
        "sites_br": sites,
        "n_sites_br": len(sites),
        "n_sites_br_recruiting": sum(s["status"] == "RECRUITING" for s in sites),
        "states_br": sorted({s["uf"] for s in sites if s["uf"]}),
        "is_oncology": is_oncology(conditions, title, conds.get("keywords", [])),
    }
