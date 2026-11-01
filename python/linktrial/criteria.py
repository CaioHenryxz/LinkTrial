"""Parse ClinicalTrials.gov free-text eligibility into structured lists and features."""
import re

_ESCAPE = re.compile(r"\\([<>=.\-*_#()\[\]+|~`!])")  # CT.gov markdown escapes: "7\." "\<"
_HEADER = re.compile(r"^\s*(?:key\s+|main\s+|general\s+)?(inclusion|exclusion)\b.*criteri", re.I)
_LIST_INTRO = re.compile(r":\s*$|any of the following|one of the following|all of the following|following criteria|"
                         r"defined as|as follows|at least one of|either\b|\bincluding\b.*:|meet .* following", re.I)
_BULLET = re.compile(r"^\s*(?:[*\-•·]|\d+[.)]|[a-z][.)]|[ivx]+[.)])\s+", re.I)

BIOMARKERS = {
    "HER2": r"\bHER[\s-]?2\b|\bERBB2\b",
    "HR": r"\bHR[\s-]?(?:\+|pos|neg)|hormone[\s-]receptor|\bER[\s-]?(?:\+|pos|neg)|estrogen receptor|progesterone receptor",
    "EGFR": r"\bEGFR\b",
    "ALK": r"\bALK\b",
    "ROS1": r"\bROS-?1\b",
    "KRAS": r"\bKRAS\b",
    "NRAS": r"\bNRAS\b",
    "BRAF": r"\bBRAF\b",
    "MET": r"\bMET\b(?:\s+(?:exon|amplif|alter|mutat))",
    "RET": r"\bRET\b(?:\s+(?:fusion|rearr|mutat|alter))",
    "NTRK": r"\bNTRK",
    "PIK3CA": r"\bPIK3CA\b",
    "AKT1": r"\bAKT1?\b",
    "PTEN": r"\bPTEN\b",
    "ESR1": r"\bESR1\b",
    "BRCA": r"\bBRCA[12]?\b",
    "HRD": r"\bHRD\b|homologous recombination",
    "PD-L1": r"\bPD-?L1\b",
    "MSI/dMMR": r"\bMSI(?:-H)?\b|\bdMMR\b|mismatch repair|microsatellite",
    "TMB": r"\bTMB\b|tumor mutational burden",
    "FGFR": r"\bFGFR\d?\b",
    "IDH": r"\bIDH[12]?\b",
    "FLT3": r"\bFLT3\b",
    "CD20": r"\bCD20\b",
    "CD19": r"\bCD19\b",
    "BCMA": r"\bBCMA\b",
    "CLDN18.2": r"\bCLDN18\.?2\b|claudin[\s-]?18",
    "TROP2": r"\bTROP-?2\b",
    "PSMA": r"\bPSMA\b",
    "HLA": r"\bHLA-[A-Z]\*?\d",
    "KIT": r"\bc?-?KIT\b",
}
_BIO = {k: re.compile(v, re.I) for k, v in BIOMARKERS.items()}

SETTINGS = {
    "metastatic": r"metasta|stage\s+IV\b",
    "advanced": r"\badvanced\b|stage\s+III[ABC]?\b",
    "locally_advanced": r"locally[\s-]advanced",
    "unresectable": r"unresectable|not amenable to (?:surgical|curative)",
    "recurrent_relapsed": r"recurren|relaps",
    "refractory": r"refractory",
    "early_stage": r"early[\s-]stage|\bstage\s+(?:I|II|1|2)[ABC]?\b",
    "neoadjuvant": r"neo-?adjuvant|pre-?operative",
    "adjuvant": r"(?<!neo)(?<!neo-)\badjuvant",
    "first_line": r"first[\s-]line|treatment[\s-]na[iï]ve|previously untreated|no prior systemic",
    "previously_treated": r"previously treated|second[\s-]line|prior (?:line|systemic|therap)|progress(?:ed|ion) (?:on|after|during)",
}
_SET = {k: re.compile(v, re.I) for k, v in SETTINGS.items()}

_BRAIN = re.compile(r"brain metasta|CNS metasta|central nervous system (?:metasta|involvement)|leptomeningeal", re.I)
_STABLE = re.compile(r"stable|treated|asymptomatic|unless|except|allowed|eligible", re.I)
_MEASURABLE = re.compile(r"measurable disease|RECIST|measurable lesion", re.I)
_ECOG = re.compile(r"ECOG|Eastern Cooperative|Zubrod|WHO performance", re.I)
_KPS = re.compile(r"Karnofsky|\bKPS\b", re.I)


