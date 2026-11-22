# 15 — Fase 2: o aluno sinaliza para a câmera e o sistema corrige

> **Documento vivo.** Começou em **2026-11-12**. Junta tudo que foi pedido, estudado, medido e
> decidido sobre a fase 2. É o plano de partida, não um contrato: o projeto **pode e vai mudar**
> conforme as coisas forem sendo construídas e medidas. Toda mudança entra no
> [histórico](#18-histórico-de-mudanças) com a data e o motivo, de preferência com número.
>
> Convenção da base: ✅ = **verificado executando**; ⚠️ = lido em fonte, ainda não conferido por nós.

## Sumário

1. [O pedido](#1-o-pedido)
2. [Decisões tomadas](#2-decisões-tomadas)
3. [Conceitos de base](#3-conceitos-de-base)
4. [Ferramentas estudadas](#4-ferramentas-estudadas)
5. [Datasets](#5-datasets)
6. [Modelos e trabalhos acadêmicos](#6-modelos-e-trabalhos-acadêmicos)
7. [O experimento de 12/11 (baseline com DTW)](#7-o-experimento-de-1211-baseline-com-dtw)
8. [Arquitetura](#8-arquitetura)
9. [O verificador aprendido](#9-o-verificador-aprendido)
10. [O diagnóstico pelos parâmetros da Libras](#10-o-diagnóstico-pelos-parâmetros-da-libras)
11. [Segmentação: do guiado para o corrido](#11-segmentação-do-guiado-para-o-corrido)
12. [Variantes e ordem dos sinais](#12-variantes-e-ordem-dos-sinais)
13. [A aba Praticar (interface)](#13-a-aba-praticar-interface)
14. [Hardware e custos](#14-hardware-e-custos)
15. [Questões legais](#15-questões-legais)
16. [Etapas](#16-etapas)
17. [Riscos e perguntas abertas](#17-riscos-e-perguntas-abertas)
18. [Histórico de mudanças](#18-histórico-de-mudanças)
19. [Links](#19-links)

---

## 1. O pedido

O que o Gustavo descreveu em 12/11 (resumido, sem perder nada):

**Interface**
- A fase 2 fica numa **aba nova**, acessada pelo **topo da página**.
- O topo fica **mais escuro, com efeito de vidro preto fosco** por cima (onde hoje estão
  "Libras AI Chat", "IA ligada" e o botão claro/escuro).
- Um **botão novo** no topo, antes de "IA ligada", com **hover azul** (escuro no tema escuro,
  claro no claro).
- O design fino da aba fica para depois.

**Funcionamento**
- A **câmera** do usuário fica centralizada, ocupando a maior parte da tela.
- Ao lado, o **chat de IA**, bem menor que na aba 1, com o **avatar 3D acima** dele.
- O chat mostra uma **frase curta** e o usuário tenta sinalizá-la.
- Usar biblioteca de hand tracking / gesture recognition / SLR / SLT; a sugestão é o **MediaPipe**
  (Holistic, Hand e Face Landmarker). OpenPose, MMPose e OpenCV citados como alternativas.
- **Cuidado com o Gesture Recognizer** do MediaPipe: os gestos prontos dele não são Libras.
- O **Jev** entraria para reconhecer e categorizar sinais contra o acervo de Libras, via memória
  (RAG) ou API. O objetivo é ficar **o mais verossímil possível e barato**.
- Indicou o dataset acadêmico **LIBRAS-EQT-UECE** (Zenodo), e sugeriu Hugging Face e PyTorch.

**O exemplo que define o produto**

```
FRASE PROPOSTA   Vou comprar abacaxi amanhã.
SUA EXECUÇÃO     Reconhecimento parcial
  Sinal 1: correto
  Sinal 2: correto
  Sinal 3: configuração da mão incorreta
  Sinal 4: movimento não identificado
ORIENTAÇÃO DA IA "Você executou corretamente os dois primeiros sinais. No terceiro, observe a
                  posição do polegar e a orientação da palma. Tente novamente."
                  → o avatar faz o sinal correto
```

**Princípios pedidos**
- Aviso para quem acessa: **"Libras não é português representado por gestos. A ordem dos sinais
  e a estrutura gramatical podem ser diferentes da frase em português."**
- Comparar a execução com uma **referência em Libras**, não exigir tradução palavra por palavra.
- **Permitir variantes legítimas** de sinalização.
- **Não ensinar Libras errado.**
- Ter uma **arquitetura bem definida** antes de construir, sem "sair na louca".

---

## 2. Decisões tomadas

| # | Decisão | Por quê | Quem / quando |
|---|---|---|---|
| D1 | É **verificação** do sinal esperado, não reconhecimento aberto | o sistema sabe qual sinal espera em cada posição; perguntar "é COMPRAR?" é muito mais fácil e confiável que "qual dos 24 mil é este?" | proposta 12/11 |
| D2 | Toda a visão roda **no navegador** | privacidade (o vídeo nunca sai do computador do aluno) e custo zero de servidor | proposta 12/11 |
| D3 | **Gesture Recognizer fora** | gestos de interface americanos, não Libras; usamos só os pontos | alerta do Gustavo, confirmado no estudo |
| D4 | O **Jev não vê vídeo**: escolhe a orientação num catálogo | o Jev só escolhe entre opções ([13](13-camada-de-ia-jev.md)) | proposta 12/11 |
| D5 | **Sem RAG**: as referências são indexadas pela glosa | mesma conclusão do [12](12-rag-ou-indice.md) | proposta 12/11 |
| D6 | A referência é a **glosa em Libras**, com **várias referências por sinal** e **mão dominante espelhada** | variantes legítimas; medido que espelhar ajuda (seção 7) | proposta 12/11 |
| D7 | Na dúvida: **"não consegui avaliar"**, nunca "errado" | errar a correção ensina errado | proposta 12/11 |
| D8 | "Certo/errado" só aparece com **EER ≤ 10%** medido | o baseline sem treino erra 27% (seção 7) | proposta 12/11 |
| D9 | **Ordem diferente da glosa: aceita, só avisando** | Libras admite mais de uma ordem | **Gustavo, 12/11** |
| D10 | **Foco primeiro no reconhecimento pela câmera**; as "lições" (frases propostas, roteiro) vêm depois | sem reconhecimento confiável, lição não tem base | **Gustavo, 12/11** |
| D11 | Treino começa na **CPU**; driver NVIDIA só se a CPU não der conta | a GPU hoje está no driver livre e não roda CUDA (seção 14) | proposta 12/11, a confirmar |

---

## 3. Conceitos de base

| Termo | O que é |
|---|---|
| **Landmarks** | pontos do corpo estimados em cada quadro do vídeo (pulso, juntas dos dedos, ombros, rosto) com coordenadas x, y, z |
| **Holistic** | o modelo do MediaPipe que estima pose, as duas mãos e o rosto juntos |
| **Blendshapes** | 52 números (0 a 1) que descrevem a expressão do rosto (sobrancelha erguida, boca aberta…). Em Libras a expressão facial é gramática |
| **ISLR / CSLR / SLT** | reconhecimento de sinal isolado / reconhecimento contínuo (frase) / tradução de língua de sinais para texto. A fase 2 começa em ISLR, na forma de verificação |
| **Verificação × reconhecimento** | verificação: "este trecho é o sinal X?" (sabemos o X). Reconhecimento: "qual sinal é este?" |
| **DTW** (*Dynamic Time Warping*) | compara duas sequências de tempos diferentes alinhando-as de forma elástica (a pessoa pode sinalizar mais rápido ou mais devagar) |
| **Aprendizado métrico** | treinar um modelo para transformar cada sinal num vetor em que sinais iguais ficam perto e diferentes ficam longe. Glosa nova entra só com referências, sem retreinar |
| **top-1 / top-3** | o sinal certo é o mais parecido / está entre os 3 mais parecidos |
| **AUC** | probabilidade de a execução certa parecer mais próxima que uma errada (0,5 = chute, 1 = perfeito) |
| **EER** | taxa de erro no limiar em que "aceitar errado" e "rejeitar certo" se igualam. É o número que decide se o tutor pode dizer "certo/errado" |
| **Os 5 parâmetros da Libras** | configuração de mão (CM), ponto de articulação (PA), movimento (M), orientação da palma (Or), expressões não manuais (ENM) |
| **Glosa** | a escrita dos sinais em maiúsculas, na ordem de Libras ([05](05-glosa-a-linguagem.md)) |

---

## 4. Ferramentas estudadas

### 4.1 MediaPipe (escolhido) ✅

Pacote web: `@mediapipe/tasks-vision`. Conferido **dentro do pacote** (versão 1.2.3) que existem as
classes `HolisticLandmarker`, `HandLandmarker`, `FaceLandmarker`, `PoseLandmarker` e
`GestureRecognizer` ✅. Plataformas segundo a doc: Python, Android, **Web**, iOS ⚠️.

| Tarefa | Saída | Uso aqui |
|---|---|---|
| **Holistic Landmarker** | pose 33 pontos, mãos 21+21 (imagem e 3D "mundo"), rosto 478, **52 blendshapes** opcionais, máscara opcional | **o principal** |
| Hand Landmarker | 21 pontos por mão, mão esquerda/direita | plano B, se o holístico pesar demais |
| Face Landmarker | 478 pontos + 52 blendshapes | plano B para as expressões |
| Pose Landmarker | 33 pontos | plano B para o corpo |
| Gesture Recognizer | 7 gestos prontos + classificador personalizável | **não usar** (D3) |

Detalhes que importam:
- Na **web**, o holístico só tem os modos `IMAGE` e `VIDEO`, **sem `LIVE_STREAM`**: a câmera ao vivo
  é feita com `runningMode: "VIDEO"` + `requestAnimationFrame` ⚠️.
- Tamanhos medidos ✅: wasm **14,7 MB** (`vision_wasm_internal.wasm`); modelo
  `holistic_landmarker.task` **13,7 MB**; `hand_landmarker.task` 7,8 MB. São downloads da 1ª
  visita: servir com cache longo, como o jsDelivr faz com o avatar ([03](03-player-3d.md)).
- **Fixar uma versão publicada há pelo menos 2 semanas** (a 1.2.3 teve metadado alterado no
  próprio dia 12/11). **Fixada em 13/11: `@mediapipe/tasks-vision@1.2.0`** (publicada em 27/10;
  a 1.2.3 é de 11/11). O wasm vem do jsDelivr com a mesma versão e o modelo de
  `holistic_landmarker/float16/1/` (versão fixa, não `latest`). O `mediapipe` Python também tem a
  1.2.0: **a extração da E2 tem que usar `mediapipe==1.2.0`**. O spike de 12/11 usou a 1.2.3; o
  `.venv-visao` não existe mais no disco.
- Em Python ✅: `mediapipe` 1.2.3 instala no Python 3.12 (não no 3.14 do sistema), com
  `HolisticLandmarker` em `mediapipe.tasks.python.vision`.

### 4.2 Gesture Recognizer: por que não

Os 7 gestos prontos (punho fechado, mão aberta, indicador para cima, joinha para cima e para baixo,
"paz", "I love you") são gestos de interface de origem americana. Alguns coincidem com
configurações de mão de Libras, mas reconhecer por coincidência ensinaria errado. O classificador
personalizável dele classifica **uma pose de mão parada**: um sinal de Libras tem movimento,
locação, orientação e expressão. Ficamos só com os **pontos** e fazemos a comparação nós mesmos.

### 4.3 Alternativas citadas

| Ferramenta | O que é | Por que não agora |
|---|---|---|
| **OpenPose** (CMU) | estimador de pose clássico | pesado, pensado para GPU no servidor; **licença acadêmica/não comercial** |
| **MMPose** (OpenMMLab) | caixa de ferramentas de pose (RTMPose etc.), Apache-2.0 | ótimo para pesquisa em Python; levar ao navegador exige exportar para ONNX e montar o pipeline à mão. Fica como **plano B de qualidade** se o MediaPipe falhar em mãos |
| **OpenCV** | biblioteca de imagem/vídeo, não estima pose | só serviria para ler vídeo, e **falhou** nisso (quadros pretos, seção 7) |

### 4.4 Para rodar o modelo no navegador: ONNX Runtime Web

O verificador (seção 9) é treinado em PyTorch e exportado para **ONNX**. No navegador roda com
`onnxruntime-web`: **WebGPU** quando existir (importando de `onnxruntime-web/webgpu`; a doc chama de
experimental ⚠️) e **WASM** (CPU) como reserva. Um modelo de 1–5 MB roda bem em WASM.

### 4.5 PyTorch e Hugging Face

- **PyTorch**: treino do verificador (seção 9) e exportação para ONNX.
- **Hugging Face**: o Gustavo já tem conta (`SchberGg`). Serve para hospedar as **referências**
  (landmarks por glosa) e o **modelo** com versão; e o espelho do V-LIBRASIL já está lá
  ([06](06-dataset-vlibrasil.md); ver as questões legais na seção 15).

### 4.6 O Jev

Não vê vídeo: só escolhe entre opções ([13](13-camada-de-ia-jev.md)). Na fase 2 ele recebe o
**diagnóstico estruturado** (por sinal: certo / dúvida / qual parâmetro desviou) e escolhe a
orientação num **catálogo escrito por humano**, mais o que mostrar em seguida (ex.: "repetir só o
sinal 3 devagar"). Custo: da ordem de **US$ 0,0001 por tentativa**, como uma glosa da fase 1.

---

## 5. Datasets

| Dataset | Língua | Conteúdo | Licença | Papel aqui |
|---|---|---|---|---|
| **V-LIBRASIL** (nosso espelho no HF) | Libras | **1.364 sinais × 3 pessoas** = 4.086 vídeos, 1080p/720p, fundo preto, 30 fps ✅; 1.095 têm sinal no avatar ([06](06-dataset-vlibrasil.md)) | **não declarada** (seção 15) | **referência principal** |
| **LIBRAS-EQT-UECE** (Zenodo, jun/2026) | Libras | **178 classes** (sinais e frases) de atendimento de energia elétrica ("A luz caiu", "Eu já paguei"), **5 informantes**, ~6 repetições ✅ (5.347 vídeos; 10.682 `.npy` de landmarks de mão) | **CC-BY 4.0** ✅ | treino e validação (variação dentro da classe, várias repetições) |
| **MINDS-Libras** (Zenodo) | Libras | **20 sinais × 12 pessoas × 5 repetições** (~1.155 vídeos), escolhidos pelos parâmetros fonológicos; versão RGB-D à parte | **CC-BY 4.0** ✅ | validação com muitas pessoas |
| **LIBRAS-HC-RGBDS** | Libras | as **61 configurações de mão**, 5 pessoas, Kinect ⚠️ | a localizar | futuro classificador de CM |
| **Kaggle ISLR (asl-signs)** | ASL | **250 sinais, ~94 mil sequências já em landmarks do MediaPipe** ⚠️ | **a conferir** | pré-treino do verificador |
| **PopSign ASL v1.0** | ASL | 250 sinais, ~200 mil vídeos, 47 pessoas ⚠️ | **CC-BY 4.0** ⚠️ | pré-treino |
| **ASL Citizen** (Microsoft) | ASL | ~2.700 sinais, vídeos da comunidade ⚠️ | **termos próprios da Microsoft; fontes divergem, uso comercial só com contato** ⚠️ | pré-treino, se a licença permitir |
| **Spreadthesign** | 40+ línguas, **inclui pt.br** ✅ (a página responde) | dicionário de sinais em vídeo | do site | é o dado de treino do SignCLIP (seção 6) |
| **Avatar VLibras renderizado** | Libras | os 24 mil sinais do avatar | do governo | **ideia a testar**: rodar o MediaPipe sobre o próprio avatar dá referência para qualquer sinal, e é exatamente o que o aluno viu |

Como o LIBRAS-EQT-UECE foi conferido sem baixar os 45 GB: lendo só o índice do zip por HTTP
(`remotezip`). Estrutura: `NN_GLOSA/INFORMANTE k/IMG_xxxx.mp4` e, nos landmarks,
`Libras-EQT-UECE (Hand Landmarks)/NN_GLOSA/INFORMANTE k/IMG_xxxx.npy`.

---

## 6. Modelos e trabalhos acadêmicos

| Trabalho | O que traz | Uso aqui |
|---|---|---|
| **SignCLIP** (Jiang et al., EMNLP 2024) | codificador pré-treinado sobre **MediaPipe Holistic** com o Spreadthesign (~457 mil pares vídeo-texto, 41–44 línguas). Holistic superou vídeo cru (R@1 0,68 × 0,37 ⚠️). Fora do domínio precisa de ajuste fino. Código no fork do fairseq (`J22Melody/fairseq`, `examples/MMPT`) ✅ | **testar primeiro** como codificador do verificador. A conferir: se os pesos estão disponíveis e se Libras entrou no treino |
| **1º lugar Kaggle ISLR** (hoyso48) | 1D-conv + transformer leve sobre ~118 landmarks; ~89% em 250 sinais de ASL ⚠️. Repositório público ✅ | **receita** do nosso codificador, se o SignCLIP não servir |
| **Subconjunto de pontos em Libras** (dos Santos et al., arXiv 2510.24887, IEEE SAS 2026) | usar todos os pontos do MediaPipe **piora** o acerto; o subconjunto certo é **5× mais rápido**; interpolação por spline dos pontos perdidos ajuda | escolha da entrada do codificador |
| **SignPose2Vec** (arXiv 2306.17558) | embeddings de pose robustos para língua com pouco dado, multilíngue | alternativa ao SignCLIP |
| **One-shot ISLR** (arXiv 2502.20171) | reconhecer sinal novo com **um** exemplo, entre línguas | apoia a ideia de referências sem retreino |
| **Segmentação** (Moryossef et al., EMNLP 2023) | segmenta sinais e frases a partir de pose (BIO); funcionou em língua não vista no treino | etapa da frase corrida (seção 11) |

---

## 7. O experimento de 12/11 (baseline com DTW) ✅

**Pergunta:** com as 3 pessoas por sinal do V-LIBRASIL e **sem treinar nada**, comparar
landmarks com DTW já serve para dizer "este é o sinal X"?

### Montagem
- **30 sinais sorteados** (semente 7, só sinais com 3 articuladores) × 3 = **90 vídeos, 253 MB**.
  Lista em `ia/visao/spike_amostra.json`.
- Extração: MediaPipe Holistic 1.2.3 (Python 3.12), 8 processos: **19.110 quadros em ~3 min**
  (~100 quadros/s no total). Script: `ia/visao/extrair_landmarks.py`.
- Comparação: cada vídeo contra os outros 89 (`ia/visao/spike_dtw.py`, DTW com numba).
- Medidas por quadro, a 15 fps:
  - **posição do punho** relativa ao meio dos ombros, em larguras de ombro; ou relativa ao nariz;
  - **forma da mão**: 19 ângulos (15 de flexão dos dedos e 4 de abertura), que não mudam com a rotação;
  - **orientação da palma**: vetor normal ao plano pulso–indicador–mindinho;
  - **velocidade** do punho.
- **Espelhamento:** cada consulta é comparada também com x invertido e mãos trocadas; vale a menor distância.
- **Trecho ativo:** do quadro em que a mão mais alta sobe 0,2 largura de ombro acima do repouso
  (5 primeiros quadros) até o último em que ainda está acima.

### Dois achados de engenharia (valem para sempre)
1. **O OpenCV devolve quadros PRETOS nos vídeos entrelaçados do V-LIBRASIL** (aviso
   `swscaler: Cannot convert interlaced to progressive`). Com OpenCV, 33 de 90 vídeos davam zero
   detecção. Decodificando com **`ffmpeg -vf yadif`**: **pose em 100% e alguma mão em 97–100% dos
   quadros**, nos três articuladores.
2. **A mão some por alguns quadros quando passa na frente do rosto.** Preencher o buraco como
   "mão abaixada" estragava tudo. O certo é **interpolar** (posição e ângulos).

E um dado: **22 de 90 vídeos usam a mão esquerda como dominante** (a que mais se move). Trocar de
mão é variante real, e o espelhamento é obrigatório.

### Resultado

Chute = 3,3% de top-1. Todas as linhas com espelhamento.

| Medidas comparadas | top-1 | top-3 | AUC | **EER** |
|---|---|---|---|---|
| só trajetória do punho | 11% | 31% | 0,74 | 29% |
| só forma da mão | 18% | 34% | 0,73 | 29% |
| trajetória + forma | 28% | 51% | 0,80 | 27% |
| trajetória + forma + orientação | **34%** | 52% | 0,79 | 27% |
| padronizado, relativo ao nariz, + velocidade | 26% | 47% | 0,75 | **27%** |

Sem espelhamento, o EER piora de 4 a 9 pontos.

### Conclusão
- A comparação "artesanal" bate num **teto de ~27% de EER**: o tutor diria "errado" para **1 em
  cada 4 sinais certos**. Não serve para **decidir** certo/errado.
- Serve como **baseline** (o número a bater) e como base do **diagnóstico por parâmetro**
  (seção 10), que é sobre *qual parte* desviou, não sobre o veredito.
- Ressalva: são só 2 referências por consulta, de **pessoas diferentes**, o cenário mais duro.
  Com o aluno entram as 3. A E2 refaz a medição com os 1.364 sinais.

### Reproduzir
```bash
uv venv -p 3.12 .venv-visao && uv pip install -p .venv-visao/bin/python mediapipe numpy numba
curl -sSLo holistic.task https://storage.googleapis.com/mediapipe-models/holistic_landmarker/holistic_landmarker/float16/latest/holistic_landmarker.task
# baixe os vídeos da lista em ia/visao/spike_amostra.json para videos/ (URLs em KNOWLEDGE/06)
.venv-visao/bin/python ia/visao/extrair_landmarks.py videos lm holistic.task
.venv-visao/bin/python ia/visao/spike_dtw.py        # roda na pasta que tem lm/
```
`.venv-visao/` e `*.task` estão no `.gitignore`.

---

## 8. Arquitetura

```
NAVEGADOR (aba Praticar)                                          SERVIDOR (ia/servidor.py)
câmera ─► HolisticLandmarker ─► normalização ─► segmentação ─┐
          (VIDEO + rAF)          ombros/nariz     repouso ↔    │
                                 espelho          sinal         ▼
                                                  para cada sinal esperado (da glosa):
          referências do sinal ─────────────────► (a) VERIFICADOR: modelo pequeno (ONNX)
          (baixadas por glosa,                       → distância à referência mais próxima
           poucos KB cada)                           → certo / dúvida / não bate
                                                  (b) DIAGNÓSTICO por parâmetro (DTW contra
                                                      a referência mais próxima)
                                                  ─► resultado estruturado ──► POST /api/avaliacao
                                                                                  │ Jev escolhe a
          tela: sinal a sinal + orientação ◄──────────────────────────────────────┘ orientação
          avatar: toca o sinal que falhou                                           no catálogo

OFFLINE (Python, uma vez por versão)
V-LIBRASIL (4.086 vídeos) ──┐
LIBRAS-EQT-UECE, MINDS ─────┼─► landmarks ─► referências por glosa ─► Hugging Face / web/public
avatar renderizado (futuro) ┘           └──► treino do verificador (PyTorch) ─► ONNX
```

**Peças e onde ficam (proposta):**

| Peça | Onde | Observação |
|---|---|---|
| captura + landmarks | `web/src/camera.ts` | hook no estilo do `usePlayer` |
| normalização + recorte + medidas | `web/src/sinal/` | **a mesma matemática** do `ia/visao/`, portada para TS. Um teste compara as duas saídas no mesmo vídeo |
| verificador | `web/public/modelos/*.onnx` | carregado sob demanda, com cache |
| referências | `web/public/referencias/{GLOSA}.bin` ou HF | só o que a frase usa |
| catálogo de orientações | `ia/orientacoes.py` | escrito à mão |
| avaliação | `POST /api/avaliacao` | o servidor só recebe números, nunca vídeo |

Rascunho do contrato (vai mudar):
```json
POST /api/avaliacao
{ "glosa": ["AMANHÃ","IR","COMPRAR","ABACAXI"],
  "sinais": [ {"pos":0,"veredito":"certo","conf":0.93},
              {"pos":2,"veredito":"nao_bate","conf":0.81,
               "desvios":{"CM":0.7,"Or":0.6,"M":0.1,"PA":0.2,"ENM":0.0}} ],
  "ordem": "igual" }
→ { "orientacao": "…texto do catálogo…", "mostrar": {"sinal":"COMPRAR","velocidade":0.5} }
```

---

## 9. O verificador aprendido

- **O quê:** um codificador pequeno de sequências de landmarks que transforma um sinal num vetor
  (aprendizado métrico: triplet ou ArcFace). Verificar = distância entre a execução do aluno e as
  referências daquele sinal.
- **Entrada:** subconjunto de pontos (mãos + braços/ombros + alguns do rosto), seguindo o
  arXiv 2510.24887.
- **Arquitetura:** a receita do 1º lugar do Kaggle ISLR (1D-conv + transformer leve), 1–5 MB.
- **Caminho, em ordem:**
  1. **SignCLIP pronto** como codificador: se os pesos estiverem disponíveis e o EER cair, basta.
  2. **Nosso codificador**: pré-treino em ASL (Kaggle ISLR, PopSign), afinamento em Libras
     (V-LIBRASIL, LIBRAS-EQT-UECE, MINDS-Libras), validação em **pessoa que o modelo nunca viu**.
- **Critério para ir para a tela (D8):** **EER ≤ 10%** no protocolo da seção 7, com o mesmo script.
  Enquanto não chegar, a tela mostra só o diagnóstico, sem "certo/errado".
- O limiar de "certo" sai da curva medida, nunca de chute.

---

## 10. O diagnóstico pelos parâmetros da Libras

| Parâmetro | Como medir | Mensagem típica |
|---|---|---|
| Configuração de mão (CM) | ângulos dos dedos nos quadros de "parada" do sinal | "observe a posição do polegar" |
| Ponto de articulação (PA) | posição da mão relativa a rosto, peito ou espaço neutro | "o sinal é feito perto do queixo" |
| Movimento (M) | forma da trajetória e velocidade, alinhadas por DTW | "movimento não identificado" |
| Orientação da palma (Or) | vetor normal da palma | "a palma vira para você" |
| Expressão não manual (ENM) | blendshapes do rosto | "a pergunta pede sobrancelhas franzidas" |

- O desvio de cada parâmetro é comparado com a **variação entre as referências** do mesmo sinal.
  Só é "erro" o que foge do que sinalizantes fluentes fazem.
- O diagnóstico só aparece quando o verificador diz "não bate" ou "dúvida".
- Futuro: classificador das ~61 configurações de mão (LIBRAS-HC-RGBDS e afins) para dizer "a mão
  deveria estar em L".

---

## 11. Segmentação: do guiado para o corrido

1. **Modo guiado (primeiro):** o avatar mostra o sinal *k*, o aluno faz, o sistema avalia e segue.
   Um sinal por vez, **sem problema de segmentação**. Começo e fim pela altura da mão em relação ao
   repouso (o recorte da seção 7).
2. **Frase corrida (depois):** alinhar a sequência esperada com a gravação (DTW de subsequência),
   usando pausas e trocas de mão como pistas. Se não bastar, o modelo de Moryossef et al. (seção 6).

---

## 12. Variantes e ordem dos sinais

- **Várias referências por sinal**: basta bater com uma.
- **Mão dominante espelhada** (canhotos e quem troca de mão): medido que ajuda.
- **Velocidade**: o DTW e o codificador absorvem.
- **Ordem (D9, decidido):** se todos os sinais estiverem presentes em outra ordem, a tela diz
  "ordem diferente da sugerida" **sem reprovar**.
- **Aviso fixo na aba:** "Libras não é português sinalizado. A ordem dos sinais e a gramática podem
  ser diferentes da frase em português."

---

## 13. A aba Praticar (interface)

Pedido do Gustavo (o design fino vem depois, D10):
- **Topo:** mais escuro, **vidro preto fosco** (`backdrop-filter: blur(...)` sobre fundo escuro
  translúcido), valendo para as duas abas.
- **Botão da aba** antes de "IA ligada", com **hover azul** (escuro no tema escuro, claro no claro).
  Os tokens de cor entram no `styles.css` junto com os do tema.
- **Layout:** câmera no centro, ocupando a maior parte; à direita, avatar em cima e chat pequeno
  embaixo.
- A câmera aparece **espelhada** (como espelho), com os pontos opcionalmente desenhados por cima.
- Antes de começar: pedido de permissão da câmera, o aviso **"o vídeo não sai do seu computador"**
  e uma checagem de enquadramento (mãos, rosto e ombros visíveis).

---

## 14. Hardware e custos

### A máquina do Gustavo (medida em 12/11) ✅
- CPU com **16 threads**, **31 GB de RAM**.
- GPU integrada Intel UHD (Raptor Lake) + **NVIDIA GeForce RTX 3050 Laptop, 6 GB** (Ampere).
- **A NVIDIA está no driver `nouveau` (o livre)**: `nvidia-smi` não existe e **CUDA não funciona**.
  O PyTorch hoje só usaria a CPU.

### A GPU serve?
**Serve, sim, para este tamanho de problema.** O verificador tem 1–5 milhões de parâmetros e a
entrada são números, não imagens: 6 GB sobram. O que falta é o driver: no Arch seria o
`nvidia-open` + `nvidia-utils` (as rodas do PyTorch trazem o CUDA; só o driver é exigido).
Notebook com duas GPUs pede configuração de PRIME, e trocar o driver de vídeo tem risco de tela
preta. **Decisão proposta (D11):** começar o treino na CPU e **medir uma época**. Só instalar o
driver se ficar lento demais. O SignCLIP, só para gerar vetores, roda na CPU.

### Custos
| Item | Custo |
|---|---|
| Visão no navegador | **zero** de servidor |
| Download na 1ª visita | ~28 MB do MediaPipe + modelo do verificador (1–5 MB) + avatar (~20 MB, já cacheado) |
| Jev por tentativa | da ordem de US$ 0,0001 |
| Extração do V-LIBRASIL inteiro | ~2 h de CPU, pela medição de 100 quadros/s (4.086 vídeos × ~170 quadros) |
| Treino | horas de CPU (a medir) |

---

## 15. Questões legais

> Isto é orientação prática, **não é parecer jurídico**. Para publicar algo comercial, vale um
> advogado de direito autoral.

### Quem são os autores do V-LIBRASIL
O V-LIBRASIL foi criado por **Ailton José Rodrigues** na dissertação de mestrado no **Centro de
Informática da UFPE** (2021), orientado por **Cleber Zanchettin**. Está publicado no site do
projeto (libras.cin.ufpe.br) e no **IEEE DataPort** (DOI 10.21227/v589-hn68). As pessoas que
aparecem sinalizando nos vídeos são os **articuladores** (intérpretes).

### Como funciona, em termos simples
- **O site e o código são seus.** Isso não muda.
- **Os vídeos não são seus**: são obra dos pesquisadores da UFPE e trazem a **imagem** dos intérpretes.
- **Sem licença declarada, vale a regra padrão da lei de direitos autorais (Lei 9.610/98):
  "todos os direitos reservados".** Estar disponível para baixar não é o mesmo que poder redistribuir.
- O que pesa mais, em ordem:
  1. **O espelho público no Hugging Face** (`SchberGg/v-librasil-raw`) já é uma redistribuição dos
     vídeos, inclusive do rosto dos intérpretes. É o ponto mais exposto hoje.
  2. **Publicar referências derivadas** (landmarks por glosa) no site: são números, não imagens,
     o que pesa bem menos, mas continua sendo derivado da obra.
  3. **Uso local para estudar e medir** (o que fizemos hoje): é o uso de menor risco.

### Pista ainda não lida
O site do projeto tem uma página **"Condições de uso"**
(https://libras.cin.ufpe.br/pages/conditions-of-use,3, achada por busca em 12/11). O site estava
**fora do ar (502)** nesse dia, então ninguém leu ainda. **Ler antes de qualquer coisa**: pode já
responder o que perguntamos aos autores.

### Status
- **13/11: os autores responderam, autorizando.** Resposta recebida pelo Gustavo: *"pode mandar
  bala fera, fica a vontade, parabens pela iniciativa"*. O e-mail pedia **(a)** manter o espelho
  no HF com citação e **(b)** publicar landmarks derivados no site. É uma autorização **informal e
  sem licença nomeada**: guardar o e-mail (é a prova) e **citar sempre** (dissertação + DOI), no
  cartão do dataset no HF e onde o dado aparecer no site. Os itens 1 e 2 da recomendação abaixo
  ficam resolvidos; 3 e 4 continuam valendo.
- **12/11:** e-mail único aos dois autores redigido; o Gustavo vai enviar. Os e-mails públicos
  **não foram confirmados** por nós (a busca não achou fonte oficial): procurar no Lattes, na
  página do CIn/UFPE ou no botão de contato do IEEE DataPort. Registrar aqui a resposta.

### O que fazer (recomendação)
1. **Escrever aos autores** (Ailton Rodrigues e Cleber Zanchettin, CIn/UFPE): explicar o projeto
   (tutor gratuito de Libras), pedir permissão para **(a)** manter o espelho no HF com citação e
   **(b)** publicar landmarks derivados no site, e perguntar sob qual licença preferem.
   **Posso redigir o e-mail.**
2. Enquanto não houver resposta: considerar deixar o espelho no HF **privado**, ou ao menos pôr a
   **citação** no cartão do dataset; manter as referências derivadas **só locais**.
3. **Citar sempre** (dissertação + DOI) onde o dado for usado.
4. Preferir, para tudo que for **publicado**, dados com licença clara: LIBRAS-EQT-UECE e MINDS-Libras
   são **CC-BY 4.0** (exigem só a atribuição).

### Outras licenças
| Item | Licença |
|---|---|
| LIBRAS-EQT-UECE, MINDS-Libras | CC-BY 4.0 ✅ (atribuição) |
| PopSign | CC-BY 4.0 ⚠️ |
| ASL Citizen | termos da Microsoft Research; uso comercial só com contato ⚠️ |
| Kaggle ISLR | regras da competição, a conferir ⚠️ |
| OpenPose | não comercial |
| MediaPipe, MMPose, ONNX Runtime | Apache-2.0 / MIT |
| Avatar e bundles VLibras | do Governo Federal ([FONTES](FONTES.md)) |

### Privacidade do aluno
A câmera é dado pessoal sensível (rosto). Como o processamento é **todo local** (D2), nada de
imagem chega ao servidor: só números da avaliação. A tela diz isso antes de pedir a câmera. Se um
dia gravarmos execuções para melhorar o modelo, será **opt-in explícito** (LGPD).

---

## 16. Etapas

Reordenadas em 12/11 pela decisão D10: **reconhecimento primeiro**; lições depois.

| # | Etapa | Pronto quando |
|---|---|---|
| E0 | ✅ Estudo + baseline DTW (este documento) | feito em 12/11 |
| E1 | 🟡 **Aba Praticar**: topo de vidro fosco com o botão (hover azul), câmera + HolisticLandmarker no navegador, pontos desenhados, aviso de privacidade | **FPS medido** no notebook do Gustavo. Código pronto e medido em Chrome headless (seção 16.1); falta a medida no Chrome dele, com a webcam |
| E2 | **Referências**: extrair o V-LIBRASIL inteiro (~2 h CPU) + EQT-UECE + MINDS; formato compacto por glosa | baseline DTW **medido nos 1.364 sinais** |
| E3 | **Verificador**: SignCLIP primeiro; se não servir, o nosso codificador | **EER ≤ 10%** no protocolo da seção 7 |
| E4 | **Bancada de reconhecimento**: o aluno escolhe um sinal, faz para a câmera e vê o veredito + o diagnóstico por parâmetro + o avatar fazendo o certo | o Gustavo testa ~30 sinais sem "errado" falso |
| E5 | **Lições**: frase proposta, sinal a sinal (modo guiado), orientação do Jev | a estrutura das lições, a definir com o Gustavo |
| E6 | **Frase corrida** (segmentação) | as frases da E5 sem o modo guiado |
| E7 | Avatar como referência; classificador das configurações de mão | cobertura além dos 1.095 sinais |

### 16.1 E1: o que foi feito e medido (13/11)

**Código:**
- `web/src/camera.ts`: hook `useCamera` com `getUserMedia` (1280×720 ideal, sem áudio) e
  `HolisticLandmarker` em `runningMode: "VIDEO"` + `requestAnimationFrame`. Só processa
  **quadro novo** (`video.currentTime` mudou). O modelo é criado **uma vez por página**: trocar de
  aba não baixa nem recompila. Tenta o delegate **GPU** e cai para **CPU** se falhar; `?delegate=CPU`
  na URL força a CPU, para comparar os dois.
- `web/src/Praticar.tsx`: carregado sob demanda (`React.lazy`): quem só usa o chat não baixa o
  MediaPipe (o pedaço JS tem 159 KB, ou 48 KB com gzip, mais o wasm e o modelo na 1ª vez).
  Mostra o aviso de privacidade antes de pedir a câmera, o vídeo **espelhado** com os pontos
  (tronco e braços da pose, as duas mãos; o rosto fica de fora do desenho por poluir), uma barra
  com **quadros/s · ms por quadro · delegate**, a checagem de enquadramento (rosto · ombros ·
  mãos) e o aviso fixo da seção 12.
- `App.tsx`: abas **Conversar | Praticar** no topo, antes de "IA ligada". O **avatar é o mesmo
  iframe** nas duas abas, só muda de lugar no grid (trocar de aba não recarrega o Unity). Sair da
  aba Praticar **desliga a câmera** (o componente desmonta e para as trilhas).
- `styles.css`: topo de vidro preto fosco nos dois temas (ele carrega os próprios tons do
  escuro); hover azul das abas por token (`--azul`: claro no tema claro, escuro no escuro).

**Medida (✅, 13/11):** Chrome 148 **headless** neste notebook, com câmera falsa alimentada por
`Abacaxi_Articulador1.mp4` (ffmpeg + yadif → 1280×720 y4m, 30 fps). O WebGL do headless usa a
**Intel UHD real** (`ANGLE (Intel, Mesa Intel(R) Graphics (RPL-S))`), não emulação.

| Delegate | quadros/s | ms por `detectForVideo` |
|---|---|---|
| CPU (WASM) | **13–14**, estável | ~72 |
| GPU (WebGL na Intel UHD) | 8–15, oscilando | 63–142 |

Leitura: **neste notebook a CPU ganha da GPU integrada**, e ~14 quadros/s fica perto dos 15 fps
que o spike usou para comparar sinais. Dá para a E4, mas sem folga. Se o Chrome de verdade
(com a webcam) der o mesmo, as saídas em ordem são: (1) deixar a CPU como padrão; (2) o plano B
da seção 17 (Hand + Pose separados, sem a malha de 478 pontos do rosto, e o Face Landmarker só
quando a ENM importar); (3) rodar a detecção num Web Worker para não travar a página.

**Para o Gustavo medir:** `npm run dev`, abrir `http://localhost:5173`, aba **Praticar**, ligar a
câmera, anotar os números da barra após ~10 s. Repetir em `http://localhost:5173/?delegate=CPU`.
A câmera só funciona em **localhost ou https**: `HOST=0.0.0.0` em http, acessado de outro
aparelho, não libera a câmera.

### 16.2 A mão "some" no movimento (13/11)

**Relato do Gustavo testando com a webcam:** em sinais com arrasto lateral (OI: mão em I
arrastada; NOME: dois dedos de −x a +x) os pontos param de acompanhar a mão. E ele não sabia que
a E1 ainda não reconhece nada (agora a tela diz isso).

**Experimento ✅** (Chrome headless, CPU, câmera falsa = OI + NOME dos 3 articuladores do
V-LIBRASIL, 54 s em laço; bancada descartável fora do repo, métrica = % dos quadros processados
com ≥1 mão e quantos "buracos" sem mão):

| Entrada | Config | quadros/s | ≥1 mão | 2 mãos | buracos |
|---|---|---|---|---|---|
| normal | A: Holistic padrão | 14,6 | 95,7% | 81,4% | 2 |
| normal | B: Holistic, limiares baixos¹ | 14,5 | 95,9% | 86,9% | 2 |
| normal | C: só Hand Landmarker | 23,8 | 96,4% | 47,6% | 2 |
| 2× mais rápido | A | 14,6 | 96,4% | 82,7% | 6 |
| 2× mais rápido | B | 14,4 | 97,1% | 86,3% | 3 |
| 2× mais rápido | C | 23,6 | 95,1% | 42,4% | 5 |
| 2× + **desfoque**² | A | 14,6 | **87,4%** | 70,3% | **25** |
| 2× + desfoque | B | 14,4 | **92,3%** | 75,3% | 22, mais curtos |
| 2× + desfoque | C | 23,2 | 88,9% | 35,0% | 23 |

¹ `minHandLandmarksConfidence 0,2`, pose e rosto `0,3`. ² `tmix=frames=4` (média de 4 quadros,
imita obturador lento).

**Leitura:**
- **Velocidade sozinha não derruba** o rastreio (2× = igual). **Desfoque derruba.**
- Limiares baixos (B) recuperam parte (87 → 92%) e não pioram o vídeo limpo → **aplicado no app**.
- Hand Landmarker separado é mais rápido (24 qps), mas perde a mão parada (2 mãos em 35–48%):
  **descartado** como troca; o holístico acha a mão a partir da pose.
- **A webcam do Gustavo** (`v4l2-ctl --list-ctrls`, sem ligar a câmera): `auto_exposure` em
  *Aperture Priority* e **`exposure_dynamic_framerate=1`**, ou seja, em pouca luz ela **reduz o
  FPS e alonga a exposição até 62,5 ms** (`exposure_time_absolute` 9–625, ×100 µs). É o
  desfoque do experimento. Suspeito principal, **a confirmar com um clipe dele**.
- Buracos curtos (1–7 quadros) na avaliação se resolvem por **interpolação** (já medido no
  spike, seção 7). O problema é o buraco longo.

**Próximo:** clipe de ~15 s da webcam dele (OI, NOME, mão parada) passado pela mesma bancada,
com a luz de sempre e depois com mais luz ou `exposure_dynamic_framerate=0`. Se a exposição
for a causa, as saídas em ordem são: luz (grátis), pedir exposição curta pelo navegador
(`exposureMode/exposureTime` do MediaStreamTrack, a verificar se o Chrome no Linux aceita ⚠️),
aviso de "pouca luz" na checagem de enquadramento.

No começo, as frases e sinais propostos saem de uma lista cujos sinais **todos** têm referência
(V-LIBRASIL ∩ avatar = 1.095).

---

## 17. Riscos e perguntas abertas

### Riscos
| Risco | Mitigação |
|---|---|
| Iluminação, enquadramento, câmera ruim | checagem antes de começar |
| Mão na frente do rosto some por alguns quadros | interpolar (medido) |
| Holístico pesado no navegador | medir na E1; plano B com os três landmarkers separados ou só mãos + pose |
| Modelo julga errado e ensina errado | EER ≤ 10% antes de "certo/errado"; "não consegui avaliar" na dúvida |
| Diferença entre Python (referências) e navegador (aluno) | mesma versão do MediaPipe nos dois lados; teste que compara as duas saídas no mesmo vídeo |
| Licença do V-LIBRASIL | seção 15 |
| Treino lento na CPU | medir uma época; driver NVIDIA ou Colab como saída |
| SignCLIP sem pesos públicos ou sem Libras | cai para o nosso codificador (seção 9) |

### Perguntas abertas
1. ~~Escrever aos autores do V-LIBRASIL?~~ Respondido em 13/11: autorizaram (seção 15).
2. ~~O espelho no HF: público ou privado?~~ Público, **com citação no cartão do dataset**. Conferido em 13/11: o README do HF cita o portal da UFPE, mas **não os autores nem o DOI**: falta acrescentar (dissertação de Ailton J. Rodrigues, orientação de Cleber Zanchettin, CIn/UFPE 2021; DOI 10.21227/v589-hn68).
3. Instalar o driver NVIDIA agora ou só se a CPU não der conta? (D11)
4. Formato das lições (E5): a definir depois, por decisão do Gustavo (D10).

---

## 18. Histórico de mudanças

| Data | Mudança |
|---|---|
| 2026-11-12 | Criação: pedido, estudo, experimento DTW (EER 27%), arquitetura, decisões D1–D8 |
| 2026-11-12 | Respostas do Gustavo: ordem diferente é aceita avisando (D9); reconhecimento antes das lições (D10, etapas reordenadas); GPU RTX 3050 6 GB em `nouveau`, treino começa na CPU (D11); seção legal escrita |
| 2026-11-13 | Autores do V-LIBRASIL autorizaram por e-mail (espelho no HF + landmarks derivados), seção 15. E1 implementada: aba Praticar, câmera + Holistic no navegador, `@mediapipe/tasks-vision` fixado em **1.2.0**; FPS medido em headless: CPU 13–14 quadros/s (72 ms) > GPU Intel 8–15 (seção 16.1) |
| 2026-11-13 | Mão "some" no arrasto (relato do Gustavo): velocidade não explica, desfoque sim (96 → 87%); limiares baixos aplicados (→ 92%); webcam dele alonga a exposição em pouca luz (§16.2). Tela agora diz que a E1 não reconhece sinais |

---

## 19. Links

**MediaPipe**
- Holistic Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/holistic_landmarker
- Hand Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- Face Landmarker (blendshapes): https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker
- Gesture Recognizer: https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer
- Pacote web: https://www.npmjs.com/package/@mediapipe/tasks-vision
- Modelo holístico: https://storage.googleapis.com/mediapipe-models/holistic_landmarker/holistic_landmarker/float16/latest/holistic_landmarker.task

**Execução no navegador**
- ONNX Runtime Web (começar): https://onnxruntime.ai/docs/get-started/with-javascript/web.html
- ONNX Runtime Web (deploy): https://onnxruntime.ai/docs/tutorials/web/deploy.html

**Alternativas de pose**
- OpenPose: https://github.com/CMU-Perceptual-Computing-Lab/openpose
- MMPose: https://github.com/open-mmlab/mmpose

**Datasets**
- V-LIBRASIL (site): https://libras.cin.ufpe.br
- V-LIBRASIL (IEEE DataPort): https://ieee-dataport.org/documents/v-librasil-new-dataset-signs-brazilian-sign-language-libras
- V-LIBRASIL (dissertação, UFPE): https://repositorio.ufpe.br/bitstream/123456789/43491/1/DISSERTA%c3%87%c3%83O%20Ailton%20Jos%c3%a9%20Rodrigues.pdf
- Nosso espelho: https://huggingface.co/datasets/SchberGg/v-librasil-raw
- LIBRAS-EQT-UECE: https://zenodo.org/records/20497742
- MINDS-Libras: https://zenodo.org/records/2667329 · RGB-D: https://zenodo.org/record/4322983
- Kaggle ISLR (asl-signs): https://www.kaggle.com/competitions/asl-signs
- PopSign ASL v1.0: https://signdata.cc.gatech.edu/view/datasets/popsign_v1_0/
- ASL Citizen: https://www.microsoft.com/en-us/research/project/asl-citizen/ · licença: https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/
- Spreadthesign (pt.br): https://www.spreadthesign.com/pt.br/search/

**Trabalhos**
- SignCLIP: https://arxiv.org/abs/2407.01264 · https://aclanthology.org/2024.emnlp-main.518 · código: https://github.com/J22Melody/fairseq/tree/main/examples/MMPT
- 1º lugar Kaggle ISLR: https://github.com/hoyso48/Google---Isolated-Sign-Language-Recognition-1st-place-solution
- Subconjunto de pontos em Libras: https://arxiv.org/abs/2510.24887
- SignPose2Vec: https://arxiv.org/abs/2306.17558
- One-shot ISLR: https://arxiv.org/abs/2502.20171
- Segmentação (Moryossef et al.): https://aclanthology.org/2023.findings-emnlp.846 · código: https://github.com/sign-language-processing/segmentation
- Síntese de vídeos com V-LIBRASIL para tradução: https://arxiv.org/abs/2409.01506

**Nesta base**
- [03](03-player-3d.md) player e cache · [06](06-dataset-vlibrasil.md) V-LIBRASIL · [12](12-rag-ou-indice.md) RAG ou índice ·
  [13](13-camada-de-ia-jev.md) Jev · [FONTES](FONTES.md) licenças
