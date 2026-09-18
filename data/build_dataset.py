# -*- coding: utf-8 -*-
"""
Genera backend/app/data/graph_data.json: 243 radicales (Pictograms.xlsx)
mas el catalogo COMPLETO de kanji joyo + hanzi HSK 3.0, cada uno
conectado a sus radicales/componentes.

Fuentes (ver data/fetch_sources.py para las URLs y licencias):
  - kanji-jouyou.json: los 2136 kanji joyo con JLPT, frecuencia real
    (corpus de periodico) y lecturas.
  - mega_hanzi_compilation.csv: hanzi con nivel HSK 3.0, frecuencia
    real (Jun Da, corpus moderno de ~200M caracteres) y descomposicion.
  - makemeahanzi/dictionary.txt: descomposicion posicional (IDS) +
    etimologia semantica/fonetica, fuente PRINCIPAL de componentes.
  - mega_hanzi (columna decomposition2_with_radical): respaldo 1,
    lista plana sin posicion, para lo que makemeahanzi no cubra.
  - kanjivg.xml: respaldo 2, especifico de Japon (posicion real +
    pista fonetica), para las formas shinjitai que ninguna fuente de
    origen chino cubre (図, 対, 悪, 様...).

Uso:
    cd data
    python fetch_sources.py   # una sola vez, cachea los 4 archivos
    python build_dataset.py

Vuelve a correr build_dataset.py cada vez que se edite este archivo o
el Excel. No hace falta volver a tocar fetch_sources.py salvo que
quieras refrescar los datasets (borra data/sources/ y vuelve a correrlo).
"""
import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
EXCEL_PATH = ROOT / "docs" / "Pictograms.xlsx"
SOURCES_DIR = ROOT / "data" / "sources"
OUT_PATH = ROOT / "backend" / "app" / "data" / "graph_data.json"

CATS = ['Primitive', 'Components', 'Human', 'Body', 'Matter', 'Places',
        'Nature', 'Food', 'Animals', 'Objects', 'Life']


def split_variants(cell):
    if not cell:
        return []
    return [c.strip() for c in str(cell).split(',') if c.strip()]


