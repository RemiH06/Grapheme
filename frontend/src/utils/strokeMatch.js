// Compara trazos dibujados a mano (DrawCanvas) contra los trazos reales
// de KanjiVG (backend/app/data/strokes.json, generado por
// data/build_strokes.py). Ambos lados usan el mismo sistema de
// referencia: cada trazo se re-muestrea a POINTS_PER_STROKE puntos
// espaciados por longitud de arco, normalizados a un cuadrado 0-1
// compartido por todo el glifo.

const POINTS_PER_STROKE = 12

function resampleByArcLength(points, n) {
  if (points.length === 1) return Array(n).fill(points[0])
  const segLens = []
  let total = 0
  for (let i = 1; i < points.length; i++) {
    const dx = points[i][0] - points[i - 1][0]
    const dy = points[i][1] - points[i - 1][1]
    const d = Math.hypot(dx, dy)
    segLens.push(d)
    total += d
  }
  if (total === 0) return Array(n).fill(points[0])
  const out = [points[0]]
  const step = total / (n - 1)
  let segI = 0
  let acc = 0
  let segAcc = 0
  for (let k = 1; k < n - 1; k++) {
    const target = k * step
    while (segI < segLens.length && acc + segLens[segI] < target) {
      acc += segLens[segI]
      segAcc = acc
      segI++
    }
    if (segI >= segLens.length) {
      out.push(points[points.length - 1])
      continue
    }
    const remain = target - segAcc
    const frac = segLens[segI] > 0 ? remain / segLens[segI] : 0
    const p0 = points[segI]
    const p1 = points[segI + 1]
    out.push([p0[0] + (p1[0] - p0[0]) * frac, p0[1] + (p1[1] - p0[1]) * frac])
  }
  out.push(points[points.length - 1])
  return out
}

/** [[x,y],...] por trazo (coordenadas crudas del canvas) -> mismo formato
 * que strokes.json: re-muestreados y normalizados al cuadrado 0-1 del
 * glifo completo (todos los trazos juntos), igual que build_strokes.py. */
export function normalizeDrawnStrokes(rawStrokes) {
  const allPoints = rawStrokes.flat()
  if (allPoints.length === 0) return []
  const xs = allPoints.map((p) => p[0])
  const ys = allPoints.map((p) => p[1])
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const span = Math.max(maxX - minX, maxY - minY) || 1
  const cx = (minX + maxX) / 2
  const cy = (minY + maxY) / 2
  const norm = (p) => [(p[0] - cx) / span + 0.5, (p[1] - cy) / span + 0.5]
  return rawStrokes
    .filter((s) => s.length > 0)
    .map((s) => resampleByArcLength(s, POINTS_PER_STROKE).map(norm))
}

function pointsDistance(a, b) {
  let sum = 0
  for (let i = 0; i < a.length; i++) {
    sum += Math.hypot(a[i][0] - b[i][0], a[i][1] - b[i][1])
  }
  return sum / a.length
}

/** Distancia entre dos trazos normalizados, tolerante a que el trazo se
 * haya dibujado en sentido inverso (muy comun, no es un error real de
 * orden de trazo sino de por donde empezo a dibujar el usuario). */
function strokeDistance(a, b) {
  const forward = pointsDistance(a, b)
  const reversed = pointsDistance(a, [...b].reverse())
  return Math.min(forward, reversed)
}

// Distancia tipica entre dos trazos "parecidos" en este espacio 0-1 ronda
// 0.05-0.15; por arriba de esto ya se ve claramente distinto a simple
// vista. Se usa para convertir distancia cruda a un score 0-100 legible.
const DIST_FOR_ZERO_SCORE = 0.32

function distanceToScore(d) {
  return Math.max(0, Math.round(100 * (1 - d / DIST_FOR_ZERO_SCORE)))
}

// Costo de saltar un trazo de cualquiera de los dos lados en
// alignStrokes(): ni tan barato que el algoritmo prefiera saltarse
// trazos mediocres en vez de emparejarlos (perderia la sensibilidad al
// contenido), ni tan caro que un trazo partido por accidente arrastre
// mal a todo lo que sigue. A medio camino entre un trazo "bien" (dist
// 0.05-0.15) y el umbral de score cero (DIST_FOR_ZERO_SCORE).
const SKIP_COST = 0.22

