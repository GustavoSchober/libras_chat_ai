#!/usr/bin/env bash
# Regenera os snapshots versionados em dados/.
#
# Eles são commitados de propósito: o POC depende deles em runtime, são pequenos
# (~355 KB somados) e congelam um acervo de terceiros que pode mudar ou sair do ar.
# Trate como lockfile — atualize conscientemente, não a cada execução.
#
#   ./dados/atualizar.sh

set -euo pipefail
cd "$(dirname "$0")"

echo "→ bundles.json — as glosas que o avatar sabe fazer"
curl -fsS "https://dicionario2.vlibras.gov.br/bundles" -o bundles.json.novo
python3 -c "
import json
b = json.load(open('bundles.json.novo'))
assert isinstance(b, list) and len(b) > 20000, f'resposta suspeita: {len(b)} itens'
print(f'  {len(b)} glosas')
"
mv bundles.json.novo bundles.json

echo "→ vlibrasil_sinais.txt — os sinais do corpus de vídeo no Hugging Face"
python3 - <<'PY'
import json, re, urllib.request
url = ("https://huggingface.co/api/datasets/SchberGg/v-librasil-raw"
       "/tree/main/videos?limit=1000")
nomes = []
while url:
    with urllib.request.urlopen(url, timeout=60) as r:
        nomes += [x["path"].rsplit("/", 1)[-1]
                  for x in json.load(r) if x["type"] == "file"]
        link = r.headers.get("Link", "")
    m = re.search(r'<([^>]+)>;\s*rel="next"', link)
    url = m.group(1) if m else None

sinais = sorted({re.sub(r"_Articulador\d+$", "", n.rsplit(".", 1)[0]) for n in nomes})
assert len(sinais) > 1000, f"resposta suspeita: {len(sinais)} sinais"
open("vlibrasil_sinais.txt", "w").write("\n".join(sinais))
print(f"  {len(nomes)} vídeos, {len(sinais)} sinais distintos")
PY

echo
echo "Pronto. Revise o diff antes de commitar:  git diff --stat dados/"
