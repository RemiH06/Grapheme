import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './theme/tokens.css'
import App from './App.jsx'
import RadicalCurator from './components/RadicalCurator.jsx'

// Herramienta local de curacion (ver RadicalCurator.jsx), aparte de la
// app normal: nunca se enlaza desde la UI, solo se llega escribiendo la
// URL a mano.
const isCurator = new URLSearchParams(window.location.search).get('curate') === 'radicals'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {isCurator ? <RadicalCurator /> : <App />}
  </StrictMode>,
)
