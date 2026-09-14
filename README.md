# Atlas de Radicales

Grafo interactivo que conecta los radicales kanji/hanzi con los caracteres
que los usan, para estudiar japonés (JLPT) y chino (HSK) viendo qué
componentes se repiten entre pictogramas. Nace de `Pictograms.xlsx`
(clasificación de radicales) más un set curado de caracteres compuestos.

## Estructura

```
data/build_dataset.py     # Excel -> backend/app/data/graph_data.json
backend/                  # FastAPI: sirve el grafo + notas personales (SQLite)
frontend/                 # React + Vite: el lienzo (canvas + d3-force)
```

No usa una base de datos de grafos (Neo4j, etc.): el dataset completo
(243 radicales, ~160 caracteres, ~300 aristas) pesa menos de 150 KB y
vive en un JSON estático. Lo único que necesita persistencia real son
las notas personales por nodo, guardadas en un archivo SQLite.

## Correrlo

**1. Generar el dataset** (solo hace falta de nuevo si editas
`Pictograms.xlsx` o agregas caracteres en `data/build_dataset.py`):

```bash
cd data
pip install openpyxl
python build_dataset.py
```

**2. Backend** (puerto 8055):

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8055
```

**3. Frontend** (puerto 5190):

```bash
cd frontend
npm install
npm run dev
```

Abre http://localhost:5190.

## Ampliar el set de caracteres

`data/build_dataset.py` tiene una lista `COMPOUNDS` con tuplas
`(carácter, onyomi, kunyomi, pinyin, significado, jlpt, hsk, componentes)`.
Agregar un carácter nuevo es agregar una tupla ahí y volver a correr el
script; el radical al que apunte cada componente no necesita existir de
antemano en el grafo (si no es uno de los 243 radicales, se crea como
"componente fonético" automáticamente).
