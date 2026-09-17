# De dónde sale cada dato del grafo

Este documento existe para que en 6 meses no haya que releer el código
para recordar por qué un campo dice lo que dice. Cubre el pipeline
completo: `docs/Pictograms.xlsx` → `data/fetch_sources.py` →
`data/build_dataset.py` → `backend/app/data/graph_data.json`.

## 1. Qué viene de `Pictograms.xlsx` (tuyo) vs. de fuentes externas

| Campo | Origen | Dónde en el código |
|---|---|---|
| Los 243 radicales (glifo, variantes) | Excel, hoja "Kanji", tabla "Approach" | `parse_excel()` + `MERGE_INTO` |
| Conteo de trazos por radical | Excel (columna Type/Class) | `parse_excel()` |
| Categoría semántica (Humano/Cuerpo/Naturaleza...) | Excel, matriz de filas 5-22 | `parse_excel()`, diccionario `category_of` |
| Significado en inglés de cada radical | **Escrito a mano por Claude**, la columna del Excel estaba vacía salvo 一 | `RADICAL_MEANING` |
| Tipo de trazo base (横/竖/点/撇/折/钩) | **Añadido por Claude**, no existía en el Excel; solo cubre los 6 radicales de 1 trazo | `STROKE_TYPES` |
| Lecturas on'yomi/kun'yomi/pinyin/JLPT/HSK/frecuencia de TODOS los caracteres | **100% fuentes externas** (sección 3) | `load_jouyou()`, `load_mega_hanzi()` |
| Descomposición en componentes | **100% fuentes externas** | `components_of()` |

**Importante**: la columna "Mnemonic" del Excel y el índice de nivel
(0-9) de la matriz semántica (tus nombres "Position/Base", "Unity",
"Mnemonic duality"...) NO llegan a la app hoy. El índice numérico de
nivel se parsea (`tier` en `radicals_raw`) pero no se conecta a ningún
nodo final ni se muestra en la UI; los nombres de nivel ni siquiera se
parsean ya (se cayeron en la reescritura que agregó el catálogo
externo). Si se quieren recuperar, es cuestión de volver a leerlos en
`parse_excel()` y agregar la UI que los muestre — no es que falten
datos, es que dejamos de usar los que ya teníamos.

## 2. Radicales: la fusión de variantes Unicode

El Excel repite el mismo radical dos veces cuando cambia de posición
(ej. "mano" aparece como ⺘ y como el 手 completo). Unicode además tiene
**el mismo radical dos veces** en bloques distintos: uno en "CJK
Radicals Supplement" (lo que trae el Excel, ej. ⺘) y otro en "CJK
Unified Ideographs" (lo que usan de verdad los datasets de
descomposición, ej. 扌). Sin fusionar esto, radicales tan comunes como
手/水/人/心/言 aparecían con cero conexiones. `MERGE_INTO` en
`build_dataset.py` es esa tabla de equivalencia — armada a mano
comparando los nodos con más conexiones "extra" (componentes fuera de
la lista de 243) contra los 243 radicales reales.

Caso especial: **阝** (oreja) es ambiguo sin ver la posición — a la
izquierda es 阜 (colina), a la derecha es 邑 (ciudad). Se resuelve en
`_resolve_ear()` viendo si la posición del componente dice "left" o no.

Mismo mecanismo para pares tradicional/simplificado que son el mismo
radical con dos codepoints (ej. `讲`→言, `户`→戸): el más reciente es
**齐→齊** — 济/剂/挤 (HSK) usan 齐 como fonético, pero el radical del
Excel es la forma tradicional 齊. Sin el merge, 齊 quedaba totalmente
aislado del grafo (ver sección 7).

## 3. El catálogo completo de caracteres (2136 jōyō + 3000 HSK)

Tres datasets abiertos, descargados una sola vez por
`data/fetch_sources.py` y cacheados en `data/sources/` (no se
versionan, ver `.gitignore`):

