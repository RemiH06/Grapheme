const BASE = '/api'

async function req(path, options) {
  const res = await fetch(BASE + path, options)
  if (!res.ok) throw new Error(`${options?.method || 'GET'} ${path} -> ${res.status}`)
  return res.json()
}

export function fetchGraph() {
  return req('/graph')
}

export function fetchStrokes() {
  return req('/strokes')
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

// ---- lista de estudio + repeticion espaciada ----

export function fetchStudyState(id) {
  return req(`/study/${encodeURIComponent(id)}`)
}

export function fetchDueCards() {
  return req('/study/due')
}

export function fetchStudyList() {
  return req('/study/list')
}

export function addToStudy(id, glyph) {
  return req(`/study/${encodeURIComponent(id)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ glyph }),
  })
}

export function addManyToStudy(items) {
  return req('/study/add-many', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  })
}

export function removeFromStudy(id) {
  return req(`/study/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function reviewCard(id, grade, glyph) {
  return req(`/study/${encodeURIComponent(id)}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ grade, glyph }),
  })
}

// ---- curacion manual de componentes de radicales (herramienta local) ----

export function fetchAdminRadicals() {
  return req('/admin/radicals')
}

export function saveRadicalComponents(glyph, components) {
  return req(`/admin/radical-components/${encodeURIComponent(glyph)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ components }),
  })
}

export function clearRadicalComponents(glyph) {
  return req(`/admin/radical-components/${encodeURIComponent(glyph)}`, { method: 'DELETE' })
}
