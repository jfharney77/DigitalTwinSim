import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// The gallery is the visual reference for the shared components — the page the
// dell-clean-design skill checks against. It renders every component in
// twin-ui with no backend and no twin, so a skin change is visible in one
// place before it is applied in forty-two.
export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  plugins: [react()],
  server: { port: 5171 },
  build: { outDir: "../dist-gallery", emptyOutDir: true },
});
