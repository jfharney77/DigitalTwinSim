import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api to the FastAPI backend so the frontend can use same-origin paths.
// API_TARGET overrides the backend address, e.g. when :8039 is taken:
//   API_TARGET=http://localhost:8040 npm run dev
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5212,
    proxy: {
      "/api": {
        target: process.env.API_TARGET ?? "http://localhost:8039",
        changeOrigin: true,
      },
    },
  },
});
