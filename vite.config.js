import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild',
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
        manualChunks(id) {
          if (id.includes('node_modules/react') || id.includes('node_modules/react-router')) return 'vendor-react'
          if (id.includes('node_modules/motion')) return 'vendor-motion'
          if (id.includes('node_modules/ogl')) return 'vendor-ogl'
          if (id.includes('node_modules/lucide') || id.includes('node_modules/unicornstudio')) return 'vendor-ui'
          if (id.includes('node_modules/@supabase') || id.includes('node_modules/@vercel')) return 'vendor-services'
        }
      }
    }
  },
  server: {
    port: 5173,
    open: true
  },
  preview: {
    port: 4173
  }
})
