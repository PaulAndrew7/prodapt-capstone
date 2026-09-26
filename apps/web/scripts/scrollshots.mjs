// node scripts/scrollshots.mjs <outDir> <route> y1 y2 ... (y as pixels)
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
const [out, route, ...ys] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const b = await chromium.launch({ channel: "chrome" });
const p = await b.newPage({ viewport: { width: +(process.env.W ?? 1440), height: +(process.env.H ?? 900) } });
const errs = [];
p.on("pageerror", (e) => errs.push(e.message));
await p.goto(`http://localhost:5173${route}`, { waitUntil: "networkidle" });
await p.waitForTimeout(2500);
for (const y of ys) {
  await p.evaluate((y) => window.scrollTo(0, y), +y);
  await p.waitForTimeout(+(process.env.SETTLE ?? 1600));
  await p.screenshot({ path: `${out}/y${y}.png` });
  console.log("shot", y);
}
console.log(errs.length ? errs.join("\n") : "no page errors");
await b.close();
