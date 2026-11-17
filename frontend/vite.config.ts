// Vite dev server, build, and Vitest settings for the Lyrx page.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    // Load styles.css as real text so styles.test.ts can read it with ?raw.
    css: { include: [/\/src\/styles\.css/] },
  },
});
