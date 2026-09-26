import { chromium } from "@playwright/test";
const b = await chromium.launch({ channel: "chrome", args: ["--enable-gpu", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
p.on("console", (m) => m.type() !== "debug" && console.log("console:", m.type(), m.text().slice(0, 160)));
await p.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await p.waitForTimeout(3500);
const info = await p.evaluate(() => {
  const c = document.querySelector("section canvas");
  const r = c?.getBoundingClientRect();
  return { rect: r && { x: r.x, y: r.y, w: r.width, h: r.height }, attrW: c?.width, attrH: c?.height, parentOpacity: c && getComputedStyle(c.closest("div[style]") ?? c).opacity };
});
console.log(info);
const c = await p.$("section canvas");
if (c) await c.screenshot({ path: "../../.impeccable/review/front/canvas.png" });
await p.mouse.wheel(0, 500);
await p.waitForTimeout(1500);
await p.screenshot({ path: "../../.impeccable/review/front/hero-scrolled.png" });
await b.close();
