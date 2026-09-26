import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  use: { baseURL: "http://localhost:5173", channel: "chrome", viewport: { width: 1440, height: 900 } },
  webServer: { command: "corepack pnpm dev", url: "http://localhost:5173", reuseExistingServer: true, timeout: 60_000 },
});
