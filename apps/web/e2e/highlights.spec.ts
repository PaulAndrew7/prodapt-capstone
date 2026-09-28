import { expect, test, type Locator } from "@playwright/test";

async function sweep(mark: Locator) {
  return mark.evaluate((el) => parseFloat((el as HTMLElement).style.getPropertyValue("--sweep")));
}

for (const theme of ["light", "dark"] as const) {
  for (const reducedMotion of ["no-preference", "reduce"] as const) {
    test.describe(`${theme}, ${reducedMotion}`, () => {
      test.use({ colorScheme: theme, reducedMotion, viewport: { width: 390, height: 844 } });

      test("highlights remain readable through delay, playback and reset", async ({ page }) => {
        await page.route("**/__highlight-test", async (route) => {
          const response = await route.fetch({ url: "http://localhost:5173/" });
          await route.fulfill({ response, body: (await response.text()).replace("/src/main.tsx", "/e2e/fixtures/highlight.tsx") });
        });
        await page.goto("/__highlight-test");
        const mark = page.locator("h1 mark");
        const text = theme === "dark" ? "rgb(237, 241, 238)" : "rgb(17, 20, 19)";
        await expect(mark).toHaveText("backed by policy.");
        await expect(mark).toHaveCSS("color", text);
        await expect.poll(() => sweep(mark)).toBe(0);
        await expect(mark.locator(".mark-word-overlay").first()).toHaveCSS("clip-path", /100%/);
        await expect(page.getByRole("heading", { name: "Your next move, backed by policy." })).toBeVisible();

        // Multiline text and transformed ancestors reproduce the original rendering conditions.
        expect(await page.locator("p mark .mark-word").evaluateAll((words) =>
          new Set(words.map((word) => Math.round(word.getBoundingClientRect().top))).size,
        )).toBeGreaterThan(1);

        await page.getByRole("button").click();
        if (reducedMotion === "no-preference") {
          await expect.poll(() => sweep(mark)).toBe(0);
          await expect.poll(async () => {
            const value = await sweep(mark);
            return value > 0 && value < 100;
          }, { intervals: [30] }).toBe(true);
          await expect(mark).toHaveCSS("color", text);
        }
        await expect.poll(() => sweep(mark)).toBe(100);
        await expect(mark.locator(".mark-word-overlay").first()).toHaveCSS("color", "rgb(17, 20, 19)");
        await expect(mark.locator(".mark-word-overlay").first()).toHaveCSS("background-image", /rgb\(221, 255, 60\)/);
        await expect(mark.locator(".mark-word-overlay").first()).toHaveCSS("clip-path", / 0% /);
        await expect(page.locator(".mark-span")).toHaveCSS("color", "rgb(17, 20, 19)");

        await page.getByRole("button").click();
        await expect.poll(() => sweep(mark)).toBe(0);
        await expect(mark).toHaveCSS("color", text);
        await expect(mark.locator(".mark-word-overlay").first()).toHaveCSS("clip-path", /100%/);
        await page.getByRole("button").click();
        await expect.poll(() => sweep(mark)).toBe(100);
        await expect(mark).toHaveText("backed by policy.");
      });
    });
  }
}
