"""Gerador de candidatos: palavra em português → glosas do acervo que ela PODE ser.

É o teto do sistema (KNOWLEDGE/13, Parte 5): se a glosa certa não está aqui, o Jev não tem
como escolhê-la. Por isso o gerador é generoso de propósito — inclui as armadilhas (PUS,
NÃO_X, 1S_X_2S) — e quem decide é o Jev, com o contexto da frase.
"""
import difflib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import simplemma

RAIZ = Path(__file__).resolve().parent.parent
ACERVO = json.load(open(RAIZ / "dados" / "bundles.json"))
S = set(ACERVO)


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def base(g):
    """PÔR&COLOCAR → PÔR · GOSTAR(+) → GOSTAR · NÃO_GOSTAR → NÃO_GOSTAR."""
    return re.sub(r"\([+-]\)$", "", g.split("&")[0])


# Índices sobre o acervo, em espaço sem acento (a busca ignora acento; a glosa devolvida
# mantém o acento, porque é o nome do bundle: RÚSSIA existe, RUSSIA não).
POR_BASE = {}
DIRECIONAL = {}
for g in ACERVO:
    POR_BASE.setdefault(sem_acento(base(g)), []).append(g)
    m = re.match(r"^[123][SP]_(.+)_[123][SP]$", g)
    if m:
        DIRECIONAL.setdefault(sem_acento(m.group(1)), []).append(g)
CHAVES_SIMPLES = [k for k in POR_BASE if "_" not in k and " " not in k]

# Formas que o lematizador não resolve. Pequena e explícita de propósito.
# "pus" é o caso-símbolo: substantivo (a secreção) E passado de pôr. Os dois entram.
IRREGULARES = {
    **{f: ["pôr"] for f in "pus pôs puseste pusemos puseram pusesse ponho põe põem pondo posto".split()},
    **{f: ["ser", "ir"] for f in "fui foi fomos foram fora".split()},
    # futuro/condicional e particípios irregulares que a regra de sufixo não alcança
    **{f: ["fazer"] for f in "farei farás fará faremos farão faria farias faríamos fariam fiz fez fizemos fizeram feito feita feitos feitas".split()},
    **{f: ["dizer"] for f in "direi dirá diremos dirão diria diriam disse disseram dito dita".split()},
    **{f: ["trazer"] for f in "trarei trará traremos trarão traria trouxe trouxeram".split()},
    **{f: ["morrer", "morto"] for f in "morto morta mortos mortas".split()},
    **{f: ["doer"] for f in "dói doem doía".split()},
    **{f: ["ver"] for f in "visto vi viu vimos viram".split()},
    **{f: ["vir"] for f in "vindo vim veio viemos vieram".split()},
    **{f: ["abrir"] for f in "aberto aberta abertos abertas".split()},
    **{f: ["escrever"] for f in "escrito escrita escritos escritas".split()},
    **{f: ["trazer"] for f in "traga tragas tragam tragamos".split()},   # Traga-me ≠ TRAGAR
    **{f: ["ir"] for f in "irei irás irá iremos irão iria irias iríamos iriam".split()},
    **{f: ["pôr", "colocar"] for f in "ponha ponham pus pôs posto posta".split()},
}

# Segunda tentativa, só quando o lema do simplemma não achou NADA no acervo (medido em
# 20 mil frases do Tatoeba: ele devolve irei → irar, garotas → garotar, vazia → vaziar).
# Só sobrevive o que existe como sinal, então o ruído é limitado; e por vir depois, não põe
# CASO e CASAR na frente de "casa", que já acha CASA na primeira tentativa.
FLEXOES = [
    # gênero e número
    ("ões", "ão"), ("ães", "ão"), ("ais", "al"), ("éis", "el"), ("eis", "el"), ("óis", "ol"),
    ("res", "r"), ("zes", "z"), ("as", "o"), ("os", "o"), ("a", "o"), ("as", "a"), ("s", ""),
    ("oras", "or"), ("ora", "or"), ("esas", "ês"), ("esa", "ês"),   # professora → professor
    # diminutivo: gatinho → gato, casinha → casa, cafezinho → café
    ("zinhos", ""), ("zinhas", ""), ("zinho", ""), ("zinha", ""),
    ("inhos", "o"), ("inhas", "a"), ("inho", "o"), ("inha", "a"), ("inha", "o"),
    # particípio
    ("ados", "ar"), ("adas", "ar"), ("ado", "ar"), ("ada", "ar"),
    ("idos", "er"), ("idas", "er"), ("ido", "er"), ("ida", "er"),
    ("idos", "ir"), ("idas", "ir"), ("ido", "ir"), ("ida", "ir"),
    # futuro e condicional
    ("rei", "r"), ("rás", "r"), ("rá", "r"), ("remos", "r"), ("rão", "r"),
    ("ria", "r"), ("rias", "r"), ("ríamos", "r"), ("riam", "r"),
    # subjuntivo e imperativo, com a troca de grafia (jogue → jogar, fique → ficar, comece → começar)
    ("guem", "gar"), ("gues", "gar"), ("gue", "gar"), ("quem", "car"), ("ques", "car"), ("que", "car"),
    ("cem", "çar"), ("ce", "çar"), ("çam", "cer"), ("ça", "cer"), ("ço", "cer"),
    ("em", "ar"), ("es", "ar"), ("e", "ar"), ("am", "er"), ("am", "ir"), ("a", "er"), ("a", "ir"),
    # "tu" e nós/subjuntivo: esperas → esperar, comes → comer, imprimamos → imprimir
    ("as", "ar"), ("es", "er"), ("es", "ir"), ("amos", "er"), ("amos", "ir"), ("emos", "ar"),
    # imperfeito e pretérito
    ("ávamos", "ar"), ("avam", "ar"), ("ava", "ar"), ("íamos", "er"), ("íamos", "ir"),
    ("iam", "er"), ("iam", "ir"), ("ia", "er"), ("ia", "ir"),
    ("aram", "ar"), ("eram", "er"), ("iram", "ir"), ("ou", "ar"), ("eu", "er"), ("iu", "ir"),
]


