# 02 — API de tradução PT → Glosa

Tudo aqui foi **testado ao vivo em 2026-10-22** ✅, não só lido da documentação.

## Os endpoints que existem

| Ambiente | Base URL | Estado medido |
|---|---|---|
| **Produção** | `https://traducao2.vlibras.gov.br` | ✅ funciona, **mas cai e volta** |
| **Homologação (dth)** | `https://traducao2-dth.vlibras.gov.br` | ✅ funciona, mais estável nos testes |
| Local | `http://localhost:3000` | se subirmos o repo |

Os dois ambientes estão hardcoded no bundle do widget de produção (`vlibras-initial-*.js`),
junto de todos os outros serviços. Mapa completo extraído:

```js
production: {
  TRANSLATE_URL:           "https://traducao2.vlibras.gov.br/translate",
  REVIEW_URL:              "https://traducao2.vlibras.gov.br/review",
  DICTIONARY_URL:          "https://dicionario2.vlibras.gov.br/2018.3.1/WEBGL/",
  DICTIONARY_STATIC_URL:   "https://dicionario2.vlibras.gov.br/static/BUNDLES/2018.3.1/WEBGL/",
  DICTIONARY_CATEGORIES_URL:"https://repositorio.vlibras.gov.br/api",
  SIGNS_URL:               "https://dicionario2.vlibras.gov.br/signs?version=2018.3.1",
  BUNDLES_URL:             "https://dicionario2.vlibras.gov.br/bundles"
}
// homolog: idem com "-dth" nos hosts
```

## `POST /translate` — o único que importa

```http
POST https://traducao2.vlibras.gov.br/translate
Content-Type: application/json

{"text": "o rato roeu a roupa do rei de roma"}
```

Resposta — **atenção, não é JSON**:

```
HTTP/2 200
content-type: text/html; charset=utf-8

RATO ROEDOR ROUPA REI ROMA
```

É **texto puro**. Um `response.json()` quebra. Use `response.text()`.

### Parâmetro `domain` (opcional, inútil hoje)

O `player-webjs` manda `{text, domain}` onde `domain` é o `location.host`. Testado: **não
muda o resultado**. É telemetria/estatística, não um seletor de domínio semântico. Pode omitir.

### Casos reais medidos ✅

| Entrada | Saída | Observação |
|---|---|---|
| `o rato roeu a roupa do rei de roma` | `RATO ROEDOR ROUPA REI ROMA` | ⚠️ "roeu"→**ROEDOR** (lematizou para substantivo) |
| `o rato mordeu a roupa do rei da russia` | `RATO MORDER ROUPA REI RUSSIA` | ✅ perfeito |
| `Bom dia! Hoje vamos aprender a conversar em Libras.` | `BOM_DIA [EXCLAMAÇÃO] HOJE APRENDER CONVERSAR LIBRAS [PONTO]` | ✅ |
| `Você pode me ajudar a encontrar o banheiro, por favor?` | `VOCÊ PODER&POSSIBILIDADE 2S_AJUDAR_1S 1S_ENCONTRAR_2S BANHEIRO POR_FAVOR [INTERROGAÇÃO]` | ✅ pegou **concordância verbal**! |
| `Não quero ir ao cinema hoje porque estou cansado.` | `NÃO_QUERER 1S_IR_2S CINEMA HOJE CANSADO [PONTO]` | ⚠️ `1S_IR_2S` **não tem bundle** |
| `Eu nao gosto de futebol` (sem acento) | `GOSTAR FUTEBOL` | 🔴 **a negação sumiu** — inverte o sentido |
| `Eu não gosto de futebol` (com acento) | `NÃO_GOSTAR FUTEBOL` | ✅ **o acento salva** — ver abaixo |
| `Eu vou comprar um abacaxi amanhã na feira...` | `COMPRAR&DINHEIRO ABACAXI AMANHAR FEIRA NÃO_TER DINHEIRO SUFICIENTE [PONTO]` | ⚠️ "amanhã"→**AMANHAR** (verbo) |
| `xpto zzzz blablabla` | `XPTO ZZZZ BLABLABLA` | desconhecido passa em maiúscula → datilologia |

### ⚠️ Correção importante: muita coisa era culpa da entrada sem acento

Testes posteriores ✅ mostraram que vários desses "erros do tradutor" eram, na verdade,
**erro da minha entrada**:

```
"Eu nao gosto de futebol"   → GOSTAR FUTEBOL        🔴 negação perdida
"Eu não gosto de futebol"   → NÃO_GOSTAR FUTEBOL    ✅ correto
"ela cantou uma musica"     → ELA CANTAR MUSICA     🔴 MUSICA não tem bundle
"ela cantou uma música"     → ELA CANTAR MÚSICA     ✅
"ele le o jornal"           → ELE LE JORNAL         🔴
"ele lê o jornal"           → ELE LER JORNAL        ✅ o acento corrigiu até o verbo
```

**Acentue a entrada.** É a melhoria mais barata do projeto inteiro. Um corretor ortográfico
antes da chamada — ou só avisar o usuário — resolve uma família inteira de defeitos.

**Leitura dos erros que sobram:** o tradutor erra em (a) lematização de alguns verbos
irregulares, (b) advérbios temporais que parecem verbo, (c) flexões direcionais inventadas,
e (d) **colapso contextual** — a falha mais grave, documentada em
[11](11-conjugacao-verbal-e-o-teto-das-regras.md). Isso define onde a nossa IA agrega valor
(ver [09](09-projeto-arquitetura.md)).

