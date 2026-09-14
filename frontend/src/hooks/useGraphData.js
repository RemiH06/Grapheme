import { useEffect, useState } from 'react'
import { fetchGraph } from '../api/client'
import { buildGraph } from '../graph/buildGraph'

export function useGraphData() {
  const [graph, setGraph] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetchGraph()
      .then((raw) => {
        if (!cancelled) setGraph(buildGraph(raw))
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { graph, error, loading: !graph && !error }
}
