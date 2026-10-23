# 08 — Rodar o tradutor localmente (sem depender do gov.br)

Descoberta importante: **o tradutor inteiro é instalável via pip**, e os pesos do modelo
neural estão num git público. Dá para ter PT→Glosa offline, sem rate limit e sem o
`500 Translation Core Unavailable`.

## Os dois pacotes

| Pacote | O quê | Dependências |
|---|---|---|
| **`vlibras-translate`** | tradutor de **regras** (RBMT) | `nltk`, `unidecode`, `pygtrie`, `psutil`, `interruptingcow`, `loguru`, `cogroo4py==0.5.1`, `hunspell` (Linux) |
| **`vlibras-deeplearning`** | tradutor **neural** (NMT) | `fairseq==0.12.2`, `subword-nmt==0.3.8`, `torch==2.0.0`, `sacremoses==0.0.53` |

⚠️ **Atenção às origens.** Existem duas publicações:

| Índice | `vlibras-translate` | `vlibras-deeplearning` |
|---|---|---|
| PyPI oficial | **1.1.10** (antigo) | **1.0.9** (antigo) |
| **TestPyPI** | **1.3.4rc1** (atual, usado em produção) | **1.4.1rc1** (atual) |

O `README` do `vlibras-translator-text-core` manda instalar do **TestPyPI**:

```bash
python -m pip install --upgrade \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple \
  vlibras-translate==1.3.4rc1

python -m pip install --upgrade \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple \
  vlibras-deeplearning==1.4.1rc1
```

O `--extra-index-url` é obrigatório: o TestPyPI não tem `torch`, `nltk` etc.

## Requisitos de ambiente

- **Python 3.12** (o README do text-core cita esta versão explicitamente)
- **Linux** — `hunspell` é marcado `platform_system == "Linux"`. No seu Arch, ok.
- `torch==2.0.0` é pesado (~2 GB). Se só quiser a parte de regras, instale **apenas**
  `vlibras-translate` e pule o deeplearning.
- `cogroo4py` precisa de **Java** (o CoGrOO é um analisador gramatical de português em Java).

## O modelo neural

`vlibras_deeplearning` tem só **10 KB** — é um carregador. Os pesos são clonados em runtime:

```
git clone --single-branch --depth 1 --branch v1.4-LATEST \
  https://gitlab.lavid.ufpb.br/vlibras-deeplearning/models.git
```

✅ **Verificado:** o `git-upload-pack` responde **200 sem autenticação**. Tags disponíveis:
`v1.0.9 … v1.4.0, v1.4.1, v1.4-LATEST` (e `v1.1-LATEST`, `v1.2-LATEST`, `v1.3-LATEST`).

Variável de ambiente para fixar versão: `VLIBRAS_DL_MODEL_TAG=v1.4.1`.

O repo usa **git LFS**. Instale antes (`sudo pacman -S git-lfs && git lfs install`).

Arquivos que o carregador espera:
```
model/BIN/dict.gi.txt         ← vocabulário alvo (glosa)
model/BIN/dict.gr.txt         ← vocabulário fonte
model/Checkpoints/checkpoint_best.pt
model/BPE/bpe_code
model/VERSION
```

### Arquitetura do modelo

```python
fairseq.models.lightconv.LightConvModel.from_pretrained(
    'model/Checkpoints', checkpoint_file='checkpoint_best.pt',
    data_name_or_path='model/BIN',
    bpe='subword_nmt', bpe_codes='model/BPE/bpe_code',
    source_lang='gr',    # "gr" = saída do tradutor de regras
    target_lang='gi',    # "gi" = glosa final
)
```

**LightConv** (Wu et al. 2019), seq2seq com convolução dinâmica + BPE. Não é um LLM: é um
tradutor automático neural clássico, pequeno e rápido.

### O detalhe que revela o pipeline

```python
def translate(self, gr):
    tokenized = [g for g in gr
        .replace('[PONTO]', '[PONTO]\n')
        .replace('[INTERROGAÇÃO]', '[INTERROGAÇÃO]\n')
        .replace('[EXCLAMAÇÃO]', '[EXCLAMAÇÃO]\n')
        .split('\n') if g.strip()]
    return ' '.join(self._model.translate(t) for t in tokenized)
```

O modelo **não traduz português cru**. Ele recebe a saída do tradutor de regras (`gr`) e a
refina para glosa (`gi`), **frase a frase**, usando os marcadores de pontuação como
separadores. Confirma a arquitetura em dois estágios:

