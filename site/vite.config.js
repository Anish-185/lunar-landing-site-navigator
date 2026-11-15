import { defineConfig } from "vite";

// Relative base: the same build works on GitHub Pages (/<repo>/) and locally.
export default defineConfig({
  base: "./",
  build: { target: "es2022", assetsInlineLimit: 0, chunkSizeWarningLimit: 4000 },
});
