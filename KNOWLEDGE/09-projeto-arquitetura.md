# 09 — LIBRAS AI CHAT: arquitetura proposta

Tudo que vem antes é o terreno. Isto é o que construir em cima.

> ⚠️ **Atualizado em 2026-10-29.** A camada 2 foi redesenhada: o modelo escolhido é o **Jev
> (TypeSafe)**, que **não gera texto**. Onde este documento dizia "o LLM devolve um JSON",
> leia "o Jev devolve decisões típadas e **o nosso código monta** a glosa". O desenho completo,
> com preço, limites e defeitos conhecidos, está em
> [13](13-camada-de-ia-jev.md) — e **ele tem precedência sobre este arquivo** onde os dois
> divergirem.

## A ideia, reformulada com precisão

> "um chat de IA, mas em vez de eu falar com o chat, ele vai me ensinar a falar"

Não é um tradutor. **É um tutor.** A diferença operacional:

| Tradutor (o que o VLibras já é) | Tutor (o que vamos fazer) |
|---|---|
| texto entra, sinal sai | texto entra, **lição** sai |
| otimiza fidelidade | otimiza **aprendizado** |
| frase inteira de uma vez | sinal a sinal, com explicação |
| não sabe o que você já aprendeu | acompanha e adapta |
| silencia nos erros | **diz** "isto o avatar vai soletrar, e aqui está uma pessoa fazendo" |

Se a gente só encadear `translate` + `playNow`, construímos um VLibras com UI diferente.
O valor está nas camadas que ele não tem.

## As três camadas

```
┌─ CAMADA 3 — PEDAGOGIA  (o que é nosso de verdade)
│   decompõe a frase em lição, explica por que a glosa é assim,
│   mostra o vídeo humano, acompanha progresso, propõe exercício
│
├─ CAMADA 2 — IA DE GLOSA  (onde o Jev entra)
│   escolhe o sentido pelo contexto, a pessoa do verbo direcional, a ordem,
│   a intensidade e a emoção facial — tudo como decisão típada;
│   o CÓDIGO monta a glosa e VALIDA contra os bundles
│
└─ CAMADA 1 — MOTOR  (resolvido, é só plumbing)
    tradutor VLibras + player Unity + lista de bundles + dataset HF
```

**A camada 1 já está provada e documentada.** Comece por ela porque é rápida, e passe o
tempo de verdade nas camadas 2 e 3.

## Fluxo completo de um turno

```
  usuário digita: "Eu não gosto de futebol"
          │
          ├─[1]─► CÓDIGO: normaliza acento/pontuação, tokeniza, lematiza
          │       levanta candidatos no acervo e descarta palavras funcionais
          │       gera 3–6 ordenações plausíveis
          │
          ├─[2]─► POST /translate ──► "GOSTAR FUTEBOL"       🔴 negação perdida
          │       (vira DICA dentro do state, não a glosa final)
          │
          ├─[3]─► JEV — uma requisição, N perguntas, ~114 ms
          │       Choice sentido_gostar {GOSTAR, GOSTAR(+), GOSTAR(-), GOSTO}  → GOSTAR
          │       Noul   nega_gostar    "a frase nega esta ação?"              → 0.97
          │       Choice ordem          {3 ordenações candidatas}              → tópico à frente
          │       Choice emocao         {default, happy, sad, …}               → default
          │       Score  intensidade    [neutra, moderada, forte]              → 1.8
          │       Noul   nota_0..nota_N "esta regra explica a diferença?"      → 8 e 9 altas
          │
          ├─[4]─► CÓDIGO monta a glosa a partir das respostas:
          │       nega_gostar > 0.7 e o par NÃO_GOSTAR existe → troca
          │       → "FUTEBOL EU NÃO_GOSTAR [PONTO]"
          │
          ├─[5]─► VALIDADOR: cada token existe em bundles.json?
          │       NÃO_GOSTAR ✅  FUTEBOL ✅  EU ✅  [PONTO] ✅
          │       (se algum falhar → degrada com aviso; o Jev não inventa token,
          │        mas a MONTAGEM em código pode errar — ex.: 1S_IR_2S)
          │
          ├─[6]─► send('EmotionBridge','ApplyDefaultEmotion','2')
          │       send('PlayerManager','playNow','FUTEBOL EU NÃO_GOSTAR [PONTO]')
          │
          └─[7]─► counter_gloss [n,total] → destaca o token n na UI
                  + as notas 8 e 9 do catálogo aparecem como explicação
                  + se o sinal estiver no V-LIBRASIL, oferece o vídeo humano
```

