// Screenshot helper: node scripts/shot.mjs <url> <outfile> [width] [height] [--full] [--dark] [--reduced]
import { chromium } from "@playwright/test";

const [url, out, w = "1440", h = "900", ...flags] = process.argv.slice(2);
const browser = await chromium.launch({ channel: "chrome" });
const context = await browser.newContext({
  viewport: { width: Number(w), height: Number(h) },
  deviceScaleFactor: 1,
  colorScheme: flags.includes("--dark") ? "dark" : "light",
  reducedMotion: flags.includes("--reduced") ? "reduce" : "no-preference",
});
const page = await context.newPage();
page.on("pageerror", (e) => console.error("pageerror:", e.message));
page.on("console", (m) => m.type() === "error" && console.error("console:", m.text()));
await page.goto(url, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(Number(process.env.SHOT_WAIT ?? 900));
await page.screenshot({ path: out, fullPage: flags.includes("--full") });
await browser.close();
console.log("saved", out);
