import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Override when port 8000 is taken: API_URL=http://127.0.0.1:8001 npm run dev
    proxy: { "/api": process.env.API_URL ?? "http://127.0.0.1:8000" },
  },
  build: {
    chunkSizeWarningLimit: 900,
  },
  test: {
    environment: "node",
  },
});
