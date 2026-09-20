import { useEffect, useMemo, useState } from 'react'
import {
  clearRadicalComponents,
  fetchAdminAuxiliares,
  fetchAdminKanji,
  fetchAdminRadicals,
  fetchAdminStrokes,
  saveRadicalComponents,
} from '../api/client'

/** Herramienta local de curacion, sin relacion con la app de estudio:
 * revisar los 242 radicales y decidir a mano de que radicales reales
 * esta compuesto cada uno, para los casos donde la fuente etimologica
 * los marca "pictograficos" (=atomicos) pero en realidad si tienen
 * piezas reconocibles (ver docs/METODOLOGIA.md seccion 11). Montada
 * aparte del resto de la app en /?curate=radicals, nunca en la UI
 * normal. Dos pestañas, cada una con su propio significado de "listo":
 *
 * - Radicales: los 242 (menos las fusiones), "se compone de" (multiple).
 * - Auxiliares: los nodos "extra" reales sin pronunciacion, mismo
 *   editor que los radicales.
 *
 * Los trazos del bloque oficial CJK Strokes ya se terminaron de curar
 * (cada uno "deriva de" un radical o de otro trazo, sin pestaña propia
 * ya que no queda nada por revisar ahi); siguen disponibles como
 * opcion seleccionable en "se compone de" via canonicalStrokes.
 *
 * Ambos guardan en data/radical_components_manual.json, que lee
 * build_dataset.py en la siguiente corrida. */

