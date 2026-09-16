import { useEffect, useRef, useState } from 'react'
import './App.css'
import { useGraphData } from './hooks/useGraphData'
import { CATEGORY_ORDER } from './graph/constants'
import TopBar from './components/TopBar'
import Legend from './components/Legend'
import RadicalGraph from './components/RadicalGraph'
import DetailPanel from './components/DetailPanel'
import NotesVault from './components/NotesVault'

export default function App() {
  const { graph, error } = useGraphData()
  const [filters, setFilters] = useState({
    lang: 'all',
    showAllRadicals: false,
    levelFilter: 'core',
    activeCategories: new Set(CATEGORY_ORDER),
  })
  const [selectedId, setSelectedId] = useState(null)
  const [vaultOpen, setVaultOpen] = useState(false)
  const graphRef = useRef(null)

  function selectAndCenter(id, opts = {}) {
    setSelectedId(id)
    if (opts.center) {
      requestAnimationFrame(() => requestAnimationFrame(() => graphRef.current?.centerOn(id)))
    }
  }

  function handleSelectSearch(n) {
    if (n.kind === 'radical' && n.degree === 0 && !filters.showAllRadicals) {
      setFilters((f) => ({ ...f, showAllRadicals: true }))
    }
    selectAndCenter(n.id, { center: true })
  }

  // Atajos de teclado. "typing" evita que / o N secuestren lo que el
  // usuario esta escribiendo en el buscador o en las notas; Esc si
  // funciona siempre (primero cierra la boveda si esta abierta, luego
  // quita el foco de lo que se este escribiendo, luego deselecciona).
  useEffect(() => {
    function onKeyDown(e) {
      const active = document.activeElement
      const typing = active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA')

      if (e.key === 'Escape') {
        if (vaultOpen) { setVaultOpen(false); return }
        if (typing) active.blur()
        setSelectedId(null)
        return
      }
      if (typing || vaultOpen) return
      if (e.key === '/') {
        e.preventDefault()
        document.querySelector('.search-wrap input')?.focus()
        return
      }
      if ((e.key === 'n' || e.key === 'N') && selectedId) {
        document.querySelector('.notes-box textarea')?.focus()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [selectedId, vaultOpen])

  if (error) {
    return (
      <div className="app" style={{ alignItems: 'center', justifyContent: 'center', display: 'flex' }}>
        <p style={{ color: 'var(--ink)' }}>
          No se pudo conectar con la API ({String(error.message)}). ¿Corriste{' '}
          <code>uvicorn app.main:app --reload --port 8055</code> dentro de <code>backend/</code>?
        </p>
      </div>
    )
  }
  if (!graph) {
    return (
      <div className="app" style={{ alignItems: 'center', justifyContent: 'center', display: 'flex' }}>
        <p style={{ color: 'var(--ink)' }}>Cargando el atlas...</p>
      </div>
    )
  }

  const selectedNode = selectedId ? graph.nodesById.get(selectedId) : null

  return (
    <div className="app">
      <TopBar
        nodesById={graph.nodesById}
        filters={filters}
        setFilters={setFilters}
        onSelectSearch={handleSelectSearch}
        onOpenVault={() => setVaultOpen(true)}
      />
      <Legend filters={filters} setFilters={setFilters} />
      <div style={{ position: 'relative', flex: 1, minHeight: 0 }}>
        <RadicalGraph
          ref={graphRef}
          nodesById={graph.nodesById}
          edges={graph.edges}
          adjacency={graph.adjacency}
          filters={filters}
          selectedId={selectedId}
          onSelect={(id) => selectAndCenter(id)}
        />
        <DetailPanel
          node={selectedNode}
          nodesById={graph.nodesById}
          adjacency={graph.adjacency}
          onClose={() => setSelectedId(null)}
          onSelect={(id) => selectAndCenter(id)}
        />
      </div>
      <NotesVault
        open={vaultOpen}
        onClose={() => setVaultOpen(false)}
        nodesById={graph.nodesById}
        onSelect={(id) => selectAndCenter(id, { center: true })}
      />
    </div>
  )
}