/** Alinea trazos dibujados contra los reales permitiendo saltar un
 * trazo de cualquiera de los dos lados (tipo distancia de edicion:
 * emparejar, insertar o borrar), en vez de solo comparar por posicion
 * fija. Arregla el caso reportado: levantar el lapiz a mitad de un
 * trazo lo parte en dos, y con emparejamiento estricto por indice todo
 * lo que sigue se desalineaba con el trazo siguiente (real) y el
 * puntaje se desplomaba aunque el dibujo real estuviera casi bien.
 * Sigue siendo sensible al orden: no se permite reordenar trazos, solo
 * saltarse alguno de cualquiera de los dos lados. */
function alignStrokes(drawn, reference) {
  const n = drawn.length
  const m = reference.length
  const dp = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0))
  for (let i = 1; i <= n; i++) dp[i][0] = i * SKIP_COST
  for (let j = 1; j <= m; j++) dp[0][j] = j * SKIP_COST
  for (let i = 1; i <= n; i++) {
    for (let j = 1; j <= m; j++) {
      const matchCost = dp[i - 1][j - 1] + strokeDistance(drawn[i - 1], reference[j - 1])
      const insertCost = dp[i - 1][j] + SKIP_COST // drawn[i-1] no corresponde a nada real
      const deleteCost = dp[i][j - 1] + SKIP_COST // reference[j-1] no se dibujo
      dp[i][j] = Math.min(matchCost, insertCost, deleteCost)
    }
  }
  const pairs = []
  let i = n
  let j = m
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && dp[i][j] === dp[i - 1][j - 1] + strokeDistance(drawn[i - 1], reference[j - 1])) {
      pairs.push({ drawnIdx: i - 1, refIdx: j - 1 })
      i--
      j--
    } else if (i > 0 && dp[i][j] === dp[i - 1][j] + SKIP_COST) {
      pairs.push({ drawnIdx: i - 1, refIdx: null })
      i--
    } else {
      pairs.push({ drawnIdx: null, refIdx: j - 1 })
      j--
    }
  }
  return pairs.reverse()
}

/** Califica un trazado contra los trazos reales de un glifo. Alinea con
 * alignStrokes() en vez de emparejar por indice fijo, y sigue penalizando
 * tener mas o menos trazos que los reales (un trazo saltado o de sobra
 * SI importa para aprender a escribir bien), pero ya no deja que un
 * salto de conteo tumbe la comparacion de todo lo que sigue. */
export function scoreTracing(drawnRawStrokes, referenceStrokes) {
  const drawn = normalizeDrawnStrokes(drawnRawStrokes)
  const pairs = alignStrokes(drawn, referenceStrokes)
  const perStroke = new Array(drawn.length).fill(0)
  const matchedScores = []
  for (const p of pairs) {
    if (p.drawnIdx == null) continue // trazo real sin trazo dibujado correspondiente
    if (p.refIdx == null) continue // trazo dibujado extra: se deja en 0 (rojo)
    const d = strokeDistance(drawn[p.drawnIdx], referenceStrokes[p.refIdx])
    const score = distanceToScore(d)
    perStroke[p.drawnIdx] = score
    matchedScores.push(score)
  }
  const countDiff = Math.abs(drawn.length - referenceStrokes.length)
  const countPenalty = Math.min(40, countDiff * 15)
  const base = matchedScores.length ? matchedScores.reduce((a, b) => a + b, 0) / matchedScores.length : 0
  const overall = Math.max(0, Math.round(base - countPenalty))
  return { overall, perStroke, drawnCount: drawn.length, referenceCount: referenceStrokes.length }
}