O passo **[5] não é opcional.** Sem ele, o avatar soletra lixo em silêncio ([04](04-dicionario-e-bundles.md)).

Repare no passo **[2]**: o tradutor do governo deixou de montar a glosa. Ele virou uma pista
dentro do `state`. É por isso que o colapso do ponto final
([11](11-conjugacao-verbal-e-o-teto-das-regras.md)) **deixa de existir no nosso caminho** —
ele é um defeito do parser deles, e nós paramos de depender do parser deles.

## Por que a IA pertence à camada 2

Não é "IA porque está na moda". Cada erro medido do tradutor é exatamente o tipo de
problema que semântica resolve e um sistema de regras não — e cada um deles vira **uma
primitiva do Jev**, não um prompt:

| Erro medido ✅ | Por que regras falham | Como o Jev resolve |
|---|---|---|
| "não gosto" → `GOSTAR` | regra de negação não cobriu o padrão | `Noul` "a frase nega esta ação?" sobre os 386 pares `X`/`NÃO_X` |
| "roeu" → `ROEDOR` | lematizador escolheu o substantivo | `Choice` {ROER, ROEDOR} com `not_for` em cada opção |
| "amanhã" → `AMANHAR` | ambiguidade advérbio/verbo | `Choice` {AMANHÃ, AMANHAR} |
| `COMPRAR&DINHEIRO` para "comprar abacaxi" | escolha lexical isolada | `Choice` sobre o grupo `&` inteiro, vendo a frase |
| "aumentou muito" perde o "muito" | não usa `(+)` | `Choice` {AUMENTAR, AUMENTAR(+), AUMENTAR(-)} |
| `1S_IR_2S` inexistente | não valida contra acervo | 2 `Choice` de pessoa + **o código monta e valida** contra as 367 formas reais |
| "eu pus o livro" → `PUS` | sem conceito de sentido | `Choice` {POR, PÔR&COLOCAR, PÔR&SOL, …} — medido ✅, o alvo está nos candidatos |

E a prova de que a direção está certa: **o próprio VLibras adicionou refinamento por LLM**
em 2026 (`ENABLE_REFINEMENT`, `LLM_PROVIDER`, `LLM_MODEL`). Estamos indo ao mesmo lugar,
por um caminho mais barato e mais auditável.

### Como dar o acervo ao Jev

24.213 glosas não cabem numa requisição. A estratégia que funciona (e **é a mesma de antes** —
esta parte do desenho original sobreviveu intacta):

1. traduza com a API → glosa base, **como dica no `state`**, não como resultado
2. para cada token, levante **candidatos** dos bundles (lema → exato, grupo `&`, `(+)/(-)`,
   par `NÃO_`, vizinhança) — medido: **1 a 12 por palavra**, recall 12/12 ✅
3. mande ao Jev **só esses candidatos**, como `criteria` de um `Choice`
4. não é preciso "restringir a saída": o `Choice` **é** restrito por construção
5. valide a **montagem** depois — o Jev não alucina glosa, mas o nosso código pode errar ao
   montar um direcional

⚠️ **Prefixo puro não serve.** `RO*` devolve 108 candidatos (`ROBÔ`, `ROÇA`, `ROCHA`…).
É preciso lematizar antes. Receita completa em [13](13-camada-de-ia-jev.md), Parte 5.

## O que o Jev devolve — e o que o código monta

O Jev **não devolve JSON de texto livre**. Ele devolve uma resposta típada por pergunta:

```json
{
  "model": "jev-1.14.0",
  "answers": {
    "sentido_gostar": { "type": "choice", "choice": "GOSTAR", "confidence": 0.91,
                        "probabilities": {"GOSTAR":0.94,"GOSTO":0.04,"GOSTAR(+)":0.02} },
    "nega_gostar":    { "type": "noul", "noul": 0.97 },
    "ordem":          { "type": "choice", "choice": "b", "confidence": 0.63, "…": "…" },
    "emocao":         { "type": "choice", "choice": "default", "confidence": 0.8 },
    "intensidade":    { "type": "score", "score": 1.8, "legend": {"0":"neutra","1":"moderada","2":"forte"} },
    "nota_8":         { "type": "noul", "noul": 0.95 }
  },
  "usage": { "input_tokens": 1020, "output_tokens": 212 }
}
```

E **o nosso código** transforma isso no objeto que a camada 3 consome:

```json
{
  "glosa": "FUTEBOL EU NÃO_GOSTAR [PONTO]",
  "emocao": { "nome": "default", "intensidade": 2 },
  "tokens": [
    { "glosa": "FUTEBOL", "pt": "futebol", "confianca": 0.98,
      "notas": [9],
      "tem_bundle": true, "video_humano": "https://huggingface.co/.../Futebol_Articulador1.mp4" }
  ],
  "notas_aplicadas": [8, 9],
  "alertas": ["o tradutor base perdeu a negação de 'não gosto'"],
  "confianca_minima": 0.63
}
```

O contrato com a camada 3 **é o mesmo de antes**. O que mudou é quem o preenche: o campo
`"nota"` virou `"notas": [8, 9]` — índices para um **catálogo de notas escritas por um
humano** ([13](13-camada-de-ia-jev.md), Parte 4h), porque o Jev seleciona notas, não as
escreve. Num app de ensino isso é um upgrade: nenhum modelo inventa regra gramatical de
Libras na frente de um aluno.

E `confianca` deixou de ser um número que o modelo narra sobre si mesmo: é a `confidence`
calibrada que vem em cada resposta, pronta para entrar num `if`.

Note `video_humano`: é o gancho entre o avatar e o seu dataset. 1.095 dos 1.364 sinais do
V-LIBRASIL existem nos dois mundos — **mostrar o humano ao lado do boneco é a feature
didática mais barata e mais valiosa do projeto.**

## A parte "ele se adapta" — o que isso significa de fato

Você descreveu: mudar "roeu" para "mordeu", "Roma" para "Rússia", e o boneco se adaptar.
Isso funciona de três formas, em ordem de ambição:

**Nível 1 — adaptação reativa (grátis, já funciona).**
Mudou o texto, re-traduz, re-sinaliza. Confirmado ✅: `MORDER` e `RÚSSIA` existem no acervo
e a API acerta os dois.

**Nível 2 — adaptação por diferença (alto valor, barato).**
Compare a glosa nova com a anterior e **destaque só o que mudou**:
> "Você trocou 2 sinais: `ROEDOR`→`MORDER`, `ROMA`→`RÚSSIA`. Repita só esses."
Isto é pedagogia de verdade — prática espaçada sobre o delta. Dá para fazer com `diff` de
listas, sem IA nenhuma.

**Nível 3 — adaptação ao aluno (o produto maduro).**
O sistema sabe quais sinais você já viu e acertou, e passa a propor frases que reusam o
conhecido e introduzem pouca coisa nova. Precisa de persistência de estado e um modelo
simples de domínio (repetição espaçada tipo SM-2).

Recomendo mirar o **nível 2 na v1**. É onde o esforço vira diferencial visível.

## Stack sugerida

