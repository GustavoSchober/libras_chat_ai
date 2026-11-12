# 13 — A camada de IA: Jev (TypeSafe)

Estudo feito em 2026-10-29 para responder: *"dá para usar o Jev como a IA deste projeto?"*

**Resposta curta: dá, e o encaixe é melhor do que o de um LLM — mas só depois de redesenhar
a camada 2, porque o Jev não gera texto.**

Este documento substitui a leitura de <https://docs.typesafe.ai>. Tudo que está aqui veio da
documentação oficial (38 páginas, baixadas e lidas em 2026-10-29) ou de medição local contra
`dados/bundles.json`. O que foi **medido** está marcado ✅; o que é **estimativa** está
marcado 📐; o que **ainda não foi testado** está marcado ⏳.

> ⚠️ **Decisão do projeto (2026-10-29): Jev sozinho, sem LLM.** Um LLM seria usado só para
> prosa sob demanda, e isso ficou para o futuro. Todo o desenho abaixo assume **Jev-only**.
> As consequências dessa decisão estão marcadas 🚩 ao longo do texto.

---

## Parte 1 — O que o Jev é

Jev é o modelo da TypeSafe, o primeiro de uma classe que eles chamam **System One** (do
"pensar rápido" de Kahneman). Ele recebe um `state` (o conteúdo a avaliar) e um conjunto de
`questions`, e devolve **uma resposta típada por pergunta**. Todas as perguntas são avaliadas
**em paralelo e isoladamente** contra o mesmo `state`, numa única requisição.

### As três primitivas — e nada além delas

| Tipo | Pergunta | Devolve | Limite |
|---|---|---|---|
| `Choice` | "qual destas opções?" | `choice`, `probabilities` (soma 1), `confidence` | **1–255 opções** |
| `Score` | "qual nível?" | `score` (pode cair entre níveis), `legend`, `probabilities`, `confidence` | **1–10 níveis** |
| `Noul` | "isto é verdade?" | `noul` — a probabilidade de "sim", 0 a 1 | — (sem `confidence`) |

Existe uma quarta, `Box` (caixa delimitadora em imagem), irrelevante aqui — e que exige o
header `TypeSafe-Danger-Zone-Images: true`.

### 🔴 O fato que redesenha o projeto: o Jev NÃO gera texto

> `jev-1.13` is not trained to generate text. While you can force it to by chaining choices,
> this will not work well and will be very slow. (…) If you really need to generate text…
> there are other models for that.
> — [model-jaggedness/jev-1.13](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md), falha nº 9

Logo, **o esquema JSON proposto no [09](09-projeto-arquitetura.md) é impossível de obter do
Jev**. Nem a string `"FUTEBOL EU NÃO_GOSTAR [PONTO]"`, nem o campo `"nota"`, nem o campo
`"correcoes"`. Nada que seja texto livre.

A saída de um `Choice` é **sempre** uma das opções que você mandou. Não é que alucinação seja
improvável — ela é **impossível por construção**. Isso tem uma consequência boa que a Parte 3
explora.

### A regra de ouro do desenho

> Build a normal software workflow and insert System One only where AI is needed.
> Keep control flow, deterministic rules, and side effects in code.

O código manda. O modelo só emite julgamentos pequenos e típados. **A glosa passa a ser
montada pelo nosso código** a partir das decisões do Jev — o Jev nunca escreve a glosa.

---

## Parte 2 — Modelos, preço, limites

| | Jev 1.14 | Jev 1.13 |
|---|---|---|
| Model ID | `jev-1.14.0` | `jev-1.13.0` |
| Preço (Btok / Mtok) | **US$ 42 / US$ 0,042** | idem |
| Contexto | 64k por requisição / 32k por pergunta | idem |
| Entrada | só texto (string, objeto JSON ou array) | idem |

- **Você paga só a entrada. Tokens de saída são de graça.** Btok = bilhão de tokens.
- Aliases: `jev-latest` → `jev-1.14.0` (padrão dos SDKs), `jev-preview` → hoje aponta para o
  mesmo. 1.14 saiu em 2026-10-14.
- Alias se move sozinho quando sai versão nova. **Se você calibrar thresholds de `confidence`,
  fixe o ID versionado** (`jev-1.14.0`), não o alias. A resposta sempre traz o `model` que
  respondeu, então dá para logar.
- Contexto longo (262k) existe via header `TypeSafe-Danger-Zone-Long-Context: true`, é mais
  lento e **menos preciso**. Não vamos precisar — nossas requisições têm ~1k tokens.
- Endpoint único: `POST https://api.typesafe.ai/v1/systemone`. Chave em
  `console.typesafe.ai/keys`, variável de ambiente `TYPESAFE_API_KEY`.
- Limites de corpo: 32 MiB, UTF-8 sem BOM, no máximo 64 níveis de aninhamento.
- Erros: `429` (rate limit) e `529` (sobrecarga) pedem backoff exponencial — **os SDKs
  oficiais já fazem isso sozinhos**. Rate limit é por organização, em tokens/s e req/s,
  consultável em `console.typesafe.ai/rate-limits`.
