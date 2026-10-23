# 04 — O dicionário: o que o avatar realmente sabe fazer

Números apurados em 2026-10-22 ✅ baixando a lista inteira.

## Onde fica o vocabulário

```
GET https://dicionario2.vlibras.gov.br/bundles        → JSON array com TODAS as glosas
GET https://dicionario2.vlibras.gov.br/signs?version=2018.3.1   → 301 → /static/TREES/2018.3.1.json
GET https://repositorio.vlibras.gov.br/api/signs      → mesma lista
```

- `/bundles` → **342 KB, 24.213 glosas.** Essa é a verdade sobre o que o avatar consegue fazer.
- `/static/TREES/2018.3.1.json` → **3,5 MB**, a mesma lista como *trie* (árvore de prefixos,
  `{children:{...}, end:bool}`). É o que o widget usa para autocompletar no dicionário.
  Para nós a lista plana é mais útil; a trie serve se quisermos busca por prefixo rápida.

**Baixe uma vez, versione no repo, consulte em memória.** Não há motivo para bater nesse
endpoint em runtime.

## Como um sinal é baixado

```
https://dicionario2.vlibras.gov.br/static/BUNDLES/2018.3.1/WEBGL/{REGIÃO}/{GLOSA}
```

Exemplo real: `.../WEBGL/BR/ABACAXI` → `200`, `application/octet-stream`, **32.010 bytes**,
começando com o header mágico `UnityFS` + `2018.3.1f1`. É um **AssetBundle Unity** com a
animação do sinal.

Há também a rota curta `.../2018.3.1/WEBGL/BR/ABACAXI` que faz `301` para a `/static/`.

### Regiões — só existe `BR` hoje ✅

Testei `SP, RJ, MG, RS, PE, CE, BA, PR, DF`: **todos 404**. O player tem `setRegion` e a
interface oferece "Seleção de Região" para regionalismos, mas na prática só a pasta `BR`
está publicada. **Hardcode `BR`.**

## Anatomia das 24.213 glosas

| Tipo | Quantidade | Exemplos |
|---|---|---|
| Palavra simples | 16.875 | `CASA`, `ABACAXI`, `CORRER` |
| Com `&` (desambiguação) | 3.251 | `ABAIXAR&SOM`, `ABAIXAR&VOZ`, `COMPRAR&DINHEIRO` |
| Com `_` (sinal composto) | 3.985 | `BOM_DIA`, `TUDO_BEM`, `NÃO_TER`, `CRISE_ECONÔMICA` |
| Verbos direcionais `1P_X_3S` | 367 | `1P_AJUDAR_3S`, `2S_AJUDAR_1S`, `1P_DAR_2P` |
| Intensidade `(+)` / `(-)` | 365 | `ALEGRE(+)`, `AGRESSIVO(-)`, `ÁGUA(+)` |
| Pontuação | 3 | `[PONTO]`, `[INTERROGAÇÃO]`, `[EXCLAMAÇÃO]` |
| Alfabeto + dígitos | 38 | `A`..`Z`, `Ç`, `0`..`9`, `%` |

### O alfabeto é o que permite a datilologia

`A B C D E F G H I J K L M N O P Q R S T U V W X Y Z Ç 0 1 2 3 4 5 6 7 8 9 %`

Quando uma glosa não existe no dicionário, **o player soletra**. Testei `GUSTAVO`:
reportou `counter_gloss [1,1]` — ou seja, conta como **um único item de glosa**, mas por
dentro executa 7 configurações de mão. A datilologia é transparente para o contador.

## 🔴 A armadilha que você precisa conhecer

Um token de glosa que **não tem bundle não gera erro**. O player o trata como palavra a
soletrar — **letra por letra, incluindo números e underscores**.

