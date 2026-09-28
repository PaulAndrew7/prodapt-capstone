// Exports docs/architecture/diagram/architecture.html to the submission formats:
// architecture.pdf (two A4 landscape pages) and one JPEG per page.
import { chromium } from "@playwright/test";
import { fileURLToPath, pathToFileURL } from "node:url";
import { resolve, dirname } from "node:path";

const docs = resolve(dirname(fileURLToPath(import.meta.url)), "../../../docs/architecture");
const source = pathToFileURL(resolve(docs, "diagram/architecture.html")).href;

const browser = await chromium.launch({ channel: "chrome" });
// A4 landscape at 96 dpi is 1123 x 794; scale 2 gives print-quality JPEGs.
const page = await browser.newPage({ viewport: { width: 1123, height: 794 }, deviceScaleFactor: 2 });
await page.goto(source, { waitUntil: "load" });
await page.evaluate(() => document.fonts.ready);

await page.pdf({ path: resolve(docs, "architecture.pdf"), format: "A4", landscape: true, printBackground: true });
for (const id of ["system", "workflow"]) {
  await page.locator(`#${id}`).screenshot({ path: resolve(docs, `architecture-${id}.jpg`), type: "jpeg", quality: 92 });
}
await browser.close();
console.log("Wrote architecture.pdf, architecture-system.jpg and architecture-workflow.jpg");
