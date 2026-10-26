import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    // This checkout lives on a network-mounted home directory (HPC), where
    // the default fs.watch/inotify-based watcher frequently misses file
    // change events entirely -- edits land on disk but never trigger HMR,
    // so the dev server keeps serving whatever was loaded at last restart.
    // Polling stat()s each watched file on an interval instead, which is
    // reliable on network filesystems at the cost of slightly higher CPU.
    watch: {
      usePolling: true,
      interval: 300
    }
  }
})
