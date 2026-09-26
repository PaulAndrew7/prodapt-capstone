import { expect, test } from "@playwright/test";

test("front door leads into the demo", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("pinned to its clause");
  await page.getByRole("link", { name: "Enter demo" }).first().click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: /Describe what you.re planning to do/ })).toBeVisible();
});

test("vendor case: clarify, verdict, evidence, hypothetical", async ({ page }) => {
  await page.goto("/app/cases/new");
  await page.getByRole("button", { name: /Share data with a new vendor/ }).click();
  await page.getByRole("button", { name: "Assess" }).click();
  await page.getByRole("heading", { name: /questions before I finish/ }).waitFor({ timeout: 15_000 });
  await page.getByRole("radio", { name: "I don’t know" }).click();
  await page.getByLabel("Which customer fields will you share, and for what purpose?").fill("Customer ID and postcode, for churn modelling.");
  await page.getByRole("button", { name: "Answer" }).click();
  await expect(page.getByRole("heading", { name: "Non-compliant." })).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: /Open evidence §4.2 v1 for Data-owner approval/ }).first().click();
  const drawer = page.locator('aside[aria-labelledby="evidence-h"]');
  await expect(drawer.locator("mark").first()).toContainText("requires written approval from the data owner");
  await page.keyboard.press("Escape");
  await expect(drawer).toBeHidden();
  await page.getByRole("button", { name: "Try a hypothetical" }).click();
  await page.getByRole("button", { name: "Run hypothetical" }).click();
  await expect(page.getByText("Compliant within scope.").first()).toBeVisible({ timeout: 10_000 });
});

test("citation link opens the policy with the cited words marked", async ({ page }) => {
  await page.goto("/app/cases/case_vendor_share");
  await page.getByRole("button", { name: /Open evidence §4.2 v1 for Data-owner approval/ }).first().click();
  await page.getByRole("link", { name: "Open in policy" }).first().click();
  await expect(page).toHaveURL(/\/app\/policies\/ds\/versions\/ds_v1\?clause=/);
  await expect(page.locator('[id="ds_v1_4_4.2"] mark')).toContainText("recorded in the data-sharing register");
});

test.describe("reduced motion", () => {
  test.use({ reducedMotion: "reduce" });
  test("front door skips the 3D scene and shows the still", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForTimeout(800);
    await expect(page.locator("section canvas")).toHaveCount(0);
    await expect(page.locator('img[src="/front/policy-stack.webp"]').first()).toBeAttached();
  });
});
