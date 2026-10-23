# 10 — Desafios, riscos e dúvidas já respondidas

Você pediu para eu antecipar os problemas. Aqui estão, por ordem de dor.

---

## 🔴 Risco 1 — Glosa sem bundle vira lixo silencioso

**O quê:** token sem AssetBundle não dá erro. O player tenta soletrá-lo literalmente.
Medido ✅: `1S_IR_2S` numa frase de 6 glosas manteve a animação em `[1,6]` por 14 s e levou
mais 25 s para chegar a `[5,6]`. Zero eventos de erro.

**Por que é o pior risco de todos:** num app de *ensino*, o aluno copia o que vê. Um sinal
errado ensinado com confiança é pior que nenhum sinal.

**Mitigação:** validar todo token contra `bundles.json` antes de `playNow`. Função pronta
em [04](04-dicionario-e-bundles.md). Faça isso no passo 2 do roteiro, não no passo 9.

---

## 🔴 Risco 2 — O sinal existe, está válido, e está errado

**O quê:** há uma classe de erro em que o tradutor produz um token que **tem bundle** e é
semanticamente errado. O validador não pega, o player não reclama, o avatar sinaliza com
perfeição a coisa errada.

Medidos ✅: "eu **pus** o livro" → `PUS` (a secreção); "eu **vi** o filme" → `1S_VER_2S`
("eu *te* vi"); "ele **quis** sair" → `QUER` (presente). Todos existem no acervo.

**Por que é o risco nº 1 real:** o Risco 1 (abaixo) o sistema *consegue admitir*. Este ele
comete com confiança total. Não há sinal técnico nenhum.

**Mitigação:** só semântica resolve → é a justificativa central da camada de IA.
Medição completa e o que dá para fazer antes disso em
[11](11-conjugacao-verbal-e-o-teto-das-regras.md).

---

## 🔴 Risco 2c — Colapso contextual: a frase encolhe sozinha

**O quê:** uma mudança mínima no texto faz o tradutor **descartar metade da frase**.
Medido e reproduzido 5× ✅:

```
"O rato roeu a roupa do rei de Roma"    → RATO ROEDOR ROUPA REI ROMA
"O rato roeu a roupa do rei de Roma."   → RATO ROMA&CIDADE ROMA&CIDADE [PONTO]   🔴
                                  ▲
                            um ponto final
```

Some o verbo, some "roupa", some "rei", e "Roma" aparece duas vezes. E não há regra:
`"O cachorro roeu a roupa do rei de Roma."` funciona perfeitamente.

**Mitigação:** heurísticas que **detectam** (já implementadas no POC) — glosa muito mais
curta que a frase, token repetido em sequência. Elas não consertam, mas permitem avisar.
Consertar exige semântica → camada de IA. Ver [11](11-conjugacao-verbal-e-o-teto-das-regras.md).

---

## 🟠 Risco 2b — A negação se perde (quando falta acento)

**O quê:** `Eu nao gosto de futebol` → `GOSTAR FUTEBOL` — o app ensinaria o oposto.

**⚠️ Correção de uma afirmação anterior:** eu havia registrado isso como falha intrínseca
do tradutor. Não é. Com a acentuação correta, `Eu não gosto de futebol` → `NÃO_GOSTAR
FUTEBOL` ✅. O erro estava na minha entrada de teste, não no tradutor. Baixei de 🔴 para 🟠.

Ainda assim merece guarda: o usuário real digita sem acento o tempo todo.

**Mitigação:** (a) corrigir acentuação da entrada — resolve a maioria; (b) teste de sanidade:
se a frase tem marca de negação (`não`, `nunca`, `jamais`, `nenhum`, `nada`) e a glosa não
tem nada que a carregue, **avise** (implementado no POC); (c) a camada LLM cobre o resto.

---

## 🔴 Risco 3 — A API cai (e os dois ambientes caem juntos)

**O quê:** `500 {"error":"Translation Core Unavailable"}` quatro vezes em duas horas de
apuração ✅. É o worker Python da fila morrendo atrás do Express.

**O agravante que eu só descobri testando o POC:** numa das quedas, **prod e homologação
estavam fora ao mesmo tempo** (500 e 503), com `x-ratelimit-remaining: 273` — ou seja,
não era limite nosso, era queda real e correlacionada.

Subi este risco de 🟠 para 🔴 por isso: **a estratégia de fallback entre ambientes é ilusória.**
Eles compartilham infraestrutura e caem juntos.

**Mitigação em camadas:**
1. **cache de tradução** por frase (localStorage) — mais barato e mais eficaz do que parece,
   porque um tutor repete as mesmas frases;
2. cadeia prod → dth → retry → `texto.toUpperCase()` ([02](02-api-traducao.md)) — cobre a
   queda de um só;
3. **tradutor local** ([08](08-traducao-offline.md)) — a única resiliência de verdade. Se
   o app precisar funcionar em demo ou em sala de aula, faça isso antes da demo.

---

## 🟠 Risco 4 — 20 MB de player na primeira visita

**O quê:** medido ✅ — 16,99 MB de dados + 3 MB de wasm. ~5 s numa conexão boa, bem pior no 4G.

**Mitigação:** carregue o iframe **imediatamente**, em paralelo com a UI; mostre o progresso
(evento `update_progress` dá 0..1); deixe a caixa de texto utilizável antes do player pronto e
enfileire a primeira frase. Não é bloqueador, é questão de percepção.

---

## 🟠 Risco 5 — Dependência de uma infraestrutura de terceiros

**O quê:** o projeto inteiro depende de `vlibras.gov.br` e `dicionario2.vlibras.gov.br`.
Se o governo mudar URL, versão ou fechar CORS, quebramos.

