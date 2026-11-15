// Gnomon story site. Real data from site/public/data/story.json (written by pipeline/export_site.py).
// Libraries do the heavy lifting: Lenis (smooth scroll), Motion (scroll-linked progress), three.js (cosmos, lazy),
// Plotly.js (charts, lazy), Lucide (status icons). This file is glue.
import "@fontsource-variable/fraunces/full.css";
import "@fontsource-variable/hanken-grotesk";
import "./style.css";
import Lenis from "lenis";
import { scroll } from "motion";
import { createElement, CircleCheck, TriangleAlert, OctagonX } from "lucide";

const BASE = import.meta.env.BASE_URL;
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (s, el = document) => el.querySelector(s);
const fmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
const fmtT = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "UTC" });
const pct = (v) => `${Math.round(v)}%`;

const [data, config] = await Promise.all([
  fetch(`${BASE}data/story.json`).then((r) => r.json()),
  fetch(`${BASE}config.json`).then((r) => (r.ok ? r.json() : {})).catch(() => ({})),
]);

// --- smooth scroll ---
if (!reduced) {
  const lenis = new Lenis({ autoRaf: true, lerp: 0.09 });
  document.querySelectorAll('a[href^="#"]').forEach((a) =>
    a.addEventListener("click", (e) => { e.preventDefault(); lenis.scrollTo(a.getAttribute("href"), { offset: 0 }); }));
}

// --- chapter rail ---
const chapters = [...document.querySelectorAll(".chapter")];
const rail = $("#rail");
chapters.forEach((c) => {
  const a = document.createElement("a");
  a.href = `#${c.id}`;
  a.setAttribute("aria-label", c.dataset.title);
  a.title = c.dataset.title;
  rail.append(a);
});
const io = new IntersectionObserver((es) => es.forEach((e) => {
  if (e.isIntersecting) [...rail.children].forEach((a) => a.setAttribute("aria-current", String(a.hash === `#${e.target.id}`)));
}), { rootMargin: "-45% 0px -45% 0px" });
chapters.forEach((c) => io.observe(c));

// --- beats: copy that appears for a slice of a pinned chapter's scroll ---
function beats(section, p) {
  section.querySelectorAll(".beat").forEach((b) => {
    b.classList.toggle("on", reduced || (p >= +b.dataset.at && p <= +b.dataset.until));
  });
}

// --- 1-2: the cosmos (three.js, loaded after first paint) ---
// The download happens at idle; the Big Bang itself waits for the reader's first move ("Scroll to start the
// universe"), so the first paint never waits for WebGL.
let cosmos = null;
const cosmosModule = new Promise((res) => (window.requestIdleCallback || setTimeout)(() => res(import("./cosmos.js")), { timeout: 1500 }));
let started = false;
const startCosmos = () => {
  if (started) return;
  started = true;
  ["wheel", "touchstart", "keydown", "pointerdown", "scroll"].forEach((ev) => removeEventListener(ev, startCosmos));
  cosmosModule.then(({ createCosmos }) => {
    cosmos = createCosmos($("#cosmos"), { reduced, base: BASE });
    $(".singularity")?.classList.add("gone");
    toCosmos();
  });
};
["wheel", "touchstart", "keydown", "pointerdown", "scroll"].forEach((ev) => addEventListener(ev, startCosmos, { passive: true }));
if (scrollY > 0) startCosmos();

const origin = $("#origin"), pole = $("#pole");
// Two chapters drive one scene: keep both progresses and hand the cosmos their sum, so neither callback overrides
// the other when the reader jumps (anchor links, reloads mid-page).
const prog = { origin: 0, pole: 0 };
const toCosmos = () => cosmos?.setProgress(prog.origin + prog.pole);
scroll((p) => { prog.origin = p; beats(origin, p); toCosmos(); }, { target: origin, offset: ["start start", "end end"] });
beats(origin, 0);

