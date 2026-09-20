import { useEffect, useMemo, useState } from 'react'
import {
  clearRadicalComponents,
  fetchAdminAuxiliares,
  fetchAdminKanji,
  fetchAdminRadicals,
  fetchAdminStrokes,
  saveRadicalComponents,
  saveStrokeDerivation,
} from '../api/client'

/** Herramienta local de curacion, sin relacion con la app de estudio:
 * revisar los 242 radicales y decidir a mano de que radicales reales
 * esta compuesto cada uno, para los casos donde la fuente etimologica
 * los marca "pictograficos" (=atomicos) pero en realidad si tienen
 * piezas reconocibles (ver docs/METODOLOGIA.md seccion 11). Montada
 * aparte del resto de la app en /?curate=radicals, nunca en la UI
 * normal. Tres pestañas, cada una con su propio significado de "listo":
 *
 * - Radicales: los 242 (menos las fusiones), "se compone de" (multiple).
 * - Trazos: los del bloque oficial CJK Strokes que no duplican un
 *   radical de un solo trazo, "deriva de" (un solo radical o ninguno).
 * - Auxiliares: los nodos "extra" reales sin pronunciacion (321 al
 *   momento de escribir esto), mismo editor que los radicales.
 *
 * Radicales/Auxiliares guardan en data/radical_components_manual.json;
 * Trazos guarda en data/stroke_derivation_manual.json. Ambos los lee
 * build_dataset.py en la siguiente corrida. */

