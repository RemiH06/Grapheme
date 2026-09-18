import { useEffect, useMemo, useState } from 'react'
import { clearRadicalComponents, fetchAdminRadicals, saveRadicalComponents } from '../api/client'

/** Herramienta local de curacion, sin relacion con la app de estudio:
 * revisar los 242 radicales y decidir a mano de que radicales reales
 * esta compuesto cada uno, para los casos donde la fuente etimologica
 * los marca "pictograficos" (=atomicos) pero en realidad si tienen
 * piezas reconocibles (ver docs/METODOLOGIA.md seccion 11). Montada
 * aparte del resto de la app en /?curate=radicals, nunca en la UI
 * normal. Guarda en data/radical_components_manual.json via el backend;
 * build_dataset.py la lee en la siguiente corrida. */

function statusOf(r) {
  if (r.manual != null) return r.manual.length === 0 ? 'confirmed-atomic' : 'manual'
  return r.components.length === 0 ? 'needs-review' : 'auto-ok'
}

const STATUS_LABEL = {
  'needs-review': 'Sin componentes, sin revisar',
  'auto-ok': 'Automático (con componentes)',
  manual: 'Curado a mano',
  'confirmed-atomic': 'Confirmado atómico',
}

const STATUS_ORDER = { 'needs-review': 0, 'auto-ok': 1, manual: 2, 'confirmed-atomic': 3 }

