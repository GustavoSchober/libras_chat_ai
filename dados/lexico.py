"""Extrai do bundles.json o léxico estruturado que já está lá dentro."""
import json, re, collections, unicodedata

S = set(json.load(open(__import__('os').path.join(__import__('os').path.dirname(__file__), 'bundles.json'))))

def sem_acento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')

# ── índices derivados do acervo ──────────────────────────────────────────────
NEG = {g[4:]: g for g in S if g.startswith('NÃO_') and g[4:] in S}

SENTIDOS = collections.defaultdict(list)
for x in S:
    if '&' in x:
        base, sent = x.split('&', 1)
        SENTIDOS[base].append((sent, x))

INTENS = collections.defaultdict(dict)
for x in S:
    m = re.match(r'^(.+)\(([+-])\)$', x)
    if m:
        INTENS[m.group(1)][m.group(2)] = x

DIRECIONAL = collections.defaultdict(set)
for x in S:
    m = re.match(r'^([123][SP])_(.+)_([123][SP])$', x)
    if m:
        DIRECIONAL[m.group(2)].add((m.group(1), m.group(3)))

# índice sem acento → forma correta (resolve "MUSICA" → "MÚSICA")
SEM_ACENTO = {}
for x in S:
    SEM_ACENTO.setdefault(sem_acento(x), x)

print(f"acervo: {len(S)} glosas")
print(f"  negação incorporada  : {len(NEG)} pares  (X / NÃO_X)")
print(f"  palavras polissêmicas: {len(SENTIDOS)} ({sum(1 for v in SENTIDOS.values() if len(v) > 1)} com >1 sentido)")
print(f"  pares de intensidade : {len(INTENS)}")
print(f"  verbos direcionais   : {len(DIRECIONAL)}")
print(f"  índice sem acento    : {len(SEM_ACENTO)}")
print()

# ── o corretor determinístico ────────────────────────────────────────────────
MARCAS_NEG = {'NÃO', 'NAO', 'NUNCA', 'JAMAIS', 'NENHUM', 'NENHUMA', 'NADA'}
VAZIAS = {'DE', 'DA', 'DO', 'DAS', 'DOS', 'A', 'O', 'AS', 'OS', 'UM', 'UMA',
          'EM', 'NO', 'NA', 'PARA', 'POR', 'COM', 'QUE'}

def corrigir(glosa):
    """Aplica só o que o acervo permite decidir sem ambiguidade."""
    toks = glosa.split()
    out, notas, i = [], [], 0
    while i < len(toks):
        t = toks[i]

        # 1) acento faltando: MUSICA -> MÚSICA
        if t not in S and sem_acento(t) in SEM_ACENTO:
            novo = SEM_ACENTO[sem_acento(t)]
            notas.append(f'{t} → {novo} (acento)')
            t = novo

        # 2) palavra funcional sem sinal: seria soletrada à toa
        if t in VAZIAS and t not in S:
            notas.append(f'{t} removido (não existe em Libras)')
            i += 1
            continue

        # 3) negação + verbo → forma incorporada do acervo
        if t in MARCAS_NEG and i + 1 < len(toks):
            prox = toks[i + 1]
            prox = SEM_ACENTO.get(sem_acento(prox), prox)
            if prox in NEG:
                notas.append(f'{t} {toks[i+1]} → {NEG[prox]} (negação incorporada)')
                out.append(NEG[prox])
                i += 2
                continue

        out.append(t)
        i += 1
    return ' '.join(out), notas


CASOS = [
    ("eu nao gosto de futebol",   "NAO GOSTO DE FUTEBOL",            "NÃO_GOSTAR FUTEBOL"),
    ("eu nao quero isso",         "EU NAO QUERO ISSO",               "EU NÃO_QUERER ISSO"),
    ("ela cantou uma musica",     "ELA CANTAR MUSICA",               "ELA CANTAR MÚSICA"),
    ("o menino correu rapido",    "MENINO CORRER&PESSOA RAPIDO",     "MENINO CORRER&PESSOA RÁPIDO"),
    ("nao tenho dinheiro",        "NAO TER DINHEIRO",                "NÃO_TER DINHEIRO"),
    ("eu nao sei nada",           "EU NAO SABER NADA",               "EU NÃO_SABER NADA"),
    ("nunca comi isso",           "NUNCA COMER ISSO",                "NÃO_COMER ISSO"),
]

print("=== o corretor determinístico, caso a caso ===")
acertos = 0
for pt, entrada, esperado in CASOS:
    saida, notas = corrigir(entrada)
    ok = saida == esperado
    acertos += ok
    print(f"  {'OK ' if ok else 'ERR'} {pt}")
    print(f"      antes : {entrada}")
    print(f"      depois: {saida}")
    if not ok:
        print(f"      queria: {esperado}")
    for n in notas:
        print(f"        · {n}")
print(f"\n  {acertos}/{len(CASOS)} corrigidos sem nenhuma IA")

print()
print("=== o que o acervo NÃO consegue decidir sozinho ===")
for palavra in ['GOSTO', 'PODER', 'BANCO', 'MANGA']:
    alts = SENTIDOS.get(palavra, [])
    extra = ' | também existe como glosa simples' if palavra in S else ''
    print(f"  {palavra:8s} {len(alts)} sentidos: {sorted(s for s, _ in alts)}{extra}")
