import { fileURLToPath } from 'node:url';
import { defineConfig, devices } from '@playwright/experimental-ct-react';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

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
        dedupe: [
          'react',
          'react-dom',
          '@tanstack/react-query',
          '@tanstack/react-router',
          '@tanstack/router-core',
          '@heroui/react',
          '@heroui/system',
        ],
        alias: {
          '@': srcRoot,
        },
      },
    },
    ...devices['Desktop Chrome'],
  },
  projects: [
    {
      name: 'chromium-ct',
    },
  ],
});