def parse_excel(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb['Kanji']

    # matriz semantica (filas 5-22, columnas C..M = categorias 0..10)
    category_of, tier_of = {}, {}
    for r in range(5, 23):
        tier_val = ws.cell(row=r, column=2).value
        tier = int(tier_val) if tier_val is not None else None
        for ci, cat in enumerate(CATS):
            cell = ws.cell(row=r, column=3 + ci).value
            for g in split_variants(cell):
                category_of[g] = cat
                if tier is not None:
                    tier_of[g] = tier

    def parse_approach(ws, has_dual_reading):
        entries = []
        current_type = current_class = None
        r = 32
        while r <= ws.max_row + 1 and r <= 32 + 320:
            b = ws.cell(row=r, column=2).value
            c = ws.cell(row=r, column=3).value
            if b is None and c is None:
                r += 1
                continue
            is_subheader = isinstance(c, (int, float))
            if is_subheader:
                current_class, current_type = b, c
            else:
                glyph = c
                if glyph:
                    entry = {'n': b, 'glyph': glyph, 'strokeType': current_type}
                    d = ws.cell(row=r, column=4).value
                    e = ws.cell(row=r, column=5).value
                    f = ws.cell(row=r, column=6).value
                    g = ws.cell(row=r, column=7).value
                    h = ws.cell(row=r, column=8).value
                    if has_dual_reading:
                        entry.update(onyomi=d, kunyomi=e, meaningRadical=f,
                                     meaningKanji=g, mnemonic=h)
                    else:
                        entry.update(sound=d, meaning=e, mnemonic=f)
                    entries.append(entry)
            r += 1
        return entries

    kanji_entries = parse_approach(wb['Kanji'], True)
    hanzi_entries = parse_approach(wb['Hanzi'], False)

    by_glyph, order = {}, []
    for e in kanji_entries:
        g = e['glyph']
        if g not in by_glyph:
            by_glyph[g] = {'glyph': g}
            order.append(g)
        rec = by_glyph[g]
        rec['strokeCount'] = e['strokeType']
        rec['onyomi'] = e.get('onyomi')
        rec['kunyomi'] = e.get('kunyomi')
        rec['meaningRadical'] = e.get('meaningRadical')
        rec['n'] = e.get('n')
    for e in hanzi_entries:
        g = e['glyph']
        if g not in by_glyph:
            by_glyph[g] = {'glyph': g}
            order.append(g)
        rec = by_glyph[g]
        rec.setdefault('strokeCount', e['strokeType'])
        if e.get('sound'):
            rec['pinyin'] = e['sound']

    for g in order:
        rec = by_glyph[g]
        if g in category_of:
            rec['category'] = category_of[g]
            rec['tier'] = tier_of.get(g)
    return [by_glyph[g] for g in order]


radicals_raw = parse_excel(EXCEL_PATH)

# ---------------------------------------------------------------------------
# Significados en ingles para los 253 radicales (glosa breve, uso en
# diccionarios kanji/hanzi estandar). Se usa solo si el Excel no trae ya
# "meaningRadical" cargado (hoy solo esta lleno para el radical #1).
# ---------------------------------------------------------------------------
RADICAL_MEANING = {
    '一': 'one', '｜': 'line, stick', '丶': 'dot', 'ノ': 'slash, sweep',
    '乙': 'second, twist', '亅': 'hook',
    '二': 'two', '亠': 'lid', '人': 'person', '⺅': 'person (side form)',
    '𠆢': 'person (top form)', '儿': 'legs, son', '入': 'enter', 'ハ': 'eight, divide',
    '丷': 'divide (variant)', '冂': 'wide, borders', '冖': 'cloth cover',
    '冫': 'ice', '几': 'small table, stool', '凵': 'open container',
    '刀': 'knife, sword', '⺉': 'knife (side form)', '力': 'power, strength',
    '勹': 'wrap', '匕': 'spoon, ladle', '匚': 'box, container',
    '十': 'ten', '卜': 'divination', '卩': 'seal, kneeling figure',
    '厂': 'cliff', '厶': 'private, self', '又': 'again, right hand',
    'マ': 'curl shape (mnemonic)', '九': 'nine', 'ユ': 'hook shape (mnemonic)',
    '乃': 'thus, namely', '𠂉': 'slanted stroke (shape variant)',
    '⻌': 'movement, road', '口': 'mouth', '囗': 'enclosure, border',
    '土': 'earth, soil', '士': 'samurai, scholar', '夂': 'go slowly, follow',
    '夕': 'evening', '大': 'big', '女': 'woman', '子': 'child',
    '宀': 'roof', '寸': 'inch, hand rule', '小': 'small',
    '⺌': 'small (variant)', '尢': 'lame leg, weak', '尸': 'corpse, dwelling',
    '屮': 'sprout', '山': 'mountain', '川': 'river', '巛': 'river (variant)',
    '工': 'work, craft', '已': 'already, stop', '巾': 'cloth, towel',
    '干': 'dry, shield, stem', '幺': 'tiny, thread', '广': 'shelter',
    '廴': 'long stride', '廾': 'two hands, clasped', '弋': 'dart, arrow with cord',
    '弓': 'bow', 'ヨ': "snout, pig's head (variant)", '彑': "snout, pig's head",
    '彡': 'hair, bristles', '彳': 'step, going', '⺖': 'heart (side form)',
    '⺘': 'hand (side form)', '⺡': 'water (side form)', '⺨': 'dog/beast (side form)',
    '⺾': 'grass (top form)', '⻏': 'city, village (right form)',
    '⻖': 'mound, hill (left form)', '也': 'also (particle)', '亡': 'death, flee, lose',
    '及': 'reach, extend to', '久': 'long time, endure', '⺹': 'old, aged (variant)',
    '心': 'heart, mind', '戈': 'spear, halberd', '戸': 'door',
    '手': 'hand', '支': 'branch, support', '攵': 'tap, strike',
    '文': 'writing, culture', '斗': 'dipper, measure', '斤': 'axe, unit of weight',
    '方': 'direction, square', '无': 'without, nothingness', '日': 'sun, day',
    '曰': 'say, speak', '月': 'moon, month (also flesh/body as 肉)', '木': 'tree, wood',
    '欠': 'lack, yawn', '止': 'stop, halt', '歹': 'death, decay',
    '殳': 'weapon, to strike', '比': 'compare', '毛': 'hair, fur',
    '氏': 'clan, family name', '气': 'steam, vapor', '水': 'water',
    '火': 'fire', '⺣': 'fire (bottom form, four dots)', '爪': 'claw, nail',
    '父': 'father', '爻': 'trigram lines, intersect', '爿': 'split wood, bed',
    '片': 'slice, fragment', '牛': 'cow, ox', '犬': 'dog',
    '⺭': 'spirit, altar (side form)', '王': 'king, jewel', '元': 'origin, beginning',
    '井': 'well', '勿': 'do not, must not', '尤': 'especially, more',
    '五': 'five', '屯': 'collect, sprout', '巴': 'python, cling',
    '毋': 'do not (prohibition)', '玄': 'mysterious, profound', '瓦': 'tile, earthenware',
    '甘': 'sweet', '生': 'life, birth, grow', '用': 'use',
    '田': 'rice field', '疋': 'bolt of cloth, leg', '疒': 'sickness',
    '癶': 'footsteps, walk', '白': 'white', '皮': 'skin, hide',
    '皿': 'dish, plate', '目': 'eye', '矛': 'spear, lance',
    '矢': 'arrow', '石': 'stone', '示': 'altar, spirit, show',
    '禸': 'animal track', '禾': 'grain, rice plant', '穴': 'cave, hole',
    '立': 'stand', '⻂': 'clothes (top form)', '世': 'world, generation',
    '巨': 'huge, giant', '冊': 'volume, bound bamboo strips', '母': 'mother',
    '⺲': 'net (variant)', '牙': 'fang, tusk', '瓜': 'melon, gourd',
    '竹': 'bamboo', '米': 'rice', '糸': 'thread', '缶': 'jar, earthen vessel',
    '羊': 'sheep', '羽': 'feather, wing', '而': 'and yet (orig. beard)',
    '耒': 'plow', '耳': 'ear', '聿': 'writing brush', '肉': 'meat, flesh',
    '自': 'self, from', '至': 'arrive, reach', '臼': 'mortar',
    '舌': 'tongue', '舟': 'boat', '艮': 'stop, stubborn',
    '色': 'color', '虍': 'tiger stripes', '虫': 'insect, bug',
    '血': 'blood', '行': 'go, road, conduct', '衣': 'clothes',
    '西': 'west', '臣': 'vassal, retainer', '見': 'see',
    '角': 'horn, angle', '言': 'words, speech', '谷': 'valley',
    '豆': 'bean (also ancient vessel)', '豕': 'pig, boar', '豸': 'badger, legless creature',
    '貝': 'shell, money, treasure', '赤': 'red', '走': 'run',
    '足': 'foot, leg', '身': 'body', '車': 'vehicle, cart',
    '辛': 'bitter, hardship', '辰': 'time, dragon (zodiac)', '酉': 'wine jar, alcohol',
    '釆': 'distinguish, discern', '里': 'village, distance unit', '舛': 'oppose, dance steps',
    '麦': 'wheat, barley', '金': 'gold, metal', '長': 'long, chief',
    '門': 'gate, door', '隶': 'servant, capture', '隹': 'short-tailed bird',
    '雨': 'rain', '青': 'blue, green', '非': 'wrong, negate',
    '奄': 'cover, sudden', '岡': 'ridge, hill', '免': 'avoid, escape',
    '斉': 'align, uniform', '面': 'face, surface', '革': 'leather, reform',
    '韭': 'leek, chives', '音': 'sound', '頁': 'page, head',
    '風': 'wind', '飛': 'fly', '食': 'eat, food',
    '首': 'head, neck', '香': 'fragrance', '品': 'goods, article',
    '馬': 'horse', '骨': 'bone', '高': 'tall, high',
    '髟': 'long hair', '鬥': 'fight, combat', '鬯': 'sacrificial wine',
    '鬲': 'tripod cauldron', '鬼': 'ghost, demon', '竜': 'dragon',
    '韋': 'tanned leather, defy', '魚': 'fish', '鳥': 'bird',
    '鹵': 'salt marsh, brine', '鹿': 'deer', '麻': 'hemp, numbness',
    '亀': 'turtle', '啇': 'root (phonetic in 敵/適/摘)', '黄': 'yellow',
    '黒': 'black', '黍': 'millet', '黹': 'embroidery, needlework',
    '無': 'nothing, without', '歯': 'tooth', '黽': 'frog, toad, hardworking',
    '鼎': 'tripod cauldron, ancient vessel', '鼓': 'drum', '鼠': 'mouse, rat',
    '鼻': 'nose', '齊': 'align, uniform', '龠': 'flute, pipes',
}

# Formas-variante que en realidad son la misma idea que otro radical de la
# lista, solo que escritas en otra posicion dentro del caracter. Se fusionan
# en un solo nodo canonico; la forma corta queda como "variante" del nodo.
MERGE_INTO = {
    '⺅': '人', '𠆢': '人', '⺨': '犬', '⺡': '水', '⺣': '火',
    '⺖': '心', '⺘': '手', '⺭': '示', '⻂': '衣', '⺌': '小',
    # Las mismas formas de arriba, pero con el codepoint Unicode que de
    # verdad usan los datasets de descomposicion (bloque CJK Unified
    # Ideographs / simplificado chino) en vez del bloque "CJK Radicals
    # Supplement" que trae el Excel. Visualmente identicas, puntos de
    # codigo distintos -- sin esto, 手/水/人/etc. quedaban "huerfanos"
    # aunque en realidad si aparecen en cientos de compuestos.
    '扌': '手', '氵': '水', '亻': '人', '忄': '心', '犭': '犬',
    '礻': '示', '衤': '衣', '钅': '金', '釒': '金',
    '艹': '⺾', '⺮': '竹', '罒': '⺲', '灬': '火',
    '辶': '⻌', '⺼': '肉', '爫': '爪',
    '丨': '｜', '丿': 'ノ', '乚': '乙', '彐': '彑',
    '丬': '爿',
    # Radicales simplificados en chino continental (distintos del
    # tradicional que trae el Excel, pero la misma idea).
    '讠': '言', '纟': '糸', '糹': '糸', '刂': '刀', '饣': '食', '飠': '食',
    '韦': '韋',
    # Omitidos en la primera pasada de fusiones (sesion anterior):
    # ⺉ nunca se fusiono con 刀 como si paso con los demas "side forms".
    '⺉': '刀',
    # 戸 (puerta, forma japonesa, U+6238) vs 戶 tradicional (U+6236) y
    # 户 simplificado (U+6237): mismo radical, tres codepoints distintos.
    '户': '戸', '戶': '戸',
    # 八 (el caracter real "ocho") vs ハ (la forma-trazo que trae el
    # Excel): los datasets de descomposicion casi siempre usan 八.
    '八': 'ハ',
    # 老 (viejo, caracter completo) vs ⺹ (forma recortada de "corona"
    # que trae el Excel).
    '老': '⺹',
    # Encontrados al integrar KanjiVG (mismos "dos codepoints" del punto 2):
    # 覀 forma recortada de 襾/西 cuando corona un caracter (ej. 価).
    '覀': '西',
    # ⺍ variante de "pequeno" que usa KanjiVG, distinta de la ⺌ del Excel.
    '⺍': '小',
    # 齐 (simplificado, HSK real) vs 齊 (tradicional, radical del Excel):
    # mismo caracter, mismo caso que 讲/言 o 户/戶 de arriba. Sin esto, 齊
    # quedaba aislado del grafo aunque 济/剂/挤 (HSK) sí lo usan como
    # fonetico -- solo que codificado como 齐, no como 齊.
    '齐': '齊',
    # Encontrados al resolver el radical de indexacion real (el campo
    # "radical" que trae makemeahanzi por caracter, usado para asignarle
    # un dominio semantico a cada compuesto): mas variantes simplificadas
    # o formas recortadas que nunca hicieron falta para la descomposicion
    # en si, pero que makemeahanzi si usa como radical de un caracter.
    '马': '馬', '车': '車', '见': '見', '贝': '貝', '龙': '竜',
    '耂': '⺹', '⺗': '心', '攴': '攵', '肀': '聿', '玉': '王', '⺊': '卜',
    # Segunda tanda, encontrados al revisar por que ~70 caracteres se
    # quedaban sin dominio (ver docs/METODOLOGIA.md seccion 9.2): mismo
    # mecanismo, simplificado/variante -> canonico del catalogo de 242.
    # 齿/龟 no resuelven a su propia forma tradicional (齒/龜, que no
    # estan en el catalogo) sino a la forma japonesa shinjitai que si lo
    # esta (歯/亀, ya usada por otros 19 radicales "core"). 飞/飛 son el
    # mismo caso que 齐/齊: identidad lexica igual aunque la forma visual
    # no se parezca en nada (por eso el trazo de 飞 sigue viniendo de
    # makemeahanzi, no de kanjivg -- ver seccion 8 -- pero para dominio
    # semantico lo que importa es que es el mismo caracter).
    '门': '門', '页': '頁', '风': '風', '鱼': '魚', '鸟': '鳥',
    '氺': '水', '㔾': '卩', '齿': '歯', '龟': '亀', '飞': '飛',
    # Tercera tanda, encontrados al agregar resolucion recursiva de
    # ancla (resolve_anchor_radical con MAX_ANCHOR_DEPTH): mismo caso de
    # siempre, radical de indexacion en su forma tradicional/simplificada
    # que no esta en el catalogo de 242 en vez de la shinjitai que si.
    '黑': '黒', '卤': '鹵',
}

# El radical de "oreja" (阝) es ambiguo sin ver la posicion: a la
# izquierda es 阜 (colina, ⻖ en el Excel), a la derecha es 邑 (ciudad,
# ⻏). Se resuelve aparte en components_of(), no aqui.
EAR_LEFT, EAR_RIGHT = '⻖', '⻏'

# Base de una taxonomia de trazos: los radicales de 1 solo trazo son,
# literalmente, los trazos fundamentales del sistema (bloque Unicode
# "CJK Strokes" + las 8 categorias clasicas del "yong zi ba fa" 永字八法).
# strokeType = categoria principal; strokeTypeName = nombre chino/pinyin.
# Los radicales de 2+ trazos (十, 又, 工...) no se etiquetan aqui todavia:
# requieren datos reales de ORDEN de trazo (ej. KanjiVG) para no adivinar.
STROKE_TYPES = {
    '一': ('heng', '横 (héng): horizontal'),
    '｜': ('shu', '竖 (shù): vertical'),
    '丶': ('dian', '点 (diǎn): punto'),
    'ノ': ('pie', '撇 (piě): caída a la izquierda'),
    '乙': ('zhe', '折 (zhé): trazo quebrado/curvo'),
    '亅': ('gou', '钩 (gōu): gancho'),
}

# ---------------------------------------------------------------------------
# Descomposicion de caracteres compuestos via Ideographic Description
# Sequences (⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻, bloque Unicode 2FF0-2FFB).
# ---------------------------------------------------------------------------
IDS_POS = {
    '⿰': ('left', 'right'), '⿱': ('top', 'bottom'),
    '⿲': ('left', 'center', 'right'), '⿳': ('top', 'center', 'bottom'),
    '⿴': ('enclosure', 'inside'), '⿵': ('enclosure', 'inside'),
    '⿶': ('enclosure', 'inside'), '⿷': ('enclosure', 'inside'),
    '⿸': ('enclosure', 'inside'), '⿹': ('enclosure', 'inside'),
    '⿺': ('enclosure', 'inside'), '⿻': ('whole', 'whole'),
}


def _parse_ids(s, i):
    ch = s[i]
    if ch in IDS_POS:
        children, j = [], i + 1
        for _ in IDS_POS[ch]:
            node, j = _parse_ids(s, j)
            children.append(node)
        return {'op': ch, 'children': children}, j
    return {'leaf': ch}, i + 1


def decompose_ids(ids_string):
    """'⿰日月' -> [('日','left'), ('月','right')]. Ignora placeholders '?'."""
    if not ids_string:
        return []
    try:
        tree, _ = _parse_ids(ids_string, 0)
    except IndexError:
        return []
    out = []

    def walk(node, prefix):
        if 'leaf' in node:
            if node['leaf'] not in ('？', '?'):
                out.append((node['leaf'], prefix or 'whole'))
            return
        for child, pos in zip(node['children'], IDS_POS[node['op']]):
            walk(child, f"{prefix}-{pos}" if prefix else pos)

    walk(tree, '')
    return out


def load_jouyou():
    with open(SOURCES_DIR / "kanji-jouyou.json", encoding="utf-8") as f:
        return json.load(f)


def load_mega_hanzi():
    """dict: caracter simplificado -> fila del csv (se queda con la fila
    que tenga nivel HSK si hay glifos duplicados)."""
    by_glyph = {}
    with open(SOURCES_DIR / "mega_hanzi_compilation.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            g = (row.get('simplified') or '').strip()
            if not g:
                continue
            if g not in by_glyph or (row.get('hsk30_level') and not by_glyph[g].get('hsk30_level')):
                by_glyph[g] = row
    return by_glyph


def load_mmh_dictionary():
    by_glyph = {}
    with open(SOURCES_DIR / "makemeahanzi_dictionary.txt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            by_glyph[d['character']] = d
    return by_glyph


KANJIVG_NS = '{http://kanjivg.tagaini.net}'
# Vocabulario japones de posicion de radical (構え kamae=envuelve por
# fuera, 垂れ tare=cuelga desde arriba-izquierda, 繞 nyo=envuelve por
# abajo-izquierda como ⻌) traducido al vocabulario que ya usa el resto
# del pipeline (mismo que las operaciones IDS de decompose_ids()).
KANJIVG_POSITION_MAP = {
    'kamae': 'enclosure', 'kamaec': 'inside',
    'tare': 'enclosure', 'tarec': 'inside',
    'nyo': 'enclosure', 'nyoc': 'inside',
    'middle': 'center',
}


def _kvg_named_parts(g, glyph, inherited_pos):
    """Componentes reales dentro de un grupo <g>, bajando por los
    envoltorios sin kvg:element propio (grupos que KanjiVG usa solo para
    agrupar visualmente 2+ piezas reales bajo una misma posicion, ej. el
    "top" de 黙 que envuelve a 黒(parte 1) y 犬 sin tener el mismo
    elemento). Antes el parser solo miraba hijos directos y se saltaba
    estos envoltorios enteros (`if not comp: continue`), perdiendo TODO
    lo que hubiera adentro -- confirmado en 63 caracteres de nuestro
    catalogo que se quedaban con un solo componente real teniendo dos o
    mas (ej. 黙 solo mostraba 黒 y nunca 犬, aunque el usuario lo notara
    a simple vista comparando el kanji con sus piezas)."""
    out = []
    for child in g:
        if child.tag != 'g':
            continue
        comp = child.get(KANJIVG_NS + 'element')
        pos = child.get(KANJIVG_NS + 'position')
        pos = KANJIVG_POSITION_MAP.get(pos, pos) if pos else None
        if comp and comp != glyph:
            phon = child.get(KANJIVG_NS + 'phon')
            out.append((comp, pos or inherited_pos or 'component', phon))
        else:
            # envoltorio sin elemento propio (o repite el glifo raiz,
            # que pasa en pictogramas simples cuando KanjiVG solo agrupa
            # el trazo): bajar un nivel, heredando su posicion si tenia
            # una mas especifica que la de mas arriba.
            out.extend(_kvg_named_parts(child, glyph, pos or inherited_pos))
    return out


def load_kanjivg():
    """glyph -> [(componente, posicion, pista_fonetica)], bajando por
    envoltorios de agrupacion visual sin su propio kvg:element (ver
    `_kvg_named_parts`). Deduplicado por componente: un mismo radical
    puede aparecer partido en 2+ trozos visuales dentro del SVG (ej. 黒
    en 黙 se dibuja en dos bloques separados), pero para el grafo es un
    solo componente real, no dos aristas iguales."""
    tree = ET.parse(SOURCES_DIR / 'kanjivg.xml')
    by_glyph = {}
    for kanji_el in tree.getroot():
        root_g = kanji_el.find('g')
        if root_g is None:
            continue
        glyph = root_g.get(KANJIVG_NS + 'element')
        if not glyph:
            continue
        parts = []
        seen_comps = set()
        for comp, pos, phon in _kvg_named_parts(root_g, glyph, None):
            if comp in seen_comps:
                continue
            seen_comps.add(comp)
            parts.append((comp, pos, phon))
        if parts:
            by_glyph[glyph] = parts
    return by_glyph


def hsk_level_of(row):
    if not row:
        return None
    m = re.match(r'HSK_L(\d+)', row.get('hsk30_level') or '')
    return int(m.group(1)) if m else None


def _resolve_ear(glyph, pos):
    """阝 es ambiguo sin posicion: izquierda = 阜 (colina), derecha =
    邑 (ciudad). El resto de los componentes se resuelve via MERGE_INTO;
    este es el unico que necesita ver la posicion para decidirse."""
    if glyph != '阝':
        return glyph
    return EAR_LEFT if 'left' in pos else EAR_RIGHT


def components_of(glyph, mmh_by_glyph, mega_by_glyph, kanjivg_by_glyph):
    """[(componente, posicion, rol)] para un caracter compuesto, o [] si
    es atomico. Prioriza Make Me a Hanzi (posicion real + rol
    semantico/fonetico via su etimologia); mega_hanzi es el respaldo 1
    (lista plana, sin posicion); KanjiVG es el respaldo 2, especifico
    de Japon, para formas shinjitai que ninguna fuente china cubre."""
    mmh = mmh_by_glyph.get(glyph)
    if mmh and mmh.get('decomposition'):
        leaves = [(g, p) for g, p in decompose_ids(mmh['decomposition']) if g != glyph]
        if leaves:
            etym = mmh.get('etymology') or {}
            phon, sem = etym.get('phonetic'), etym.get('semantic')
            return [(_resolve_ear(g, pos), pos, 'phon' if g == phon else 'sem') for g, pos in leaves]
    row = mega_by_glyph.get(glyph)
    if row:
        raw = row.get('decomposition2_with_radical', '') or ''
        parts = [p.strip() for p in raw.split(',') if p.strip() and p.strip() != 'No glyph available']
        parts = [p for p in parts if p != glyph]
        if len(parts) >= 2:
            return [(_resolve_ear(p, 'component'), 'component', 'sem') for p in parts]
    kvg_parts = kanjivg_by_glyph.get(glyph)
    if kvg_parts:
        return [(_resolve_ear(g, pos), pos, 'phon' if phon else 'sem') for g, pos, phon in kvg_parts]
    return []


def is_pictographic(glyph, mmh_by_glyph):
    """True si makemeahanzi marca este caracter como pictograma puro
    (un dibujo de una sola pieza, ej. 木 water 水 fuego 火). Para esos,
    el campo "decomposition" describe como se dibuja el glifo (trazos),
    no de que partes semanticas esta hecho -- 木 "decompone" en 十+八
    graficamente, pero eso no es un componente real para un estudiante.
    Solo cuando el tipo es 'ideographic' o 'pictophonetic' (o no hay
    etimologia registrada) confiamos en la descomposicion como real."""
    mmh = mmh_by_glyph.get(glyph)
    if not mmh:
        return False
    etym = mmh.get('etymology') or {}
    return etym.get('type') == 'pictographic'


def pick_illustrative_example(glyph, mega_by_glyph):
    """Para un radical que quedo totalmente aislado (ni entrada ni salida):
    busca en el campo component_in de mega_hanzi un compuesto real (aunque
    quede fuera del catalogo jouyou/HSK) que SI lo use, para no dejarlo
    como una isla sin ninguna conexion. None si mega_hanzi no tiene fila
    para este radical o su component_in viene vacio."""
    row = mega_by_glyph.get(glyph)
    if not row:
        return None
    raw = row.get('component_in', '') or ''
    candidates = [c.strip() for c in raw.split(',') if c.strip() and c.strip() != glyph]
    best = None
    for c in candidates:
        crow = mega_by_glyph.get(c)
        meaning = crow and (crow.get('meaning_junda') or crow.get('cc_cedict_definitions'))
        if meaning:
            return c, crow
        if best is None:
            best = (c, crow)
    return best


# Dominio semantico de cada uno de los 242 radicales canonicos, asignado
# a mano por el significado real de cada uno (ver docs/METODOLOGIA.md):
# nada de clustering automatico -- se probo agrupar los ~3684 caracteres
# por co-ocurrencia de radicales compartidos (Louvain) y salio disparejo
# e in-intuitivo (clusters de 1 caracter junto a otros de 200+, dificil
# de nombrar). Los radicales son solo 242 y ya vienen con un significado
# real en ingles (RADICAL_MEANING), asi que clasificarlos directamente
# es mas simple, mas intuitivo y mas facil de auditar a mano.
DOMAIN_MAP = {
    '一': 'Abstract', '｜': 'Abstract', '丶': 'Abstract', 'ノ': 'Abstract', '乙': 'Abstract',
    '亅': 'Abstract', '二': 'Abstract', '亠': 'Objects', '人': 'People', '儿': 'Body',
    '入': 'Actions', 'ハ': 'Abstract', '丷': 'Abstract', '冂': 'Places', '冖': 'Objects',
    '冫': 'Nature', '几': 'Objects', '凵': 'Objects', '刀': 'Objects', '力': 'Abstract',
    '勹': 'Actions', '匕': 'Objects', '匚': 'Objects', '十': 'Abstract', '卜': 'Abstract',
    '卩': 'People', '厂': 'Places', '厶': 'Abstract', '又': 'Actions', 'マ': 'Abstract',
    '九': 'Abstract', 'ユ': 'Abstract', '乃': 'Abstract', '𠂉': 'Abstract', '⻌': 'Places',
    '口': 'Body', '囗': 'Places', '土': 'Nature', '士': 'People', '夂': 'Actions',
    '夕': 'Nature', '大': 'Abstract', '女': 'People', '子': 'People', '宀': 'Places',
    '寸': 'Abstract', '小': 'Abstract', '尢': 'Body', '尸': 'Body', '屮': 'Nature',
    '山': 'Nature', '川': 'Nature', '巛': 'Nature', '工': 'Objects', '已': 'Abstract',
    '巾': 'Objects', '干': 'Abstract', '幺': 'Objects', '广': 'Places', '廴': 'Actions',
    '廾': 'Actions', '弋': 'Objects', '弓': 'Objects', 'ヨ': 'Animals', '彑': 'Animals',
    '彡': 'Body', '彳': 'Actions', '⺾': 'Nature', '⻏': 'Places', '⻖': 'Nature',
    '也': 'Abstract', '亡': 'Abstract', '及': 'Actions', '久': 'Abstract', '⺹': 'People',
    '心': 'Body', '戈': 'Objects', '戸': 'Places', '手': 'Body', '支': 'Nature',
    '攵': 'Actions', '文': 'People', '斗': 'Abstract', '斤': 'Objects', '方': 'Abstract',
    '无': 'Abstract', '日': 'Nature', '曰': 'People', '月': 'Nature', '木': 'Nature',
    '欠': 'Body', '止': 'Actions', '歹': 'Abstract', '殳': 'Actions', '比': 'Abstract',
    '毛': 'Animals', '氏': 'People', '气': 'Nature', '水': 'Nature', '火': 'Nature',
    '爪': 'Body', '父': 'People', '爻': 'Abstract', '爿': 'Objects', '片': 'Objects',
    '牛': 'Animals', '犬': 'Animals', '王': 'Objects', '元': 'Abstract', '井': 'Places',
    '勿': 'Abstract', '尤': 'Abstract', '五': 'Abstract', '屯': 'Places', '巴': 'Abstract',
    '毋': 'Abstract', '玄': 'Abstract', '瓦': 'Objects', '甘': 'Food', '生': 'People',
    '用': 'Abstract', '田': 'Food', '疋': 'Objects', '疒': 'Body', '癶': 'Actions',
    '白': 'Nature', '皮': 'Animals', '皿': 'Objects', '目': 'Body', '矛': 'Objects',
    '矢': 'Objects', '石': 'Nature', '示': 'People', '禸': 'Animals', '禾': 'Food',
    '穴': 'Places', '立': 'Actions', '世': 'People', '巨': 'Abstract', '冊': 'Objects',
    '母': 'People', '⺲': 'Objects', '牙': 'Animals', '瓜': 'Food', '竹': 'Nature',
    '米': 'Food', '糸': 'Objects', '缶': 'Objects', '羊': 'Animals', '羽': 'Animals',
    '而': 'Abstract', '耒': 'Food', '耳': 'Body', '聿': 'Objects', '肉': 'Body',
    '自': 'People', '至': 'Abstract', '臼': 'Objects', '舌': 'Body', '舟': 'Objects',
    '艮': 'Abstract', '色': 'Abstract', '虍': 'Animals', '虫': 'Animals', '血': 'Body',
    '行': 'Actions', '衣': 'Objects', '西': 'Abstract', '臣': 'People', '見': 'Body',
    '角': 'Animals', '言': 'People', '谷': 'Nature', '豆': 'Food', '豕': 'Animals',
    '豸': 'Animals', '貝': 'Objects', '赤': 'Nature', '走': 'Actions', '足': 'Body',
    '身': 'Body', '車': 'Objects', '辛': 'Food', '辰': 'Abstract', '酉': 'Food',
    '釆': 'Abstract', '里': 'Places', '舛': 'Actions', '麦': 'Food', '金': 'Objects',
    '長': 'Abstract', '門': 'Places', '隶': 'People', '隹': 'Animals', '雨': 'Nature',
    '青': 'Nature', '非': 'Abstract', '奄': 'Abstract', '岡': 'Nature', '免': 'Abstract',
    '斉': 'Abstract', '面': 'Body', '革': 'Objects', '韭': 'Food', '音': 'People',
    '頁': 'Body', '風': 'Nature', '飛': 'Actions', '食': 'Food', '首': 'Body',
    '香': 'Food', '品': 'Objects', '馬': 'Animals', '骨': 'Body', '高': 'Abstract',
    '髟': 'Body', '鬥': 'Actions', '鬯': 'Objects', '鬲': 'Objects', '鬼': 'Abstract',
    '竜': 'Animals', '韋': 'Objects', '魚': 'Animals', '鳥': 'Animals', '鹵': 'Nature',
    '鹿': 'Animals', '麻': 'Nature', '亀': 'Animals', '啇': 'Abstract', '黄': 'Nature',
    '黒': 'Nature', '黹': 'Objects', '無': 'Abstract', '歯': 'Body', '黽': 'Animals',
    '鼎': 'Objects', '鼓': 'Objects', '鼠': 'Animals', '鼻': 'Body', '齊': 'Abstract',
    '龠': 'Objects', '黍': 'Food',
}


MAX_ANCHOR_DEPTH = 4


def resolve_anchor_radical(glyph, mmh_by_glyph, mega_by_glyph, kanjivg_by_glyph, canonical_glyphs, _depth=0, _seen=None):
    """El radical de indexacion real de un caracter (el mismo que usan
    los diccionarios de papel), resuelto a uno de los 242 canonicos, para
    asignarle un dominio semantico. Prioriza el campo "radical" que trae
    makemeahanzi; si no esta o no resuelve a uno canonico (variante que
    MERGE_INTO no cubre, o un radical fuera de nuestros 242), cae al
    primer componente SEMANTICO real de components_of().

    Si NINGUNO de los componentes directos es canonico, intenta un salto
    mas: resolver el anclaje de cada componente semantico a su vez (ej.
    勲 -> 動, no canonico -> componentes de 動 -> 力, canonico). Antes esto
    se quedaba en None con solo un salto; la mayoria de los residuos sin
    categoria eran justo casos donde el radical de indexacion real esta
    a 2 saltos, no 1. `_seen` evita ciclos (no deberian existir en una
    descomposicion real, pero es una red de seguridad barata) y
    MAX_ANCHOR_DEPTH pone un tope duro por si acaso.

    Si el propio glyph es un pictograma puro (is_pictographic), su
    "descomposicion" es solo el trazo, no componentes reales -- igual
    que para los 243 radicales, no hay que confiar en ella (ver seccion
    4 de METODOLOGIA.md); simplemente no hay mas de donde sacar un ancla."""
    mmh = mmh_by_glyph.get(glyph)
    if mmh and mmh.get('radical'):
        cand = MERGE_INTO.get(mmh['radical'], mmh['radical'])
        if cand in canonical_glyphs:
            return cand
    if is_pictographic(glyph, mmh_by_glyph):
        return None
    if _seen is None:
        _seen = set()
    if glyph in _seen or _depth >= MAX_ANCHOR_DEPTH:
        return None
    _seen.add(glyph)
    sem_comps = [
        MERGE_INTO.get(comp_glyph, comp_glyph)
        for comp_glyph, pos, role in components_of(glyph, mmh_by_glyph, mega_by_glyph, kanjivg_by_glyph)
        if role == 'sem'
    ]
    for cand in sem_comps:
        if cand in canonical_glyphs:
            return cand
    for cand in sem_comps:
        deeper = resolve_anchor_radical(
            cand, mmh_by_glyph, mega_by_glyph, kanjivg_by_glyph, canonical_glyphs, _depth + 1, _seen,
        )
        if deeper:
            return deeper
    return None


def pct_rank(rank, worst_rank):
    """Percentil 0-100 dentro de SU PROPIO corpus (japones y chino no son
    comparables entre si en una sola escala; cada uno usa su propio rango
    de frecuencia real)."""
    if rank is None or worst_rank <= 1:
        return None
    return max(0, min(100, round(100 * (1 - (rank - 1) / (worst_rank - 1)))))


def build():
    by_glyph = {d['glyph']: d for d in radicals_raw}
    n_of = lambda g: by_glyph[g]['n'] if g in by_glyph else 9999

    # ---- 1) radicales canonicos (Excel) ----
    canonical = {}
    for rec in radicals_raw:
        g = rec['glyph']
        target = MERGE_INTO.get(g, g)
        stroke_type, stroke_type_name = STROKE_TYPES.get(target, (None, None))
        node = canonical.setdefault(target, {
            'id': None, 'glyph': target, 'variants': [], 'isRadical': True,
            'strokeCount': None, 'category': None, 'tier': None,
            'onyomi': None, 'kunyomi': None, 'pinyin': None,
            'meaning': RADICAL_MEANING.get(target), 'n': n_of(target),
            'strokeType': stroke_type, 'strokeTypeName': stroke_type_name,
            'isCharacter': False, 'jlpt': None, 'hsk': None,
            'freqJa': None, 'freqZh': None,
        })
        if g != target:
            node['variants'].append(g)
        if rec.get('strokeCount') is not None and node['strokeCount'] is None:
            node['strokeCount'] = rec['strokeCount']
        if node['category'] is None:
            node['category'] = DOMAIN_MAP.get(target)
        if rec.get('tier') is not None and node['tier'] is None:
            node['tier'] = rec.get('tier')
        if not node['meaning']:
            node['meaning'] = RADICAL_MEANING.get(target)

    canonical_glyphs = set(canonical.keys())

    # ---- 2) catalogo completo de kanji joyo + hanzi HSK 3.0 ----
    jouyou = load_jouyou()
    mega_by_glyph = load_mega_hanzi()
    mmh_by_glyph = load_mmh_dictionary()
    kanjivg_by_glyph = load_kanjivg()

    ja_worst = max(v['freq'] for v in jouyou.values() if v.get('freq') is not None)
    zh_worst = max(
        (int(r['frequency_junda']) for r in mega_by_glyph.values() if (r.get('frequency_junda') or '').isdigit()),
        default=None,
    )

    all_glyphs = set(jouyou.keys()) | {g for g, r in mega_by_glyph.items() if hsk_level_of(r)}

    characters_final = []
    compound_id_by_glyph = {}
    compound_order = []  # (glyph, node_data) en el orden en que se crean

    for glyph in sorted(all_glyphs):
        ja = jouyou.get(glyph)
        zh = mega_by_glyph.get(glyph)
        zh_level = hsk_level_of(zh)
        langs = []
        if ja:
            langs.append('ja')
        if zh_level:
            langs.append('zh')

        onyomi = ', '.join(ja['readings_on']) if ja and ja.get('readings_on') else None
        kunyomi = ', '.join(ja['readings_kun']) if ja and ja.get('readings_kun') else None
        pinyin = zh.get('pinyin') if zh else None
        if ja and ja.get('meanings'):
            meaning = ja['meanings'][0]
        elif zh:
            meaning = zh.get('meaning_junda') or zh.get('cc_cedict_definitions')
        else:
            meaning = None
        jlpt = f"N{ja['jlpt_new']}" if ja and ja.get('jlpt_new') else None
        freq_ja = pct_rank(ja.get('freq'), ja_worst) if ja else None
        freq_zh = None
        if zh and zh_worst and (zh.get('frequency_junda') or '').isdigit():
            freq_zh = pct_rank(int(zh['frequency_junda']), zh_worst)

        target = MERGE_INTO.get(glyph, glyph)
        if target in canonical:
            # el caracter ES uno de nuestros 243 radicales, o se funde en
            # uno via MERGE_INTO (ej. 马 -> 馬, mismo caracter simplificado/
            # tradicional): se fusiona en ese nodo en vez de crear un
            # duplicado (ej. 木, 人, 水, 好... no, 好 no es radical, pero
            # 木/人/水 si lo son). Cuando el merge SI cambio el glifo se
            # guarda la forma alterna en "variants" (si no, 马/车/见/门/
            # etc. dejaban de ser encontrables por busqueda: el nodo final
            # solo conserva el glifo tradicional/shinjitai). Los campos de
            # nivel/frecuencia nunca se sobreescriben con None: si el
            # mismo nodo recibe una pasada japonesa y otra china (en
            # cualquier orden, sorted() no lo garantiza), las dos deben
            # sobrevivir -- antes procesar 马 despues de 馬 borraba el
            # JLPT que la pasada de 馬 ya habia puesto.
            node = canonical[target]
            node['isCharacter'] = True
            if glyph != target and glyph not in node['variants']:
                node['variants'].append(glyph)
            node['onyomi'] = onyomi or node['onyomi']
            node['kunyomi'] = kunyomi or node['kunyomi']
            node['pinyin'] = pinyin or node['pinyin']
            if meaning:
                node['meaning'] = meaning
            if jlpt:
                node['jlpt'] = jlpt
            if zh_level is not None:
                node['hsk'] = zh_level
            if freq_ja is not None:
                node['freqJa'] = freq_ja
            if freq_zh is not None:
                node['freqZh'] = freq_zh
            continue  # ser radical no significa ser atomico -- ver mas abajo

        if not langs:
            continue  # ni joyo ni HSK (solo aparecio como fila de mega_hanzi sin nivel)

        cid = f"c{len(compound_order) + 1:05d}"
        anchor = resolve_anchor_radical(glyph, mmh_by_glyph, mega_by_glyph, kanjivg_by_glyph, canonical_glyphs)
        data = {
            'id': cid, 'glyph': glyph, 'isCharacter': True, 'isRadical': False,
            'onyomi': onyomi, 'kunyomi': kunyomi, 'pinyin': pinyin, 'meaning': meaning,
            'jlpt': jlpt, 'hsk': zh_level, 'langs': langs,
            'freqJa': freq_ja, 'freqZh': freq_zh,
            'category': DOMAIN_MAP.get(anchor) if anchor else None,
        }
        characters_final.append(data)
        compound_id_by_glyph[glyph] = cid
        compound_order.append(glyph)

    radicals_final = sorted(canonical.values(), key=lambda d: d['n'])
    for i, r in enumerate(radicals_final):
        r['id'] = f"r{i + 1:03d}"
    radical_id_by_glyph = {r['glyph']: r['id'] for r in radicals_final}

    # ---- 3) aristas: componente -> radical/compuesto/extra ----
    extra_nodes = {}

    def resolve_component_id(glyph):
        glyph = MERGE_INTO.get(glyph, glyph)
        if glyph in radical_id_by_glyph:
            return radical_id_by_glyph[glyph]
        if glyph in compound_id_by_glyph:
            return compound_id_by_glyph[glyph]
        if glyph in extra_nodes:
            return extra_nodes[glyph]['id']
        eid = f"x{len(extra_nodes) + 1:04d}"
        extra_nodes[glyph] = {'id': eid, 'glyph': glyph}
        return eid

    # Direccion: SIEMPRE de la pieza simple hacia lo que la contiene
    # (componente -> compuesto), nunca al reves. Un radical no es
    # automaticamente atomico solo por estar en la lista de 243: 色
    # (color) es radical Y se descompone en 巴 real (⺈+巴, etimologia
    # ideografica) -- si es un pictograma puro (木, 水, 火...) su
    # "descomposicion" es solo la forma en que se dibuja el trazo, no
    # componentes reales, y is_pictographic() la descarta.
    edges_final = []

    def add_edges_for(owner_glyph, owner_id):
        for comp_glyph, pos, role in components_of(owner_glyph, mmh_by_glyph, mega_by_glyph, kanjivg_by_glyph):
            edges_final.append({
                'from': resolve_component_id(comp_glyph), 'to': owner_id,
                'pos': pos, 'role': role,
            })

    for glyph in compound_order:
        add_edges_for(glyph, compound_id_by_glyph[glyph])

    for glyph, radical_id in radical_id_by_glyph.items():
        if not is_pictographic(glyph, mmh_by_glyph):
            add_edges_for(glyph, radical_id)

    # Un puñado de radicales canonicos (韭, 鹵, 黽, 鼎, 鼠, 龠...) son
    # pictogramas puros legitimos -- igual que 木/水/火 -- pero ademas no
    # aparecen como componente de NINGUN caracter jouyou/HSK real, asi que
    # quedan como islas totales (ni entrada ni salida). La exclusion de
    # descomposicion sigue siendo correcta; para que no parezcan un nodo
    # roto se les agrega UNA arista de ejemplo hacia un compuesto real
    # (aunque quede fuera del catalogo oficial) usando component_in de
    # mega_hanzi. Si mega_hanzi no tiene ni eso (ej. 鹵, 黽), se quedan
    # aislados de verdad -- no hay ninguna fuente con un ejemplo real.
    touched = {e['from'] for e in edges_final} | {e['to'] for e in edges_final}
    for glyph, radical_id in radical_id_by_glyph.items():
        if radical_id in touched:
            continue
        pick = pick_illustrative_example(glyph, mega_by_glyph)
        if not pick:
            continue
        example_glyph, example_row = pick
        example_id = resolve_component_id(example_glyph)
        resolved_glyph = MERGE_INTO.get(example_glyph, example_glyph)
        if resolved_glyph in extra_nodes:
            extra_nodes[resolved_glyph].update({
                'meaning': example_row.get('meaning_junda') or example_row.get('cc_cedict_definitions'),
                'pinyin': example_row.get('pinyin'),
                'isExample': True,
            })
        edges_final.append({'from': radical_id, 'to': example_id, 'pos': 'example', 'role': 'sem'})

    # ---- 4) los nodos "extra" tampoco son atomos ----
    # Cayeron fuera del catalogo de 242 radicales Y del catalogo
    # jouyou+HSK, pero eso no los vuelve pictogramas puros: la mayoria SI
    # tiene descomposicion real en las mismas fuentes que ya usamos para
    # radicales y caracteres (ver docs/METODOLOGIA.md seccion 10). Se
    # procesa en cola porque descomponer un extra puede revelar un
    # componente que todavia no existe como nodo (un extra "nieto"), que
    # a su vez hay que descomponer -- en la practica satura rapido (el
    # espacio real de componentes CJK es finito), pero se procesa como
    # cola en vez de una sola pasada por si acaso. `seen_extras` evita
    # reprocesar el mismo glifo dos veces (y corta cualquier ciclo).
    seen_extras = set()
    worklist = list(extra_nodes.keys())
    while worklist:
        glyph = worklist.pop()
        if glyph in seen_extras:
            continue
        seen_extras.add(glyph)
        if is_pictographic(glyph, mmh_by_glyph):
            continue  # mismo criterio que para radicales: sin componentes reales
        owner_id = extra_nodes[glyph]['id']
        before = set(extra_nodes.keys())
        add_edges_for(glyph, owner_id)
        worklist.extend(set(extra_nodes.keys()) - before)

    for x in extra_nodes.values():
        anchor = resolve_anchor_radical(x['glyph'], mmh_by_glyph, mega_by_glyph, kanjivg_by_glyph, canonical_glyphs)
        x['category'] = DOMAIN_MAP.get(anchor) if anchor else None

    return {
        'radicals': radicals_final,
        'characters': characters_final,
        'extras': list(extra_nodes.values()),
        'edges': edges_final,
    }


if __name__ == '__main__':
    result = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))
    ja_n = sum(1 for c in result['characters'] if 'ja' in c['langs'])
    zh_n = sum(1 for c in result['characters'] if 'zh' in c['langs'])
    print(f"radicals={len(result['radicals'])} characters={len(result['characters'])} "
          f"(ja={ja_n} zh={zh_n}) extras={len(result['extras'])} edges={len(result['edges'])}")
    print(f"-> {OUT_PATH}")
