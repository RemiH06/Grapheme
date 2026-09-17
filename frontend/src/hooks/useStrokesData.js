import { useEffect, useState } from 'react'
import { fetchStrokes } from '../api/client'

// Cache a nivel de modulo: varios componentes (StudyMode, DrawFinder)
// usan este hook, pero solo se pide /strokes una vez sin importar
// cuantos lo monten.
let cache = null
let inflight = null

export function useStrokesData() {
  const [strokes, setStrokes] = useState(cache)

  useEffect(() => {
    if (cache) {
      setStrokes(cache)
      return
    }
    if (!inflight) inflight = fetchStrokes().then((data) => (cache = data))
    inflight.then(setStrokes).catch(() => setStrokes({}))
  }, [])

  return strokes // null mientras carga, luego {glifo: trazos[][]}
}
