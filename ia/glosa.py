"""Frase em português → glosa de Libras, com o Jev escolhendo e o código montando.

Fluxo (KNOWLEDGE/13, Parte 4):
  1. código   tokeniza; junta compostos do acervo (bom dia → BOM_DIA)
  2. código   descarta palavras funcionais; separa pronomes oblíquos, "não", "muito"
  3. código   levanta candidatos no acervo para cada palavra de conteúdo
  4. JEV      UMA requisição: uma Choice por palavra ambígua + emoção + intensidade
  5. código   absorve "não"/"muito"/pronomes quando o sinal escolhido já os contém
  6. código   tempo para o começo (ONTEM ...), pontuação no fim
  7. código   valida tudo contra o acervo; o que não existe é soletrado, COM aviso

O Jev nunca escreve texto: só escolhe entre glosas que existem no acervo.
"""
import re
from itertools import product
import time
from functools import lru_cache

import simplemma

from candidatos import S, base, candidatos_detalhe, candidatos_sigla, corrigir, descrever, sem_acento
from jev import MODELO, PRECO_POR_TOKEN, perguntar

# Abaixo disto o tutor avisa que não tem certeza (KNOWLEDGE/13, Parte 10: média 0,84 nos
# acertos, 0,37 nos erros). Calibrar com mais dados.
LIMIAR_INCERTO = 0.5

VAZIAS = set("""o a os as um uma uns umas de da do das dos em no na nos nas num numa nuns numas
ao aos à às pelo pela pelos pelas para pra pro por com que e é dum duma""".split())
# Interjeição não tem sinal (as que têm, como UAU e UFA, ficam: só sai o que não está no acervo).
INTERJEICOES = set("oh ah ó né ei hum hmm ué ops opa ahn eh uh".split())
# Às vezes sinal, às vezes só gramática: o Jev decide pelo contexto com a opção OMITIR.
#   se   → SE condicional ("se chover") ou reflexivo/passivo, sem sinal ("a mala se perdeu")
#   ter  → TER de posse ou auxiliar de tempo composto ("tinha comido"), sem sinal
# estar + gerúndio é aspecto, não sinal: "estou procurando" → PROCURAR
ESTAR = set("""estar estou está estás estamos estão estava estavas estávamos estavam esteve estive
estivemos estiveram esteja estejam estivesse estivessem estará estarão estaria estariam estarei""".split())
TER = set("""ter tenho tens tem temos têm tinha tinhas tínhamos tinham tive teve tivemos tiveram
terei terá teremos terão teria teriam tenha tenham tivesse tivessem""".split())
OMITIR = {
    "se": {"kind": "no sign", "meaning": "reflexive or passive 'se' (ele se machucou, "
           "a mala se perdeu, vende-se): it is grammar only, Libras has no sign for it",
           "use_only_if": "`se` is NOT a conditional 'if' and NOT 'whether'"},
    "ter": {"kind": "no sign", "meaning": "auxiliary 'ter' that only builds a compound tense with "
            "the next verb (tinha comido, tenho estudado, queria não ter gastado)",
            "use_only_if": "the next word is a past participle of a verb, not an object owned"},
}
SE = {"word": "se", "meaning": "conditional 'if' (se chover, se você quiser) or 'whether' "
      "(não sei se ele vem)"}
# Expressões feitas só de palavras gramaticais: valem como fórmula sozinha ("De nada!"),
# não no meio da frase ("não sei de nada", "acho que isso funciona") — medido no Tatoeba.
SO_ISOLADAS = {"DE_NADA", "QUE_ISSO", "QUE_ISTO"}
SO_PERGUNTA = {"PARA_QUE"}   # "para que serve?" sim; "torcer para que dê certo" não
PRONOMES_PLURAIS = {"VOCES", "ELES", "ELAS", "NOS"}  # com vocês ≠ COM_VOCÊ
OBLIQUOS = {"me": "1S", "te": "2S", "lhe": "3S", "lhes": "3P", "vos": "2P",
            "lo": "3S", "la": "3S", "los": "3P", "las": "3P"}  # vê-la, encontrá-lo
