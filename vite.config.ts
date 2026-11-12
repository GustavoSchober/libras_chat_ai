import { spawn } from 'node:child_process'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

const API = 'http://127.0.0.1:8765'

// `npm run dev` sobe o ia/servidor.py junto: a chave do Jev fica nele, nunca no navegador.
// Se já houver um servidor na 8765, o novo falha com "address in use" e o proxy usa o que está de pé.
function servidorPython(): Plugin {
  return {
    name: 'servidor-python',
    apply: 'serve',
    configureServer(server) {
      const py = spawn('.venv/bin/python', ['ia/servidor.py'], { stdio: 'inherit' })
      const parar = () => py.kill()
      server.httpServer?.on('close', parar)
      process.on('exit', parar)
    },
  }
}

export default defineConfig({
  root: 'web',
  plugins: [react(), servidorPython()],
  server: {
    proxy: { '/api': API, '/dados/bundles.json': API },
  },
})
