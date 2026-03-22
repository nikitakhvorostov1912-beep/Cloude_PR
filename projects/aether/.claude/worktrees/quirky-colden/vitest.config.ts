import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    setupFiles: ['./src/test/setup.ts', './src/test/setup.jsdom.ts'],
    // Use jsdom for component and service tests that need browser APIs
    environment: 'jsdom',
    // Use singleFork to prevent OOM from multiple jsdom environments in parallel
    pool: 'forks',
    singleFork: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      // Focus coverage on the modules that are actually tested
      include: [
        'src/stores/**',
        'src/lib/**',
        'src/services/keys.service.ts',
        'src/services/file.service.ts',
        'src/components/glass/**',
        'src/types/api.types.ts',
      ],
      exclude: [
        'src/**/*.d.ts',
        'src/styles/**',
        'src/test/**',
      ],
      thresholds: {
        branches: 70,
        functions: 70,
        lines: 70,
        statements: 70,
      },
    },
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
