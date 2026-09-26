import type { ComplianceApi } from "./client";
import { FixtureApi } from "./fixtureApi";
import { HttpApi } from "./httpApi";

export const api: ComplianceApi =
  import.meta.env.VITE_API_MODE === "http" ? new HttpApi() : new FixtureApi();

export * from "./types";
export type { ComplianceApi } from "./client";