SUJEITOS = {"eu": "1S", "tu": "2S", "você": "2S", "voce": "2S", "ele": "3S", "ela": "3S",
            "nós": "1P", "nos": "1P", "vocês": "2P", "voces": "2P", "eles": "3P", "elas": "3P"}
TEMPO = {"ontem", "hoje", "amanhã", "amanha", "anteontem", "agora"}
# Verbo de ligação: em Libras "o importante é ser feliz" é IMPORTANTE FELIZ. Ficam de fora
# as formas que também são do verbo IR (foi, fui, fosse…): essas o Jev decide pelo contexto.
COPULA = set("""ser sou és somos sois são era eras éramos eram seja sejas sejamos sejam sê
será serão seria seriam sendo sido""".split())
# Abreviação de chat: o dicionário acha que "vc" é palavra, então vem antes de tudo.
ABREVIACOES = {"vc": "você", "vcs": "vocês", "tb": "também", "tbm": "também", "pq": "porque",
               "q": "que", "td": "tudo", "blz": "beleza", "obg": "obrigado", "hj": "hoje",
               "msg": "mensagem", "cmg": "comigo", "ctz": "certeza", "ñ": "não", "mto": "muito",
               # sem sinal próprio, mas com equivalente que tem
               "ti": "você", "contigo": "com você", "cá": "aqui", "donde": "de onde"}
INTENSIFICADORES = {"muito", "muita", "muitos", "muitas", "bastante", "demais"}

INSTRUCOES = {
    "question": "Which Libras sign (gloss) translates the word `{w}` (word #{n} of `frase`) "
                "as it is used in the sentence `frase`?",
    "gloss_conventions": {
        "WORD&SENSE": "the same Portuguese word, restricted to one specific sense",
        "NÃO_WORD": "a sign with the negation built in; use it when the sentence negates it",
        "WORD(+) / WORD(-)": "intensified / attenuated version of the sign",
        "1S_WORD_2S": "directional verb that moves from one person (1S=I, 2S=you, 3S=he/she, "
                      "1P=we, 2P=you all, 3P=they) to another; only when the receiver is a "
                      "person",
        "SOLETRAR": "none of the signs means this word here: spell it letter by letter",
        "WORD": "the plain sign, Portuguese word in uppercase",
    },
}

EMOCOES = {
    "default": "neutral statement, no particular emotion",
    "happy": "joy, satisfaction, good news",
    "sad": "sadness, loss, disappointment",
    "angry": "anger, irritation",
    "disgust": "disgust, repulsion",
    "fear": "fear, worry",
    "surprise": "surprise, astonishment",
    "upset": "annoyance, being bothered or upset",
}
EMOCAO_METODO = {k: f"Apply{k.capitalize()}Emotion" for k in EMOCOES}


def _soletrar(palavra):
    """Token para datilologia. O alfabeto do acervo não tem letras acentuadas."""
    return sem_acento(palavra).upper()


def _tokenizar(texto):
    pont = "[PONTO]"
    t = texto.strip()
    if t.endswith("?"):
        pont = "[INTERROGAÇÃO]"
    elif t.endswith("!"):
        pont = "[EXCLAMAÇÃO]"
    elif not t.endswith("."):
        pont = None
    # palavra com hífen (dá-me) vira duas; números ficam
    brutas = re.findall(r"[\wÀ-ÿ]+", t)
    return brutas, pont


# sinais compostos do acervo, por chave sem acento (montado uma vez)
COMPOSTOS = {}
for _g in S:
    if "_" in _g and not re.match(r"^[123][SP]_", _g):
        COMPOSTOS.setdefault(sem_acento(_g), _g)


def _flexoes(w):
    """O acervo guarda o composto no masculino singular: vinda/vindas/vindos → VINDO."""
    w = sem_acento(w.upper())
    out = [w]
    if w in PRONOMES_PLURAIS:
        return out
    for suf, troca in (("AS", "O"), ("OS", "O"), ("A", "O"), ("ES", ""), ("S", "")):
        if w.endswith(suf) and len(w) > len(suf) + 1:
            out.append(w[: -len(suf)] + troca)
    return out


