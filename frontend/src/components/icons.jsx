// Set propio de iconos SVG (trazo simple, currentColor) para reemplazar
// los emojis nativos: se ven igual en cualquier sistema operativo y
// heredan el color del texto (gris en reposo, rojo carmín en hover,
// verde/rojo de calificación para correcto/incorrecto).

function base(size, extra) {
  return { width: size, height: size, viewBox: '0 0 24 24', 'aria-hidden': 'true', focusable: 'false', ...extra }
}

export function SoundIcon({ size = 18, className, style }) {
  return (
    <svg {...base(size)} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
      <path d="M4 9v6h4l5 4V5L8 9H4z" />
      <path d="M16.5 8.5a5 5 0 0 1 0 7" />
      <path d="M19 6a8.5 8.5 0 0 1 0 12" />
    </svg>
  )
}

export function CloseIcon({ size = 16, className, style }) {
  return (
    <svg {...base(size)} fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" className={className} style={style}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  )
}

export function StarIcon({ size = 16, filled = false, className, style }) {
  return (
    <svg
      {...base(size)}
      fill={filled ? 'currentColor' : 'none'}
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinejoin="round"
      className={className}
      style={style}
    >
      <path d="M12 3.5l2.47 5.18 5.53.68-4.06 3.98 1.02 5.66L12 16.9l-4.96 2.1 1.02-5.66-4.06-3.98 5.53-.68L12 3.5z" />
    </svg>
  )
}

export function CheckIcon({ size = 16, className, style }) {
  return (
    <svg {...base(size)} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
      <path d="M5 12.5l4.5 4.5L19 7.5" />
    </svg>
  )
}

export function XMarkIcon({ size = 14, className, style }) {
  return (
    <svg {...base(size)} fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" className={className} style={style}>
      <path d="M7 7l10 10M17 7L7 17" />
    </svg>
  )
}

export function BookIcon({ size = 18, className, style }) {
  return (
    <svg {...base(size)} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
      <path d="M6 6.2c1.6-.7 3.4-.7 4.6.2v11.2c-1.2-.9-3-.9-4.6-.2v-11.2z" />
      <path d="M18 6.2c-1.6-.7-3.4-.7-4.6.2v11.2c1.2-.9 3-.9 4.6-.2v-11.2z" />
      <path d="M12 6.5v11.2" />
    </svg>
  )
}

export function BookmarkIcon({ size = 18, className, style }) {
  return (
    <svg {...base(size)} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
      <path d="M6 3.5h12v17l-6-4.2-6 4.2v-17z" />
    </svg>
  )
}

export function PencilIcon({ size = 18, className, style }) {
  return (
    <svg {...base(size)} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
      <path d="M14.5 4.5l5 5L8 21H3v-5z" />
      <path d="M12.5 6.5l5 5" />
    </svg>
  )
}
