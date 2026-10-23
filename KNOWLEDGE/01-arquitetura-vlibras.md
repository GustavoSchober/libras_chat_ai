# 01 — Arquitetura da suíte VLibras

Destilado dos 4 PDFs em `how_to_act/` + leitura dos repositórios `spbgovbr-vlibras/*`.

> `how_to_act/` fica **fora do Git** (material de terceiros, já destilado aqui).
> Ver [FONTES.md](FONTES.md).

## Quem é quem

A suíte VLibras é do **LAViD/UFPB** em parceria com a Secretaria de Governo Digital.
Licença **LGPLv3** em todos os repos — podemos usar, modificar e distribuir, desde que
alterações na própria biblioteca voltem como LGPL. Nosso app por cima é nosso.

| Peça | O que faz | Nos interessa? |
|---|---|---|
| **Translator API** | REST Node/Express. Recebe PT, devolve glosa. Fila RabbitMQ + MongoDB (cache/estatística) + Redis | **Sim, central** |
| **Translator Text Core** | Worker Python que faz a tradução de verdade (regras + rede neural) | **Sim** — dá para rodar local |
| **Player (Unity WebGL)** | O boneco 3D. Recebe glosa, baixa as animações, sinaliza | **Sim, central** |
| **player-webjs** | Lib JS que faz ponte com o Unity (versão antiga, v5) | Referência |
| **web-browsers / portal** | Widget e plugin de navegador (v7 atual) | Referência de API |
| **Dicionário / Repositório** | Servidor dos *bundles* (arquivos de animação) | **Sim, central** |
| **WikiLibras** | Plataforma colaborativa onde humanos animam sinais novos | Contexto ([07](07-wikilibras-e-rig-3d.md)) |
| **Console** | Painel de gestão (Grafana, k8s, treino de IA). Login Único gov.br | Não (interno do gov) |
| **Cross Platform App** | App Ionic/React iOS+Android | Não |
| **Libraskê** | Worker Python de processamento | Não |
| **VLibras Vídeo** | Gera MP4 do avatar sinalizando | Talvez (export) |

### Os PDFs em `how_to_act/` — veredito

São **DEV Guides de 2021** (Console, Cross Platform App, Plugin/Widget, WikiLibras). Úteis
para entender *conceito e fluxo*, mas **as instruções de instalação estão obsoletas**
(Ubuntu 18.04, Node 10/12, MongoDB 4.2, Ionic 5, widget "versão 5.2.0"). O widget hoje
está na **v7.12.2** com arquitetura diferente (iframe + postMessage em vez de SendMessage
direto). Trate os PDFs como história, não como manual.

O PDF que ainda vale ouro é o **Plugin/Widget**, porque descreve o fluxo conceitual que
continua verdadeiro:

> 1. usuário seleciona texto → 2. POST na API de tradução para obter glosa →
> 3. envia a glosa ao Player Unity → 4. o player busca cada palavra no repositório de sinais
> (BUNDLES); **se não encontrar, o avatar apenas soletra a palavra** →
> 5. o player devolve um contador de quantos sinais já foram reproduzidos.

Esse passo 4.1 ("apenas soletra") é a origem do nosso maior risco de qualidade — ver [10](10-desafios-e-duvidas.md).

## O fluxo real, em produção, hoje ✅

```
                 ┌──────────────────────────── seu app ────────────────────────────┐
                 │                                                                 │
   texto PT ─────┼──► POST https://traducao2.vlibras.gov.br/translate              │
                 │         │                                                       │
                 │         └──► "RATO ROEDOR ROUPA REI ROMA"  (text/plain)         │
                 │                        │                                        │
                 │                        ▼                                        │
                 │     iframe  https://vlibras.gov.br/app/unity/index.html         │
                 │         postMessage {type:'unity',                              │
                 │            object:'PlayerManager', method:'playNow',            │
                 │            params:'RATO ROEDOR ROUPA REI ROMA'}                 │
                 │                        │                                        │
                 └────────────────────────┼────────────────────────────────────────┘
                                          ▼
                     GET dicionario2.vlibras.gov.br/static/BUNDLES/
                         2018.3.1/WEBGL/BR/RATO      (AssetBundle Unity, ~32 KB)
                                          │
                                          ▼
                              avatar executa o sinal
                              ◄── evento counter_gloss [n, total]
```

Por dentro da API de tradução (não precisamos reproduzir, mas explica os sintomas):

```
Express  ──► cache Redis ──► fila RabbitMQ "translate.to_text" ──► worker Python
                                                                      │
                                              vlibras-translate (regras: Aelius POS,
                                              CFG NLTK, léxico, lematização)
                                                                      │
                                              vlibras-deeplearning (fairseq LightConv,
                                              BPE subword-nmt) — se ENABLE_DL_TRANSLATION
                                                                      │
                                              [opcional, novo em 2026]
                                              refinamento por LLM (OpenAI/Ollama)
```

**Consequência prática:** a API é assíncrona por dentro. Se o worker Python cai, o Express
continua de pé e devolve `500 {"error":"Translation Core Unavailable"}`. Vimos isso acontecer
e voltar sozinho duas vezes durante a apuração. Trate como **instabilidade normal** e tenha
fallback — ver [02](02-api-traducao.md).

## Novidade de 2026 que importa muito para nós

O `vlibras-translator-text-core` v2.5.0 ganhou **refinamento de glosa por LLM**:

```yaml
ENABLE_DL_TRANSLATION: "false"   # liga/desliga a rede neural
ENABLE_REFINEMENT: "false"       # liga o refinador por LLM
REFINEMENT_QUEUE: "refine.to_text"
LLM_PROVIDER: "openai"           # aceita "openai" ou "ollama"
LLM_MODEL: "gpt-4o"
LLM_API_KEY: "changeme"
LLM_BASE_URL: "https://api.openai.com/v1"
```

Ou seja: **o próprio governo já concluiu que um LLM em cima da glosa melhora o resultado.**
Isso valida a tese do nosso projeto e nos dá um ponto de extensão legítimo. O endpoint
`/dl/translate` (que seria a rota neural/refinada) existe em produção mas responde
`401 Unauthorized` — é privado. Nós fazemos a nossa própria camada.

## Links (para auditoria, não para rotina)

- Repos: `https://github.com/spbgovbr-vlibras/` — `vlibras-translator-api`, `vlibras-translator-text-core`, `vlibras-player-webjs`, `vlibras-web-browsers`, `vlibras-portal`, `libraske-processor`
- Doc widget: `https://vlibras.gov.br/doc/widget/installation/webpageintegration.html`
- Doc desktop Linux: `https://vlibras.gov.br/doc/linux/index.html`
- Portal: `https://www.gov.br/governodigital/pt-br/acessibilidade-e-usuario/vlibras`
