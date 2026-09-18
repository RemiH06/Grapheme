import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, forceX, forceY } from 'd3-force'
import { CATEGORY_INFO, OTHER_CATEGORY_KEY } from '../graph/constants'

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function radiusOf(n) {
  if (n.kind === 'radical') return 5 + Math.min(11, Math.sqrt(n.degree) * 3.4)
  if (n.kind === 'compound') return 5.5
  return 3.4
}

/** Flecha componente -> contenedor, pegada al borde del nodo destino
 * para no taparlo. Solo se dibuja en las aristas resaltadas (nodo
 * seleccionado): con miles de aristas a la vez seria puro ruido. */
function drawArrowhead(ctx, sx, sy, tx, ty, atRadius, size, color, k) {
  const dx = tx - sx, dy = ty - sy
  const len = Math.hypot(dx, dy) || 1
  const ux = dx / len, uy = dy / len
  const px = tx - ux * atRadius
  const py = ty - uy * atRadius
  const ang = Math.atan2(uy, ux)
  const s = size / k
  ctx.beginPath()
  ctx.moveTo(px, py)
  ctx.lineTo(px - s * Math.cos(ang - Math.PI / 6), py - s * Math.sin(ang - Math.PI / 6))
  ctx.lineTo(px - s * Math.cos(ang + Math.PI / 6), py - s * Math.sin(ang + Math.PI / 6))
  ctx.closePath()
  ctx.fillStyle = color
  ctx.fill()
}

const CORE_JLPT = new Set(['N5', 'N4', 'N3'])
const CORE_HSK_MAX = 6

/** "Core" = JLPT N5-N3 o HSK 1-6: lo que de verdad se estudia para la
 * certificacion. El resto (N2/N1, HSK 7-9) existe en los datos pero
 * queda oculto por defecto para que el grafo no se sature. No depende
 * de `langs` (los radicales no tienen ese campo) porque jlpt/hsk ya
 * vienen vacios cuando el idioma correspondiente no aplica. */
function isCore(n) {
  const jaCore = CORE_JLPT.has(n.jlpt)
  const zhCore = n.hsk != null && n.hsk <= CORE_HSK_MAX
  return jaCore || zhCore
}

/** Los nodos sin dominio real (el residuo de caracteres sin radical
 * indexador resoluble, y los componentes "extra" fuera de la lista de
 * radicales) caen en el cajon virtual OTHER_CATEGORY_KEY: se tratan
 * como una categoria mas, togglable igual que las demas. Antes no
 * tenian categoria en absoluto y por eso `isCategoryDimmed` los daba
 * siempre por "no apagados", lo que los volvia puentes gratis: un
 * radical de una categoria apagada se quedaba visible solo por tocar
 * alguno de estos ~389 nodos sin relacion real con lo que el usuario
 * si queria ver. */
function categoryKeyOf(n) {
  return n.category || OTHER_CATEGORY_KEY
}

function isCategoryDimmed(n, activeCategories) {
  return !activeCategories.has(categoryKeyOf(n))
}

/** Un nodo apagado por categoria desaparece del todo salvo que sea un
 * puente necesario: si al menos uno de sus vecinos directos SI se va a
 * mostrar con normalidad (su categoria, real o el cajon OTHER, esta
 * activa), se queda (opacado, como antes) para no dejar ese vecino con
 * una conexion que apunta a la nada. Solo se checa un salto: un nodo
 * apagado que cuelga de OTRO nodo apagado (sin tocar nada visible
 * directamente) si desaparece, aunque ese otro se quede como puente. */
function dropUnnecessaryDimmed(keep, nodesById, adjacency, activeCategories) {
  const toRemove = []
  for (const id of keep) {
    const n = nodesById.get(id)
    if (!isCategoryDimmed(n, activeCategories)) continue
    const isBridge = adjacency.get(id).some((nb) => {
      if (!keep.has(nb.id)) return false
      return !isCategoryDimmed(nodesById.get(nb.id), activeCategories)
    })
    if (!isBridge) toRemove.push(id)
  }
  for (const id of toRemove) keep.delete(id)
  return keep
}

