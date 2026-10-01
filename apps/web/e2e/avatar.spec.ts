import { expect, test } from "@playwright/test";
import { LOOKS, type Expression } from "../src/features/avatar/expressions";

const expressions = Object.keys(LOOKS) as Expression[];

for (const reducedMotion of ["no-preference", "reduce"] as const) {
  test.describe(reducedMotion, () => {
    test.use({ reducedMotion });

    test("every expression draws its hands and emote, and nothing else", async ({ page }) => {
      const errors: string[] = [];
      page.on("pageerror", (e) => errors.push(e.message));
      await page.route("**/__avatar-test", async (route) => {
        const response = await route.fetch({ url: new URL("/", route.request().url()).href });
        await route.fulfill({ response, body: (await response.text()).replace("/src/main.tsx", "/e2e/fixtures/avatar.tsx") });
      });
      await page.goto("/__avatar-test");
      await expect(page.locator("figure")).toHaveCount(expressions.length);
      for (const e of expressions) {
        const svg = page.locator(`figure[data-expression="${e}"] svg`);
        await expect(svg).toBeVisible();
        await expect(svg.locator('[data-part="hands"] > *')).toHaveCount(LOOKS[e].hands === "none" ? 0 : 1);
        await expect(svg.locator('[data-part="emote"] > *')).toHaveCount(LOOKS[e].emote === "none" ? 0 : 1);
      }
      expect(errors).toEqual([]);
    });
  });
}
