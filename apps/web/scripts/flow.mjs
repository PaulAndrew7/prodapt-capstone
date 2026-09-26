// Drives the vendor flow end to end and captures each state.
// node scripts/flow.mjs <outDir> [width] [height]
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";

const [out = "../../.impeccable/review/p04", w = "1440", h = "900"] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const base = process.env.BASE ?? "http://localhost:5173";
const browser = await chromium.launch({ channel: "chrome" });
const page = await (await browser.newContext({ viewport: { width: +w, height: +h } })).newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
const shot = async (name, full = false) => {
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${out}/${name}.png`, fullPage: full });
  console.log("shot", name);
};

await page.goto(`${base}/app/cases/new`, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
await shot("01-new-case");
await page.getByRole("button", { name: /Share data with a new vendor/ }).click();
await page.getByRole("button", { name: "Assess" }).click();
await page.waitForURL(/\/app\/cases\/case_/);
await page.waitForTimeout(1600);
await shot("02-running");
await page.getByRole("heading", { name: /questions before I finish/ }).waitFor({ timeout: 15000 });
await shot("03-clarification");
await page.getByRole("radio", { name: "I don’t know" }).click();
await page.getByLabel("Which customer fields will you share, and for what purpose?").fill("Customer ID, postcode and product holdings, for churn modelling.");
await page.getByRole("button", { name: "Answer" }).click();
await page.getByText("Non-compliant.", { exact: false }).first().waitFor({ timeout: 20000 });
await shot("04-verdict");
await shot("04b-verdict-full", true);
await page.getByRole("button", { name: /Open evidence §4.2 v1 for Data-owner approval/ }).first().click();
await page.waitForTimeout(900);
await shot("05-evidence");
await page.getByRole("button", { name: "Close evidence" }).click();
await page.getByRole("tab", { name: "Requirements" }).click();
await shot("06-requirements");
await page.getByRole("tab", { name: "Trace" }).click();
await shot("07-trace");
await page.getByRole("button", { name: "Try a hypothetical" }).click();
await page.getByRole("button", { name: "Run hypothetical" }).click();
await page.getByText("Compliant within scope.").first().waitFor({ timeout: 10000 });
await shot("08-hypothetical", true);

console.log(errors.length ? `ERRORS:\n${errors.join("\n")}` : "no console errors");
await browser.close();
