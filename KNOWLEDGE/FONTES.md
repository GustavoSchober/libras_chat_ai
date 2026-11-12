# Fontes

Tudo que foi lido para montar esta base de conhecimento. Os arquivos pesados e de
terceiros ficam **fora do Git** (ver `.gitignore`) — este arquivo garante que nada se perca.

## O que está fora do repositório, e onde encontrar de novo

### `how_to_act/` — material de origem

Quatro DEV Guides do VLibras (fev/2021 e out/2021), exportados do Google Docs pelo LAViD/UFPB.
Copyright de terceiros; todo o conteúdo útil está destilado em `01-arquitetura-vlibras.md`.

| Arquivo | Conteúdo | Ainda vale? |
|---|---|---|
| `Dev_VLibras_Plugin_Widget.pdf` | fluxo texto → glosa → player, arquitetura Unity | **sim**, o fluxo conceitual continua verdadeiro |
| `Doc_VLibras_Wikilibras.pdf` | plataforma colaborativa de criação de sinais | sim, como contexto |
| `Dev_VLibras_Console.pdf` | painel interno do governo (Grafana, k8s, Login Único) | não, é interno |
| `Dev_VLibras_CrossPlatform_App.pdf` | app Ionic/React iOS+Android | não |

⚠️ As instruções de instalação desses PDFs estão **obsoletas** (Ubuntu 18.04, Node 10/12,
MongoDB 4.2, widget "5.2.0" — hoje é v7.12.2 com arquitetura diferente). Trate como história.

Contatos que constam nos documentos: `suanny@lavid.ufpb.br`, `marcos.alves@lavid.ufpb.br`.

### `3dchar/BLENDER_PADRAO_VLIBRAS.zip` — rig 3D

`padrao.blend`, 5,87 MB descompactado, Blender 2.76 (2015). Rig padrão do WikiLibras.
Anatomia completa (~60 ossos) documentada em `07-wikilibras-e-rig-3d.md` — inclusive a lista
de ossos, para não precisar reabrir o arquivo.

---

## Links originais

### VLibras — repositórios

- https://github.com/spbgovbr-vlibras/vlibras-translator-api — API REST de tradução
- https://github.com/spbgovbr-vlibras/vlibras-translator-text-core — worker Python (regras + NMT + LLM)
- https://github.com/spbgovbr-vlibras/vlibras-player-webjs — ponte JS ↔ Unity (v5, referência)
- https://github.com/spbgovbr-vlibras/vlibras-web-browsers — widget e plugin
- https://github.com/spbgovbr-vlibras/vlibras-portal — **player Unity atual** (`app/unity/`)
- https://github.com/spbgovbr-vlibras/libraske-processor

### VLibras — documentação oficial

- https://www.gov.br/governodigital/pt-br/acessibilidade-e-usuario/vlibras
- https://vlibras.gov.br/doc/widget/installation/webpageintegration.html
- https://vlibras.gov.br/doc/linux/index.html

### VLibras — endpoints em produção

| Serviço | URL |
|---|---|
| Tradução | `https://traducao2.vlibras.gov.br/translate` · `-dth` para homologação |
| Review | `https://traducao2.vlibras.gov.br/review` |
| Lista de sinais | `https://dicionario2.vlibras.gov.br/bundles` |
| Trie de sinais | `https://dicionario2.vlibras.gov.br/static/TREES/2018.3.1.json` |
| Bundle de um sinal | `https://dicionario2.vlibras.gov.br/static/BUNDLES/2018.3.1/WEBGL/BR/{GLOSA}` |
| Player Unity | `https://vlibras.gov.br/app/unity/index.html` |
| Widget | `https://vlibras.gov.br/app/vlibras-plugin.js` |
| Espelho fixado | `https://cdn.jsdelivr.net/gh/spbgovbr-vlibras/vlibras-portal@v7.12.2/app/` |

### Tradutor instalável (TestPyPI — as versões do PyPI oficial estão defasadas)

- `vlibras-translate==1.3.4rc1` · `vlibras-deeplearning==1.4.1rc1`
- Pesos do modelo neural: `https://gitlab.lavid.ufpb.br/vlibras-deeplearning/models.git` (tag `v1.4-LATEST`, git LFS)

### Hugging Face

- https://huggingface.co/datasets/SchberGg/v-librasil-raw — o dataset do projeto
- https://huggingface.co/docs/dataset-viewer/index — API do dataset-viewer
- https://huggingface.co/docs/hub/datasets-viewer-embed — embutir o viewer
- https://huggingface.co/docs/hub/index — docs do Hub

### Jev (TypeSafe) e corpus da auditoria

- https://docs.typesafe.ai — documentação do Jev (índice em https://docs.typesafe.ai/llms.txt); resumo em [13](13-camada-de-ia-jev.md)
- https://downloads.tatoeba.org/exports/per_language/por/ — frases em português do Tatoeba (CC-BY 2.0 FR), usadas na auditoria ([14](14-auditoria-de-glosa.md))

---

## Licenças — confirmar antes de qualquer uso comercial

| Ativo | Licença | Observação |
|---|---|---|
| Repositórios VLibras | **LGPLv3** | nosso app por cima é nosso; alterações na lib deles voltam como LGPL |
| Avatares e bundles | do Governo Federal | consumir via API pública é o uso pretendido; **redistribuir é outra conversa** |
| `padrao.blend` | não declarada | veio do pacote do WikiLibras |
| V-LIBRASIL | **não declarada no HF** | o dataset está sem campo `license` — convém declarar |
