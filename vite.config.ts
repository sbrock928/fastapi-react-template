import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  root: '.', // Set the root directory to project root instead of frontend
  publicDir: 'frontend/public',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'frontend'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true,
    },
    proxy: {
      '/api': {
        // Use backend service name when running in Docker, fallback to localhost otherwise
        target: process.env.NODE_ENV === 'development' && process.env.DOCKER_ENV === 'true' 
          ? 'http://backend:8000' 
          : (process.env.VITE_API_BASE_URL || 'http://localhost:8000'),
        changeOrigin: true,
        secure: false,
      },
      '/docs': {
        // Use backend service name when running in Docker, fallback to localhost otherwise
        target: process.env.NODE_ENV === 'development' && process.env.DOCKER_ENV === 'true' 
          ? 'http://backend:8000' 
          : (process.env.VITE_API_BASE_URL || 'http://localhost:8000'),
        changeOrigin: true,
        secure: false,
      },
    },
  },
  optimizeDeps: {
    include: ['bootstrap'],
  },
  build: {
    outDir: 'static', // Updated path (no need for '../' since root is now at project level)
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          bootstrap: ['bootstrap'],
        },
      },
    },
  },
});