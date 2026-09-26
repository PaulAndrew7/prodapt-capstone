import { chromium } from "@playwright/test";
const b = await chromium.launch({ channel: "chrome" });
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
await p.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await p.waitForTimeout(1500);
const top = await p.evaluate(() => document.getElementById("features-h").closest("section").getBoundingClientRect().top + scrollY);
await p.evaluate((y) => window.scrollTo(0, y - 72), top);
await p.waitForTimeout(1500);
for (const name of ["Assess a scenario", "Open the evidence", "Try a hypothetical"]) {
  await p.getByRole("tab", { name }).click();
  await p.waitForTimeout(name === "Assess a scenario" ? 7000 : 2200);
  await p.screenshot({ path: `../../.impeccable/review/front/tab-${name.split(" ")[0].toLowerCase()}.png` });
  console.log("shot", name);
}
const r = await p.evaluate(() => document.getElementById("review-h").closest("section").getBoundingClientRect().top + scrollY);
await p.evaluate((y) => window.scrollTo(0, y + 700), r);
await p.waitForTimeout(6000);
await p.screenshot({ path: "../../.impeccable/review/front/bento-lower.png" });
await b.close();
