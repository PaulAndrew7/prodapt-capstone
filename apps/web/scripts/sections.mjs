// Scrolls each front-door section into place and captures it. node scripts/sections.mjs <outDir> [width] [height]
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
const [out, w = "1440", h = "900"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const b = await chromium.launch({ channel: "chrome" });
const p = await b.newPage({ viewport: { width: +w, height: +h }, reducedMotion: process.env.REDUCED ? "reduce" : "no-preference" });
const errs = [];
p.on("pageerror", (e) => errs.push(e.message));
p.on("console", (m) => m.type() === "error" && errs.push(m.text()));
await p.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await p.waitForTimeout(2000);
const targets = await p.evaluate(() => {
  const ids = ["product-h", "features-h", "how", "unknown-h", "versions-h", "review-h", "close-h"];
  return ids.map((id) => {
    const el = document.getElementById(id);
    const sec = el?.closest("section") ?? el;
    return { id, top: sec ? sec.getBoundingClientRect().top + scrollY : 0, height: sec?.getBoundingClientRect().height ?? 0 };
  });
});
for (const t of targets) {
  const stops = t.id === "how" ? [0.05, 0.45, 0.85].map((f) => t.top + 72 + f * (t.height - +h)) : [t.top - 72 + (t.id === "product-h" ? 260 : 0)];
  let i = 0;
  for (const y of stops) {
    await p.evaluate((y) => window.scrollTo(0, y), Math.round(y));
    await p.waitForTimeout(+(process.env.SETTLE ?? 2600));
    await p.screenshot({ path: `${out}/${t.id}${stops.length > 1 ? `-${i++}` : ""}.png` });
    console.log("shot", t.id);
  }
}
const overflow = await p.evaluate(() => document.documentElement.scrollWidth);
if (overflow > +w) errs.push(`horizontal overflow ${overflow}`);
console.log(errs.length ? "ISSUES:\n" + errs.join("\n") : "no errors, no overflow");
await b.close();