**Sinais de que isso é real:** a arquitetura **já mudou** entre v5 e v7 (de `SendMessage`
direto para iframe + `postMessage`). O `/dl/translate` **já fechou** com 401.

**Mitigação:** espelhe os ~20 MB do player e o `bundles.json` no nosso repo. Tudo é
LGPLv3 — é permitido. Mantenha uma flag `PLAYER_BASE` para alternar remoto/local. Fixe
versão via jsDelivr (`vlibras-portal@v7.12.2`) em vez de usar `main`.

---

## 🟡 Risco 6 — Rate limit no trabalho em lote

300 req/janela (~1 min) por IP. Um chat nunca chega perto. **Pré-processar 1.364 sinais
ou montar corpus de avaliação chega em minutos.** Para lote: tradutor local ([08](08-traducao-offline.md)).

---

## 🟡 Risco 7 — O dataset não é consultável

Só a coluna `video`; `search: false`. Resolver com `metadata.csv` ([06](06-dataset-vlibrasil.md)).
Faça cedo — todo script que escrevermos antes disso vira gambiarra de parsing de nome de arquivo.

---

## 🟡 Risco 8 — LLM alucinando glosa

Um LLM vai inventar `CORRER_RAPIDO` com toda a confiança do mundo. **Nunca mande saída de
LLM direto ao player.** Sempre: LLM → validador → player. E dê candidatos no prompt em vez
de pedir invenção livre.

---

## Dúvidas que você provavelmente teria — já respondidas

**"Preciso de backend?"**
Só para esconder a chave do LLM. Tradução e player funcionam direto do browser: CORS
totalmente aberto nos dois ✅.

**"Dá para usar o boneco sem o widget oficial?"**
Sim. `<iframe src="https://vlibras.gov.br/app/unity/index.html">` + `postMessage`.
Sem X-Frame-Options, `access-control-allow-origin: *` ✅. Código completo em [03](03-player-3d.md).

**"Dá para mandar glosa pronta, pulando o tradutor?"**
Sim, e é a chave do projeto. `playNow` com `'ABACAXI AMANHÃ COMPRAR'` funcionou ✅.
Nossa IA pode gerar a glosa direto.

**"Dá para funcionar offline?"**
Em parte. Player: espelhando os 20 MB, sim. Bundles: são 24 mil arquivos de ~32 KB
(~775 MB estimados) — espelhe só o vocabulário que você usa. Tradutor: sim, via pip ([08](08-traducao-offline.md)).

**"Quantos sinais o avatar sabe?"** 24.213 ✅. **"Quantos estão no meu dataset?"** 1.364,
dos quais ~1.095 (80%) o avatar também sabe.

**"A acentuação da entrada importa?"**
**Muito**, e é a melhoria mais barata do projeto ✅. "musica" → `MUSICA` (não existe, soletra);
"música" → `MÚSICA` ✅. "ele le o jornal" → `LE` (soletra); "ele lê o jornal" → `LER` ✅ —
o acento corrigiu até a lematização do verbo. Passe um corretor ortográfico antes da chamada,
ou no mínimo avise o usuário.

**"O tradutor é determinístico?"**
Sim ✅. Mesma frase → mesma glosa, sempre, e produção e homologação concordam. Isso é bom:
dá para cachear com segurança e escrever testes de regressão.

**"O que acontece com nome próprio?"**
Datilologia — o avatar soletra. `GUSTAVO` reportou `counter_gloss [1,1]` ✅: conta como um
item de glosa, executa 7 configurações de mão. Comportamento **correto** em Libras.

**"Dá para controlar a expressão facial?"**
Sim: `EmotionBridge` com 8 emoções × 3 intensidades ✅. E a pontuação (`[INTERROGAÇÃO]`)
já é expressão facial embutida na glosa.

**"Dá para criar um sinal novo?"**
Na prática, não. O player consome AssetBundle do Unity 2018.3.1, e o pipeline de exportação
do WikiLibras não é público ([07](07-wikilibras-e-rig-3d.md)). Para sinais faltantes, use o
vídeo humano do V-LIBRASIL.

**"Posso usar isso comercialmente?"**
LGPLv3 nos repos VLibras: nosso app por cima é nosso; modificações na biblioteca deles voltam
como LGPL. Os bundles e o avatar são do governo — usá-los via API pública é o uso pretendido;
**redistribuir** é outra conversa. Para qualquer coisa comercial séria, confirme com o LAViD/SGD.
O V-LIBRASIL tem licença própria — **verifique antes de publicar qualquer coisa derivada dele.**

**"E a acessibilidade de verdade?"**
Pergunta certa, e a mais importante: o público-alvo deste projeto é **ouvinte aprendendo
Libras**, não pessoa surda. São necessidades opostas. Não venda como ferramenta de
acessibilidade — e, se possível, **valide com pessoas surdas**: avatares 3D são
notoriamente criticados pela comunidade surda por expressão facial pobre e ritmo artificial.

---

## O que ainda não sei (honestamente)

| Pergunta | Como descobrir |
|---|---|
| A janela do rate limit é 60 s mesmo? | o `x-ratelimit-reset` não caiu em fronteira redonda; medir ao longo de alguns minutos |
| Quantos dos 24.213 bundles realmente existem no servidor? | a lista é o índice; só amostragem confirma. Testei 2, ambos 200 |
| `setRegion` terá outras regiões um dia? | hoje só `BR` ✅; o widget tem UI para mais |
| O modelo neural melhora os erros que medimos? | instalar local e comparar `rbmt_glosa` vs `nmt_glosa` nas mesmas 10 frases |
| Licença exata do V-LIBRASIL | o dataset no HF está sem campo `license` preenchido — convém declarar |
| Qual a latência real do LLM no fluxo | depende do modelo; medir quando a camada 2 existir |

Nenhuma dessas bloqueia começar.
