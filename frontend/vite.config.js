import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";
import { fileURLToPath } from "url";

const rootDir = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [vue()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(rootDir, "index.html"),
        app: resolve(rootDir, "app.html"),
      },
    },
  },
  resolve: {
    alias: {
      "@/api": resolve(rootDir, "src/api"),
      "@/components": resolve(rootDir, "src/components"),
      "@/composables": resolve(rootDir, "src/composables"),
      "@/layouts": resolve(rootDir, "src/layouts"),
      "@/modules": resolve(rootDir, "src/api"),
      "@/stores": resolve(rootDir, "src/stores"),
      "@/styles": resolve(rootDir, "src/styles"),
      "@/utils": resolve(rootDir, "src/utils"),
      "@": resolve(rootDir, "src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_DEV_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
