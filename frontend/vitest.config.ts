import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    // Test environment
    environment: 'jsdom',
    
    // Global test timeout (milliseconds)
    testTimeout: 10000,
    
    // Hook timeout
    hookTimeout: 10000,
    
    // Test globals (no need to import describe, it, expect, etc.)
    globals: true,
    
    // Include patterns
    include: ['src/**/*.{test,spec}.{js,ts,jsx,tsx}'],
    
    // Exclude patterns
    exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],
    
    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/**/*.test.{js,ts,jsx,tsx}',
        'dist/',
      ],
      statements: 60,
      branches: 60,
      functions: 60,
      lines: 60,
    },
    
    // Setup files
    setupFiles: ['./src/tests/setup.ts'],
    
    // Globals setup
    mockReset: true,
    restoreMocks: true,
    clearMocks: true,
  },
  
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@tests': path.resolve(__dirname, './src/tests'),
    },
  },
});
