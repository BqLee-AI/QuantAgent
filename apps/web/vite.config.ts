import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import { fileURLToPath } from "node:url";

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const isProductionBundle = command === "build";
  const apiProxyTarget = env.VITE_DEV_API_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [
      tanstackRouter({
        target: "react",
        autoCodeSplitting: true,
      }),
      react(),
      tailwindcss(),
    ],
    resolve: {
      dedupe: [
        "react",
        "react-dom",
        "@tanstack/react-query",
        "@tanstack/react-router",
        "@tanstack/router-core",
        "@heroui/react",
        "@heroui/system",
      ],
      alias: [
        {
          find: /^@\/debug\/route-api\.runtime$/,
          replacement: fileURLToPath(
            new URL(
              isProductionBundle
                ? "./src/debug/route-api.production.ts"
                : "./src/debug/route-api.development.tsx",
              import.meta.url,
            ),
          ),
        },
        {
          find: "@",
          replacement: fileURLToPath(new URL("./src", import.meta.url)),
        },
      ],
    },
    server: {
      proxy: {
        "/api": {
          target: apiProxyTarget,
        },
      },
      watch: {
        ignored: [
          "**/playwright-report/**",
          "**/test-results/**",
          "**/playwright/.cache/**",
        ],
      },
    },
  };
});