def _parece_participio(w):
    return bool(re.search(r"(ado|ido|ito|eito|isto|osto|erto)$", w.lower())) and len(w) > 3  # tido, dito


def _compostos(brutas, pergunta=False):
    """Junta n-gramas que são UM sinal no acervo: bom dia → BOM_DIA, tudo bem → TUDO_BEM,
    bem vinda → BEM_VINDO. A forma exata tem prioridade; a flexão é a segunda tentativa."""
    idx = COMPOSTOS
    out, i = [], 0
    while i < len(brutas):
        for n in (4, 3, 2):
            if i + n <= len(brutas):
                janela = brutas[i:i + n]
                chaves = ["_".join(c) for c in product(*(_flexoes(w) for w in janela))]
                achou = next((idx[c] for c in chaves if c in idx), None)
                prox = brutas[i + n] if i + n < len(brutas) else ""
                if achou and (achou in SO_ISOLADAS and n != len(brutas)
                        or achou in SO_PERGUNTA and not pergunta
                        or achou.endswith("_TER") and _parece_participio(prox)):
                    achou = None
                if achou:
                    out.append(("composto", " ".join(janela), achou, i))
                    i += n
                    break
        else:
            out.append(("palavra", brutas[i], None, i))
            i += 1
    return out


def preparar(texto):
    """A parte só de código (sem Jev, sem custo): palavra a palavra, o que vira sinal e o que
    precisa de pergunta. A auditoria (ia/auditoria.py) roda isto em massa de graça."""
    brutas, pont = _tokenizar(texto)
    notas = [f"“{w}” lido como “{ABREVIACOES[w.lower()]}”" for w in brutas if w.lower() in ABREVIACOES]
    # Maiúscula depois de . ! ? … é começo de frase, não nome ("Coloque o casaco. Está frio").
    inicios, inicio, brutas = set(), True, []
    for w in re.findall(r"[\wÀ-ÿ]+|[.!?…]", texto):
        if w in ".!?…":
            inicio = True
            continue
        if inicio:
            inicios.add(len(brutas))
            inicio = False
        brutas += ABREVIACOES.get(w.lower(), w).split()
    siglas = not texto.isupper()  # frase toda em maiúsculas não é sigla
    itens = []          # um por palavra da frase, na ordem
    perguntas = {}
    partes = _compostos(brutas, pergunta=texto.strip().endswith("?"))
    for k, (tipo, palavra, glosa, i) in enumerate(partes):
        p = palavra.lower()
        prox = partes[k + 1][1] if k + 1 < len(partes) else ""
        it = {"palavra": palavra, "pos": k}
        omitir = ("se" if p == "se" else
                  "ter" if p in TER and _parece_participio(prox) else None)
        if tipo == "composto":
            it.update(tok=glosa, fonte="composto")
        elif p in TER and prox.lower() == "tido":  # "ter tido": o 1º é sempre o auxiliar
            it.update(tok=None, fonte="funcional",
                      nota=f"“{palavra}” é auxiliar aqui: o verbo seguinte já carrega o sentido")
        elif p in ESTAR and prox.lower().endswith("ndo"):
            it.update(tok=None, fonte="funcional",
                      nota=f"“{palavra} {prox}”: em Libras o verbo da ação basta, sem o “{palavra}”")
        elif omitir:
            opcoes = ["SE"] if p == "se" else list(candidatos_detalhe(palavra)[0])
            perguntas[f"p{k}"] = _pergunta(palavra, k, opcoes, {"OMITIR": OMITIR[omitir]})
            it.update(tok=None, fonte="jev", pergunta=f"p{k}", candidatos=opcoes + ["OMITIR"],
                      omitir=omitir)
        elif p in VAZIAS or p in COPULA or (p in INTERJEICOES and p.upper() not in S):
            it.update(tok=None, fonte="funcional", nota=f"“{palavra}” não vira sinal em Libras")
        elif p in OBLIQUOS:
            it.update(tok=None, fonte="obliquo", pessoa=OBLIQUOS[p],
                      nota=f"“{palavra}” vai para a direção do verbo, não é um sinal")
        elif p == "não" or p == "nao":
            it.update(tok="NÃO", fonte="negacao")
        elif p.isdigit():
            it.update(tok=p if p in S else _soletrar(p), fonte="numero")
        else:
            sigla = siglas and palavra.isupper() and 2 <= len(palavra) <= 5
            cands, origem = (candidatos_sigla(palavra), "sigla") if sigla else candidatos_detalhe(palavra)
            if sem_acento(p) != p:  # o aluno pôs acento: "está" não é ESTA, "avó" não é AVÔ
                cands = tuple(c for c in cands if sem_acento(base(c)) != sem_acento(p.upper())
                              or base(c) == p.upper()) or cands
            if p.endswith("ndo"):  # gerúndio: a glosa usa o infinitivo (PROCURAR, não PROCURANDO)
                cands = tuple(c for c in cands if sem_acento(c) != sem_acento(p.upper())) or cands
            cap = palavra[:1].isupper() and not sigla
            if cap and i not in inicios:  # Brasil → BRASIL sim; Tomás → TOMAR (lema de "tomas") não
                cands = tuple(c for c in cands if sem_acento(base(c)) == sem_acento(p.upper()))
                origem = origem if cands else "nenhum"
            # Maiúscula no meio da frase só aceita sinal exato: a regra de sufixo leva nome a palavra.
            # No começo da frase a maiúscula não diz nada: o Jev decide, com a opção SOLETRAR.
            achou = cands and (origem in ("exato", "sigla") or origem == "flexao" and not cap)
            # Maiúscula sem sinal no acervo é nome próprio, em QUALQUER posição (Mary virava MAR,
            # Sami virava cartão de digitação). Só um erro "forte" (vcoê) ainda pergunta.
            nome_proprio = cap and not achou and (i not in inicios or not cands or origem == "vizinho")
            if achou or (cands and origem == "flexao") or simplemma.is_known(p, lang="pt"):
                sugestoes = []
            elif nome_proprio:
                sugestoes = corrigir(palavra, so_forte=True)
            else:
                sugestoes = corrigir(palavra)
            if nome_proprio and not sugestoes:
                cands = ()
            if sugestoes:  # o aluno escolhe na tela; chutar aqui é o que fez IA virar IR
                it.update(tok=_soletrar(palavra), fonte="duvida", ok=False, sugestoes=sugestoes,
                          nota=f"“{palavra}” parece erro de digitação")
            elif not cands:
                it.update(tok=_soletrar(palavra), fonte="soletrado", ok=False,
                          nota=f"“{palavra}” não está no acervo: será soletrado"
                               + (" (nome próprio)" if nome_proprio else ""))
            elif len(cands) == 1 and achou:
                it.update(tok=cands[0], fonte="unico")
            else:
                opcoes = list(cands)
                extra = ({"SOLETRAR": {"kind": "fallback", "meaning": "spell the word (a name)"}}
                         if origem in ("vizinho", "sigla") or not achou else {})  # pode não ser nada
                perguntas[f"p{k}"] = _pergunta(palavra, k, opcoes, extra)
                it.update(tok=None, fonte="jev", pergunta=f"p{k}", candidatos=opcoes + list(extra),
                          vizinho=bool(extra))
        itens.append(it)
    return itens, perguntas, notas, pont


