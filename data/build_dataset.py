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
    etimologia semantica/fonetica, usada como fuente principal de
    componentes; mega_hanzi es el respaldo cuando un kanji joyo
    (forma shinjitai) no aparece ahi.

Uso:
    cd data
    python fetch_sources.py   # una sola vez, cachea los 3 archivos
    python build_dataset.py

Vuelve a correr build_dataset.py cada vez que se edite este archivo o
el Excel. No hace falta volver a tocar fetch_sources.py salvo que
quieras refrescar los datasets (borra data/sources/ y vuelve a correrlo).
"""
import csv
import json
import re
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
}

# Base de una taxonomia de trazos: los radicales de 1 solo trazo son,
# literalmente, los trazos fundamentales del sistema (bloque Unicode
# "CJK Strokes" + las 8 categorias clasicas del "yong zi ba fa" 永字八法).
# strokeType = categoria principal; strokeTypeName = nombre chino/pinyin.
# Los radicales de 2+ trazos (十, 又, 工...) no se etiquetan aqui todavia:
# requieren datos reales de ORDEN de trazo (ej. KanjiVG) para no adivinar.
STROKE_TYPES = {
    '一': ('heng', '横 (héng) — horizontal'),
    '｜': ('shu', '竖 (shù) — vertical'),
    '丶': ('dian', '点 (diǎn) — punto'),
    'ノ': ('pie', '撇 (piě) — caída a la izquierda'),
    '乙': ('zhe', '折 (zhé) — trazo quebrado/curvo'),
    '亅': ('gou', '钩 (gōu) — gancho'),
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


def hsk_level_of(row):
    if not row:
        return None
    m = re.match(r'HSK_L(\d+)', row.get('hsk30_level') or '')
    return int(m.group(1)) if m else None


def components_of(glyph, mmh_by_glyph, mega_by_glyph):
    """[(componente, posicion, rol)] para un caracter compuesto, o [] si
    es atomico. Prioriza Make Me a Hanzi (posicion real + rol
    semantico/fonetico via su etimologia); mega_hanzi es el respaldo
    (lista plana, sin posicion) para formas que no esten ahi."""
    mmh = mmh_by_glyph.get(glyph)
    if mmh and mmh.get('decomposition'):
        leaves = [(g, p) for g, p in decompose_ids(mmh['decomposition']) if g != glyph]
        if leaves:
            etym = mmh.get('etymology') or {}
            phon, sem = etym.get('phonetic'), etym.get('semantic')
            return [(g, pos, 'phon' if g == phon else 'sem') for g, pos in leaves]
    row = mega_by_glyph.get(glyph)
    if row:
        raw = row.get('decomposition2_with_radical', '') or ''
        parts = [p.strip() for p in raw.split(',') if p.strip() and p.strip() != 'No glyph available']
        parts = [p for p in parts if p != glyph]
        if len(parts) >= 2:
            return [(p, 'component', 'sem') for p in parts]
    return []


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
        if rec.get('category') and node['category'] is None:
            node['category'] = rec['category']
            node['tier'] = rec.get('tier')
        if not node['meaning']:
            node['meaning'] = RADICAL_MEANING.get(target)

    # ---- 2) catalogo completo de kanji joyo + hanzi HSK 3.0 ----
    jouyou = load_jouyou()
    mega_by_glyph = load_mega_hanzi()
    mmh_by_glyph = load_mmh_dictionary()

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
            # el caracter ES uno de nuestros 243 radicales: se fusiona en
            # ese nodo en vez de crear un duplicado (ej. 木, 人, 水, 好...
            # no, 好 no es radical, pero 木/人/水 si lo son).
            node = canonical[target]
            node['isCharacter'] = True
            node['onyomi'] = onyomi or node['onyomi']
            node['kunyomi'] = kunyomi or node['kunyomi']
            node['pinyin'] = pinyin or node['pinyin']
            if meaning:
                node['meaning'] = meaning
            node['jlpt'] = jlpt
            node['hsk'] = zh_level
            node['freqJa'] = freq_ja
            node['freqZh'] = freq_zh
            continue

        if not langs:
            continue  # ni joyo ni HSK (solo aparecio como fila de mega_hanzi sin nivel)

        cid = f"c{len(compound_order) + 1:05d}"
        data = {
            'id': cid, 'glyph': glyph, 'isCharacter': True, 'isRadical': False,
            'onyomi': onyomi, 'kunyomi': kunyomi, 'pinyin': pinyin, 'meaning': meaning,
            'jlpt': jlpt, 'hsk': zh_level, 'langs': langs,
            'freqJa': freq_ja, 'freqZh': freq_zh,
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

    edges_final = []
    for glyph in compound_order:
        cid = compound_id_by_glyph[glyph]
        for comp_glyph, pos, role in components_of(glyph, mmh_by_glyph, mega_by_glyph):
            edges_final.append({
                'from': cid, 'to': resolve_component_id(comp_glyph),
                'pos': pos, 'role': role,
            })

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
