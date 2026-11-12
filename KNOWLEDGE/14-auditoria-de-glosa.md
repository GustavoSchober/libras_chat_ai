# 14 — Auditoria da glosa em massa (Tatoeba) e o backlog

> Apurado em **2026-11-11**. Tudo aqui foi **medido executando** ✅ com `ia/auditoria.py`.

## Por que existe

Testar frase a frase na mão não escala: cada erro achado ("seja bem vinda", "IA → IR")
custava uma conversa. A auditoria roda **milhares de frases reais** e agrupa o resultado por
**padrão** (palavra → sinal), então cada problema é revisado uma vez, não uma vez por frase.

## Como rodar

```bash
# corpus: frases em português do Tatoeba (CC-BY), fica em dados/cache/ (fora do git)
curl -sSfLo dados/cache/tatoeba/por_sentences.tsv.bz2 \
  https://downloads.tatoeba.org/exports/per_language/por/por_sentences.tsv.bz2
bunzip2 -k dados/cache/tatoeba/por_sentences.tsv.bz2

.venv/bin/python ia/auditoria.py codigo --n 20000 --rotulo X   # grátis, ~40 s
.venv/bin/python ia/auditoria.py jev    --n 2000  --rotulo X   # ~US$ 0,12, ~10 min, retoma se cair
.venv/bin/python ia/regressao_verbos.py                         # as 40 frases de sempre
```

Filtro do corpus: 3 a 10 palavras, sem números, sem marcas fortes de Portugal (tu, estás,
comboio…). Sobram **368 mil frases**; a amostra é fixa (semente 42), então duas rodadas com
rótulos diferentes são comparáveis frase a frase. Saída em `ia/resultados/auditoria/`.

- **Passada `codigo`** (sem Jev): mostra o que o código decide sozinho. O Tatoeba é texto limpo,
  então **todo cartão "parece erro de digitação" ali é falso positivo** — é o termômetro do corretor.
- **Passada `jev`**: grava cada frase em `.jsonl` e um resumo por palavra com a confiança média.
  O jeito mais barato de revisar é **comparar duas rodadas e ler só as glosas que mudaram**.

## O que foi medido e corrigido

Passada `codigo`, 20 mil frases (ocorrências):

| Balde | antes | depois |
|---|---|---|
| cartão de "erro de digitação" em texto correto | 216 | **67** (o resto é palavra estrangeira ou erro real do corpus: "dissse", "boaa") |
| palavra só com vizinho de grafia | 1.911 | **623** (sobram línguas/nacionalidades sem sinal) |
| palavra soletrada que não é nome | 2.296 | **339** (sobram palavras que não existem no acervo) |

A regressão das 40 frases ficou em **40/40** depois de cada mudança.