# Vizinho de grafia (sem sinal exato): medido em 2 mil frases do Tatoeba, os acertos vêm com
# confiança ≥ 0,8 (camião → CAMINHÃO 0,99) e os erros abaixo (absorto → ABORTO 0,42,
# bronca → BRANCA 0,32). E o vizinho pode ser o ANTÔNIMO: insatisfatória → SATISFATÓRIA.
LIMIAR_VIZINHO = 0.8
PREFIXOS_NEGATIVOS = ("des", "in", "im", "ir", "anti")


def _vizinho_ruim(palavra, a):
    p, g = sem_acento(palavra.upper()), sem_acento(base(a["choice"]))
    antonimo = any(p.startswith(x.upper()) and p[len(x):][:4] == g[:4] for x in PREFIXOS_NEGATIVOS)
    return a["confidence"] < LIMIAR_VIZINHO or antonimo


def _mesma_familia(a, b):
    """VAI/IR, SEUS/SEU, TEMPO/TEMPO&ÉPOCA: a mesma ideia em outra forma. Dividir a confiança
    entre elas não é dúvida de sentido (no Tatoeba eram a maioria dos "incertos"). Já
    NÃO_ESTAR × ESTAR é dúvida de verdade: a negação separa as famílias."""
    if a == b:
        return True
    if a.startswith("NÃO_") != b.startswith("NÃO_") or "SOLETRAR" in (a, b) or "OMITIR" in (a, b):
        return False
    def formas(g):  # lema do dicionário + plural; sem o palpite de infinitivo (casa ≠ casar)
        w = base(g.removeprefix("NÃO_")).lower()
        return {w, simplemma.lemmatize(w, lang="pt"), w[:-1] if w.endswith("s") else w}
    return bool(formas(a) & formas(b))


