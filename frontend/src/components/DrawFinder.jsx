import { useRef, useState } from 'react'
import { useStrokesData } from '../hooks/useStrokesData'
import { findCandidates } from '../utils/strokeMatch'
import DrawCanvas from './DrawCanvas'
import { CloseIcon, PencilIcon } from './icons'

/** El sentido inverso del trazado a mano: el usuario dibuja un carácter
 * que no recuerda cómo se busca y la app propone los candidatos del
 * catálogo cuyos trazos reales (KanjiVG) se parecen más, comparando
 * contra el mismo índice que usa el quiz de trazado en StudyMode. */
export default function DrawFinder({ open, onClose, nodesById, onSelect }) {
  const canvasRef = useRef(null)
  const strokesData = useStrokesData()
  const [results, setResults] = useState(null) // null antes de buscar

  if (!open) return null

  function search() {
    if (!canvasRef.current || !strokesData) return
    const strokes = canvasRef.current.getStrokes()
    if (strokes.length === 0) return
    setResults(findCandidates(strokes, strokesData, 8))
  }

  function clear() {
    canvasRef.current?.clear()
    setResults(null)
  }

  function pick(glyph) {
    // el id del nodo no esta en el indice de trazos (solo el glifo);
    // buscarlo entre los nodos ya cargados por glifo
    for (const n of nodesById.values()) {
      if (n.glyph === glyph) {
        onSelect(n.id)
        onClose()
        return
      }
    }
  }

  return (
    <div className="modal-backdrop open" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal draw-finder-modal">
        <div className="modal-head">
          <h2>
            <PencilIcon size={17} /> Encontrador por dibujo
          </h2>
          <button className="panel-close" aria-label="Cerrar" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>
        <div className="study-body">
          <div className="draw-missing" style={{ marginBottom: 4 }}>
            Dibuja el carácter que no recuerdas cómo se busca.
          </div>
          <DrawCanvas ref={canvasRef} />
          <div className="draw-tools">
            <button className="draw-tool-btn" onClick={() => canvasRef.current?.undo()}>
              Deshacer
            </button>
            <button className="draw-tool-btn" onClick={clear}>
              Borrar
            </button>
          </div>
          <button className="study-reveal" onClick={search} disabled={!strokesData}>
            {strokesData ? 'Buscar' : 'Cargando datos de trazo...'}
          </button>

          {results !== null && (
            <div className="conn-list" style={{ width: '100%', marginTop: 4 }}>
              {results.length === 0 && <div className="draw-missing">Sin candidatos parecidos.</div>}
              {results.map((r) => {
                const n = Array.from(nodesById.values()).find((x) => x.glyph === r.glyph)
                return (
                  <button className="conn-item" key={r.glyph} onClick={() => pick(r.glyph)}>
                    <span className="g">{r.glyph}</span>
                    <span className="info">
                      <div className="m">{n?.meaning || r.glyph}</div>
                      <div className="r">{[n?.onyomi, n?.kunyomi, n?.pinyin].filter(Boolean).join(' · ')}</div>
                    </span>
                    <span className="role-tag">{r.score}%</span>
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
