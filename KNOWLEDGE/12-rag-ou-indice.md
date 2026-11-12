# 12 — Precisamos de RAG? (não, e aqui está o porquê)

Investigação de 2026-10-23, provocada por um caso real:

> `"eu nao gosto de futebol"` sinalizou **NAO · GOSTO · DE · FUTEBOL**, soletrando "nao" e
> "de", e usando **GOSTO no sentido de sabor**. Já `"nao gosto futebol"` saiu
> **NÃO_GOSTAR · FUTEBOL**, correto.

A observação está certíssima e o diagnóstico é instrutivo. Mas a conclusão é o contrário
da esperada: **o banco que você imaginou já existe — e não é RAG.**

---

## Parte 1 — O que de fato aconteceu no seu teste

Medi a API nas duas formas ✅:

```
"eu nao gosto de futebol"   → GOSTAR FUTEBOL          ← negação perdida
"nao gosto de futebol"      → NÃO_GOSTAR FUTEBOL      ← correto
"eu não gosto de futebol"   → NÃO_GOSTAR FUTEBOL      ← correto
```

Repare: **a API nunca devolveu `NAO GOSTO DE FUTEBOL`.** Então o que você viu não veio do
tradutor — veio do **nosso fallback**. A API estava fora do ar (acontece o tempo todo,
Risco 3 em [10](10-desafios-e-duvidas.md)) e o POC caiu na linha:

```js
return texto.toUpperCase();   // fallback herdado do próprio VLibras
```

"eu nao gosto de futebol" virou "EU NAO GOSTO DE FUTEBOL", e o player tentou cada palavra:

| Token | Tem bundle? | O que o avatar fez |
|---|---|---|
| `EU` | ✅ | sinal certo, por acaso |
| `NAO` | ❌ (só `NÃO` com til existe) | soletrou N-A-O |
| `GOSTO` | ✅ **mas é o substantivo** (sabor) | **sinal errado, com confiança** |
| `DE` | ❌ | soletrou D-E |
| `FUTEBOL` | ✅ | sinal certo |

> 🔴 **Isto é um defeito nosso, não do VLibras.** O fallback `toUpperCase()` fabrica tokens
> que às vezes *casam por acidente* com um sinal de outro sentido. É a Classe B
> ([11](11-conjugacao-verbal-e-o-teto-das-regras.md)) sendo **criada por nós**.
> Corrigido — ver Parte 4.

E, de brinde, mais uma fragilidade do tradutor: a palavra **"eu"** quebra a regra de
negação quando falta o til. `nao gosto` funciona, `eu nao gosto` não.

---

## Parte 2 — O acervo já é um léxico estruturado

Aqui está a descoberta que responde a sua pergunta. Mineirei o `dados/bundles.json`
(342 KB, já versionado) e ele **não é uma lista de palavras — é um dicionário com
gramática embutida** ✅:

| Estrutura | Quantidade | Exemplo |
|---|---|---|
| **Pares de negação** `X` / `NÃO_X` | **386** | `GOSTAR` / `NÃO_GOSTAR`, `TER` / `NÃO_TER` |
| **Palavras polissêmicas** com sentidos explícitos | **1.533** (719 com mais de um) | `BANCO&DADOS`, `BANCO&DINHEIRO`, `BANCO&SENTAR` |
| **Pares de intensidade** `(+)` / `(-)` | **284** | `GRANDE(+)`, `TÍMIDO(-)` |
| **Verbos direcionais** com paradigma de pessoa | **70 verbos** | `AJUDAR` tem 28 combinações |
| **Afirmação enfática** `_SIM` | 25 | `CONHECER_SIM` |
| **Índice sem acento** | 24.101 | `MUSICA` → `MÚSICA` |

Olhe o que o acervo sabe sobre `PODER`, de graça:

```
PODER&DOM · PODER&EXECUTIVO · PODER&INFLUÊNCIA · PODER&JUDICIÁRIO
PODER&LEGISLATIVO · PODER&POSSIBILIDADE · PODER&POTÊNCIA
```

