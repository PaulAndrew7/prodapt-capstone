// Captures isolated still frames of the real 3D renders (transparent background) for fallbacks.
import { chromium } from "@playwright/test";
const b = await chromium.launch({ channel: "chrome" });
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 });
const p = await ctx.newPage();
await p.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await p.waitForTimeout(3500);
const isolate = `html,body,main,section,div,header,figure{background:transparent!important;border-color:transparent!important}
  h1,h2,h3,p,a,button,header,nav,figcaption,img{visibility:hidden!important}`;
const tag = await p.addStyleTag({ content: isolate });
await p.waitForTimeout(300);
await p.locator("section canvas").first().screenshot({ path: "public/front/policy-stack.png", omitBackground: true });
console.log("policy stack still");
await tag.evaluate((n) => n.remove());
const top = await p.evaluate(() => document.getElementById("review-h").closest("section").getBoundingClientRect().top + scrollY);
await p.evaluate((y) => window.scrollTo(0, y + 900), top);
await p.waitForTimeout(700);
await p.addStyleTag({ content: isolate });
await p.waitForTimeout(300);
await p.locator("#review canvas").screenshot({ path: "public/avatar/still.png", omitBackground: true });
console.log("avatar still");
await b.close();