- **Jev não é treinado nos nossos dados.** ZDR existe para enterprise.

### Velocidade e custo, medidos pela TypeSafe ✅

Benchmark deles, 15 itens, mesma tarefa de classificação
([cookbook de self-consistency](https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook.md)):

| Condição | Latência | Custo |
|---|---|---|
| **typesafe_choice** | **114 ms** | **US$ 0,000046** |
| gpt-5.4-mini single-pick | 826 ms | US$ 0,000936 |
| claude-haiku-4-5 single-pick | 992 ms | US$ 0,001527 |
| claude-haiku-4-5 default | 3.860 ms | US$ 0,003494 |
| gpt-5.5-reasoning | 12.978 ms | US$ 0,041255 |

**33× a 76× mais barato, 8× a 34× mais rápido** que os LLMs pequenos. A 114 ms, cabe no
caminho de renderização da UI — dá para re-perguntar a cada tecla, se quisermos.

### Custo para o nosso caso 📐

Modelei a requisição real da frase-símbolo (19 perguntas: 5 de sentido, 5 de existência,
1 de ordem, 8 de nota pedagógica) e medi o corpo JSON: **3.570 chars ≈ 1.020 tokens** de
entrada (a ~3,5 chars/token em português).

| | |
|---|---|
| Custo por frase | **US$ 0,000043** |
| Frases por US$ 1 | **~23.300** |
| 1 milhão de frases | **US$ 43** |
| Um aluno, 50 frases/dia, 1 ano | **US$ 0,78** |
| **A suíte de regressão de 40 frases do [11](11-conjugacao-verbal-e-o-teto-das-regras.md)** | **US$ 0,0017** |

A estimativa bateu com o número medido do benchmark deles (US$ 0,000046), o que dá confiança
no modelo de custo.

> 💡 **A última linha é a mais importante deste documento.** Validar se o Jev serve para
> português custa **menos de um centavo**. Não há razão para decidir no escuro.

---

## Parte 3 — Por que isto encaixa melhor que um LLM

Não é consolo por não ter geração de texto. São três encaixes reais.

### 3.1 O [12](12-rag-ou-indice.md) já tinha desenhado a pergunta — faltava o modelo

> ❌ "Qual sentido cabe nesta frase?" — não é RAG, **é prompt**. `PODER` tem 7 sentidos.
> Você joga os 7 no prompt junto da frase e pede para o modelo escolher.

Isso **é** um `Choice`, ao pé da letra. O projeto já tinha concluído que o problema central da
camada 2 era *escolher dentro de um inventário fechado que cabe na memória*. O Jev é um modelo
que **só** sabe fazer isso.

Os 3.251 grupos `&` do acervo ([05](05-glosa-a-linguagem.md)) são 3.251 `Choice` prontos.

### 3.2 `confidence` calibrada é a premissa fundadora do produto

Do README:

> Num app de ensino, um erro confiante é pior que um erro admitido — porque o aluno **copia**.
> Este projeto nasceu com a premissa de que dizer "aqui eu não sei" é funcionalidade, não falha.

O Jev é treinado com RLCD para devolver **probabilidade calibrada**, e toda resposta de
`Choice`/`Score` vem com `confidence` derivada da forma da distribuição (1 = toda a
probabilidade numa opção; 0 = espalhada por igual).

Um LLM devolve prosa confiante. O Jev devolve um número que entra num `if`. **A propriedade
que é o diferencial declarado do modelo é exatamente a premissa fundadora do produto.**

### 3.3 Alucinação de glosa deixa de existir

O [09](09-projeto-arquitetura.md) dizia: *"valide de novo depois — LLM alucina glosa; o
validador é a rede de segurança"*. Com `Choice`, a resposta é garantidamente uma das opções
que mandamos, e nós só mandamos glosas que existem no acervo.

O validador contra `bundles.json` **continua**, porque ele ainda pega a montagem em código
(um direcional `1S_IR_2S` montado por nós, por exemplo). Mas ele deixa de ser rede de
segurança contra o modelo.

---

## Parte 4 — A camada 2, redesenhada para Jev

### Fluxo completo de um turno

```
"O rato roeu a roupa do rei de Roma."
   │
   ├─[1] CÓDIGO  normaliza acentuação e pontuação                      ([11] Classe A)
   ├─[2] CÓDIGO  tokeniza + lematiza (simplemma ou spaCy pt)
   ├─[3] CÓDIGO  levanta candidatos no acervo por token:
   │               acerto exato · grupo & · (+)/(-) · par NÃO_X · vizinhança ortográfica
   ├─[4] CÓDIGO  descarta palavras funcionais (o, a, do, de)           (regra determinística)
   ├─[5] CÓDIGO  gera 3–6 ordenações plausíveis
   ├─[6] CÓDIGO  (opcional) chama o VLibras só para ter uma pista      ← agora é DICA, não motor
   │
   ├─[7] ══════ JEV — UMA requisição, ~19 perguntas, ~114 ms ══════
   │
   ├─[8] CÓDIGO  monta a string da glosa a partir das respostas
   ├─[9] CÓDIGO  valida cada token contra o Set de 24.213              ([04])
   ├─[10] CÓDIGO confidence baixa → vídeo humano / aviso, nunca sinalizar errado
   └─[11] player: EmotionBridge + playNow + counter_gloss              ([03])
```

