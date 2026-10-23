# 05 — Glosa: a linguagem intermediária

Entender isto é entender o projeto. A glosa é o "assembly" do VLibras: o formato que o
tradutor produz e o player consome. Quem domina a glosa controla o boneco.

## O que glosa é — e o que não é

Glosa **não é Libras**. É uma **transcrição em palavras do português** da sequência de
sinais, tradicionalmente escrita em maiúsculas. Libras de verdade tem:
- espaço (o sinal muda de lugar conforme quem/o quê),
- expressão facial como gramática,
- classificadores, simultaneidade, direcionalidade,
- ritmo e intensidade.

A glosa captura **a ordem dos sinais** e pouco mais. O VLibras compensa parte do resto com
marcadores — e é exatamente nesses marcadores que mora a nossa oportunidade.

## Gramática de Libras que a glosa reflete

O tradutor aplica transformações reais da língua:

| Regra | Exemplo observado ✅ |
|---|---|
| **Sem artigos** | "o rato roeu a roupa" → `RATO ROER ROUPA` |
| **Sem preposições** de ligação | "do rei de roma" → `REI ROMA` |
| **Verbo no infinitivo** (sem flexão de tempo) | "roeu" → `ROER`; "explicou" → `EXPLICAR` |
| **Sem flexão de gênero** | "a professora" → `PROFESSOR` |
| **Sem flexão de número** | "os alunos" → `ALUNO` |
| **Tempo vem por advérbio** | "vai chover" → `AMANHÃ CHOVER` |
| **Pronome sujeito só quando necessário** | "Eu vou comprar" → `COMPRAR...` (eu elidido) |
| **Negação incorporada** | "não quero" → `NÃO_QUERER` |

Isso é linguisticamente correto e é o que torna o VLibras um bom ponto de partida.

## Os cinco marcadores do formato

### 1. `_` — sinal composto (um sinal só)

`BOM_DIA`, `TUDO_BEM`, `POR_FAVOR`, `NÃO_TER`, `NÃO_QUERER`, `GUARDA_CHUVA`, `CRISE_ECONÔMICA`

Um token com underscore é **um único sinal** no acervo, não dois. `BOM_DIA` ≠ `BOM DIA`.
Existem **3.985** desses.

### 2. `&` — desambiguação de sentido

`COMPRAR&DINHEIRO`, `CONSULTAR&MÉDICO`, `MARCAR&REGISTRAR`, `ABAIXAR&SOM`, `ABAIXAR&VOZ`,
`PODER&POSSIBILIDADE`, `DADO&INFORMAÇÃO`, `MATÉRIA&SUBSTÂNCIA`, `CORRER&PERSEGUIR`

O lado esquerdo é a palavra; o direito é o **sentido escolhido**. "Abaixar o som" e
"abaixar a voz" são sinais diferentes em Libras, e o `&` carrega essa escolha.
Existem **3.251**.

**Isto é um ponto de ataque direto para IA.** O tradutor de regras escolhe o sentido por
heurística lexical; um LLM escolhe pelo contexto da frase inteira. É um ganho barato e
mensurável.

### 3. `1S_VERBO_3P` — verbos direcionais (concordância)

`1P_AJUDAR_3S`, `2S_AJUDAR_1S`, `1S_ENCONTRAR_2S`, `1P_DAR_2P`, `1P_VER_3S`

Em Libras, alguns verbos **se movem no espaço** do sujeito para o objeto: "eu te ajudo" e
"você me ajuda" são o mesmo sinal com direção invertida. A notação é
`{pessoa}{S|P}_VERBO_{pessoa}{S|P}` (S=singular, P=plural).

O acervo tem **367** formas, cobrindo ~25 verbos. A API realmente produz isso: `Você pode me
ajudar a encontrar o banheiro` → `2S_AJUDAR_1S 1S_ENCONTRAR_2S`. Impressionante.

⚠️ **Mas o tradutor inventa formas que não existem.** Ele gerou `1S_IR_2S`; não há bundle.
Ver [04](04-dicionario-e-bundles.md).

### 4. `(+)` e `(-)` — intensidade

`ALEGRE(+)`, `ÁGUA(+)`, `AGRESSIVO(-)`, `ALTO(+)`

Variantes intensificadas/atenuadas do mesmo sinal. **365** no acervo. Em Libras a intensidade
é marcada por amplitude e expressão facial; aqui virou um sinal separado.

