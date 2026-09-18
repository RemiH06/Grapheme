# De dónde sale cada dato del grafo

Este documento existe para que en 6 meses no haya que releer el código
para recordar por qué un campo dice lo que dice. Cubre el pipeline
completo: `docs/Pictograms.xlsx` → `data/fetch_sources.py` →
`data/build_dataset.py` → `backend/app/data/graph_data.json`, más el
pipeline paralelo de trazos: `data/build_strokes.py` →
`backend/app/data/strokes.json` (sección 8).

## 1. Qué viene de `Pictograms.xlsx` (tuyo) vs. de fuentes externas

| Campo | Origen | Dónde en el código |
|---|---|---|
| Los 243 radicales (glifo, variantes) | Excel, hoja "Kanji", tabla "Approach" | `parse_excel()` + `MERGE_INTO` |
| Conteo de trazos por radical | Excel (columna Type/Class) | `parse_excel()` |
| Dominio semántico (Personas/Cuerpo/Naturaleza...) | **Ya no viene del Excel** (ver sección 9), reclasificado a mano por significado real | `DOMAIN_MAP` en `build_dataset.py` |
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
`parse_excel()` y agregar la UI que los muestre. No es que falten
datos, es que dejamos de usar los que ya teníamos.

## 2. Radicales: la fusión de variantes Unicode

El Excel repite el mismo radical dos veces cuando cambia de posición
(ej. "mano" aparece como ⺘ y como el 手 completo). Unicode además tiene
**el mismo radical dos veces** en bloques distintos: uno en "CJK
Radicals Supplement" (lo que trae el Excel, ej. ⺘) y otro en "CJK
Unified Ideographs" (lo que usan de verdad los datasets de
descomposición, ej. 扌). Sin fusionar esto, radicales tan comunes como
手/水/人/心/言 aparecían con cero conexiones. `MERGE_INTO` en
`build_dataset.py` es esa tabla de equivalencia, armada a mano
comparando los nodos con más conexiones "extra" (componentes fuera de
la lista de 243) contra los 243 radicales reales.

Caso especial: **阝** (oreja) es ambiguo sin ver la posición: a la
izquierda es 阜 (colina), a la derecha es 邑 (ciudad). Se resuelve en
`_resolve_ear()` viendo si la posición del componente dice "left" o no.

Mismo mecanismo para pares tradicional/simplificado que son el mismo
radical con dos codepoints (ej. `讲`→言, `户`→戸): el más reciente es
**齐→齊**: 济/剂/挤 (HSK) usan 齐 como fonético, pero el radical del
Excel es la forma tradicional 齊. Sin el merge, 齊 quedaba totalmente
aislado del grafo (ver sección 7).

## 3. El catálogo completo de caracteres (2136 jōyō + 3000 HSK)

Cuatro datasets abiertos, descargados una sola vez por
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

1. **makemeahanzi** (IDS + etimología con rol semántico/fonético):
   fuente principal, la más confiable.
2. **`mega_hanzi_compilation.csv`** (dentro del repo de HSK), respaldo
   cuando makemeahanzi no tiene el carácter: lista plana de componentes
   sin posición ni rol (se le asigna `role='sem'` por default, con
   menos confianza que la fuente principal).
3. **KanjiVG**: segundo respaldo, solo entra cuando ni makemeahanzi ni
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
"es uno de los 243 radicales" como sinónimo de "es átomo". Falso:
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
correcto que se quede así: makemeahanzi clasifica su etimología como
`pictographic` ("Panpipes": un dibujo de una sola pieza), así que
`is_pictographic()` lo protege igual que a 木 o 水. No es un hueco de
cobertura, es la regla funcionando como debe.

### 4.1 Radicales pictográficos sin ningún compuesto real en el catálogo

Que `is_pictographic()` proteja correctamente a un radical de una
descomposición falsa no significa que ese radical tenga uso real en el
catálogo jōyō+HSK: 韭, 鹵, 黽, 鼎, 鼠 y 龠 son radicales Kangxi legítimos
(misma categoría que 木/水/火/人/口), pero a diferencia de esos, no
aparecen como componente de NINGÚN carácter jōyō/HSK: quedaban como
nodos totalmente aislados (ni una arista, ni entrante ni saliente), lo
que en el lienzo se ve indistinguible de un nodo roto.