// --- 2: parallax layers into the south pole ---
(function poleChapter() {
  const { extent_km: [x0, y0, x1, y1], sites } = data.pole;
  const box = $("#pole-markers");
  for (const s of sites) {
    const m = document.createElement("i");
    m.className = "marker";
    m.style.left = `${((s.x_km - x0) / (x1 - x0)) * 100}%`;
    m.style.top = `${((y1 - s.y_km) / (y1 - y0)) * 100}%`;
    m.innerHTML = `<span>${s.name}</span>`;
    box.append(m);
  }
  const nebula = $(".layer-nebula", pole), starsL = $(".layer-stars", pole), terrain = $("#terrain");
  const ease = (a, b, x) => Math.min(1, Math.max(0, (x - a) / (b - a)));
  scroll((p) => {
    prog.pole = p;
    toCosmos();
    beats(pole, p);
    if (reduced) return;
    const z = 0.7 + p * 2.3;                                   // fly in toward the pole
    terrain.style.transform = `scale(${z})`;
    terrain.style.setProperty("--z", z);
    terrain.style.opacity = String(ease(0.22, 0.5, p));        // the 3D Moon's pole hands over to LOLA relief
    nebula.style.transform = `translateY(${-p * 8}%) scale(${1 + p * 0.15})`;
    nebula.style.opacity = String(0.45 * ease(0.25, 0.6, p));
    starsL.style.transform = `translateY(${-p * 18}%)`;
    pole.classList.toggle("zoomed", p > 0.5);
  }, { target: pole, offset: ["start start", "end end"] });
  if (reduced) { terrain.style.opacity = "1"; pole.classList.add("zoomed"); beats(pole, 1); }
})();

