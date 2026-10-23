# 03 — O player 3D: como comandar o boneco

**Este é o arquivo mais importante do projeto.** Contrato completo, verificado executando ✅.

## O que é

Um build **Unity WebGL** (Unity 2018.3.1f1, WebGL 1.0, 256 MB de heap) que:
- carrega o avatar (Ícaro, Hosana ou Guga),
- recebe uma string de glosa,
- baixa um *AssetBundle* por sinal do servidor de dicionário,
- executa as animações em sequência, com legenda opcional.

Ele vive numa página própria, auto-contida: **`https://vlibras.gov.br/app/unity/index.html`**

## Pode embutir? Sim, de qualquer origem ✅

```
GET https://vlibras.gov.br/app/unity/index.html
  access-control-allow-origin: *
  cross-origin-resource-policy: cross-origin
  (sem X-Frame-Options, sem CSP frame-ancestors)
```

E os bundles também liberam CORS para qualquer origem:
```
GET https://dicionario2.vlibras.gov.br/static/BUNDLES/2018.3.1/WEBGL/BR/ABACAXI
  access-control-allow-origin: http://localhost:8099   ← reflete a nossa origem
```

**Conclusão: `<iframe src="https://vlibras.gov.br/app/unity/index.html">` funciona em
localhost, em Vite, em qualquer lugar.** Sem proxy, sem backend.

## Custo de download (medido) ✅

| Arquivo | Tamanho |
|---|---|
| `playerweb.data.unityweb` | **16,99 MB** |
| `playerweb.wasm.code.unityweb` | 3,00 MB |
| `playerweb.wasm.framework.unityweb` | 77 KB |
| `unity-loader.js` | 150 KB |
| `playerweb.json` | 464 B |
| **total do player** | **~20,2 MB, uma vez** |
| cada sinal (bundle) | ~32 KB |

Carregou em **~5 s** numa conexão comum. É um custo de primeira visita; depois o browser cacheia.

## O contrato de comunicação

A página do player é um iframe isolado. A conversa é **`postMessage` nos dois sentidos**.
Isto veio da leitura de `app/unity/index.js` (a ponte real, 1.177 bytes):

### Pai → Player (comandar)

```js
iframe.contentWindow.postMessage(
  { type: 'unity', object: '<GameObject>', method: '<método>', params: '<string>' },
  '*'
);
```

Por dentro o bridge faz `gameInstance.SendMessage(object, method, params)`.
**`params` é sempre string.** Números vão como `'2'`, booleanos como `'1'`/`'0'`.

### Player → Pai (eventos)

```js
window.addEventListener('message', e => {
  const d = e.data;
  if (!d || d.type !== 'unity_event') return;
  // d.event, d.data
});
```

| Evento | `data` | Quando |
|---|---|---|
| `on_load_player` | — | **player pronto. Só comande depois disto.** |
| `update_progress` | `0..1` | download/inicialização |
| `on_playing_state_change` | `[isPlaying, isPaused, isPlayingInterval, isLoading, isRepeatable]` — strings `"True"`/`"False"` | mudança de estado |
| `counter_gloss` | `[n, total]` | **avançou para o sinal n de total** ⭐ |
| `get_avatar` | `"icaro"` | avatar atual |
| `finish_welcome` | bool | fim da animação de boas-vindas |
| `on_error` | `"unsupported"` | sem WebGL |

⭐ `counter_gloss` é o evento que torna o projeto *didático*: ele diz **qual palavra está
sendo sinalizada agora**, permitindo destacar o token correspondente no texto.

## Os GameObjects e todos os métodos

Extraído do bundle de produção v7.12.2 — lista completa e atual:

```js
const OBJ = {
  PLAYER:        'PlayerManager',
  EMOTION:       'EmotionBridge',
  CUSTOMIZATION: 'CustomizationBridge',
};
```

### `PlayerManager`

| Método | `params` | O que faz |
|---|---|---|
| `playNow` | glosa, ex. `'RATO ROER CASA'` | **toca a glosa** |
| `setPauseState` | `'1'` pausa / `'0'` continua | pausa/retoma |
| `stopAll` | `''` | para tudo |
| `repeat` | — | repete |
| `setSlider` | `'0.5'`..`'2'` | velocidade |
| `Change` | `'icaro'` \| `'hosana'` \| `'guga'` | troca de avatar |
| `setBaseUrl` | URL do dicionário + região | **de onde baixar os sinais** |
| `setSubtitlesState` | `'1'` / `'0'` | legenda liga/desliga |
| `playWellcome` | — | animação de boas-vindas |
| `initRandomAnimationsProcess` | — | micro-movimentos de idle |

### `EmotionBridge` — expressão facial

| Método | params |
|---|---|
| `ApplyDefaultEmotion` | intensidade `'1'`..`'3'` (padrão `'2'`) |
| `ApplyHappyEmotion` | idem |
| `ApplySadEmotion` | idem |
| `ApplyAngryEmotion` | idem |
| `ApplyDisgustEmotion` | idem |
| `ApplyFearEmotion` | idem |
| `ApplySurpriseEmotion` | idem |
| `ApplyUpsetEmotion` | idem |

**Isto não é enfeite.** Em Libras, a expressão facial é *gramática* (marcação não-manual):
interrogativa, negativa, intensidade. Ter 8 emoções controláveis é uma alavanca real de
qualidade — ver [05](05-glosa-a-linguagem.md).

### `CustomizationBridge`

