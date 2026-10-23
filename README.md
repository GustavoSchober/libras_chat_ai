<div align="center">

# LIBRAS AI CHAT

### O chat de IA que funciona ao contrário: você não conversa com ele — ele te ensina a conversar.

</div>

---

## O problema

A Libras é reconhecida por lei como meio legal de comunicação e expressão desde 2002.
De um lado há **cerca de 2,2 milhões de brasileiros com surdez total ou dificuldade
auditiva severa** — quase 10 milhões se contarmos qualquer grau de dificuldade. Do outro,
um país que majoritariamente não sabe dizer "bom dia" para eles.

Quem tenta aprender esbarra sempre na mesma parede: material estático. Um dicionário mostra
o sinal de "casa". Um vídeo no YouTube mostra uma frase pronta. Mas **ninguém te mostra a
frase que você quer dizer agora** — e aprender uma língua é exatamente isso: querer dizer
algo e descobrir como.

Existe tradutor automático de português para Libras. Ele traduz. Ele não ensina.
Devolve o resultado e vai embora, sem dizer por que a ordem das palavras mudou, por que o
verbo perdeu a conjugação, por que o rosto do avatar fez aquilo no fim da frase.

## A ideia

**Você digita a frase que quer aprender. Um avatar 3D a sinaliza. E o sistema te explica.**

```
   você escreve ──►  "o rato roeu a roupa do rei de roma"

   o avatar faz ──►  RATO · ROER · ROUPA · REI · ROMA
                      ▲
                      │ destacado em tempo real, sinal por sinal

   e o sistema explica ──►  "Em Libras não há artigos nem preposições de ligação.
                             O verbo vai ao infinitivo — o tempo, quando precisa,
                             vem por um advérbio no começo da frase."
```

Depois você muda a frase para **"o rato mordeu a roupa do rei da Rússia"** — e o sistema
não recomeça do zero. Ele mostra o que mudou:

> **2 sinais diferentes.** `ROER` → `MORDER`, `ROMA` → `RÚSSIA`.
> O resto é idêntico. Pratique só esses dois.

É essa a diferença entre um tradutor e um professor: o professor sabe o que você já sabe.

## Por que isto não é mais um tradutor

| Tradutor | **LIBRAS AI CHAT** |
|---|---|
| texto entra, sinal sai | texto entra, **lição** sai |
| otimiza fidelidade | otimiza **aprendizado** |
| a frase inteira de uma vez | sinal a sinal, com o porquê |
| não sabe quem é você | acompanha o que você já domina |
| erra em silêncio | **avisa** quando não tem certeza |

Esse último ponto é o coração do produto. Num app de ensino, um erro confiante é pior que
um erro admitido — porque o aluno **copia**. Este projeto nasceu com a premissa de que
dizer "aqui eu não sei" é funcionalidade, não falha.

E ela já está implementada: o protótipo valida cada sinal contra o acervo, detecta quando a
tradução encolheu demais, quando um sinal apareceu repetido e quando a negação da frase
sumiu — avisando na tela em vez de sinalizar em silêncio.

## Como funciona

Três camadas. A de baixo já está pronta e provada; a do meio é onde a IA entra.

```
┌─ PEDAGOGIA ───────────────────────────────────────────────────────────┐
│  decompõe a frase em lição · explica a gramática · mostra o vídeo de  │
│  uma pessoa real sinalizando · compara versões · acompanha progresso  │
├─ INTELIGÊNCIA ────────────────────────────────── ◄── a IA entra aqui ─┤
│  corrige a gramática · escolhe o sentido pelo contexto · valida cada  │
│  sinal contra o acervo · define a expressão facial da frase           │
├─ MOTOR ────────────────────────────────────────────── ✅ funcionando ─┤
│  avatar 3D (24.213 sinais) · tradutor base · 4.086 vídeos de          │
│  sinalizadores humanos reais                                          │
└───────────────────────────────────────────────────────────────────────┘
```

**O que já existe e foi testado ponta a ponta:** o avatar carrega, recebe uma frase,
sinaliza, e devolve em tempo real qual sinal está executando — o que permite destacar a
palavra correspondente na tela. Rode `poc/index.html` e veja.

## O ativo escondido: 4.086 vídeos de pessoas reais

Além do avatar, o projeto tem acesso ao corpus **V-LIBRASIL**: 1.364 sinais gravados por
**três sinalizadores diferentes** cada um — porque sinal, como sotaque, varia de pessoa
para pessoa.

Isso ataca o problema mais antigo dos avatares 3D: eles são corretos, mas sem alma.
Quando o aluno quiser ver *como uma pessoa de verdade faz*, está lá. E quando o avatar não
souber um sinal — são **269 casos** — em vez de soletrar letra por letra, o app mostra o
ser humano. Uma falha vira uma funcionalidade melhor que o original.

## Onde a IA é indispensável — e por quê

Esta não é a parte onde se escreve "usamos IA" porque soa bem. O tradutor automático
disponível hoje tem um teto, e ele foi **medido**:

| Caso real testado | Resultado | O que deveria ser |
|---|---|---|
| "eu **pus** o livro na mesa" | `PUS` | o sinal de *pus*, a secreção. Não o verbo pôr |
| "eu **vi** o filme" | `1S_VER_2S` | "eu **te** vi" — pessoa errada |
| "ele **quis** sair" | `QUER` | presente no lugar do passado |
| "O rato roeu a roupa do rei de Roma**.**" | `RATO ROMA ROMA` | a frase inteira, menos um ponto final |

**O último encerra a discussão.** É a frase símbolo do projeto, escrita corretamente. Sem o
ponto final, o tradutor devolve `RATO ROEDOR ROUPA REI ROMA`. Com o ponto final — ou seja,
**escrita do jeito certo** — devolve `RATO ROMA ROMA`: perde o verbo, perde "roupa",
perde "rei", e repete "Roma" duas vezes.

Um caractere. Cinco execuções, resultado idêntico nas cinco. Não é instabilidade: é a
fragilidade estrutural de um sistema que analisa sintaxe sem nunca entender sentido.
E o usuário não tem como aprender a evitar, porque não há regra — "O cachorro roeu a roupa
do rei de Roma." funciona perfeitamente.

Repare também nos três primeiros casos: todos produzem um sinal que **existe** no acervo.
Nenhuma validação automática os detecta. O avatar executa com perfeição a coisa errada.
É a fronteira exata entre o erro que um sistema consegue admitir e o erro que ele comete
com confiança — e só a segunda categoria exige semântica.

> **Nota de validação:** o próprio VLibras chegou à mesma conclusão. A versão 2026 do
> tradutor oficial do governo incluiu um estágio opcional de refinamento de glosa por LLM.
> Estamos na mesma direção, com a liberdade de ir mais longe.

## O estado hoje

| | |
|---|---|
| ✅ **Motor funcionando** | avatar 3D sinalizando frases arbitrárias, validado no navegador |
| ✅ **Terreno mapeado** | 12 documentos técnicos, tudo verificado executando, não lendo |
| ✅ **Acervo em mãos** | 24.213 sinais do avatar + 1.364 sinais em vídeo humano |
| ✅ **Rede de segurança** | validação de glosa + heurísticas que detectam tradução quebrada |
| ✅ **Riscos medidos** | documentados com mitigação definida, não como suposição |
| 🔜 **Camada de IA** | arquitetura e contrato definidos; aguardando a API de um modelo |
| 🔜 **Camada pedagógica** | onde o produto vira produto |

### Próximos passos

1. **UI didática** — glosa token a token, destaque sincronizado, controles de ritmo
2. **Vídeo humano lado a lado** — mapear glosa → V-LIBRASIL
3. **Camada de IA** — backend fino; teste de aceitação já escrito:
   `"O rato roeu a roupa do rei de Roma."` precisa sair `RATO ROER ROUPA REI ROMA [PONTO]`
4. **Comparação entre versões** — "mudaram 2 sinais, pratique só esses"
5. **Progresso do aluno** — repetição espaçada

Nada antes do passo 3 depende de IA, e já é um produto útil.

## Rodando

```bash
python3 -m http.server 8080
# abra http://localhost:8080/poc/index.html
```

A primeira carga baixa ~20 MB do avatar. Depois é instantâneo.
Não há build, não há dependências, não há backend.

## Estrutura

```
README.md       este arquivo
KNOWLEDGE/      base de conhecimento técnica — comece por 00-INDEX.md
poc/            prova de conceito funcional (um HTML, sem build)
dados/          snapshots versionados: 24.213 sinais do avatar + índice do corpus
                └ atualizar.sh regenera tudo a partir das fontes
```

Duas pastas ficam **fora do Git** (ver `.gitignore`), por serem material de terceiros,
pesado e já destilado em `KNOWLEDGE/`:

| Pasta | O que é | Onde achar de novo |
|---|---|---|
| `how_to_act/` | PDFs e docs de origem do VLibras (3,0 MB) | `KNOWLEDGE/FONTES.md` |
| `3dchar/` | rig 3D do avatar padrão, Blender (2,3 MB) | `KNOWLEDGE/FONTES.md` |

## Uma honestidade necessária

Este projeto é para **ouvintes aprendendo Libras**. Não é uma ferramenta de acessibilidade
para pessoas surdas — são necessidades opostas, e confundi-las seria desrespeitoso com
quem a língua pertence.

Avatares 3D são, com razão, criticados pela comunidade surda: expressão facial pobre, ritmo
artificial, ausência das marcações que fazem a língua ser língua. Usamos o avatar porque ele
permite frases infinitas, e o vídeo humano porque ele tem o que o avatar não tem. **Validar
com pessoas surdas não é etapa opcional deste roadmap — é o que separa uma ferramenta útil
de mais um aplicativo feito sobre uma comunidade em vez de com ela.**

---

<div align="center">

Construído sobre a suíte **VLibras** (LAViD/UFPB + Secretaria de Governo Digital, LGPLv3)
e o corpus **V-LIBRASIL**. Licenças e fontes em [`KNOWLEDGE/FONTES.md`](KNOWLEDGE/FONTES.md).

</div>
