import { useEffect, useState } from 'react'
import { fetchAllNotes } from '../api/client'

export default function NotesVault({ open, onClose, nodesById, onSelect }) {
  const [rows, setRows] = useState(null)

  useEffect(() => {
    if (!open) return
    setRows(null)
    fetchAllNotes()
      .then(setRows)
      .catch(() => setRows([]))
  }, [open])

  return (
    <div className={`modal-backdrop${open ? ' open' : ''}`} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-head">
          <h2>🔖 Bóveda de notas</h2>
          <button className="panel-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="modal-body">
          {rows === null && <div className="modal-empty">Cargando...</div>}
          {rows !== null && rows.length === 0 && (
            <div className="modal-empty">
              Todavía no has anotado ningún nodo.
              <br />
              Selecciona un radical o un carácter y escribe algo en "Notas personales".
            </div>
          )}
          {rows !== null &&
            rows.map((row) => {
              const n = nodesById.get(row.id)
              if (!n) return null
              return (
                <button
                  key={row.id}
                  className="conn-item"
                  style={{ width: '100%' }}
                  onClick={() => {
                    onClose()
                    onSelect(n.id)
                  }}
                >
                  <span className="g">{n.glyph}</span>
                  <span className="info">
                    <div className="m">{row.text.slice(0, 60)}</div>
                    <div className="r">{n.meaning || ''}</div>
                  </span>
                </button>
              )
            })}
        </div>
      </div>
    </div>
  )
}
