// Screenshot every Streamlit page at desktop and mobile widths (Playwright, Apache-2.0).
import { chromium } from "playwright";
const base = process.argv[2] || "http://localhost:8599";
const out = process.argv[3] || "shots";
const pages = (process.argv[4] || "site,compare,replan,map,athena,evidence").split(",");
const only = process.argv[5];
const widths = { desktop: [1440, 900], mobile: [390, 844] };
const browser = await chromium.launch({ executablePath: "/usr/bin/chromium" });
for (const [label, [w, h]] of Object.entries(widths)) {
  if (only && only !== label) continue;
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  for (const p of pages) {
    const url = p === "site" ? `${base}/` : `${base}/${p}`;
    await page.goto(url, { waitUntil: "networkidle", timeout: 120000 });
    await page.waitForTimeout(4000);
    await page.waitForFunction(() => !document.querySelector('[data-testid="stStatusWidget"]'), null, { timeout: 120000 }).catch(() => {});
    await page.waitForTimeout(2500);
    const full = await page.evaluate(() => {
      const m = document.querySelector('[data-testid="stMain"]') || document.querySelector('[data-testid="stAppViewContainer"]');
      return m ? m.scrollHeight : document.body.scrollHeight;
    });
    await page.setViewportSize({ width: w, height: Math.min(full + 40, 9000) });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: `${out}/app_${p}_${label}.png`, fullPage: true });
    await page.setViewportSize({ width: w, height: h });
    console.log("shot", p, label);
  }
  await ctx.close();
}
await browser.close();