**O passo [6] é a mudança de maior impacto.** O VLibras deixa de montar a glosa e vira uma
dica dentro do `state` ("a baseline disse isto; as heurísticas acham que ela colapsou").
**O colapso do ponto final simplesmente deixa de existir no nosso caminho**, porque ele é um
defeito do parser deles, e nós paramos de depender do parser deles.

### As perguntas, uma a uma

Todas numa requisição só. O padrão se chama
[**speculative fan-out**](https://docs.typesafe.ai/patterns/fan-out.md): mande tudo que o
código *pode* precisar e ignore o que não usar, porque perguntas rodam em paralelo e custam
poucos tokens cada.

#### a) Sentido do token — `Choice`

```python
"sentido_roeu": Choice(
    instructions="Na frase `frase_pt`, qual destes sinais de Libras corresponde a 'roeu'?",
    criteria={
        "ROER":   {"what": "to gnaw / to chew on something", "pos": "verb"},
        "ROEDOR": {"what": "a rodent, the animal",           "pos": "noun",
                   "not_for": "the action of gnawing"},
    },
)
```

Resolve a **Classe B inteira** do [11](11-conjugacao-verbal-e-o-teto-das-regras.md): `PUS`,
`QUER`, `ROEDOR`, e a escolha de `&`.

🚩 Note as descrições **em inglês** — ver o risco de idioma na Parte 6.

> ⚡ **Token com candidato único não vira pergunta.** `roeu → ['ROER']` e `roupa → ['ROUPA']`
> são decididos em código. Só palavra ambígua gasta token.

#### b) "Algum candidato serve?" — `Noul` companheiro

As probabilidades de um `Choice` **sempre somam 1**: ele vai escolher alguma coisa mesmo
quando nenhuma opção presta. O idioma oficial para isso
([cookbook de busca linha a linha](https://docs.typesafe.ai/cookbooks/semantic_find.md)) é um
`Noul` ao lado, cuja probabilidade **não** depende das opções:

```python
"existe_roeu": Noul(
    instructions="Algum dos sinais listados expressa corretamente 'roeu' nesta frase?",
    criteria=NoulCriteria(true="um dos sinais expressa o sentido",
                          false="nenhum deles expressa"),
)
```

`noul` baixo → palavra órfã → vídeo humano do V-LIBRASIL, ou datilologia **com aviso na tela**.
É a regra "admite em vez de mentir", agora com um número.

A doc recomenda começar em **0,7 para sim e 0,3 para não**, e calibrar depois.

#### c) Ordem dos sinais — `Choice` sobre ordenações geradas em código

```python
"ordem": Choice(
    instructions="Qual destas ordens segue melhor a sintaxe tópico-comentário da Libras?",
    criteria={"a": "RATO ROER ROUPA REI ROMA",
              "b": "ROUPA REI ROMA RATO ROER",
              "c": "RATO ROUPA REI ROMA ROER"},
)
```

⚠️ **Este é o ponto fraco real do desenho.** O Jev escolhe bem entre ordenações que você
propôs; ele **não descobre** uma ordenação que você não gerou. Para frase curta, tranquilo;
para frase longa, o gerador de candidatos de ordem vira a parte difícil do projeto.

**Mitigação:** comece com 3 padrões (como está · tópico à frente · advérbio de tempo à
frente), meça, e só complique com evidência.

#### d) Verbo direcional — duas `Choice` + montagem em código

Conserta `"eu vi o filme" → 1S_VER_2S` ([11](11-conjugacao-verbal-e-o-teto-das-regras.md)):

```python
"sujeito": Choice(instructions="Quem pratica a ação?",  criteria=PESSOAS),  # 1S,2S,3S,1P,2P,3P
"objeto":  Choice(instructions="Quem/o que recebe?",    criteria=PESSOAS),
"obj_pessoa": Noul(instructions="O objeto da ação é uma pessoa, não uma coisa?"),
```

O código monta `1S_VER_2S` **e valida contra as 367 formas reais do acervo**. Se `obj_pessoa`
der baixo (um filme não é pessoa), o código usa `VER` simples. É assim que a forma inventada
`1S_IR_2S` ([05](05-glosa-a-linguagem.md)) deixa de ser produzida.

#### e) Negação incorporada — `Noul`

386 pares `X`/`NÃO_X` no acervo. `Noul` "a frase nega esta ação?" → se sim e o par existe, o
código troca. Pega `"eu não gosto de futebol" → NÃO_GOSTAR` sem depender do acento.

#### f) Intensidade `(+)`/`(-)` — `Choice` de 3 opções

365 variantes no acervo, que a API do governo **nunca usa**. `{AUMENTAR, AUMENTAR(+),
AUMENTAR(-)}` → pega o "muito" de *"aumentou muito"*. Acervo subutilizado virando feature.

#### g) Expressão facial — `Choice` + `Score`

```python
"emocao":      Choice(criteria={"default":None,"happy":None,"sad":None,"angry":None,
                                "disgust":None,"fear":None,"surprise":None,"upset":None}),
"intensidade": Score(instructions="Qual a intensidade emocional da frase?",
                     criteria=["neutra", "moderada", "forte"]),   # → 1,2,3 no EmotionBridge
```

Casa exatamente com o contrato do `EmotionBridge` ([03](03-player-3d.md)).

#### h) 🚩 Notas pedagógicas — catálogo humano + `Noul` por nota

**Aqui está a maior consequência do Jev-only.** O Jev não escreve a explicação. Então ela vira
um **catálogo de notas escritas por um humano**, e o Jev só decide **quais se aplicam**:

```python
for i, nota in enumerate(CATALOGO):
    questions[f"nota_{i}"] = Noul(
        instructions=f"Esta regra explica uma diferença entre `frase_pt` e a glosa: {nota.regra}")
```

O catálogo nasce pronto: **a tabela "Gramática de Libras que a glosa reflete" do
[05](05-glosa-a-linguagem.md) já é o seed**, e todas as suas linhas foram verificadas ✅.

| # | Regra | Nota ao aluno (exemplo) |
|---|---|---|
| 1 | sem artigos | "Libras não tem artigos — *o*, *a*, *um* não viram sinal." |
| 2 | sem preposições de ligação | "*do rei de Roma* vira `REI ROMA`: a relação vem do espaço, não de palavras." |
| 3 | verbo no infinitivo | "O verbo não flexiona: *roeu* vira `ROER`." |
| 4 | tempo por advérbio | "O tempo vem no começo da frase, por advérbio: `AMANHÃ CHOVER`." |
| 5 | sem flexão de gênero | "*a professora* vira `PROFESSOR`." |
| 6 | sem flexão de número | "*os alunos* vira `ALUNO`." |
| 7 | pronome sujeito elidido | "O *eu* some quando já está claro quem fala." |
| 8 | negação incorporada | "A negação entra no próprio sinal: `NÃO_GOSTAR`, com balanço de cabeça." |
| 9 | tópico-comentário | "Libras costuma marcar o assunto antes do comentário." |
| 10 | pontuação é marcação não-manual | "`[INTERROGAÇÃO]` não é um ponto: são sobrancelhas e inclinação de cabeça." |
| 11 | sinal composto | "`BOM_DIA` é **um** sinal, não dois." |
| 12 | desambiguação de sentido | "`ABAIXAR&SOM` e `ABAIXAR&VOZ` são sinais diferentes." |
| 13 | verbo direcional | "O sinal se move do sujeito ao objeto: *eu te ajudo* e *você me ajuda* são o mesmo sinal invertido." |
| 14 | intensidade | "A intensidade é amplitude e rosto: `GRANDE(+)`." |

**Isto é um upgrade, não um remendo.** Num app de ensino, você nunca vai ter um modelo
inventando uma regra gramatical de Libras na frente de um aluno. Cada nota é escrita uma vez,
revisada idealmente por quem ensina Libras, e versionada no Git — o que conversa diretamente
com a "Honestidade necessária" do README (*validar com pessoas surdas não é etapa opcional*).

**Slots preenchidos em código** dão o resto da personalização:
`"O verbo {roer} foi para o infinitivo"` — o `{roer}` sai do nosso tokenizador, não do modelo.

### O que o código faz, e o Jev nunca

| Trabalho | Quem |
|---|---|
| Normalizar acento e pontuação | código |
| Lematizar, tokenizar | código (`simplemma` / spaCy) |
| Levantar candidatos no acervo | código (trie + `Set` + grupos `&`) |
| Descartar palavras funcionais | código |
| Gerar ordenações candidatas | código |
| **Escolher sentido, ordem, pessoa, emoção, notas** | **Jev** |
| **Montar a string da glosa** | **código** |
| Validar contra `bundles.json` | código |
| Diff entre duas glosas ("mudaram 2 sinais") | código |
| Decidir agir / avisar / mostrar humano | código, lendo `confidence` |

---

## Parte 5 — O recall de candidatos (medido ✅)

Se a glosa certa não estiver na lista, o Jev não tem como escolhê-la. **O gerador de
candidatos passa a ser o teto do sistema.** Testei contra o `bundles.json` real, nos casos
que o [11](11-conjugacao-verbal-e-o-teto-das-regras.md) mediu como insolúveis sem semântica:

```
palavra     n   alvo presente?  candidatos
roeu        1   SIM             ['ROER']
pus        12   SIM             ['POR','PÔR&ANOTAR','PÔR&COLOCAR','PÔR&ENFEITAR','PÔR&FIXAR',
                                 'PÔR&FOGO','PÔR&OVO','PÔR&ROUPA','PÔR&SOL','PORO','PIOR','OPOR']
quis        4   SIM             ['QUERER','NÃO_QUERER','REQUERER','QUEREREM']
vi          2   SIM             ['VER','NÃO_VER']
pediu       5   SIM             ['PEDIR','PEDIR&DEMISSÃO','NÃO_PEDIR','IMPEDIR','EXPEDIR']
mordeu      4   SIM             ['MORDER','MORDER&LÍNGUA','NÃO_MORDER','MORRER']
gosto      12   SIM             ['GOSTAR','GOSTAR(-)','GOSTAR(+)','NÃO_GOSTAR','GOSTARIA',
                                 'TOSTAR','POSTAR','GASTAR','GOSTO','GOSTOU','AGOSTO','GOSTOSO']
roma        4   SIM             ['ROMA','ROMÃ','ROMA&CIDADE','AROMA']
aumentou   12   SIM             ['AUMENTAR','AUMENTAR&VOLUME_SOM',…,'NÃO_AUMENTAR']

recall: 12/12 — conjuntos de 1 a 12 opções (o limite do Choice é 255)
```

**A linha do `pus` é a prova do conceito.** `PÔR&COLOCAR` está no conjunto. Esse é o erro que
o [11](11-conjugacao-verbal-e-o-teto-das-regras.md) classificou como "o pior defeito possível"
— o avatar executando com perfeição o sinal de *pus, a secreção*, sem nenhum sinal técnico de
erro. Escolher `PÔR&COLOCAR` em vez de `POR` (preposição) e `PÔR&SOL` é **desambiguação
lexical por contexto**: a tarefa em que um System One model é mais forte, não menos.

### A receita do gerador

```python
def candidatos(palavra, k=12):
    lemas = lematizar(palavra)              # simplemma / spaCy — AINDA NÃO INSTALADO
    out = []
    for lema in lemas:
        n = sem_acento(lema.upper())
        out += NORM.get(n, [])                                   # 1. exato (recupera o acento)
        out += [g for g in B                                     # 2. grupo &, (+)/(-)
                if sem_acento(g).split('&')[0].rstrip('(+-)') == n]
        out += NORM.get('NÃO_' + n, [])                          # 3. par de negação
        for m in difflib.get_close_matches(n, KEYS, n=6, cutoff=0.82):
            out += NORM[m]                                       # 4. vizinhança ortográfica
    return dedup(out)[:k]
```

⚠️ **Prefixo puro não serve:** `RO*` devolve 108 candidatos (`ROBÔ`, `ROÇA`, `ROCHA`…). É
preciso lematizar primeiro. Nenhum lematizador está instalado hoje — nem `simplemma`, nem
`spaCy`, nem `nltk`, nem `rapidfuzz` ✅ (verificado).

⚠️ **O passo 4 é um stand-in.** A vizinhança ortográfica pega `MORDER`/`MORRER`, mas não pega
*automóvel* → `CARRO`. Para isso vale o passo 6 do [12](12-rag-ou-indice.md): embeddings das
24.213 glosas, calculados **uma vez, offline, por centavos** — sem LLM em runtime, o que
preserva a decisão Jev-only. O Jev então confirma ou rejeita o vizinho proposto.

---

## Parte 6 — Dificuldades antecipadas, com solução definida

A TypeSafe publica uma página de defeitos conhecidos
([jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)) — raro e honesto. Nove
falhas; estas são as que nos tocam.

### ✅ 1. Português — era o único risco de verdade; **resolvido em 2026-11-09** (ver Parte 10)

> Jev's primary training language is English; other languages, including CJK scripts, are
> accepted but currently **have lower accuracy**.

Não há número publicado para PT. Três coisas atenuam:

1. O alerta nomeia **CJK** como o caso difícil. Português é latino e de alto recurso.
2. **Nome da opção e descrição da opção são campos separados.** Mantemos `PÔR&COLOCAR` como
   nome (é o token que o bundle exige) e escrevemos a descrição **em inglês**:
   `{"what": "to place/put an object somewhere"}`. O ancoramento semântico acontece em
   inglês; o token sai em português. **Esta é a mitigação mais forte que temos.**
3. O `state` fica curto e estruturado, que é onde o modelo sofre menos.

**Como resolver antes de gastar:** o [11](11-conjugacao-verbal-e-o-teto-das-regras.md) já
deixou pronta a suíte de **40 frases de verbos, com baseline medida de 82%**. Rodar as 40
contra o Jev custa **US$ 0,0017**. Se a precisão ficar bem acima de 82%, está decidido. Se
ficar perto ou abaixo, **teste de novo com `criteria` em inglês antes de concluir qualquer
coisa** — é exatamente a variável que a mitigação 2 controla.

### 2. Leitura literal (falha nº 1)

> `jev-1.13` answers the question you wrote, not the one you meant.

→ `instructions` cirúrgicas. Casos-limite dentro do `criteria`, não na cabeça. Use `criteria`
estruturado (`what` / `not_for` / `examples`) para separar vizinhos perigosos — é o remédio
oficial para opções que o modelo confunde:

```python
"GOSTO": {"what": "taste, flavour (noun)", "not_for": "the verb 'to like'",
          "examples": ["o gosto do café"]},
"GOSTAR": {"what": "to like (verb)", "not_for": "the noun 'taste'"},
```

> "When you look at a wrong answer and find yourself explaining what you really meant, that
> explanation is the missing half of the instruction."

### 3. Viés de ordem das opções (falha nº 8)

> `jev-1.13` leans toward the option that comes first.

→ Embaralhe a ordem dos candidatos e inclua no teste de regressão **a mesma frase com a lista
invertida**. Barato, e pega o viés.

### 4. Nada de contar, nada de aritmética (falha nº 2)

> Jev is not a calculator. (…) `jev-1.13` does not count reliably.

→ O "mudaram 2 sinais, pratique só esses" (nível 2 do [09](09-projeto-arquitetura.md)) é
`diff` de listas em Python. **Nunca** pergunte ao Jev quantos sinais mudaram.
Mesmo vale para `Score`: serve para comparar com um limiar, **não** para reconstruir um número
por interpolação entre níveis.

### 5. Estado grande com detalhe irrelevante (falha nº 5)

> Jev suffers from context rot, so unrelated material in the `state` costs you accuracy.

→ `state` enxuto: frase, glosa-base (como dica), alertas das heurísticas. **Não** mande o
acervo inteiro, nem o histórico do aluno, nem o catálogo de notas dentro do `state`.

### 6. Indireção (falha nº 4)

→ Aponte o campo pelo caminho com crases: ``"Na frase `frase_pt`, …"``. É sintaxe suportada
e remove ambiguidade.

### 7. Instruções e critérios contraditórios (falha nº 7)

→ Um `Noul` em que `true` significa "não" performa pior. Mantenha `instructions` e `criteria`
puxando para o mesmo lado.

### 8. Conteúdo adversarial (falha nº 6)

> State is data, and `jev-1.13` does not treat it as hostile by default.

→ O `state` carrega texto digitado pelo usuário. Baixo risco num tutor de Libras, mas vale
lembrar que um aluno pode digitar instruções no campo de frase.

### 9. A página de jaggedness é da 1.13 ⏳

Revisada em 2026-10-02; o modelo atual é o 1.14. **Alguns desses defeitos podem já estar
corrigidos.** Vale reler quando saírem as notas da 1.14.

### 10. Contexto — não é problema

64k por requisição / 32k por pergunta. Vamos usar ~1k. Folga de 60×.

---

## Parte 7 — O que o Jev não faz

| Precisa | Jev dá? | Saída no desenho Jev-only |
|---|---|---|
| Desambiguar sentido pelo contexto | ✅ ideal | `Choice` sobre candidatos |
| Consertar Classe B (`PUS`, `QUER`, `ROEDOR`) | ✅ | `Choice` |
| Pessoa do verbo direcional (`1S_VER_2S`) | ✅ | 2 `Choice` + `Noul`, montagem em código |
| Detectar negação perdida | ✅ | `Noul` sobre os 386 pares |
| Escolher `(+)`/`(-)` | ✅ | `Choice` de 3 |
| Escolher expressão facial | ✅ ideal | `Choice` + `Score` |
| Dizer "não sei" de forma calibrada | ✅ **melhor que LLM** | `confidence` + `Noul` companheiro |
| Montar a string da glosa | ❌ | **o código monta** a partir dos `Choice` |
| Reordenar livremente | ⚠️ parcial | código propõe 3–6, Jev escolhe |
| Escrever explicação pedagógica | ❌ | 🚩 catálogo de ~40–80 notas humanas + `Noul` |
| Sinal para palavra fora do acervo | ❌ | embeddings offline propõem, Jev confirma |
| Prosa livre ("me explique melhor") | ❌ | 🚩 **fora de escopo** — LLM, no futuro |

🚩 **Consequência da decisão Jev-only:** as duas últimas linhas. O botão "me explique melhor"
com texto livre não existe na v1. Em troca, o custo por turno fica em US$ 0,000043 e o
conteúdo pedagógico é 100% auditável. Se um dia entrar um LLM, ele entra **sob demanda e
raro** — arquitetura de custo bonita, e nada do que está desenhado aqui precisa mudar.

---

## Parte 8 — Ordem de construção

| # | Passo | Depende da chave? | Custo |
|---|---|---|---|
| 1 | Chave em `.env`, `.env` no `.gitignore`, apagar `doc_ai/importante.md` | — | 0 |
| 2 | ✅ **Rodar as 40 frases contra o Jev** — 100% com descrição estruturada (Parte 10) | sim | US$ 0,0033 |
| 2b | ~~Se ficar ≤ 82%: repetir com `criteria` em inglês~~ — não foi preciso | — | — |
| 3 | 🟡 Gerador de candidatos — v1 em `ia/candidatos.py` (simplemma + redução de infinitivo), recall 40/40 | **não** | 0 |
| 4 | Catálogo de notas pedagógicas (as 14 do [05](05-glosa-a-linguagem.md) como seed) | **não** | 0 |
| 5 | ✅ Backend fino: `POST /api/glosa` em `ia/servidor.py` → `ia/glosa.py` → validação; POC usa, com o tradutor do governo de reserva (2026-11-09) | sim | ~US$ 0,00004/frase |
| 6 | 🟡 Teste de aceitação — sai `RATO ROER ROUPA REI ROMA&CIDADE [PONTO]`; só `ROMA` × `ROMA&CIDADE` ficou incerto (conf 0,28) e a tela avisa | sim | ~0 |
| 7 | Embeddings offline do acervo (palavra órfã → sinal próximo) | não | centavos, uma vez |

**Os passos 3 e 4 não dependem da chave e são o teto do sistema.** Dá para construir tudo
isso antes de contratar o Jev.

### Teste de aceitação (inalterado desde o [11](11-conjugacao-verbal-e-o-teto-das-regras.md))

```
entrada:  "O rato roeu a roupa do rei de Roma."
hoje:      RATO ROMA&CIDADE ROMA&CIDADE [PONTO]     🔴
meta:      RATO ROER ROUPA REI ROMA [PONTO]         ✅
```

### Antes de escrever o código

A TypeSafe publica uma skill oficial para agentes de código, com as formas de requisição e
resposta e os padrões arquiteturais:

```bash
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai
```

Vale instalar **antes** de pedir o backend — a doc avisa que agentes caem no hábito de uma
pergunta por requisição, que é o anti-padrão central aqui.

---

## Parte 9 — O que explicitamente não fazer

- ❌ **Não peça texto ao Jev.** Nem a glosa, nem a explicação, nem uma justificativa. Se a
  resposta precisa ser escrita, ela vem de catálogo ou de código.
- ❌ **Não mande o acervo inteiro no `state`.** 24.213 glosas não cabem, e mesmo que
  coubessem, o context rot cobraria a conta. Mande 1–12 candidatos por token.
- ❌ **Não faça uma requisição por pergunta.** O
  [cookbook de perguntas paralelas](https://docs.typesafe.ai/cookbooks/parallel_questions.md)
  mediu 12,2× mais barato e 10× mais rápido batendo 13 perguntas numa chamada só, **sem
  mudança nas respostas**.
- ❌ **Não normalize acentos** antes de consultar bundles. `RÚSSIA` existe, `RUSSIA` não.
  (Repetido do [09](09-projeto-arquitetura.md) de propósito.)
- ❌ **Não confie no alias `jev-latest`** depois de calibrar thresholds. Fixe `jev-1.14.0`.
- ❌ **Não use `Score` para reconstruir número.** Só para comparar com limiar.
- ❌ **Não deixe o `Choice` decidir sozinho se o candidato presta.** Sempre o `Noul`
  companheiro.
- ❌ **Não comece pela IA.** Os passos 1–4 do [12](12-rag-ou-indice.md) continuam valendo
  integralmente e não precisam de chave nenhuma.

---

## Parte 10 — Resultado: as 40 frases contra o Jev (2026-11-09) ✅

Código: `ia/regressao_verbos.py` (suíte) · `ia/candidatos.py` (gerador) · `ia/jev.py` (cliente).
Bruto de cada execução em `ia/resultados/`. Modelo fixado: `jev-1.14.0`.

Cada frase = **uma** requisição com 5 perguntas sobre o mesmo `state`: a mesma `Choice` em 4
variantes (só o nome da glosa × descrição estruturada, cada uma em ordem normal e invertida)
e o `Noul` "algum candidato serve?".

| Variante | Acertos |
|---|---|
| só o nome da glosa | 37/40 · 92,5% |
| só o nome, ordem invertida | 38/40 · 95,0% |
| **descrição estruturada** | **40/40 · 100%** |
| **descrição estruturada, ordem invertida** | **40/40 · 100%** |
| baseline VLibras ([11](11-conjugacao-verbal-e-o-teto-das-regras.md), conjunto **não pareado**) | 33/40 · 82,5% |

Recall do gerador: **40/40**. Custo real: **US$ 0,0033** (78.799 tokens — ~2k por requisição,
o dobro da estimativa da Parte 2, porque cada requisição levou 4 cópias da mesma pergunta e as
convenções de glosa nas `instructions`). Latência: mediana **245 ms**, máx 548 ms.

**O que isso decide:**

1. **Português não é obstáculo.** A Classe B inteira caiu: `pus → PÔR&COLOCAR`, `quis →
   QUERER`, `vi → VER` (e `te vi → 1S_VER_2S`, `você me pediu → 2S_PEDIR_1S` — o direcional
   certo quando *é* direcional), `não gosto → NÃO_GOSTAR`, `o gosto do café → GOSTO`
   (substantivo), `água correu → CORRER&LÍQUIDO`, `gosto muito → GOSTAR(+)`.
2. **A descrição estruturada é obrigatória, não opcional.** Sem ela o Jev erra exatamente o
   caso-símbolo (`pus → PUS`, a secreção) e pega um direcional à toa (`eu vi o filme →
   1S_VER_3S`). Ela é gerada **pela sintaxe da glosa** (`&`, `NÃO_`, `(+)`, `1S_X_2S`), com
   chaves em inglês e valores em português — sem dicionário, sem LLM. Ver `descrever()`.
3. **`confidence` separa acerto de erro.** Na variante só-nome: média **0,84** nos acertos e
   **0,37** nos erros. O limiar "abaixo de ~0,5 → não sinaliza com confiança" é viável.
4. **Viés de ordem: pequeno.** A ordem invertida mudou a resposta em 2 casos, só na variante
   só-nome, e ambos com confidence < 0,55. Na estruturada, zero.

**Limites honestos desta medição:**

- As 40 frases e os conjuntos de respostas aceitas foram escritos pela mesma sessão que
  escreveu `descrever()` — risco de sobreajuste. Próxima suíte deve vir de frases que ninguém
  do projeto escreveu (ex.: legendas do V-LIBRASIL, [06](06-dataset-vlibrasil.md)).
- Algumas respostas aceitas são lenientes (`COMPRAR` / `COMPRAR&DINHEIRO` / `COMPRAR&ADQUIRIR`
  valem igual). Quem ensina Libras deveria dizer se são mesmo intercambiáveis.
- O `Noul` "existe" **não foi testado de verdade**: todas as 40 frases tinham o alvo entre os
  candidatos, então não houve caso negativo. Os valores (0,40 a 0,93) mostram que ele é
  ruidoso; calibrá-lo exige frases com palavra órfã.
- Testa só a escolha do sinal por palavra. Ordem dos sinais, descarte de palavras funcionais
  e a frase inteira (`O rato roeu a roupa do rei de Roma.`) ainda não passaram pelo Jev.

## Fontes

Documentação oficial, baixada e lida em 2026-10-29:

| Página | URL |
|---|---|
| Índice de toda a doc | <https://docs.typesafe.ai/llms.txt> |
| Introdução / System One | <https://docs.typesafe.ai/concepts/system-one.md> |
| Primitivas (visão geral) | <https://docs.typesafe.ai/primitives.md> |
| Choice · Score · Noul | `/primitives/choice.md` · `/score.md` · `/noul.md` |
| Estrutura em instructions/criteria | <https://docs.typesafe.ai/primitives/advanced.md> |
| State | <https://docs.typesafe.ai/concepts/state.md> |
| Confidence (fórmulas exatas) | <https://docs.typesafe.ai/confidence.md> |
| Como construir | <https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md> |
| **Defeitos conhecidos** | <https://docs.typesafe.ai/model-jaggedness/jev-1.13.md> |
| Modelos, preço, contexto | <https://docs.typesafe.ai/models.md> |
| API e erros | `/api/system-one.md` · `/api/errors.md` |
| Speculative fan-out | <https://docs.typesafe.ai/patterns/fan-out.md> |
| Busca linha a linha (Choice + Noul) | <https://docs.typesafe.ai/cookbooks/semantic_find.md> |
| Perguntas paralelas (12,2× mais barato) | <https://docs.typesafe.ai/cookbooks/parallel_questions.md> |
| Benchmark de latência e custo | <https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook.md> |
| Function calling (closed sets) | <https://docs.typesafe.ai/cookbooks/function_calling.md> |
| Skill para agentes de código | <https://docs.typesafe.ai/agent-skill.md> |
| Console (chaves, rate limits) | <https://console.typesafe.ai/keys> |

Medições locais desta apuração: recall de candidatos contra `dados/bundles.json` (12/12),
modelagem de tokens da requisição real (~1.020 tokens), ausência de lematizador no ambiente.

---

## O resumo de uma linha

> **O Jev não gera texto — então o código monta a glosa a partir de decisões típadas, e as
> explicações vêm de um catálogo humano. Isso custa US$ 0,000043 por frase, responde em
> 114 ms, torna alucinação de glosa impossível, e entrega `confidence` calibrada, que é
> exatamente a premissa fundadora do produto. O risco do português foi eliminado em 2026-11-09:
> 40/40 com descrição estruturada, por US$ 0,0033 (Parte 10).**
