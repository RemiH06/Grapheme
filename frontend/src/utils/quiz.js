function normalize(s) {
  return s
    .toLowerCase()
    .trim()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
}

// Los significados vienen como "love; affection" o "to become tired, weary":
// se compara contra cada parte por separado y se acepta contención en
// cualquier sentido para tolerar respuestas parciales ("tired" vs.
// "to become tired").
export function checkMeaning(input, meaning) {
  const guess = normalize(input || '')
  if (guess.length < 2 || !meaning) return false
  const parts = meaning
    .split(/[;,/]/)
    .map(normalize)
    .filter(Boolean)
  return parts.some((part) => part === guess || part.includes(guess) || guess.includes(part))
}
