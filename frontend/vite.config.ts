import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";


export default defineConfig(({ mode }) => ({
  base: mode === "production" ? "/static/" : "/",
  plugins: [react()],
  build: {
    emptyOutDir: true,
    outDir: "../src/ai_hunger_games/web",
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/experiments": "http://127.0.0.1:8000",
      "/generations": "http://127.0.0.1:8000",
    },
  },
  test: {
    css: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
}));
