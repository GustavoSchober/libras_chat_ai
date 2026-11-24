"""Entrada da Vercel: reaproveita o ia/servidor.py (/api/saude e /api/glosa) como função."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ia"))
from servidor import Handler  # noqa: E402


# A Vercel só reconhece a função se `handler` for DEFINIDO aqui (classe/def/atribuição); import com `as` não conta.
class handler(Handler):
    pass
