// Drives the real LinkTrial vitrine as a video: window.renderAt(t) sets the whole frame from t (seconds).
(() => {
const $ = s => document.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const VW = innerWidth, VH = innerHeight;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const prog = (t, a, b) => clamp((t - a) / (b - a));
const io = x => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const out = x => 1 - Math.pow(1 - clamp(x), 3);
const lerp = (a, b, k) => a + (b - a) * k;
const LOGO = $('.brand img').src;
const shell = $('.shell');

const css = document.createElement('style');
css.textContent = `
*,*:before,*:after{animation:none!important;transition:none!important;caret-color:transparent!important}
html,body{overflow:hidden!important}
.shell{transform-origin:0 0}
#stage{position:fixed;inset:0;pointer-events:none;z-index:9999;font-family:'DM Sans',sans-serif}
#dip{position:absolute;inset:0;background:var(--bg);opacity:0}
.card{position:absolute;inset:0;background:var(--navy);color:#fff;display:flex;align-items:center;overflow:hidden}
.card:before{content:'';position:absolute;inset:-20%;background:radial-gradient(circle at 78% 50%,#5ff5cf14,transparent 46%)}
.brandmark{position:absolute;left:72px;top:58px;display:flex;align-items:center;gap:12px;font:800 26px Manrope;letter-spacing:-.8px}
.brandmark img{width:46px}.brandmark b,.ou-name b{color:#5ff5cf;font-weight:800}
#hook .copy{position:relative;margin-left:72px;max-width:760px}
#hook h1{font:800 64px/1.06 Manrope;letter-spacing:-2.4px;margin:0 0 26px;color:#fff}
#hook h2{font:800 46px/1.1 Manrope;letter-spacing:-1.6px;margin:0;color:#5ff5cf}
.hk-ring{position:absolute;right:120px;top:50%;width:400px;height:400px;margin-top:-200px;display:grid;place-content:center;text-align:center}
.hk-ring svg{position:absolute;inset:0;transform:rotate(-90deg)}
.hk-ring circle{fill:none;stroke-width:2.2}.hk-ring .tr{stroke:#ffffff14}.hk-ring .vl{stroke:#5ff5cf;stroke-linecap:round}
.hk-ring strong{font:800 118px/1 Manrope;letter-spacing:-5px;position:relative}
.hk-ring em{font-style:normal;font-size:17px;letter-spacing:2.4px;color:#9dbbc7;margin-top:10px;position:relative;text-transform:uppercase}
#outro{flex-direction:column;justify-content:center;text-align:center}
#outro img{width:150px;position:relative}
.ou-name{font:800 82px Manrope;letter-spacing:-3px;margin:14px 0 6px;position:relative}
.ou-tag{font:800 38px Manrope;letter-spacing:-1.2px;color:#fff;position:relative}
.ou-small{margin-top:26px;font-size:17px;color:#9dbbc7;letter-spacing:.2px;position:relative}
#cap{position:absolute;left:44px;bottom:40px;display:flex;align-items:center;gap:20px;background:var(--navy);color:#fff;border-radius:16px;padding:20px 28px 20px 20px;box-shadow:0 18px 50px #03112c40;max-width:820px}
#cap b{flex:none;width:58px;height:58px;border-radius:13px;background:#5ff5cf1c;color:#5ff5cf;display:grid;place-items:center;font:800 28px Manrope}
#cap strong{display:block;font:800 31px/1.15 Manrope;letter-spacing:-.9px}
#cap span{display:block;margin-top:6px;font-size:17px;color:#b9cdd7}
#cursor{position:absolute;left:0;top:0;width:30px;height:30px;filter:drop-shadow(0 3px 6px #03112c55)}
#cursor path{fill:#03112c;stroke:#fff;stroke-width:1.5;stroke-linejoin:round}
#ping{position:absolute;width:56px;height:56px;margin:-28px 0 0 -28px;border-radius:50%;border:3px solid var(--teal);opacity:0}
.hl-pid input{background:#e4f4ec!important;color:#26735b!important;font-weight:700;border-color:#26735b!important}
.hl-block{background:#fae9e7;border-radius:8px;box-shadow:0 0 0 2px #a04d44 inset;padding-left:10px!important;padding-right:10px!important}
#link{justify-content:center}
#link:before{background:radial-gradient(circle at 50% 46%,#5ff5cf1f,transparent 42%)}
.lk-stage{position:absolute;left:50%;top:44%;width:504px;height:312px;margin:-156px 0 0 -252px}
.lk-stage svg,.lk-stage img{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.lk-glow{position:absolute;left:50%;top:55%;width:760px;height:760px;margin:-380px 0 0 -380px;border-radius:50%;background:radial-gradient(circle,#5ff5cf55,#5ff5cf00 60%)}
.lk-tag{position:absolute;top:44%;margin-top:-46px;width:330px;font-family:'DM Sans',sans-serif}
.lk-tag small{display:block;font-size:15px;letter-spacing:2.6px;text-transform:uppercase;color:#9dbbc7}
.lk-tag strong{display:block;font:800 40px/1.1 Manrope;letter-spacing:-1.2px;margin:6px 0 6px}
.lk-tag span{display:block;font-size:17px;color:#b9cdd7}
#lk-p{right:calc(50% + 300px);text-align:right}#lk-p strong{color:#fff}
#lk-t{left:calc(50% + 300px)}#lk-t strong{color:#5ff5cf}
.lk-res{position:absolute;left:0;right:0;top:calc(44% + 190px);text-align:center}
.lk-res strong{display:block;font:800 60px/1 Manrope;letter-spacing:-2px;color:#5ff5cf}
.lk-res span{display:block;margin-top:14px;font-size:20px;color:#d5e3ea}
.lk-dot{position:absolute;width:5px;height:5px;border-radius:50%;background:#5ff5cf;left:50%;top:50%}
`;
document.head.appendChild(css);

const stage = document.createElement('div');
stage.id = 'stage';
stage.innerHTML = `<div id="dip"></div>
<div id="cap"><b id="cap-n"></b><div><strong id="cap-t"></strong><span id="cap-s"></span></div></div>
<div id="ping"></div>
<svg id="cursor" viewBox="0 0 24 24"><path d="M5 2.5l14 10.6-6.2.9 3.6 7.4-2.9 1.4-3.6-7.5L5 19.6z"/></svg>
<section class="card" id="hook"><div class="brandmark"><img src="${LOGO}" alt=""><span>Link<b>Trial</b></span></div>
 <div class="copy"><h1 id="hk1">359 oncology trials are open in Brazil.</h1><h2 id="hk2">Which one fits your patient?</h2></div>
 <div class="hk-ring"><svg viewBox="0 0 36 36"><circle class="tr" cx="18" cy="18" r="16"/><circle id="hk-arc" class="vl" cx="18" cy="18" r="16" pathLength="100"/></svg><strong id="hk-num">0</strong><em>open trials</em></div></section>
<section class="card" id="link"><div class="lk-glow" id="lk-glow"></div>
 <div class="lk-tag" id="lk-p"><small>Patient</small><strong>SYN-002</strong><span>54 y · Breast HR+ HER2− · RS</span></div>
 <div class="lk-tag" id="lk-t"><small>Trial</small><strong>NCT07062965</strong><span>Recruiting · ONCOSITE, Ijuí / RS</span></div>
 <div class="lk-stage" id="lk-stage">
  <svg viewBox="0 0 252 156" id="lk-rings"><defs>
   <linearGradient id="lkw" x1="0" x2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#c9d3da"/></linearGradient>
   <linearGradient id="lkt" x1="0" x2="1"><stop offset="0" stop-color="#2fb8a6"/><stop offset="1" stop-color="#5ff5cf"/></linearGradient>
   <filter id="lkf" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
   <g id="lk-gw"><path id="lk-rw" d="M68 40a56 56 0 1 0 .01 0" fill="none" stroke="url(#lkw)" stroke-width="24" stroke-linecap="round" pathLength="100" filter="url(#lkf)"/></g>
   <g id="lk-gt"><path id="lk-rt" d="M172 152a56 56 0 1 0 -.01 0" fill="none" stroke="url(#lkt)" stroke-width="24" stroke-linecap="round" pathLength="100" filter="url(#lkf)"/></g>
  </svg>
  <img id="lk-logo" src="${LOGO}" alt="" style="-webkit-mask-image:radial-gradient(circle 52px at 48.4% 17%,transparent 98%,#000 100%);mask-image:radial-gradient(circle 52px at 48.4% 17%,transparent 98%,#000 100%)"><img id="lk-head" src="${LOGO}" alt="" style="clip-path:circle(52px at 48.4% 17%);transform-origin:48.4% 17%">
  <div id="lk-sparks"></div>
 </div>
 <div class="lk-res" id="lk-res"><strong>✦ Possible match</strong><span>All 5 inclusion criteria met · no exclusion criterion found</span></div></section>
<section class="card" id="outro"><img src="${LOGO}" alt=""><div class="ou-name">Link<b>Trial</b></div>
 <div class="ou-tag">From patient record to referral.</div><div class="ou-small">Pre-screening support · the study team confirms eligibility</div></section>`;
document.body.appendChild(stage);
const el = id => document.getElementById(id);

/* ---------- real-app handles ---------- */
const reg = el('reg'), F = n => reg.elements[n];
const pidField = reg.querySelector('input[disabled]');
const setting = name => $$('#reg-settings label').find(l => l.textContent.trim() === name)?.querySelector('input');
const linkRow = () => $$('#links li').find(li => li.textContent.includes('SYN-002'));
const card = () => $$('#plist > section').find(c => c.querySelector('.p-head strong')?.textContent === 'SYN-002');
const blockedRow = () => $$('.results li', card()).find(li => li.textContent.includes('NCT04669873'));
const funnel = () => $$('#funnels .funnel-row').find(r => r.textContent.includes('SYN-002'));
const DIAG = 'Invasive ductal carcinoma, HR+ HER2-, metastatic to liver and bone';
const BIO = 'ER positive 95%; PR positive 40%; HER2 negative (IHC 1+); PIK3CA not detected; ESR1 Y537S detected (liquid biopsy)';
const typed = (s, t, a, b) => s.slice(0, Math.round(s.length * prog(t, a, b)));
const VIEWS = { overview: 'Overview', patients: 'Patients' };

function setView(v) {
  for (const id of ['overview', 'find', 'patients']) { const s = el('v-' + id), h = id !== v; if (s.hidden !== h) s.hidden = h; }
  $$('.nav button').forEach(b => b.classList.toggle('active', b.dataset.view === v));
  el('crumb').textContent = '/ ' + VIEWS[v];
}
const setVal = (e, v) => { if (e && e.value !== v) e.value = v; };
const setOpen = (d, o) => { if (d && d.open !== o) d.open = o; };
function grow(els, k) { els.forEach(i => i.style.transform = k >= 1 ? '' : `scaleX(${k})`); }

/* ---------- camera ---------- */
const REGION = { x: 56, y: 44, w: VW - 112, h: VH - 230 };
function rectOf(...els) {
  const rs = els.filter(Boolean).map(e => e.getBoundingClientRect());
  const x = Math.min(...rs.map(r => r.left)), y = Math.min(...rs.map(r => r.top));
  return { x, y, w: Math.max(...rs.map(r => r.right)) - x, h: Math.max(...rs.map(r => r.bottom)) - y };
}
// A camera is the world point shown at the region centre plus a scale.
function fit(r, { maxH = Infinity, maxW = Infinity, smax = 2.2, region = REGION, align = 'center' } = {}) {
  r = { ...r, w: Math.min(r.w, maxW) };
  const h = Math.min(r.h, maxH), s = Math.min(region.w / r.w, region.h / h, smax);
  const cy = align === 'top' ? r.y + region.h / s / 2 - 8 / s : r.y + h / 2;
  return { x: r.x + r.w / 2, y: cy, s };
}
const mix = (A, B, k) => ({ x: lerp(A.x, B.x, k), y: lerp(A.y, B.y, k), s: Math.exp(lerp(Math.log(A.s), Math.log(B.s), k)) });
function apply(cam) {
  const cx = REGION.x + REGION.w / 2, cy = REGION.y + REGION.h / 2;
  cam.tx = cx - cam.x * cam.s; cam.ty = cy - cam.y * cam.s;
  shell.style.transform = `translate(${cam.tx}px,${cam.ty}px) scale(${cam.s})`;
  return cam;
}
// keys: [[t, () => camera], ...]; eases between consecutive keys.
function camera(t, keys) {
  shell.style.transform = 'none';
  let i = keys.length - 1;
  while (i > 0 && t < keys[i][0]) i--;
  const A = keys[i][1]();
  if (i === keys.length - 1) return apply(A);
  const [tb, fb] = keys[i + 1];
  return apply(mix(A, fb(), io(prog(t, keys[i][0], tb))));
}
const toScreen = (cam, e, fx = .5, fy = .5) => { const r = e.getBoundingClientRect(); return { x: r.left + r.width * fx, y: r.top + r.height * fy }; };

/* ---------- overlays ---------- */
function cursor(t, cam, path) {
  const c = el('cursor'), p = el('ping');
  if (!path) { c.style.opacity = 0; p.style.opacity = 0; return; }
  const { t0, t1, from, target, click, fade } = path;
  const to = toScreen(cam, target());
  const k = io(prog(t, t0, t1));
  const x = lerp(from.x, to.x, k), y = lerp(from.y, to.y, k);
  const press = t >= click && t < click + .14 ? .86 : 1;
  c.style.opacity = t < t0 ? 0 : 1 - prog(t, fade, fade + .25);
  c.style.transform = `translate(${x - 6}px,${y - 4}px) scale(${press})`;
  const pk = prog(t, click, click + .5);
  p.style.opacity = t >= click ? (1 - pk) * .9 : 0;
  p.style.left = x + 'px'; p.style.top = y + 'px'; p.style.transform = `scale(${.4 + pk})`;
}
const CAPS = [
  [3.3, 8.25, '1', 'Register the patient', 'Structured and pseudonymized. AI reads the biomarker report.'],
  [8.55, 10.85, '2', 'AI review, criterion by criterion', '359 trials → 40 pre-filtered → top 8 reviewed'],
  [11.2, 14.65, '✓', 'Match: every inclusion criterion met', 'No exclusion criterion found · 3 items still to confirm'],
  [14.95, 18.25, '!', 'No match: one inclusion criterion fails', 'I13 · No hematogenous metastases. She is metastatic.'],
  [18.55, 21.0, '3', 'Refer to a recruiting hospital', "ONCOSITE, Ijuí · in the patient's own state (RS)"],
];
function caption(t) {
  const c = CAPS.find(([a, b]) => t >= a - .05 && t < b + .3), box = el('cap');
  if (!c) { box.style.opacity = 0; return; }
  const [a, b, n, title, sub] = c, k = out(prog(t, a, a + .4)), o = 1 - prog(t, b, b + .25);
  el('cap-n').textContent = n; el('cap-t').textContent = title; el('cap-s').textContent = sub;
  box.style.opacity = Math.min(k, o);
  box.style.transform = `translateY(${(1 - k) * 24}px)`;
}
function dip(t) {
  const peaks = [8.4, 14.8, 18.4];
  el('dip').style.opacity = Math.max(0, ...peaks.map(p => 1 - Math.abs(t - p) / .17));
}

/* ---------- scenes ---------- */
function sceneRegister(t) {
  setView('patients');
  setOpen(el('register'), true);
  setVal(F('age'), typed('54', t, 3.55, 3.7));
  setVal(F('sex'), t >= 3.85 ? 'FEMALE' : '');
  setVal(F('uf'), t >= 4.05 ? 'RS' : '');
  setVal(F('tumor_group'), t >= 4.25 ? 'Mama' : '');
  setVal(F('ecog'), t >= 4.45 ? '1' : '');
  const met = setting('Metastatic'), prev = setting('Previously treated');
  if (met) met.checked = t >= 5.0; if (prev) prev.checked = t >= 5.15;
  setVal(F('diagnosis'), typed(DIAG, t, 5.25, 5.95));
  setVal(F('biomarker_report'), typed(BIO, t, 6.0, 7.1));
  const done = t >= 7.65;
  setVal(pidField, done ? 'SYN-002' : 'Assigned automatically on save');
  pidField.parentElement.classList.toggle('hl-pid', done);
  const focus = t < 3.75 ? F('age') : t < 3.95 ? F('sex') : t < 4.15 ? F('uf') : t < 4.35 ? F('tumor_group') : t < 4.6 ? F('ecog')
    : t < 5.2 ? null : t < 5.98 ? F('diagnosis') : t < 7.3 ? F('biomarker_report') : null;
  if (focus) { if (document.activeElement !== focus) focus.focus({ preventScroll: true }); } else document.activeElement?.blur();
  const first = pidField.closest('.field'), ecog = F('ecog').closest('.field');
  const diag = F('diagnosis').closest('.field'), bio = F('biomarker_report').closest('.field');
  const top = () => fit(rectOf(first, ecog), { smax: 1.55 });
  const mid = () => fit(rectOf(diag, bio), { smax: 1.6 });
  const all = () => fit(rectOf(first, bio), { smax: 1.3 });
  const cam = camera(t, [[2.8, top], [4.75, top], [5.25, mid], [7.15, mid], [7.6, all], [8.4, () => ({ ...all(), s: all().s * 1.03 })]]);
  cursor(t, cam, null);
}
function sceneReview(t) {
  setView('overview');
  const steps = $$('#stepper .step');
  steps.forEach((s, i) => { const k = out(prog(t, 8.6 + i * .36, 8.9 + i * .36)); s.style.opacity = .22 + .78 * k; s.style.transform = `scale(${.92 + .08 * k})`; });
  const fr = funnel();
  grow($$('.tiers i', fr), out(prog(t, 10.0, 10.7)));
  const pipe = () => fit(rectOf(el('stepper'), fr), { smax: 1.7 });
  camera(t, [[8.4, pipe], [11.0, () => ({ ...pipe(), s: pipe().s * 1.04 })]]);
  cursor(t, null, null);
}
function sceneMatch(t) {
  setView('patients');
  setOpen(el('register'), false);
  const c = card(), best = c.querySelector('.best'), crit = best.querySelector('details.crit');
  setOpen(c.querySelector('details.more'), false);
  setOpen(crit, t >= 12.3);
  grow($$('.cbar i', crit), out(prog(t, 12.35, 13.1)));
  const head = () => fit(rectOf(c.querySelector('.p-head'), best.querySelector('.site')), { maxW: 860, smax: 1.6 });
  const open = () => fit(rectOf(best.querySelector('h3'), best.querySelector('.csec')), { maxH: 520, smax: 1.4, align: 'top' });
  const cam = camera(t, [[11.0, head], [12.3, () => ({ ...head(), s: head().s * 1.03 })], [12.85, open], [14.8, () => ({ ...open(), y: open().y + 90 })]]);
  cursor(t, cam, { t0: 11.55, t1: 12.15, from: { x: VW * .78, y: VH * .82 }, target: () => crit.querySelector('summary'), click: 12.25, fade: 12.8 });
}
function sceneNoMatch(t) {
  setView('patients');
  setOpen(el('register'), false);
  setOpen(card().querySelector('.best details.crit'), false);
  setOpen(card().querySelector('details.more'), true);
  const row = blockedRow(), crit = row.querySelector('details');
  setOpen(crit, t >= 15.65);
  grow($$('.cbar i', crit), out(prog(t, 15.7, 16.5)));
  const i13 = $$('.clist li', crit).find(li => li.querySelector('b')?.textContent === 'I13');
  i13?.classList.toggle('hl-block', t >= 16.3);
  const head = () => fit(rectOf(row), { maxH: 110, maxW: 920, smax: 1.6 });
  const open = () => fit(rectOf(row), { maxH: 430, smax: 1.45, align: 'top' });
  const cam = camera(t, [[14.8, head], [15.7, head], [16.2, open], [18.4, () => ({ ...open(), s: open().s * 1.03 })]]);
  cursor(t, cam, { t0: 14.95, t1: 15.5, from: { x: VW * .8, y: VH * .75 }, target: () => crit.querySelector('summary'), click: 15.6, fade: 16.1 });
}
let referred = false;
function sceneRecruit(t) {
  setView('overview');
  let row = linkRow();
  setOpen(row.querySelector('details'), false);
  if (t >= 19.65 && !referred) { referred = true; row.querySelector('button[data-link]').click(); row = linkRow(); }
  const btn = row.querySelector('button[data-link]') || row.querySelector('.pill.green');
  const near = () => fit(rectOf(row), { smax: 1.55 });
  const wide = () => fit(rectOf(el('links-sum'), row), { smax: 1.35 });
  const cam = camera(t, [[18.4, near], [19.9, near], [20.5, wide], [21.2, () => ({ ...wide(), s: wide().s * 1.02 })]]);
  cursor(t, cam, { t0: 18.75, t1: 19.5, from: { x: VW * .55, y: VH * .9 }, target: () => btn, click: 19.6, fade: 20.3 });
}
function cards(t) {
  const hook = el('hook'), o = el('outro');
  const up = io(prog(t, 2.8, 3.3));
  hook.style.transform = `translateY(${-up * 100}%)`; hook.style.display = up >= 1 ? 'none' : '';
  const a = out(prog(t, .1, .55)), b = out(prog(t, .95, 1.4));
  el('hk1').style.opacity = a; el('hk1').style.transform = `translateY(${(1 - a) * 26}px)`;
  el('hk2').style.opacity = b; el('hk2').style.transform = `translateY(${(1 - b) * 26}px)`;
  const r = out(prog(t, .2, 1.6));
  el('hk-arc').style.strokeDasharray = `${r * 100} 100`;
  el('hk-num').textContent = Math.round(359 * r);
  const dn = io(prog(t, 21.0, 21.45));
  o.style.transform = `translateY(${(1 - dn) * 100}%)`; o.style.display = dn <= 0 ? 'none' : '';
  [...o.children].forEach((c, i) => { const k = out(prog(t, 21.3 + i * .14, 21.75 + i * .14)); c.style.opacity = k; c.style.transform = `translateY(${(1 - k) * 18}px)`; });
}

/* ---------- the link: patient and trial lock into the logo ---------- */
const L0 = 11.0, LDUR = 2.6;
const SPARKS = Array.from({ length: 34 }, (_, i) => { const a = i * 2.39996, r = .55 + ((i * 37) % 11) / 11; return { a, r, s: 3 + (i % 3) * 2 }; });
el('lk-sparks').innerHTML = SPARKS.map(() => '<i class="lk-dot"></i>').join('');
function linkCard(T) {
  const c = el('link'), u = T - L0;
  const inK = io(prog(T, L0 - .3, L0 + .05)), outK = io(prog(u, LDUR - .35, LDUR));
  c.style.display = inK <= 0 || outK >= 1 ? 'none' : '';
  c.style.transform = `translateY(${(1 - inK) * 100 - outK * 100}%)`;
  if (c.style.display) return;
  const lock = 1.15, fly = io(prog(u, .1, lock)), draw = out(prog(u, .05, lock - .1));
  const pre = u < lock;
  el('lk-rings').style.opacity = Math.min(clamp(draw * 12), 1 - prog(u, lock - .04, lock + .06));  // round caps draw a dot at zero length
  el('lk-gw').setAttribute('transform', `translate(${-190 * (1 - fly)} ${-26 * Math.sin(fly * Math.PI)}) rotate(${-140 * (1 - fly)} 68 96)`);
  el('lk-gt').setAttribute('transform', `translate(${190 * (1 - fly)} ${26 * Math.sin(fly * Math.PI)}) rotate(${140 * (1 - fly)} 172 96)`);
  el('lk-rw').style.strokeDasharray = `${draw * 100} 100`;
  el('lk-rt').style.strokeDasharray = `${draw * 100} 100`;
  const pop = prog(u, lock, lock + .45), sc = pre ? 1 : 1 + .09 * Math.sin(pop * Math.PI) * (1 - pop);
  const logo = el('lk-logo'); logo.style.opacity = prog(u, lock - .06, lock + .04); logo.style.transform = `scale(${sc})`;
  const hk = prog(u, lock + .3, lock + .62), hb = hk - 1, hs = 1 + 2.70158 * hb * hb * hb + 1.70158 * hb * hb;  // back-out pop
  const head = el('lk-head'); head.style.opacity = hk > 0 ? 1 : 0; head.style.transform = `scale(${hs})`;
  el('lk-glow').style.opacity = pre ? .3 * fly + .7 * prog(u, lock - .25, lock) : .3 + .7 * (1 - prog(u, lock, lock + .7));
  el('lk-glow').style.transform = `scale(${pre ? .6 + .4 * fly : 1 + .25 * prog(u, lock, lock + .7)})`;
  const sp = prog(u, lock, lock + .9);
  $$('#lk-sparks i').forEach((d, i) => { const p = SPARKS[i], R = 60 + 260 * out(sp) * p.r;
    d.style.opacity = sp > 0 ? (1 - sp) : 0; d.style.width = d.style.height = p.s + 'px';
    d.style.transform = `translate(${Math.cos(p.a) * R}px,${Math.sin(p.a) * R * .62}px)`; });
  const tagIn = out(prog(u, .7, 1.15)), tagNear = io(prog(u, .55, lock + .1));
  el('lk-p').style.opacity = tagIn; el('lk-p').style.transform = `translateX(${-90 * (1 - tagNear)}px)`;
  el('lk-t').style.opacity = tagIn; el('lk-t').style.transform = `translateX(${90 * (1 - tagNear)}px)`;
  const r = out(prog(u, lock + .35, lock + .75));
  el('lk-res').style.opacity = r; el('lk-res').style.transform = `translateY(${(1 - r) * 22}px)`;
}

window.renderAt = T => {
  // The link card holds the app at the start of the match scene; everything after it runs LDUR later.
  const t = T < L0 ? T : T < L0 + LDUR ? L0 : T - LDUR;
  if (t < 8.4) sceneRegister(t);
  else if (t < 11.0) sceneReview(t);
  else if (t < 14.8) sceneMatch(t);
  else if (t < 18.4) sceneNoMatch(t);
  else sceneRecruit(t);
  caption(T < L0 || T >= L0 + LDUR ? t : -1); dip(t); cards(t); linkCard(T);
  return true;
};
window.DURATION = 23.8 + LDUR;
})();
