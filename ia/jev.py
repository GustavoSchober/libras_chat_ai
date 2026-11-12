"""Cliente mínimo do Jev (TypeSafe) — uma função, sem SDK.

A chave vem de TYPESAFE_API_KEY (ambiente) ou de .env.local / .env na raiz do repo.
Ver KNOWLEDGE/13-camada-de-ia-jev.md.
"""
import json
import os
import time
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
URL = "https://api.typesafe.ai/v1/systemone"
# Versão fixa, não o alias: thresholds de confidence são calibrados contra UMA versão.
MODELO = "jev-1.14.0"
PRECO_POR_TOKEN = 0.042 / 1_000_000  # US$ por token de entrada; saída é de graça

# Conexão reaproveitada (keep-alive): sem isso cada frase paga um handshake TLS novo.
_SESSAO = requests.Session()


def _chave():
    if os.environ.get("TYPESAFE_API_KEY"):
        return os.environ["TYPESAFE_API_KEY"]
    for nome in (".env.local", ".env"):
        p = RAIZ / nome
        if p.exists():
            for linha in p.read_text().splitlines():
                if linha.startswith("TYPESAFE_API_KEY="):
                    v = linha.split("=", 1)[1].strip().strip('"').strip("'")
                    if v:
                        return v
    raise RuntimeError("TYPESAFE_API_KEY não encontrada (.env.local)")


_CHAVE_OK = {"t": 0.0, "ok": False}


def verificar_chave(ttl=300):
    """GET /v1/models não consome crédito: serve para saber se a chave é aceita."""
    if time.time() - _CHAVE_OK["t"] < ttl:
        return _CHAVE_OK["ok"]
    r = _SESSAO.get("https://api.typesafe.ai/v1/models",
                    headers={"Authorization": f"Bearer {_chave()}"}, timeout=10)
    _CHAVE_OK.update(t=time.time(), ok=r.status_code == 200)
    return _CHAVE_OK["ok"]


def perguntar(state, questions, modelo=MODELO, tentativas=5):
    """Uma requisição, N perguntas. Devolve o JSON da resposta (answers, usage, model)."""
    corpo = {"model": modelo, "state": state, "questions": questions}
    cab = {"Authorization": f"Bearer {_chave()}", "Content-Type": "application/json"}
    espera = 1.0
    for i in range(tentativas):
        r = _SESSAO.post(URL, headers=cab, data=json.dumps(corpo, ensure_ascii=False).encode(),
                          timeout=30)
        if r.status_code in (429, 529) and i < tentativas - 1:
            time.sleep(float(r.headers.get("retry-after", espera)))
            espera *= 2
            continue
        if r.status_code != 200:
            raise RuntimeError(f"Jev {r.status_code}: {r.text[:500]}")
        return r.json()