const KIND_TABS = [
  { key: 'radical', label: 'Radicales' },
  { key: 'auxiliar', label: 'Auxiliares' },
]

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
  const [kind, setKind] = useState('radical')
  const [radicals, setRadicals] = useState(null) // la lista que se esta REVISANDO (radical o auxiliar segun kind)
  const [canonicalRadicals, setCanonicalRadicals] = useState(null) // los 240, SIEMPRE cargados, para los pickers
  const [canonicalStrokes, setCanonicalStrokes] = useState(null) // los del bloque oficial CJK Strokes, SIEMPRE cargados
  const [canonicalAuxiliares, setCanonicalAuxiliares] = useState(null) // SIEMPRE cargados (solo se listan en el picker si hay busqueda)
  const [canonicalKanji, setCanonicalKanji] = useState(null) // los 3668, SIEMPRE cargados (idem)
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('needs-review')
  const [editingGlyph, setEditingGlyph] = useState(null)
  const [editSelection, setEditSelection] = useState([])
  const [pickerQuery, setPickerQuery] = useState('')
  const [saving, setSaving] = useState(false)
  const [approvingGlyph, setApprovingGlyph] = useState(null)

  // Radicales, trazos, auxiliares Y kanji/hanzi se usan como opciones de
  // CUALQUIER buscador de componentes: la descomposicion real de un
  // radical o auxiliar a veces SI es un kanji completo o otro auxiliar,
  // no solo otro radical (ej. 巷 usa 共, un kanji real; 七/中 tambien son
  // kanji, no radicales ni auxiliares). Los 4 se cargan una sola vez al
  // montar, independiente de que pestaña este activa.
  useEffect(() => {
    fetchAdminRadicals().then(setCanonicalRadicals).catch(setError)
    fetchAdminStrokes().then(setCanonicalStrokes).catch(setError)
    fetchAdminAuxiliares().then(setCanonicalAuxiliares).catch(setError)
    fetchAdminKanji().then(setCanonicalKanji).catch(setError)
  }, [])

  function loadList() {
    const fetcher = kind === 'auxiliar' ? fetchAdminAuxiliares : fetchAdminRadicals
    return fetcher()
      .then((data) => setRadicals(data))
      .catch((e) => setError(e))
  }
  useEffect(() => {
    setError(null)
    setRadicals(null)
    setStatusFilter('needs-review')
    loadList()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind])

  // Boton rapido para el caso comun de estar revisando el lote
  // "automatico": confirmar que los componentes que ya detecto la
  // fuente etimologica son correctos, sin abrir el editor completo.
  // Guarda esos mismos componentes como curados a mano (no una lista
  // vacia: eso mezclaria "ya revise esto y esta bien" con "esto es
  // atomico de verdad", que son cosas distintas). Solo aplica a items
  // sin curar todavia (r.manual == null); uno ya curado a mano se edita
  // con el editor completo, nunca se pisa con este atajo.
  async function approveAsCurated(r) {
    setApprovingGlyph(r.glyph)
    try {
      await saveRadicalComponents(r.glyph, r.components.map((c) => c.glyph))
      await loadList()
    } finally {
      setApprovingGlyph(null)
    }
  }

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
      .sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status] || (a.strokeCount || 0) - (b.strokeCount || 0))
  }, [withStatus, statusFilter, query])

  function openEditor(r) {
    setEditingGlyph(r.glyph)
    setEditSelection(r.manual != null ? r.manual : r.components.map((c) => c.glyph))
    setPickerQuery('')
  }

  // Se permiten repetidos (ej. 厽 = 厶+厶+厶): agregar SIEMPRE suma una
  // instancia nueva, nunca quita una existente (para eso esta el "x" de
  // cada chip, que quita solo esa instancia por indice, no por glifo).
  function addComponent(glyph) {
    setEditSelection((sel) => [...sel, glyph])
  }

  function removeComponentAt(index) {
    setEditSelection((sel) => sel.filter((_, i) => i !== index))
  }

  async function save() {
    setSaving(true)
    try {
      await saveRadicalComponents(editingGlyph, editSelection)
      setEditingGlyph(null)
      loadList()
    } finally {
      setSaving(false)
    }
  }

  async function revertToAuto() {
    setSaving(true)
    try {
      await clearRadicalComponents(editingGlyph)
      setEditingGlyph(null)
      loadList()
    } finally {
      setSaving(false)
    }
  }

  if (error) {
    return <div style={{ padding: 24, fontFamily: 'sans-serif' }}>No se pudo cargar el admin: {String(error.message)}</div>
  }

  const editing = editingGlyph ? withStatus.find((r) => r.glyph === editingGlyph) : null
  const pickerQRaw = pickerQuery.trim()
  const pickerQ = pickerQRaw.toLowerCase()
  const radicalCandidates = (canonicalRadicals || []).map((r) => ({
    id: r.id,
    glyph: r.glyph,
    label: r.meaning,
    isStroke: false,
  }))
  const strokeCandidates = (canonicalStrokes || []).map((s) => ({
    id: `stroke-${s.glyph}`,
    glyph: s.glyph,
    label: s.derivesFrom ? `trazo, deriva de ${s.derivesFrom}` : 'trazo (bloque CJK Strokes)',
    isStroke: true,
  }))
  // Los auxiliares (mismo orden de magnitud que los 240 radicales) se
  // muestran siempre, igual que radicales/trazos. Kanji si que solo
  // entra a la lista de candidatos si hay busqueda: son 3668, mostrarlos
  // sin filtrar si haria el modal lento sin ganar nada.
  const otherCandidates = (canonicalAuxiliares || []).map((x) => ({
    id: x.id,
    glyph: x.glyph,
    label: 'auxiliar',
    isOther: true,
  }))
  const kanjiCandidates = pickerQ
    ? (canonicalKanji || []).map((k) => ({
        id: k.id,
        glyph: k.glyph,
        label: k.meaning || 'kanji/hanzi',
        isKanji: true,
      }))
    : []
  const pickerCandidates = [...radicalCandidates, ...strokeCandidates, ...otherCandidates, ...kanjiCandidates]
    .filter((r) => r.glyph !== editingGlyph)
    .filter((r) => {
      if (!pickerQ) return true
      const badge = r.isStroke ? 'trazo' : r.isOther ? 'auxiliar' : r.isKanji ? 'kanji' : ''
      return r.glyph.includes(pickerQ) || r.label.toLowerCase().includes(pickerQ) || badge.includes(pickerQ)
    })
  // Si lo que se busco es exactamente UN glifo (por codepoint, no por
  // longitud de string: ojo con los que usan par subrogado) y no esta
  // en ninguna de las 4 listas conocidas, se puede agregar tal cual
  // como componente nuevo (queda como auxiliar nuevo en el siguiente
  // build: resolve_component_id() en build_dataset.py ya sabe crear un
  // nodo "extra" para cualquier glifo no visto antes).
  const canAddCustomGlyph =
    pickerQRaw.length > 0 &&
    Array.from(pickerQRaw).length === 1 &&
    pickerQRaw !== editingGlyph &&
    !pickerCandidates.some((c) => c.glyph === pickerQRaw)

  return (
    <div className="curator">
      <header className="curator-head">
        <h1>Curar componentes de radicales</h1>
        <div className="curator-tabs">
          {KIND_TABS.map((t) => (
            <button
              key={t.key}
              className={`curator-tab${kind === t.key ? ' active' : ''}`}
              onClick={() => setKind(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {!radicals && <p>Cargando...</p>}
        {radicals && (
          <p>
            {kind === 'radical' ? '242 radicales.' : `${radicals.length} auxiliares.`} {counts['needs-review']} sin
            componentes y sin revisar{kind === 'radical' ? ' (esperado: solo 2-3, los de un trazo)' : ''}.{' '}
            {counts['auto-ok']} con componentes automáticos. {counts.manual} curados a mano.{' '}
            {counts['confirmed-atomic']} confirmados como atómicos.
          </p>
        )}

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
            <option value="all">Todos</option>
          </select>
        </div>
      </header>

      {radicals && (
        <div className="curator-list">
          {filtered.map((r) => (
            <div key={r.id} className={`curator-row status-${r.status}`}>
              <div className="curator-glyph">{r.glyph}</div>
              <div className="curator-info">
                <div className="curator-meaning">{r.meaning || '(sin significado)'}</div>
                <div className="curator-meta">
                  {r.strokeCount ? `${r.strokeCount} trazo${r.strokeCount === 1 ? '' : 's'}` : kind === 'auxiliar' ? 'auxiliar' : 'trazos: ?'}{' '}
                  · {STATUS_LABEL[r.status]}
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
              <div className="curator-row-actions">
                {r.manual == null && (
                  <button
                    className="curator-approve-btn"
                    onClick={() => approveAsCurated(r)}
                    disabled={approvingGlyph === r.glyph}
                    title="Confirmar estos componentes (o la falta de ellos) como curados a mano"
                  >
                    {approvingGlyph === r.glyph ? 'Guardando...' : 'Curado'}
                  </button>
                )}
                <button className="curator-edit-btn" onClick={() => openEditor(r)}>
                  Editar
                </button>
              </div>
            </div>
          ))}
          {filtered.length === 0 && <div className="curator-empty-state">Nada que mostrar con este filtro.</div>}
        </div>
      )}

      {editing && (
        <div className="curator-modal-backdrop" onClick={(e) => e.target === e.currentTarget && setEditingGlyph(null)}>
          <div className="curator-modal">
            <div className="curator-modal-head">
              <div className="curator-glyph big">{editing.glyph}</div>
              <div>
                <div className="curator-meaning">{editing.meaning || '(auxiliar, sin significado propio)'}</div>
                <div className="curator-meta">
                  {editing.strokeCount ? `${editing.strokeCount} trazos · ` : ''}componente de {editing.status}
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
                {editSelection.map((g, i) => (
                  <button className="curator-chip removable" key={`${g}-${i}`} onClick={() => removeComponentAt(i)}>
                    {g} ×
                  </button>
                ))}
              </div>
            </div>

            <input
              className="curator-search"
              autoFocus
              placeholder="Buscar radical, trazo o auxiliar, o escribe algo para buscar también entre kanji..."
              value={pickerQuery}
              onChange={(e) => setPickerQuery(e.target.value)}
            />
            <div className="curator-picker-grid">
              {canAddCustomGlyph && (
                <button
                  className="curator-picker-item add-new"
                  onClick={() => addComponent(pickerQRaw)}
                  title="No esta en radicales, trazos, auxiliares ni kanji: agregarlo como componente nuevo"
                >
                  <span className="g">{pickerQRaw}</span>
                  <span className="m">+ agregar nuevo</span>
                </button>
              )}
              {pickerCandidates.map((r) => {
                const count = editSelection.filter((g) => g === r.glyph).length
                return (
                  <button
                    key={r.id}
                    className={`curator-picker-item${count > 0 ? ' selected' : ''}${r.isStroke ? ' stroke' : ''}${r.isOther ? ' other' : ''}${r.isKanji ? ' kanji' : ''}`}
                    onClick={() => addComponent(r.glyph)}
                    title={r.label}
                  >
                    <span className="g">{r.glyph}</span>
                    <span className="m">{r.isStroke ? 'trazo' : r.isOther ? 'auxiliar' : r.label}{count > 1 ? ` ×${count}` : ''}</span>
                  </button>
                )
              })}
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
