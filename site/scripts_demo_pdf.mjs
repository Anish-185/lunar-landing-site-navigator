// Print the 7-slide deck (demo_src/slides.html) to public/demo/gnomon_slides.pdf, plus a PNG per slide for checking. Playwright, Apache-2.0.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
const here = fileURLToPath(new URL(".", import.meta.url));
const pngs = process.argv[2];  // optional folder for slide PNGs
mkdirSync(`${here}public/demo`, { recursive: true });
const browser = await chromium.launch({ executablePath: "/usr/bin/chromium" });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(`file://${here}demo_src/slides.html`, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
await page.pdf({ path: `${here}public/demo/gnomon_slides.pdf`, width: "1920px", height: "1080px", printBackground: true, preferCSSPageSize: true });
if (pngs) {
  const n = await page.locator(".slide").count();
  for (let i = 0; i < n; i++) await page.locator(".slide").nth(i).screenshot({ path: `${pngs}/slide_${i + 1}.png` });
}
await browser.close();
console.log("wrote public/demo/gnomon_slides.pdf");
