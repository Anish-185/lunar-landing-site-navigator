// Screenshot every story chapter (pinned chapters at several scroll points), desktop and mobile. Playwright, Apache-2.0.
import { chromium } from "playwright";
const base = process.argv[2] || "http://localhost:4173/";
const out = process.argv[3] || "shots";
const only = process.argv[4];
const sizes = { desktop: [1440, 900], mobile: [390, 844] };
const plan = [["origin", [0.0, 0.42, 0.8]], ["pole", [0.15, 0.7]], ["sun", [0.35, 0.95]], ["earth", [0.5]], ["ridge", [0.5]],
  ["athena", [0.5]], ["slip", [0.15, 0.6]], ["console", [0.3]], ["evidence", [0.2, 0.8]]];
const browser = await chromium.launch({ executablePath: "/usr/bin/chromium", args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
for (const [label, [w, h]] of Object.entries(sizes)) {
  if (only && only !== label) continue;
  const page = await (await browser.newContext({ viewport: { width: w, height: h } })).newPage();
  page.on("pageerror", (e) => console.log("PAGEERROR", e.message));
  page.on("console", (m) => { if (m.type() === "error") console.log("CONSOLE", m.text()); });
  await page.goto(base, { waitUntil: "networkidle" });
  await page.waitForTimeout(3500);
  for (const [id, ps] of plan) {
    for (const p of ps) {
      await page.evaluate(([id, p]) => {
        const el = document.getElementById(id);
        const top = el.getBoundingClientRect().top + scrollY;
        const span = Math.max(el.offsetHeight - innerHeight, 0);
        window.scrollTo(0, top + span * p + (span === 0 ? el.offsetHeight * p - innerHeight * 0.5 : 0));  // non-pinned: the reading point mid-screen
      }, [id, p]);
      await page.waitForTimeout(id === "earth" || id === "ridge" || id === "athena" || id === "slip" ? 2600 : 1400);
      await page.screenshot({ path: `${out}/story_${id}_${Math.round(p * 100)}_${label}.png` });
    }
    console.log("shot", id, label);
  }
}
await browser.close();
