import { defineConfig } from 'vite';

export default defineConfig({
  base: '/mapper/',
  build: {
    outDir: 'dist',
  },
  test: {
    exclude: ['tests/visual/**', 'node_modules/**'],
  },
});