def split_criteria(text):
    """Return (inclusion, exclusion) lists of criterion strings.

    Indented sub-items/paragraphs (>= 2 spaces deeper than their parent) are folded into the parent as
    "(1) a; (2) b" so OR-alternatives ("post-menopausal defined as any of: ...") are evaluated together.
    """
    if not text:
        return [], []
    inc, exc, cur = [], [], None
    parent = None
    for raw in _ESCAPE.sub(r"\1", text).replace("\t", "    ").splitlines():
        line = raw.strip()
        if not line:
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        m = _HEADER.match(line)
        if m and len(line) < 120 and line.rstrip().endswith(":"):
            cur = exc if m.group(1).lower() == "exclusion" else inc
            parent = None
            continue
        target = cur if cur is not None else inc
        is_bullet = bool(_BULLET.match(line))
        item = _BULLET.sub("", line).strip()
        if not item:
            continue
        nested = parent is not None and parent["list"] is target and indent >= parent["indent"] + 2
        if nested and not is_bullet:  # indented paragraph = continuation of the current item
            if parent["children"]:
                parent["children"][-1] += " " + item
            else:
                parent["text"] += " " + item
            continue
        if nested and _LIST_INTRO.search(parent["text"]):  # parent announces a list -> fold as alternatives
            parent["children"].append(item)
            continue
        parent = {"text": item, "children": [], "list": target, "indent": indent}
        target.append(parent)

    def render(node):
        if not node["children"]:
            return node["text"]
        kids = "; ".join(f"({k}) {c.rstrip(' ;')}" for k, c in enumerate(node["children"], 1))
        return f"{node['text']} {kids}"

    return [render(n) for n in inc], [render(n) for n in exc]


def _ecog_max(criteria):
    for c in criteria:
        m = _ECOG.search(c)
        if not m:
            continue
        after = re.sub(r"\([^)]*\)", " ", c[m.end(): m.end() + 120])  # drop "(ECOG)", "(PS)"
        before = c[max(0, m.start() - 80): m.start()]
        found = _ecog_value(after)
        if found is None and re.search(r"performance status", before, re.I):
            found = _ecog_value(before)
        if found is not None:
            return found
    return None


def _ecog_value(window):
    le = re.search(r"(?:≤|<=|less than or equal to|of no more than|at most)\s*([0-4])\b", window)
    if le:
        return int(le.group(1))
    lt = re.search(r"(?:<|less than)\s*([1-5])\b", window)
    if lt:
        return int(lt.group(1)) - 1
    nums = [int(n) for n in re.findall(r"(?<![\d.])([0-4])(?!\d|\.\d)", window)]
    return max(nums) if nums else None


def _kps_min(criteria):
    for c in criteria:
        m = _KPS.search(c)
        if m:
            n = re.search(r"(\d{2,3})\s*%?", c[m.end(): m.end() + 80])
            if n and 10 <= int(n.group(1)) <= 100:
                return int(n.group(1))
    return None


def _biomarkers(criteria):
    text = " \n ".join(criteria)
    return sorted(k for k, rx in _BIO.items() if rx.search(text))


def extract_features(inclusion, exclusion, title=""):
    inc_text = " \n ".join([title, *inclusion])
    brain_exc = [c for c in exclusion if _BRAIN.search(c)]
    brain_inc = [c for c in inclusion if _BRAIN.search(c)]
    return {
        "ecog_max": _ecog_max(inclusion),
        "kps_min": _kps_min(inclusion),
        "biomarkers_inclusion": _biomarkers(inclusion),
        "biomarkers_exclusion": _biomarkers(exclusion),
        "disease_setting": sorted(k for k, rx in _SET.items() if rx.search(inc_text)),
        "requires_measurable_disease": bool(_MEASURABLE.search(inc_text)),
        "excludes_brain_mets": bool(brain_exc),
        "allows_brain_mets_if_stable": any(_STABLE.search(c) for c in brain_exc + brain_inc),
        "n_inclusion": len(inclusion),
        "n_exclusion": len(exclusion),
    }
