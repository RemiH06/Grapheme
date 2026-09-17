[![Made with Python](https://forthebadge.com/images/badges/made-with-python.svg)](https://github.com/RemiH06/Grapheme)
[![React](https://img.shields.io/badge/-React-61DAFB?style=for-the-badge&logo=react&logoColor=white)](https://github.com/RemiH06/Grapheme)

```ascii
 ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗███████╗███╗   ███╗███████╗
██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║██╔════╝████╗ ████║██╔════╝
██║  ███╗██████╔╝███████║██████╔╝███████║█████╗  ██╔████╔██║█████╗  
██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║██╔══╝  ██║╚██╔╝██║██╔══╝  
╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║███████╗██║ ╚═╝ ██║███████╗
 ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚══════╝
        by Hex (@RemiH06)          version 0.1
```

[![AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg?style=for-the-badge)](LICENSE)

## Overview

### General Description

**Grapheme** conecta los 243 radicales kanji/hanzi con el catálogo
completo de kanji jōyō (2136) y hanzi HSK 3.0 (3000) en un solo grafo,
para estudiar japonés (JLPT) y chino (HSK) viendo qué componentes
comparten los caracteres entre sí. Nace de una clasificación de
radicales hecha a mano en Excel que hice hace varios años (`docs/Pictograms.xlsx`), ampliada con
cinco datasets abiertos para cubrir lecturas, frecuencia real de uso y
descomposición de cada carácter: ver `docs/METODOLOGIA.md` para el
detalle completo de qué dato sale de dónde.

El grafo es dirigido (componente → carácter que lo contiene) y
distingue conexiones semánticas de fonéticas. La mayoría de los hanzi
son compuestos fono-semánticos, y confundir "suena igual" con
"significa algo relacionado" es un error común al aprender. Corre
completamente local: un backend FastAPI sirve el grafo estático y
guarda notas personales por nodo en SQLite; el frontend es un lienzo
canvas + d3-force en React.

```diff
- El grafo completo (~4265 nodos) es denso a simple vista sin filtrar; por default solo se muestra JLPT N5-N3 + HSK 1-6.
```

## Installation

1. Generar el dataset (descarga ~6 MB de datasets abiertos la primera vez):
   ```bash
   cd data
   pip install openpyxl
   python fetch_sources.py
   python build_dataset.py
   python build_strokes.py
   ```
2. Levantar el backend (puerto 8055):
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8055
   ```
3. Levantar el frontend (puerto 5190):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
4. Abrir `http://localhost:5190`.

## Features

- Grafo interactivo (canvas + d3-force) de 242 radicales, 3684
  caracteres y ~7750 aristas dirigidas.
- Distingue conexiones semánticas de fonéticas (línea sólida vs.
  punteada) con flecha componente → contenedor al seleccionar un nodo.
- Filtro por idioma (japonés / chino / ambos) y por nivel (JLPT N5-N3
  + HSK 1-6 por default; catálogo completo con un toggle).
- Leyenda de categorías semánticas (Humano, Cuerpo, Naturaleza...),
  togglable por categoría.
- Búsqueda por glifo, lectura o significado.
- Panel de detalle: lecturas, significado, qué tan común es (percentil
  de frecuencia real de corpus, no inventado), de qué se compone un
  carácter y en cuáles otros aparece. Se filtra por idioma igual que el
  grafo.
- Notas personales por nodo, persistentes en SQLite.
- Modo de estudio con repetición espaciada (SM-2 simplificado) y tres
  técnicas: mostrar la respuesta, escribir el significado, o trazar el
  carácter a mano y calificarlo contra el orden de trazo real (99.9%
  del catálogo, KanjiVG + makemeahanzi). Lectura en voz alta con Web
  Speech API.
- Encontrador de símbolos por dibujo: dibuja un carácter que no
  recuerdas cómo se busca y la app propone los candidatos del catálogo
  con trazos más parecidos, comparando la forma completa sin importar
  el orden ni en cuántos trazos lo partiste.
- Modo claro/oscuro automático, con paleta neutra y un solo acento de
  color.

## Future Features

- Recuperar el sistema de nivel/mnemónico del Excel original (ver
  `steps.md`): existía una progresión de aprendizaje pensada a mano
  que se perdió al conectar el catálogo externo.
- Clustering real sobre la estructura del grafo para verificar (o
  reemplazar) las categorías semánticas asignadas a mano en el Excel.
- Alineación de trazos tolerante a errores en el quiz de trazado (ver
  `steps.md`), para que partir un trazo por accidente no desalinee la
  calificación del resto.

## Autoría

por Hex ([@RemiH06](https://github.com/RemiH06))
