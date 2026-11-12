// Quem decide QUAIS sinais: o Jev (via ia/servidor.py) e, se ele cair, o tradutor do governo.
// Os sinais em si vêm sempre do acervo do governo (dicionario2.vlibras.gov.br).

export type Item = {
  tok: string
  ok: boolean
  palavra?: string
  confianca?: number
  alternativas?: [string, number][]
  incerto?: boolean
  nota?: string
  sugestoes?: string[] // parece erro de digitação: o aluno escolhe antes do avatar sinalizar
}

export type Emocao = { metodo: string; intensidade: string; emocao: string }

export type Resultado = {
  motor: 'jev' | 'codigo' | 'vlibras'
  modelo?: string
  ms?: number
  itens: Item[]
  descartadas?: { palavra: string; nota: string }[]
  notas?: string[]
  emocao?: Emocao | null
  avisos: string[]
}

const ENDPOINTS = [
  'https://traducao2.vlibras.gov.br/translate',
  'https://traducao2-dth.vlibras.gov.br/translate',
]

export async function saudeIA(): Promise<{ ok: boolean; erro?: string }> {
  try {
    const r = await fetch('/api/saude', { cache: 'no-store' })
    const j = await r.json()
    return { ok: !!j.ok, erro: j.erro ?? undefined }
  } catch {
    return { ok: false, erro: 'o servidor do projeto não está rodando' }
  }
}

async function glosarComJev(texto: string) {
  const ctl = new AbortController()
  const t = setTimeout(() => ctl.abort(), 5000)
  try {
    const r = await fetch('/api/glosa', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto }),
      signal: ctl.signal,
    })
    if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + (await r.text()).slice(0, 200))
    return await r.json()
  } catch (e) {
    console.warn('motor Jev indisponível — usando o tradutor do governo', e)
    return null
  } finally {
    clearTimeout(t)
  }
}

// existem em português, mas não são sinalizadas em Libras
const VAZIAS = new Set(['DE', 'DA', 'DO', 'DAS', 'DOS', 'A', 'O', 'AS', 'OS', 'UM', 'UMA', 'UNS', 'UMAS',
  'EM', 'NO', 'NA', 'NOS', 'NAS', 'AO', 'À', 'PARA', 'PRA', 'POR', 'COM', 'QUE', 'E', 'É', 'SE', 'SEU', 'SUA'])

// a API de produção cai de vez em quando; prod e homologação costumam cair juntas
async function traduzir(texto: string): Promise<{ glosa: string; degradado: boolean }> {
  for (let tentativa = 0; tentativa < 3; tentativa++) {
    for (const ep of ENDPOINTS) {
      try {
        const r = await fetch(ep, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: texto }),
        })
        if (r.ok) return { glosa: (await r.text()).trim(), degradado: false } // text/plain
      } catch { /* tenta o próximo */ }
    }
    await new Promise(r => setTimeout(r, 1200))
  }
  // NÃO devolve o texto cru: GOSTO casaria por acidente com o sinal de "sabor".
  const glosa = texto.toUpperCase().split(/\s+/).filter(p => p && !VAZIAS.has(p)).join(' ')
  return { glosa, degradado: true }
}

let bundles: Promise<Set<string> | null> | null = null
const acervo = () => (bundles ??= fetch('/dados/bundles.json')
  .then(r => r.json()).then(b => new Set<string>(b)).catch(() => null))

async function validar(glosa: string): Promise<Item[]> {
  const B = await acervo()
  return glosa.split(/\s+/).filter(Boolean).map(tok => {
    if (!B || B.has(tok)) return { tok, ok: true }
    const dir = tok.match(/^[123][SP]_(.+?)_[123][SP]$/) // 1S_IR_2S -> IR
    if (dir && B.has(dir[1])) return { tok: dir[1], ok: true, nota: `${tok} não existe; usando ${dir[1]}` }
    const base = tok.split('&')[0] // COMPRAR&DINHEIRO -> COMPRAR
    if (B.has(base)) return { tok: base, ok: true, nota: `${tok} não existe; usando ${base}` }
    return { tok, ok: false, nota: `${tok} será soletrado` }
  })
}

const NEGACOES = /\b(não|nao|nunca|jamais|nenhum|nenhuma|nada|ninguém|ninguem)\b/i

// heurísticas que pegam erro do tradutor do governo sem precisar de IA
function auditar(texto: string, itens: Item[]) {
  const avisos: string[] = []
  const toks = itens.map(i => i.tok)
  if (NEGACOES.test(texto) && !toks.some(t => /^(NÃO|NUNCA|NADA|NENHUM)/.test(t)))
    avisos.push('A frase tem negação, mas a glosa não. O sinal pode dizer o contrário.')
  const palavras = texto.split(/\s+/).filter(p => p.length > 2).length
  if (palavras >= 5 && toks.length < palavras / 2)
    avisos.push('A tradução encolheu muito e pode ter perdido palavras.')
  for (let i = 1; i < toks.length; i++)
    if (toks[i] === toks[i - 1]) { avisos.push(`"${toks[i]}" saiu repetido, sinal de tradução quebrada.`); break }
  if (itens.some(i => !i.ok) && !/[áàâãéêíóôõúç]/i.test(texto))
    avisos.push('O texto está sem acentos. Acentuar costuma resolver o sinal que falta.')
  return avisos
}

export async function glosar(texto: string): Promise<Resultado> {
  const j = await glosarComJev(texto)
  if (j) {
    const itens: Item[] = j.itens // já validados no servidor
    const avisos = itens.some(i => i.incerto)
      ? ['A IA não teve certeza de um sinal (borda tracejada). Passe o mouse para ver as alternativas.']
      : []
    return { ...j, avisos }
  }
  const { glosa, degradado } = await traduzir(texto)
  const itens = await validar(glosa)
  const avisos = auditar(texto, itens)
  if (degradado) avisos.unshift('O tradutor está fora do ar. Isto é soletração palavra a palavra, não Libras. Não use para aprender.')
  return { motor: 'vlibras', itens, avisos }
}