// --- 3: the Sun circles the horizon ---
(function sunChapter() {
  const d = data.sun;
  const W = 1440, H = 420, LO = -3, HI = 11;
  const X = (az) => (az / 360) * W, Y = (el) => H - ((el - LO) / (HI - LO)) * H;
  const svg = $("#sun-svg");
  const ns = "http://www.w3.org/2000/svg";
  const el = (tag, attrs, parent = svg) => { const n = document.createElementNS(ns, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); parent.append(n); return n; };
  const defs = el("defs", {});
  defs.innerHTML = `<linearGradient id="rock" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8E909C"/><stop offset="1" stop-color="#2A2C3A"/></linearGradient>
    <linearGradient id="fadeTop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".16" stop-color="#fff" stop-opacity="1"/></linearGradient>
    <mask id="skyFade" maskUnits="userSpaceOnUse" x="0" y="0" width="1440" height="420"><rect width="1440" height="420" fill="url(#fadeTop)"/></mask>
    <radialGradient id="glow"><stop offset="0" stop-color="#FFE7B0"/><stop offset=".35" stop-color="#F6B94A" stop-opacity=".55"/><stop offset="1" stop-color="#F6B94A" stop-opacity="0"/></radialGradient>`;
  el("line", { x1: 0, x2: W, y1: Y(0), y2: Y(0), stroke: "rgba(236,233,247,.18)", "stroke-dasharray": "3 6" });
  const sky = d.az.map((a, i) => `${X(a).toFixed(1)},${Y(d.horizon[i]).toFixed(1)}`).join(" ");
  el("polygon", { points: `0,${H} ${sky} ${W},${Y(d.horizon[0]).toFixed(1)} ${W},${H}`, fill: "url(#rock)", opacity: 0.92, mask: "url(#skyFade)" });
  // ridge labels: one per named segment wide enough to read
  const widest = {};
  for (const s of d.segments) if (s.km >= 2 && (!widest[s.name] || s.az1 - s.az0 > widest[s.name].az1 - widest[s.name].az0)) widest[s.name] = s;
  let lastX = -1e9;
  for (const s of Object.values(widest).filter((s) => s.az1 - s.az0 >= 8).sort((a, b) => a.az0 - b.az0)) {
    const mid = (s.az0 + s.az1) / 2;
    const i0 = Math.round(s.az0 * 2), i1 = Math.round(s.az1 * 2);
    const top = Math.max(...d.horizon.slice(i0, i1 + 1));
    if (X(mid) - lastX < 170) continue;                       // keep labels from colliding
    lastX = X(mid);
    const y = Math.max(Y(top) - 18, 40);
    el("line", { x1: X(mid), x2: X(mid), y1: y + 4, y2: Math.max(Y(top), y + 4), stroke: "rgba(236,233,247,.4)" });
    const t = el("text", { x: X(mid), y: y - 4, "text-anchor": "middle", fill: "#ECE9F7", "font-size": 16, "font-family": "Hanken Grotesk Variable, sans-serif" });
    t.textContent = `${s.name}, ${Math.round(s.km)} km`;
  }
  for (const [a, lab] of [[0, "N"], [90, "E"], [180, "S"], [270, "W"], [360, "N"]]) {
    const t = el("text", { x: Math.min(Math.max(X(a), 10), W - 10), y: H - 8, "text-anchor": "middle", fill: "#A9A6C2", "font-size": 13 });
    t.textContent = lab;
  }
  // Sun path: one path, broken where the azimuth wraps past north
  let dpath = "";
  d.sun_az.forEach((a, i) => {
    const wrap = i > 0 && Math.abs(a - d.sun_az[i - 1]) > 180;
    dpath += `${i === 0 || wrap ? "M" : "L"}${X(a).toFixed(1)},${Y(d.sun_el[i]).toFixed(1)}`;
  });
  const path = el("path", { d: dpath, fill: "none", stroke: "#F6B94A", "stroke-width": 2, "stroke-linecap": "round", opacity: 0.95 });
  const len = path.getTotalLength();
  path.style.strokeDasharray = `${len}`;
  const halo = el("circle", { r: 26, fill: "url(#glow)" });
  const disc = el("circle", { r: Math.max(4, (d.sun_r / (HI - LO)) * H), fill: "#FFE7B0" });
  const read = $("#sun-readout");
  $("#sun-cap").textContent = `Every compass direction across, elevation up (stretched about ${Math.round((H / (HI - LO)) / (W / 360))}× so a 2° Sun is visible; peaks above ${HI}° are cut off). Grey is the real skyline from 20 m and 80 m LOLA terrain; labels name the ridge in that direction and its distance. Gold is the Sun's real path through January 2027 (SPICE, DE440).`;
  const blocks = d.blocks.map((b) => ({ ...b, t0: Date.parse(b.start), t1: Date.parse(b.start) + b.hours * 3.6e6 }));
  const malapert = blocks.find((b) => /Malapert/.test(b.why));
  $("#sun-lede").innerHTML = `${d.site}, January 2027. The Sun goes once around the whole sky in a month and never climbs more than
    ${Math.max(...d.sun_el).toFixed(1)}° above the horizon. It clears the ridges ${pct(d.pct_sunlit)} of the month.
    ${malapert ? `On ${fmt.format(new Date(malapert.t0))}, a mountain <em class="sun">${malapert.why.match(/by (.*?),/)[1]}</em>,
    ${malapert.why.match(/, (\d+ km) away/)[1]} away, steals ${malapert.hours} hours of it.` : ""}`;
  const n = d.sun_az.length;
  const draw = (p) => {
    const i = Math.min(n - 1, Math.max(0, Math.floor(p * (n - 1))));
    path.style.strokeDashoffset = `${len * (1 - (i + 1) / n)}`;
    const x = X(d.sun_az[i]), y = Y(d.sun_el[i]);
    const pan = $("#pan-scroll");
    if (pan.scrollWidth > pan.clientWidth) pan.scrollLeft = (x / W) * pan.scrollWidth - pan.clientWidth / 2;  // follow the Sun
    disc.setAttribute("cx", x); disc.setAttribute("cy", y); halo.setAttribute("cx", x); halo.setAttribute("cy", y);
    const lit = d.sunlit[i] === 1;
    disc.setAttribute("fill", lit ? "#FFE7B0" : "#5b5d6b");
    halo.setAttribute("opacity", lit ? 1 : 0.08);
    const t = Date.parse(d.t[i]);
    const b = blocks.find((b) => t >= b.t0 && t < b.t1);
    read.innerHTML = `<b>${fmtT.format(new Date(t))} UTC</b> &nbsp;Sun ${d.sun_el[i] >= 0 ? "+" : ""}${d.sun_el[i].toFixed(2)}° at ${Math.round(d.sun_az[i])}°`
      + (lit ? "" : `<span class="why">${b ? b.why.replace(" at az", ", az") : "Sun below the horizon"}</span>`);
  };
  draw(reduced ? 1 : 0);
  if (!reduced) scroll((p) => draw(Math.min(1, p * 1.12)), { target: $("#sun"), offset: ["start start", "end end"] });
})();

