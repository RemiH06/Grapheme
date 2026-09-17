# -*- coding: utf-8 -*-
"""
Genera backend/app/data/strokes.json: para cada glifo del catalogo
(radicales + caracteres jouyou/HSK), la lista de sus trazos en el
orden real de escritura, cada uno como una polilinea de N puntos
normalizados a un cuadrado 0-1 compartido por todo el glifo (mismo
sistema de referencia que usa el lienzo de dibujo del frontend, ver
frontend/src/utils/strokeMatch.js).

Dos fuentes en cascada:
  1. KanjiVG (primaria): usa solo dos comandos de trazo SVG en todo el
     dataset, M (mover pluma) y C (curva de Bezier cubica) -- verificado
     escaneando las ~80,000 rutas del XML. Sin arcos, lineas ni curvas
     "smooth", asi que el parser de rutas de abajo cubre el 100% de los
     casos reales. Es de origen japones y no cubre bien los caracteres
     simplificados que se alejaron mucho de su forma tradicional (ej.
     飞 vs 飛: 3 trazos contra 9, formas sin relacion visual real).
  2. makemeahanzi/graphics.txt (respaldo): campo "medians", la linea
     central de cada trazo ya como lista de puntos (no hace falta
     evaluar curvas), en el orden real de escritura. Es un dataset de
     origen chino, asi que cubre justo el hueco que deja KanjiVG.
     Sus coordenadas vienen con el eje Y invertido (documentado en su
     propio README: "the y-axes DECREASES as you move downwards"), se
     corrige con `y_final = 900 - y_fuente` antes de normalizar.

Uso:
    cd data
    python build_dataset.py   # primero, genera graph_data.json
    python build_strokes.py
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT / "data" / "sources"
GRAPH_PATH = ROOT / "backend" / "app" / "data" / "graph_data.json"
OUT_PATH = ROOT / "backend" / "app" / "data" / "strokes.json"

KANJIVG_NS = '{http://kanjivg.tagaini.net}'
POINTS_PER_STROKE = 12
SAMPLES_PER_SEGMENT = 24  # densidad de la polilinea intermedia antes de re-muestrear por longitud de arco

NUM_RE = re.compile(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')


def _tokenize(d):
    """'M1,2c3,4 5,6 7,8' -> [('M', False, [1,2]), ('c', True, [3,4,5,6,7,8])]"""
    tokens = []
    i = 0
    n = len(d)
    while i < n:
        ch = d[i]
        if ch.isalpha():
            cmd = ch
            i += 1
            nums = []
            while i < n:
                m = NUM_RE.match(d, i)
                if not m:
                    # separador (espacio o coma) entre numeros
                    if d[i] in ' ,\t\n':
                        i += 1
                        continue
                    break
                nums.append(float(m.group()))
                i = m.end()
            tokens.append((cmd.upper(), cmd.islower(), nums))
        else:
            i += 1
    return tokens


def _cubic_point(p0, p1, p2, p3, t):
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
    y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)


def path_to_polyline(d):
    """Ruta SVG (solo M/C, absolutos o relativos) -> lista densa de puntos (x,y)."""
    tokens = _tokenize(d)
    cur = (0.0, 0.0)
    poly = []
    for cmd, relative, nums in tokens:
        if cmd == 'M':
            x, y = nums[0], nums[1]
            cur = (cur[0] + x, cur[1] + y) if relative else (x, y)
            poly.append(cur)
            # M seguido de mas pares de numeros se trata como L implicito;
            # KanjiVG no lo usa, pero no cuesta nada cubrirlo
            extra = nums[2:]
            for j in range(0, len(extra) - 1, 2):
                x, y = extra[j], extra[j + 1]
                cur = (cur[0] + x, cur[1] + y) if relative else (x, y)
                poly.append(cur)
        elif cmd == 'C':
            for j in range(0, len(nums) - 5, 6):
                x1, y1, x2, y2, x, y = nums[j:j + 6]
                if relative:
                    p1 = (cur[0] + x1, cur[1] + y1)
                    p2 = (cur[0] + x2, cur[1] + y2)
                    p3 = (cur[0] + x, cur[1] + y)
                else:
                    p1, p2, p3 = (x1, y1), (x2, y2), (x, y)
                for s in range(1, SAMPLES_PER_SEGMENT + 1):
                    t = s / SAMPLES_PER_SEGMENT
                    poly.append(_cubic_point(cur, p1, p2, p3, t))
                cur = p3
    return poly


def resample_by_arclength(poly, n):
    if len(poly) == 1:
        return [poly[0]] * n
    seg_lens = []
    total = 0.0
    for i in range(1, len(poly)):
        dx = poly[i][0] - poly[i - 1][0]
        dy = poly[i][1] - poly[i - 1][1]
        d = (dx * dx + dy * dy) ** 0.5
        seg_lens.append(d)
        total += d
    if total == 0:
        return [poly[0]] * n
    out = []
    target_step = total / (n - 1)
    acc = 0.0
    seg_i = 0
    seg_acc = 0.0
    out.append(poly[0])
    for k in range(1, n - 1):
        target = k * target_step
        while seg_i < len(seg_lens) and acc + seg_lens[seg_i] < target:
            acc += seg_lens[seg_i]
            seg_acc = acc
            seg_i += 1
        if seg_i >= len(seg_lens):
            out.append(poly[-1])
            continue
        remain = target - seg_acc
        frac = remain / seg_lens[seg_i] if seg_lens[seg_i] > 0 else 0
        p0, p1 = poly[seg_i], poly[seg_i + 1]
        out.append((p0[0] + (p1[0] - p0[0]) * frac, p0[1] + (p1[1] - p0[1]) * frac))
    out.append(poly[-1])
    return out


def collect_strokes(root_g):
    """Todos los <path> del subarbol, en orden de documento = orden de trazo."""
    ds = []
    for el in root_g.iter():
        tag = el.tag.split('}')[-1]
        if tag == 'path':
            d = el.get('d')
            if d:
                ds.append(d)
    return ds


def normalize_polylines(polylines):
    all_points = [p for poly in polylines for p in poly]
    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span = max(max_x - min_x, max_y - min_y) or 1.0
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2

    def norm(p):
        return ((p[0] - cx) / span + 0.5, (p[1] - cy) / span + 0.5)

    result = []
    for poly in polylines:
        resampled = resample_by_arclength(poly, POINTS_PER_STROKE)
        # 4 decimales (~0.0001 en un espacio 0-1) sobra de precision para
        # comparar trazos dibujados a mano y reduce el JSON final a una
        # fraccion de su tamano sin perder nada perceptible.
        result.append([[round(x, 4), round(y, 4)] for x, y in map(norm, resampled)])
    return result


def load_kanjivg_all_strokes():
    tree = ET.parse(SOURCES_DIR / 'kanjivg.xml')
    by_glyph = {}
    for kanji_el in tree.getroot():
        root_g = kanji_el.find('g')
        if root_g is None:
            continue
        glyph = root_g.get(KANJIVG_NS + 'element')
        if not glyph or glyph in by_glyph:
            continue
        ds = collect_strokes(root_g)
        if ds:
            by_glyph[glyph] = ds
    return by_glyph


def load_mmh_graphics_medians():
    """glifo -> [[(x,y),...] por trazo], ya con el eje Y corregido."""
    by_glyph = {}
    path = SOURCES_DIR / 'makemeahanzi_graphics.txt'
    if not path.exists():
        return by_glyph
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            medians = rec.get('medians')
            glyph = rec.get('character')
            if not glyph or not medians:
                continue
            by_glyph[glyph] = [[(x, 900 - y) for x, y in stroke] for stroke in medians]
    return by_glyph


def main():
    graph = json.loads(GRAPH_PATH.read_text(encoding='utf-8'))
    catalog_glyphs = {n['glyph'] for n in graph['radicals']} | {n['glyph'] for n in graph['characters']}
    kvg_strokes = load_kanjivg_all_strokes()
    mmh_medians = load_mmh_graphics_medians()

    out = {}
    from_kvg = from_mmh = 0
    for glyph in catalog_glyphs:
        raw_ds = kvg_strokes.get(glyph)
        if raw_ds:
            out[glyph] = normalize_polylines([path_to_polyline(d) for d in raw_ds])
            from_kvg += 1
            continue
        medians = mmh_medians.get(glyph)
        if medians:
            out[glyph] = normalize_polylines(medians)
            from_mmh += 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f"glifos con trazos: {len(out)} / {len(catalog_glyphs)} en catalogo "
          f"(KanjiVG={from_kvg}, makemeahanzi={from_mmh}) -> {OUT_PATH}")


if __name__ == '__main__':
    main()
