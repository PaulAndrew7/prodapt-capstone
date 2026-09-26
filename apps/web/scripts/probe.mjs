import { chromium } from "@playwright/test";
const b = await chromium.launch({ channel: "chrome" });
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
await p.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await p.waitForTimeout(2500);
for (const y of [300, 780, 1100]) {
  await p.evaluate((y) => window.scrollTo(0, y), y);
  await p.waitForTimeout(1600);
  console.log(y, await p.evaluate(() => {
    const w = document.querySelector("#hero-h").parentElement;
    const sec = document.querySelector("#hero-h").closest("section");
    return { scrollY: Math.round(scrollY), style: w.getAttribute("style"), computed: getComputedStyle(w).opacity, anims: w.getAnimations().map((a) => a.constructor.name + ":" + (a.timeline?.constructor?.name ?? "none") + ":" + a.playState) };
  }));
}
await b.close();