const KIND_TABS = [
  { key: 'radical', label: 'Radicales' },
  { key: 'stroke', label: 'Trazos' },
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
  const [canonicalAuxiliares, setCanonicalAuxiliares] = useState(null) // los 321, SIEMPRE cargados (solo se listan en el picker si hay busqueda)
  const [canonicalKanji, setCanonicalKanji] = useState(null) // los 3668, SIEMPRE cargados (idem)
  const [strokes, setStrokes] = useState(null) // la lista que se esta REVISANDO en la pestaña "Trazos"
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('needs-review')
  const [editingGlyph, setEditingGlyph] = useState(null)
  const [editSelection, setEditSelection] = useState([])
  const [pickerQuery, setPickerQuery] = useState('')
  const [saving, setSaving] = useState(false)
  const [approvingGlyph, setApprovingGlyph] = useState(null)
  const [strokeEditGlyph, setStrokeEditGlyph] = useState(null)
  const [strokePickerQuery, setStrokePickerQuery] = useState('')

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
  function loadStrokes() {
    return fetchAdminStrokes()
      .then((data) => setStrokes(data))
      .catch((e) => setError(e))
  }
  useEffect(() => {
    setError(null)
    setRadicals(null)
    setStrokes(null)
    setStatusFilter(kind === 'stroke' ? 'all' : 'needs-review')
    if (kind === 'stroke') loadStrokes()
    else loadList()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind])

  // Boton rapido para el caso comun: confirmar que un radical/auxiliar
  // de verdad es un atomo (sin abrir el editor completo a poner "sin
  // componentes" a mano cada vez). Guarda lista vacia = "revisado, es
  // atomico de verdad" (distinto de null = "no revisado").
  async function approveAsAtomic(r) {
    setApprovingGlyph(r.glyph)
    try {
      await saveRadicalComponents(r.glyph, [])
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

  const strokeCounts = useMemo(() => {
    if (!strokes) return { derived: 0, undetermined: 0 }
    return {
      derived: strokes.filter((s) => s.derivesFrom).length,
      undetermined: strokes.filter((s) => !s.derivesFrom).length,
    }
  }, [strokes])

  const filteredStrokes = useMemo(() => {
    if (!strokes) return []
    const q = query.trim().toLowerCase()
    return strokes
      .filter((s) => !q || s.glyph.includes(q) || (s.derivesFrom || '').includes(q))
      .sort((a, b) => (a.derivesFrom ? 1 : 0) - (b.derivesFrom ? 1 : 0))
  }, [strokes, query])

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

  async function setDerivation(glyph, radicalGlyph) {
    setSaving(true)
    try {
      await saveStrokeDerivation(glyph, radicalGlyph)
      setStrokeEditGlyph(null)
      await loadStrokes()
    } finally {
      setSaving(false)
    }
  }

  if (error) {
    return <div style={{ padding: 24, fontFamily: 'sans-serif' }}>No se pudo cargar el admin: {String(error.message)}</div>
  }

  const editing = editingGlyph ? withStatus.find((r) => r.glyph === editingGlyph) : null
  const pickerQ = pickerQuery.trim().toLowerCase()
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
  // Auxiliares y kanji solo entran a la lista de candidatos si hay
  // busqueda: son 321 y 3668, mostrarlos sin filtrar haria el modal
  // lento sin ganar nada (radicales/trazos ya cubren la mayoria de
  // casos, y son pocos como para mostrarlos siempre).
  const otherCandidates = pickerQ
    ? (canonicalAuxiliares || []).map((x) => ({
        id: x.id,
        glyph: x.glyph,
        label: 'auxiliar',
        isOther: true,
      }))
    : []
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

  const strokeEditing = strokeEditGlyph ? strokes?.find((s) => s.glyph === strokeEditGlyph) : null
  const strokePickerQ = strokePickerQuery.trim().toLowerCase()

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

        {kind !== 'stroke' && !radicals && <p>Cargando...</p>}
        {kind !== 'stroke' && radicals && (
          <p>
            {kind === 'radical' ? '242 radicales.' : `${radicals.length} auxiliares.`} {counts['needs-review']} sin
            componentes y sin revisar{kind === 'radical' ? ' (esperado: solo 2-3, los de un trazo)' : ''}.{' '}
            {counts['auto-ok']} con componentes automáticos. {counts.manual} curados a mano.{' '}
            {counts['confirmed-atomic']} confirmados como atómicos.
          </p>
        )}
        {kind === 'stroke' && !strokes && <p>Cargando...</p>}
        {kind === 'stroke' && strokes && (
          <p>
            {strokes.length} trazos del bloque oficial CJK Strokes. {strokeCounts.derived} ya con radical asignado.{' '}
            {strokeCounts.undetermined} sin asignar todavía.
          </p>
        )}

        <div className="curator-controls">
          <input
            className="curator-search"
            placeholder={kind === 'stroke' ? 'Buscar trazo o radical asignado...' : 'Buscar radical o significado...'}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {kind !== 'stroke' && (
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="needs-review">Sin revisar ({counts['needs-review']})</option>
              <option value="auto-ok">Automático ({counts['auto-ok']})</option>
              <option value="manual">Curado a mano ({counts.manual})</option>
              <option value="confirmed-atomic">Confirmado atómico ({counts['confirmed-atomic']})</option>
              <option value="all">Todos</option>
            </select>
          )}
        </div>
      </header>

      {kind !== 'stroke' && radicals && (
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
                {r.status !== 'confirmed-atomic' && (
                  <button
                    className="curator-approve-btn"
                    onClick={() => approveAsAtomic(r)}
                    disabled={approvingGlyph === r.glyph}
                    title="Confirmar que este radical de verdad no tiene componentes"
                  >
                    {approvingGlyph === r.glyph ? 'Guardando...' : 'Aprobar como unidad'}
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

      {kind === 'stroke' && strokes && (
        <div className="curator-list">
          {filteredStrokes.map((s) => (
            <div key={s.glyph} className={`curator-row status-${s.derivesFrom ? 'confirmed-atomic' : 'needs-review'}`}>
              <div className="curator-glyph">{s.glyph}</div>
              <div className="curator-info">
                <div className="curator-meaning">{s.derivesFrom ? `Deriva de ${s.derivesFrom}` : '(sin asignar)'}</div>
                <div className="curator-meta">trazo, bloque CJK Strokes</div>
              </div>
              <div className="curator-row-actions">
                <button className="curator-edit-btn" onClick={() => setStrokeEditGlyph(s.glyph)}>
                  Asignar radical
                </button>
              </div>
            </div>
          ))}
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
              placeholder="Buscar radical o trazo, o escribe algo para buscar también entre auxiliares y kanji..."
              value={pickerQuery}
              onChange={(e) => setPickerQuery(e.target.value)}
            />
            <div className="curator-picker-grid">
              {pickerCandidates.map((r) => (
                <button
                  key={r.id}
                  className={`curator-picker-item${editSelection.includes(r.glyph) ? ' selected' : ''}${r.isStroke ? ' stroke' : ''}${r.isOther ? ' other' : ''}${r.isKanji ? ' kanji' : ''}`}
                  onClick={() => toggleComponent(r.glyph)}
                  title={r.label}
                >
                  <span className="g">{r.glyph}</span>
                  <span className="m">{r.isStroke ? 'trazo' : r.isOther ? 'auxiliar' : r.label}</span>
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

      {strokeEditing && (
        <div className="curator-modal-backdrop" onClick={(e) => e.target === e.currentTarget && setStrokeEditGlyph(null)}>
          <div className="curator-modal">
            <div className="curator-modal-head">
              <div className="curator-glyph big">{strokeEditing.glyph}</div>
              <div>
                <div className="curator-meaning">
                  {strokeEditing.derivesFrom ? `Deriva de ${strokeEditing.derivesFrom}` : 'Sin asignar todavía'}
                </div>
                <div className="curator-meta">trazo, bloque CJK Strokes</div>
              </div>
              <button className="curator-close" onClick={() => setStrokeEditGlyph(null)}>
                ×
              </button>
            </div>

            <input
              className="curator-search"
              autoFocus
              placeholder="Buscar el radical del que deriva este trazo..."
              value={strokePickerQuery}
              onChange={(e) => setStrokePickerQuery(e.target.value)}
            />
            <div className="curator-picker-grid">
              {[
                ...(canonicalRadicals || []).map((r) => ({ id: r.id, glyph: r.glyph, label: r.meaning, isStroke: false })),
                ...(canonicalStrokes || []).map((s) => ({
                  id: `stroke-${s.glyph}`,
                  glyph: s.glyph,
                  label: s.derivesFrom ? `trazo, deriva de ${s.derivesFrom}` : 'trazo (bloque CJK Strokes)',
                  isStroke: true,
                })),
              ]
                .filter((r) => r.glyph !== strokeEditing.glyph)
                .filter((r) => {
                  if (!strokePickerQ) return true
                  const badge = r.isStroke ? 'trazo' : ''
                  return r.glyph.includes(strokePickerQ) || r.label.toLowerCase().includes(strokePickerQ) || badge.includes(strokePickerQ)
                })
                .map((r) => (
                  <button
                    key={r.id}
                    className={`curator-picker-item${strokeEditing.derivesFrom === r.glyph ? ' selected' : ''}${r.isStroke ? ' stroke' : ''}`}
                    onClick={() => setDerivation(strokeEditing.glyph, r.glyph)}
                    title={r.label}
                    disabled={saving}
                  >
                    <span className="g">{r.glyph}</span>
                    <span className="m">{r.isStroke ? 'trazo' : r.label}</span>
                  </button>
                ))}
            </div>

            <div className="curator-modal-actions">
              <button onClick={() => setStrokeEditGlyph(null)} disabled={saving}>
                Cerrar
              </button>
              {strokeEditing.derivesFrom && (
                <button onClick={() => setDerivation(strokeEditing.glyph, null)} disabled={saving}>
                  Quitar asignación
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