function computeVisible(nodesById, adjacency, lang, showAllRadicals, levelFilter, activeCategories) {
  const keep = new Set()
  for (const n of nodesById.values()) {
    if (n.kind === 'compound') {
      if (lang !== 'all' && !n.langs.includes(lang)) continue
      if (levelFilter === 'core' && !isCore(n)) continue
      keep.add(n.id)
    } else if (n.kind === 'radical' && n.isCharacter && levelFilter === 'core' && isCore(n)) {
      // Radical que TAMBIEN es su propio caracter jouyou/HSK (ej. 赤 N4,
      // 長 N5, 風 N4): se muestra por si mismo en modo "core" aunque
      // ninguno de sus compuestos dependientes sea core (antes solo se
      // mostraba si algun compuesto vecino lo arrastraba, escondiendo
      // caracteres basicos reales -- 19 radicales tenian este problema).
      const hasJa = !!n.jlpt
      const hasZh = n.hsk != null
      if (lang === 'all' || (lang === 'ja' && hasJa) || (lang === 'zh' && hasZh)) keep.add(n.id)
    }
  }
  for (const id of Array.from(keep)) {
    for (const nb of adjacency.get(id)) {
      const nbNode = nodesById.get(nb.id)
      // en modo "core" no arrastramos otro caracter completo solo porque
      // sea componente de uno core (ej. 体 usa 本 como fonetico); los
      // radicales y componentes fonéticos "extra" si se muestran siempre.
      if (levelFilter === 'core' && nbNode.kind === 'compound' && !isCore(nbNode)) continue
      keep.add(nb.id)
    }
  }
  if (showAllRadicals) {
    for (const n of nodesById.values()) if (n.kind === 'radical') keep.add(n.id)
  }
  if (activeCategories) dropUnnecessaryDimmed(keep, nodesById, adjacency, activeCategories)
  return keep
}

/**
 * Lienzo del grafo: canvas + d3-force para el layout, con paneo/zoom/drag
 * dibujados a mano (mismo enfoque usado en el grafo de LinNeo: refs para
 * todo lo que cambia por frame, para no re-renderizar React en cada tick).
 */
