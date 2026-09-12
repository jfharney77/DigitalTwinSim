import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// The shared skin and shell live in packages/twin-ui, consumed as a workspace
// package. The alias makes it resolve from the source without a build step or
// an npm install — the declared dependency in package.json is what a fresh
// checkout installs.
const twinUi = fileURLToPath(new URL("../../packages/twin-ui/src", import.meta.url));

// Proxy /api to the FastAPI backend so the frontend can use same-origin paths.
// API_TARGET overrides the backend address, e.g. when :8032 is taken:
//   API_TARGET=http://localhost:8017 npm run dev
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@twinsim/twin-ui": twinUi } },
  server: {
    port: 5205,
    proxy: {
      "/api": {
        target: process.env.API_TARGET ?? "http://localhost:8032",
        changeOrigin: true,
      },
    },
  },
});
