import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: true,
    proxy: {
      "/auth": { target: "http://localhost:8000", changeOrigin: true },
      "/admin": { target: "http://localhost:8000", changeOrigin: true },
      "/updates": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  build: {
  outDir: "../backend/static",
  emptyOutDir: true,
}