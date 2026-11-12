"""Suíte de regressão: 40 frases de verbos contra o Jev (passo 2 do KNOWLEDGE/13, Parte 8).

Pergunta que responde: o Jev escolhe o sinal certo em PORTUGUÊS?

Cada frase vira UMA requisição com 5 perguntas sobre o mesmo `state`:
  nomes      Choice, opções só com o nome da glosa (sem descrição)
  nomes_inv  idem, ordem invertida              → mede o viés de ordem (falha nº 8)
  estrut     Choice, descrição estruturada gerada da sintaxe da glosa (chaves em inglês)
  estrut_inv idem, ordem invertida
  existe     Noul companheiro: "algum candidato serve?"

Baseline: o tradutor do VLibras acertou 33/40 (82%) num conjunto de 40 frases de verbos
(KNOWLEDGE/11). Aquelas 40 não foram guardadas literalmente; esta suíte contém todas as que
o 11 cita nominalmente, mais armadilhas novas (direcionais verdadeiros, GOSTO substantivo,
negação, sentido &). A comparação com os 82% é indicativa, não pareada.

Uso:  .venv/bin/python ia/regressao_verbos.py
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidatos import candidatos, descrever  # noqa: E402
from jev import MODELO, PRECO_POR_TOKEN, perguntar  # noqa: E402

COMPRAR = {"COMPRAR", "COMPRAR&DINHEIRO", "COMPRAR&ADQUIRIR"}

# (frase, palavra-alvo, glosas aceitas, origem)
#   origem: "11-ok"  = o VLibras acertou no KNOWLEDGE/11
#           "11-err" = o VLibras errou no KNOWLEDGE/11 (Classe A ou B)
#           "nova"   = armadilha nova desta suíte
CASOS = [
    ("o rato roeu a roupa do rei", "roeu", {"ROER"}, "11-ok"),
    ("o cachorro mordeu o menino", "mordeu", {"MORDER"}, "11-ok"),
    ("ela comeu o bolo", "comeu", {"COMER"}, "11-ok"),
    ("ele rasgou o papel", "rasgou", {"RASGAR"}, "11-ok"),
    ("eu comprei um carro", "comprei", COMPRAR, "11-ok"),
    ("eu compro pão todo dia", "compro", COMPRAR, "11-ok"),
    ("amanhã comprarei um livro", "comprarei", COMPRAR, "11-ok"),
    ("eu vou comprar uma casa", "comprar", COMPRAR, "11-ok"),
    ("nós fizemos o trabalho", "fizemos", {"FAZER"}, "11-ok"),
    ("ela trouxe o presente", "trouxe", {"TRAZER"}, "11-ok"),
    ("ele disse a verdade", "disse", {"DIZER"}, "11-ok"),
    ("ele leu o livro", "leu", {"LER"}, "11-ok"),
    ("eu soube da notícia ontem", "soube", {"SABER"}, "11-ok"),
    ("nós viemos de ônibus", "viemos", {"VIR"}, "11-ok"),
    ("ela escreveu uma carta", "escreveu", {"ESCREVER", "ESCREVER&PAPEL"}, "11-ok"),
    ("ele bebeu água", "bebeu", {"BEBER"}, "11-ok"),
    ("ele perdeu a chave", "perdeu", {"PERDER"}, "11-ok"),
    ("o bebê dormiu cedo", "dormiu", {"DORMIR"}, "11-ok"),
    ("a criança caiu da escada", "caiu", {"CAIR", "CAIR&PESSOA"}, "11-ok"),
    ("ela abriu a porta", "abriu", {"ABRIR", "ABRIR&PORTA"}, "11-ok"),
    ("ele pagou a conta", "pagou", {"PAGAR"}, "11-ok"),
    ("ele le o jornal", "le", {"LER"}, "11-err"),
    ("ela cantou uma musica", "cantou", {"CANTAR"}, "11-err"),
    ("o menino correu rapido", "correu", {"CORRER", "CORRER&PESSOA"}, "11-err"),
    ("eu pus o livro na mesa", "pus", {"PÔR&COLOCAR"}, "11-err"),
    ("ele quis sair", "quis", {"QUERER"}, "11-err"),
    ("eu vi o filme", "vi", {"VER"}, "11-err"),
    ("ele pediu ajuda", "pediu", {"PEDIR"}, "11-err"),
    ("eu não gosto de futebol", "gosto", {"NÃO_GOSTAR"}, "nova"),
    ("o preço aumentou muito", "aumentou", {"AUMENTAR&VALOR", "AUMENTAR"}, "nova"),
    ("eu te vi ontem na praça", "vi", {"1S_VER_2S"}, "nova"),
    ("você me pediu um favor", "pediu", {"2S_PEDIR_1S"}, "nova"),
    ("ela pôs o casaco porque estava frio", "pôs", {"PÔR&ROUPA"}, "nova"),
    ("eu não quero isso", "quero", {"NÃO_QUERER"}, "nova"),
    ("eu gosto muito de chocolate", "gosto", {"GOSTAR(+)", "GOSTAR"}, "nova"),
    ("o gosto do café é amargo", "gosto", {"GOSTO"}, "nova"),
    ("nós não temos dinheiro", "temos", {"NÃO_TER"}, "nova"),
    ("ela não sabe nadar", "sabe", {"NÃO_SABER"}, "nova"),
    ("o carro correu muito na estrada", "correu", {"CORRER&VEÍCULO"}, "nova"),
    ("a água correu pelo chão da cozinha", "correu", {"CORRER&LÍQUIDO"}, "nova"),
]

INSTRUCOES = {
    "question": "Which Libras sign (gloss) translates the word `palavra` as it is used in "
                "the sentence `frase`?",
    "gloss_conventions": {
        "WORD&SENSE": "the same Portuguese word, restricted to one specific sense",
        "NÃO_WORD": "a sign with the negation built in; use it when the sentence negates it",
        "WORD(+) / WORD(-)": "intensified / attenuated version of the sign",
        "1S_WORD_2S": "directional verb that moves from one person (1S=I, 2S=you, 3S=he/she, "
                      "1P=we, 2P=you all, 3P=they) to another; only when the receiver is a "
                      "person",
        "WORD": "the plain sign, Portuguese word in uppercase",
    },
}


def montar(frase, palavra):
    cands = list(candidatos(palavra))
    inv = cands[::-1]
    nomes = lambda xs: {g: None for g in xs}                      # noqa: E731
    estrut = lambda xs: {g: descrever(g) for g in xs}              # noqa: E731
    q = {
        "nomes":      {"type": "choice", "instructions": INSTRUCOES, "criteria": nomes(cands)},
        "nomes_inv":  {"type": "choice", "instructions": INSTRUCOES, "criteria": nomes(inv)},
        "estrut":     {"type": "choice", "instructions": INSTRUCOES, "criteria": estrut(cands)},
        "estrut_inv": {"type": "choice", "instructions": INSTRUCOES, "criteria": estrut(inv)},
        "existe": {
            "type": "noul",
            "instructions": {"question": "Does at least one of these Libras signs correctly "
                                         "express the word `palavra` as used in `frase`?",
                             "signs": cands},
        },
    }
    return {"frase": frase, "palavra": palavra}, q, cands


def rodar(caso):
    frase, palavra, aceitas, origem = caso
    state, q, cands = montar(frase, palavra)
    if len(cands) == 1:  # candidato único é decidido em código: não gasta token
        return {"frase": frase, "palavra": palavra, "origem": origem, "aceitas": sorted(aceitas),
                "cands": cands, "recall": cands[0] in aceitas, "unico": True, "resp": None}
    t = time.perf_counter()
    r = perguntar(state, q)
    return {"frase": frase, "palavra": palavra, "origem": origem, "aceitas": sorted(aceitas),
            "cands": cands, "recall": bool(aceitas & set(cands)), "unico": False,
            "ms": round((time.perf_counter() - t) * 1000), "resp": r}


def main():
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(rodar, CASOS))

    variantes = ["nomes", "nomes_inv", "estrut", "estrut_inv"]
    tokens = sum(r["resp"]["usage"]["input_tokens"] for r in res if r["resp"])
    modelos = {r["resp"]["model"] for r in res if r["resp"]}

    print(f"\nmodelo: {modelos or MODELO}   frases: {len(res)}   "
          f"tokens de entrada: {tokens}   custo: US$ {tokens * PRECO_POR_TOKEN:.5f}")
    lat = sorted(r["ms"] for r in res if r["resp"])
    if lat:
        print(f"latência por requisição (5 perguntas): mediana {lat[len(lat)//2]} ms, "
              f"máx {max(lat)} ms")
    print(f"recall do gerador: {sum(r['recall'] for r in res)}/{len(res)}\n")

    acertos = {v: 0 for v in variantes}
    print(f"{'frase':42s} {'alvo':14s} " + " ".join(f"{v:>16s}" for v in variantes) + "  existe")
    for r in res:
        alvo = "|".join(r["aceitas"])[:14]
        if r["unico"]:
            linha = [f"{'(único) ' + r['cands'][0]:>16s}"] * 4
            for v in variantes:
                acertos[v] += r["recall"]
            print(f"{r['frase'][:42]:42s} {alvo:14s} " + " ".join(linha) + "     —")
            continue
        a = r["resp"]["answers"]
        linha = []
        for v in variantes:
            ok = a[v]["choice"] in r["aceitas"]
            acertos[v] += ok
            linha.append(f"{('✓ ' if ok else '✗ ') + a[v]['choice'][:11]} {a[v]['confidence']:.2f}"
                         .rjust(16))
        print(f"{r['frase'][:42]:42s} {alvo:14s} " + " ".join(linha) +
              f"  {a['existe']['noul']:.2f}")

    print()
    n = len(res)
    for v in variantes:
        print(f"  {v:11s} {acertos[v]:2d}/{n}  {acertos[v] / n:5.1%}")
    print(f"  baseline VLibras (KNOWLEDGE/11, conjunto não pareado): 33/40  82.5%")

    # por origem
    print()
    for origem in ("11-ok", "11-err", "nova"):
        sub = [r for r in res if r["origem"] == origem]
        linha = []
        for v in variantes:
            k = sum((r["recall"] if r["unico"] else r["resp"]["answers"][v]["choice"] in r["aceitas"])
                    for r in sub)
            linha.append(f"{v} {k}/{len(sub)}")
        print(f"  {origem:7s} " + "   ".join(linha))

    # confidence: acerto vs erro (é o número que vai para o `if`)
    print()
    for v in ("nomes", "estrut"):
        ok, err = [], []
        for r in res:
            if r["unico"]:
                continue
            x = r["resp"]["answers"][v]
            (ok if x["choice"] in r["aceitas"] else err).append(x["confidence"])
        m = lambda xs: sum(xs) / len(xs) if xs else float("nan")  # noqa: E731
        print(f"  confidence {v:7s} acertos {m(ok):.2f} (n={len(ok)})   "
              f"erros {m(err):.2f} (n={len(err)})")

    out = Path(__file__).resolve().parent / "resultados"
    out.mkdir(exist_ok=True)
    arq = out / f"regressao_verbos_{datetime.now():%Y%m%d_%H%M%S}.json"
    arq.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=list))
    print(f"\nbruto salvo em {arq.relative_to(Path.cwd()) if arq.is_relative_to(Path.cwd()) else arq}")


if __name__ == "__main__":
    main()