| Método | params |
|---|---|
| `setURL` | URL de um JSON de personalização (cabelo, pele, roupa, logo) |
| `SetSubtitleColor` / `SetSubtitleOutlineColor` / `SetSubtitleShadowColor` | cor |

⚠️ A personalização de avatar é, segundo a doc oficial, "recurso exclusivo de instituições
parceiras". O JSON é gerado pelo Console do governo. Não conte com ela.

## Código mínimo que funciona ✅

Este é o POC que rodou de verdade — avatar carregou, traduziu e sinalizou:

```html
<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><title>LIBRAS</title></head>
<body>
<iframe id="pl" src="https://vlibras.gov.br/app/unity/index.html"
        style="width:420px;height:420px;border:0"
        sandbox="allow-scripts allow-same-origin"></iframe>
<script>
const fr = document.getElementById('pl');
const send = (object, method, params) =>
  fr.contentWindow.postMessage({ type:'unity', object, method, params }, '*');

let pronto = false;
window.addEventListener('message', e => {
  const d = e.data; if (!d || d.type !== 'unity_event') return;
  if (d.event === 'on_load_player') {
    pronto = true;
    // obrigatório: dizer de onde baixar os sinais
    send('PlayerManager','setBaseUrl',
         'https://dicionario2.vlibras.gov.br/static/BUNDLES/2018.3.1/WEBGL/BR/');
  }
  if (d.event === 'counter_gloss') {
    const [n, total] = d.data;      // destaque a n-ésima palavra aqui
  }
});

const play = g => pronto && send('PlayerManager','playNow', g);

async function falar(texto) {
  const r = await fetch('https://traducao2.vlibras.gov.br/translate', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ text: texto })
  });
  play((await r.text()).trim());
}
</script></body></html>
```

**Resultado real do teste:**
```
EVT get_avatar "icaro"
EVT on_load_player
TRAD: o rato roeu a roupa do rei de roma => RATO ROEDOR ROUPA REI ROMA
EVT counter_gloss [1,5] [2,5] [3,5] [4,5] [5,5]
```
O avatar Ícaro apareceu e sinalizou as 5 glosas, com legenda. ✅

## ⚠️ `playNow` durante uma reprodução é ignorado

Descoberto testando ✅: se você mandar `playNow` enquanto o avatar ainda está sinalizando a
frase anterior, **o comando se perde em silêncio** — a nova glosa não entra na fila nem
interrompe a atual.

Isso importa muito num chat, onde o usuário corrige o texto e manda de novo sem esperar.
A correção é parar antes:

```js
send('PlayerManager', 'stopAll', '');
setTimeout(() => send('PlayerManager', 'playNow', glosa), 150);
```

O pequeno atraso dá tempo de o Unity processar o `stopAll` antes do `playNow`.

## Três coisas que esse teste provou

1. **`setBaseUrl` é obrigatório.** Sem ele o player não sabe onde buscar os bundles e não
   sinaliza nada. Mande no `on_load_player`, sempre.
2. **Dá para pular o tradutor.** `play('ABACAXI AMANHÃ COMPRAR')` funcionou direto — 3 sinais.
   **Logo, qualquer IA nossa que produza glosa pode comandar o avatar.** Essa é a liberdade
   que viabiliza o projeto.
3. **Pontuação conta como sinal.** `'OI TUDO_BEM VOCÊ [INTERROGAÇÃO]'` reportou `[4,4]`.
   O `[INTERROGAÇÃO]` é um sinal de verdade (expressão facial interrogativa), não um caractere.

## Hospedar o player localmente (opcional)

Todos os arquivos estão no repo `spbgovbr-vlibras/vlibras-portal`, pasta `app/unity/`:
`index.html`, `index.js`, `unity-loader.js`, `playerweb.json`, `playerweb.data.unityweb`,
`playerweb.wasm.code.unityweb`, `playerweb.wasm.framework.unityweb`.

Espelho em CDN (útil para fixar versão):
`https://cdn.jsdelivr.net/gh/spbgovbr-vlibras/vlibras-portal@v7.12.2/app/unity/...`

Vantagens de hospedar: funciona offline, não quebra se o gov mudar a URL, carrega mais rápido
em LAN. Desvantagem: você congela a versão e perde correções. **Recomendação:** use o remoto
no desenvolvimento, espelhe antes de qualquer demo que não possa falhar.

## Alternativa: o widget oficial (atalho)

Se não quiser gerenciar o iframe, o widget v7 expõe uma API global depois de aberto:

```html
<script src="https://vlibras.gov.br/app/vlibras-plugin.js"></script>
<script>
  new window.VLibras.Widget({ avatar: 'icaro', position: 'R' });
</script>
```

Depois de carregado, existe `window.vlibras` com:
`translate(text)`, `translateAndPlay(text)`, `play(gloss)`, `playStatic(gloss, baseUrl?)`,
`pause()`, `stop()`, `repeat()`, `setSpeed(n)`, `setEmotion(nome, intensidade)`,
`setRegion(r)`, `setSubtitleColor({color,outline,shadow})`, `toggleAvatar(nome)`,
`toggleSubtitles()`, `send(object, method, params)`, `setConfig({baseUrl, personalizationUrl})`.

Emoções válidas: `default, happy, sad, angry, disgust, fear, surprise, upset`.

**Por que eu não recomendo para este projeto:** o widget traz botão flutuante, menu,
dicionário, telemetria PostHog e um layout que não é nosso — e o usuário precisa *clicar*
para abrir. Para um chat onde o avatar é o protagonista, o iframe cru dá controle total.
Mas é um ótimo plano B e uma referência viva da API.
