import { describe, expect, it } from "vitest";
import { CONTRACT_FIXTURES } from "./contractFixtures";

/*
  File snapshots (paths resolve relative to this file): `pnpm contracts:fixtures` (vitest -u)
  rewrites packages/contracts/fixtures; a normal run fails when they drift.
*/
describe("shared contract fixtures", () => {
  it.each(Object.entries(CONTRACT_FIXTURES))("%s matches the web fixture", async (name, build) => {
    await expect(JSON.stringify(build(), null, 2) + "\n").toMatchFileSnapshot(
      `../../../../packages/contracts/fixtures/${name}`,
    );
  });
});
