# 11 — Conjugação verbal: o que dá para consertar sem IA e o que não dá

Investigação feita em 2026-10-22 para responder a uma pergunta direta:
*"certas conjugações verbais não foram adaptadas — dá para fazer algo, ou o ideal é mesmo
seguir com IA?"*

**Resposta curta: as duas coisas. Há ganho real sem IA, mas a classe de erro que mais
incomoda é estruturalmente insolúvel sem semântica. Vá atrás da API de IA.**

---

## Primeiro, desfazendo um mal-entendido: "mordeu" funciona ✅

```
"o rato mordeu a roupa do rei de roma"  →  RATO MORDER ROUPA REI ROMA&CIDADE
```

O tradutor **lematiza "mordeu" corretamente** para `MORDER`, e `MORDER` existe no acervo.

Se no POC apareceu `O RATO MORDEU A ROUPA DO REI DA RUSSIA` em maiúsculas, foi o
**fallback de datilologia** entrando porque a API estava fora do ar naquele instante — o
log registrou `tradução falhou — caindo para datilologia`. Não foi o tradutor errando a
conjugação; foi o tradutor não existindo naquele segundo. (Risco 3 em [10](10-desafios-e-duvidas.md).)

## Quão bem o tradutor conjuga, medido ✅

40 frases com verbos irregulares, em vários tempos e pessoas:

**33 de 40 corretas — 82%.**

Funcionaram, incluindo irregulares difíceis:

| Entrada | Glosa |
|---|---|
| roeu / mordeu / comeu / rasgou | `ROER` / `MORDER` / `COMER` / `RASGAR` |
| comprei · compro · comprarei · vou comprar | `COMPRAR&DINHEIRO` (os 4) |
| fizemos | `FAZER` |
| trouxe | `TRAZER` |
| disse | `DIZER` |
| leu | `LER` |
| soube | `SABER` |
| viemos | `VIR` |
| escreveu · bebeu · perdeu · dormiu · caiu · abriu · pagou | todos no infinitivo correto |

Repare que **os quatro tempos de "comprar" caem na mesma glosa** — e isso está *certo*:
Libras não flexiona o verbo, o tempo vem por advérbio. O tradutor entendeu a regra.

## Os 7 erros — e eles se dividem em dois mundos muito diferentes

### Classe A — erro que o código detecta (dá para consertar sem IA)

| Entrada | Glosa | Problema |
|---|---|---|
| "ele **lê** o jornal" escrito "ele **le** o jornal" | `LE` | `LE` não existe no acervo → vira datilologia |
| "uma **música**" escrito "musica" | `MUSICA` | idem |
| "correu **rápido**" escrito "rapido" | `RAPIDO` | idem |

**A causa é a acentuação da entrada**, e isso é 100% resolvível hoje ✅:

```
SEM acento: "ela cantou uma musica"   → ELA CANTAR MUSICA   ❌ falta bundle
COM acento: "ela cantou uma música"   → ELA CANTAR MÚSICA   ✅
SEM acento: "ele le o jornal"         → ELE LE JORNAL       ❌ falta bundle
COM acento: "ele lê o jornal"         → ELE LER JORNAL      ✅ até o verbo foi corrigido
```

> **Acentue a entrada e o tradutor melhora sozinho.** Pôr um corretor ortográfico antes da
> chamada — ou simplesmente avisar o usuário — é barato e tem retorno imediato.

Além disso, o validador de bundles ([04](04-dicionario-e-bundles.md)) **pega todos esses
casos**, porque o token resultante não existe no acervo. O sistema *sabe* que errou.

### Classe B — erro que o código NÃO detecta 🔴

Aqui mora o problema de verdade:

| Entrada | Glosa | O sinal que o avatar faz |
|---|---|---|
| "eu **pus** o livro na mesa" | `PUS` | o sinal de **pus**, a secreção |
| "ele **quis** sair" | `QUER` | presente em vez de passado |
| "eu **vi** o filme" | `1S_VER_2S` | "eu **te** vi" — objeto errado |
| "ele **pediu** ajuda" | `1S_PEDIR_2S` | "eu **te** pedi" — pessoa errada |

**Verifiquei: `PUS`, `QUER`, `1S_VER_2S` e `1S_PEDIR_2S` todos existem no acervo** ✅.

Ou seja: o validador olha, vê que o bundle existe, e deixa passar. O avatar executa uma
animação perfeitamente válida — e completamente errada. **Não há nenhum sinal técnico de
que algo deu errado.** Só quem entende a frase percebe.

> Esta é a diferença essencial:
> **Classe A é um erro que o sistema consegue admitir. Classe B é um erro que ele comete com confiança.**
> E num app de ensino, confiança errada é o pior defeito possível.

---

## E então veio a descoberta que fecha a discussão

Testando a frase do projeto palavra por palavra:

```
"o rato roeu a roupa do rei"            →  RATO ROER ROUPA REI             ✅
"o rato roeu a roupa do rei de roma"    →  RATO ROEDOR ROUPA REI ROMA      ❌ virou substantivo
"o rato roeu a roupa de roma"           →  RATO ROMA&CIDADE                🔴 sumiu ROER e ROUPA
"o gato roeu a roupa do rei de roma"    →  GATO ROMA&CIDADE ROMA&CIDADE    🔴 colapso
"a rata roeu a roupa do rei de roma"    →  RATA ROMA&CIDADE ROMA&CIDADE    🔴 colapso
"o rato roeu a roupa do rei de paris"   →  RATO ROER ROUPA REI PARIS       ✅ volta a funcionar
```