Teste real: a API traduziu `Não quero ir ao cinema hoje porque estou cansado` para
`NÃO_QUERER 1S_IR_2S CINEMA HOJE CANSADO [PONTO]`. O token **`1S_IR_2S` não existe** na
lista de bundles. O que foi observado ✅: aos 14 s a animação ainda estava em `counter_gloss [1,6]`;
foram precisos **mais de 25 s** para chegar a `[5,6]`. Nenhum evento de erro foi emitido em
momento algum — do ponto de vista do código, estava tudo bem.

A leitura: o player tentou **soletrar literalmente** `1-S-I-R-2-S`, consumindo um tempo
desproporcional. Removendo o token quebrado (`NÃO_QUERER IR CINEMA HOJE CANSADO [PONTO]`),
a mesma frase voltou ao ritmo normal.

> Não é um travamento — é pior: é lentidão silenciosa produzindo um sinal sem sentido.
> Quem está aprendendo vai *copiar* esse lixo.

### A regra de ouro do projeto

> **Antes de mandar qualquer glosa para o `playNow`, valide cada token contra a lista de
> bundles. Nunca confie na saída do tradutor.**

```js
const BUNDLES = new Set(await (await fetch('/dados/bundles.json')).json());

function sanitizar(glosa) {
  return glosa.split(/\s+/).filter(Boolean).map(tok => {
    if (BUNDLES.has(tok)) return { tok, ok: true };
    // 1) tentar o lado esquerdo de um composto direcional: 1S_IR_2S -> IR
    const m = tok.match(/^[123][SP]_(.+?)_[123][SP]$/);
    if (m && BUNDLES.has(m[1])) return { tok: m[1], ok: true, nota: 'direcional sem bundle' };
    // 2) tentar sem o qualificador &: COMPRAR&DINHEIRO -> COMPRAR
    const base = tok.split('&')[0];
    if (BUNDLES.has(base)) return { tok: base, ok: true, nota: 'desambiguação sem bundle' };
    // 3) desistir: vai virar datilologia — avise o usuário
    return { tok, ok: false, nota: 'será soletrado' };
  });
}
```

Essa função é, provavelmente, **o primeiro código que vale a pena escrever no projeto.**
Ela também é a base da UI didática: dá para mostrar "esta palavra o avatar sabe / esta ele
vai soletrar", que é informação *valiosa* para quem está aprendendo.

## Cobertura medida com frases reais ✅

10 frases do cotidiano → 65 tokens de glosa → **2 sem bundle (3,1%)**.
Os dois faltantes foram `GUSTAVO` (nome próprio, esperado e correto soletrar) e
`1S_IR_2S` (bug do tradutor: inventou uma flexão direcional que não existe no acervo).

**Interpretação:** o acervo de 24 mil sinais é generoso. O gargalo não é vocabulário, é
gramática e os buracos silenciosos.

## Cruzamento com o seu dataset V-LIBRASIL

Dos **1.364 sinais** do dataset `SchberGg/v-librasil-raw`:
- **1.030** batem com um bundle por nome exato (maiúsculas + `_`);
- **1.095 (80%)** batem se ignorarmos acento e parênteses;
- **269 não têm bundle correspondente.**

Esses 269 são a parte mais interessante: sinais que **existem em vídeo humano mas o avatar
não sabe fazer**. Exemplos: `ABRIR_A_PORTA`, `BATER_PAPO`, `AO_REDOR`, `BARCO_A_VELA`,
`CADEIRA_DE_BALANÇO`, `ATÉ_AGORA`, `APAIXONAR-SE`.

Isso abre dois caminhos (ver [07](07-wikilibras-e-rig-3d.md) e [09](09-projeto-arquitetura.md)):
mostrar o **vídeo humano** quando o avatar não souber, ou um dia **gerar a animação** a
partir do vídeo.

## Snippet para baixar e versionar a lista

```bash
curl -sS https://dicionario2.vlibras.gov.br/bundles -o dados/bundles.json
python3 -c "import json;b=json.load(open('dados/bundles.json'));print(len(b),'glosas')"
```
