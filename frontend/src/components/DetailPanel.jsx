import { useState } from 'react'
import { addManyToStudy } from '../api/client'
import { CATEGORY_INFO, ROLE_LABEL } from '../graph/constants'
import { useNotes } from '../hooks/useNotes'
import { useStudyStar } from '../hooks/useStudyStar'
import { canSpeak, preferredLang, speak } from '../utils/speech'

function kindLine(n) {
  if (n.kind === 'radical') {
    const info = CATEGORY_INFO[n.category]
    const strokes = n.strokeCount ? `${n.strokeCount | 0} trazo${n.strokeCount === 1 ? '' : 's'}` : ''
    return `Radical · ${info.label}${strokes ? ' · ' + strokes : ''}`
  }
  if (n.kind === 'compound') {
    if (n.langs.includes('ja') && n.langs.includes('zh')) return 'Kanji / Hanzi compartido'
    if (n.langs.includes('ja')) return 'Kanji compuesto'
    if (n.langs.includes('zh')) return 'Hanzi compuesto'
    return 'Carácter compuesto'
  }
  return 'Componente fonético (fuera de la lista de radicales)'
}

export default function DetailPanel({ node, nodesById, adjacency, onClose, onSelect, onStudyChange, langFilter }) {
  const notes = useNotes(node?.id, node?.glyph)
  const star = useStudyStar(node?.id, node?.glyph)
  if (!node) return <div className="panel" />

  async function toggleStar() {
    await star.toggle()
    onStudyChange?.()
  }

  const byDegreeDesc = (a, b) => (nodesById.get(b.id)?.degree || 0) - (nodesById.get(a.id)?.degree || 0)
  const allConns = adjacency.get(node.id)
  // "component": esto es una PIEZA de node (flecha componente -> node).
  // "owner": node es pieza de ESTO (flecha node -> owner).
  const components = allConns.filter((c) => c.direction === 'component').sort(byDegreeDesc)
  const usedIn = allConns.filter((c) => c.direction === 'owner').sort(byDegreeDesc)

  return (
    <div className={`panel${node ? ' open' : ''}`}>
      <div className="panel-head">
        <div className="panel-glyph">{node.glyph}</div>
        <div className="panel-titles">
          <div className="panel-kind">{kindLine(node)}</div>
          <div className="panel-meaning">
            {node.meaning || (node.kind === 'extra' ? '(componente sin ficha propia todavía)' : '—')}
          </div>
        </div>
        {canSpeak() && (
          <button
            className="panel-speak"
            title="Leer en voz alta"
            onClick={() => speak(node.glyph, preferredLang(node, langFilter))}
          >
            🔊
          </button>
        )}
        <button className="panel-close" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="panel-body">
        <button className={`study-star${star.inStudy ? ' on' : ''}`} onClick={toggleStar} style={{ marginBottom: 14 }}>
          {star.inStudy ? '★ En mi lista de estudio' : '☆ Agregar a mi lista de estudio'}
        </button>

        <div className="badges">
          {node.kind === 'radical' && (
            <span className="badge cat" style={{ background: `var(${CATEGORY_INFO[node.category].varName})` }}>
              {CATEGORY_INFO[node.category].label}
            </span>
          )}
          {node.jlpt && <span className="badge">JLPT {node.jlpt}</span>}
          {node.hsk && <span className="badge">HSK {node.hsk}</span>}
          {node.isCharacter && <span className="badge">También se usa solo</span>}
        </div>

        <div className="readings">
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
          {node.strokeTypeName && (
            <div className="reading-row">
              <span className="label">Trazo base</span>
              <span className="val">{node.strokeTypeName}</span>
            </div>
          )}
        </div>

        {(node.freqJa != null || node.freqZh != null) && (
          <div style={{ marginBottom: 16 }}>
            <div className="section-title">Qué tan común es</div>
            {node.freqJa != null && <FreqBar label="En japonés" pct={node.freqJa} />}
            {node.freqZh != null && <FreqBar label="En chino" pct={node.freqZh} />}
          </div>
        )}

        {node.variants && node.variants.length > 0 && (
          <>
            <div className="section-title">También se escribe</div>
            <div className="variants-row">
              {node.variants.map((v) => (
                <span className="variant-chip" key={v}>
                  {v}
                </span>
              ))}
            </div>
          </>
        )}

        {node.mnemonic && (
          <div style={{ marginBottom: 16 }}>
            <div className="section-title">Mnemónico</div>
            <div style={{ fontSize: 13, color: 'var(--ink)' }}>{node.mnemonic}</div>
          </div>
        )}

        {components.length > 0 && (
          <>
            <div className="section-title">
              Se compone de ({components.length})
              <AddAllButton conns={components} nodesById={nodesById} onDone={onStudyChange} />
            </div>
            <ConnList conns={components} nodesById={nodesById} onSelect={onSelect} />
          </>
        )}

        <div className="section-title">
          {usedIn.length === 0
            ? 'No aparece en ningún otro carácter todavía'
            : `Aparece en ${usedIn.length} carácter${usedIn.length === 1 ? '' : 'es'}`}
          {usedIn.length > 0 && <AddAllButton conns={usedIn} nodesById={nodesById} onDone={onStudyChange} />}
        </div>
        {usedIn.length === 0 ? (
          <div className="empty-conn">Es una hoja: nada lo usa como pieza en el catálogo actual.</div>
        ) : (
          <ConnList conns={usedIn} nodesById={nodesById} onSelect={onSelect} />
        )}

        <div className="section-title">Notas personales</div>
        <div className="notes-box">
          <textarea
            value={notes.text}
            onChange={(e) => notes.onChange(e.target.value)}
            placeholder="Escribe tu propia nota sobre este nodo: mnemónico, confusiones, ejemplos..."
          />
          <div className="notes-status">{notes.status}</div>
        </div>
      </div>
    </div>
  )
}

function AddAllButton({ conns, nodesById, onDone }) {
  const [done, setDone] = useState(false)
  const items = conns.map((c) => nodesById.get(c.id)).filter(Boolean)
  if (done) return <span className="add-all-btn" style={{ color: 'var(--muted)', cursor: 'default' }}>agregadas ✓</span>
  return (
    <button
      className="add-all-btn"
      onClick={async () => {
        setDone(true)
        await addManyToStudy(items.map((n) => ({ id: n.id, glyph: n.glyph })))
        onDone?.()
      }}
    >
      + agregar todas a estudio
    </button>
  )
}

function ConnList({ conns, nodesById, onSelect }) {
  return (
    <div className="conn-list">
      {conns.map((c, i) => {
        const cn = nodesById.get(c.id)
        if (!cn) return null
        return (
          <button className="conn-item" key={`${c.id}-${c.direction}-${c.pos}-${i}`} onClick={() => onSelect(cn.id)}>
            <span className="g">{cn.glyph}</span>
            <span className="info">
              <div className="m">{cn.meaning || cn.glyph}</div>
              <div className="r">{[cn.onyomi, cn.kunyomi, cn.pinyin].filter(Boolean).join(' · ')}</div>
            </span>
            <span className="role-tag">{ROLE_LABEL[c.role] || ''}</span>
          </button>
        )
      })}
    </div>
  )
}

function FreqBar({ label, pct }) {
  return (
    <div className="freq-row">
      <span className="freq-label">{label}</span>
      <div className="freq-track">
        <div className="freq-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="freq-pct">{pct}%</span>
    </div>
  )
}