E então o caso que encerra qualquer dúvida — **o ponto final sozinho destrói a frase**:

```
"O rato roeu a roupa do rei de Roma"    →  RATO ROEDOR ROUPA REI ROMA           ✅ (verbo torto, mas inteira)
"O rato roeu a roupa do rei de Roma."   →  RATO ROMA&CIDADE ROMA&CIDADE [PONTO] 🔴 COLAPSO
                                   ▲
                             um caractere
```

Some o verbo, some `ROUPA`, some `REI`, e `ROMA` aparece duas vezes.
**Reproduzido 5× seguidas: idêntico nas cinco.** Idêntico também entre produção e homologação.
**Não é instabilidade — é determinístico.** O tradutor é consistentemente frágil.

E note a crueldade do padrão: não há regra que o usuário possa aprender.

| Frase | Resultado |
|---|---|
| `O rato roeu a roupa do rei de Roma.` | 🔴 colapsa |
| `A rata roeu a roupa do rei de Roma.` | 🔴 colapsa |
| `O gato roeu a roupa do rei de Roma.` | ✅ funciona |
| `O cachorro roeu a roupa do rei de Roma.` | ✅ funciona |
| `O gato roeu a roupa do rei de Paris.` | ✅ funciona |

Escrever **corretamente** não protege: a versão bem pontuada da frase-símbolo do projeto é
justamente a que quebra. Do ponto de vista de quem usa, é **aleatório**.

### Por que isso acontece

O tradutor é um sistema de regras: analisador morfológico (Aelius), gramática livre de
contexto (NLTK), léxico, lematizador ([08](08-traducao-offline.md)). Ele monta uma árvore
sintática. Quando a árvore falha — porque "roma" também é forma do verbo "romar", porque
"gato" muda a estatística do tagger — ele **não tem como se recuperar**, e simplesmente
descarta os ramos que não encaixaram.

Não existe patch para isso. O sistema não tem o conceito de *sentido* para checar o
resultado contra. E repare na ironia: o `[PONTO]` que derruba a frase é o mesmo marcador
que o modelo neural usa para **segmentar** sentenças ([08](08-traducao-offline.md)) — a
pontuação é um eixo estrutural do pipeline, e é exatamente onde ele se desequilibra.

---

## O veredito

### O que dá para fazer AGORA, sem nenhuma IA

| Ação | Esforço | Ganho |
|---|---|---|
| **Acentuar/corrigir a entrada** | baixo | elimina toda a Classe A |
| **Validar contra `bundles.json`** | baixo | pega Classe A e evita datilologia de lixo |
| **Detectar negação perdida** | baixo | pega `nao gosto`→`GOSTAR` quando o acento falhar |
| **Detectar colapso**: glosa muito mais curta que a frase, ou token repetido em sequência | baixo | pega o caso `RATO ROMA ROMA` e permite avisar |
| **Cache de traduções boas** | baixo | resiliência à queda da API |

Isso já leva o sistema de "erra em silêncio" para "admite quando não sabe" — que é, por si
só, uma mudança de categoria para um app de ensino. **Faça tudo isso antes da IA.**

### O que só a IA resolve

- Classe B inteira (`PUS`, `QUER`, `1S_VER_2S`) — exige entender o sentido da frase
- O colapso contextual (`GATO ROMA ROMA`) — detectável por heurística, **corrigível** só com semântica
- Escolha de desambiguação `&` pelo contexto (`COMPRAR&DINHEIRO` vs outra leitura)
- Intensidade `(+)`/`(-)`, que o tradutor nunca usa
- Escolha da expressão facial ([03](03-player-3d.md))
- A camada pedagógica inteira: *explicar por que* a glosa é assim

> **Sim, vá atrás da API de IA.** O tradutor de regras não é um ponto de partida ruim — ele
> acerta 82% da conjugação e 97% do vocabulário. Mas o teto dele é rígido, e o que fica de
> fora é exatamente aquilo que diferencia um tutor de um tradutor.

### Como encaixar as duas coisas

Não substitua o tradutor pela IA — **empilhe**:

```
texto ──► corretor de acentuação        (código)
      ──► tradutor VLibras              → glosa base, 82% certa, de graça
      ──► heurísticas de alerta         (código: negação sumida? colapso? token faltando?)
      ──► IA, com a glosa base + os alertas + os candidatos do acervo
      ──► validador contra bundles      (código: a IA também alucina)
      ──► player
```

A IA recebe trabalho **já adiantado e já auditado**, em vez de partir do zero. Fica mais
barata, mais rápida e mais fácil de avaliar — porque dá para medir exatamente quanto ela
melhorou sobre a baseline.

E quando ela estiver pronta, o teste de aceitação já existe — a própria frase do projeto:

```
entrada:  "O rato roeu a roupa do rei de Roma."
hoje:      RATO ROMA&CIDADE ROMA&CIDADE [PONTO]     🔴
meta:      RATO ROER ROUPA REI ROMA [PONTO]         ✅
```

Se a camada de IA entregar isso, ela está fazendo o que o motor sozinho jamais faria.
Guarde as 40 frases de verbos deste documento como suíte de regressão: a baseline é 82%,
e agora dá para medir quanto a IA some a isso em vez de confiar na impressão.
