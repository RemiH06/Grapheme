import { useEffect, useRef, useState } from 'react'
import { fetchNote, saveNote } from '../api/client'

const SAVE_DELAY = 650

/** Nota personal de un nodo: carga al seleccionar, guarda con debounce. */
export function useNotes(nodeId, glyph) {
  const [text, setText] = useState('')
  const [status, setStatus] = useState('')
  const timer = useRef(null)

  useEffect(() => {
    setText('')
    setStatus('')
    if (!nodeId) return
    let cancelled = false
    fetchNote(nodeId).then((note) => {
      if (!cancelled) setText(note.text || '')
    })
    return () => {
      cancelled = true
      clearTimeout(timer.current)
    }
  }, [nodeId])

  function onChange(value) {
    setText(value)
    setStatus('Escribiendo...')
    clearTimeout(timer.current)
    timer.current = setTimeout(async () => {
      try {
        await saveNote(nodeId, value, glyph)
        setStatus(value ? 'Guardado' : 'Nota borrada')
      } catch {
        setStatus('No se pudo guardar')
      }
    }, SAVE_DELAY)
  }

  return { text, status, onChange }
}
