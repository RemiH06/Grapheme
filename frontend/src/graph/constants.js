// Dominio semantico por radical/caracter, asignado a mano por el
// significado real de cada uno de los 242 radicales (ver
// docs/METODOLOGIA.md): cada caracter hereda el dominio de su radical
// de indexacion real (el mismo que usan los diccionarios de papel), no
// de un clustering automatico -- se probo agrupar caracteres por
// co-ocurrencia (Louvain) y salio disparejo y dificil de nombrar.
export const CATEGORY_INFO = {
  People: { label: 'Personas', hint: 'gente, roles, comunicación', varName: '--cat-human' },
  Body: { label: 'Cuerpo', hint: 'anatomía, salud', varName: '--cat-body' },
  Places: { label: 'Lugares', hint: 'geografía, arquitectura', varName: '--cat-places' },
  Nature: { label: 'Naturaleza', hint: 'elementos, plantas, clima', varName: '--cat-nature' },
  Food: { label: 'Comida', hint: 'grano, bebida, sabor', varName: '--cat-food' },
  Animals: { label: 'Animales', hint: 'fauna', varName: '--cat-animals' },
  Objects: { label: 'Objetos', hint: 'herramientas, materiales, artefactos', varName: '--cat-objects' },
  Actions: { label: 'Acciones', hint: 'movimiento, verbos', varName: '--cat-life' },
  Abstract: { label: 'Abstracto', hint: 'cualidades, gramática, números', varName: '--cat-structural' },
}

export const CATEGORY_ORDER = [
  'People', 'Body', 'Places', 'Nature', 'Food', 'Animals', 'Objects', 'Actions', 'Abstract',
]

export const ROLE_LABEL = { sem: 'significado', phon: 'fonético', mark: 'marca gráfica' }
export const KIND_LABEL = { radical: 'Radical', compound: 'Compuesto', extra: 'Componente fonético' }
