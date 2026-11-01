"""Build a self-contained HTML 'trial marketplace' (LinkTrial demo) from data/studies_br.json.

Styling comes from the LinkTrial design system, copied into assets/ds/ (tokens.json, bundle.css,
official symbol); this script inlines all of it so the output stays a single file.

Usage: python scripts/build_html.py   ->  data/linktrial_vitrine.html
"""
import base64
import json
import logging
import pathlib
import sqlite3
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from linktrial.decision import MAX_PENDING_FOR_POSSIBLE, TIERS, _is_ancestor  # noqa: E402

DATA = ROOT / "data"
DS = ROOT / "assets" / "ds"

KEEP = ["nct_id", "url", "brief_title", "acronym", "phases", "lead_sponsor", "sponsor_class", "tumor_groups",
        "conditions", "sex", "min_age_years", "max_age_years", "inclusion_criteria", "exclusion_criteria",
        "features", "states_br", "n_sites_br", "n_sites_br_recruiting", "start_date", "interventions"]
SITE_STATUS = {"RECRUITING": "R", "NOT_YET_RECRUITING": "N"}

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LinkTrial — oncology trials recruiting in Brazil</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;650;700&family=Manrope:wght@700;750;800&display=swap">
<style>
__CSS__
/* Views (hash routed from the sidebar) */
.view[hidden]{display:none}
/* Stat cards: the value sits inside a ring; the ring and the bottom bar both encode the ratio spelled out in .stat-note */
.stat{position:relative;overflow:hidden;display:flex;align-items:center;gap:16px}
.ring-wrap{position:relative;flex:none;width:96px;height:96px;display:grid;place-content:center;text-align:center}
.ring-wrap .ring{position:absolute;inset:0;width:100%;height:100%;transform:rotate(-90deg)}
.stat .ring-wrap strong{position:relative;margin:0;font-size:24px;line-height:1}
.ring-wrap em{position:relative;font-style:normal;font-size:10px;font-weight:650;color:var(--muted);margin-top:4px}
.stat small{display:block;font-size:13px}.stat .stat-note{display:block;margin-top:8px;line-height:1.4}
.ring circle{fill:none;stroke-width:3.4}.ring .track{stroke:var(--chart-track)}
.ring .val{stroke:var(--chart-bar);stroke-linecap:round;stroke-dasharray:var(--p) 100;animation:ring 1.4s cubic-bezier(.2,.7,.2,1) both}
.stat .bar{position:absolute;left:0;bottom:0;height:3px;width:calc(var(--p) * 1%);background:var(--chart-bar);transform-origin:left;animation:grow 1.4s cubic-bezier(.2,.7,.2,1) both}
@keyframes ring{from{stroke-dasharray:0 100}}@keyframes grow{from{transform:scaleX(0)}}
/* Patient pipeline */
.step small{display:block;color:var(--muted);font-size:10px;margin-top:3px}
.funnel-row{padding:14px 0;border-top:1px solid var(--line)}.funnel-row:first-of-type{border-top:0}
.funnel-head{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;font-size:12px;color:var(--muted)}.funnel-head strong{color:var(--ink);font-size:13px}
.tiers{display:flex;height:12px;border-radius:7px;overflow:hidden;background:var(--chart-track);margin:9px 0}
.tiers i{display:block;width:calc(var(--n) * 1%);transform-origin:left;animation:grow 1.2s cubic-bezier(.2,.7,.2,1) both}
.t0{background:var(--match-high-ink)}.t1{background:var(--match-possible-ink)}.t2{background:var(--match-review-ink)}.t3{background:var(--match-barrier-ink)}
.legend .pill{margin:0 4px 4px 0}
/* Criteria review */
.clabel{display:flex;justify-content:space-between;gap:8px;font-size:12px;margin-bottom:5px}.clabel span{color:var(--muted)}
.cbar{display:flex;height:8px;border-radius:5px;overflow:hidden;background:var(--chart-track)}
.cbar i{display:block;width:calc(var(--n) * 1%);transform-origin:left;animation:grow 1s cubic-bezier(.2,.7,.2,1) both}
.c-ok{background:var(--pill-green-ink)}.c-tbd{background:var(--pill-amber-ink)}.c-no{background:var(--pill-red-ink)}
.clist{list-style:none;padding:0;margin:8px 0 0;font-size:12px;line-height:1.5}.clist li{padding:8px 0;border-top:1px solid var(--line)}
.clist b{margin-right:4px}.clist small{display:block;color:var(--muted);margin-top:3px}
.clist h4{font-size:11px;letter-spacing:1px;color:var(--muted);margin:12px 0 2px;text-transform:uppercase}
.csec{margin-top:14px}.csec .cbar{margin-bottom:2px}
.why-list,.results .why-list{list-style:none;padding:0;margin:6px 0 0;font-size:12px;line-height:1.5}
.why-list li,.results .why-list li{display:flex;gap:7px;padding:1px 0;border:0}
.why-list b{flex:none;width:14px;text-align:center}
.why-list .ok b{color:var(--pill-green-ink)}.why-list .tbd b{color:var(--pill-amber-ink)}.why-list .no{color:var(--pill-red-ink);font-weight:650}
.best{margin:14px 0 0}.best h3{font-size:15px;margin:0 0 2px}.best .site{font-size:12px;color:var(--muted);margin:8px 0 0}
details.more{margin-top:18px;border-top:1px solid var(--line);padding-top:14px}
details.more>summary{cursor:pointer;font-weight:650;font-size:13px;color:var(--teal)}details.more>summary span{color:var(--muted);font-weight:400}
details.more[open]>summary{margin-bottom:10px}
.rules{font-size:12px}.rules p{margin:0}.rules details summary{cursor:pointer;color:var(--teal);font-weight:600;margin-top:6px}.rules details p{margin-top:6px}
.features{display:grid;grid-template-columns:150px 1fr;gap:10px 14px;font-size:12px;margin:0}.features dt{font-weight:650}.features dd{margin:0;color:var(--muted)}
.timeline-panel{max-height:760px;overflow:auto}
.link-row{display:flex;gap:14px;align-items:center;justify-content:space-between}.link-row .btn,.link-row>.pill{flex:none}
/* Collapsible panels */
details.collapse>summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:10px}
details.collapse>summary::-webkit-details-marker{display:none}
details.collapse>summary h2{margin:0}details.collapse>summary small{color:var(--muted);font-size:12px}
details.collapse>summary .icon{margin-left:auto;transition:transform .2s}details.collapse[open]>summary .icon{transform:rotate(180deg)}
details.collapse[open]>summary{margin-bottom:16px}
/* Find trials */
.vitrine{display:grid;grid-template-columns:300px minmax(0,1fr);gap:22px;align-items:start}
.vitrine:has(>.filters:not([open])){grid-template-columns:minmax(0,1fr)}
.filters[open]{position:sticky;top:20px}.filters .field{margin-bottom:14px}
.bios{display:flex;flex-wrap:wrap;gap:4px 12px;font-weight:400;color:var(--ink)}.bios label{display:inline-flex;gap:5px;align-items:center}
.bios input{width:auto;accent-color:var(--teal)}
.study-grid{grid-template-columns:repeat(auto-fill,minmax(min(330px,100%),1fr))}
.study-card{content-visibility:auto;contain-intrinsic-size:auto 620px}
.study-body h3.long{font-size:16px;line-height:1.3}
.study-body .pill{margin:0 4px 4px 0}.pill.strike{text-decoration:line-through}
.site-list details summary{cursor:pointer;color:var(--teal);font-size:11px;font-weight:600}
.why{font-size:12px;color:var(--muted);margin:4px 0}.why.warn{color:var(--warning-ink)}
.crit summary{cursor:pointer;font-size:13px;color:var(--teal);font-weight:600;margin-top:8px}
.crit ol,.crit dl{font-size:12px;line-height:1.6;padding-left:18px;margin:6px 0;max-height:260px;overflow:auto}
.card-actions{display:flex;flex-wrap:wrap;gap:9px;margin-top:auto;padding-top:14px}.card-actions .btn{flex:1 1 auto;white-space:nowrap}
/* Patients */
.p-head{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:12px}.p-head strong{display:block}.p-head small{color:var(--muted);font-size:12px}.p-head .btn{margin-left:auto}
.p-dx{font-size:13px;margin:0 0 10px}.panel .pill{margin:0 4px 4px 0}
.results{list-style:none;padding:0;margin:0;font-size:12px}.results li{padding:9px 0;border-top:1px solid var(--line)}
.results a{color:var(--teal);font-weight:650}.results small{display:block;color:var(--muted);margin-top:3px}
.crit dl{padding-left:0}.crit dt{font-weight:650}.crit dd{margin:0 0 6px;color:var(--muted)}
.form-grid .wide{grid-column:1/-1}.form-grid .field{margin:0}.form-grid textarea{resize:vertical}
.field [aria-invalid]{border-color:var(--error-ink)}
.reg-actions{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
#reg-json{background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:14px;font-size:12px;max-height:340px;overflow:auto;white-space:pre-wrap}
@media(max-width:1150px){.vitrine{grid-template-columns:1fr}.filters[open]{position:static}}
@media(max-width:1400px){.stat{flex-direction:column;align-items:flex-start;gap:10px}}
@media(max-width:560px){.features{grid-template-columns:1fr}.features dd{margin-bottom:6px}.ring-wrap{width:80px;height:80px}.stat .ring-wrap strong{font-size:20px}.link-row{flex-wrap:wrap}.p-head .btn{margin-left:0}}
@media(prefers-reduced-motion:reduce){.ring .val,.stat .bar,.tiers i,.cbar i{animation:none}details.collapse>summary .icon{transition:none}}
</style></head><body>
<div class="shell">
<aside class="sidebar"><a class="brand" href="#overview"><img class="symbol" src="__LOGO__" alt="LinkTrial"><div><strong>Link<span class="trial">Trial</span></strong><small>CONNECTIONS THAT CARE</small></div></a>
<div class="nav-label">WORKSPACE</div>
<nav class="nav" aria-label="Main navigation">
<button data-view="overview" aria-label="Overview"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12h4l3-8 4 16 3-8h4"/></svg><span>Overview</span></button>
<button data-view="find" aria-label="Find trials"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 21l-5-5 M10.5 18a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15"/></svg><span>Find trials</span></button>
<button data-view="patients" aria-label="Patients"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M22 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75"/></svg><span>Patients</span></button>
</nav>
<div class="sidebar-bottom"><div class="demo-card"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m12 2 8 4v6c0 6-8 10-8 10S4 18 4 12V6l8-4 M8 12l3 3 5-6"/></svg><strong>Pre-screening only</strong><p>Real registry data.<br>Human decision.</p></div><div class="sidebar-foot">MIT Hacking Medicine<br>Oncology · Public demo</div></div></aside>
<div class="main-wrap">
<header class="topbar"><div class="breadcrumb">LinkTrial <span id="crumb"></span></div><span class="source-label">ClinicalTrials.gov · real registered trials</span></header>
<div class="banner"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m12 2 8 4v6c0 6-8 10-8 10S4 18 4 12V6l8-4 M8 12l3 3 5-6"/></svg> Recruiting and not-yet-recruiting trials with a site in Brazil · Pre-screening does not confirm eligibility or slot availability</div>
<main class="content">

<section class="view" id="v-overview" hidden>
<div class="heading"><div><div class="eyebrow">OVERVIEW</div><h1>Pipeline observability</h1><p>What the LinkTrial pipeline has synced from the registry, which patients are moving through matching, and every run so far.</p></div></div>
<div class="stats" id="ov-stats"></div>
<section class="panel"><h2>Patient–trial links and referrals</h2><p id="links-sum"></p><div class="info-row rules" id="rules-links"></div><ol class="results" id="links"></ol><p class="why">Demo: a referral is recorded on this page only and is not transmitted.</p></section>
<div class="two-col"><div>
<section class="panel"><h2>Patient pipeline</h2><p>Patients at each stage of their latest match run.</p><div class="stepper" id="stepper"></div><div id="funnels"></div></section>
<section class="panel"><h2>Running in the pipeline</h2><p>Parts of the official LinkTrial engine behind these numbers.</p><dl class="features" id="features"></dl></section>
</div>
<section class="panel timeline-panel"><h2>Timeline</h2><p>Registry sync runs and match runs, newest first.</p><ol class="timeline" id="timeline"></ol></section>
</div>
</section>

<section class="view" id="v-find" hidden>
<div class="heading"><div><div class="eyebrow">FIND TRIALS</div><h1>Oncology trials recruiting in Brazil</h1><p>Pre-screen trials against a patient profile and see which hospitals are recruiting. Final eligibility is always decided by the study team.</p></div></div>
<div class="vitrine"><details class="panel filters collapse" id="profile"><summary><div><h2>Patient profile</h2><small>Age, sex, ECOG, state, setting, biomarkers</small></div><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></summary>
<label class="field"><span>Age</span><input id="age" type="number" min="0" max="110" placeholder="e.g. 58"></label>
<label class="field"><span>Sex</span><select id="sex"><option value="">—</option><option value="FEMALE">Female</option><option value="MALE">Male</option></select></label>
<label class="field"><span>ECOG</span><select id="ecog"><option value="">—</option><option>0</option><option>1</option><option>2</option><option>3</option></select></label>
<label class="field"><span>State (UF)</span><select id="uf"><option value="">All</option></select><small>Hospitals in this state are listed first.</small></label>
<label class="field"><span>Disease setting</span><select id="setting"><option value="">—</option></select></label>
<div class="field"><span>Positive biomarkers</span><div class="bios" id="bios"></div></div>
<p class="caution"><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m12 2 8 4v6c0 6-8 10-8 10S4 18 4 12V6l8-4 M8 12l3 3 5-6"/></svg><span><strong>A high fit is an invitation to review:</strong> the study team confirms final eligibility.</span></p>
</details>
<div><div class="toolbar"><input id="q" aria-label="Search trials" placeholder="Search by drug, sponsor, condition or NCT"></div>
<div class="chips" id="cats"></div>
<div class="section-head"><h2 id="count"></h2><span>Sorted by pre-screening fit</span></div>
<div class="study-grid" id="list"></div></div></div>
</section>

<section class="view" id="v-patients" hidden>
<div class="heading"><div><div class="eyebrow">PATIENTS</div><h1>Patients in the pipeline</h1><p>Pseudonymized records sent to the match engine, with the latest decision for each one.</p></div></div>
<details class="panel collapse" id="register"><summary><div><h2>Register a patient</h2><small>Structured record in the same schema the match engine reads</small></div><svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></summary>
<form id="reg" class="form-grid" novalidate>
<div class="field"><span>Pseudonym ID</span><input value="Assigned automatically on save" disabled aria-describedby="pid-hint"><small id="pid-hint">Created by the backend. Names and document numbers are never stored.</small></div>
<label class="field"><span>Age *</span><input name="age" type="number" min="0" max="110" required></label>
<label class="field"><span>Sex *</span><select name="sex" required><option value="">—</option><option value="FEMALE">Female</option><option value="MALE">Male</option></select></label>
<label class="field"><span>State (UF) *</span><select name="uf" id="reg-uf" required><option value="">—</option></select></label>
<label class="field"><span>Tumor group *</span><select name="tumor_group" id="reg-tg" required><option value="">—</option></select></label>
<label class="field"><span>ECOG *</span><select name="ecog" required><option value="">—</option><option>0</option><option>1</option><option>2</option><option>3</option><option>4</option></select></label>
<label class="field wide"><span>Diagnosis</span><input name="diagnosis" placeholder="Histology, stage, metastatic sites, date of diagnosis"></label>
<div class="field wide"><span>Disease setting</span><div class="bios" id="reg-settings"></div></div>
<label class="field wide"><span>Biomarker report</span><textarea name="biomarker_report" rows="5" placeholder="Paste the pathology or molecular report as written, e.g. KRAS G12C mutated by tissue NGS; EGFR wild type; PD-L1 TPS 60% (22C3)"></textarea><small>Free text. The NLP extractor pulls the structured biomarkers from it.</small></label>
<label class="field"><span>Clinical findings</span><textarea name="clinical" rows="4" placeholder="Brain metastases: absent&#10;Measurable disease (RECIST 1.1): yes"></textarea><small>One per line, as finding: value</small></label>
<label class="field"><span>Labs</span><textarea name="labs" rows="4" placeholder="Hemoglobin: 12.8 g/dL&#10;Platelets: 245,000/mm3"></textarea><small>One per line, as test: value</small></label>
<label class="field wide"><span>Prior therapies</span><textarea name="prior_therapies" rows="4" placeholder="One regimen per line, with response and date"></textarea></label>
<div class="wide reg-actions"><button class="btn primary" type="submit">Build patient record</button><span id="reg-msg" class="why warn" role="alert"></span></div>
</form>
<div id="reg-out" hidden><div class="section-head"><h2>Patient record</h2><span>Demo: nothing is sent or stored</span></div><pre id="reg-json"></pre>
<div class="card-actions"><a class="btn primary" id="reg-dl" href="#">Download JSON</a></div><p class="why">On save, the backend assigns the pseudonym ID and the NLP extractor turns the biomarker report into structured biomarkers.</p></div>
</details>
<div class="warning"><strong>Synthetic patients.</strong> Fictitious records for the demo. Records are pseudonymized and never carry names or document numbers. Clinical fields are shown as entered (pt-BR).</div>
<div class="info-row rules" id="rules-patients"></div>
<div id="plist"></div>
</section>

<footer class="footer"><span>LinkTrial · Connected care and research</span><span>Source: ClinicalTrials.gov API v2 · generated on __GENERATED__</span></footer>
</main></div></div>
<script>
const S=__DATA__;
const O=__OBS__;
const SETTINGS={metastatic:"Metastatic",advanced:"Advanced",locally_advanced:"Locally advanced",unresectable:"Unresectable",first_line:"First line",previously_treated:"Previously treated",recurrent_relapsed:"Recurrent/relapsed",refractory:"Refractory",adjuvant:"Adjuvant",neoadjuvant:"Neoadjuvant",early_stage:"Early stage"};
// ponytail: display labels only; the data keys (linktrial/ctgov.py tumor_groups) stay in Portuguese for filtering
const GROUPS={"Hematológico":"Hematologic","Pulmão":"Lung","Mama":"Breast","Ginecológico":"Gynecologic","Colorretal":"Colorectal","Gástrico/Esôfago":"Gastric/Esophageal","Próstata":"Prostate","Urológico":"Urologic","Suporte/Qualidade de vida":"Supportive care/Quality of life","Tumores sólidos (geral)":"Solid tumors (general)","Pâncreas/Fígado/Vias biliares":"Pancreas/Liver/Biliary","Cabeça e pescoço":"Head and neck","Sarcoma":"Sarcoma","Pele/Melanoma":"Skin/Melanoma","Neuroendócrino":"Neuroendocrine","SNC":"CNS","Pediátrico (embrionários)":"Pediatric (embryonal)","Outros":"Other","Tireoide":"Thyroid"};
// Engine decisions (linktrial/decision.py TIERS), in tier order: label, pill color, match-banner class, symbol
const TIER={MATCH_PROVAVEL:["Likely match","green","","✓"],MATCH_POSSIVEL:["Possible match","amber","possible","✦"],REVISAO_NECESSARIA:["Review needed","blue","review","◇"],INELEGIVEL:["Ineligible at pre-screening","red","barrier","!"]};
const SEX={FEMALE:"Female",MALE:"Male"};
const TG=g=>GROUPS[g]||g;
const PH=p=>(p||[]).map(x=>x.replace("EARLY_","Early ").replace("PHASE","Phase ")).join("/")||"Observational/NA";
const ART=p=>(p||[]).includes("PHASE3")?"":(p||[]).includes("PHASE2")?"blue":"purple";
const HELIX=`<div class="helix" aria-hidden="true">${[...Array(10)].map((_,i)=>`<i style="--i:${i}"></i>`).join("")}</div>`;
const PIN=`<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0 M15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0"/></svg>`;
const $=id=>document.getElementById(id);let cat="";
const nf=n=>n.toLocaleString("en-US");
const pct=(a,b)=>b?Math.round(a/b*1000)/10:0;
const esc=t=>String(t).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const fmtT=s=>new Date(s).toLocaleString("en-US",{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit",hourCycle:"h23"});
const RM=matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- Overview ---------- */
const allSites=S.flatMap(s=>s.sites),recSites=allSites.filter(x=>x[3]==="R");
const hospitals=new Set(recSites.map(x=>x[0])).size;
const structured=S.filter(s=>s.features.ecog_max!=null||s.features.biomarkers_inclusion.length).length;
const decided=O.patients.filter(p=>O.latest[p.id]).length;
// A patient is linked to a trial when the latest run gives a likely or possible match
const LINKS=Object.entries(O.top).flatMap(([pid,rows])=>rows.filter(r=>r[2]==="MATCH_PROVAVEL"||r[2]==="MATCH_POSSIVEL")
 .map(([nct,title,d,blk,pend,js,site,inc,exc,cohort])=>({pid,nct,title,d,pend,site,inc,exc,cohort})));
const linkedPatients=new Set(LINKS.map(l=>l.pid)).size;
const STATS=[["Active trials",O.active,pct(O.active,O.total),`${nf(O.active)} of ${nf(O.total)} synced trials still active`],
 ["Recruiting hospitals",hospitals,pct(recSites.length,allSites.length),`${pct(recSites.length,allSites.length)}% of ${nf(allSites.length)} trial sites recruiting now`],
 ["Trials with structured criteria",structured,pct(structured,S.length),`ECOG or biomarkers parsed in ${pct(structured,S.length)}%`],
 ["Patients linked to a trial",linkedPatients,pct(linkedPatients,O.patients.length),`${linkedPatients} of ${O.patients.length} patients have a likely or possible match`]];
$("ov-stats").innerHTML=STATS.map(([label,v,p,note])=>`<div class="stat" style="--p:${p}"><div class="ring-wrap"><svg class="ring" viewBox="0 0 36 36" aria-hidden="true"><circle class="track" cx="18" cy="18" r="15.9"/><circle class="val" cx="18" cy="18" r="15.9" pathLength="100"/></svg><strong data-n="${v}">${nf(v)}</strong><em>${p}%</em></div><div><small>${label}</small><span class="stat-note">${note}</span></div><i class="bar" aria-hidden="true"></i></div>`).join("");
function countUp(){if(RM)return;document.querySelectorAll("#ov-stats strong[data-n]").forEach(el=>{const n=+el.dataset.n,t0=performance.now();
 const tick=t=>{const k=Math.min(1,Math.max(0,(t-t0)/1200));el.textContent=nf(Math.round(n*(1-(1-k)**3)));if(k<1)requestAnimationFrame(tick)};requestAnimationFrame(tick)})}
const latest=Object.values(O.latest),n=O.patients.length;
const STEPS=[["Registered",n,`${n} records`],["Pre-filtered",latest.length,`${Math.max(0,...latest.map(r=>r.n_prefiltered))} of ${nf(O.active)} trials each`],
 ["AI review",latest.filter(r=>r.n_deep).length,`top ${Math.max(0,...latest.map(r=>r.n_deep))} trials each`],["Decision",decided,"human review next"]];
$("stepper").innerHTML=STEPS.map(([t,c,s])=>`<div class="step${c?" done":""}"><b>${c}</b>${t}<small>${s}</small></div>`).join("");
const tierBar=c=>{const tot=Object.values(c).reduce((a,b)=>a+b,0)||1;return `<div class="tiers" role="img" aria-label="${Object.keys(TIER).filter(k=>c[k]).map(k=>`${c[k]} ${TIER[k][0]}`).join(", ")}">${Object.keys(TIER).map((k,i)=>c[k]?`<i class="t${i}" style="--n:${c[k]/tot*100}"></i>`:"").join("")}</div>`};
const tierPills=c=>`<div class="legend">${Object.keys(TIER).filter(k=>c[k]).map(k=>`<span class="pill ${TIER[k][1]}">${c[k]} ${TIER[k][0]}</span>`).join("")}</div>`;
$("funnels").innerHTML=latest.map(r=>`<div class="funnel-row"><div class="funnel-head"><strong>${esc(r.patient_id)}</strong><span>${nf(r.n_active)} active → ${r.n_prefiltered} pre-filtered → ${r.n_deep} in AI review</span></div>${tierBar(r.counts)}${tierPills(r.counts)}</div>`).join("");
const ev=Object.values(O.events).reduce((a,b)=>a+b,0),lr=latest[0]||{};
$("features").innerHTML=[["Daily registry sync",`CRUD sync with ClinicalTrials.gov every day at 06:00 (scripts/scheduler.py or the Windows task): content-hash diff, soft delete and reactivation of trials.`],
 ["Audit trail",`${nf(ev)} study events recorded: ${Object.entries(O.events).map(([k,v])=>`${nf(v)} ${k.toLowerCase()}`).join(" · ")}.`],
 ["AI review",`Ranks the ${lr.n_prefiltered||0} pre-filtered trials per patient, then reads the top ${lr.n_deep||0} criterion by criterion and cites evidence from the record.`],
 ["Judgment cache",`${nf(O.caches.llm_cache+O.caches.jev_cache)} AI review judgments cached, so re-runs stay fast and stable.`]]
 .map(([t,d])=>`<dt>${t}</dt><dd>${d}</dd>`).join("");
const TL=[...O.runs.map(r=>({at:r.started_at,t:`Registry sync #${r.id} · ${r.status}`,d:`${nf(r.fetched)} fetched · ${r.created} created · ${r.updated} updated · ${r.unchanged} unchanged · ${r.deactivated} deactivated · ${r.reactivated} reactivated`})),
 ...O.reports.map(r=>({at:r.at,t:`Match run · ${r.patient_id}`,d:`${r.n_prefiltered} pre-filtered · ${r.n_deep} in AI review — ${Object.keys(TIER).filter(k=>r.counts[k]).map(k=>`${r.counts[k]} ${TIER[k][0].toLowerCase()}`).join(", ")}`}))]
 .sort((a,b)=>b.at.localeCompare(a.at));
$("timeline").innerHTML=TL.map(e=>`<li><strong>${esc(e.t)}</strong><p>${esc(e.d)}</p><small>${fmtT(e.at)}</small></li>`).join("");

/* ---------- Criteria review ---------- */
// Verdicts come from linktrial/decision.py. Inclusion MET is good; exclusion MET means the patient HAS the exclusion.
const VERD={inc:{MET:["Met","green","✓"],NOT_MET:["Not met","red","!"],UNKNOWN:["To confirm","amber","◇"]},
 exc:{MET:["Present","red","!"],NOT_MET:["Absent","green","✓"],UNKNOWN:["To confirm","amber","◇"]}};
const blocks=(t,v)=>t==="inc"?v==="NOT_MET":v==="MET";
const state=(t,v)=>blocks(t,v)?"no":v==="UNKNOWN"?"tbd":"ok";
const RULES=`<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m12 2 8 4v6c0 6-8 10-8 10S4 18 4 12V6l8-4 M8 12l3 3 5-6"/></svg><div><p><strong>Match rule:</strong> the patient must meet every inclusion criterion and have none of the exclusion criteria. AI review checks each one against the record and quotes the evidence.</p>
 <details><summary>How the labels are decided</summary><p><b>Likely match:</b> every criterion confirmed. <b>Possible match:</b> nothing fails and up to ${O.max_pending} items need confirmation.
 <b>Review needed:</b> more than ${O.max_pending} items need confirmation. <b>Ineligible at pre-screening:</b> an inclusion criterion is not met or an exclusion criterion is present. The study team confirms eligibility.</p></details></div>`;
$("rules-links").innerHTML=RULES;$("rules-patients").innerHTML=RULES;
const counts=c=>c[2]!=="NOT_APPLICABLE"&&c[6];
function cbar(list,t){const ev=list.filter(counts),n=ev.length||1,k={ok:0,tbd:0,no:0};ev.forEach(c=>k[state(t,c[2])]++);
 return {k,ev:ev.length,html:`<div class="cbar" role="img" aria-label="${k.ok} satisfied, ${k.tbd} to confirm, ${k.no} blocking">${["ok","tbd","no"].map(s=>k[s]?`<i class="c-${s}" style="--n:${k[s]/n*100}"></i>`:"").join("")}</div>`}}
const critItem=(c,t)=>{const [id,txt,v,evd,why,miss]=c,[label,color,sym]=VERD[t][v];
 const detail=v==="UNKNOWN"?(miss?`Missing: ${esc(miss)}`:esc(why)):`${evd?`Evidence: “${esc(evd)}”. `:""}${esc(why)}`;
 return `<li><span class="pill ${color}">${sym} ${label}</span> <b>${esc(id)}</b>${esc(txt)}${detail?`<small lang="pt">${detail}</small>`:""}</li>`};
const ORDER={no:0,tbd:1,ok:2},clip=t=>t.length>90?t.slice(0,88)+"…":t,crits=n=>n===1?"criterion":"criteria";
// Two lines that answer "why": inclusion must all be met, exclusion must all be absent. A failing criterion replaces both.
function whyList(inc,exc){const I=cbar(inc,"inc").k,E=cbar(exc,"exc").k,ni=I.ok+I.tbd+I.no,ne=E.ok+E.tbd+E.no;
 const fails=[...inc.filter(c=>counts(c)&&blocks("inc",c[2])).map(c=>`Inclusion ${c[0]} not met: ${clip(c[1])}`),
  ...exc.filter(c=>counts(c)&&blocks("exc",c[2])).map(c=>`Exclusion ${c[0]} present: ${clip(c[1])}`)];
 const li=(k,sym,txt)=>`<li class="${k}"><b>${sym}</b><span>${esc(txt)}</span></li>`;
 if(fails.length)return `<ul class="why-list">${fails.map(f=>li("no","!",f)).join("")}</ul>`;
 return `<ul class="why-list">${I.tbd?li("tbd","◇",`Meets ${I.ok} of ${ni} inclusion ${crits(ni)} · ${I.tbd} to confirm`):li("ok","✓",ni===1?"Meets the 1 inclusion criterion":`Meets all ${ni} inclusion criteria`)}
 ${E.tbd?li("tbd","◇",`No exclusion criterion found · ${E.tbd} of ${ne} still to confirm`):li("ok","✓",ne?`Has none of the ${ne} exclusion ${crits(ne)}`:"No exclusion criterion applies")}</ul>`}
function section(list,t){const B=cbar(list,t),k=B.k,ev=list.filter(counts).sort((a,b)=>ORDER[state(t,a[2])]-ORDER[state(t,b[2])]);
 if(!ev.length)return "";
 const lab=t==="inc"?[`${k.ok} of ${B.ev} met`,k.no&&`${k.no} not met`,k.tbd&&`${k.tbd} to confirm`]:[`${k.ok} absent`,k.no&&`${k.no} present`,k.tbd&&`${k.tbd} to confirm`];
 return `<div class="csec"><div class="clabel"><strong>${t==="inc"?"Inclusion criteria · must all be met":"Exclusion criteria · must all be absent"}</strong><span>${lab.filter(Boolean).join(" · ")}</span></div>${B.html}<ul class="clist">${ev.map(c=>critItem(c,t)).join("")}</ul></div>`}
function review(inc,exc,cohort,extra=""){if(!inc)return "";
 const na=[...inc,...exc].filter(c=>!counts(c)).length;
 return `${whyList(inc,exc)}${extra}<details class="crit"><summary>Criteria review</summary>${section(inc,"inc")}${section(exc,"exc")}
 ${na?`<p class="why">${na} criteria do not apply${cohort?` to the cohort evaluated (<span lang="pt">${esc(cohort)}</span>)`:""} and do not count.</p>`:""}</details>`}

const refs={};  // ponytail: in-memory referral log; the real referral goes through the backend
const linkKey=l=>`${l.pid}|${l.nct}`;
const linkRow=l=>{const sent=refs[linkKey(l)];
 return `<li class="link-row"><div><span class="pill ${TIER[l.d][1]}">${TIER[l.d][0]}</span> <strong>${esc(l.pid)}</strong> → <a href="https://clinicaltrials.gov/study/${esc(l.nct)}" target="_blank" rel="noopener">${esc(l.nct)}</a> ${esc(l.title)}
 <small>${l.site?`Recruiting hospital in the patient's state: ${esc(l.site[0])} · ${esc(l.site[1])} / ${esc(l.site[2])}`:"No recruiting hospital in the patient's state"}</small>${review(l.inc,l.exc,l.cohort)}</div>
 ${sent?`<span class="pill green dot">Referred · ${sent}</span>`:`<button class="btn small primary" data-link="${esc(linkKey(l))}">Refer patient →</button>`}</li>`};
function renderLinks(){const n=Object.keys(refs).length;
 $("links-sum").textContent=`${linkedPatients} of ${O.patients.length} patients linked to ${new Set(LINKS.map(l=>l.nct)).size} trials · ${n} referred · ${LINKS.length-n} awaiting referral`;
 $("links").innerHTML=LINKS.map(linkRow).join("")||"<li>No likely or possible matches yet.</li>"}
$("links").onclick=e=>{const b=e.target.closest("[data-link]");if(!b)return;
 refs[b.dataset.link]=new Date().toLocaleTimeString("en-US",{hour:"2-digit",minute:"2-digit",hourCycle:"h23"});renderLinks()};
renderLinks();

/* ---------- Find trials ---------- */
const cnt={};S.forEach(s=>s.tumor_groups.forEach(g=>cnt[g]=(cnt[g]||0)+1));
$("cats").innerHTML=`<button class="chip active" data-c="">All ${S.length}</button>`+Object.entries(cnt).sort((a,b)=>b[1]-a[1]).map(([g,n])=>`<button class="chip" data-c="${g}">${TG(g)} ${n}</button>`).join("");
$("cats").onclick=e=>{const t=e.target.closest(".chip");if(!t)return;cat=t.dataset.c;document.querySelectorAll(".chip").forEach(x=>x.classList.toggle("active",x===t));render()};
const UFS=[...new Set(S.flatMap(s=>s.states_br))].sort();
UFS.forEach(u=>{$("uf").insertAdjacentHTML("beforeend",`<option>${u}</option>`);$("reg-uf").insertAdjacentHTML("beforeend",`<option>${u}</option>`)});
Object.entries(SETTINGS).forEach(([k,v])=>{$("setting").insertAdjacentHTML("beforeend",`<option value="${k}">${v}</option>`);$("reg-settings").insertAdjacentHTML("beforeend",`<label><input type="checkbox" name="settings" value="${k}">${v}</label>`)});
Object.entries(GROUPS).forEach(([k,v])=>$("reg-tg").insertAdjacentHTML("beforeend",`<option value="${k}">${v}</option>`));
const bc={};S.forEach(s=>s.features.biomarkers_inclusion.forEach(b=>bc[b]=(bc[b]||0)+1));
$("bios").innerHTML=Object.entries(bc).sort((a,b)=>b[1]-a[1]).slice(0,16).map(([b])=>`<label><input type="checkbox" value="${b}">${b}</label>`).join("");
document.querySelectorAll(".filters input,.filters select,#q").forEach(el=>el.addEventListener("input",render));
$("list").onclick=e=>{const b=e.target.closest("[data-refer]");if(b)alert(`Demo: referral sent to the research coordinator at ${b.dataset.refer}.`)};
const siteLabel=x=>`${x[0]} · ${x[1]}${x[2]?" / "+x[2]:""}`;
const siteItem=x=>`<li>${esc(siteLabel(x))}${x[3]==="N"?" <span>· not yet recruiting</span>":""}</li>`;
// Selected state first, then recruiting before not-yet-recruiting
const siteRank=(x,uf)=>(uf&&x[2]===uf?0:2)+(x[3]==="R"?0:1);
const sortSites=(s,uf)=>[...s.sites].sort((a,b)=>siteRank(a,uf)-siteRank(b,uf));
function sitesHtml(s,uf){
 const sites=sortSites(s,uf);
 const rec=sites.filter(x=>x[3]==="R").length,top=sites.slice(0,3),rest=sites.length-top.length;
 return `<div class="site-list">${PIN}<div><strong>Recruiting hospitals in Brazil · ${rec}</strong><ul>${top.map(siteItem).join("")}</ul>${rest>0?`<details><summary>All ${sites.length} sites</summary><ul>${sites.slice(3).map(siteItem).join("")}</ul></details>`:""}</div></div>`}
function evaluate(s,p){let score=50,why=[],warn=[];const f=s.features;
 if(p.age){if(s.min_age_years!=null&&p.age<s.min_age_years)return null;if(s.max_age_years!=null&&p.age>s.max_age_years)return null;why.push("age ok")}
 if(p.sex){if(s.sex!=="ALL"&&s.sex!==p.sex)return null;why.push("sex ok")}
 if(p.ecog!==""){if(f.ecog_max!=null){if(+p.ecog>f.ecog_max)return null;why.push(`ECOG ≤ ${f.ecog_max}`);score+=10}else warn.push("ECOG not structured")}
 if(p.uf){if(!s.states_br.includes(p.uf))return null;why.push(`site in ${p.uf}`);score+=15}
 if(p.setting){if(f.disease_setting.includes(p.setting)){score+=10;why.push(SETTINGS[p.setting])}else score-=10}
 p.bios.forEach(b=>{if(f.biomarkers_inclusion.includes(b)){score+=15;why.push(`${b} cited in inclusion`)}if(f.biomarkers_exclusion.includes(b)){score-=20;warn.push(`${b} cited in exclusion`)}});
 score+=Math.min(10,s.n_sites_br_recruiting);return{score:Math.max(0,Math.min(100,score)),why,warn}}
function card(s,r,uf){const f=s.features,first=sortSites(s,uf)[0];
 return `<article class="study-card"><div class="study-art ${ART(s.phases)}"><span class="pill blue">${PH(s.phases).toUpperCase()}</span><span class="art-code">${esc(s.nct_id)}</span>${HELIX}</div>
 <div class="study-body">${s.acronym?`<h3>${esc(s.acronym)}</h3><p class="subtitle">${esc(s.brief_title)}</p>`:`<h3 class="long">${esc(s.brief_title)}</h3>`}
 ${sitesHtml(s,uf)}
 <div class="meta">${esc(s.lead_sponsor)} · <span title="Pre-screening fit score (a ranking, not a probability)">fit ${r.score}</span></div>
 <div>${s.tumor_groups.map(g=>`<span class="pill purple">${TG(g)}</span>`).join("")}${f.ecog_max!=null?`<span class="pill">ECOG ≤ ${f.ecog_max}</span>`:""}${f.biomarkers_inclusion.map(b=>`<span class="pill green">${b}</span>`).join("")}${f.excludes_brain_mets?`<span class="pill red strike">CNS mets</span>`:""}${f.disease_setting.slice(0,3).map(k=>`<span class="pill">${SETTINGS[k]}</span>`).join("")}</div>
 ${r.why.length?`<div class="why">✓ ${r.why.join(" · ")}</div>`:""}${r.warn.length?`<div class="why warn">! ${r.warn.join(" · ")}</div>`:""}
 <details class="crit"><summary>Inclusion criteria (${s.inclusion_criteria.length})</summary><ol>${s.inclusion_criteria.map(c=>`<li>${esc(c)}</li>`).join("")}</ol></details>
 <details class="crit"><summary>Exclusion criteria (${s.exclusion_criteria.length})</summary><ol>${s.exclusion_criteria.map(c=>`<li>${esc(c)}</li>`).join("")}</ol></details>
 <div class="card-actions"><a class="btn" target="_blank" rel="noopener" href="${s.url}">ClinicalTrials.gov</a>${first?`<button class="btn primary" data-refer="${esc(first[0])}">Refer patient →</button>`:""}</div>
 <div class="study-note">Final eligibility is decided by the study team.</div></div></article>`}
function render(){const p={age:+$("age").value||0,sex:$("sex").value,ecog:$("ecog").value,uf:$("uf").value,setting:$("setting").value,
 bios:[...document.querySelectorAll("#bios input:checked")].map(x=>x.value),q:$("q").value.toLowerCase()};
 let out=[];for(const s of S){if(cat&&!s.tumor_groups.includes(cat))continue;
  if(p.q&&!JSON.stringify([s.nct_id,s.brief_title,s.lead_sponsor,s.interventions,s.conditions]).toLowerCase().includes(p.q))continue;
  const r=evaluate(s,p);if(r)out.push([s,r])}
 out.sort((a,b)=>b[1].score-a[1].score);$("count").textContent=`${out.length} trials compatible with the profile`;
 $("list").innerHTML=out.slice(0,120).map(([s,r])=>card(s,r,p.uf)).join("")}
render();

/* ---------- Patients ---------- */
const recordDl=(t,o)=>Object.keys(o||{}).length?`<dt>${t}</dt><dd lang="pt">${Object.entries(o).map(([k,v])=>`${esc(k)}: ${esc(v)}`).join("<br>")}</dd>`:"";
const WHY={MATCH_PROVAVEL:"Why it matches",MATCH_POSSIVEL:"Why it matches",REVISAO_NECESSARIA:"What still needs review",INELEGIVEL:"Why it is not a match"};
const ncta=id=>`<a href="https://clinicaltrials.gov/study/${esc(id)}" target="_blank" rel="noopener">${esc(id)}</a>`;
function patientCard(p){const r=O.latest[p.id],top=O.top[p.id]||[],runs=O.reports.filter(x=>x.patient_id===p.id).length,best=top[0],rest=top.slice(1);
 const bestHtml=best?(([id,t,d,blk,pend,js,site,inc,exc,cohort])=>`<div class="match-banner ${TIER[d][2]}"><span class="match-symbol">${TIER[d][3]}</span><div><strong>${TIER[d][0]}</strong><small>${esc(id)} · ${esc(t)}</small></div></div>
 <div class="best"><h3>${WHY[d]}</h3>${review(inc,exc,cohort,`<p class="site">${site?`Recruiting hospital in ${esc(p.uf)}: ${esc(site[0])} · ${esc(site[1])}`:`No recruiting hospital in ${esc(p.uf)}`} · ${ncta(id)}</p>`)}</div>`)(best):"";
 return `<section class="panel"><div class="p-head"><span class="avatar">${esc(p.id.split("-").pop())}</span><div><strong>${esc(p.id)}</strong><small>${p.age} y · ${SEX[p.sex]||esc(p.sex)} · ${esc(p.uf)} · ${TG(p.tumor_group)} · ECOG ${p.ecog??"n/a"}</small></div><a class="btn small" href="#find" data-profile="${esc(p.id)}">Find trials for this profile →</a></div>
 <p class="p-dx" lang="pt">${esc(p.diagnosis||"")}</p>
 ${r?`${bestHtml}${rest.length?`<details class="more"><summary>Other trials reviewed · ${rest.length} <span>· latest run ${fmtT(r.at)} · ${runs} run${runs>1?"s":""}</span></summary>${tierBar(r.counts)}
 <ol class="results">${rest.map(([id,t,d,blk,pend,js,site,inc,exc,cohort])=>`<li><span class="pill ${TIER[d][1]}">${TIER[d][0]}</span> ${ncta(id)} ${esc(t)}${review(inc,exc,cohort)}</li>`).join("")}</ol></details>`:""}`
 :`<p class="why">No match run yet. Run <code>python scripts/match.py patients/${esc(p.id)}.json</code></p>`}
 <details class="crit"><summary>Clinical record</summary><div>${(p.settings||[]).map(k=>`<span class="pill">${SETTINGS[k]||esc(k)}</span>`).join("")}</div><dl>${recordDl("Biomarkers",p.biomarkers)}${recordDl("Clinical findings",p.clinical)}${recordDl("Labs",p.labs)}${(p.prior_therapies||[]).length?`<dt>Prior therapies</dt><dd lang="pt">${p.prior_therapies.map(esc).join("<br>")}</dd>`:""}${p.notes?`<dt>Notes</dt><dd lang="pt">${esc(p.notes)}</dd>`:""}</dl></details></section>`}
$("plist").innerHTML=O.patients.map(patientCard).join("");
$("plist").onclick=e=>{const a=e.target.closest("[data-profile]");if(!a)return;const p=O.patients.find(x=>x.id===a.dataset.profile);
 $("age").value=p.age;$("sex").value=p.sex;$("ecog").value=p.ecog??"";$("uf").value=UFS.includes(p.uf)?p.uf:"";$("setting").value=(p.settings||[]).find(k=>SETTINGS[k])||"";
 document.querySelectorAll("#bios input").forEach(x=>x.checked=false);$("profile").open=true;render()};
const lines=t=>t.split("\n").map(x=>x.trim()).filter(Boolean);
const pairs=t=>Object.fromEntries(lines(t).map(l=>{const i=l.indexOf(":");return i>0?[l.slice(0,i).trim(),l.slice(i+1).trim()]:[l,""]}));
$("reg").onsubmit=e=>{e.preventDefault();const f=e.target,d=new FormData(f),msg=$("reg-msg");
 f.querySelectorAll("[aria-invalid]").forEach(x=>x.removeAttribute("aria-invalid"));
 const bad=[...f.querySelectorAll("[required]")].filter(x=>!x.checkValidity());bad.forEach(x=>x.setAttribute("aria-invalid","true"));
 if(bad.length){msg.textContent="! Fill in the required fields";bad[0].focus();$("reg-out").hidden=true;return}
 // ponytail: id and structured biomarkers are left out on purpose; the backend and the NLP extractor fill them on save
 const rec={_aviso:"Pseudonymized record - no direct identifiers",age:+d.get("age"),sex:d.get("sex"),uf:d.get("uf"),tumor_group:d.get("tumor_group"),
  diagnosis:d.get("diagnosis").trim(),ecog:+d.get("ecog"),settings:d.getAll("settings"),biomarker_report:d.get("biomarker_report").trim(),
  clinical:pairs(d.get("clinical")),labs:pairs(d.get("labs")),prior_therapies:lines(d.get("prior_therapies"))};
 const json=JSON.stringify(rec,null,1),dl=$("reg-dl");
 $("reg-json").textContent=json;if(dl.href.startsWith("blob:"))URL.revokeObjectURL(dl.href);
 dl.href=URL.createObjectURL(new Blob([json],{type:"application/json"}));dl.download="patient-record.json";
 msg.textContent="";$("reg-out").hidden=false};

/* ---------- Router ---------- */
const VIEWS={overview:"Overview",find:"Find trials",patients:"Patients"};
function show(){const h=location.hash.slice(1),v=VIEWS[h]?h:"overview";
 for(const k in VIEWS)$("v-"+k).hidden=k!==v;
 document.querySelectorAll(".nav button").forEach(b=>{const on=b.dataset.view===v;b.classList.toggle("active",on);on?b.setAttribute("aria-current","page"):b.removeAttribute("aria-current")});
 $("crumb").textContent="/ "+VIEWS[v];if(v==="overview")countUp();scrollTo(0,0)}
document.querySelector(".nav").onclick=e=>{const b=e.target.closest("[data-view]");if(b)location.hash=b.dataset.view};
addEventListener("hashchange",show);show();
</script></body></html>"""


def ds_css():
    """CSS custom properties from the design system tokens, followed by its stylesheet."""
    tokens = json.loads((DS / "tokens.json").read_text(encoding="utf-8"))
    values = {t["name"]: t["value"] for family in ("color", "shadow") for t in tokens[family]["tokens"]}
    # ponytail: tokens.json only uses one alias level ("{navy}"), so a single lookup resolves it
    resolve = lambda v: values[v[1:-1]] if v.startswith("{") else v
    root = ":root{" + ";".join(f"--{name}:{resolve(v)}" for name, v in values.items()) + "}"
    return root + "\n" + (DS / "bundle.css").read_text(encoding="utf-8")


def logo_uri():
    return "data:image/png;base64," + base64.b64encode((DS / "linktrial-simbolo-oficial.png").read_bytes()).decode()


def slim_study(s):
    sites = [[x["facility"], x["city"], x["uf"], SITE_STATUS[x["status"]]] for x in s["sites_br"] if x["status"] in SITE_STATUS]
    return {**{k: s[k] for k in KEEP}, "sites": sites}


def report_summary(r):
    return {"patient_id": r["patient_id"], "at": r["generated_at"], "n_active": r["n_studies_active"],
            "n_prefiltered": r["n_prefiltered"], "n_deep": r.get("n_deep") or len(r["results"]),
            "counts": Counter(x["decision"] for x in r["results"])}


def criteria(items, leaf):
    """[id, criterion, verdict, evidence, rationale, missing data, applies] per criterion.

    `applies` mirrors decide_with_cohorts: untagged criteria and those of the chosen cohort (or its ancestors) count.
    """
    def applies(c):
        k = (c.get("cohort") or "").strip()
        return not leaf or k == "" or k == leaf or _is_ancestor(k, leaf)
    return [[c["id"], c["criterion"], c["verdict"], c.get("evidence", ""), c.get("rationale", ""), c.get("missing_data", ""),
             applies(c)] for c in items]


def first_site(x):
    s = (x.get("sites_in_patient_uf") or [None])[0]
    return [s["facility"], s["city"], s["uf"]] if s else None


def observability():
    """Sync runs, audit trail and caches from data/linktrial.db plus patients and match reports."""
    conn = sqlite3.connect(DATA / "linktrial.db")
    cur = conn.execute("select id, started_at, status, fetched, created, updated, unchanged, deactivated, reactivated"
                       " from sync_runs order by id")
    cols = [c[0] for c in cur.description]
    runs = [dict(zip(cols, row)) for row in cur]
    events = dict(conn.execute("select event, count(*) from study_events group by event"))
    active, total = conn.execute("select sum(active), count(*) from studies").fetchone()
    caches = {t: conn.execute(f"select count(*) from {t}").fetchone()[0] for t in ("llm_cache", "jev_cache")}
    conn.close()
    patients = [json.loads(f.read_text(encoding="utf-8")) for f in sorted((ROOT / "patients").glob("*.json"))]
    reports = [json.loads(f.read_text(encoding="utf-8")) for f in sorted((ROOT / "reports").glob("*.json"))]
    latest = {}
    for r in reports:  # file names sort by generation time, so the last one per patient wins
        latest[r["patient_id"]] = r
    top = {pid: [[x["nct_id"], x["title"], x["decision"], len(x["blocking"]), len(x["pending"]), x.get("jev_score"), first_site(x),
                  criteria(x["inclusion"], x.get("cohort")), criteria(x["exclusion"], x.get("cohort")), x.get("cohort") or ""]
                 for x in sorted(r["results"], key=lambda x: (TIERS[x["decision"]], -(x.get("jev_score") or 0)))]
           for pid, r in latest.items()}
    return {"runs": runs, "events": events, "active": active, "total": total, "caches": caches,
            "patients": patients, "reports": [report_summary(r) for r in reports],
            "latest": {pid: report_summary(r) for pid, r in latest.items()}, "top": top,
            "max_pending": MAX_PENDING_FOR_POSSIBLE}


def embed(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    studies = json.loads((DATA / "studies_br.json").read_text(encoding="utf-8"))
    summary = json.loads((DATA / "summary.json").read_text(encoding="utf-8"))
    html = (TEMPLATE.replace("__CSS__", ds_css()).replace("__LOGO__", logo_uri())
            .replace("__GENERATED__", summary["generated_at"][:10]).replace("__OBS__", embed(observability()))
            .replace("__DATA__", embed([slim_study(s) for s in studies])))
    out = DATA / "linktrial_vitrine.html"
    out.write_text(html, encoding="utf-8")
    logging.info("%s %d studies %.1f MB", out, len(studies), out.stat().st_size / 1e6)


if __name__ == "__main__":
    main()
