import { useCamera } from './camera'

/** Aba Praticar, etapa E1: câmera espelhada + pontos do MediaPipe + medição de FPS. Ainda não avalia nada. */
export default function Praticar() {
  const c = useCamera()
  const m = c.medida
  const rodando = c.estado === 'rodando'

  return (
    <section className="camera" aria-label="Câmera">
      <div className={'espelho' + (rodando ? ' ligado' : '')}>
        {/* vídeo e pontos ficam sempre montados: o hook precisa deles antes de a câmera abrir */}
        <video ref={c.video} muted playsInline aria-hidden="true" />
        <canvas ref={c.tela} aria-hidden="true" />

        {!rodando && (
          <div className="camera-capa">
            {c.estado === 'pedindo' || c.estado === 'carregando' ? (
              <div className="camera-esperando" role="status">
                <span className="orbita grande"><span /><span /><span /></span>
                <p>{c.estado === 'pedindo' ? 'Aguardando a permissão da câmera' : 'Carregando o modelo de visão (cerca de 28 MB na primeira vez)'}</p>
              </div>
            ) : (
              <div className="camera-intro">
                <h1>Faça os sinais para a câmera.</h1>
                <p><b>O vídeo não sai do seu computador.</b> Os pontos das mãos, do rosto e dos ombros são calculados
                  aqui mesmo, no navegador. Nada é gravado nem enviado.</p>
                <p>Por enquanto a câmera só mostra o que enxerga: <b>ainda não reconhece nem corrige os sinais</b>.
                  Isso vem nas próximas etapas.</p>
                {c.erro && <p className="camera-erro" role="alert">{c.erro}</p>}
                <button type="button" className="enviar" onClick={c.ligar}>Ligar a câmera</button>
              </div>
            )}
          </div>
        )}

        {rodando && (
          <div className="camera-barra">
            <span className="camera-etapa">Só visualização: ainda não reconhece sinais</span>
            <span className="camera-medida" aria-live="off">
              {m ? `${Math.round(m.fps)} quadros/s · ${m.ms.toFixed(0)} ms · ${m.delegate}` : 'medindo…'}
            </span>
            {m && (
              <span className="camera-enquadra" aria-label="O que a câmera está vendo">
                <i className={m.rosto ? 'ok' : ''}>rosto</i>
                <i className={m.ombros ? 'ok' : ''}>ombros</i>
                <i className={m.maos ? 'ok' : ''}>{m.maos === 2 ? '2 mãos' : m.maos === 1 ? '1 mão' : 'mãos'}</i>
              </span>
            )}
            <span className="camera-acoes">
              <button type="button" className="link" aria-pressed={c.pontos} onClick={() => c.setPontos(!c.pontos)}>
                {c.pontos ? 'Esconder pontos' : 'Mostrar pontos'}
              </button>
              <button type="button" className="link" onClick={c.desligar}>Desligar</button>
            </span>
          </div>
        )}
      </div>
      <p className="camera-aviso">
        Libras não é português sinalizado. A ordem dos sinais e a gramática podem ser diferentes da frase em português.
      </p>
    </section>
  )
}