| Fuente | Repo | Para qué | Licencia |
|---|---|---|---|
| kanji-data | [davidluzgouveia/kanji-data](https://github.com/davidluzgouveia/kanji-data) | Los 2136 kanji jōyō oficiales: JLPT (escala no oficial post-2010, la única que existe hoy), grado escolar, frecuencia real (corpus de periódico), on'yomi/kun'yomi, significado en inglés | MIT |
| chinese-hsk-and-frequency-lists | [alyssabedard/...](https://github.com/alyssabedard/chinese-hsk-and-frequency-lists) | Los 3000 hanzi HSK 3.0 oficiales (niveles 1-9), pinyin, frecuencia real (Jun Da, corpus moderno de ~200M caracteres) | MIT / CC BY-SA 4.0 |
| makemeahanzi | [skishore/makemeahanzi](https://github.com/skishore/makemeahanzi) | Descomposición posicional (IDS, Ideographic Description Sequences) + etimología con rol semántico/fonético, para ~9500 caracteres | MIT |
| KanjiVG | [KanjiVG/kanjivg](https://github.com/KanjiVG/kanjivg) | Descomposición de trazos específica de Japón (`kvg:element`/`kvg:position`/`kvg:phon`), único respaldo que sí conoce la forma *shinjitai* | CC BY-SA 3.0 |

`components_of()` en `build_dataset.py` prueba las fuentes en cascada,
en este orden, y usa la primera que tenga datos para el glifo:

1. **makemeahanzi** (IDS + etimología con rol semántico/fonético) —
   fuente principal, la más confiable.
2. **`mega_hanzi_compilation.csv`** (dentro del repo de HSK) — respaldo
   cuando makemeahanzi no tiene el carácter: lista plana de componentes
   sin posición ni rol (se le asigna `role='sem'` por default, con
   menos confianza que la fuente principal).
3. **KanjiVG** — segundo respaldo, solo entra cuando ni makemeahanzi ni
   mega_hanzi tienen nada. Es de origen japonés (no chino como las
   otras dos), así que es la única que cubre los kanji jōyō en su forma
   *shinjitai* (図, 対, 労, 営, 実...), que las fuentes chinas no
   indexan bajo ningún codepoint. Trae posición (`kvg:position`,
   términos de caligrafía japonesa: kamae/tare/nyo/etc., mapeados a las
   mismas etiquetas que IDS en `KANJIVG_POSITION_MAP`) y a veces un
   hint fonético (`kvg:phon`) que se usa igual que el `phonetic` de
   makemeahanzi para decidir el rol de la arista.

## 4. Cómo se decide si un radical "ya no se descompone más"

Esto fue un bug real que el usuario encontró (色 no se conectaba a 巴
a pesar de que sí se compone de él). La causa: el código trataba
"es uno de los 243 radicales" como sinónimo de "es átomo". Falso —
色 es radical Y se compone de otras piezas.

La regla correcta usa la **etimología** que trae makemeahanzi
(`is_pictographic()` en `build_dataset.py`): si el tipo es
`pictographic` (un dibujo de una sola pieza, como 木 水 火 人 口), su
campo de "descomposición" describe cómo se traza el glifo en trazos
sueltos, no componentes reales, así que se ignora. Si el tipo es
`ideographic` o `pictophonetic` (o no hay etimología registrada), se
confía en la descomposición porque el propio registro etimológico dice
que el carácter se construyó combinando partes con sentido.

Esta regla es imperfecta en el margen: 大, 小 y 川 están etiquetados
`ideographic` en la fuente y por eso sí se descomponen en trazos
sueltos (大 = 一+人, "una persona con los brazos abiertos"), aunque
para un radical tan básico eso raye en trivial. Se dejó así por ser
una regla explicable y consistente en vez de una lista de excepciones
a mano.

Caso de verificación: **龠** (flauta de pan) sigue sin aristas de
entrada aunque KanjiVG sí trae un desglose gráfico de sus trazos. Es
correcto que se quede así — makemeahanzi clasifica su etimología como
`pictographic` ("Panpipes": un dibujo de una sola pieza), así que
`is_pictographic()` lo protege igual que a 木 o 水. No es un hueco de
cobertura, es la regla funcionando como debe.

### 4.1 Radicales pictográficos sin ningún compuesto real en el catálogo

Que `is_pictographic()` proteja correctamente a un radical de una
descomposición falsa no significa que ese radical tenga uso real en el
catálogo jōyō+HSK: 韭, 鹵, 黽, 鼎, 鼠 y 龠 son radicales Kangxi legítimos
(misma categoría que 木/水/火/人/口), pero a diferencia de esos, no
aparecen como componente de NINGÚN carácter jōyō/HSK — quedaban como
nodos totalmente aislados (ni una arista, ni entrante ni saliente), lo
que en el lienzo se ve indistinguible de un nodo roto.

`pick_illustrative_example()` en `build_dataset.py` les agrega **una**
arista de ejemplo hacia un compuesto real (aunque quede fuera del
catálogo oficial 2136+3000), usando el campo `component_in` que
mega_hanzi ya trae por cada radical/carácter — ej. 韭 → 谶 ("prophecy/
omen"), 鼎 → 鼐 ("incense tripod"). Ese nodo extra se marca
`isExample: true` y se etiqueta "ejemplo real" en la UI (en vez de
"significado"/"fonético") para dejar claro que es una ilustración fuera
del alcance oficial del proyecto, no un carácter jōyō/HSK más. Si
mega_hanzi no tiene ni siquiera una fila para el radical (caso de 鹵 y
黽), no hay ningún ejemplo que agregar — se quedan aislados de verdad,
por falta total de datos, no por una regla mal aplicada.

## 5. Dirección de las aristas y rol semántico/fonético

Cada arista va **del componente hacia lo que lo contiene** (nunca al
revés): `{from: componente, to: contenedor}`. Esto se decidió porque
así se lee la jerarquía real (una pieza simple es usada por muchas
palabras; una palabra compleja no es usada por nada). El rol
(`sem`/`phon`) sale directo de `etymology.phonetic` /
`etymology.semantic` cuando makemeahanzi lo trae — es dato real de la
fuente, no inferido. En el lienzo esto se ve como flecha (hacia el
contenedor) y línea punteada cuando el rol es `phon`, pero solo en las
aristas resaltadas del nodo seleccionado (dibujar flechas en las ~7400
aristas a la vez sería puro ruido visual).

## 6. El campo "qué tan común es" (0-100%)

Percentil de una posición de frecuencia **real** dentro de su propio
corpus — no un número inventado, y japonés/chino no son comparables
1 a 1 porque son corpus distintos (`pct_rank()` en `build_dataset.py`):

- Japonés: el campo `freq` de kanji-data, un ranking 1-2495 basado en
  un corpus de periódico. ~97 de los 2136 jōyō no tienen ranking (son
  demasiado raros para ese corpus) y quedan sin porcentaje.
- Chino: `frequency_junda`, el ranking de Jun Da sobre ~9933
  caracteres de un corpus moderno de ~200 millones de caracteres — se
  usa el rango completo de esa lista como denominador, no solo los 3000
  HSK, para que el percentil signifique "qué tan común en chino en
  general", no solo "qué tan común dentro de HSK".

## 7. Límites conocidos (ver también `steps.md`)

- **Caracteres sin ninguna arista de entrada: 0.** El hueco de ~194
  kanji jōyō en forma *shinjitai* (図, 対, 労, 営, 実...) que las
  fuentes chinas no cubrían quedó resuelto al agregar KanjiVG como
  tercer nivel de respaldo en `components_of()` (sección 3).
- **Radicales totalmente aislados (ni una arista, entrante ni
  saliente): 5** (de 242) — todos verificados como correctos, no como
  huecos, y sin ningún dato en ninguna de las cuatro fuentes que
  permita conectarlos a nada:
  - マ, ユ: marcadores mnemotécnicos propios (no son radicales Unicode
    reales, no hay fuente externa que pueda cubrirlos).
  - ヨ: variante rara de "hocico de cerdo", sin uso como componente en
    el catálogo actual.
  - 鹵, 黽: radicales Kangxi legítimos pero tan raros que mega_hanzi ni
    siquiera trae una fila propia para ellos (ver sección 4.1) — a
    diferencia de 韭/鼎/鼠/龠, que sí tienen una arista de ejemplo hacia
    un compuesto real fuera de catálogo.
  - 齊 dejó de estar aislado: se fusionó con su forma simplificada 齐
    (sección 2), que sí es HSK 3 y aparece en 济/剂/挤.
- **111 de 242 radicales sin categoría semántica**: así estaba tu
  matriz original, nunca se completó.
- **Tier / nombres de nivel del Excel**: parseados parcialmente,
  no conectados a la UI (ver sección 1).
- **La marca "remove" (鬥)** del Excel original nunca se resolvió —
  sigue en la lista de radicales sin cambios, por instrucción explícita
  (no se elimina ningún radical del mapeo aunque el Excel lo marcara
  para quitar).
