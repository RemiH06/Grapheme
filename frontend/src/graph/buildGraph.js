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
      category: r.category || null,
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
      category: c.category || null,
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
    nodesById.set(x.id, {
      id: x.id,
      glyph: x.glyph,
      kind: 'extra',
      meaning: x.meaning,
      pinyin: x.pinyin,
      isExample: !!x.isExample,
      x: null,
      y: null,
    })
  }

  // e.from = el componente (la pieza simple), e.to = lo que lo contiene
  // (el radical o caracter compuesto). La direccion siempre va de lo
  // simple a lo complejo.
  const edges = raw.edges.map((e) => ({ source: e.from, target: e.to, pos: e.pos, role: e.role }))

  const adjacency = new Map()
  for (const n of nodesById.values()) adjacency.set(n.id, [])
  for (const e of edges) {
    // desde el nodo "to": esta es una de MIS piezas (direction: component)
    adjacency.get(e.target).push({ id: e.source, role: e.role, pos: e.pos, direction: 'component' })
    // desde el nodo "from": esto es algo de lo que YO soy pieza (direction: owner)
    adjacency.get(e.source).push({ id: e.target, role: e.role, pos: e.pos, direction: 'owner' })
  }
  for (const n of nodesById.values()) n.degree = adjacency.get(n.id).length

  return { nodesById, edges, adjacency }
}
