import { useEffect, useRef, useState } from 'react'
import { KIND_LABEL } from '../graph/constants'

function norm(s) {
  return (s || '').toString().toLowerCase()
}

export default function TopBar({ nodesById, filters, setFilters, onSelectSearch, onOpenVault }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)

  useEffect(() => {
    function onDocClick(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('click', onDocClick)
    return () => document.removeEventListener('click', onDocClick)
  }, [])

  const q = norm(query)
  const hits = []
  if (q) {
    for (const n of nodesById.values()) {
      if (hits.length >= 18) break
      const hay = [n.glyph, n.onyomi, n.kunyomi, n.pinyin, n.meaning].map(norm).join(' ')
      if (hay.includes(q)) hits.push(n)
    }
  }

  function pick(n) {
    setOpen(false)
    setQuery('')
    onSelectSearch(n)
  }

  return (
    <div className="topbar">
      <div className="brand">
        <span className="mark">部</span>
        <span className="word">Atlas de Radicales</span>
      </div>

      <div className="search-wrap" ref={wrapRef}>
        <input
          type="text"
          placeholder="Buscar 木, kun, pinyin, significado..."
          autoComplete="off"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(!!query)}
        />
        {open && q && (
          <div className="search-results">
            {hits.length === 0 && (
              <div style={{ padding: 10, fontSize: 12, color: 'var(--muted)' }}>Sin resultados</div>
            )}
            {hits.map((n) => (
              <button key={n.id} onClick={() => pick(n)}>
                <span className="g">{n.glyph}</span>
                <span>
                  <div>{n.meaning || KIND_LABEL[n.kind]}</div>
                  <div className="meta">{[n.onyomi, n.kunyomi, n.pinyin].filter(Boolean).join(' · ') || KIND_LABEL[n.kind]}</div>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="seg">
        {[
          ['all', 'Ambos'],
          ['ja', '日本語'],
          ['zh', '中文'],
        ].map(([key, label]) => (
          <button
            key={key}
            className={filters.lang === key ? 'active' : ''}
            onClick={() => setFilters((f) => ({ ...f, lang: key }))}
          >
            {label}
          </button>
        ))}
      </div>

      <button
        className={`toggle-pill${filters.levelFilter === 'all' ? ' on' : ''}`}
        title="Por defecto solo se ven JLPT N5-N3 y HSK 1-6. Actívalo para ver también N2/N1 y HSK 7-9."
        onClick={() =>
          setFilters((f) => ({ ...f, levelFilter: f.levelFilter === 'all' ? 'core' : 'all' }))
        }
      >
        <span className="sw" /> Ver catálogo completo (N2/N1, HSK 7-9)
      </button>

      <button
        className={`toggle-pill${filters.showAllRadicals ? ' on' : ''}`}
        onClick={() => setFilters((f) => ({ ...f, showAllRadicals: !f.showAllRadicals }))}
      >
        <span className="sw" /> Ver los 243 radicales
      </button>

      <button className="vault-btn" onClick={onOpenVault}>
        🔖 <span className="label">Mis notas</span>
      </button>
    </div>
  )
}
