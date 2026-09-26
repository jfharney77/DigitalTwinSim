import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// The shared skin and shell live in packages/twin-ui, consumed as a workspace
// package. The alias makes it resolve from the source without a build step or
// an npm install — the declared dependency in package.json is what a fresh
// checkout installs.
const twinUi = fileURLToPath(new URL("../../packages/twin-ui/src", import.meta.url));

// Proxy /api to the FastAPI backend so the frontend can use same-origin paths.
// API_TARGET overrides the backend address, e.g. when :8046 is taken:
//   API_TARGET=http://localhost:8017 npm run dev
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@twinsim/twin-ui": twinUi } },
  server: {
    port: 5219,
    proxy: {
      "/api": {
        target: process.env.API_TARGET ?? "http://localhost:8046",
        changeOrigin: true,
      },
      // "Fed by engines" mode reads the composition layer (compose/, :8048),
      // which runs the detailed twins and carries their outputs in across
      // tested seams. Optional: with nothing there, the control disables
      // itself. COMPOSE_TARGET moves it when :8048 is taken.
      "/compose-api": {
        target: process.env.COMPOSE_TARGET ?? "http://localhost:8048",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/compose-api/, "/api"),
      },
    },
  },
});