// A diferencia de scoreTracing, aqui NO se compara trazo por trazo: se
// probo primero con un emparejamiento voraz por trazo filtrando
// candidatos por conteo de trazos (+-1), y resulto sesgado hacia
// caracteres simples. La razon real: escribir "en cursiva" (fusionar
// trazos reales en menos movimientos de pluma) cambia cuantos trazos
// parece tener el dibujo, asi que ese filtro descartaba el caracter
// correcto de la competencia entera y solo dejaba competir a
// caracteres con pocos trazos, que ademas suelen ser los mas comunes:
// de ahi el sesgo. Comprobado: dibujando 学 (8 trazos reales) fusionado
// en 4 "trazos" de cursiva, el propio 学 seguia siendo la mejor
// coincidencia real, pero el filtro nunca lo dejaba competir y ganaban
// caracteres de 3-4 trazos sin relacion (手, 予, 干...).
//
// Un intento intermedio (concatenar todos los trazos en un solo
// camino y comparar por longitud de arco) tampoco sirvio: el "salto"
// entre el final de un trazo y el inicio del siguiente se contaba como
// distancia real, así que dos trazos bien dibujados pero separados
// (ej. una cruz simple) se comparaban peor de lo que deberian.
//
// La solucion: tratar el dibujo como una NUBE de puntos sin orden ni
// conectividad (distancia "Chamfer": cada punto busca su vecino mas
// cercano del otro lado, en ambas direcciones). Esto es insensible a
// en cuantos trazos se partio el dibujo, en que orden, y a los huecos
// entre trazos.
//
// Con esto se coló un sesgo nuevo, tambien reportado por el usuario:
// dibujos simples encontraban caracteres muy complejos (10-17 trazos)
// casi empatados con los simples correctos. La causa es una asimetria
// real de Chamfer cuando las dos nubes tienen tamanos muy distintos: un
// caracter de 17 trazos aporta ~4x mas puntos que uno de 4, repartidos
// por todo el cuadrado 0-1, asi que CUALQUIER dibujo (simple o no)
// tiene mas chance de caer cerca de alguno de esos puntos con solo
// azar, aunque la forma real no se parezca en nada. Comprobado: una
// simple linea horizontal encontraba 一 correctamente pero con
// caracteres de 13-17 trazos casi empatados unos puntos despues.
//
// El arreglo: limitar ambos lados (dibujo y cada candidato) al mismo
// tope fijo de puntos (CLOUD_CAP) en vez de diluir proporcionalmente a
// su propio tamano -- asi un caracter complejo no aporta mas "chances"
// de coincidir por pura densidad. Tambien resuelve el costo de
// comparar nube contra nube (O(n*m) por candidato, ~2865 candidatos):
// capado a 24 puntos por lado corre una busqueda completa en ~200ms.
const CLOUD_CAP = 24
const CHAMFER_DIST_FOR_ZERO_SCORE = 0.12

function boundedCloud(strokes) {
  const flat = strokes.flat()
  if (flat.length <= CLOUD_CAP) return flat
  const out = []
  for (let i = 0; i < CLOUD_CAP; i++) {
    out.push(flat[Math.round((i * (flat.length - 1)) / (CLOUD_CAP - 1))])
  }
  return out
}

function chamferDistance(a, b) {
  function nearestAvg(x, y) {
    let sum = 0
    for (const p of x) {
      let best = Infinity
      for (const q of y) {
        const d = Math.hypot(p[0] - q[0], p[1] - q[1])
        if (d < best) best = d
      }
      sum += best
    }
    return sum / x.length
  }
  return (nearestAvg(a, b) + nearestAvg(b, a)) / 2
}

// El indice de nubes de referencia no cambia una vez cargado /strokes,
// asi que se calcula una sola vez por indice (no en cada busqueda).
let cloudIndexCache = null
let cloudIndexSource = null

function getCloudIndex(strokesIndex) {
  if (cloudIndexSource === strokesIndex) return cloudIndexCache
  const index = {}
  for (const glyph in strokesIndex) index[glyph] = boundedCloud(strokesIndex[glyph])
  cloudIndexCache = index
  cloudIndexSource = strokesIndex
  return index
}

/** Busca los candidatos del catalogo cuya forma completa se parece mas
 * a lo dibujado (para el "encontrador de simbolos"). strokesIndex es
 * el mismo {glifo: trazos[][]} que sirve /strokes. */
export function findCandidates(drawnRawStrokes, strokesIndex, topK = 8) {
  const drawn = normalizeDrawnStrokes(drawnRawStrokes)
  if (drawn.length === 0) return []
  const drawnCloud = boundedCloud(drawn)
  const clouds = getCloudIndex(strokesIndex)
  const results = []
  for (const glyph in clouds) {
    const d = chamferDistance(drawnCloud, clouds[glyph])
    results.push({ glyph, score: Math.max(0, Math.round(100 * (1 - d / CHAMFER_DIST_FOR_ZERO_SCORE))) })
  }
  results.sort((a, b) => b.score - a.score)
  return results.slice(0, topK)
}