**Isso é um inventário de sentidos pronto** — exatamente o tipo de conhecimento que você
imaginou ter que construir num banco vetorial. Ele já veio junto, e cabe na memória.

---

## Parte 3 — Quanto dá para consertar sem IA nenhuma (medido)

Escrevi um corretor determinístico que só usa o que o acervo permite decidir sem
ambiguidade: acento, remoção de palavras funcionais, e negação incorporada.

**Resultado: 5 de 7 casos corrigidos, zero IA, zero latência, zero custo** ✅

```
"nao tenho dinheiro"      NAO TER DINHEIRO            → NÃO_TER DINHEIRO       ✅
"eu nao sei nada"         EU NAO SABER NADA           → EU NÃO_SABER NADA      ✅
"nunca comi isso"         NUNCA COMER ISSO            → NÃO_COMER ISSO         ✅
"ela cantou uma musica"   ELA CANTAR MUSICA           → ELA CANTAR MÚSICA      ✅
"o menino correu rapido"  MENINO CORRER&PESSOA RAPIDO → ...CORRER&PESSOA RÁPIDO ✅
```

Os 2 que falharam mostram exatamente onde fica a fronteira:

```
"eu nao gosto de futebol"  NAO GOSTO DE FUTEBOL  →  NÃO GOSTO FUTEBOL
                                                    (queria NÃO_GOSTAR FUTEBOL)
```

O corretor tirou o `DE`, acertou o til — mas **não sabe que `GOSTO` é flexão de `GOSTAR`**.
Para saber isso é preciso lematizar, e lematizar é PLN. Ou seja: ou o tradutor local
([08](08-traducao-offline.md)), ou IA.

**A fronteira, em uma frase:** o acervo resolve *morfologia de sinal* (que forma usar);
ele não resolve *morfologia de português* (que palavra é essa).

---

## Parte 4 — Correção aplicada no POC

O fallback deixou de mentir. Quando a API cai, ele agora:

1. **avisa em destaque** que não houve tradução e aquilo não é Libras, é soletração;
2. **remove palavras funcionais** (`de`, `da`, `o`, `que`…), que nunca viram sinal;
3. **marca como não confiável** qualquer token que case com bundle por acidente — porque
   `GOSTO` casar não significa que está certo.

Melhor mostrar menos e avisar, do que sinalizar "sabor" com confiança.

---

## Parte 5 — Então, RAG serve para quê?

Sua intuição — "precisamos de um banco para a IA consultar" — está certa. O que muda é
**qual banco, e com que tecnologia**. Separando o problema em quatro perguntas:

### ❌ "Essa glosa existe?" — não é RAG, é um `Set`

Conjunto fechado de 24.213 strings, 342 KB. Resposta exata em O(1). Busca semântica aqui
seria usar um helicóptero para atravessar a rua. **Já implementado.**

### ❌ "Quais glosas são candidatas para esta palavra?" — não é RAG, é índice

Prefixo, lema, sem-acento, grupos `&`. Tudo determinístico, offline, instantâneo. O próprio
VLibras publica uma *trie* pronta em `/static/TREES/2018.3.1.json`. **Falta construir, é barato.**

### ❌ "Qual sentido cabe nesta frase?" — não é RAG, é prompt

`PODER` tem 7 sentidos. Você joga os 7 no prompt junto da frase e pede para o modelo
escolher. Não há o que recuperar: o inventário é minúsculo e você já o tem em memória.
RAG só faria sentido se o inventário não coubesse no contexto — e ele cabe com folga.

### ✅ "Não existe glosa para esta palavra — qual é o sinal mais próximo?"

**Aqui sim vale vetor.** "automóvel" não está no acervo; `CARRO` está. "enfermidade" não
está; `DOENÇA` está. Hoje essas palavras viram datilologia.