| # | Problema achado | Causa | Correção |
|---|---|---|---|
| 1 | irei → REI/VIRAR, garotas → ARROTAR, perdoe → PERDER | o **simplemma lematiza mal** (irei → "irar", garotas → "garotar", vazia → "vaziar") | 2ª tentativa por sufixo em `candidatos.py` (`FLEXOES`: gênero, número, particípio, futuro, subjuntivo com troca de grafia, diminutivo, -mente), **só quando a 1ª não acha nada**; plural simples já na 1ª (unhas → UNHA, não UNHAR) |
| 2 | "acho **que isso**" → QUE_ISSO, "não sei **de nada**" → DE_NADA, "torcer **para que**" → PARA_QUE | composto de palavras gramaticais casando no meio da frase | `SO_ISOLADAS` (só a frase inteira) e `SO_PERGUNTA` em `glosa.py` |
| 3 | Maria → MAR, Mary → MAR, Tomás → TOMAR, Sami → cartão de digitação | nome no começo da frase não era reconhecido; a regra de sufixo leva nome a palavra (ma-**ria** → mar) | maiúscula sem sinal exato = nome em qualquer posição; no meio da frase só vale sinal com o **próprio** nome (Brasil → BRASIL); radical mínimo de 3 letras |
| 4 | "não conseguia parar" → NÃO_CONSEGUIR **NÃO_PARAR**; "nunca machucamos" → NUNCA **NÃO_MACHUCAR** | o Jev escolhe sinal negado para todo verbo de frase negativa | um "não" vira UM sinal negado; sem "não" livre antes, volta para o positivo |
| 5 | "estou procurando" → ESTAR PROCURANDO | o acervo tem gerúndios como sinal | estar + gerúndio sai; gerúndio prefere o infinitivo |
| 6 | "a mala **se** extraviou" perdia nada, mas "**se** chover" perdia o SE; "tinha comido" → TER COMER | palavra que às vezes é sinal, às vezes gramática | o Jev decide com a opção **OMITIR** (`se`, e `ter` antes de particípio) — "tenho namorado" mantém TER |
| 7 | "se eu fosse gay" → SER; "Sami foi preso" → SER | SER sobrando como única opção, ou escolhido para foi/fui | todo SER escolhido sai (ligação/passiva) |
| 8 | "eu vi você" → 1S_VER_2S **VOCÊ** | o direcional já contém a pessoa | o objeto depois do verbo também é absorvido |
| 9 | absorto → ABORTO, bronca → BRANCA, **insatisfatória → SATISFATÓRIA** | escolha entre vizinhos de grafia: os acertos vêm com confiança ≥ 0,8, os erros abaixo; e o vizinho pode ser o antônimo | `LIMIAR_VIZINHO = 0.8` e veto a prefixo negativo (des-, in-, anti-) → soletra |
| 10 | "está" com candidato ESTA (pronome) | busca sem acento | se o aluno pôs acento, a forma sem acento é outra palavra (está/esta, avó/avô) |
| 11 | Traga-me → TRAGAR; ti, cá, donde, oh, né, demais | formas irregulares ou sem sinal | tabelas `IRREGULARES`, `ABREVIACOES`, `INTERJEICOES`, `INTENSIFICADORES` |
| 12 | palavra de 1 letra fora do dicionário derrubava o servidor (502) | `corrigir()` gerava string vazia | guarda no `corrigir()` |
| 13 | "Tom **não quer** ficar" → TOM QUER (negação apagada!) | a correção nº 4 revertia também o composto do acervo NÃO_QUER, que já contém o "não" | só reverte o que **o Jev** escolheu (`fonte == "jev"`) |
| 14 | "ter tido" → TER TER | teste de particípio exigia > 4 letras | > 3 letras (tido, dito); "ter tido" tira o 1º sem perguntar |
| 15 | "vê-la" → `O` (a letra) | -la/-lo não eram pronome | `OBLIQUOS` ganhou lo/la/los/las |
| 16 | 18% das escolhas marcadas "incerto" (borda tracejada) | o Jev divide a confiança entre VAI e IR, SEUS e SEU, MUITA e MUITO: mesma ideia, outra forma | "incerto" agora usa a confiança da **família** (`_mesma_familia`: lema do dicionário + plural; a negação separa famílias; CASA ≠ CASAR) |
| 17 | "Coloque o casaco. **Está** frio" → E-S-T-Á (nome); idem Estou, Vou, Foi, Diga… no começo da 2ª frase: **48 casos** em 20 mil | só a posição 0 contava como começo de frase; o resto caía na regra "maiúscula no meio = nome" (antes da nº 10 dava ESTA, também errado) | palavra depois de `. ! ? …` conta como começo de frase (`inicios` em `preparar()`); auditoria `codigo` v5 → v5b: só esses 48 mudaram (12/11) |

### Rodada de 5 mil frases (rótulo `v4`, US$ 0,31)

Depois das correções 1–12, antes das 13–16:

- 0 sinais NÃO_X sem negação na frase; 0 glosas vazias; 14 cartões de digitação em 5 mil frases.
- 18 glosas com sinal repetido — quase todas fiéis à frase ("promessa é promessa", "palavra
  por palavra", "Deus, Deus"); só TER TER era bug (nº 14).
- 28 frases com negação e glosa sem — eram o bug nº 13 (e falsos alarmes com `AINDA_NÃO`).
- Re-rodando só as 60 frases afetadas pelos bugs 13–15: **59/60 certas**. A que sobra
  ("Vocês têm de ter cuidado" → TER TER) é o item 2 do backlog ("ter de").
- Nas 2 mil frases em comum com a rodada anterior, 1.864 deram a mesma glosa.

### Rodada de 2 mil frases (rótulo `v5`, 12/11, US$ 0,12)

Mede as correções 13–16 em escala, contra as mesmas 2 mil frases da `v4`:

- **Negação perdida: 0** (a v4 tinha 28). NÃO_X sem negação na frase: 0. Glosas vazias: 0.
- **"Incerto": 18,6% → 3,2%** das escolhas do Jev (confiança bruta × confiança da família).
- 124 de 2.000 glosas mudaram. **46** são as correções: `-lo/-la` saiu (O → nada, 16×; "tê-la"
  não vira mais LÁ), NÃO_QUER voltou (6×), `ter` auxiliar saiu (5×), NÃO X → NÃO_X.
- As outras **~78 são o Jev oscilando** entre formas e sentidos do mesmo sinal: TENHO/TER/TEM,
  VAI/IR, FAZER/FAÇA, NOVO/NOVO&RECENTE, MAIS/MAIS&QUANTIDADE, TEMPO/TEMPO&ÉPOCA. São os itens 4
  e 5 do backlog: fixar a forma tiraria esse ruído de ~4% das frases.
- Achado novo na passada `codigo`: a correção nº 17 (maiúscula depois de ponto).

Custo total da auditoria de 11/11: **~US$ 0,60** (rodadas de 2 mil, 2 mil e 5 mil + testes).

Os negados estão bons: em 2 mil frases, **289 sinais NÃO_X, todos com negação na frase**; o
único sem ("proibido de entrar" → NÃO_ENTRAR) está certo no sentido.

## Backlog aberto

### Precisa de decisão de linguística (do Gustavo)

1. **ESTAR de ligação** — "Maria está em casa" → `MARIA ESTAR CASA`; "ela está ocupada" →
   `ELA ESTAR OCUPADA`. É o mesmo caso do SER (que já sai), mas ESTAR de lugar é menos claro.
   Opções: sair sempre, ou dar ao Jev a opção OMITIR como no `se`.
2. **"ter de / ter que"** (obrigação) — "temos de dizer" → `TER DIZER`. Talvez `DEVER&OBRIGAÇÃO`.
3. **"o que" relativo** — "preocupado com o que vai acontecer" → `O_QUE`. Em pergunta
   embutida ("sei o que você faz") é aceitável; como relativo puro, duvidoso.

### Precisa olhar o vídeo do sinal (não dá para resolver lendo)

4. **Formas conjugadas que são sinais diferentes no acervo** — comparando os arquivos:
   `TEM`/`TENHO` (22.701 bytes) ≠ `TER` (22.391); `VAI` ≠ `IR`; `PRECISA`/`PRECISO` ≠ `PRECISAR`;
   `QUER` ≠ `QUERER`/`QUERO`. Já `GOSTAR`/`GOSTARIA` e `PODE`/`PODER` diferem só pelo nome
   (são o mesmo sinal). O Jev alterna entre as formas (tem → TEM 38×, TER 7×). Vale ver no
   player ou no V-LIBRASIL ([06](06-dataset-vlibrasil.md)) e, se forem equivalentes, fixar o infinitivo.
5. **Sentido dos sinais com `&`** — MAIS&SUPERIOR × MAIS&QUANTIDADE, TEMPO&ÉPOCA × TEMPO,
   BEM&ESTAR em "durmam bem". Só dá para julgar vendo o sinal.
6. **MUITO_BEM, DO_QUE, DE_PÉ** — casam certo na grafia, mas o sentido do sinal não está
   verificado ("ela mente muito bem" → MUITO_BEM).

### Limites conhecidos do Jev (aceitos por ora)

7. **foi/fui de SER em frase clivada** — "Não fui eu que escolhi" → `NÃO_IR EU`.
8. **Pessoa do direcional no imperativo** — "Apenas olhe para ele" → `1S_OLHAR_3S` (seria 2S).
9. **"nos"** — contração (nos jornais) e pronome (ele nos ajudou) caem juntos nas vazias.

### Corretor de digitação

10. Sem lista de frequência, a ordem às vezes erra (amanhan → "amanhar" antes de "amanhã").
11. Palavra com maiúscula no começo da frase e erro "fraco" vira nome: "Felis aniversário"
    soletra F-E-L-I-S. Erro "forte" (letras trocadas, letra repetida: "Vcoê") ainda pergunta.
12. Erro que forma outra palavra válida ("cassa" por "casa") não é detectável sem contexto.
