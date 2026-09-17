import { useEffect, useState } from 'react'
import { addToStudy, fetchStudyState, removeFromStudy } from '../api/client'

/** Estrella de "en mi lista de estudio" para un solo nodo. */
export function useStudyStar(nodeId, glyph) {
  const [inStudy, setInStudy] = useState(false)

  useEffect(() => {
    if (!nodeId) return
    let cancelled = false
    fetchStudyState(nodeId).then((s) => {
      if (!cancelled) setInStudy(!!s && s.in_study !== false)
    })
    return () => {
      cancelled = true
    }
  }, [nodeId])

  async function toggle() {
    if (inStudy) {
      setInStudy(false)
      await removeFromStudy(nodeId)
    } else {
      setInStudy(true)
      await addToStudy(nodeId, glyph)
    }
  }

  return { inStudy, toggle }
}