| Camada | Escolha | Por quê |
|---|---|---|
| Front | **Vite + React + TypeScript** | o iframe exige controle fino de ciclo de vida; TS pega erro de contrato cedo |
| Player | iframe `vlibras.gov.br/app/unity/index.html` | CORS aberto, zero backend ✅ |
| Tradução base | API VLibras direto do browser | CORS aberto ✅ |
| Bundles | `public/dados/bundles.json` versionado | 342 KB, carrega uma vez, valida em memória |
| **IA** | **Jev (TypeSafe), `jev-1.14.0`** | 114 ms, US$ 0,000043/frase, `confidence` calibrada — ver [13](13-camada-de-ia-jev.md) |
| Chamada da IA | **backend fino** (não exponha a chave no browser) | única razão de existir backend |
| Lematizador | `simplemma` (leve) ou `spaCy pt_core_news_sm` | **ainda não instalado** ✅; é o teto do recall de candidatos |
| Persistência | localStorage na v1 | não construa banco antes de precisar |

**O backend mínimo é um endpoint só:** `POST /glosa {texto}` → JSON. Ele lematiza, levanta
candidatos, chama o Jev uma vez, monta a glosa e valida. Não construa mais que isso no começo.

> 🚩 **Decisão de 2026-10-29: Jev sozinho, sem LLM.** Um LLM entraria só para prosa sob
> demanda ("me explique melhor" em texto livre), e isso ficou para o futuro. Nada do que está
> desenhado aqui precisa mudar se ele entrar depois.

## Ordem de construção (incremental, cada passo entrega algo usável)

1. **Esqueleto que fala** — iframe + caixa de texto + `translate` + `playNow`.
   Já existe, é o POC em [03](03-player-3d.md). *Meio dia.*
2. **Validador de glosa** — carregar `bundles.json`, marcar cada token
   ✅ sabe / ⚠️ vai soletrar. *Um dia.* **Maior ganho de qualidade por hora investida.**
3. **UI didática** — mostrar a glosa token a token, destacar com `counter_gloss`,
   controles de velocidade/repetir/pausar. *Dois dias.*
4. **Vídeo humano** — mapear glosa → vídeo V-LIBRASIL, mostrar lado a lado. *Um dia.*
5. **Gerador de candidatos** — lematizador + trie sobre `bundles.json`. *Dois dias.*
   **Não precisa de chave de API** e é o teto de qualidade de tudo que vem depois.
6. **Catálogo de notas pedagógicas** — as 14 regras do [05](05-glosa-a-linguagem.md) como
   seed. *Um dia.* Também **não precisa de chave**.
7. **Camada Jev** — backend fino, uma requisição com ~19 perguntas, montagem em código.
   *Uma semana.* Primeiro comando a dar com a chave: rodar as 40 frases do
   [11](11-conjugacao-verbal-e-o-teto-das-regras.md) — custa **US$ 0,0017**.
8. **Diferença entre frases** — nível 2 da adaptação. *Dois dias.* `diff` de listas, sem IA:
   o Jev não conta ([13](13-camada-de-ia-jev.md), Parte 6.4).
9. **Progresso do aluno** — repetição espaçada. *Depois.*

Repare que **nada antes do passo 7 precisa de chave de API**, e já é um produto útil. Resista à
tentação de começar pela IA.

## O que explicitamente não fazer

- ❌ **Não gere animação nova.** Sem Unity 2018.3.1 + ferramentas internas do LAViD, não há
  como produzir AssetBundle ([07](07-wikilibras-e-rig-3d.md)).
- ❌ **Não use `/video`** para o chat. É fila assíncrona; mata a interatividade.
- ❌ **Não construa proxy de CORS.** Já é aberto ✅. Backend só pela chave do LLM.
- ❌ **Não normalize acentos** antes de consultar bundles. `RUSSIA` não existe, `RÚSSIA` sim.
- ❌ **Não confie na glosa sem validar.** Repetido de propósito.
- ❌ **Não peça texto ao Jev.** Nem a glosa, nem a explicação. Se a resposta precisa ser
  escrita, ela vem de catálogo ou de código ([13](13-camada-de-ia-jev.md)).
- ❌ **Não faça uma requisição por pergunta.** Mande todas juntas: medido em 12,2× mais
  barato e 10× mais rápido, sem mudança nas respostas.