// --- 4-7: charts (Plotly, loaded when the reader gets close) ---
const charts = import.meta.glob("./charts.js");
let plotting = null;
const loadCharts = () => (plotting ??= charts["./charts.js"]());
const near = new IntersectionObserver((es) => es.forEach((e) => {
  if (!e.isIntersecting) return;
  near.unobserve(e.target);
  loadCharts().then((m) => m.draw(e.target.id, data));
}), { rootMargin: "60% 0px" });
["earth-chart", "ridge-chart", "athena-chart", "slip-chart"].forEach((id) => near.observe($(`#${id}`)));

const e = data.earth;
$("#earth-lede").innerHTML = `Libration nods Earth up and down every month: from ${e.range[0].toFixed(1)}° to +${e.range[1].toFixed(1)}° here.
  Behind the ridges it drops out of sight, and over January it is in view only <em class="earth">${pct(e.pct_visible)}</em> of the time.`;

const r = data.ridge;
$("#ridge-duo").innerHTML = `<div class="lo"><b>${r.nasa_min}%</b><span>NASA's darkest cell</span></div><i>to</i>
  <div class="hi"><b>${r.nasa_max}%</b><span>NASA's brightest cell</span></div>`;
$("#ridge-lede").innerHTML = `Blue Moon MK1 is headed for the ridge that joins Shackleton to its neighbours. Within ${r.radius_m} m of
  the target, NASA's 18.6-year sunlight map runs from pits that never see the Sun to a crest lit ${r.nasa_max}% of the time. Our own number
  at the target, from 20 m terrain, is ${r.ours}%, inside NASA's range. A few hundred metres is the difference between a mission
  and a monument.`;

const a = data.athena;
$("#athena-beats").innerHTML = [
  [`Off by ${a.reported_miss_m} m.`, `Intuitive Machines' Athena came down about ${a.reported_miss_m} m from its target on 6 March 2025 (AP); LROC's published positions differ by ${a.lroc_miss_m} m.`],
  [`The Sun was ${a.sun_el}° up.`, `At that angle a 1 m boulder throws a ${a.boulder_m} m shadow. The company later blamed long shadows and dim polar light for confusing its navigation.`],
  [`The map said all clear.`, `On 20 m orbital terrain, ${a.shadow_pct}% of the landing zone was shadowed and ${a.p_success_target}% of our simulated landings around the target pass slope, power, link and light.`],
  [`The crater was one pixel.`, `LROC found Athena on its side in a ${a.crater_m} m crater. With the Sun at ${a.sun_el}°, its rim shades ${a.crater_shadow_m[0]}–${a.crater_shadow_m[1]} m of ground: the floor was dark. No public map resolves it; NASA's 5 m terrain stops 30 km short. That is why landing zones carry margins, and why we score the whole ellipse.`],
].map(([h, p]) => `<li><b>${h}</b><p>${p}</p></li>`).join("");
$("#athena-cap").textContent = `20 m LOLA relief, lit from the Sun's direction at touchdown (az ${a.sun_az}°). Red diamond: where Athena rests. Blue diamond: its target. Grey dots: 200 simulated landings. Red ring: a ${a.crater_m} m crater, to scale.`;

