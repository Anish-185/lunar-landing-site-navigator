// Verify the LIVE deployment: demo page plays the video with English subtitles showing, the PDF opens,
// and the story site's Mission Console iframe loads the Streamlit app (embed=true) with a working "Open full screen". Playwright, Apache-2.0.
import { chromium } from "playwright";
const site = process.argv[2] || "https://anish-185.github.io/lunar-landing-site-navigator/";
const appUrl = process.argv[3] || "https://gnomon-moon.streamlit.app";
const shots = process.argv[4];
const ok = (c, m) => { console.log(`${c ? "PASS" : "FAIL"}  ${m}`); if (!c) process.exitCode = 1; };
const browser = await chromium.launch({ executablePath: "/usr/bin/chromium", args: ["--autoplay-policy=no-user-gesture-required"] });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

// 1. Demo page
const r = await page.goto(`${site}demo/?v=${Date.now()}`, { waitUntil: "load" });
ok(r.status() === 200, `demo page HTTP ${r.status()}`);
const v = await page.evaluate(async () => {
  const el = document.getElementById("demo");
  el.muted = true;
  el.play().catch(() => {});                    // don't await: the promise can stall under automation
  await new Promise((res) => setTimeout(res, 4000));
  const tr = [...el.textTracks].find((t) => t.language === "en");
  return { t: el.currentTime, dur: el.duration, w: el.videoWidth, h: el.videoHeight, err: el.error?.code ?? null,
    track: tr?.mode, cues: tr?.cues?.length ?? 0, active: tr?.activeCues?.[0]?.text ?? "" };
});
ok(v.err === null && v.t > 2, `video plays (t=${v.t.toFixed(2)} s of ${v.dur.toFixed(2)} s, ${v.w}x${v.h})`);
ok(v.dur > 0 && v.dur < 30, `video under 30 s (${v.dur.toFixed(2)} s)`);
ok(v.track === "showing" && v.cues === 6, `English subtitles showing by default (${v.cues} cues; now: "${v.active.replace(/\n/g, " / ")}")`);
if (shots) await page.screenshot({ path: `${shots}/live_demo.png` });
const pdfHref = await page.locator("a[href$='gnomon_slides.pdf']").first().getAttribute("href");
const pdf = await ctx.request.get(new URL(pdfHref, page.url()).href);
const body = await pdf.body();
ok(pdf.status() === 200 && pdf.headers()["content-type"]?.includes("pdf") && body.subarray(0, 5).toString() === "%PDF-",
  `PDF opens (HTTP ${pdf.status()}, ${pdf.headers()["content-type"]}, ${(body.length / 1e6).toFixed(1)} MB)`);
const pages = (body.toString("latin1").match(/\/Type\s*\/Page[^s]/g) || []).length;
ok(pages === 7, `PDF has ${pages} pages`);

// 2. Story site: Mission Console
const s = await ctx.newPage();
await s.goto(`${site}?v=${Date.now()}`, { waitUntil: "networkidle" });
await s.waitForTimeout(2500);
await s.evaluate(() => document.getElementById("console").scrollIntoView());
await s.waitForTimeout(3000);
const src = await s.locator("#console-frame iframe").getAttribute("src").catch(() => null);
ok(!!src && src.startsWith(appUrl) && src.includes("embed=true"), `console iframe src: ${src}`);
// the Streamlit app renders inside the (Cloud) iframe chain
let rendered = false;
for (let i = 0; i < 40 && !rendered; i++) {
  for (const f of s.frames()) {
    if (await f.locator("[data-testid=stApp], [data-testid=stMain]").count().catch(() => 0)) { rendered = true; break; }
  }
  if (!rendered) await s.waitForTimeout(3000);
}
ok(rendered, "console iframe renders the Streamlit app");
if (shots) { await s.waitForTimeout(6000); await s.screenshot({ path: `${shots}/live_console.png` }); }
const href = await s.locator("#console-open").getAttribute("href");
ok(href === appUrl, `"Open full screen" href: ${href}`);
const [popup] = await Promise.all([s.waitForEvent("popup"), s.locator("#console-open").click()]);
await popup.waitForURL((u) => u.href.startsWith(appUrl), { timeout: 60000 }).catch(() => {});
ok(popup.url().startsWith(appUrl), `"Open full screen" opens ${popup.url().slice(0, 60)}`);
await browser.close();
