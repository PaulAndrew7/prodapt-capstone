import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    port: 5173,
    // Same-origin API in http mode (VITE_API_MODE=http): /api and /health go to FastAPI.
    proxy: {
      "/api": process.env.VITE_API_PROXY ?? "http://localhost:8000",
      "/health": process.env.VITE_API_PROXY ?? "http://localhost:8000",
    },
  },
});
