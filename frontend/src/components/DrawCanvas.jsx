import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'

const SIZE = 260

/** Lienzo de dibujo para trazar caracteres a mano: captura cada trazo
 * (pointerdown -> pointerup) como una lista de puntos [x,y] en
 * coordenadas del canvas. `strokeColors`, si se pasa, pinta cada trazo
 * ya dibujado con ese color (feedback de calificación por trazo) en vez
 * del color de tinta normal. */
const DrawCanvas = forwardRef(function DrawCanvas({ strokeColors }, ref) {
  const canvasRef = useRef(null)
  const strokesRef = useRef([]) // [[ [x,y], ... ], ...]
  const drawingRef = useRef(false)

  function redraw() {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, SIZE, SIZE)

    const root = getComputedStyle(document.documentElement)
    const lineStrong = root.getPropertyValue('--line-strong').trim() || '#babec6'
    const inkColor = root.getPropertyValue('--ink').trim() || '#1e2027'

    // guia tipo hoja de caligrafia: marco + cruz central
    ctx.strokeStyle = lineStrong
    ctx.lineWidth = 1
    ctx.setLineDash([4, 4])
    ctx.strokeRect(0.5, 0.5, SIZE - 1, SIZE - 1)
    ctx.beginPath()
    ctx.moveTo(SIZE / 2, 0)
    ctx.lineTo(SIZE / 2, SIZE)
    ctx.moveTo(0, SIZE / 2)
    ctx.lineTo(SIZE, SIZE / 2)
    ctx.stroke()
    ctx.setLineDash([])
    strokesRef.current.forEach((stroke, i) => {
      if (stroke.length === 0) return
      ctx.strokeStyle = (strokeColors && strokeColors[i]) || inkColor
      ctx.lineWidth = 5
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      ctx.beginPath()
      ctx.moveTo(stroke[0][0], stroke[0][1])
      for (let p = 1; p < stroke.length; p++) ctx.lineTo(stroke[p][0], stroke[p][1])
      ctx.stroke()
    })
  }

  useEffect(redraw, [strokeColors])

  useImperativeHandle(ref, () => ({
    getStrokes: () => strokesRef.current.filter((s) => s.length > 1),
    clear: () => {
      strokesRef.current = []
      redraw()
    },
    undo: () => {
      strokesRef.current.pop()
      redraw()
    },
    isEmpty: () => strokesRef.current.every((s) => s.length === 0),
  }))

  function localPoint(e) {
    const rect = canvasRef.current.getBoundingClientRect()
    return [
      ((e.clientX - rect.left) / rect.width) * SIZE,
      ((e.clientY - rect.top) / rect.height) * SIZE,
    ]
  }

  function onPointerDown(e) {
    canvasRef.current.setPointerCapture(e.pointerId)
    drawingRef.current = true
    strokesRef.current.push([localPoint(e)])
    redraw()
  }

  function onPointerMove(e) {
    if (!drawingRef.current) return
    strokesRef.current[strokesRef.current.length - 1].push(localPoint(e))
    redraw()
  }

  function onPointerUp() {
    drawingRef.current = false
  }

  return (
    <canvas
      ref={canvasRef}
      className="draw-canvas"
      width={SIZE}
      height={SIZE}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerLeave={onPointerUp}
    />
  )
})

export default DrawCanvas