### Cobertura medida

Em 10 frases cotidianas → **65 tokens de glosa, 2 sem bundle (3,1%)**. Ou seja, o tradutor
acerta o vocabulário quase sempre; o problema é **gramática e os 3% silenciosos**.

## Rate limit e CORS ✅

Headers de resposta reais:

```
x-ratelimit-limit: 300
x-ratelimit-remaining: 297
x-ratelimit-reset: 1792697449     # epoch do fim da janela (~1 min)
```

- **300 requisições por janela de ~1 minuto, por IP.** Folgado para um chat, apertado
  para pré-processar um dataset de 1.364 sinais em paralelo. Para lote, use o tradutor local ([08](08-traducao-offline.md)).
- **CORS totalmente aberto** ✅: o preflight `OPTIONS` reflete qualquer `Origin`
  (testado com `http://localhost:5173` → `access-control-allow-origin: http://localhost:5173`).
  **O browser pode chamar direto, sem proxy.** Nada de backend só para contornar CORS.

## Instabilidade — planeje para ela ✅

Durante a apuração, `traducao2.vlibras.gov.br/translate` alternou entre:

```
500  {"error":"Translation Core Unavailable"}     ← worker Python fora do ar
200  RATO ROEDOR ROUPA REI ROMA                   ← normal
```

Isso aconteceu **quatro vezes em duas horas** de apuração. E na última, o pior cenário:

```
traducao2.vlibras.gov.br/translate       → 500  {"error":"Translation Core Unavailable"}
traducao2-dth.vlibras.gov.br/translate   → 503
```

**Os dois ambientes fora ao mesmo tempo.** E não foi rate limit — o header mostrava
`x-ratelimit-remaining: 273` de 300. Foi queda real e simultânea de prod e homologação.

> Consequência de projeto: **o fallback entre prod e dth não é suficiente.** Os dois
> ambientes compartilham destino. Se a disponibilidade importar, o tradutor local
> ([08](08-traducao-offline.md)) deixa de ser conveniência e vira a única resiliência real.
> No mínimo: **cacheie toda tradução bem-sucedida** — um tutor repete frases o tempo todo.

**Regra para o nosso código:**

```js
const EPS = [
  "https://traducao2.vlibras.gov.br/translate",
  "https://traducao2-dth.vlibras.gov.br/translate",
];
async function traduzir(text) {
  for (let tentativa = 0; tentativa < 3; tentativa++) {
    for (const ep of EPS) {
      try {
        const r = await fetch(ep, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        if (r.ok) return (await r.text()).trim();   // text(), NÃO json()
      } catch (_) { /* tenta o próximo */ }
    }
    await new Promise(r => setTimeout(r, 1500));
  }
  return text.toUpperCase();   // fallback do próprio VLibras: datilologia
}
```

Esse fallback final (`text.toUpperCase()`) é exatamente o que o `player-webjs` faz quando a
tradução falha. Mantém o app vivo, às custas de soletrar tudo.

## Os outros endpoints

### `POST /review` — feedback de tradução

```json
{
  "text": "o rato roeu a roupa do rei de roma",
  "translation": "RATO ROER ROUPA REI ROMA",
  "rating": "bad",                       // "good" | "bad"
  "review": "RATO ROER ROUPA REI ROMA"   // opcional: a correção
}
```
Resposta: `OK`. É assim que o VLibras coleta dados de treino. **Ideia:** nosso app pode
alimentar isso de volta — e, mais importante, guardar as mesmas correções para nós.

### Geração de vídeo (assíncrona)

```
POST /video                      {"gloss":"...", "avatar":"icaro|hozana", "caption":"enable|disable"}
                                 → {"requestUID":"c6730846-..."}
GET  /video/status/{requestUID}  → {"status":"queued|processing|generated|failed","size":483214}
GET  /video/download/{requestUID} → MP4 binário (disponível por 1 hora)
```

Útil se um dia quisermos exportar uma lição em vídeo. **Não é o caminho do chat** — vídeo
tem latência de fila; o player WebGL é instantâneo.

### `/dl/translate` — a rota neural, fechada

```
POST https://traducao2.vlibras.gov.br/dl/translate  → 401 {"error":"Unauthorized"}
```
O `player-webjs` (v5) aponta para ela, mas hoje exige credencial. Não conte com ela.
Para ter tradução neural, rode local ([08](08-traducao-offline.md)).

## Contrato OpenAPI (resumo oficial, v2.4.0)

| Método | Rota | Corpo / Param | Respostas |
|---|---|---|---|
| POST | `/translate` | `{text}` | 200 texto, 422, 500 |
| POST | `/review` | `{text, translation, rating, review?}` | 200 `OK`, 422, 500 |
| POST | `/video` | `{gloss, avatar, caption}` | 200 `{requestUID}`, 422, 500 |
| GET | `/video/status/{uid}` | — | 200 `{status,size}`, 404, 422 |
| GET | `/video/download/{uid}` | — | 200 binário, 404, 422 |
| GET | `/docs` | — | Swagger (só no localhost) |
| GET | `/metrics` | — | Prometheus |

Fonte: `src/app/doc/openapi.json` do repo `vlibras-translator-api`.
Curiosidade: o exemplo oficial da própria spec é **exatamente** "o rato roeu a roupa do rei
de roma" → `RATO ROER ROUPA REI ROMA`. Note que a spec promete `ROER` e a produção entrega
`ROEDOR` — a documentação está à frente do que o modelo faz.
