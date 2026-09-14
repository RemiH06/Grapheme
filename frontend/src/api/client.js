const BASE = '/api'

async function req(path, options) {
  const res = await fetch(BASE + path, options)
  if (!res.ok) throw new Error(`${options?.method || 'GET'} ${path} -> ${res.status}`)
  return res.json()
}

export function fetchGraph() {
  return req('/graph')
}

export function fetchAllNotes() {
  return req('/notes')
}

export function fetchNote(id) {
  return req(`/notes/${encodeURIComponent(id)}`)
}

export function saveNote(id, text, glyph) {
  return req(`/notes/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, glyph }),
  })
}
