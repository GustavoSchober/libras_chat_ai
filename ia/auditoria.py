"""Auditoria em massa da glosa com frases reais do Tatoeba (dados/cache/tatoeba/).

Não há gabarito: o objetivo é achar PADRÕES suspeitos e revisar cada padrão uma vez, em vez
de revisar frase a frase. Duas passadas:

  codigo   grátis, sem Jev: o que o código decide sozinho (soletrar, descartar, compostos,
           siglas, "erro de digitação"). Tatoeba é texto limpo, então todo "parece erro de
           digitação" aqui é FALSO POSITIVO do corretor — é o termômetro dele.
  jev      paga (~US$ 0,00006/frase): as escolhas do Jev, agrupadas por palavra → sinal,
           com a confiança média. Grava cada frase em .jsonl e retoma de onde parou.

Uso:
  .venv/bin/python ia/auditoria.py codigo [--n 20000]
  .venv/bin/python ia/auditoria.py jev --n 2000 [--rotulo base]
Saída: ia/resultados/auditoria/
"""
import argparse
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from glosa import glosar, preparar  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CORPUS = RAIZ / "dados" / "cache" / "tatoeba" / "por_sentences.tsv"
SAIDA = RAIZ / "ia" / "resultados" / "auditoria"
# O público é brasileiro; frases com marca forte de Portugal distorcem a contagem.
LUSITANAS = re.compile(r"\b(estás|tens|connosco|facto|contacto|equipa|autocarro|comboio|"
                       r"telemóvel|pequeno-almoço|vós|sois|estou a|está a|estão a|tu)\b", re.I)


def frases(n, semente=42):
    vistas, todas = set(), []
    for linha in CORPUS.read_text(encoding="utf-8").splitlines():
        partes = linha.split("\t")
        if len(partes) < 3:
            continue
        f = partes[2].strip()
        k = f.lower()
        if k in vistas or not 3 <= len(f.split()) <= 10 or LUSITANAS.search(f) or re.search(r"\d", f):
            continue
        vistas.add(k)
        todas.append(f)
    random.Random(semente).shuffle(todas)
    return todas[:n]


def exemplos(d, chave, frase, m=3):
    if len(d[chave]) < m:
        d[chave].append(frase)


def passada_codigo(n):
    cont = defaultdict(Counter)       # balde → palavra → n
    ex = defaultdict(list)
    t0 = time.time()
    lista = frases(n)
    for i, f in enumerate(lista):
        itens, perguntas, _, _ = preparar(f)
        for it in itens:
            w = it["palavra"].lower()
            fonte = it["fonte"]
            if fonte == "soletrado":
                b = "soletrado_nome" if "nome próprio" in it.get("nota", "") else "soletrado"
            elif fonte == "duvida":
                b = "duvida_falso_positivo"
            elif fonte == "jev" and "SOLETRAR" in it.get("candidatos", []):
                b = "so_vizinho" if not w.isupper() else "sigla"
            elif fonte == "composto":
                b, w = "composto", f"{w} → {it['tok']}"
            elif fonte == "funcional":
                b = "descartada"
            else:
                continue
            cont[b][w] += 1
            exemplos(ex, (b, w), f)
        if i and i % 2000 == 0:
            print(f"  {i}/{len(lista)}  {time.time() - t0:.0f}s", flush=True)
    return {"frases": len(lista), "segundos": round(time.time() - t0),
            "baldes": {b: [{"palavra": w, "n": c, "exemplos": ex[(b, w)],
                            **({"sugestoes": preparar_sug(w)} if b == "duvida_falso_positivo" else {})}
                           for w, c in cont[b].most_common()]
                       for b in cont}}


def preparar_sug(w):
    itens, *_ = preparar(w)
    return itens[0].get("sugestoes", []) if itens else []


def passada_jev(n, rotulo):
    SAIDA.mkdir(parents=True, exist_ok=True)
    arq = SAIDA / f"jev_{rotulo}.jsonl"
    feitas = {json.loads(l)["frase"] for l in arq.open()} if arq.exists() else set()
    lista = frases(n)
    custo, t0 = 0.0, time.time()
    with arq.open("a") as out:
        for i, f in enumerate(lista):
            if f in feitas:
                continue
            try:
                r = glosar(f)
            except Exception as e:  # uma frase ruim não derruba o lote
                print(f"  erro em {f!r}: {e}", flush=True)
                continue
            custo += r["custo_usd"]
            out.write(json.dumps({"frase": f, "glosa": r["glosa"], "itens": [
                {k: it.get(k) for k in ("palavra", "tok", "fonte", "confianca", "alternativas",
                                        "candidatos", "nota")} for it in r["itens"]],
                "descartadas": r["descartadas"]}, ensure_ascii=False) + "\n")
            if i % 100 == 0:
                print(f"  {i}/{len(lista)}  US$ {custo:.4f}  {time.time() - t0:.0f}s", flush=True)
    print(f"custo desta rodada: US$ {custo:.4f}")
    return arq


def resumo_jev(arq):
    """palavra → sinal escolhido, com confiança média; destaca palavra com mais de um sinal."""
    linhas = [json.loads(l) for l in arq.open()]
    pares = defaultdict(list)
    ex = defaultdict(list)
    for r in linhas:
        for it in r["itens"]:
            if it["fonte"] != "jev":
                continue
            k = (it["palavra"].lower(), it["tok"])
            pares[k].append(it["confianca"])
            exemplos(ex, k, f"{r['frase']}  →  {r['glosa']}", 2)
    por_palavra = defaultdict(list)
    for (w, tok), cs in pares.items():
        por_palavra[w].append({"tok": tok, "n": len(cs), "conf": round(sum(cs) / len(cs), 2),
                               "exemplos": ex[(w, tok)]})
    saida = sorted(({"palavra": w, "total": sum(x["n"] for x in v),
                     "sinais": sorted(v, key=lambda x: -x["n"])} for w, v in por_palavra.items()),
                   key=lambda x: -x["total"])
    return {"frases": len(linhas), "palavras": saida}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("passada", choices=["codigo", "jev"])
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--rotulo", default="base")
    a = ap.parse_args()
    SAIDA.mkdir(parents=True, exist_ok=True)
    if a.passada == "codigo":
        r = passada_codigo(a.n)
        destino = SAIDA / f"codigo_{a.rotulo}.json"
    else:
        r = resumo_jev(passada_jev(a.n, a.rotulo))
        destino = SAIDA / f"jev_{a.rotulo}_resumo.json"
    destino.write_text(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"→ {destino}")
