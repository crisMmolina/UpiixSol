import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Each worktree gets its own port: API on $UAK_PORT, web on $UAK_PORT+1 (AGENTS.md §3.7).
const apiPort = Number(process.env.UAK_PORT ?? 8000);
const apiTarget = `http://127.0.0.1:${apiPort}`;

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: apiPort + 1,
    strictPort: true,
    proxy: { "/api": apiTarget, "/media": apiTarget },
  },
  // Budget is 250 KB gzip of initial JS (PROJECT.md); ~500 KB minified is roughly that.
  build: { sourcemap: false, chunkSizeWarningLimit: 500 },
});