def _pergunta(palavra, k, opcoes, extra):
    inst = dict(INSTRUCOES)
    inst["question"] = INSTRUCOES["question"].format(w=palavra, n=k + 1)
    crit = {g: (SE if g == "SE" and palavra.lower() == "se" else descrever(g)) for g in opcoes}
    return {"type": "choice", "instructions": inst, "criteria": {**crit, **extra}}


@lru_cache(maxsize=2048)
def glosar(texto):
    t_ini = time.perf_counter()
    itens, perguntas, notas, pont = preparar(texto)

    usage, modelo, emocao = None, None, None
    if perguntas:
        perguntas["emocao"] = {
            "type": "choice",
            "instructions": "Which facial expression should a Libras signer use for `frase`?",
            "criteria": EMOCOES,
        }
        perguntas["intensidade"] = {
            "type": "score",
            "instructions": "How emotionally intense is `frase`?",
            "criteria": ["neutral or mild", "moderate", "strong"],
        }
        r = perguntar({"frase": texto}, perguntas)
        usage, modelo, ans = r["usage"], r["model"], r["answers"]
        for it in itens:
            if it.get("fonte") != "jev":
                continue
            a = ans[it.pop("pergunta")]
            it["confianca"] = a["confidence"]
            it["alternativas"] = sorted(a["probabilities"].items(), key=lambda x: -x[1])[:3]
            it["confianca_familia"] = sum(pr for g, pr in a["probabilities"].items()
                                          if _mesma_familia(g, a["choice"]))
            # SER escolhido para um "foi/fui" ambíguo é ligação ou passiva ("foi preso"): sem sinal
            if a["choice"] == "OMITIR" or a["choice"] == "SER":
                w = it["palavra"]
                it.update(tok=None, nota=f"“{w}” não vira sinal em Libras" if it.get("omitir") != "ter"
                          else f"“{w}” é auxiliar aqui: o verbo seguinte já carrega o sentido")
            elif a["choice"] == "SOLETRAR" or it.get("vizinho") and _vizinho_ruim(it["palavra"], a):
                it.update(tok=_soletrar(it["palavra"]), ok=False,
                          nota=f"“{it['palavra']}” não tem sinal no acervo: será soletrado")
            else:
                it["tok"] = a["choice"]
        e, s = ans["emocao"], ans["intensidade"]
        nivel = max(1, min(3, round(s["score"]) + 1))
        emocao = {"emocao": e["choice"], "confianca": e["confidence"],
                  "metodo": EMOCAO_METODO[e["choice"]] if e["confidence"] >= LIMIAR_INCERTO
                  else "ApplyDefaultEmotion",
                  "intensidade": str(nivel)}

    _absorver(itens)
    seq = _ordenar(itens)
    if pont:
        seq.append({"tok": pont, "palavra": pont, "fonte": "pontuacao"})

    # validação final: nada chega ao player sem existir no acervo ou estar marcado soletrado
    for it in seq:
        it.setdefault("ok", it["tok"] in S)
        if not it["ok"] and "nota" not in it:
            it["nota"] = f"{it['tok']} não existe no acervo: será soletrado"
        it["incerto"] = it.get("confianca_familia", it.get("confianca", 1.0)) < LIMIAR_INCERTO

    custo = usage["input_tokens"] * PRECO_POR_TOKEN if usage else 0.0
    return {
        "motor": "jev" if perguntas else "codigo",
        "modelo": modelo or MODELO,
        "glosa": " ".join(it["tok"] for it in seq),
        "itens": seq,
        "notas": notas,
        "descartadas": [{"palavra": it["palavra"], "nota": it.get("nota", "")}
                        for it in itens if it.get("tok") is None],
        "emocao": emocao,
        "ms": round((time.perf_counter() - t_ini) * 1000),
        "custo_usd": custo,
        "tokens": usage["input_tokens"] if usage else 0,
    }