const RadicalGraph = forwardRef(function RadicalGraph(
  { nodesById, edges, adjacency, filters, selectedId, onSelect },
  ref,
) {
  const canvasRef = useRef(null)
  const stageRef = useRef(null)
  const simRef = useRef(null)
  const activeNodesRef = useRef([])
  const activeEdgesRef = useRef([])
  const viewRef = useRef({ x: 0, y: 0, k: 1 })
  const hoverIdRef = useRef(null)
  const selectedIdRef = useRef(selectedId)
  const filtersRef = useRef(filters)
  const sizeRef = useRef({ w: 0, h: 0 })
  const [counts, setCounts] = useState({ radicals: 0, compounds: 0, edges: 0 })

  selectedIdRef.current = selectedId
  filtersRef.current = filters

  // ---- dibujo ----
  function draw() {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const dpr = Math.max(1, window.devicePixelRatio || 1)
    const { w: W, h: H } = sizeRef.current
    const view = viewRef.current
    const selected = selectedIdRef.current ? nodesById.get(selectedIdRef.current) : null
    const neighborIds = selected ? new Set(adjacency.get(selected.id).map((x) => x.id)) : null
    const activeCategories = filtersRef.current.activeCategories

    ctx.save()
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, W, H)
    ctx.fillStyle = cssVar('--bg')
    ctx.fillRect(0, 0, W, H)
    ctx.translate(view.x, view.y)
    ctx.scale(view.k, view.k)

    const edgeColor = cssVar('--edge')
    const accent = cssVar('--accent')
    for (const e of activeEdgesRef.current) {
      const s = e.source, t = e.target
      if (!s || !t || s.x == null || t.x == null) continue
      const touchesSel = selected && (s.id === selected.id || t.id === selected.id)
      ctx.beginPath()
      ctx.moveTo(s.x, s.y)
      ctx.lineTo(t.x, t.y)
      ctx.strokeStyle = touchesSel ? accent : edgeColor
      ctx.globalAlpha = selected ? (touchesSel ? 0.85 : 0.12) : 0.55
      ctx.lineWidth = (touchesSel ? 1.6 : 1) / view.k
      if (touchesSel && e.role === 'phon') ctx.setLineDash([5 / view.k, 4 / view.k])
      ctx.stroke()
      if (touchesSel) {
        ctx.setLineDash([])
        drawArrowhead(ctx, s.x, s.y, t.x, t.y, radiusOf(t) + 2, 7, accent, view.k)
      }
    }
    ctx.setLineDash([])
    ctx.globalAlpha = 1

    for (const n of activeNodesRef.current) {
      if (n.x == null) continue
      const r = radiusOf(n)
      const isSel = selected && n.id === selected.id
      const isNeighbor = neighborIds && neighborIds.has(n.id)
      const categoryDimmed = isCategoryDimmed(n, activeCategories)
      const dim = selected ? !(isSel || isNeighbor) : categoryDimmed

      ctx.beginPath()
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2)
      if (n.kind === 'extra') {
        ctx.strokeStyle = cssVar('--muted')
        ctx.lineWidth = 1.2 / view.k
        ctx.globalAlpha = dim ? 0.12 : 0.75
        ctx.stroke()
        ctx.globalAlpha = 1
        continue
      }
      ctx.fillStyle = cssVar(CATEGORY_INFO[categoryKeyOf(n)].varName)
      ctx.globalAlpha = dim ? 0.16 : 0.93
      ctx.fill()
      if (isSel) {
        ctx.lineWidth = 2.4 / view.k
        ctx.strokeStyle = accent
        ctx.globalAlpha = 1
        ctx.stroke()
      } else if (hoverIdRef.current === n.id) {
        ctx.lineWidth = 1.6 / view.k
        ctx.strokeStyle = cssVar('--ink')
        ctx.globalAlpha = 0.7
        ctx.stroke()
      }
      ctx.globalAlpha = 1

      const showLabel =
        isSel || isNeighbor || hoverIdRef.current === n.id ||
        (!selected && (n.kind === 'radical' ? view.k > 0.9 || n.degree >= 6 : view.k > 1.6))
      if (showLabel && !dim) {
        ctx.font = `${isSel ? '600 ' : ''}${13 / view.k}px "Noto Serif JP", serif`
        ctx.fillStyle = cssVar('--ink')
        ctx.textAlign = 'left'
        ctx.textBaseline = 'middle'
        ctx.fillText(n.glyph, n.x + r + 4, n.y)
      }
    }
    ctx.restore()
  }
  const drawRef = useRef(draw)
  drawRef.current = draw

  // ---- montaje: tamano de canvas + eventos de interaccion (una sola vez) ----
  useEffect(() => {
    const canvas = canvasRef.current
    const stage = stageRef.current
    const ctx = canvas.getContext('2d')

    function setSize() {
      const dpr = Math.max(1, window.devicePixelRatio || 1)
      const w = stage.clientWidth, h = stage.clientHeight
      sizeRef.current = { w, h }
      canvas.width = w * dpr
      canvas.height = h * dpr
      canvas.style.width = w + 'px'
      canvas.style.height = h + 'px'
    }
    setSize()

    const toWorld = (sx, sy) => {
      const v = viewRef.current
      return { x: (sx - v.x) / v.k, y: (sy - v.y) / v.k }
    }
    const screenPos = (e) => {
      const rect = canvas.getBoundingClientRect()
      return { x: e.clientX - rect.left, y: e.clientY - rect.top }
    }
    const nodeAt = (wx, wy) => {
      const nodes = activeNodesRef.current
      for (let i = nodes.length - 1; i >= 0; i--) {
        const n = nodes[i]
        if (n.x == null) continue
        const r = radiusOf(n) + 4
        if ((n.x - wx) ** 2 + (n.y - wy) ** 2 <= r * r) return n
      }
      return null
    }

    let dragging = null, panning = false, panStart = null, moved = false

    function onDown(e) {
      const sp = screenPos(e)
      const w = toWorld(sp.x, sp.y)
      const n = nodeAt(w.x, w.y)
      moved = false
      if (n) {
        dragging = n
        simRef.current?.alphaTarget(0.15).restart()
        n.fx = n.x
        n.fy = n.y
      } else {
        panning = true
        const v = viewRef.current
        panStart = { x: sp.x - v.x, y: sp.y - v.y }
      }
    }
    function onMove(e) {
      const sp = screenPos(e)
      if (dragging) {
        const w = toWorld(sp.x, sp.y)
        dragging.fx = w.x
        dragging.fy = w.y
        moved = true
      } else if (panning) {
        viewRef.current.x = sp.x - panStart.x
        viewRef.current.y = sp.y - panStart.y
        moved = true
        drawRef.current()
      } else {
        const w = toWorld(sp.x, sp.y)
        const n = nodeAt(w.x, w.y)
        const nh = n ? n.id : null
        if (nh !== hoverIdRef.current) {
          hoverIdRef.current = nh
          canvas.style.cursor = n ? 'pointer' : 'grab'
          drawRef.current()
        }
      }
    }
    function onUp() {
      if (dragging) {
        if (!moved) onSelect(dragging.id)
        dragging.fx = null
        dragging.fy = null
        simRef.current?.alphaTarget(0)
      }
      dragging = null
      panning = false
    }
    function onWheel(e) {
      e.preventDefault()
      const sp = screenPos(e)
      const w = toWorld(sp.x, sp.y)
      const v = viewRef.current
      const f = e.deltaY < 0 ? 1.12 : 1 / 1.12
      const nk = Math.max(0.25, Math.min(5, v.k * f))
      v.x = sp.x - w.x * nk
      v.y = sp.y - w.y * nk
      v.k = nk
      drawRef.current()
    }
    function onResize() {
      setSize()
      simRef.current?.force('center', forceCenter(sizeRef.current.w / 2, sizeRef.current.h / 2).strength(0.02))
      simRef.current?.alpha(0.3).restart()
    }

    canvas.addEventListener('mousedown', onDown)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    canvas.addEventListener('wheel', onWheel, { passive: false })
    window.addEventListener('resize', onResize)
    canvas.style.cursor = 'grab'

    return () => {
      canvas.removeEventListener('mousedown', onDown)
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
      canvas.removeEventListener('wheel', onWheel)
      window.removeEventListener('resize', onResize)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ---- reconstruir la simulacion cuando cambian los datos o el filtro ----
  useEffect(() => {
    const visible = computeVisible(
      nodesById,
      adjacency,
      filters.lang,
      filters.showAllRadicals,
      filters.levelFilter,
      filters.activeCategories,
    )
    const activeNodes = Array.from(visible).map((id) => nodesById.get(id))
    const idSet = new Set(activeNodes.map((n) => n.id))
    const activeEdges = edges.filter((e) => {
      const s = typeof e.source === 'object' ? e.source.id : e.source
      const t = typeof e.target === 'object' ? e.target.id : e.target
      return idSet.has(s) && idSet.has(t)
    })
    const { w: W, h: H } = sizeRef.current
    for (const n of activeNodes) {
      if (n.x === null) {
        n.x = W / 2 + (Math.random() - 0.5) * W * 0.6
        n.y = H / 2 + (Math.random() - 0.5) * H * 0.6
      }
    }
    activeNodesRef.current = activeNodes
    activeEdgesRef.current = activeEdges
    setCounts({
      radicals: activeNodes.filter((n) => n.kind === 'radical').length,
      compounds: activeNodes.filter((n) => n.kind === 'compound').length,
      edges: activeEdges.length,
    })

    simRef.current?.stop()
    const sim = forceSimulation(activeNodes)
      .force(
        'link',
        forceLink(activeEdges)
          .id((d) => d.id)
          .distance((d) => (d.source.kind === 'radical' || d.target.kind === 'radical' ? 46 : 60))
          .strength(0.55),
      )
      .force('charge', forceManyBody().strength((d) => (d.kind === 'radical' ? -70 - d.degree * 6 : -50)))
      .force('center', forceCenter(W / 2, H / 2).strength(0.02))
      .force('x', forceX(W / 2).strength(0.02))
      .force('y', forceY(H / 2).strength(0.02))
      .force('collide', forceCollide().radius((d) => radiusOf(d) + 3))
      .alpha(0.9)
      .alphaDecay(0.02)
      .on('tick', () => drawRef.current())
    simRef.current = sim

    // quien pidio menos movimiento no deberia ver 2000 nodos volando por
    // 5 segundos cada vez que cambia un filtro: resolvemos el layout de
    // una vez (sin animar) y dibujamos solo el resultado final.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      sim.stop()
      for (let i = 0; i < 300; i++) sim.tick()
      drawRef.current()
    }

    return () => sim.stop()
  }, [nodesById, edges, adjacency, filters.lang, filters.showAllRadicals, filters.levelFilter, filters.activeCategories])

  // ---- redibujar (sin re-simular) cuando cambia la seleccion o las categorias activas ----
  useEffect(() => {
    draw()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, filters.activeCategories])

  // ---- API imperativa: centrar la camara en un nodo (usado por la busqueda) ----
  useImperativeHandle(ref, () => ({
    centerOn(id) {
      const n = nodesById.get(id)
      if (!n || n.x == null) return
      const v = viewRef.current
      const { w: W, h: H } = sizeRef.current
      v.k = Math.max(v.k, 1.1)
      v.x = W / 2 - n.x * v.k
      v.y = H / 2 - n.y * v.k
      draw()
    },
  }))

  return (
    <div className="stage" ref={stageRef}>
      <canvas ref={canvasRef} />
      <div className="hint">
        Arrastra el fondo para mover el mapa · rueda para zoom · arrastra un nodo para acomodarlo · clic para ver el
        detalle (flecha = componente → contenedor, punteado = solo suena igual) · <kbd>/</kbd> buscar ·{' '}
        <kbd>N</kbd> ir a notas · <kbd>S</kbd> estudiar · <kbd>Esc</kbd> cerrar
      </div>
      <div className="counts">
        {counts.radicals} radicales · {counts.compounds} caracteres · {counts.edges} conexiones
      </div>
    </div>
  )
})

export default RadicalGraph
export { computeVisible, radiusOf }