// --- 7: the slip teaser ---
(function slipChapter() {
  const s = data.slip;
  const dates = s.dates.map((d) => Date.parse(d));
  const planned = Date.parse(s.planned);
  const iOf = (t) => dates.reduce((best, d, i) => (Math.abs(d - t) < Math.abs(dates[best] - t) ? i : best), 0);
  const row = s.names.indexOf(s.site);
  const icon = (k) => createElement({ go: CircleCheck, caution: TriangleAlert, nogo: OctagonX }[k]).outerHTML;
  const status = (v, ok) => (!ok || v < 25 ? ["nogo", "No-go"] : v >= 60 ? ["go", "Go"] : ["caution", "Caution"]);
  const card = (title, accent, name, i, j) => {
    const v = s.pct_both[j][i], ok = s.survives[j][i] === 1;
    const [k, word] = status(v, ok);
    return `<article class="scard" style="--accent:${accent}"><h3>${title}</h3><span class="status ${k}">${icon(k)}${word}</span>
      <div class="num">${Math.round(v)}<small>% Sun and link</small></div>
      <p>${v < 5 && title.startsWith("Plan B: switch") ? "Every candidate is dark that day. Best: " : ""}${name}, land ${fmt.format(new Date(dates[i]))}. Battery ${ok ? "survives" : "runs flat"}.</p></article>`;
  };
  const out = $("#slip-out"), range = $("#slip-range");
  const update = () => {
    const slip = +range.value;
    out.textContent = `${slip} days`;
    const i0 = iOf(planned), i = iOf(planned + slip * 864e5);
    let best = -1, bestV = -1e9;
    s.names.forEach((nm, j) => { const v = s.pct_both[j][i] - (s.survives[j][i] ? 0 : 1000); if (j !== row && v > bestV) { bestV = v; best = j; } });
    let later = i, laterV = -1e9;
    for (let k = i; k < dates.length; k++) { const v = s.pct_both[row][k] - (s.survives[row][k] ? 0 : 1000); if (v > laterV) { laterV = v; later = k; } }
    $("#slip-cards").innerHTML = card("Planned", "#A7A9B4", s.site, i0, row)
      + card(`After a ${slip}-day slip`, "#FF5A5F", s.site, i, row)
      + card("Plan B: switch site, same day", "#59A8FF", s.names[best], i, best)
      + (later !== i ? card("Plan B: same site, wait", "#F6B94A", s.site, later, row) : "");
    document.dispatchEvent(new CustomEvent("slip", { detail: dates[i] }));
  };
  range.addEventListener("input", update);
  update();
  $("#slip-lede").innerHTML = `${s.site}, a week on the surface from ${fmt.format(new Date(planned))} 2027: Sun and Earth the whole
    time. Then the rocket slips ${s.slip_days} days and you land at nightfall. Drag the slip: every candidate site and every landing
    day is re-ranked from the same physics (${s.lander}, illustrative power numbers).`;
})();

// --- 8: mission console ---
(function consoleChapter() {
  const url = (config.appUrl || "").trim().replace(/\/$/, "");
  const frame = $("#console-frame"), open = $("#console-open");
  if (url) {
    open.href = url;
    const load = new IntersectionObserver((es) => {
      if (!es[0].isIntersecting) return;
      load.disconnect();
      frame.innerHTML = `<iframe src="${url}/?embed=true&embed_options=dark_theme" title="Gnomon mission console" loading="lazy" allow="clipboard-write"></iframe>`;
    }, { rootMargin: "50% 0px" });
    load.observe(frame);
  } else {
    open.setAttribute("aria-disabled", "true");
    open.textContent = "Console launching soon";
    frame.innerHTML = `<div class="console-empty"><p class="body">The live console is not linked yet. Run it on your machine with
      <b>make app</b> (source on <a href="https://github.com/Anish-185/lunar-landing-site-navigator">GitHub</a>).</p></div>`;
  }
})();

// --- 9: evidence ---
(function evidenceChapter() {
  const v = data.evidence;
  const cy3 = v.hindcast.find((h) => /Chandrayaan/.test(h.name));
  $("#proofs").innerHTML = `
    <div class="proof"><b>${v.horizons_max_arcsec.toFixed(3)}″</b><span>Largest gap between our Sun and Earth positions and NASA JPL's Horizons, over ${v.horizons_n} checks.</span></div>
    <div class="proof"><b>${v.sun_in_range} of ${v.n_sites}</b><span>Sites where our long-run sunlight falls inside NASA's own map range within 420 m (PGDA product 69).</span></div>
    <div class="proof"><b>${fmt.format(new Date(cy3.our_sunset))} 2023</b><span>Our predicted sunset at Chandrayaan-3's landing site. ISRO shut Vikram down "at sunset over the landing site, twelve days after landing".</span></div>`;
  const rows = v.hindcast.map((h) => `<tr><td>${h.name}</td><td>${fmtT.format(new Date(h.landed))}</td><td>${h.our_sunset ? fmtT.format(new Date(h.our_sunset)) : "none"}</td>
    <td>${h.reported}</td><td>${h.ended_by}</td><td><a href="${h.source}">source</a></td></tr>`).join("");
  $("#hindcast").innerHTML = `<h3 class="h3">The landers that went before</h3><table class="ev"><thead><tr><th>Mission</th><th>Landed (UTC)</th>
    <th>Our first sunset (UTC)</th><th>Reported end</th><th>Ended by</th><th></th></tr></thead><tbody>${rows}</tbody></table>`;
})();
