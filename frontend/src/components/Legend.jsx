import { CATEGORY_INFO, CATEGORY_ORDER } from '../graph/constants'

export default function Legend({ filters, setFilters }) {
  function toggle(key) {
    setFilters((f) => {
      const next = new Set(f.activeCategories)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return { ...f, activeCategories: next }
    })
  }

  return (
    <div className="legend">
      {CATEGORY_ORDER.map((key) => {
        const info = CATEGORY_INFO[key]
        const off = !filters.activeCategories.has(key)
        return (
          <button key={key} className={`chip${off ? ' off' : ''}`} title={info.hint} onClick={() => toggle(key)}>
            <span className="dot" style={{ background: `var(${info.varName})` }} />
            {info.label}
          </button>
        )
      })}
    </div>
  )
}
