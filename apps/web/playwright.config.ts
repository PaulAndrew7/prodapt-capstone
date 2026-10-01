import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  use: { baseURL: "http://localhost:5174", channel: "chrome", viewport: { width: 1440, height: 900 } },
  // Fixture tests must not attach to a user's live-mode demo on port 5173.
  webServer: {
    command: "corepack pnpm dev --port 5174 --strictPort",
    url: "http://localhost:5174",
    env: { VITE_API_MODE: "fixture" },
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
