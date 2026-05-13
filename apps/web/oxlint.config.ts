import { defineConfig } from "oxlint";

export default defineConfig({
  categories: {
    correctness: "error",
    nursery: "off",
    pedantic: "off",
    perf: "warn",
    restriction: "off",
    style: "off",
    suspicious: "warn",
  },
  plugins: ["typescript", "react", "oxc"],
  rules: {
    "no-console": "warn",
    "typescript/no-unused-vars": "warn",
    "typescript/no-explicit-any": "warn",
    "react/exhaustive-deps": "warn",
    "react/no-direct-mutation-state": "error",
    "react/react-in-jsx-scope": "off",
  },
  ignorePatterns: [
    "dist/**",
    "*.gen.ts",
    "*.gen.tsx",
  ],
  overrides: [
    {
      files: ["vite.config.ts"],
      env: { node: true },
    },
    {
      files: ["**/*.{test,spec}.{ts,tsx}"],
      rules: {
        "no-console": "off",
      },
    },
  ],
});
