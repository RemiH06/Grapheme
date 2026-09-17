// Lectura en voz alta via Web Speech API (nativa del navegador, sin
// servidor ni costo). La calidad de la voz depende de las voces que
// el sistema operativo tenga instaladas; si no hay ninguna para el
// idioma pedido, el navegador cae a la que tenga mas parecida o no
// dice nada -- por eso speak() regresa un booleano, para que quien
// llama pueda avisar si no funciono.

export function canSpeak() {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

/** true si el nodo tiene alguna lectura real registrada (on'yomi,
 * kun'yomi o pinyin). Sin esto no sabemos como se pronuncia de verdad,
 * asi que no tiene sentido ofrecer el boton de leer en voz alta. */
export function hasReading(node) {
  return !!(node?.onyomi || node?.kunyomi || node?.pinyin)
}

/** lang: 'ja-JP' | 'zh-CN' (BCP-47). Corta cualquier lectura anterior
 * antes de empezar una nueva, para que no se encimen. */
export function speak(text, lang) {
  if (!canSpeak() || !text) return false
  const utter = new SpeechSynthesisUtterance(text)
  utter.lang = lang
  utter.rate = 0.85
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utter)
  return true
}

/** Idioma preferido para leer un nodo en voz alta, segun lo que tenga
 * cargado (jouyou/HSK) y, si tiene ambos, cual esta viendo el usuario. */
export function preferredLang(node, langFilter) {
  const hasJa = !!(node.onyomi || node.kunyomi || node.jlpt)
  const hasZh = !!(node.pinyin || node.hsk)
  if (hasJa && hasZh) return langFilter === 'zh' ? 'zh-CN' : 'ja-JP'
  if (hasZh) return 'zh-CN'
  return 'ja-JP'
}
