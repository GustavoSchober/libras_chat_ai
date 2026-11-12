# Base de conhecimento — LIBRAS AI CHAT

> Objetivo desta pasta: **substituir a consulta aos sites**. Tudo que foi lido em PDFs,
> repositórios, docs oficiais e **testado ao vivo** está destilado aqui. Abrir browser é caro;
> ler estes `.md` é barato. Os links continuam no fim de cada arquivo para auditoria.

Data da apuração: **2026-10-22**; camada de IA apurada em **2026-10-29** ([13](13-camada-de-ia-jev.md)).
Tudo marcado com ✅ foi **verificado executando**, não lido.

## Índice

| Arquivo | O que responde |
|---|---|
| [01-arquitetura-vlibras.md](01-arquitetura-vlibras.md) | O que é cada peça da suíte VLibras e como elas se encaixam |
| [02-api-traducao.md](02-api-traducao.md) | Endpoints de tradução PT→Glosa, contratos, rate limit, CORS, falhas |
| [03-player-3d.md](03-player-3d.md) | Como embutir e **comandar o boneco 3D** (contrato postMessage completo) |
| [04-dicionario-e-bundles.md](04-dicionario-e-bundles.md) | As 24.213 glosas que o avatar sabe fazer; datilologia; verbos direcionais |
| [05-glosa-a-linguagem.md](05-glosa-a-linguagem.md) | A sintaxe da glosa: `&`, `_`, `[PONTO]`, `(+)`, `1S_X_3S` |
| [06-dataset-vlibrasil.md](06-dataset-vlibrasil.md) | Seu dataset no HF: o que tem, o que falta, API do dataset-viewer |
| [07-wikilibras-e-rig-3d.md](07-wikilibras-e-rig-3d.md) | O `padrao.blend`, os ossos do rig, como nascem sinais novos |
| [08-traducao-offline.md](08-traducao-offline.md) | Rodar o tradutor (regras + rede neural fairseq) **sem internet** |
| [09-projeto-arquitetura.md](09-projeto-arquitetura.md) | A proposta de arquitetura para o LIBRAS AI CHAT |
| [10-desafios-e-duvidas.md](10-desafios-e-duvidas.md) | Problemas que vamos enfrentar, já respondidos antes de aparecerem |
| [11-conjugacao-verbal-e-o-teto-das-regras.md](11-conjugacao-verbal-e-o-teto-das-regras.md) | **Onde o tradutor sem IA trava** — medido verbo a verbo; o que dá e o que não dá para consertar com código |
| [12-rag-ou-indice.md](12-rag-ou-indice.md) | **Precisamos de RAG?** O acervo já é um léxico estruturado; o que resolver com índice e o que exige IA |
| [13-camada-de-ia-jev.md](13-camada-de-ia-jev.md) | **O modelo escolhido: Jev (TypeSafe).** Por que ele não gera texto, como isso redesenha a camada 2, preço, limites, defeitos conhecidos — e o resultado: **40/40 em português** com descrição estruturada (Parte 10, 2026-11-09) |
| [14-auditoria-de-glosa.md](14-auditoria-de-glosa.md) | **Auditoria em massa** com 20 mil frases do Tatoeba: como rodar, o que foi corrigido (12 padrões) e o **backlog aberto** (2026-11-11) |
| [FONTES.md](FONTES.md) | Todos os links, o material que ficou fora do Git e as licenças |

## O resumo de uma página

O projeto é: **digito uma frase → o boneco 3D me ensina a sinalizá-la, e se eu mudar a frase ele se adapta.**

O caminho completo, provado ponta a ponta:

```
texto PT  ──► tradutor (regras + NMT)  ──► GLOSA  ──► player Unity WebGL ──► sinais
  "o rato roeu a roupa       POST /translate      "RATO ROEDOR ROUPA      postMessage
   do rei de roma"                                 REI ROMA"              playNow
```

As três descobertas que mudam o projeto:

1. **Dá para pular o tradutor.** O player aceita glosa pronta via `playNow`. Logo, uma IA
   nossa pode gerar a glosa e mandar direto. O tradutor do governo vira *baseline*, não dependência.
2. **O player é auto-contido e embutível de qualquer origem** (CORS liberado, sem X-Frame-Options).
   ~20 MB de download único + ~32 KB por sinal.
3. **O tradutor inteiro é instalável via pip** (`vlibras-translate` + `vlibras-deeplearning`),
   e os pesos do modelo neural estão num git público. Dá para rodar tudo offline.

E os dois alertas mais importantes:

- **Valide a glosa contra a lista de bundles antes de tocar.** Um token sem bundle não dá
  erro — vira datilologia literal e arrasta a animação. Ver [04](04-dicionario-e-bundles.md).
- **Mas validar não basta.** Existe uma classe de erro em que o tradutor produz um sinal
  *que existe* e *está errado* ("eu pus o livro" → o sinal de **pus**, a secreção). O código
  não tem como perceber. Essa é a fronteira exata onde a IA deixa de ser opcional —
  ver [11](11-conjugacao-verbal-e-o-teto-das-regras.md).

E a decisão de 2026-10-29, que redesenha a camada 2: **o modelo é o Jev (TypeSafe), e ele não
gera texto.** A glosa passa a ser *montada pelo nosso código* a partir de decisões típadas
(`Choice`/`Score`/`Noul`), e as explicações vêm de um catálogo escrito por humano que o Jev
apenas seleciona. Custo: US$ 0,000043 por frase, 114 ms, `confidence` calibrada em toda
resposta. Único risco em aberto: a precisão em português, que custa **US$ 0,0017** para ser
medida. Tudo em [13](13-camada-de-ia-jev.md).
