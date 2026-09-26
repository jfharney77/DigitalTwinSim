import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// The shared skin and shell live in packages/twin-ui, consumed as a workspace
// package. The alias makes it resolve from the source without a build step or
// an npm install — the declared dependency in package.json is what a fresh
// checkout installs.
const twinUi = fileURLToPath(new URL("../../packages/twin-ui/src", import.meta.url));

// Proxy /api to the FastAPI backend so the frontend can use same-origin paths.
// API_TARGET overrides the backend address, e.g. when :8034 is taken:
//   API_TARGET=http://localhost:8017 npm run dev
//
// strictPort is deliberate. Without it Vite silently walks to the next free
// port, which on a machine running several twins means squatting a sibling's
// port — the sibling's links then open this app instead, and nobody is told.
// Failing to start is the honest outcome. If 5207 is taken and you only need
// this app running, take a spare port instead:
//   PORT=5307 npm run dev
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@twinsim/twin-ui": twinUi } },
  server: {
    port: Number(process.env.PORT ?? 5207),
    strictPort: true,
    proxy: {
      "/api": {
        target: process.env.API_TARGET ?? "http://localhost:8034",
        changeOrigin: true,
      },
    },
  },
});
