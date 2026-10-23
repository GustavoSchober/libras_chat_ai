# 09 — LIBRAS AI CHAT: arquitetura proposta

Tudo que vem antes é o terreno. Isto é o que construir em cima.

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
├─ CAMADA 2 — IA DE GLOSA  (onde o LLM entra)
│   corrige a gramática que o tradutor erra, escolhe sentido pelo contexto,
│   VALIDA contra os bundles, escolhe emoção facial
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
          ├─[1]─► POST /translate ──► "GOSTAR FUTEBOL"       🔴 negação perdida
          │
          ├─[2]─► LLM recebe: frase + glosa-base + lista de bundles candidatos
          │       devolve JSON:
          │       {
          │         "glosa": "FUTEBOL EU NÃO_GOSTAR [PONTO]",
          │         "emocao": {"nome":"default","intensidade":2},
          │         "tokens": [
          │           {"glosa":"FUTEBOL","pt":"futebol","nota":"tópico vem primeiro em Libras"},
          │           {"glosa":"EU","pt":"eu"},
          │           {"glosa":"NÃO_GOSTAR","pt":"não gosto",
          │            "nota":"a negação é incorporada ao sinal + balanço de cabeça"}
          │         ],
          │         "correcoes":["o tradutor base perdeu a negação"]
          │       }
          │
          ├─[3]─► VALIDADOR: cada token existe em bundles.json?
          │       NÃO_GOSTAR ✅  FUTEBOL ✅  EU ✅  [PONTO] ✅
          │       (se algum falhar → pede correção ao LLM ou degrada)
          │
          ├─[4]─► send('EmotionBridge','ApplyDefaultEmotion','2')
          │       send('PlayerManager','playNow','FUTEBOL EU NÃO_GOSTAR [PONTO]')
          │
          └─[5]─► counter_gloss [n,total] → destaca o token n na UI
                  + se o sinal estiver no V-LIBRASIL, oferece o vídeo humano
```

O passo **[3] não é opcional.** Sem ele, o avatar soletra lixo em silêncio ([04](04-dicionario-e-bundles.md)).

## Por que o LLM pertence à camada 2

Não é "IA porque está na moda". Cada erro medido do tradutor é exatamente o tipo de
problema que um LLM resolve e um sistema de regras não:

| Erro medido ✅ | Por que regras falham | Por que LLM resolve |
|---|---|---|
| "não gosto" → `GOSTAR` | regra de negação não cobriu o padrão | entende negação como semântica |
| "roeu" → `ROEDOR` | lematizador escolheu o substantivo | desambigua por contexto sintático |
| "amanhã" → `AMANHAR` | ambiguidade advérbio/verbo | contexto temporal é óbvio |
| `COMPRAR&DINHEIRO` para "comprar abacaxi" | escolha lexical isolada | vê a frase inteira |
| "aumentou muito" perde o "muito" | não usa `(+)` | pode escolher `AUMENTAR(+)` |
| `1S_IR_2S` inexistente | não valida contra acervo | **damos o acervo no prompt** |

E a prova de que a direção está certa: **o próprio VLibras adicionou refinamento por LLM**
em 2026 (`ENABLE_REFINEMENT`, `LLM_PROVIDER`, `LLM_MODEL`). Estamos indo ao mesmo lugar,
com liberdade de fazer melhor.

### Como dar o acervo ao LLM

24.213 glosas não cabem num prompt. A estratégia que funciona:

1. traduza com a API → glosa base
2. para cada token, levante **candidatos** dos bundles (prefixo via trie, ou busca fuzzy
   sobre o lema) — tipicamente 5–20 por palavra
3. mande ao LLM **só esses candidatos**, não o acervo inteiro
4. restrinja a saída: "use apenas glosas da lista fornecida"
5. valide de novo depois — LLM alucina glosa; o validador é a rede de segurança

## O que o LLM devolve: esquema sugerido

```json
{
  "glosa": "FUTEBOL EU NÃO_GOSTAR [PONTO]",
  "emocao": { "nome": "default", "intensidade": 2 },
  "tokens": [
    { "glosa": "FUTEBOL", "pt": "futebol",
      "nota": "Tópico primeiro: Libras costuma marcar o assunto antes do comentário.",
      "tem_bundle": true, "video_humano": "https://huggingface.co/.../Futebol_Articulador1.mp4" }
  ],
  "correcoes": ["o tradutor base perdeu a negação de 'não gosto'"],
  "confianca": 0.86
}
```

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
| LLM | **backend fino** (não exponha a chave no browser) | única razão de existir backend |
| Persistência | localStorage na v1 | não construa banco antes de precisar |

**O backend mínimo é um endpoint só:** `POST /glosa {texto, glosaBase, candidatos}` → JSON.
Não construa mais que isso no começo.

## Ordem de construção (incremental, cada passo entrega algo usável)

1. **Esqueleto que fala** — iframe + caixa de texto + `translate` + `playNow`.
   Já existe, é o POC em [03](03-player-3d.md). *Meio dia.*
2. **Validador de glosa** — carregar `bundles.json`, marcar cada token
   ✅ sabe / ⚠️ vai soletrar. *Um dia.* **Maior ganho de qualidade por hora investida.**
3. **UI didática** — mostrar a glosa token a token, destacar com `counter_gloss`,
   controles de velocidade/repetir/pausar. *Dois dias.*
4. **Vídeo humano** — mapear glosa → vídeo V-LIBRASIL, mostrar lado a lado. *Um dia.*
5. **Camada LLM** — backend fino, prompt com candidatos, esquema JSON acima. *Uma semana.*
6. **Diferença entre frases** — nível 2 da adaptação. *Dois dias.*
7. **Progresso do aluno** — repetição espaçada. *Depois.*

Repare que **nada antes do passo 5 precisa de LLM**, e já é um produto útil. Resista à
tentação de começar pela IA.

## O que explicitamente não fazer

- ❌ **Não gere animação nova.** Sem Unity 2018.3.1 + ferramentas internas do LAViD, não há
  como produzir AssetBundle ([07](07-wikilibras-e-rig-3d.md)).
- ❌ **Não use `/video`** para o chat. É fila assíncrona; mata a interatividade.
- ❌ **Não construa proxy de CORS.** Já é aberto ✅. Backend só pela chave do LLM.
- ❌ **Não normalize acentos** antes de consultar bundles. `RUSSIA` não existe, `RÚSSIA` sim.
- ❌ **Não confie na glosa sem validar.** Repetido de propósito.
