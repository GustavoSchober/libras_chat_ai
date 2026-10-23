# 06 — Seu dataset: `SchberGg/v-librasil-raw`

Tudo apurado via API do Hugging Face em 2026-10-22 ✅.

## O que tem lá

| Propriedade | Valor |
|---|---|
| Tipo | `videofolder` (builder automático do `datasets`) |
| Split | só `train` |
| Linhas | **4.086** |
| Colunas | **1** — `video` (`{"_type":"Video"}`) |
| Tamanho dos vídeos | **~10,85 GB** |
| Parquet (índice) | 476 KB |
| Sinais distintos | **1.364** |
| Articuladores por sinal | **3** (1.358 sinais têm 3; 6 têm 2) |
| Formato | MP4 |
| Duração | min 1,47 s · **mediana 5,37 s** · média 5,72 s · máx 22,6 s |

Convenção de nome: `videos/{Sinal}_Articulador{1,2,3}.mp4`, ex. `Abacaxi_Articulador1.mp4`,
`Creme dental_Articulador2.mp4`.

Os rótulos vêm em português natural, com capitalização de frase e **parênteses de
desambiguação**: `Acordar (alarme)`, `Garoto (menino)`, `Batida (pancada)`, `Batida (ritmo)`,
`Boxe (esporte)`. Há espaços: `Abrir a porta`, `À noite toda`, `Água congelada`.

Isto é o **V-LIBRASIL** — corpus de vídeos de sinalizadores humanos reais. Não é animação,
não é mocap: são **gravações de pessoas**.

## 🔴 O problema estrutural nº 1

**O dataset não tem coluna de rótulo.** A única coluna é `video`. A glosa existe apenas no
*nome do arquivo*, que o parquet não expõe como campo consultável.

Consequência concreta, confirmada pelo endpoint `/is-valid`:
```json
{"preview":true,"viewer":true,"search":false,"filter":true,"statistics":true}
```
**`search: false`** — não dá para buscar "me dê o vídeo do sinal CASA". É preciso varrer
as linhas e parsear a URL.

### A correção (recomendo fazer cedo)

Suba um `metadata.csv` junto dos vídeos. O builder `videofolder` o detecta automaticamente
e cria as colunas:

```csv
file_name,gloss,gloss_bundle,articulador,tem_bundle
videos/Abacaxi_Articulador1.mp4,Abacaxi,ABACAXI,1,true
videos/Abacaxi_Articulador2.mp4,Abacaxi,ABACAXI,2,true
videos/Abrir a porta_Articulador1.mp4,Abrir a porta,ABRIR_A_PORTA,1,false
```

Ganhos imediatos: busca e filtro funcionam, o viewer fica navegável, e **você pode juntar
o dataset com a lista de bundles do VLibras direto numa query**. Hoje isso é um script;
com metadata vira um `filter`.

## Cruzamento com o acervo do avatar

- **1.030** dos 1.364 sinais batem com um bundle por nome exato (`.upper()`, espaço→`_`)
- **1.095 (80%)** batem ignorando acento e parênteses
- **269 não têm bundle** — o avatar não sabe fazer

Amostra dos 269: `ABRIR_A_PORTA`, `ABRIR_A_JANELA`, `BATER_PAPO`, `AO_REDOR`, `BARCO_A_VELA`,
`CADEIRA_DE_BALANÇO`, `APAGAR_O_QUADRO`, `APAIXONAR-SE`, `ATÉ_AGORA`, `BRONZEAMENTO`,
`ALUNO_DO_SEGUNDO_ANO_DO_ENSINO_MÉDIO`.

Esses 269 são **ativo, não passivo**: são sinais com referência humana em vídeo onde o
avatar é omisso. O app pode cair para o vídeo humano nesses casos — e isso é
*pedagogicamente melhor* que soletrar.

## API do dataset-viewer (tudo testado ✅)

Base: `https://datasets-server.huggingface.co`. Dataset público → **não precisa de token**.
Para datasets privados: `Authorization: Bearer hf_...`.

