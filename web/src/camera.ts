// Câmera + MediaPipe Holistic, tudo no navegador: o vídeo nunca sai do computador (KNOWLEDGE/15, D2).
import { useCallback, useEffect, useRef, useState } from 'react'
import { DrawingUtils, FilesetResolver, HolisticLandmarker, type HolisticLandmarkerResult } from '@mediapipe/tasks-vision'

// mesma versão do pacote npm (package.json) e do mediapipe Python que vai extrair as referências (E2)
const WASM = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.2.0/wasm'
const MODELO = 'https://storage.googleapis.com/mediapipe-models/holistic_landmarker/holistic_landmarker/float16/1/holistic_landmarker.task'

export type Estado = 'parada' | 'pedindo' | 'carregando' | 'rodando' | 'erro'
export type Medida = { fps: number; ms: number; delegate: 'GPU' | 'CPU'; rosto: boolean; ombros: boolean; maos: number }

// um só modelo por página: sair e voltar para a aba não baixa nem compila de novo
let criado: Promise<{ lm: HolisticLandmarker; delegate: 'GPU' | 'CPU' }> | null = null
function criar() {
  criado ??= (async () => {
    const fs = await FilesetResolver.forVisionTasks(WASM)
    // ?delegate=CPU força a CPU, para medir os dois caminhos na mesma máquina (KNOWLEDGE/15, E1)
    const ordem = new URLSearchParams(location.search).get('delegate') === 'CPU' ? ['CPU'] as const : ['GPU', 'CPU'] as const
    for (const delegate of ordem) {
      try {
        // limiares baixos: com desfoque de movimento a mão some menos (87% → 92% dos quadros, KNOWLEDGE/15 §16.2)
        const lm = await HolisticLandmarker.createFromOptions(fs, {
          baseOptions: { modelAssetPath: MODELO, delegate }, runningMode: 'VIDEO',
          minHandLandmarksConfidence: 0.2, minPoseDetectionConfidence: 0.3, minPosePresenceConfidence: 0.3,
          minFaceDetectionConfidence: 0.3, minFacePresenceConfidence: 0.3,
        })
        return { lm, delegate }
      } catch (e) { if (delegate === 'CPU') throw e }
    }
    throw new Error('inalcançável')
  })()
  criado.catch(() => { criado = null }) // deixa tentar de novo
  return criado
}

export function useCamera() {
  const video = useRef<HTMLVideoElement>(null)
  const tela = useRef<HTMLCanvasElement>(null)
  const [estado, setEstado] = useState<Estado>('parada')
  const [erro, setErro] = useState('')
  const [medida, setMedida] = useState<Medida | null>(null)
  const [pontos, setPontos] = useState(true)
  const desenhar = useRef(pontos)
  desenhar.current = pontos
  const fluxo = useRef<MediaStream | null>(null)
  const raf = useRef(0)

  const desligar = useCallback(() => {
    cancelAnimationFrame(raf.current)
    fluxo.current?.getTracks().forEach(t => t.stop())
    fluxo.current = null
    setEstado('parada'); setMedida(null)
  }, [])
  useEffect(() => desligar, [desligar])

  const ligar = useCallback(async () => {
    setErro('')
    try {
      setEstado('pedindo')
      fluxo.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false,
      })
      setEstado('carregando')
      const [{ lm, delegate }] = await Promise.all([criar(), (async () => {
        const v = video.current!
        v.srcObject = fluxo.current
        await v.play()
      })()])
      if (!fluxo.current) return // desligou enquanto carregava
      setEstado('rodando')
      laco(lm, delegate)
    } catch (e) {
      fluxo.current?.getTracks().forEach(t => t.stop())
      fluxo.current = null
      setErro(mensagem(e)); setEstado('erro')
    }
  }, [])

  function laco(lm: HolisticLandmarker, delegate: 'GPU' | 'CPU') {
    const v = video.current!, c = tela.current!
    const ctx = c.getContext('2d')!
    const du = new DrawingUtils(ctx)
    let ultimo = -1, janela = performance.now(), quadros = 0, gasto = 0
    let r: HolisticLandmarkerResult | null = null
    const passo = () => {
      raf.current = requestAnimationFrame(passo)
      if (v.currentTime === ultimo || v.readyState < 2) return // só processa quadro novo da câmera
      ultimo = v.currentTime
      const t0 = performance.now()
      r = lm.detectForVideo(v, t0)
      gasto += performance.now() - t0
      quadros++
      if (c.width !== v.videoWidth) { c.width = v.videoWidth; c.height = v.videoHeight }
      ctx.clearRect(0, 0, c.width, c.height)
      if (desenhar.current) pintar(du, r)
      if (t0 - janela >= 1000) {
        setMedida({
          fps: quadros * 1000 / (t0 - janela), ms: gasto / quadros, delegate,
          rosto: r.faceLandmarks.length > 0,
          ombros: !!r.poseLandmarks[0] && [11, 12].every(i => (r!.poseLandmarks[0][i].visibility ?? 1) > 0.5),
          maos: r.leftHandLandmarks.length + r.rightHandLandmarks.length,
        })
        janela = t0; quadros = 0; gasto = 0
      }
    }
    passo()
  }

  return { video, tela, estado, erro, medida, pontos, setPontos, ligar, desligar }
}

function pintar(du: DrawingUtils, r: HolisticLandmarkerResult) {
  const pose = r.poseLandmarks[0]
  if (pose) du.drawConnectors(pose, HolisticLandmarker.POSE_CONNECTIONS.filter(c => c.start <= 24 && c.end <= 24),
    { color: 'rgba(255,255,255,.55)', lineWidth: 2 }) // só tronco e braços: as pernas não entram na Libras
  for (const mao of [...r.leftHandLandmarks, ...r.rightHandLandmarks]) {
    du.drawConnectors(mao, HolisticLandmarker.HAND_CONNECTIONS, { color: '#e2654b', lineWidth: 3 })
    du.drawLandmarks(mao, { color: '#fff', lineWidth: 1, radius: 3 })
  }
}

function mensagem(e: unknown) {
  if (!navigator.mediaDevices) return 'O navegador só libera a câmera em páginas https ou em localhost (HOST=0.0.0.0 em http não serve).'
  const nome = e instanceof DOMException ? e.name : ''
  if (nome === 'NotAllowedError') return 'A permissão da câmera foi negada. Libere a câmera no cadeado da barra de endereço e tente de novo.'
  if (nome === 'NotFoundError') return 'Nenhuma câmera foi encontrada neste computador.'
  if (nome === 'NotReadableError') return 'A câmera está em uso por outro programa. Feche-o e tente de novo.'
  return 'Não consegui ligar a câmera ou carregar o modelo: ' + (e instanceof Error ? e.message : String(e))
}
