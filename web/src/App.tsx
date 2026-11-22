import { lazy, Suspense, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { glosar, saudeIA, type Item, type Resultado } from './glosa'
import { PLAYER_URL, usePlayer } from './player'

// o MediaPipe só é baixado quando o aluno abre a aba Praticar
const Praticar = lazy(() => import('./Praticar'))

type Turno = { id: number; texto: string; r?: Resultado; soletrar?: string[] }

// a primeira palavra que parece erro de digitação e o aluno ainda não decidiu
const duvida = (t: Turno) => t.r?.itens.find(i => i.sugestoes?.length && !t.soletrar?.includes(i.palavra!))

const SUGESTOES = [
  'O rato roeu a roupa do rei de Roma.',
  'Eu não gosto de futebol.',
  'Amanhã vou comprar abacaxi.',
]
// só no placeholder digitado; os botões da tela inicial mostram apenas SUGESTOES
const DIGITADAS = [
  ...SUGESTOES,
  'Hoje eu acordei cedo porque precisava ir trabalhar.',
  'Você gosta de estudar ou prefere aprender na prática?',
  'Amanhã vou à igreja participar da Santa Missa.',
  'Minha família gosta de viajar durante as férias.',
  'Você pode me ajudar a encontrar meu celular?',
  'Ontem choveu muito, mas hoje o dia está ensolarado.',
  'Eu quero aprender Libras para conversar com pessoas surdas.',
  'Onde você mora e há quanto tempo vive nessa cidade?',
  'No próximo sábado teremos um encontro com os jovens da comunidade.',
  'Deus nos ensina a amar o próximo e ajudar quem precisa.',
]
const VELOCIDADES = [0.5, 1, 1.5, 2]

export default function App() {
  const p = usePlayer()
  const [aba, setAba] = useState<'conversar' | 'praticar'>('conversar')
  const [turnos, setTurnos] = useState<Turno[]>([])
  const [ativo, setAtivo] = useState<number | null>(null)
  const [inicio, setInicio] = useState(0) // sinal isolado: o player conta do 0, a glosa não
  const [solo, setSolo] = useState(false)
  const [texto, setTexto] = useState('')
  const [ia, setIa] = useState<{ ok: boolean; erro?: string } | null>(null)
  const [tema, setTema] = useState(() => document.documentElement.dataset.tema || 'claro')
  const lista = useRef<HTMLOListElement>(null)
  const caixa = useRef<HTMLTextAreaElement>(null)
  const dica = useDigitando(DIGITADAS, !texto)

  useEffect(() => { saudeIA().then(setIa) }, [])
  useEffect(() => {
    const html = document.documentElement
    if (html.dataset.tema === tema) return
    // as cores mudam rápido, mas não de estalo; a classe sai quando a transição acaba
    html.classList.add('trocando-tema')
    html.dataset.tema = tema
    const t = setTimeout(() => html.classList.remove('trocando-tema'), 400)
    try { localStorage.setItem('tema', tema) } catch { /* sem storage */ }
    return () => clearTimeout(t)
  }, [tema])
  useEffect(() => { lista.current?.lastElementChild?.scrollIntoView({ block: 'end', behavior: 'smooth' }) }, [turnos.length])

  const turnoAtivo = turnos.find(t => t.id === ativo)
  const itensAtivos = turnoAtivo?.r?.itens ?? []
  const agora = p.atual >= 0 ? inicio + p.atual : -1

  function tocarTurno(t: Turno) {
    if (!t.r || duvida(t)) return
    setAtivo(t.id); setInicio(0); setSolo(false)
    p.tocar(t.r.itens.map(i => i.tok), t.r.emocao)
  }

  function tocarSinal(t: Turno, k: number) {
    if (!t.r || !p.pronto) return
    setAtivo(t.id); setInicio(k); setSolo(true)
    p.tocar([t.r.itens[k].tok], t.r.emocao)
  }

  async function enviar(frase: string, id = Date.now()) {
    frase = frase.trim()
    if (!frase || !p.pronto) return
    setTexto('')
    setTurnos(ts => ts.some(x => x.id === id) ? ts.map(x => (x.id === id ? { id, texto: frase } : x)) : [...ts, { id, texto: frase }])
    setAtivo(id)
    const r = await glosar(frase)
    if (r.motor === 'vlibras') setIa(s => (s?.ok ? { ok: false, erro: 'o motor de IA não respondeu' } : s))
    const t = { id, texto: frase, r }
    setTurnos(ts => ts.map(x => (x.id === id ? t : x)))
    tocarTurno(t)
  }

  // respostas do cartão "Você quis dizer?"
  function corrigir(t: Turno, errada: string, certa: string) {
    const re = new RegExp(`(?<![\\p{L}\\p{N}])${errada.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![\\p{L}\\p{N}])`, 'u')
    enviar(t.texto.replace(re, certa), t.id)
  }
  function soletrar(t: Turno, palavra: string) {
    const novo = { ...t, soletrar: [...(t.soletrar ?? []), palavra] }
    setTurnos(ts => ts.map(x => (x.id === t.id ? novo : x)))
    tocarTurno(novo)
  }
  function reescrever(t: Turno) {
    setTurnos(ts => ts.filter(x => x.id !== t.id))
    setTexto(t.texto)
    caixa.current?.focus()
  }

  const onSubmit = (e: FormEvent) => { e.preventDefault(); enviar(texto) }
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(texto) }
  }

  const sinal = agora >= 0 ? itensAtivos[agora] : undefined
  const escuro = tema === 'escuro'

  return (
    <div className="app">
      <a className="pular" href="#frase">Pular para a caixa de frase</a>
      <header className="topo">
        <span className="marca">Libras <b>AI</b> Chat</span>
        <div className="topo-dir">
          <nav className="abas" aria-label="Seções">
            {(['conversar', 'praticar'] as const).map(a => (
              <button key={a} type="button" className="aba" aria-current={aba === a ? 'page' : undefined} onClick={() => setAba(a)}>
                {a === 'conversar' ? 'Conversar' : 'Praticar'}
              </button>
            ))}
          </nav>
          <span className={'status ' + (ia === null ? '' : ia.ok ? 'ok' : 'off')} role="status">
            {ia === null ? 'Verificando a IA' : ia.ok ? 'IA ligada' : 'IA desligada'}
          </span>
          <button type="button" className="tema" onClick={() => setTema(escuro ? 'claro' : 'escuro')}
            aria-label={escuro ? 'Usar tema claro' : 'Usar tema escuro'} title={escuro ? 'Tema claro' : 'Tema escuro'}>
            {escuro
              ? <Svg d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />
              : <Svg d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z" />}
          </button>
        </div>
      </header>

      <main className={'principal' + (aba === 'praticar' ? ' praticar' : '')}>
        {/* o avatar é o mesmo iframe nas duas abas: trocar de aba não recarrega o Unity */}
        {aba === 'praticar' && <Suspense><Praticar /></Suspense>}
        <section className="palco" aria-label="Avatar">
          <div className="avatar">
            <iframe ref={p.ref} src={PLAYER_URL} title="Avatar 3D do VLibras sinalizando a frase"
              tabIndex={-1} sandbox="allow-scripts allow-same-origin" className={p.visivel ? 'visivel' : ''} />
            {!p.visivel && (
              <div className="carregando"><Orbita rotulo="Carregando o avatar" /></div>
            )}
          </div>

          <div className="legenda" aria-live="polite">
            {sinal ? (
              <>
                <span className="legenda-tok">{sinal.tok}</span>
                <span className="legenda-meta">
                  {sinal.palavra && sinal.palavra !== sinal.tok ? `“${sinal.palavra}”` : ''}
                  {solo ? '' : `${sinal.palavra && sinal.palavra !== sinal.tok ? ' · ' : ''}sinal ${agora + 1} de ${itensAtivos.length}`}
                </span>
              </>
            ) : (
              <span className="legenda-meta">{!turnoAtivo?.r ? ' ' : duvida(turnoAtivo) ? 'Confirme a palavra ao lado para o avatar sinalizar.' : 'Clique em um sinal da frase para ver só ele.'}</span>
            )}
          </div>

          <div className="controles">
            <button type="button" className="icone" onClick={() => turnoAtivo && tocarTurno(turnoAtivo)}
              disabled={!turnoAtivo?.r || !!duvida(turnoAtivo)} aria-label="Repetir a frase">
              <Svg d="M4 12a8 8 0 1 0 2.4-5.7M4 4v4h4" /> <span>Repetir</span>
            </button>
            <button type="button" className="icone" onClick={p.pausar} disabled={p.atual < 0}
              aria-label={p.pausado ? 'Continuar' : 'Pausar'}>
              {p.pausado ? <Svg d="M7 5l12 7-12 7z" /> : <Svg d="M8 5v14M16 5v14" />}
            </button>
            <button type="button" className="icone" onClick={p.parar} disabled={p.atual < 0} aria-label="Parar">
              <Svg d="M6 6h12v12H6z" />
            </button>
            <div className="seg vel" role="group" aria-label="Velocidade do avatar">
              {VELOCIDADES.map(v => (
                <button key={v} type="button" aria-pressed={p.velocidade === v} onClick={() => p.setVelocidade(v)}>
                  {String(v).replace('.', ',')}×
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="conversa" aria-label="Frases">
          {ia && !ia.ok && (
            <div className="alerta" role="alert">
              <b>IA desligada: {ia.erro}.</b> As frases vão para o tradutor do governo, que erra
              (ex.: <code>RATO ROEDOR</code>, negação perdida). Rode <code>npm run dev</code> na pasta do projeto.
            </div>
          )}

          {turnos.length === 0 ? (
            <div className="vazio">
              <h1>Escreva o que você quer dizer. O avatar mostra como é em Libras.</h1>
              <p>Cada sinal acende enquanto é feito. Comece por uma destas:</p>
              <ul>
                {SUGESTOES.map(s => (
                  <li key={s}><button type="button" className="sugestao" disabled={!p.pronto} onClick={() => enviar(s)}>{s}</button></li>
                ))}
              </ul>
            </div>
          ) : (
            <ol className="turnos" ref={lista}>
              {turnos.map(t => (
                <li key={t.id} className={'turno' + (t.id === ativo ? ' ativo' : '')}>
                  <p className="frase">{t.texto}</p>
                  {!t.r ? <Orbita /> : duvida(t) ? (
                    <Duvida it={duvida(t)!} onCorrigir={c => corrigir(t, duvida(t)!.palavra!, c)}
                      onSoletrar={() => soletrar(t, duvida(t)!.palavra!)} onReescrever={() => reescrever(t)} />
                  ) : (
                    <>
                      <Glosa itens={t.r.itens} atual={t.id === ativo ? agora : -1} onSinal={k => tocarSinal(t, k)} />
                      {t.r.avisos.map(a => <p key={a} className="aviso">{a}</p>)}
                      <Notas r={t.r} />
                      <Pe t={t} ativo={t.id === ativo} onVer={() => tocarTurno(t)} />
                    </>
                  )}
                </li>
              ))}
            </ol>
          )}

          <form className="compositor" onSubmit={onSubmit}>
            <label htmlFor="frase" className="sr">Frase em português</label>
            <textarea id="frase" ref={caixa} rows={1} value={texto} maxLength={500} placeholder={dica}
              onChange={e => setTexto(e.target.value)} onKeyDown={onKey} />
            <button type="submit" className="enviar" disabled={!p.pronto || !texto.trim()}>
              {p.pronto ? 'Sinalizar' : 'Aguarde'}
            </button>
          </form>
        </section>
      </main>
    </div>
  )
}

/** Placeholder que digita cada sugestão, segura 2 s completa, apaga e passa para a próxima. */
function useDigitando(frases: string[], ligado: boolean) {
  const parado = matchMedia('(prefers-reduced-motion: reduce)').matches
  const [txt, setTxt] = useState('')
  useEffect(() => {
    if (!ligado || parado) return
    let i = 0, n = 0, apagando = false, t = 0
    const passo = () => {
      const f = frases[i]
      if (!apagando && n < f.length) { setTxt(f.slice(0, ++n)); t = window.setTimeout(passo, 55) }
      else if (!apagando) { apagando = true; t = window.setTimeout(passo, 2000) }
      else if (n > 0) { setTxt(f.slice(0, --n)); t = window.setTimeout(passo, 25) }
      else { apagando = false; i = (i + 1) % frases.length; t = window.setTimeout(passo, 400) }
    }
    t = window.setTimeout(passo, 600)
    return () => clearTimeout(t)
  }, [frases, ligado, parado])
  return parado ? 'Escreva uma frase' : txt
}

function Glosa({ itens, atual, onSinal }: { itens: Item[]; atual: number; onSinal: (k: number) => void }) {
  return (
    <ol className="glosa" aria-label="Glosa: clique em um sinal para ver só ele">
      {itens.map((it, k) => {
        const dica = [
          it.palavra && it.palavra !== it.tok ? `“${it.palavra}”` : '',
          it.confianca != null ? `confiança ${it.confianca.toFixed(2)}` : '',
          it.alternativas ? 'alternativas: ' + it.alternativas.map(([g, c]) => `${g} ${c.toFixed(2)}`).join(', ') : '',
          it.nota ?? '',
        ].filter(Boolean).join(' · ')
        return (
          <li key={k}>
            <button type="button" title={dica || undefined} onClick={() => onSinal(k)} aria-label={`Ver só o sinal ${it.tok}`}
              className={'tok' + (it.ok ? '' : ' soletra') + (it.incerto ? ' incerto' : '') + (k === atual ? ' agora' : '')}>
              {it.tok}
            </button>
          </li>
        )
      })}
    </ol>
  )
}

function Duvida({ it, onCorrigir, onSoletrar, onReescrever }:
  { it: Item; onCorrigir: (c: string) => void; onSoletrar: () => void; onReescrever: () => void }) {
  return (
    <div className="duvida" role="group" aria-label={`Possível erro de digitação em ${it.palavra}`}>
      <p><b>“{it.palavra}”</b> não existe em português. Você quis dizer:</p>
      <div className="duvida-opcoes">
        {it.sugestoes!.map(s => <button key={s} type="button" className="opcao" onClick={() => onCorrigir(s)}>{s}</button>)}
      </div>
      <div className="duvida-saidas">
        <button type="button" className="link" onClick={onSoletrar}>Soletrar “{it.palavra}”</button>
        <button type="button" className="link" onClick={onReescrever}>Reescrever a frase</button>
      </div>
    </div>
  )
}

function Pe({ t, ativo, onVer }: { t: Turno; ativo: boolean; onVer: () => void }) {
  const r = t.r!
  const meta = [
    r.motor === 'vlibras' ? 'tradutor do governo (reserva)' : '',
    r.emocao && r.emocao.emocao !== 'default' ? `expressão ${r.emocao.emocao}` : '',
  ].filter(Boolean).join(' · ')
  if (!meta && ativo) return null
  return (
    <div className="turno-pe">
      <span className="meta">{meta}</span>
      {!ativo && <button type="button" className="link" onClick={onVer}>Ver de novo</button>}
    </div>
  )
}

const SEM_SINAL = 'não vira sinal em Libras'

function Notas({ r }: { r: Resultado }) {
  // artigos e preposições viram uma linha só; as notas de verdade ficam cada uma na sua
  const desc = r.descartadas ?? []
  const vazias = desc.filter(d => d.nota.endsWith(SEM_SINAL)).map(d => d.palavra)
  const notas = [...(r.notas ?? []), ...r.itens.map(i => i.nota), ...desc.filter(d => !d.nota.endsWith(SEM_SINAL)).map(d => d.nota)]
    .filter((n): n is string => !!n)
  if (vazias.length) notas.unshift(`Sem sinal em Libras: ${[...new Set(vazias)].join(', ')}`)
  if (!notas.length) return null
  return <ul className="notas">{[...new Set(notas)].map(n => <li key={n}>{n}</li>)}</ul>
}

function Orbita({ rotulo = 'Montando a glosa' }) {
  return <span className="orbita" role="status" aria-label={rotulo}><span /><span /><span /></span>
}

function Svg({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>
  )
}