def _flexionar(p):
    """garotas → garota/garoto · perdoe → perdoar · alegremente → alegre · irei → ir."""
    if p.endswith("mente") and len(p) > 7:
        # advérbio: a base é o adjetivo no feminino (cuidadosamente → cuidadosa → cuidadoso);
        # sem as regras de verbo, senão alegremente ganha ALEGRAR
        b = p[:-5]
        return [v for v in (b, b[:-1] + "o" if b.endswith("a") else b)
                if sem_acento(v.upper()) in POR_BASE]
    out = []
    for suf, troca in FLEXOES:
        # radical de 3+ letras: com 2, Maria virava MAR (ma + -ria) e Lia virava LER
        if p.endswith(suf) and len(p) - len(suf) >= 3:
            v = p[: -len(suf)] + troca
            if v not in out and sem_acento(v.upper()) in POR_BASE:
                out.append(v)
    return out

VOGAIS = {"a": "áâãà", "e": "éê", "i": "í", "o": "óôõ", "u": "ú"}


def _variantes_acento(p):
    """'le' → ['lé','lê'] — só as que o lematizador reconhece como palavra."""
    out = []
    for i, c in enumerate(p):
        for v in VOGAIS.get(c, ""):
            w = p[:i] + v + p[i + 1:]
            if simplemma.is_known(w, lang="pt"):
                out.append(w)
    return out


# O simplemma devolve UM lema, e escolhe o substantivo quando a forma é ambígua
# ("gosto" → gosto, nunca gostar). Esta redução propõe o infinitivo também; só sobrevive o
# que existe como sinal no acervo, então o ruído é limitado.
TERMINACOES = [
    ("aram", "ar"), ("eram", "er"), ("iram", "ir"), ("amos", "ar"), ("emos", "er"),
    ("imos", "ir"), ("ando", "ar"), ("endo", "er"), ("indo", "ir"), ("ava", "ar"),
    ("ou", "ar"), ("ei", "ar"), ("eu", "er"), ("iu", "ir"), ("am", "ar"), ("em", "er"),
    ("o", "ar"), ("o", "er"), ("o", "ir"), ("a", "ar"), ("e", "er"), ("e", "ir"),
]


def _infinitivos(p):
    out = []
    for suf, inf in TERMINACOES:
        if p.endswith(suf) and len(p) - len(suf) >= 2:
            v = p[: -len(suf)] + inf
            if sem_acento(v.upper()) in POR_BASE and v not in out:
                out.append(v)
    return out


def lemas(palavra):
    p = palavra.lower()
    formas = [p] + IRREGULARES.get(p, [])
    # plural simples já na 1ª tentativa: o simplemma leva "unhas" a UNHAR e nunca a UNHA
    formas += [f for f in (p[:-1] if p.endswith("s") and len(p) > 3 else "",
                           p[:-2] if p.endswith("es") and len(p) > 4 else "") if f]
    if not simplemma.is_known(p, lang="pt"):
        formas += _variantes_acento(p)  # "le" → "lê" → ler
    out = []
    for f in formas:
        for x in (f, simplemma.lemmatize(f, lang="pt"), *_infinitivos(f)):
            if x not in out:
                out.append(x)
    return out


@lru_cache(maxsize=4096)
def candidatos_detalhe(palavra, k_vizinhos=4):
    """→ (candidatos, origem) com origem em 'exato' | 'flexao' | 'vizinho' | 'nenhum'.

    'flexao' é exato também, só que achado pela regra de sufixo (garotas → GAROTA).

    'vizinho' quer dizer "só parecido na grafia" — pode não ter relação nenhuma de sentido,
    então quem chama deve oferecer a opção de soletrar.
    """
    out = []

    def add(xs):
        for x in xs:
            if x not in out:
                out.append(x)

    for lema in lemas(palavra):
        n = sem_acento(lema.upper())
        add(sorted(POR_BASE.get(n, [])))                       # exato + grupo & + (+)/(-)
        add(sorted(POR_BASE.get("NAO_" + n, [])))              # par de negação
        add(sorted(DIRECIONAL.get(n, [])))                     # 1S_VER_2S e companhia
    if out:
        return tuple(out), "exato"
    for lema in lemas(palavra):
        for v in _flexionar(lema):
            add(sorted(POR_BASE.get(sem_acento(v.upper()), [])))
    if out:
        return tuple(out), "flexao"
    # vizinhança ortográfica: só se nada exato apareceu (senão vira ruído: VER → VERDE…)
    for lema in lemas(palavra):
        n = sem_acento(lema.upper())
        for m in difflib.get_close_matches(n, CHAVES_SIMPLES, n=k_vizinhos, cutoff=0.82):
            add(sorted(POR_BASE[m]))
    return tuple(out), ("vizinho" if out else "nenhum")