Observado: a API **não usou** esses marcadores em nenhuma das frases de teste, mesmo com
"aumentou **muito**" (saiu `AUMENTAR&VALOR`, o "muito" sumiu). **Outro buraco onde a IA entra.**

### 5. `[PONTO]`, `[INTERROGAÇÃO]`, `[EXCLAMAÇÃO]` — pontuação como sinal

Não são caracteres: são **animações de expressão facial** no fim da frase. Confirmado ✅:
`OI TUDO_BEM VOCÊ [INTERROGAÇÃO]` reporta `counter_gloss [4,4]` — a pontuação conta como
um dos 4 sinais.

Em Libras isso é a **marcação não-manual** da interrogativa: sobrancelhas e inclinação de
cabeça. É gramática de verdade, não enfeite. **Nunca remova a pontuação da glosa.**

## Expressão facial via `EmotionBridge`

Além da pontuação, o player aceita emoção contínua ([03](03-player-3d.md)):
`default, happy, sad, angry, disgust, fear, surprise, upset`, intensidade 1–3.

Isso é um canal paralelo à glosa. Um LLM que entenda a frase pode escolher a emoção e
aproximar bem mais o resultado de Libras real. Exemplo:

```js
send('EmotionBridge', 'ApplySadEmotion', '2');
send('PlayerManager', 'playNow', 'EU TRISTE [PONTO]');
```

## Onde o tradutor de regras falha — o mapa da nossa oportunidade

Todos observados ao vivo ✅:

| Falha | Exemplo | Gravidade |
|---|---|---|
| 🔴 **Colapso contextual** | "O rato roeu a roupa do rei de Roma**.**" → `RATO ROMA ROMA` | **Perde metade da frase.** Crítico |
| 🔴 **Sinal válido mas errado** | "eu pus o livro" → `PUS` (a secreção) | indetectável por código |
| 🟠 Perde a negação **se faltar acento** | "Eu nao gosto" → `GOSTAR`; com "não" sai `NÃO_GOSTAR` ✅ | resolvível acentuando |
| 🟠 Lematiza errado verbo no passado | "roeu" → `ROEDOR` (substantivo!) | sinal errado |
| 🟠 Confunde advérbio com verbo | "amanhã" → `AMANHAR` | sinal errado |
| 🟠 Inventa direcional inexistente | `1S_IR_2S` | vira datilologia lenta |
| 🟡 Ignora intensificadores | "aumentou muito" → `AUMENTAR&VALOR` | perde nuance |
| 🟡 Desambiguação por heurística | `COMPRAR&DINHEIRO` para "comprar abacaxi" | às vezes esquisito |
| 🟡 Não usa `(+)/(-)` | nunca apareceu nos testes | acervo subutilizado |

🔴 **E há uma falha pior, descoberta depois** — colapso contextual. Trocar *uma* palavra pode
apagar metade da frase:

```
"o rato roeu a roupa do rei de roma"  →  RATO ROEDOR ROUPA REI ROMA
"o gato roeu a roupa do rei de roma"  →  GATO ROMA&CIDADE ROMA&CIDADE   🔴
```

Determinístico, reproduzido 3×. Detalhes e medição completa em
[11](11-conjugacao-verbal-e-o-teto-das-regras.md).

Repare no padrão: **o vocabulário está certo (97% de cobertura), a gramática é que escorrega.**
Um LLM é exatamente a ferramenta certa para corrigir gramática e escolha de sentido — e o
próprio governo chegou à mesma conclusão ao adicionar `ENABLE_REFINEMENT` com LLM no
text-core v2.5.0 ([01](01-arquitetura-vlibras.md)).

## Gramática formal do token (para o validador)

```
glosa      := token (' ' token)*
token      := pontuacao | direcional | composto | intensidade | palavra
pontuacao  := '[PONTO]' | '[INTERROGAÇÃO]' | '[EXCLAMAÇÃO]'
direcional := pessoa '_' palavra '_' pessoa
pessoa     := ('1'|'2'|'3') ('S'|'P')
composto   := palavra ('_' palavra)+
intensidade:= palavra '(' ('+'|'-') ')'
palavra    := [A-ZÀ-Ü0-9&'-]+          # maiúsculas, acentos preservados
```

⚠️ **Acentos importam.** `RÚSSIA` existe, `RUSSIA` não. `VOCÊ` existe, `VOCE` não.
Nunca normalize removendo acentos antes de consultar os bundles.
