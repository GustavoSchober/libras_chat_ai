// Ponte com o player Unity do VLibras (contrato completo em KNOWLEDGE/03-player-3d.md).
import { useCallback, useEffect, useRef, useState } from 'react'
import type { Emocao } from './glosa'

export const PLAYER_URL = 'https://vlibras.gov.br/app/unity/index.html'
const BASE_BUNDLES = 'https://dicionario2.vlibras.gov.br/static/BUNDLES/2018.3.1/WEBGL/BR/'

export function usePlayer() {
  const ref = useRef<HTMLIFrameElement>(null)
  const [pronto, setPronto] = useState(false)
  const [visivel, setVisivel] = useState(false)
  const [atual, setAtual] = useState(-1) // índice do sinal em execução; -1 = parado
  const [pausado, setPausado] = useState(false)
  const [velocidade, setVel] = useState(() => {
    try { return Number(localStorage.getItem('velocidade')) || 1.5 } catch { return 1.5 }
  })
  const glosa = useRef('')
  const indice = useRef(0)
  const timer = useRef(0)

  const send = useCallback((object: string, method: string, params: string | number) =>
    ref.current?.contentWindow?.postMessage({ type: 'unity', object, method, params }, '*'), [])

  // ⚠ setSlider precisa de NÚMERO: com string o Unity ignora em silêncio.
  const setVelocidade = useCallback((v: number) => {
    setVel(v)
    send('PlayerManager', 'setSlider', v)
    try { localStorage.setItem('velocidade', String(v)) } catch { /* sem storage */ }
  }, [send])

  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      const d = e.data
      if (!d || d.type !== 'unity_event' || e.source !== ref.current?.contentWindow) return
      if (d.event === 'on_load_player') {
        // OBRIGATÓRIO: sem isto o player não sabe de onde baixar os sinais.
        send('PlayerManager', 'setBaseUrl', BASE_BUNDLES)
        send('PlayerManager', 'setSlider', velocidade)
        setPronto(true)
        // shortcut: o canvas do Unity fica branco ~1 s depois do on_load_player (medido); sem evento melhor, espera fixa
        setTimeout(() => setVisivel(true), 1200)
      }
      // [n, total] chega quando o sinal n TERMINA; o que está em execução é o índice n.
      if (d.event === 'counter_gloss') {
        const [n, total] = d.data
        if (total) { indice.current = n; setAtual(n < total ? n : -1) }
      }
      if (d.event === 'on_playing_state_change') {
        const [tocando, emPausa] = d.data ?? []
        setPausado(emPausa === 'True')
        // logo depois do playNow vem isPlaying=False antes do True: não limpe o destaque ali.
        if (tocando === 'True') setAtual(indice.current)
      }
    }
    addEventListener('message', onMsg)
    return () => removeEventListener('message', onMsg)
  }, [send, velocidade])

  const tocar = useCallback((tokens: string[], emocao?: Emocao | null) => {
    glosa.current = tokens.join(' ')
    // um playNow durante uma reprodução em curso é ignorado: pare antes.
    send('PlayerManager', 'stopAll', '')
    send('EmotionBridge', emocao ? emocao.metodo : 'ApplyDefaultEmotion', emocao ? Number(emocao.intensidade) : 2)
    indice.current = 0
    setPausado(false)
    clearTimeout(timer.current)
    timer.current = window.setTimeout(() => send('PlayerManager', 'playNow', glosa.current), 150)
  }, [send])

  const pausar = useCallback(() => send('PlayerManager', 'setPauseState', pausado ? '0' : '1'), [send, pausado])
  const parar = useCallback(() => { send('PlayerManager', 'stopAll', ''); setAtual(-1) }, [send])

  return { ref, pronto, visivel, atual, pausado, velocidade, setVelocidade, tocar, pausar, parar }
}
