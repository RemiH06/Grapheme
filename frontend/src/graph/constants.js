export const CATEGORY_FOLD = {
  Human: 'Human', Body: 'Body', Places: 'Places', Nature: 'Nature', Matter: 'Nature',
  Food: 'Food', Animals: 'Animals', Objects: 'Objects', Life: 'Life',
  Primitive: 'Structural', Components: 'Structural',
}

export const CATEGORY_INFO = {
  Human: { label: 'Humano', hint: 'personas, roles, cuerpo social', varName: '--cat-human' },
  Body: { label: 'Cuerpo', hint: 'anatomía, salud', varName: '--cat-body' },
  Places: { label: 'Lugares', hint: 'geografía, arquitectura', varName: '--cat-places' },
  Nature: { label: 'Naturaleza', hint: 'elementos, materia, plantas', varName: '--cat-nature' },
  Food: { label: 'Comida', hint: 'grano, bebida, sabor', varName: '--cat-food' },
  Animals: { label: 'Animales', hint: 'fauna', varName: '--cat-animals' },
  Objects: { label: 'Objetos', hint: 'herramientas, artefactos', varName: '--cat-objects' },
  Life: { label: 'Vida', hint: 'nacer, crecer, existir', varName: '--cat-life' },
  Structural: { label: 'Estructural', hint: 'trazos base, sin clasificar aún', varName: '--cat-structural' },
}

export const CATEGORY_ORDER = [
  'Human', 'Body', 'Places', 'Nature', 'Food', 'Animals', 'Objects', 'Life', 'Structural',
]

export const ROLE_LABEL = { sem: 'significado', phon: 'fonético', mark: 'marca gráfica' }
export const KIND_LABEL = { radical: 'Radical', compound: 'Compuesto', extra: 'Componente fonético' }
