import { expect, test } from "@playwright/test";

test.use({ reducedMotion: "reduce" });
for (const width of [1440, 390]) {
  test(`local fallback explains confirmations and supports early finish at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.route("**/__local-review-test", async (route) => {
      const response = await route.fetch({ url: new URL("/", route.request().url()).href });
      await route.fulfill({ response, body: (await response.text()).replace("/src/main.tsx", "/e2e/fixtures/local-review.tsx") });
    });
    await page.goto("/__local-review-test");
    await expect(page.getByLabel("Local review mode")).toBeVisible();
    await expect(page.getByText(/failed during analysis/)).toBeVisible();
    const save = page.getByRole("button", { name: "Save confirmations" });
    await expect(save).toBeDisabled();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `../../tmp/local-review-${width}.png`, fullPage: true });
    const finish = page.getByRole("button", { name: "Finish with remaining checks unknown" });
    await finish.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Not enough to decide." })).toBeVisible();
    await expect(page.getByLabel("Local review mode")).toBeVisible();
    await page.emulateMedia({ media: "print" });
    await expect(page.getByText("local-review-v1")).toBeVisible();
    await expect(page.getByText(/No language model semantically validated this result/)).toBeVisible();
  });
}