`pick_illustrative_example()` en `build_dataset.py` les agrega **una**
arista de ejemplo hacia un compuesto real (aunque quede fuera del
catálogo oficial 2136+3000), usando el campo `component_in` que
mega_hanzi ya trae por cada radical/carácter (ej. 韭 → 谶, "prophecy/
omen"; 鼎 → 鼐, "incense tripod"). Ese nodo extra se marca
`isExample: true` y se etiqueta "ejemplo real" en la UI (en vez de
"significado"/"fonético") para dejar claro que es una ilustración fuera
del alcance oficial del proyecto, no un carácter jōyō/HSK más. Si
mega_hanzi no tiene ni siquiera una fila para el radical (caso de 鹵 y
黽), no hay ningún ejemplo que agregar: se quedan aislados de verdad,
por falta total de datos, no por una regla mal aplicada.

## 5. Dirección de las aristas y rol semántico/fonético

Cada arista va **del componente hacia lo que lo contiene** (nunca al
revés): `{from: componente, to: contenedor}`. Esto se decidió porque
así se lee la jerarquía real (una pieza simple es usada por muchas
palabras; una palabra compleja no es usada por nada). El rol
(`sem`/`phon`) sale directo de `etymology.phonetic` /
`etymology.semantic` cuando makemeahanzi lo trae: es dato real de la
fuente, no inferido. En el lienzo esto se ve como flecha (hacia el
contenedor) y línea punteada cuando el rol es `phon`, pero solo en las
aristas resaltadas del nodo seleccionado (dibujar flechas en las ~7400
aristas a la vez sería puro ruido visual).

## 6. El campo "qué tan común es" (0-100%)

Percentil de una posición de frecuencia **real** dentro de su propio
corpus: no un número inventado, y japonés/chino no son comparables
1 a 1 porque son corpus distintos (`pct_rank()` en `build_dataset.py`):

- Japonés: el campo `freq` de kanji-data, un ranking 1-2495 basado en
  un corpus de periódico. ~97 de los 2136 jōyō no tienen ranking (son
  demasiado raros para ese corpus) y quedan sin porcentaje.
- Chino: `frequency_junda`, el ranking de Jun Da sobre ~9933
  caracteres de un corpus moderno de ~200 millones de caracteres. Se
  usa el rango completo de esa lista como denominador, no solo los 3000
  HSK, para que el percentil signifique "qué tan común en chino en
  general", no solo "qué tan común dentro de HSK".

## 7. Límites conocidos (ver también `steps.md`)

- **Caracteres sin ninguna arista de entrada: 0.** El hueco de ~194
  kanji jōyō en forma *shinjitai* (図, 対, 労, 営, 実...) que las
  fuentes chinas no cubrían quedó resuelto al agregar KanjiVG como
  tercer nivel de respaldo en `components_of()` (sección 3).
- **Radicales totalmente aislados (ni una arista, entrante ni
  saliente): 5** (de 242): todos verificados como correctos, no como
  huecos, y sin ningún dato en ninguna de las cuatro fuentes que
  permita conectarlos a nada:
  - マ, ユ: marcadores mnemotécnicos propios (no son radicales Unicode
    reales, no hay fuente externa que pueda cubrirlos).
  - ヨ: variante rara de "hocico de cerdo", sin uso como componente en
    el catálogo actual.
  - 鹵, 黽: radicales Kangxi legítimos pero tan raros que mega_hanzi ni
    siquiera trae una fila propia para ellos (ver sección 4.1). A
    diferencia de 韭/鼎/鼠/龠, que sí tienen una arista de ejemplo hacia
    un compuesto real fuera de catálogo.
  - 齊 dejó de estar aislado: se fusionó con su forma simplificada 齐
    (sección 2), que sí es HSK 3 y aparece en 济/剂/挤.
- **~70 caracteres (1.9%) sin dominio semántico resoluble**: ver
  sección 9 para el porqué y el mecanismo completo de clasificación.
- **Tier / nombres de nivel del Excel**: parseados parcialmente,
  no conectados a la UI (ver sección 1).
- **La marca "remove" (鬥)** del Excel original nunca se resolvió:
  sigue en la lista de radicales sin cambios, por instrucción explícita
  (no se elimina ningún radical del mapeo aunque el Excel lo marcara
  para quitar).

## 8. Trazado a mano y encontrador de símbolos por dibujo

`data/build_strokes.py` extrae, para cada glifo del catálogo, sus
trazos reales en el orden de escritura correcto (3921 de 3926 glifos,
99.9%; los 5 que faltan son formas-variante de radicales sin entrada
propia como carácter completo, ej. 𠂉 y ｜, que ninguna de las dos
fuentes cubre porque no son caracteres escribibles por sí solas).

Dos fuentes en cascada:

- **KanjiVG** (primaria, 2865 glifos): dibuja cada carácter como un
  `<path>` de SVG por trazo (curvas de Bezier cúbicas, comando `C`) en
  el orden real de escritura. `path_to_polyline()` evalúa esa curva a
  mano (sin librerías de SVG) porque las ~80,000 rutas del dataset
  completo usan únicamente los comandos `M` y `C`, verificado
  escaneando el XML completo antes de escribir el parser. Es de origen
  japonés y no cubre bien los simplificados que se alejaron mucho de
  su forma tradicional (ej. 飞, 3 trazos, contra 飛, 9 trazos: formas
  sin relación visual real, fusionarlas habría sido peor que no tener
  dato).
- **makemeahanzi/graphics.txt** (respaldo, 1056 glifos): campo
  `medians`, la línea central de cada trazo ya como lista de puntos
  (no hace falta evaluar curvas). Es un dataset de origen chino, así
  que cubre justo el hueco que deja KanjiVG (permitió encontrar 飞,
  entre muchos otros). Sus coordenadas vienen con el eje Y invertido
  (documentado en su propio README: "the y-axes DECREASES as you move
  downwards"); se corrige con `y_final = 900 - y_fuente` antes de
  normalizar (verificado con las esquinas documentadas del cuadro:
  (0,900) y (1024,-124) en la fuente deben mapear a (0,0) y
  (1024,1024)).
- **Normalización**: cada trazo se re-muestrea a 12 puntos espaciados
  por longitud de arco, y todos los trazos de un mismo glifo se
  escalan/centran juntos en un cuadrado 0-1 compartido (para que la
  posición y tamaño relativo de cada trazo dentro del carácter se
  conserve). El frontend (`utils/strokeMatch.js`,
  `normalizeDrawnStrokes()`) le hace exactamente lo mismo a lo que el
  usuario dibuja en `DrawCanvas.jsx`, para que ambos lados sean
  comparables sin importar el tamaño real del canvas ni la velocidad
  de trazo.
- **Quiz de trazado** (`StudyMode.jsx`, modo "Dibujar"): compara el
  trazo dibujado contra el trazo real, **a propósito sensible al
  orden**: el objetivo es evaluar si el orden de escritura es el
  correcto, no solo si la forma final se parece. `alignStrokes()` en
  `utils/strokeMatch.js` alinea ambas secuencias con una variante de
  distancia de edición (emparejar, insertar o borrar un trazo, nunca
  reordenar) en vez de comparar por índice fijo. Esto arregla un caso
  real: levantar el lápiz a mitad de un trazo lo parte en dos, y con
  índice fijo todo lo que seguía se comparaba contra el trazo real
  equivocado (desde ahí en adelante, incluso trazos bien dibujados
  cruzaban por completo el conteo, y el último trazo real ni siquiera
  llegaba a compararse: el bucle antiguo se detenía en
  `min(dibujados, reales)`). Con la alineación, el trazo de sobra se
  detecta como tal (se pinta en rojo, cuenta como trazo extra) y el
  resto de la secuencia se re-sincroniza sola. Sigue penalizando tener
  más o menos trazos que los reales (`countPenalty`), pero ya no deja
  que ese desfase arruine la comparación de todo lo que sigue.
- **Encontrador de símbolos por dibujo** (`DrawFinder.jsx`): el sentido
  inverso, buscar qué carácter es a partir de un dibujo sin saber su
  nombre. Aquí el orden de trazo y en cuántos trazos se partió el
  dibujo **no** deberían importar (es reconocer una forma, no evaluar
  caligrafía).

  La primera versión sí filtraba candidatos por conteo de trazos (±1)
  y comparaba trazo por trazo. El usuario reportó que la inferencia se
  sentía sesgada hacia caracteres comunes al escribir en cursiva o sin
  el orden correcto: comprobado con datos reales (学, 8 trazos,
  fusionado a mano en 4 "trazos" de cursiva). El propio 学 seguía
  siendo la mejor coincidencia real por forma, pero el filtro de ±1
  trazo lo descartaba de la competencia por completo, dejando ganar
  solo a caracteres de 3-4 trazos sin relación (手, 予, 干...), que
  además tienden a ser los más comunes del catálogo. No era sesgo
  hacia la frecuencia real (`findCandidates` nunca usa ese dato); era
  que solo los caracteres simples podían competir siquiera.

  El arreglo (`findCandidates` en `utils/strokeMatch.js`) trata el
  dibujo como una nube de puntos sin orden ni conectividad entre
  trazos (distancia "Chamfer": cada punto busca su vecino más cercano
  del otro lado, en ambas direcciones), en vez de comparar trazo por
  trazo. Un intento intermedio (concatenar todos los trazos en un solo
  camino y re-muestrear por longitud de arco) tampoco sirvió: el salto
  entre el final de un trazo y el inicio del siguiente se contaba como
  distancia real, así que dos trazos bien dibujados pero separados
  (ej. una cruz simple para 十) se comparaban peor de lo que debían.
  Esto trajo un segundo sesgo, tambien reportado por el usuario: un
  dibujo simple encontraba caracteres muy complejos (10-17 trazos)
  casi empatados con la respuesta simple correcta. La causa es una
  asimetria real de la distancia Chamfer cuando las dos nubes de
  puntos tienen tamaños muy distintos: un carácter de 17 trazos aporta
  ~4 veces más puntos que uno de 4, repartidos por todo el cuadrado
  0-1, así que CUALQUIER dibujo tiene más chance de caer cerca de
  alguno de esos puntos solo por azar, sin que la forma real se
  parezca en nada. Comprobado: una simple línea horizontal encontraba
  一 correctamente pero con caracteres de 13-17 trazos casi empatados
  unos puntos después.

  El arreglo final: en vez de diluir cada nube proporcionalmente a su
  propio tamaño (1 de cada 3 puntos), se limita a ambos lados (dibujo y
  cada candidato) al mismo tope fijo de 24 puntos (`CLOUD_CAP` en
  `utils/strokeMatch.js`): así un carácter complejo ya no aporta más
  "oportunidades" de coincidir por pura densidad de puntos. De paso
  resuelve el costo de comparar ~2865 candidatos (una búsqueda completa
  corre en ~200ms).

## 9. Dominios semánticos: clasificación directa, no clustering

Las categorías originales (Humano, Cuerpo, Naturaleza, Comida,
Animales, Objetos, Vida, Estructural...) venían de una matriz que el
usuario llenó a mano en `Pictograms.xlsx`, y solo cubrían 131 de 242
radicales: era una clasificación subjetiva de una versión temprana del
proyecto, nunca completada, y los caracteres compuestos no tenían
categoría en absoluto (todos los nodos compuestos se pintaban del
mismo gris en el lienzo).

### 9.1 Por qué no terminamos usando clustering

El primer intento fue detección de comunidades sobre el grafo real
(Louvain, `networkx.community.louvain_communities`), probado en dos
variantes: comunidades sobre los 242 radicales directamente, y sobre
una proyección ponderada (Newman) del grafo bipartito
radical-carácter, agrupando así los ~3700 caracteres compuestos por
similitud de qué radicales comparten. Se revisaron los resultados en
un documento publicado con los 52-53 clusters encontrados.

El usuario rechazó el resultado explícitamente tras revisarlo: los
clusters salían de tamaño muy desigual (algunos con un solo carácter,
otros enormes), varias agrupaciones no eran intuitivas para alguien
estudiando el idioma (mezclaba dominios que no tienen relación de
significado real, solo coincidencia estructural en el grafo), y de
todos modos habría necesitado ajuste manual para los casos borde. La
conclusión fue que un clustering automático optimiza por estructura
del grafo (qué tan conectados están los nodos entre sí), no por
significado real, que es lo que de verdad importa para organizar el
aprendizaje. Louvain no se descartó por un error de implementación:
se descartó porque optimiza la pregunta equivocada para este caso de
uso.

### 9.2 El mecanismo adoptado: clasificar radicales, heredar caracteres

En vez de inferir dominios de la estructura del grafo, se clasifican
los 242 radicales directamente por su significado real en inglés
(`RADICAL_MEANING`), a mano, uno por uno, en 9 dominios fijos:
Personas, Cuerpo, Lugares, Naturaleza, Comida, Animales, Objetos,
Acciones, Abstracto (`DOMAIN_MAP` en `build_dataset.py`, y
`CATEGORY_INFO` en `frontend/src/graph/constants.js` para las
etiquetas en español y el color de cada uno). Esta clasificación se
revisó primero a nivel de conteo de radicales por dominio, y después a
nivel de conteo de CARACTERES por dominio (no solo radicales), porque
un dominio con pocos radicales pero que son componentes muy usados
(ej. 水, agua) puede terminar representando a cientos de caracteres:
la distribución final por caracteres fue Naturaleza 868, Cuerpo 778,
Objetos 595, Personas 431, Lugares 261, Abstracto 240, Comida 149,
Animales 148, Acciones 138.

Cada carácter compuesto hereda su dominio del radical que
**dictionary-wise** lo indexa, no del primer componente que aparezca
en su descomposición: `resolve_anchor_radical()` usa primero el campo
`radical` que el propio makemeahanzi trae por carácter (el radical
tradicional de diccionario, el mismo criterio que usaría un diccionario
de papel), resuelto a su forma canónica vía `MERGE_INTO` cuando
corresponde. Solo si ese campo no existe o no resuelve a uno de los
242 radicales reales, cae de regreso al primer componente real con rol
`sem` en la descomposición (`components_of()`, sección 3). Ejemplo
verificado: 河 (río) se compone de 水 (semántico, "agua") y 可
(fonético, "poder"); el radical de diccionario es 水, así que 河
hereda Naturaleza de 水, no de 可.

`MERGE_INTO` se extendió con 11 pares adicionales específicamente
porque el campo `radical` de makemeahanzi a veces usa la forma
simplificada donde el catálogo de 242 radicales solo tiene la
tradicional (o viceversa): `马→馬, 车→車, 见→見, 贝→貝, 龙→竜, 耂→⺹,
⺗→心, 攴→攵, 肀→聿, 玉→王, ⺊→卜`. Sin estos, esos caracteres se habrían
quedado sin dominio aunque su radical real sí esté clasificado, solo
que bajo el otro codepoint.

El residuo final de **20 caracteres (0.5%)** sin dominio resoluble son
casos donde ni el campo `radical` de makemeahanzi resuelve a uno de los
242 canónicos ni hay ningún componente real con rol semántico
registrado en ninguna fuente (ej. 刁, 勲, 区, 匿, 呉): se dejan sin
`category` (`null`) en vez de forzar una categoría arbitraria; la UI
(`DetailPanel.jsx`, `StudyMode.jsx`) simplemente no muestra el badge de
dominio cuando `category` es `null`, sin caerse ni mostrar un valor
inventado. La mayoría son formas kyūjitai japonesas (勲営壱巻帯暦気発舎
舗霊黙) que ni siquiera tienen entrada en makemeahanzi (fuente china), o
radicales genuinamente ausentes de los 242 (匸, 己, 民, 旡, 巳).

Este residuo bajó de ~70 (1.9%) a 20 en una segunda pasada: revisando
uno por uno por qué fallaban, la mayoría (50 de 70) resultó ser el
mismo caso ya conocido (campo `radical` apuntando a la forma
simplificada cuando el catálogo de 242 solo tiene la tradicional o la
shinjitai japonesa), así que se resolvió extendiendo `MERGE_INTO` con
10 pares más: `门→門, 页→頁, 风→風, 鱼→魚, 鸟→鳥, 氺→水, 㔾→卩, 齿→歯,
龟→亀, 飞→飛`. 飞/飛 es el mismo caso que 齐/齊 (sección 2): misma
identidad léxica aunque las formas no se parezcan nada visualmente (por
eso el trazo de 飞 sigue viniendo de makemeahanzi y no de KanjiVG, ver
sección 8; para dominio semántico lo que importa es que es el mismo
carácter, no el trazo).

**Bug real encontrado al hacer esta extensión** (no exclusivo de los 10
pares nuevos: ya afectaba a los 6 pares anteriores de la sección 2,
`马/馬, 车/車, 见/見, 贝/貝, 龙/竜, 齐/齊`): cuando un carácter se funde en
un nodo radical vía `MERGE_INTO` (`build()`, bloque "el carácter ES uno
de nuestros 243 radicales"), los campos `jlpt`/`hsk`/`freqJa`/`freqZh`
se sobreescribían sin condición. Si el mismo nodo recibía una pasada
japonesa y otra china (el orden depende del codepoint, no está
garantizado), la segunda pasada podía borrar con `None` lo que la
primera ya había puesto. Confirmado con 馬: antes de este arreglo se
quedaba con `jlpt=None` a pesar de ser N3, porque la pasada de 马
(sin datos de jouyou) se procesaba después y pisaba el campo. Arreglado
usando guardas (`if jlpt:`, `if zh_level is not None:`, etc.) en vez de
asignación directa. De paso, estos merges tampoco guardaban la forma
alterna en `variants`, así que buscar "马" en la app no encontraba nada
(la búsqueda en `TopBar.jsx` no incluía `variants` en el texto
comparado): ambos arreglos hicieron falta juntos para que 马, 车, 见,
贝, 龙, 齐 y los 10 pares nuevos queden completos y encontrables por
cualquiera de sus dos formas.

### 9.3 El toggle "Sin categoría" y por qué hacía falta

En el lienzo (`RadicalGraph.jsx`), apagar un dominio en la leyenda no
solo opaca sus nodos: los quita del todo salvo que sean un puente
directo hacia algún nodo que sigue visible con normalidad
(`dropUnnecessaryDimmed()`). El residuo sin dominio (sección 9.2) y los
~319 componentes "extra" (fonéticos fuera de la lista de 242 radicales)
no traen ningún `category` en absoluto, así que al principio quedaban
fuera de este mecanismo por completo: `isCategoryDimmed()` los daba
siempre por "no apagados" sin importar qué dominios estuvieran activos.
El efecto reportado por el usuario fue justo ese: radicales de un
dominio apagado seguían apareciendo, "pegados" a alguno de estos ~389
nodos sin relación real con el dominio que sí quería ver, y con los 9
dominios apagados a la vez el grafo nunca llegaba a vaciarse del todo.

El arreglo trata a estos ~389 nodos como un dominio virtual más
(`OTHER_CATEGORY_KEY` en `constants.js`, con su propia entrada en
`CATEGORY_INFO` y su chip "Sin categoría" en la leyenda,
`--cat-other` en `theme/tokens.css`): `categoryKeyOf(n)` resuelve
`n.category || OTHER_CATEGORY_KEY`, y tanto el apagado por opacidad
como el filtro de "puente necesario" usan esa clave de forma uniforme,
sin ningún caso especial. Apagar "Sin categoría" ahora los oculta igual
que cualquier otro dominio (salvo que sean puente real), y apagar los
10 dominios a la vez vacía el lienzo por completo.
