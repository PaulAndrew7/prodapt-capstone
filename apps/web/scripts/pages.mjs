// Batch screenshots: node scripts/pages.mjs <outDir> <width> <height> [--dark] route1=name1 route2=name2 ...
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";

const [out, w, h, ...rest] = process.argv.slice(2);
const dark = rest.includes("--dark");
const full = rest.includes("--full");
const pairs = rest.filter((r) => r.includes("=")).map((r) => r.split("="));
mkdirSync(out, { recursive: true });
const base = process.env.BASE ?? "http://localhost:5173";
const browser = await chromium.launch({ channel: "chrome" });
const ctx = await browser.newContext({ viewport: { width: +w, height: +h }, colorScheme: dark ? "dark" : "light" });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => m.type() === "error" && !m.text().includes("Outdated Optimize Dep") && errors.push(m.text()));
for (const [route, name] of pairs) {
  await page.goto(`${base}${route}`, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(Number(process.env.SHOT_WAIT ?? 1200));
  const scrollW = await page.evaluate(() => document.documentElement.scrollWidth);
  if (scrollW > +w) errors.push(`${route}: horizontal overflow ${scrollW}px > ${w}px`);
  await page.screenshot({ path: `${out}/${name}.png`, fullPage: full });
  console.log("shot", name);
}
console.log(errors.length ? `ISSUES:\n${errors.join("\n")}` : "no console errors, no overflow");
await browser.close();
