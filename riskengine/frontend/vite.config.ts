import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/signals': 'http://127.0.0.1:8000',
      '/analyze': 'http://127.0.0.1:8000',
      '/events': 'http://127.0.0.1:8000',
      '/risk-summary': 'http://127.0.0.1:8000',
      '/refresh': 'http://127.0.0.1:8000',
      '/sources': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/portfolio': 'http://127.0.0.1:8000',
      '/rebalance': 'http://127.0.0.1:8000',
      '/backtest': 'http://127.0.0.1:8000',
      '/stress-test': 'http://127.0.0.1:8000',
      '/portfolio-composition': 'http://127.0.0.1:8000',
    }
  }
})
