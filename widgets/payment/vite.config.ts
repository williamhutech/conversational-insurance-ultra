import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: {
    outDir: 'dist',
    assetsDir: '',
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        entryFileNames: 'payment-widget.js',
        assetFileNames: 'payment-widget.[ext]',
      },
    },
  },
  server: {
    port: 4444,
    cors: true,
  },
})
