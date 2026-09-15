import { CATEGORY_FOLD } from './constants'

/**
 * Convierte la respuesta cruda de /api/graph (radicales, caracteres
 * compuestos, componentes fonéticos "extra" y aristas) en las
 * estructuras que usa el lienzo: un mapa de nodos por id, la lista de
 * aristas, y una lista de adyacencia (para "aparece en X caracteres" y
 * para decidir que radicales entran al filtro por idioma).
 */
export function buildGraph(raw) {
  const nodesById = new Map()

  for (const r of raw.radicals) {
    nodesById.set(r.id, {
      id: r.id,
      glyph: r.glyph,
      kind: 'radical',
      category: CATEGORY_FOLD[r.category] || 'Structural',
      strokeCount: r.strokeCount,
      strokeType: r.strokeType,
      strokeTypeName: r.strokeTypeName,
      onyomi: r.onyomi,
      kunyomi: r.kunyomi,
      pinyin: r.pinyin,
      meaning: r.meaning,
      mnemonic: r.mnemonic,
      variants: r.variants || [],
      isCharacter: !!r.isCharacter,
      jlpt: r.jlpt,
      hsk: r.hsk,
      freqJa: r.freqJa,
      freqZh: r.freqZh,
      x: null,
      y: null,
    })
  }
  for (const c of raw.characters) {
    nodesById.set(c.id, {
      id: c.id,
      glyph: c.glyph,
      kind: 'compound',
      onyomi: c.onyomi,
      kunyomi: c.kunyomi,
      pinyin: c.pinyin,
      meaning: c.meaning,
      jlpt: c.jlpt,
      hsk: c.hsk,
      freqJa: c.freqJa,
      freqZh: c.freqZh,
      langs: c.langs || [],
      x: null,
      y: null,
    })
  }
  for (const x of raw.extras) {
    nodesById.set(x.id, { id: x.id, glyph: x.glyph, kind: 'extra', x: null, y: null })
  }

  const edges = raw.edges.map((e) => ({ source: e.from, target: e.to, pos: e.pos, role: e.role }))

  const adjacency = new Map()
  for (const n of nodesById.values()) adjacency.set(n.id, [])
  for (const e of edges) {
    adjacency.get(e.source).push({ id: e.target, role: e.role, pos: e.pos })
    adjacency.get(e.target).push({ id: e.source, role: e.role, pos: e.pos })
  }
  for (const n of nodesById.values()) n.degree = adjacency.get(n.id).length

  return { nodesById, edges, adjacency }
}
