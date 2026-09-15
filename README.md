# Atlas de Radicales

Grafo interactivo que conecta los radicales kanji/hanzi con **todos** los
kanji jōyō y hanzi HSK 3.0 que los usan, para estudiar japonés (JLPT) y
chino (HSK) viendo qué componentes se repiten entre pictogramas. Nace de
`docs/Pictograms.xlsx` (clasificación de radicales) más el catálogo
completo de caracteres, armado a partir de datasets abiertos.

## Estructura

```
docs/Pictograms.xlsx      # clasificacion de radicales (no se versiona, ver .gitignore)
data/fetch_sources.py     # descarga y cachea los 3 datasets abiertos en data/sources/
data/build_dataset.py     # Excel + data/sources/ -> backend/app/data/graph_data.json
backend/                  # FastAPI: sirve el grafo + notas personales (SQLite)
frontend/                 # React + Vite: el lienzo (canvas + d3-force)
```

No usa una base de datos de grafos (Neo4j, etc.): el dataset completo
(243 radicales + 3688 caracteres + ~330 componentes fonéticos, ~7200
aristas) pesa unos pocos MB y vive en un JSON estático, generado una
vez con `build_dataset.py`. Lo único que necesita persistencia real en
tiempo de ejecución son las notas personales por nodo, guardadas en un
archivo SQLite.

## Qué cubre el catálogo

- **2136 kanji jōyō** completos (todos), con JLPT, grado escolar y
  frecuencia real de uso.
- **3000 hanzi HSK 3.0** completos (niveles 1 a 9), con pinyin y
  frecuencia real de uso.
- Descomposición en componentes para ambos (con posición y, cuando se
  sabe, si el componente aporta significado o solo suena — la mayoría
  de los caracteres chinos son fono-semánticos).
- El campo **"qué tan común"** (0-100%) es un percentil calculado sobre
  un ranking de frecuencia real de corpus — no un número inventado, y
  japonés/chino usan cada uno su propia escala (no son comparables
  1 a 1 entre sí, son corpus distintos).
- Por defecto el grafo solo muestra JLPT N5–N3 y HSK 1–6 (lo que de
  verdad se estudia para certificarse); hay un botón para revelar todo
  el catálogo (N2/N1, HSK 7-9).

**Límite conocido**: unos 194 kanji jōyō en su forma *shinjitai*
(simplificación específica de Japón, ej. 図 対 労 営 実) no tienen
descomposición todavía — las fuentes usadas son de origen chino y no
siempre cubren esas formas. Quedan como nodos con lectura/significado
pero sin aristas hacia radicales.

### Fuentes de datos (todas de licencia abierta)

| Dataset | Para qué | Licencia |
|---|---|---|
| [kanji-data](https://github.com/davidluzgouveia/kanji-data) | Los 2136 kanji jōyō: JLPT, grado, frecuencia, lecturas | MIT |
| [chinese-hsk-and-frequency-lists](https://github.com/alyssabedard/chinese-hsk-and-frequency-lists) | Hanzi HSK 3.0, frecuencia real (Jun Da), descomposición | MIT / CC BY-SA 4.0 |
| [makemeahanzi](https://github.com/skishore/makemeahanzi) | Descomposición posicional + rol semántico/fonético | MIT |

## Correrlo

**1. Generar el dataset** (solo hace falta de nuevo si editas
`docs/Pictograms.xlsx`; los datasets externos se cachean una sola vez):

```bash
cd data
pip install openpyxl
python fetch_sources.py   # descarga ~6 MB, una sola vez
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

## Ampliar o corregir el catálogo

El catálogo de caracteres ya no se edita a mano: sale completo de
`data/fetch_sources.py` + `data/build_dataset.py`. Para agregar
información que falte (por ejemplo, decomposición para los ~194
shinjitai sin cubrir), lo natural es sumar una fuente más en
`fetch_sources.py` y un paso de resolución en `components_of()` dentro
de `build_dataset.py`, en vez de tipear caracteres sueltos.

Los 243 **radicales** sí siguen viniendo de `docs/Pictograms.xlsx` y de
los diccionarios `RADICAL_MEANING` / `STROKE_TYPES` en
`build_dataset.py` — esos sí se editan a mano ahí.