def _absorver(itens):
    """O sinal escolhido já contém a negação, a intensidade ou as pessoas? Tira o avulso."""
    for it in itens:
        if it.get("tok") == "SER":  # fosse, fora…: sobrou como única opção, mas é ligação
            it.update(tok=None, nota=f"“{it['palavra']}” não vira sinal em Libras")
    for i, it in enumerate(itens):
        tok = it.get("tok") or ""
        anteriores = [x for x in itens[max(0, i - 3):i] if x.get("tok") or x["fonte"] == "obliquo"]
        if tok.startswith("NÃO_"):
            for x in reversed(anteriores):
                if x["fonte"] == "negacao":
                    x["tok"] = None
                    x["nota"] = f"a negação entrou no próprio sinal: {tok}"
                    break
            else:
                # Um "não" vira UM sinal negado. Sem "não" livre antes (já gasto, ou a negação é
                # nunca/ninguém), o negado vira negação dupla: "nunca machucamos" ≠ NUNCA NÃO_MACHUCAR.
                # só o que o Jev escolheu: o composto do acervo (não quer → NÃO_QUER) já
                # contém o próprio "não" — revertê-lo apagava a negação (medido no Tatoeba)
                if it.get("fonte") == "jev" and tok[4:] in S:
                    it["tok"] = tok = tok[4:]
        if tok.endswith("(+)"):
            for x in itens[max(0, i - 2):i + 3]:
                if x is not it and x["palavra"].lower() in INTENSIFICADORES:
                    x["tok"] = None
                    x["nota"] = f"a intensidade entrou no próprio sinal: {tok}"
        m = re.match(r"^([123][SP])_.+_([123][SP])$", tok)
        if m:
            for x in anteriores:
                if x["palavra"].lower() in SUJEITOS or x["fonte"] == "obliquo":
                    x["tok"] = None
                    x["nota"] = f"as pessoas entraram na direção do verbo: {tok}"
            # o objeto depois do verbo também: "eu vi você" → 1S_VER_2S, sem VOCÊ de novo
            for x in itens[i + 1:i + 3]:
                if x.get("tok") and SUJEITOS.get(x["palavra"].lower()) == m.group(2):
                    x["tok"] = None
                    x["nota"] = f"as pessoas entraram na direção do verbo: {tok}"
                    break


def _ordenar(itens):
    """v1: ordem do português (SVO é aceita em Libras), com o tempo à frente."""
    vivos = [it for it in itens if it.get("tok")]
    tempo = [it for it in vivos if it["palavra"].lower() in TEMPO]
    for it in tempo:
        if it is not vivos[0]:
            it["nota"] = "o tempo vem no começo da frase em Libras"
    return tempo + [it for it in vivos if it not in tempo]


if __name__ == "__main__":
    import json
    import sys
    for frase in sys.argv[1:]:
        r = glosar(frase)
        print(f"{frase}\n  → {r['glosa']}   ({r['ms']} ms, US$ {r['custo_usd']:.6f}, "
              f"emoção {r['emocao']})")
        for it in r["itens"]:
            extra = f" conf {it['confianca']:.2f}" if "confianca" in it else ""
            print(f"     {it['tok']:22s} ← {it['palavra']:12s} {it['fonte']}{extra}"
                  f"{'  ⚠ ' + it['nota'] if it.get('nota') else ''}")
        for d in r["descartadas"]:
            print(f"     {'—':22s} ← {d['palavra']:12s} {d['nota']}")
