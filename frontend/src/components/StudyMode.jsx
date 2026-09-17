import { useEffect, useState } from 'react'
import { fetchDueCards, reviewCard } from '../api/client'
import { CATEGORY_INFO } from '../graph/constants'
import { checkMeaning } from '../utils/quiz'
import { canSpeak, hasReading, preferredLang, speak } from '../utils/speech'

const GRADES = [
  { grade: 0, label: 'Otra vez' },
  { grade: 1, label: 'Difícil' },
  { grade: 2, label: 'Bien' },
  { grade: 3, label: 'Fácil' },
]

const MODE_KEY = 'grapheme.study.mode'

export default function StudyMode({ open, onClose, nodesById, langFilter }) {
  const [queue, setQueue] = useState(null) // null = cargando
  const [index, setIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [mode, setMode] = useState(() => {
    try {
      return localStorage.getItem(MODE_KEY) === 'type' ? 'type' : 'reveal'
    } catch {
      return 'reveal'
    }
  })
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState(null) // null | true | false

  useEffect(() => {
    if (!open) return
    setQueue(null)
    setIndex(0)
    setRevealed(false)
    setAnswer('')
    setResult(null)
    fetchDueCards()
      .then((due) => {
        const nodes = due.map((d) => nodesById.get(d.id)).filter(Boolean)
        // barajar para no repasar siempre en el mismo orden
        for (let i = nodes.length - 1; i > 0; i--) {
          const j = Math.floor(Math.random() * (i + 1))
          ;[nodes[i], nodes[j]] = [nodes[j], nodes[i]]
        }
        setQueue(nodes)
      })
      .catch(() => setQueue([]))
  }, [open, nodesById])

  if (!open) return null

  const node = queue && queue[index]

  function chooseMode(m) {
    setMode(m)
    try {
      localStorage.setItem(MODE_KEY, m)
    } catch {
      // localStorage puede fallar en privado/bloqueado, no es critico
    }
  }

  function submitAnswer(e) {
    e.preventDefault()
    if (!node) return
    setResult(checkMeaning(answer, node.meaning))
    setRevealed(true)
  }

  async function grade(g) {
    if (!node) return
    try {
      await reviewCard(node.id, g, node.glyph)
    } catch {
      // si falla el guardado seguimos la sesion igual, no vale la pena
      // interrumpir el repaso por un error de red pasajero
    }
    setRevealed(false)
    setAnswer('')
    setResult(null)
    setIndex((i) => i + 1)
  }

  function speakNode() {
    if (!node) return
    speak(node.glyph, preferredLang(node, langFilter))
  }

  return (
    <div className="modal-backdrop open" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal study-modal">
        <div className="modal-head">
          <h2>📚 Repaso de hoy</h2>
          <div className="study-mode-toggle">
            <button className={mode === 'reveal' ? 'active' : ''} onClick={() => chooseMode('reveal')}>
              Mostrar
            </button>
            <button className={mode === 'type' ? 'active' : ''} onClick={() => chooseMode('type')}>
              Escribir
            </button>
          </div>
          <button className="panel-close" onClick={onClose}>
            ✕
          </button>
        </div>

        {queue === null && <div className="modal-empty">Cargando...</div>}

        {queue !== null && queue.length === 0 && (
          <div className="modal-empty">
            No tienes tarjetas pendientes hoy.
            <br />
            Agrega nodos a tu lista de estudio desde el panel de detalle (☆) para empezar.
          </div>
        )}

        {node && (
          <div className="study-body">
            <div className="study-progress">
              {index + 1} / {queue.length}
            </div>
            <div className="study-glyph">{node.glyph}</div>

            {canSpeak() && hasReading(node) && (
              <button className="study-speak" onClick={speakNode} title="Leer en voz alta">
                🔊 Escuchar
              </button>
            )}

            {!revealed && mode === 'reveal' && (
              <button className="study-reveal" onClick={() => setRevealed(true)}>
                Mostrar respuesta
              </button>
            )}

            {!revealed && mode === 'type' && (
              <form className="study-type-form" onSubmit={submitAnswer}>
                <input
                  key={node.id}
                  autoFocus
                  className="study-type-input"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Escribe el significado en inglés..."
                />
                <button type="submit" className="study-reveal">
                  Comprobar
                </button>
              </form>
            )}

            {revealed && (
              <>
                {result !== null && (
                  <div className={`study-type-result ${result ? 'ok' : 'no'}`}>
                    {result ? '✓ Correcto' : `✗ Escribiste: "${answer || '(vacío)'}"`}
                  </div>
                )}
                <div className="badges" style={{ justifyContent: 'center' }}>
                  {node.kind === 'radical' && (
                    <span className="badge cat" style={{ background: `var(${CATEGORY_INFO[node.category].varName})` }}>
                      {CATEGORY_INFO[node.category].label}
                    </span>
                  )}
                  {node.jlpt && <span className="badge">JLPT {node.jlpt}</span>}
                  {node.hsk && <span className="badge">HSK {node.hsk}</span>}
                </div>
                <div className="study-meaning">{node.meaning || '—'}</div>
                <div className="readings" style={{ justifyContent: 'center', alignItems: 'center' }}>
                  {node.onyomi && (
                    <div className="reading-row">
                      <span className="label">On'yomi</span>
                      <span className="val">{node.onyomi}</span>
                    </div>
                  )}
                  {node.kunyomi && (
                    <div className="reading-row">
                      <span className="label">Kun'yomi</span>
                      <span className="val">{node.kunyomi}</span>
                    </div>
                  )}
                  {node.pinyin && (
                    <div className="reading-row">
                      <span className="label">Pinyin</span>
                      <span className="val">{node.pinyin}</span>
                    </div>
                  )}
                  {!hasReading(node) && <div className="empty-conn">No tiene una pronunciación propia registrada.</div>}
                </div>
                <div className="study-grades">
                  {GRADES.map((g) => (
                    <button key={g.grade} className={`study-grade g${g.grade}`} onClick={() => grade(g.grade)}>
                      {g.label}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {queue !== null && queue.length > 0 && !node && (
          <div className="modal-empty">
            Terminaste el repaso de hoy — {queue.length} tarjeta{queue.length === 1 ? '' : 's'}.
          </div>
        )}
      </div>
    </div>
  )
}
