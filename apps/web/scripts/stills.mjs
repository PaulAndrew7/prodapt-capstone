// Captures isolated still frames of the real 3D renders (transparent background) for fallbacks.
import { chromium } from "@playwright/test";
const b = await chromium.launch({ channel: "chrome" });
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 });
const p = await ctx.newPage();
await p.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await p.waitForFunction(() => !document.querySelector("[role=status]"), null, { timeout: 20000 });
await p.waitForTimeout(1500);
const isolate = `html,body,main,section,div,header,figure{background:transparent!important;border-color:transparent!important}
  h1,h2,h3,p,a,button,header,nav,figcaption,img{visibility:hidden!important}`;
const tag = await p.addStyleTag({ content: isolate });
await p.waitForTimeout(300);
await p.locator("section canvas").first().screenshot({ path: "public/front/policy-stack.png", omitBackground: true });
console.log("policy stack still");
await b.close();
