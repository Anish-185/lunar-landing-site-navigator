// Capture frame sequences of the LIVE story site and mission console for the 30 s demo video (Playwright, Apache-2.0).
// Usage: node scripts_demo_capture.mjs <site|app> <outdir> [siteUrl] [appUrl]
// Frames are 1920x1080 stills; scripts_demo_video.sh blends them with ffmpeg (smoother than recording software WebGL live).
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
const [what, out, siteUrl = "https://anish-185.github.io/lunar-landing-site-navigator/", appUrl = "https://gnomon-moon.streamlit.app"] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: "/usr/bin/chromium", args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await (await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 })).newPage();
page.on("pageerror", (e) => console.log("PAGEERROR", e.message));
const shot = async (dir, i) => page.screenshot({ path: `${out}/${dir}/${String(i).padStart(4, "0")}.png` });
const at = (id, p) => page.evaluate(([id, p]) => {
  const el = document.getElementById(id);
  const top = el.getBoundingClientRect().top + scrollY, span = Math.max(el.offsetHeight - innerHeight, 0);
  window.scrollTo(0, top + span * p + (span === 0 ? el.offsetHeight * p - innerHeight * 0.5 : 0));
}, [id, p]);

if (what === "site") {
  for (const d of ["pole", "sun", "athena", "hero"]) mkdirSync(`${out}/${d}`, { recursive: true });
  await page.goto(siteUrl, { waitUntil: "networkidle" });
  await page.waitForTimeout(4000);
  await page.screenshot({ path: `${out}/hero/0000.png` });
  // Be the Sun: zoomed pole, the cursor (the Sun) sweeps a full circle around the cap
  await at("pole", 0.7); await page.waitForTimeout(3500);
  const box = await page.locator("#terrain").boundingBox();
  const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
  const n = 48;
  for (let i = 0; i < n; i++) {
    const a = ((135 + (i / n) * 300) * Math.PI) / 180;      // compass azimuth: 0 = up (north on screen), clockwise
    await page.mouse.move(cx + Math.sin(a) * 300, cy - Math.cos(a) * 300);
    await page.waitForTimeout(140);
    await shot("pole", i);
  }
  // The Sun circles: scrub the pinned chapter
  await at("sun", 0.02); await page.waitForTimeout(2500);
  for (let i = 0; i < 48; i++) { await at("sun", 0.05 + (i / 47) * 0.9); await page.waitForTimeout(160); await shot("sun", i); }
  // Athena: settle on the chapter, then a slow scroll through its reading point
  await at("athena", 0.4); await page.waitForTimeout(3000);
  for (let i = 0; i < 20; i++) { await at("athena", 0.4 + (i / 19) * 0.2); await page.waitForTimeout(160); await shot("athena", i); }
} else {
  for (const d of ["verdicts", "replan"]) mkdirSync(`${out}/${d}`, { recursive: true });
  const ready = async () => {
    await page.waitForTimeout(3000);
    await page.waitForFunction(() => !document.querySelector('[data-testid="stStatusWidget"]'), null, { timeout: 120000 }).catch(() => {});
    await page.waitForTimeout(1500);
  };
  await page.goto(appUrl, { waitUntil: "domcontentloaded", timeout: 120000 });
  // Streamlit Cloud sleep screen: wake the app
  const wake = page.getByRole("button", { name: /get this app back up/i });
  if (await wake.isVisible({ timeout: 8000 }).catch(() => false)) { console.log("waking app"); await wake.click(); await page.waitForTimeout(45000); }
  const app = page.frameLocator("iframe[title='streamlitApp']").first();
  const hasFrame = await page.locator("iframe[title='streamlitApp']").count();
  console.log("cloud iframe:", hasFrame);
  // Go straight to the Streamlit server (Cloud serves it under /~/+/ inside its own iframe)
  // Go straight to the app origin's content to avoid the Cloud chrome around it
  await page.goto(`${appUrl}/~/+/?embed=true&embed_options=dark_theme`, { waitUntil: "networkidle", timeout: 180000 });
  await ready();
  await page.waitForSelector("[data-testid=stMain]", { timeout: 120000 }); await page.waitForTimeout(6000);
  await ready();
  await shot("verdicts", 0);
  await page.mouse.wheel(0, 500); await page.waitForTimeout(2500); await shot("verdicts", 1);
  await page.goto(`${appUrl}/~/+/replan?embed=true&embed_options=dark_theme`, { waitUntil: "networkidle", timeout: 180000 });
  await ready();
  await page.waitForSelector("[data-testid=stSlider]", { timeout: 120000 }); await page.waitForTimeout(4000);
  await ready();
  const thumb = page.locator("[data-testid=stSlider]", { hasText: "Launch slip" }).getByRole("slider").first();  // the launch-slip slider, not the sidebar ones
  await thumb.focus();
  await page.keyboard.press("Home"); await ready(); await shot("replan", 0);
  for (const [i, steps] of [[1, 14], [2, 14], [3, 14]]) {
    for (let k = 0; k < steps; k++) await page.keyboard.press("ArrowRight");
    await ready(); await shot("replan", i);
  }
  void app;
}
await browser.close();
console.log("done", what);
