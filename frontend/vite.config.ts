import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Entwicklung: API-Aufrufe an das lokale Backend weiterleiten.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: { outDir: "dist", sourcemap: false },
});