# Siglas: TV, SUS, ONU existem direto no acervo; IA → INTELIGÊNCIA_ARTIFICIAL pelas iniciais.
# Iniciais costumam casar com mais de um composto (IA → IDADE_ANTIGA, IGUAL_A): o Jev escolhe.
INICIAIS = {}
for g in ACERVO:
    if "_" in g and "&" not in g and not re.match(r"^[123][SP]_", g):
        INICIAIS.setdefault("".join(sem_acento(x[0]) for x in g.split("_") if x), []).append(g)


def candidatos_sigla(palavra):
    if palavra in S:    # TV, SUS, ONU: o sinal da sigla existe, não há o que escolher
        return (palavra,)
    return tuple(sorted(INICIAIS.get(sem_acento(palavra), [])))


LETRAS = "abcdefghijklmnopqrstuvwxyzáàâãéêíóôõúç"


@lru_cache(maxsize=1024)
def corrigir(palavra, n=3, so_forte=False):
    """Palavra fora do dicionário → até n correções que TÊM sinal no acervo (distância 1).

    Sem lista de frequência, a ordem é: a correção que é ela mesma um sinal (felis → feliz,
    não falis), depois letras trocadas de lugar (vcoê → você), depois o resto.
    A forma mostrada leva o acento do acervo: amanha → amanhã.
    """
    w = palavra.lower()
    s = [(w[:i], w[i:]) for i in range(len(w) + 1)]
    trocas = {a + b[1] + b[0] + b[2:] for a, b in s if len(b) > 1}
    outras = ({a + b[1:] for a, b in s if b} | {a + c + b[1:] for a, b in s if b for c in LETRAS}
              | {a + c + b for a, b in s for c in LETRAS})
    achadas = {}
    # "forte" = letras trocadas de lugar ou letra repetida: quase nunca é um nome próprio
    repetidas = {a + b[1:] for a, b in s if len(b) > 1 and b[0] == b[1]}
    grupos = ((0, trocas | repetidas),) if so_forte else ((0, trocas | repetidas), (1, outras - trocas))
    for peso, grupo in grupos:
        for c in grupo:
            if not c or c == w or not simplemma.is_known(c, lang="pt"):
                continue
            cands, origem = candidatos_detalhe(c)
            if origem not in ("exato", "flexao"):
                continue
            direto = sem_acento(base(cands[0])) == sem_acento(c.upper())
            forma = base(cands[0]).lower() if direto else c
            achadas[forma] = min(achadas.get(forma, (9, 9)), (0 if direto else 1, peso))
    return [f for f, _ in sorted(achadas.items(), key=lambda x: (x[1], x[0]))][:n]


def candidatos(palavra, k_vizinhos=4):
    return candidatos_detalhe(palavra, k_vizinhos)[0]


def descrever(g):
    """Descrição estruturada gerada a partir da SINTAXE da glosa — sem dicionário, sem LLM.

    Chaves em inglês (a língua forte do Jev), valores em português (são o sinal em si).
    """
    m = re.match(r"^([123][SP])_(.+)_([123][SP])$", g)
    if m:
        pessoa = {"1S": "eu (I)", "2S": "você (you)", "3S": "ele/ela (he/she)",
                  "1P": "nós (we)", "2P": "vocês (you all)", "3P": "eles (they)"}
        return {"kind": "directional verb", "verb": m.group(2).lower(),
                "from": pessoa[m.group(1)], "to": pessoa[m.group(3)],
                "use_only_if": "the action is directed at that specific PERSON "
                               "(the receiver is a person, not a thing)"}
    d = {}
    if g.startswith("NÃO_"):
        d["kind"] = "negated sign"
        d["meaning"] = f"não {base(g)[4:].lower()}"
        d["use_only_if"] = "the sentence negates this word"
        g2 = g[4:]
    else:
        d["word"] = base(g).lower()
        g2 = g
    if "&" in g2:
        d["specific_sense"] = " / ".join(s.lower() for s in g2.split("&")[1:])
    if g2.endswith("(+)"):
        d["intensity"] = "intensified (muito / a lot)"
    elif g2.endswith("(-)"):
        d["intensity"] = "attenuated (pouco / a little)"
    return d


if __name__ == "__main__":
    import sys
    for w in sys.argv[1:] or "pus quis vi pediu roeu gosto aumentou le musica".split():
        c = candidatos(w)
        print(f"{w:10s} {len(c):3d}  {list(c)[:14]}{' …' if len(c) > 14 else ''}")