```
PT  ──[regras: Aelius POS + CFG + léxico + lematização]──►  gr
gr  ──[fairseq LightConv + BPE]──►  gi (glosa final)
gi  ──[opcional, v2.5.0: LLM OpenAI/Ollama]──►  glosa refinada
```

## O que tem dentro do `vlibras-translate` (8,5 MB)

Vale saber, porque explica os erros que medimos:

```
aelius/Aelius/*.py                     ← POS tagger de português (projeto acadêmico)
aelius_tagger.py                       ← ClassificaSentencas
cfg.syn.nltk            (134 KB)       ← gramática livre de contexto NLTK
lemma.py                               ← lematização  ⚠️ fonte do "roeu→ROEDOR"
word_processing.py, char_preprocessing.py
number.py, ConverteExtenso.py, dExtenso.py   ← números por extenso
palavras_compostas_e_sinonimos (65 KB) ← origem dos BOM_DIA / COMPRAR&DINHEIRO
pronome_obliquo_atono   (25 KB)        ← origem dos 1S_AJUDAR_2S
pygtrie_CharTrie_names_pickle... (1 MB)← trie de nomes próprios
lugares.csv, famosos.csv, abreviaturas
orthography.py, name_checking.py, postprocessing.py
```

Classe principal: `vlibras_translate.translation.Translation`, com atributos de saída
`rbmt_glosa` (regras) e `nmt_glosa` (neural) — dá para **comparar os dois lado a lado**,
o que é ouro para avaliar a nossa IA.

## Vale a pena rodar local?

| | API remota | Local |
|---|---|---|
| Setup | zero | pesado (Java, torch 2 GB, LFS, Python 3.12) |
| Latência | ~0,4 s ✅ | mais rápido depois de carregado |
| Rate limit | 300/janela | nenhum |
| Disponibilidade | ⚠️ cai e volta | total |
| Tradução neural | ❌ `/dl/` é 401 | ✅ disponível |
| Ver `rbmt` vs `nmt` | ❌ | ✅ |

**Recomendação:**
- **Para o app:** use a API remota com fallback entre prod e dth ([02](02-api-traducao.md)).
  Simples e suficiente.
- **Para trabalho em lote** (pré-traduzir frases didáticas, montar dataset de avaliação,
  comparar com a nossa IA): instale local. Os 300/janela viram problema rápido, e ter
  `rbmt_glosa` e `nmt_glosa` separados permite medir de verdade onde o LLM ajuda.

## Receita de instalação local

```bash
# pré-requisitos do sistema (Arch)
sudo pacman -S --needed jdk-openjdk hunspell hunspell-pt-br git-lfs
git lfs install

python3.12 -m venv .venv && source .venv/bin/activate

pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple \
            "vlibras-translate==1.3.4rc1"

# opcional: tradução neural (baixa ~2 GB de torch + pesos via LFS)
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple \
            "vlibras-deeplearning==1.4.1rc1"

python -c "import nltk; nltk.download('punkt')"
```

Na primeira chamada do tradutor neural, o `prepare_model()` clona o repo de pesos sozinho.

## Subir a API completa com Docker (alternativa)

O `vlibras-translator-text-core` tem `docker-compose.yml`. Variáveis relevantes:

```yaml
AMQP_HOST: rabbitmq
TRANSLATOR_QUEUE: "translate.to_text"
ENABLE_DL_TRANSLATION: "false"    # true = usa a rede neural
ENABLE_REFINEMENT: "false"        # true = refina com LLM
REFINEMENT_QUEUE: "refine.to_text"
LLM_PROVIDER: "openai"            # aceita "openai" ou "ollama"
LLM_MODEL: "gpt-4o"
LLM_API_KEY: "changeme"
LLM_BASE_URL: "https://api.openai.com/v1"
```

`LLM_BASE_URL` sendo configurável significa que **qualquer API compatível com OpenAI serve** —
inclusive a da Anthropic via proxy, ou um Ollama local. Se quisermos um dia encaixar nossa
IA *dentro* do pipeline oficial em vez de por fora, o ponto de extensão está pronto.

Mas repare: subir isso é RabbitMQ + worker + API Node + Mongo + Redis. **Para o nosso
projeto, chamar `Translation()` direto do Python é muito mais simples.**
