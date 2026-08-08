import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api to the FastAPI backend so the frontend can use same-origin paths.
// API_TARGET overrides the backend address, e.g. when :8033 is taken:
//   API_TARGET=http://localhost:8017 npm run dev
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5206,
    proxy: {
      "/api": {
        target: process.env.API_TARGET ?? "http://localhost:8033",
        changeOrigin: true,
      },
    },
  },
});