| Endpoint | Para quê | Testado |
|---|---|---|
| `/is-valid?dataset=D` | descobre quais recursos funcionam | ✅ |
| `/splits?dataset=D` | lista configs e splits | ✅ |
| `/info?dataset=D` | schema, features, nº de linhas | ✅ |
| `/size?dataset=D` | bytes e linhas | ✅ |
| `/statistics?dataset=D&config=&split=` | histogramas por coluna | ✅ (deu as durações) |
| `/first-rows?dataset=D&config=&split=` | primeiras 100 linhas | ✅ |
| `/rows?dataset=D&config=&split=&offset=&length=` | paginação (length ≤ 100) | ✅ |
| `/filter?...&where=` | SQL-ish; exige coluna adequada | ⚠️ 422 aqui (só `video`) |
| `/search?...&query=` | full-text | ❌ `search:false` |
| `/parquet?dataset=D` | URLs dos parquets convertidos | ✅ |
| `/croissant-crumbs?dataset=D` | metadados Croissant/ML Commons | ✅ |

Exemplos prontos:

```bash
D=SchberGg%2Fv-librasil-raw
curl -s "https://datasets-server.huggingface.co/splits?dataset=$D"
curl -s "https://datasets-server.huggingface.co/rows?dataset=$D&config=default&split=train&offset=1000&length=3"
curl -s "https://datasets-server.huggingface.co/statistics?dataset=$D&config=default&split=train"
```

### URLs dos vídeos

As linhas devolvem o link direto, **fixado por commit**:
```
https://huggingface.co/datasets/SchberGg/v-librasil-raw/resolve/
  e6765f43a0c3e454cc5667a7b07b17e0ad113506/videos/Abacaxi_Articulador1.mp4
```
Use `resolve/main/...` se quiser sempre a versão atual. Espaços no nome vêm **percent-encoded**
(`Creme%20dental_...`) — decodifique antes de usar o nome como rótulo.

### Listar os 4.086 arquivos sem baixar nada

A API de árvore do Hub é mais direta que o viewer para isso (paginada via header `Link: rel="next"`):

```bash
curl -s -D h.txt "https://huggingface.co/api/datasets/SchberGg/v-librasil-raw/tree/main/videos?limit=1000"
grep -i '^link:' h.txt   # pega o cursor da próxima página
```

### Embutir o viewer numa página

```html
<iframe src="https://huggingface.co/datasets/SchberGg/v-librasil-raw/embed/viewer/default/train"
        frameborder="0" width="100%" height="560px"></iframe>
```

## Como carregar em Python

```python
from datasets import load_dataset
ds = load_dataset("SchberGg/v-librasil-raw", split="train")   # decodifica vídeo sob demanda
```

Para só os caminhos, sem decodificar (bem mais rápido):
```python
ds = ds.cast_column("video", datasets.Video(decode=False))
```

⚠️ Decodificar vídeo exige `decord`/`torchvision` + ffmpeg; 10,85 GB não cabem na RAM.
Trabalhe em streaming (`streaming=True`) ou por amostragem.

## O que este dataset serve — e o que não serve

**Serve muito bem para:**
- **referência humana** ao lado do avatar ("é assim que uma pessoa faz") — alto valor didático,
- cobrir os 269 sinais que o avatar não tem,
- validar visualmente se a animação do avatar está correta,
- futuramente, treinar reconhecimento (webcam → sinal) para *corrigir* quem está praticando.

**Não serve, hoje, para:**
- gerar animação do avatar diretamente — são pixels, não ossos. Precisaria de pose estimation
  + retargeting para o rig ([07](07-wikilibras-e-rig-3d.md)). É um projeto inteiro, não uma feature.
- treinar tradução PT→glosa — não há texto corrente, só pares sinal↔vídeo.

## Links

- Dataset: `https://huggingface.co/datasets/SchberGg/v-librasil-raw`
- Docs viewer: `https://huggingface.co/docs/dataset-viewer/index`
- Docs embed: `https://huggingface.co/docs/hub/datasets-viewer-embed`
- Docs Hub: `https://huggingface.co/docs/hub/index`
