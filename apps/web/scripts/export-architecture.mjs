// Exports docs/architecture/diagram/architecture.html and its shortened copy
// architecture-short.html to the submission formats: <name>.pdf (two A4 landscape
// pages) and one JPEG per page. Pass a name to export just one, for example
// `node scripts/export-architecture.mjs architecture-short`.
import { chromium } from "@playwright/test";
import { fileURLToPath, pathToFileURL } from "node:url";
import { resolve, dirname } from "node:path";

const docs = resolve(dirname(fileURLToPath(import.meta.url)), "../../../docs/architecture");
const names = process.argv[2] ? [process.argv[2]] : ["architecture", "architecture-short"];

const browser = await chromium.launch({ channel: "chrome" });
// A4 landscape at 96 dpi is 1123 x 794; scale 2 gives print-quality JPEGs.
const page = await browser.newPage({ viewport: { width: 1123, height: 794 }, deviceScaleFactor: 2 });
for (const name of names) {
  await page.goto(pathToFileURL(resolve(docs, `diagram/${name}.html`)).href, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);

  await page.pdf({ path: resolve(docs, `${name}.pdf`), format: "A4", landscape: true, printBackground: true });
  for (const id of ["system", "workflow"]) {
    await page.locator(`#${id}`).screenshot({ path: resolve(docs, `${name}-${id}.jpg`), type: "jpeg", quality: 92 });
  }
  console.log(`Wrote ${name}.pdf, ${name}-system.jpg and ${name}-workflow.jpg`);
}
await browser.close();
