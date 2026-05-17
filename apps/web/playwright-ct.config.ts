import { fileURLToPath } from 'node:url';
import { defineConfig, devices } from '@playwright/experimental-ct-react';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const appRoot = fileURLToPath(new URL('.', import.meta.url));
const srcRoot = fileURLToPath(new URL('./src', import.meta.url));

export default defineConfig({
  fullyParallel: true,
  reporter: [['list'], ['html', { open: 'never' }]],
  retries: 0,
  testDir: './tests/components',
  testMatch: '**/*.spec.tsx',
  use: {
    baseURL: 'http://127.0.0.1:3100',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ctPort: 3100,
    ctCacheDir: './playwright/.cache',
    ctViteConfig: {
      plugins: [react(), tailwindcss()] as never,
      resolve: {
        alias: {
          '@': srcRoot,
        },
      },
      root: appRoot,
    },
    ...devices['Desktop Chrome'],
  },
  projects: [
    {
      name: 'chromium-ct',
    },
  ],
});
