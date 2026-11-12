"""Servidor local do LIBRAS AI CHAT.

  GET  /...                  o app (web/dist, gerado por `npm run build`)
  GET  /poc/...               a prova de conceito antiga
  GET  /dados/bundles.json    o acervo, para a validação no navegador
  POST /api/glosa             {"texto": "..."} → glosa montada com o Jev (ia/glosa.py)

A chave do Jev fica AQUI, no servidor; o navegador nunca a vê. Por isso só uma lista
fechada de caminhos é servida: nada de .env.local, doc_ai/ ou ia/.

Uso:  npm run dev    (Vite em :5173 sobe este servidor junto e repassa /api para cá)
      npm start      (build + este servidor sozinho em :8765, como vai para produção)
"""
import json
import os
import sys
import traceback
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glosa import glosar  # noqa: E402
from jev import verificar_chave  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
HOST = os.environ.get("HOST", "127.0.0.1")
PORTA = int(os.environ.get("PORT", 8765))
DIST = RAIZ / "web" / "dist"
LIBERADOS = [(RAIZ / "poc").resolve(), (RAIZ / "dados" / "bundles.json").resolve(), DIST.resolve()]


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        caminho = self.path.split("?", 1)[0]
        if caminho == "/api/saude":
            return self._saude()
        if not caminho.startswith(("/poc", "/dados/")) and DIST.is_dir():
            self.path = "/web/dist" + (caminho if caminho != "/" else "/index.html")
        elif caminho in ("/", "/poc"):
            self.send_response(302)
            self.send_header("Location", "/poc/")
            self.end_headers()
            return
        # Confere o caminho JÁ RESOLVIDO no disco: checar a string crua deixa passar
        # /poc/%2e%2e/.env.local (o servidor decodifica depois).
        alvo = Path(self.translate_path(self.path)).resolve()
        if not any(alvo == p or p in alvo.parents for p in LIBERADOS):
            self.send_error(404)
            return
        super().do_GET()

    def _saude(self):
        """A página consulta isto ao abrir: o motor de IA está de pé E a chave é aceita?"""
        try:
            r = verificar_chave()
            self._json(200, {"ok": r, "motor": "jev",
                             "erro": None if r else "chave do Jev recusada (.env.local)"})
        except Exception as e:
            self._json(200, {"ok": False, "motor": "jev", "erro": str(e)[:200]})

    def do_POST(self):
        if self.path != "/api/glosa":
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            texto = json.loads(self.rfile.read(n) or b"{}").get("texto", "").strip()
            if not texto or len(texto) > 500:
                return self._json(400, {"erro": "texto vazio ou longo demais (máx. 500)"})
            r = glosar(texto)
            print(f"[glosa] {r['ms']:4d} ms  US$ {r['custo_usd']:.6f}  {texto!r} → {r['glosa']}",
                  flush=True)
            self._json(200, r)
        except Exception as e:  # o navegador cai para o tradutor do governo
            traceback.print_exc()
            self._json(502, {"erro": str(e)[:300]})

    def end_headers(self):
        # Sem cache: versão velha da página no navegador já fez a IA parecer desligada.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, status, obj):
        corpo = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, fmt, *args):
        if not self.path.startswith(("/api/", "/poc/", "/web/dist/index.html")):
            return
        super().log_message(fmt, *args)


if __name__ == "__main__":
    srv = ThreadingHTTPServer((HOST, PORTA), partial(Handler, directory=str(RAIZ)))
    print(f"LIBRAS AI CHAT: API em http://{HOST}:{PORTA}"
          + ("  (app em /)" if DIST.is_dir() else "  (sem build: rode npm run dev)"), flush=True)
    srv.serve_forever()
