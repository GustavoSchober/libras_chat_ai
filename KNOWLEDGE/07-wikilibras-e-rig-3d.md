# 07 — WikiLibras e o rig 3D (`padrao.blend`)

Como nascem sinais novos no VLibras, e o que há dentro do arquivo em `3dchar/`.

> `3dchar/` fica **fora do Git** (binário de terceiros, 2,3 MB, não usado em runtime).
> A anatomia completa do rig está documentada abaixo — não é preciso reabrir o arquivo.
> Ver [FONTES.md](FONTES.md).

## WikiLibras: a fábrica de sinais

Do PDF `Doc_VLibras_Wikilibras.pdf`:

> O WikiLibras é uma plataforma para a construção e evolução colaborativa dos sinais do
> VLibras com a participação de uma comunidade de usuários através da Internet. [...] permite
> que uma rede de colaboradores possa **criar, revisar, animar e avaliar** sinais em Libras,
> e caso esses sinais sejam aprovados por especialistas, eles passarão a compor/complementar
> o dicionário de sinais da Suíte VLibras.

Ou seja, o caminho oficial de um sinal novo:

```
proposta → animação no Blender (rig padrão) → revisão → aprovação por especialista
        → exportação como AssetBundle Unity → publicação em dicionario2.vlibras.gov.br
```

Isso explica por que o acervo tem 24.213 sinais: foi construído a mão, por humanos, ao
longo de anos. **Não há API pública para injetar um sinal novo.** O pipeline é interno
(Console + Login Único gov.br + Kubernetes).

Stack do WikiLibras (contexto, não vamos usar): React 16.9 + Material UI + Redux Saga no
front; **AdonisJS 4** no back.

## O arquivo `3dchar/BLENDER_PADRAO_VLIBRAS.zip`

```
padrao.blend — 5,87 MB descompactado (2,55 MB no zip), de 26/03/2021
formato: BLENDER-v276  →  Blender 2.76 (2015)
```

⚠️ **Blender 2.76 é muito antigo.** O Blender atual (4.x) abre, mas a interface mudou
radicalmente desde o 2.8. Espere ajustes em materiais e provavelmente em constraints.

### O que tem dentro

**Objetos** (todos em português, de um pipeline artesanal brasileiro):

```
Armature.001            ← o esqueleto
corpoModifAlisson       ← malha do corpo
cabecaModifAlisson      ← malha da cabeça
CABELO__MAPEADO         ← cabelo
LINGUA_e_DENTES_01, dentesSuper, dentesInfer
OlhoNOVO, Palpebras.super, Palpebras.infer
OCULOS, OculosRedondo, Empty.OCULOS
CAMERA_35, CAMERA_35.001, MirarCamera
Lamp, Lamp.001, Lamp.002
Lattice, Empty, Sphere.001
--- controles de animação ---
CtrlCabeca, CtrlOlho, CtrlOlhoGeral,
CtrlMao.L, CtrlMao.R, CtrlOrientMao,
CtrlSobrancelhaDir, CtrlSobrancelhaDi, CtrlPolyWire
```

**Ossos do rig** (~60), extraídos do bloco `ARArmature`:

| Região | Ossos |
|---|---|
| Coluna | `BnBacia`, `BnBacia.001`, `BnCol-01/02/03`, `BnPescoco`, `BnCabeca` |
| Mandíbula/língua | `BnMandibula`, `BnDirigeQueixo`, `BnLingua`, `BnLingua.001/.002/.003` |
| Sobrancelhas | `BnSobrancCentro`, `BnSobrancCentro.L/.R`, `BnSobrancLateral.L/.R` |
| Olhos | `BnOlho.L/.R`, `BnPalpebSuper.L/.R`, `BnPalpebInfe.L/.R`, `BnOlhoMira.L/.R`, `BnOlhosMira` |
| Boca/face | `BnLabioCentroSuper`, `BnLabioCentroInfer`, `BnBocaCanto.L/.R`, `BnBochecha.L/.R` |
| Braços | `BnOmbro.L/.R`, `BnBraco.L/.R`, `BnAntBraco.L/.R`, `BnAntBraco.*.001` (twist) |
| Mãos | `BnMao.L/.R` + **`BnDedo.1.{L,R}` e `.001`–`.014`** = **15 ossos por mão** |
| Pernas | `BnBacia_L/_R`, `BnPerna.L/.R` |
| IK / auxiliares | `ik_FK.L/.R`, `BnMaoOrient.L/.R`, `BnPolyV.L/.R` |

As curvas de animação são `rotation_quaternion`, `location` e `scale`. A action no arquivo
chama-se `Untitled` (é um template vazio, como esperado de um "padrão").

### Por que esse rig é bem desenhado para Libras

Repare no que ele prioriza:
- **15 ossos por mão** (5 dedos × 3 falanges) — configuração de mão é o parâmetro fonológico
  nº 1 em Libras;
- **ossos faciais detalhados** — sobrancelhas separadas em centro e lateral, pálpebras
  superior e inferior independentes, cantos da boca, bochechas, língua em 4 segmentos.
  Isso existe porque **expressão facial é gramática em Libras**, não emoção decorativa;
- **mira de olhar** (`BnOlhoMira`, `BnOlhosMira`) — direção do olhar marca referência
  espacial e concordância;
- **IK nos braços** (`ik_FK`) — permite animar pela posição da mão (como o sinalizador pensa)
  em vez de rotacionar ombro e cotovelo.

Não é um rig genérico de jogo. Foi feito por quem entende a língua.

## O que fazer com isso — avaliação honesta

### Caminho A — não mexer (recomendado para a v1)

Use os 24.213 sinais prontos. O rig não é necessário para o chat funcionar. Nada do projeto
depende do Blender.

### Caminho B — animar sinais faltantes à mão

Abrir o `padrao.blend`, animar um dos 269 sinais do seu dataset que o avatar não tem,
exportar. **Problema real:** o player consome `AssetBundle` do Unity 2018.3.1, não `.blend`
nem `.glb`. Para produzir um bundle compatível seria preciso Unity 2018.3.1 + o projeto
original do player + o script de exportação do WikiLibras — **nada disso é público**.

Veredito: **inviável sem cooperação do LAViD.** Não invista nisso.

### Caminho C — player próprio (three.js) a partir do rig

Se um dia quisermos sinais customizados, o caminho realista é *não usar o player do governo*:
carregar o `padrao.blend` → exportar glTF → animar em three.js com nossas próprias animações.
Aí o rig passa a ser essencial e esse arquivo vale ouro.

Isso é um projeto grande (meses). Mas é bom saber que **o ativo existe e é compatível com
Libras de verdade** — se o projeto crescer, o teto não é o player do governo.

### Caminho D — vídeo → animação (o sonho)

Pose estimation (MediaPipe Holistic dá 21 landmarks por mão + rosto + corpo) nos 4.086
vídeos do V-LIBRASIL → retargeting para os ossos `BnDedo.*`, `BnMao.*`, `BnSobranc*`.

É tecnicamente coerente — os nomes dos ossos mapeiam quase 1:1 com os landmarks do MediaPipe.
Mas: qualidade de mão em vídeo 2D é ruim justamente nos dedos (oclusão), e sem profundidade
a orientação da palma fica ambígua. Seria uma linha de pesquisa, não uma sprint.

**Guarde como visão de longo prazo. Não é o caminho para o produto funcionar.**

## Conclusão

O `padrao.blend` é um **ativo estratégico guardado**, não um insumo da v1.
Documentado aqui para não precisarmos redescobri-lo.
