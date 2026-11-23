"""Entrada da Vercel: reaproveita o ia/servidor.py (/api/saude e /api/glosa) como função."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ia"))
from servidor import Handler as handler  # noqa: E402,F401
