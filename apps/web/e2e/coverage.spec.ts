import { expect, test } from "@playwright/test";

test.use({ reducedMotion: "reduce" });

for (const width of [1440, 390]) {
  test(`coverage inspector preserves omitted clauses at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.route("**/__coverage-test", async (route) => {
      const response = await route.fetch({ url: new URL("/", route.request().url()).href });
      await route.fulfill({ response, body: (await response.text()).replace("/src/main.tsx", "/e2e/fixtures/coverage.tsx") });
    });
    await page.goto("/__coverage-test");
    const coverage = page.getByRole("region", { name: "Evidence coverage" });
    await expect(coverage.getByText("Review needed")).toBeVisible();
    const inspect = coverage.locator("summary").filter({ hasText: "Inspect 2 retrieved candidates" });
    await inspect.focus();
    await page.keyboard.press("Enter");
    const retention = coverage.locator("summary").filter({ hasText: "§4.5 · Retention period" });
    await retention.focus();
    await page.keyboard.press("Enter");
    await expect(coverage.getByText(/Each external share must record a retention period/)).toBeVisible();
    await expect(coverage.getByRole("link", { name: "Open original PDF for §4.5 Retention period · page 2" })).toHaveAttribute("href", "/api/v1/policy-versions/ds_v2/source?page=2");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `../../tmp/coverage-${width}.png`, fullPage: true });
    await page.emulateMedia({ media: "print" });
    await expect(page.getByRole("heading", { name: /Retention period — unassessed/ })).toBeVisible();
    await expect(page.getByText(/Retrieved candidates: 2. Accounted for: 1. Unresolved: 1/)).toBeVisible();
  });
}
