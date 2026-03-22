import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// @ts-expect-error process is a nodejs global
const host = process.env.TAURI_DEV_HOST;

export default defineConfig(async () => ({
  plugins: [react(), tailwindcss()],
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-docx': ['docx', 'jszip', 'file-saver'],
          'vendor-motion': ['motion'],
        },
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  clearScreen: false,
  server: {
    port: 1421,
    strictPort: true,
    host: host || false,
    hmr: host
      ? {
          protocol: "ws",
          host,
          port: 1422,
        }
      : undefined,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
    proxy: {
      "/api/anthropic": {
        target: "https://api.anthropic.com",
        changeOrigin: true,
        rewrite: (p: string) => p.replace(/^\/api\/anthropic/, ""),
      },
      "/api/openai": {
        target: "https://api.openai.com",
        changeOrigin: true,
        rewrite: (p: string) => p.replace(/^\/api\/openai/, ""),
      },
      "/api/groq": {
        target: "https://api.groq.com/openai",
        changeOrigin: true,
        rewrite: (p: string) => p.replace(/^\/api\/groq/, ""),
      },
      "/api/gemini": {
        target: "https://generativelanguage.googleapis.com/v1beta/openai",
        changeOrigin: true,
        rewrite: (p: string) => p.replace(/^\/api\/gemini/, ""),
      },
      "/api/deepseek": {
        target: "https://api.deepseek.com",
        changeOrigin: true,
        rewrite: (p: string) => p.replace(/^\/api\/deepseek/, ""),
      },
      "/api/mimo": {
        target: "https://api.xiaomimimo.com",
        changeOrigin: true,
        rewrite: (p: string) => p.replace(/^\/api\/mimo/, ""),
      },
      "/api/cerebras": {
        target: "https://api.cerebras.ai",
        changeOrigin: true,
        rewrite: (p: string) => p.replace(/^\/api\/cerebras/, ""),
      },
      "/api/mistral": {
        target: "https://api.mistral.ai",
        changeOrigin: true,
        rewrite: (p: string) => p.replace(/^\/api\/mistral/, ""),
      },
      "/api/openrouter": {
        target: "https://openrouter.ai",
        changeOrigin: true,
        rewrite: (p: string) => p.replace(/^\/api\/openrouter/, ""),
      },
    },
  },
}));