Isso é **busca semântica sobre vocabulário fixo**, e é barato:
- embeda as 24.213 glosas **uma vez**, offline (poucos centavos, uns minutos);
- guarda os vetores num arquivo — nem precisa de banco vetorial nesse tamanho;
  `numpy` + produto escalar resolve 24k vetores em milissegundos;
- em runtime, embeda só a palavra órfã e pega os 5 vizinhos mais próximos;
- manda os 5 para o LLM confirmar (ou rejeitar — "não há sinal equivalente" é resposta válida).

Note que **isto não é RAG** no sentido usual. É *semantic search*. Não há documentos,
não há chunks, não há recuperação de texto para o modelo ler.

### ✅✅ "Como frases parecidas com esta foram traduzidas corretamente?"

**Este é RAG de verdade, e é o mais valioso dos cinco.** Recuperar pares
(português → glosa validada) semelhantes à frase atual e usá-los como few-shot.

Mas tem um porém decisivo: **você ainda não tem esse corpus.** RAG não cria conhecimento,
só recupera o que existe. Hoje você tem zero pares validados.

A boa notícia é que o projeto é uma máquina de produzir exatamente esse dado:
- toda frase corrigida pela camada de IA e aprovada vira um par;
- toda correção manual sua vira um par;
- o endpoint `/review` do VLibras ([02](02-api-traducao.md)) mostra que eles coletam isso
  do mesmo jeito.

> **Conclusão sobre RAG: não é o primeiro passo, é o terceiro.** Antes de recuperar
> exemplos, é preciso tê-los. Construa o loop que os gera e o RAG vira consequência natural
> em alguns meses de uso.

---

## Parte 6 — A ordem recomendada

| # | Camada | Tecnologia | Custo | Resolve |
|---|---|---|---|---|
| 1 | Normalizar entrada | acento, pontuação | ~0 | família inteira de defeitos |
| 2 | Índice do acervo | `Set` + trie + grupos `&` | ~0 | "existe?", "quais candidatos?" |
| 3 | Corretor determinístico | 386 pares de negação, etc. | ~0 | **5/7 medido** ✅ |
| 4 | Heurísticas de alerta | colapso, negação sumida | ~0 | admite erro em vez de mentir |
| 5 | **Jev com candidatos** | [Jev / TypeSafe](13-camada-de-ia-jev.md) | ¢ | sentido, Classe B, pessoa, ordem, emoção |
| 6 | Vetores do acervo | embeddings offline | ¢ uma vez | palavra órfã → sinal próximo |
| 7 | **RAG de exemplos** | corpus próprio + vetores | $ | qualidade crescente com o uso |

> 📌 **Atualização 2026-10-29.** O passo 5 ganhou nome: **Jev (TypeSafe)**, a
> US$ 0,000043 por frase — ¢, não $. E a Parte 5 deste documento previu o desenho sem saber:
> *"não é RAG, é prompt — você joga os 7 sentidos de `PODER` junto da frase e pede para o
> modelo escolher"* **é literalmente um `Choice` do Jev**, que só sabe escolher dentro de um
> inventário fechado. Os 3.251 grupos `&` do acervo são 3.251 `Choice` prontos.
> A lematização do passo 5 saiu da IA e voltou para o código (`simplemma`/spaCy), porque o
> Jev não gera texto. Ver [13](13-camada-de-ia-jev.md).

Os passos 1–4 **não precisam de IA e já estão quase todos no POC**. O passo 5 é o que você
já decidiu buscar. O 6 é um bônus barato. O 7 é o que o projeto constrói sozinho, desde que
você guarde as correções desde o primeiro dia.

### A recomendação de uma linha

> **Não monte banco vetorial agora.** Monte o índice do acervo (que é grátis e resolve mais
> do que parece), contrate a API de IA para o que exige semântica, e **comece a guardar
> cada correção aprovada em um arquivo desde já** — é esse arquivo que, daqui a alguns
> meses, vira o RAG que realmente vale a pena.