export default function RadicalCurator() {
  const [radicals, setRadicals] = useState(null)
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('needs-review')
  const [editingGlyph, setEditingGlyph] = useState(null)
  const [editSelection, setEditSelection] = useState([])
  const [pickerQuery, setPickerQuery] = useState('')
  const [saving, setSaving] = useState(false)

  function load() {
    fetchAdminRadicals()
      .then((data) => setRadicals(data))
      .catch((e) => setError(e))
  }
  useEffect(load, [])

  const withStatus = useMemo(() => {
    if (!radicals) return []
    return radicals.map((r) => ({ ...r, status: statusOf(r) }))
  }, [radicals])

  const counts = useMemo(() => {
    const c = { 'needs-review': 0, 'auto-ok': 0, manual: 0, 'confirmed-atomic': 0 }
    for (const r of withStatus) c[r.status]++
    return c
  }, [withStatus])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return withStatus
      .filter((r) => statusFilter === 'all' || r.status === statusFilter)
      .filter((r) => !q || r.glyph.includes(q) || (r.meaning || '').toLowerCase().includes(q))
      .sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status] || a.strokeCount - b.strokeCount)
  }, [withStatus, statusFilter, query])

  function openEditor(r) {
    setEditingGlyph(r.glyph)
    setEditSelection(r.manual != null ? r.manual : r.components.map((c) => c.glyph))
    setPickerQuery('')
  }

  function toggleComponent(glyph) {
    setEditSelection((sel) => (sel.includes(glyph) ? sel.filter((g) => g !== glyph) : [...sel, glyph]))
  }

  async function save() {
    setSaving(true)
    try {
      await saveRadicalComponents(editingGlyph, editSelection)
      setEditingGlyph(null)
      load()
    } finally {
      setSaving(false)
    }
  }

  async function revertToAuto() {
    setSaving(true)
    try {
      await clearRadicalComponents(editingGlyph)
      setEditingGlyph(null)
      load()
    } finally {
      setSaving(false)
    }
  }

  if (error) {
    return <div style={{ padding: 24, fontFamily: 'sans-serif' }}>No se pudo cargar /admin/radicals: {String(error.message)}</div>
  }
  if (!radicals) {
    return <div style={{ padding: 24, fontFamily: 'sans-serif' }}>Cargando radicales...</div>
  }

  const editing = editingGlyph ? withStatus.find((r) => r.glyph === editingGlyph) : null
  const pickerQ = pickerQuery.trim().toLowerCase()
  const pickerCandidates = withStatus
    .filter((r) => r.glyph !== editingGlyph)
    .filter((r) => !pickerQ || r.glyph.includes(pickerQ) || (r.meaning || '').toLowerCase().includes(pickerQ))

  return (
    <div className="curator">
      <header className="curator-head">
        <h1>Curar componentes de radicales</h1>
        <p>
          242 radicales. {counts['needs-review']} sin componentes y sin revisar (esperado: solo 2-3, los de un
          trazo). {counts['auto-ok']} con componentes automáticos. {counts.manual} curados a mano.{' '}
          {counts['confirmed-atomic']} confirmados como atómicos.
        </p>
        <div className="curator-controls">
          <input
            className="curator-search"
            placeholder="Buscar radical o significado..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="needs-review">Sin revisar ({counts['needs-review']})</option>
            <option value="auto-ok">Automático ({counts['auto-ok']})</option>
            <option value="manual">Curado a mano ({counts.manual})</option>
            <option value="confirmed-atomic">Confirmado atómico ({counts['confirmed-atomic']})</option>
            <option value="all">Todos (242)</option>
          </select>
        </div>
      </header>

      <div className="curator-list">
        {filtered.map((r) => (
          <div key={r.id} className={`curator-row status-${r.status}`}>
            <div className="curator-glyph">{r.glyph}</div>
            <div className="curator-info">
              <div className="curator-meaning">{r.meaning || '(sin significado)'}</div>
              <div className="curator-meta">
                {r.strokeCount ? `${r.strokeCount} trazo${r.strokeCount === 1 ? '' : 's'}` : 'trazos: ?'} ·{' '}
                {STATUS_LABEL[r.status]}
              </div>
              <div className="curator-comps">
                {(r.manual != null ? r.manual : r.components.map((c) => c.glyph)).map((g) => (
                  <span className="curator-chip" key={g}>
                    {g}
                  </span>
                ))}
                {(r.manual != null ? r.manual.length : r.components.length) === 0 && (
                  <span className="curator-empty">sin componentes</span>
                )}
              </div>
            </div>
            <button className="curator-edit-btn" onClick={() => openEditor(r)}>
              Editar
            </button>
          </div>
        ))}
        {filtered.length === 0 && <div className="curator-empty-state">Nada que mostrar con este filtro.</div>}
      </div>

      {editing && (
        <div className="curator-modal-backdrop" onClick={(e) => e.target === e.currentTarget && setEditingGlyph(null)}>
          <div className="curator-modal">
            <div className="curator-modal-head">
              <div className="curator-glyph big">{editing.glyph}</div>
              <div>
                <div className="curator-meaning">{editing.meaning}</div>
                <div className="curator-meta">
                  {editing.strokeCount} trazos · componente de {editing.status}
                </div>
              </div>
              <button className="curator-close" onClick={() => setEditingGlyph(null)}>
                ×
              </button>
            </div>

            <div className="curator-selection">
              <div className="curator-selection-label">Se compone de ({editSelection.length}):</div>
              <div className="curator-comps">
                {editSelection.length === 0 && <span className="curator-empty">ninguno (átomo confirmado)</span>}
                {editSelection.map((g) => (
                  <button className="curator-chip removable" key={g} onClick={() => toggleComponent(g)}>
                    {g} ×
                  </button>
                ))}
              </div>
            </div>

            <input
              className="curator-search"
              autoFocus
              placeholder="Buscar radical por glifo o significado para agregar..."
              value={pickerQuery}
              onChange={(e) => setPickerQuery(e.target.value)}
            />
            <div className="curator-picker-grid">
              {pickerCandidates.map((r) => (
                <button
                  key={r.id}
                  className={`curator-picker-item${editSelection.includes(r.glyph) ? ' selected' : ''}`}
                  onClick={() => toggleComponent(r.glyph)}
                  title={r.meaning}
                >
                  <span className="g">{r.glyph}</span>
                  <span className="m">{r.meaning}</span>
                </button>
              ))}
            </div>

            <div className="curator-modal-actions">
              <button onClick={() => setEditingGlyph(null)} disabled={saving}>
                Cancelar
              </button>
              {editing.manual != null && (
                <button onClick={revertToAuto} disabled={saving}>
                  Volver a automático
                </button>
              )}
              <button className="primary" onClick={save} disabled={saving}>
                {saving ? 'Guardando...' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
