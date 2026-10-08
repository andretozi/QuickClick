import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// No "npm run dev" (porta 5173) as chamadas /api vão para o back do main.py.
const API_PROXY = { '/api': 'http://127.0.0.1:8080' };

export default defineConfig({
  plugins: [react()],
  // Caminhos relativos: o build funciona em qualquer subpasta (ex.: GitHub Pages).
  base: './',
  resolve: {
    // Permite importar com "@/..." a partir de src/, sem "../../.."
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) }
  },
  server: { proxy: API_PROXY },
  preview: { proxy: API_PROXY },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    cssCodeSplit: true,
    reportCompressedSize: false,
    target: 'es2019'
  }
});
