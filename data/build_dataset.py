# -*- coding: utf-8 -*-
"""
Genera backend/app/data/graph_data.json a partir de Pictograms.xlsx.

Lee la matriz de clasificacion semantica y la lista de radicales por
numero de trazos del Excel, fusiona formas-variante (por ejemplo la
version de "persona" a la izquierda, que aparece como caracter aparte
en el Excel, no es un radical distinto sino la misma idea escrita en
otra posicion) y le agrega significados en ingles + un set curado de
caracteres compuestos (kanji/hanzi) con sus radicales componentes.

Uso:
    cd data
    python build_dataset.py

Vuelve a correr este script cada vez que se edite este archivo (para
agregar mas caracteres compuestos) o el Excel (para agregar radicales
o rellenar lecturas/significados que todavia esten vacios ahi).
"""
import json
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
EXCEL_PATH = ROOT / "docs" / "Pictograms.xlsx"
OUT_PATH = ROOT / "backend" / "app" / "data" / "graph_data.json"

CATS = ['Primitive', 'Components', 'Human', 'Body', 'Matter', 'Places',
        'Nature', 'Food', 'Animals', 'Objects', 'Life']
TIER_NAMES = {
    0: 'Position/Base', 1: 'Unity', 2: 'Mnemonic duality', 3: 'Modifiers',
    7: 'Several usages', 8: 'Auxiliar', 9: 'Complex conditional',
}


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

# Lecturas/significados para radicales que TAMBIEN son caracteres corrientes
# por si solos (no son "compuestos" -> no llevan aristas de componentes).
# (onyomi, kunyomi, pinyin, meaning, jlpt, hsk)
STANDALONE = {
    '一': ('ichi', 'hito(tsu)', 'yī', 'one', 'N5', 1),
    '二': ('ni', 'futa(tsu)', 'èr', 'two', 'N5', 1),
    '九': ('kyuu', 'kokono(tsu)', 'jiǔ', 'nine', 'N5', 1),
    '十': ('juu', 'too', 'shí', 'ten', 'N5', 1),
    '五': ('go', 'itsu(tsu)', 'wǔ', 'five', 'N5', 1),
    '人': ('jin', 'hito', 'rén', 'person', 'N5', 1),
    '口': ('kou', 'kuchi', 'kǒu', 'mouth', 'N5', 1),
    '木': ('boku', 'ki', 'mù', 'tree, wood', 'N5', 1),
    '水': ('sui', 'mizu', 'shuǐ', 'water', 'N5', 1),
    '火': ('ka', 'hi', 'huǒ', 'fire', 'N5', 1),
    '金': ('kin', 'kane', 'jīn', 'gold, metal, money', 'N5', 1),
    '土': ('do', 'tsuchi', 'tǔ', 'earth, soil', 'N5', 1),
    '日': ('nichi', 'hi', 'rì', 'sun, day', 'N5', 1),
    '月': ('getsu', 'tsuki', 'yuè', 'moon, month', 'N5', 1),
    '女': ('jo', 'onna', 'nǚ', 'woman', 'N5', 1),
    '子': ('shi', 'ko', 'zǐ', 'child', 'N5', 1),
    '大': ('dai', 'oo(kii)', 'dà', 'big', 'N5', 1),
    '小': ('shou', 'chii(sai)', 'xiǎo', 'small', 'N5', 1),
    '山': ('san', 'yama', 'shān', 'mountain', 'N5', 1),
    '川': ('sen', 'kawa', 'chuān', 'river', 'N5', 3),
    '田': ('den', 'ta', 'tián', 'rice field', 'N5', 4),
    '目': ('moku', 'me', 'mù', 'eye', 'N5', 2),
    '耳': ('ji', 'mimi', 'ěr', 'ear', 'N5', 3),
    '手': ('shu', 'te', 'shǒu', 'hand', 'N5', 1),
    '心': ('shin', 'kokoro', 'xīn', 'heart, mind', 'N4', 2),
    '足': ('soku', 'ashi', 'zú', 'foot, leg, sufficient', 'N5', 3),
    '王': ('ou', None, 'wáng', 'king', 'N2', 3),
    '牛': ('gyuu', 'ushi', 'niú', 'cow, ox', 'N3', 2),
    '犬': ('ken', 'inu', 'quǎn', 'dog', 'N4', 4),
    '馬': ('ba', 'uma', 'mǎ', 'horse', 'N4', 2),
    '鳥': ('chou', 'tori', 'niǎo', 'bird', 'N5', 3),
    '魚': ('gyo', 'sakana', 'yú', 'fish', 'N5', 2),
    '米': ('bei', 'kome', 'mǐ', 'rice', 'N4', 2),
    '石': ('seki', 'ishi', 'shí', 'stone', 'N4', 3),
    '禾': (None, None, 'hé', 'grain, rice plant', None, 5),
    '虫': ('chuu', 'mushi', 'chóng', 'insect, bug', 'N4', 3),
    '貝': (None, 'kai', 'bèi', 'shell, money', 'N3', None),
    '力': ('ryoku', 'chikara', 'lì', 'power, strength', 'N4', 2),
    '刀': ('tou', 'katana', 'dāo', 'knife, sword', 'N4', 5),
    '弓': ('kyuu', 'yumi', 'gōng', 'bow', 'N2', None),
    '矢': (None, 'ya', 'shǐ', 'arrow', 'N2', None),
    '方': ('hou', 'kata', 'fāng', 'direction, square', 'N4', 1),
    '文': ('bun', 'fumi', 'wén', 'writing, sentence', 'N4', 2),
    '止': ('shi', 'to(maru)', 'zhǐ', 'stop', 'N3', 3),
    '白': ('haku', 'shiro', 'bái', 'white', 'N4', 1),
    '母': ('bo', 'haha', 'mǔ', 'mother', 'N4', 1),
    '西': ('sei', 'nishi', 'xī', 'west', 'N5', 1),
    '色': ('shoku', 'iro', 'sè', 'color', 'N4', 2),
    '身': ('shin', 'mi', 'shēn', 'body', 'N3', 3),
    '行': ('kou', 'i(ku)', 'xíng', 'go, conduct', 'N5', 1),
    '赤': ('seki', 'aka', 'chì', 'red', 'N4', None),
    '里': ('ri', 'sato', 'lǐ', 'village, distance unit', 'N2', None),
    '高': ('kou', 'taka(i)', 'gāo', 'tall, high', 'N5', 1),
    '首': ('shu', 'kubi', 'shǒu', 'neck, head', 'N3', 4),
    '音': ('on', 'oto', 'yīn', 'sound', 'N4', 2),
    '面': ('men', 'omote', 'miàn', 'face, surface', 'N3', 2),
    '革': ('kaku', 'kawa', 'gé', 'leather, reform', 'N1', 6),
    '黄': ('kou', 'ki', 'huáng', 'yellow', 'N3', 3),
    '黒': ('koku', 'kuro', 'hēi(黑)', 'black', 'N4', None),
    '無': ('mu', 'na(i)', 'wú(无)', 'nothing, without', 'N4', 2),
    '歯': ('shi', 'ha', 'chǐ(齿)', 'tooth', 'N3', None),
    '毛': ('mou', 'ke', 'máo', 'hair, fur', 'N3', 3),
    '氏': ('shi', 'uji', 'shì', 'clan, family name', 'N2', None),
    '長': ('chou', 'naga(i)', 'zhǎng(长)', 'long, chief', 'N4', 1),
    '門': ('mon', 'kado', 'mén', 'gate, door', 'N4', 1),
    '車': ('sha', 'kuruma', 'chē', 'vehicle, cart', 'N4', 1),
    '雨': ('u', 'ame', 'yǔ', 'rain', 'N5', 2),
    '言': ('gen', 'koto', 'yán', 'word, speech', 'N3', 4),
    '自': ('ji', 'mizuka(ra)', 'zì', 'self, from', 'N4', 2),
    '見': ('ken', 'mi(ru)', 'jiàn', 'see', 'N5', 1),
    '生': ('sei', 'i(kiru)', 'shēng', 'life, birth, grow', 'N5', 1),
    '用': ('you', 'mochi(iru)', 'yòng', 'use', 'N4', 1),
}

# Caracteres compuestos: (glyph, onyomi, kunyomi, pinyin, meaning, jlpt, hsk,
# [(radical/componente, posicion, rol), ...]).
# rol: 'sem' = aporta significado, 'phon' = aporta sonido, 'mark' = marca
# grafica sin lectura propia.
COMPOUNDS = [
    ('三', 'san', 'mi(ttsu)', 'sān', 'three', 'N5', 1, [('一','top','sem'),('一','mid','sem'),('一','bottom','sem')]),
    ('四', 'shi', 'yon', 'sì', 'four', 'N5', 1, [('囗','enclosure','sem'),('ハ','inside','mark')]),
    ('六', 'roku', 'mu(ttsu)', 'liù', 'six', 'N5', 1, [('亠','top','mark'),('ハ','bottom','mark')]),
    ('林', 'rin', 'hayashi', 'lín', 'woods, grove', 'N4', 4, [('木','left','sem'),('木','right','sem')]),
    ('森', 'shin', 'mori', 'sēn', 'forest', 'N3', 4, [('木','top','sem'),('木','bottom-left','sem'),('木','bottom-right','sem')]),
    ('休', 'kyuu', 'yasu(mu)', 'xiū', 'rest', 'N5', 2, [('人','left','sem'),('木','right','sem')]),
    ('校', 'kou', None, 'xiào', 'school', 'N5', 1, [('木','left','sem'),('交','right','phon')]),
    ('村', 'son', 'mura', 'cūn', 'village', 'N4', 3, [('木','left','sem'),('寸','right','phon')]),
    ('材', 'zai', None, 'cái', 'material, timber', 'N3', 4, [('木','left','sem'),('才','right','phon')]),
    ('本', 'hon', 'moto', 'běn', 'book, origin, root', 'N5', 1, [('木','whole','sem'),('一','bottom','mark')]),
    ('末', 'matsu', 'sue', 'mò', 'end, tip', 'N2', None, [('木','whole','sem'),('一','top','mark')]),
    ('東', 'tou', 'higashi', 'dōng(东)', 'east', 'N4', 2, [('日','center','sem'),('木','whole','sem')]),
    ('橋', 'kyou', 'hashi', 'qiáo', 'bridge', 'N3', 4, [('木','left','sem'),('喬','right','phon')]),
    ('机', 'ki', 'tsukue', 'jī', 'desk', 'N3', 4, [('木','left','sem'),('几','right','phon')]),
    ('案', 'an', None, 'àn', 'plan, proposal, desk', 'N3', 4, [('安','top','phon'),('木','bottom','sem')]),
    ('柱', 'chuu', 'hashira', 'zhù', 'pillar', 'N2', 5, [('木','left','sem'),('主','right','phon')]),
    ('枝', 'shi', 'eda', 'zhī', 'branch', 'N2', 5, [('木','left','sem'),('支','right','phon')]),
    ('板', 'ban', 'ita', 'bǎn', 'board, plank', 'N3', 4, [('木','left','sem'),('反','right','phon')]),
    ('明', 'mei', 'aka(rui)', 'míng', 'bright', 'N4', 3, [('日','left','sem'),('月','right','sem')]),
    ('時', 'ji', 'toki', 'shí(时)', 'time', 'N5', None, [('日','left','sem'),('寺','right','phon')]),
    ('曜', 'you', None, None, 'weekday (as in ~曜日)', 'N5', None, [('日','left','sem'),('羽','top-right','mark'),('隹','bottom-right','phon')]),
    ('春', 'shun', 'haru', 'chūn', 'spring', 'N4', 3, [('日','bottom','sem')]),
    ('晴', 'sei', 'ha(reru)', 'qíng', 'clear weather', 'N3', 3, [('日','left','sem'),('青','right','phon')]),
    ('昼', 'chuu', 'hiru', None, 'daytime', 'N4', None, [('日','bottom','sem')]),
    ('暗', 'an', 'kura(i)', 'àn', 'dark', 'N3', 4, [('日','left','sem'),('音','right','phon')]),
    ('映', 'ei', 'utsu(ru)', 'yìng', 'reflect, project', 'N3', 5, [('日','left','sem'),('央','right','phon')]),
    ('昔', 'seki', 'mukashi', 'xī', 'long ago', 'N2', 5, [('日','bottom','sem')]),
    ('体', 'tai', 'karada', 'tǐ', 'body', 'N4', 2, [('人','left','sem'),('本','right','phon')]),
    ('他', 'ta', 'hoka', 'tā', 'other, he', 'N4', 1, [('人','left','sem'),('也','right','phon')]),
    ('何', 'ka', 'nani', 'hé', 'what', 'N5', 1, [('人','left','sem'),('可','right','phon')]),
    ('住', 'juu', 'su(mu)', 'zhù', 'reside', 'N4', 3, [('人','left','sem'),('主','right','phon')]),
    ('信', 'shin', None, 'xìn', 'trust, letter', 'N3', 3, [('人','left','sem'),('言','right','sem')]),
    ('作', 'saku', 'tsuku(ru)', 'zuò', 'make', 'N4', 2, [('人','left','sem'),('乍','right','phon')]),
    ('使', 'shi', 'tsuka(u)', 'shǐ', 'use, envoy', 'N3', 3, [('人','left','sem'),('吏','right','phon')]),
    ('便', 'ben', 'tayo(ri)', 'biàn', 'convenient', 'N3', 4, [('人','left','sem'),('更','right','phon')]),
    ('働', 'dou', 'hatara(ku)', None, 'work, labor (Japan-made kanji)', 'N4', None, [('人','left','sem'),('動','right','sem')]),
    ('係', 'kei', 'kakari', 'xì', 'relation, in charge of', 'N3', None, [('人','left','sem'),('系','right','phon')]),
    ('例', 'rei', 'tato(eru)', 'lì', 'example', 'N3', 4, [('人','left','sem'),('列','right','phon')]),
    ('今', 'kon', 'ima', 'jīn', 'now', 'N5', 1, [('𠆢','top','sem')]),
    ('以', 'i', None, 'yǐ', 'by means of, with', 'N3', 2, [('人','left','sem')]),
    ('仕', 'shi', 'tsuka(eru)', 'shì', 'serve', 'N4', 5, [('人','left','sem'),('士','right','phon')]),
    ('学', 'gaku', 'mana(bu)', 'xué', 'study, learning', 'N5', 1, [('冖','top','sem'),('子','bottom','sem')]),
    ('字', 'ji', 'aza', 'zì', 'character, letter', 'N5', 1, [('宀','top','sem'),('子','bottom','sem')]),
    ('海', 'kai', 'umi', 'hǎi', 'sea', 'N4', 2, [('水','left','sem'),('毎','right','phon')]),
    ('洗', 'sen', 'ara(u)', 'xǐ', 'wash', 'N3', 4, [('水','left','sem'),('先','right','phon')]),
    ('泳', 'ei', None, 'yǒng', 'swim', 'N3', 4, [('水','left','sem'),('永','right','phon')]),
    ('注', 'chuu', 'soso(gu)', 'zhù', 'pour,注意 attention', 'N3', 3, [('水','left','sem'),('主','right','phon')]),
    ('油', 'yu', 'abura', 'yóu', 'oil', 'N3', 3, [('水','left','sem'),('由','right','phon')]),
    ('酒', 'shu', 'sake', 'jiǔ', 'alcohol', 'N3', 4, [('水','left','sem'),('酉','right','sem')]),
    ('港', 'kou', 'minato', 'gǎng', 'harbor', 'N3', 5, [('水','left','sem'),('巷','right','phon')]),
    ('活', 'katsu', None, 'huó', 'life, activity', 'N4', 3, [('水','left','sem'),('舌','right','phon')]),
    ('漢', 'kan', None, 'hàn(汉)', 'China, Sino-', 'N3', None, [('水','left','sem')]),
    ('湖', 'ko', 'mizuumi', 'hú', 'lake', 'N3', 4, [('水','left','sem'),('胡','right','phon')]),
    ('忙', 'bou', 'isoga(shii)', 'máng', 'busy', 'N4', 3, [('心','left','sem'),('亡','right','phon')]),
    ('快', 'kai', 'kokoroyo(i)', 'kuài', 'pleasant, fast', 'N2', 3, [('心','left','sem'),('夬','right','phon')]),
    ('性', 'sei', None, 'xìng', 'nature, gender', 'N3', 3, [('心','left','sem'),('生','right','phon')]),
    ('情', 'jou', 'nasake', 'qíng', 'emotion', 'N3', 4, [('心','left','sem'),('青','right','phon')]),
    ('想', 'sou', None, 'xiǎng', 'think', 'N3', 2, [('相','top','phon'),('心','bottom','sem')]),
    ('思', 'shi', 'omo(u)', 'sī', 'think', 'N4', 2, [('田','top','mark'),('心','bottom','sem')]),
    ('意', 'i', None, 'yì', 'meaning, intention', 'N4', 2, [('音','top','phon'),('心','bottom','sem')]),
    ('急', 'kyuu', 'iso(gu)', 'jí', 'urgent', 'N3', 3, [('心','bottom','sem')]),
    ('悪', 'aku', 'waru(i)', 'è(恶)', 'bad, evil', 'N4', None, [('亜','top','phon'),('心','bottom','sem')]),
    ('忘', 'bou', 'wasu(reru)', 'wàng', 'forget', 'N3', 4, [('亡','top','phon'),('心','bottom','sem')]),
    ('語', 'go', 'kata(ru)', 'yǔ(语)', 'language, word', 'N5', None, [('言','left','sem'),('吾','right','phon')]),
    ('話', 'wa', 'hana(su)', 'huà(话)', 'talk, story', 'N5', None, [('言','left','sem'),('舌','right','phon')]),
    ('読', 'doku', 'yo(mu)', 'dú(读)', 'read', 'N5', None, [('言','left','sem'),('売','right','phon')]),
    ('記', 'ki', 'shiru(su)', 'jì(记)', 'record', 'N4', None, [('言','left','sem'),('己','right','phon')]),
    ('計', 'kei', 'haka(ru)', 'jì(计)', 'measure, plan', 'N4', None, [('言','left','sem'),('十','right','sem')]),
    ('訓', 'kun', None, 'xùn', 'instruction, kun-reading', 'N3', None, [('言','left','sem'),('川','right','phon')]),
    ('詞', 'shi', None, 'cí(词)', 'word, part of speech', 'N2', None, [('言','left','sem'),('司','right','phon')]),
    ('課', 'ka', None, 'kè(课)', 'lesson, section', 'N3', None, [('言','left','sem'),('果','right','phon')]),
    ('議', 'gi', None, 'yì(议)', 'discuss', 'N3', None, [('言','left','sem'),('義','right','phon')]),
    ('詩', 'shi', None, 'shī', 'poem', 'N2', 5, [('言','left','sem'),('寺','right','phon')]),
    ('好', 'kou', 'su(ki)', 'hǎo', 'like, good', 'N4', 1, [('女','left','sem'),('子','right','sem')]),
    ('姉', 'shi', 'ane', None, 'older sister', 'N5', None, [('女','left','sem'),('市','right','phon')]),
    ('妹', 'mai', 'imouto', 'mèi', 'younger sister', 'N5', 1, [('女','left','sem'),('未','right','phon')]),
    ('始', 'shi', 'hajime(ru)', 'shǐ', 'begin', 'N4', 3, [('女','left','sem'),('台','right','phon')]),
    ('姓', 'sei', None, 'xìng', 'surname', 'N2', 5, [('女','left','sem'),('生','right','phon')]),
    ('妻', 'sai', 'tsuma', 'qī', 'wife', 'N2', 4, [('女','bottom','sem')]),
    ('如', 'jo', None, 'rú', 'as if, likeness', 'N1', 5, [('女','left','sem'),('口','right','sem')]),
    ('姫', 'ki', 'hime', None, 'princess', 'N1', None, [('女','left','sem'),('臣','right','phon')]),
    ('持', 'ji', 'mo(tsu)', 'chí', 'hold', 'N4', 3, [('手','left','sem'),('寺','right','phon')]),
    ('打', 'da', 'u(tsu)', 'dǎ', 'hit', 'N3', 2, [('手','left','sem'),('丁','right','phon')]),
    ('投', 'tou', 'na(geru)', 'tóu', 'throw', 'N3', 4, [('手','left','sem'),('殳','right','phon')]),
    ('指', 'shi', 'yubi', 'zhǐ', 'finger, point', 'N3', 3, [('手','left','sem'),('旨','right','phon')]),
    ('押', 'ou', 'o(su)', 'yā', 'push, stamp', 'N2', 5, [('手','left','sem'),('甲','right','phon')]),
    ('拾', 'shuu', 'hiro(u)', 'shí', 'pick up', 'N3', 5, [('手','left','sem'),('合','right','phon')]),
    ('招', 'shou', 'mane(ku)', 'zhāo', 'invite, beckon', 'N1', 5, [('手','left','sem'),('召','right','phon')]),
    ('焼', 'shou', 'ya(ku)', None, 'burn', 'N3', None, [('火','left','sem'),('尭','right','phon')]),
    ('煙', 'en', 'kemuri', 'yān(烟)', 'smoke', 'N2', 4, [('火','left','sem'),('垔','right','phon')]),
    ('然', 'zen', None, 'rán', 'so, like that', 'N3', 4, [('火','bottom','sem')]),
    ('銀', 'gin', None, 'yín(银)', 'silver', 'N3', 4, [('金','left','sem'),('艮','right','phon')]),
    ('針', 'shin', 'hari', 'zhēn(针)', 'needle', 'N2', 5, [('金','left','sem'),('十','right','phon')]),
    ('鉄', 'tetsu', None, 'tiě(铁)', 'iron', 'N3', 4, [('金','left','sem'),('失','right','phon')]),
    ('地', 'chi', None, 'dì', 'ground, earth', 'N4', 1, [('土','left','sem'),('也','right','phon')]),
    ('場', 'jou', 'ba', 'chǎng(场)', 'place', 'N4', 3, [('土','left','sem'),('昜','right','phon')]),
    ('名', 'mei', 'na', 'míng', 'name', 'N5', 1, [('夕','top','sem'),('口','bottom','sem')]),
    ('号', 'gou', None, 'hào', 'number, sign', 'N3', 3, [('口','bottom','sem')]),
    ('味', 'mi', 'aji', 'wèi', 'taste', 'N3', 3, [('口','left','sem'),('未','right','phon')]),
    ('和', 'wa', None, 'hé', 'harmony, Japan', 'N3', 2, [('禾','left','phon'),('口','right','sem')]),
    ('加', 'ka', 'kuwa(eru)', 'jiā', 'add', 'N3', 3, [('力','right','sem'),('口','left','sem')]),
    ('相', 'sou', 'ai', 'xiāng', 'mutual, look', 'N3', 3, [('木','left','sem'),('目','right','sem')]),
    ('省', 'sei', 'habu(ku)', 'shěng', 'omit, reflect, province', 'N3', 3, [('少','top','phon'),('目','bottom','sem')]),
    ('聞', 'bun', 'ki(ku)', 'wén(闻)', 'hear, news', 'N5', None, [('門','enclosure','phon'),('耳','inside','sem')]),
    ('買', 'bai', 'ka(u)', 'mǎi(买)', 'buy', 'N5', None, [('貝','bottom','sem')]),
    ('費', 'hi', 'tsui(yasu)', 'fèi(费)', 'expense', 'N3', 4, [('弗','top','phon'),('貝','bottom','sem')]),
    ('貨', 'ka', None, 'huò(货)', 'goods, currency', 'N2', 5, [('化','top','phon'),('貝','bottom','sem')]),
    ('貯', 'cho', None, 'zhù(贮)', 'store, savings', 'N2', None, [('貝','left','sem')]),
    ('線', 'sen', None, 'xiàn(线)', 'line', 'N4', 3, [('糸','left','sem'),('泉','right','phon')]),
    ('紙', 'shi', 'kami', 'zhǐ(纸)', 'paper', 'N5', 2, [('糸','left','sem'),('氏','right','phon')]),
    ('終', 'shuu', 'o(waru)', 'zhōng(终)', 'end', 'N4', 4, [('糸','left','sem'),('冬','right','phon')]),
    ('続', 'zoku', 'tsuzu(ku)', 'xù(续)', 'continue', 'N4', 4, [('糸','left','sem'),('売','right','phon')]),
    ('組', 'so', 'ku(mu)', 'zǔ(组)', 'group, assemble', 'N3', 4, [('糸','left','sem'),('且','right','phon')]),
    ('給', 'kyuu', None, 'jǐ(给)', 'supply, wage', 'N3', 5, [('糸','left','sem'),('合','right','phon')]),
    ('花', 'ka', 'hana', 'huā', 'flower', 'N5', 1, [('⺾','top','sem'),('化','bottom','phon')]),
    ('茶', 'cha', None, 'chá', 'tea', 'N5', 2, [('⺾','top','sem'),('木','bottom','sem')]),
    ('草', 'sou', 'kusa', 'cǎo', 'grass', 'N4', 4, [('⺾','top','sem'),('早','bottom','phon')]),
    ('薬', 'yaku', 'kusuri', 'yào(药)', 'medicine', 'N4', None, [('⺾','top','sem'),('楽','bottom','phon')]),
    ('答', 'tou', 'kota(eru)', 'dá', 'answer', 'N4', 3, [('竹','top','sem'),('合','bottom','phon')]),
    ('第', 'dai', None, 'dì', 'ordinal prefix', 'N3', 4, [('竹','top','sem'),('弟','bottom','phon')]),
    ('筆', 'hitsu', 'fude', 'bǐ(笔)', 'writing brush', 'N2', 5, [('竹','top','sem'),('聿','bottom','sem')]),
    ('雪', 'setsu', 'yuki', 'xuě', 'snow', 'N3', 3, [('雨','top','sem')]),
    ('電', 'den', None, 'diàn(电)', 'electricity', 'N5', None, [('雨','top','sem'),('申','bottom','phon')]),
    ('雲', 'un', 'kumo', 'yún(云)', 'cloud', 'N3', 4, [('雨','top','sem'),('云','bottom','phon')]),
    ('岩', 'gan', 'iwa', 'yán', 'rock', 'N2', 5, [('山','top','sem'),('石','bottom','sem')]),
    ('島', 'tou', 'shima', 'dǎo(岛)', 'island', 'N3', 3, [('鳥','top','sem'),('山','bottom','sem')]),
    ('研', 'ken', 'to(gu)', 'yán', 'polish, research', 'N3', 3, [('石','left','sem'),('开','right','phon')]),
    ('科', 'ka', None, 'kē', 'department, science', 'N3', 3, [('禾','left','sem'),('斗','right','sem')]),
    ('秋', 'shuu', 'aki', 'qiū', 'autumn', 'N4', 3, [('禾','left','sem'),('火','right','phon')]),
    ('種', 'shu', 'tane', 'zhǒng(种)', 'seed, kind', 'N3', 3, [('禾','left','sem'),('重','right','phon')]),
    ('蛍', 'kei', 'hotaru', 'yíng(萤)', 'firefly', 'N1', None, [('虫','bottom','sem')]),
    ('輪', 'rin', 'wa', 'lún(轮)', 'wheel, ring', 'N2', 5, [('車','left','sem'),('侖','right','phon')]),
    ('軽', 'kei', 'karu(i)', 'qīng(轻)', 'light (weight)', 'N3', 4, [('車','left','sem'),('圣','right','phon')]),
    ('間', 'kan', 'aida', 'jiān(间)', 'interval, between', 'N5', None, [('門','enclosure','sem'),('日','inside','sem')]),
    ('開', 'kai', 'hira(ku)', 'kāi(开)', 'open', 'N4', None, [('門','enclosure','sem')]),
    ('閉', 'hei', 'to(jiru)', 'bì(闭)', 'close', 'N3', None, [('門','enclosure','sem'),('才','inside','phon')]),
    ('別', 'betsu', 'waka(reru)', 'bié', 'separate, different', 'N3', 3, [('刀','right','sem')]),
    ('前', 'zen', 'mae', 'qián', 'before, front', 'N5', 1, [('刀','bottom-right','sem')]),
    ('利', 'ri', None, 'lì', 'profit, advantage', 'N2', 4, [('禾','left','sem'),('刀','right','sem')]),
    ('勉', 'ben', None, 'miǎn', 'diligence, exertion', 'N3', 5, [('免','left','phon'),('力','right','sem')]),
    ('動', 'dou', 'ugo(ku)', 'dòng(动)', 'move', 'N4', 2, [('重','left','phon'),('力','right','sem')]),
    ('規', 'ki', None, 'guī(规)', 'standard, rule', 'N2', 5, [('夫','left','phon'),('見','right','sem')]),
    ('視', 'shi', None, 'shì(视)', 'look at, view', 'N2', 4, [('示','left','sem'),('見','right','sem')]),
    ('顔', 'gan', 'kao', 'yán(颜)', 'face', 'N4', None, [('彦','left','phon'),('頁','right','sem')]),
    ('題', 'dai', None, 'tí(题)', 'topic, title', 'N4', 4, [('是','top','phon'),('頁','bottom','sem')]),
    ('願', 'gan', 'nega(u)', 'yuàn(愿)', 'wish, request', 'N3', 5, [('原','left','phon'),('頁','right','sem')]),
    ('理', 'ri', None, 'lǐ', 'logic, reason', 'N3', 3, [('王','left','sem'),('里','right','phon')]),
    ('物', 'butsu', 'mono', 'wù', 'thing', 'N4', 1, [('牛','left','sem'),('勿','right','phon')]),
    ('特', 'toku', None, 'tè', 'special', 'N3', 4, [('牛','left','sem'),('寺','right','phon')]),
    ('猫', 'byou', 'neko', 'māo', 'cat', None, 3, [('⺨','left','sem'),('苗','right','phon')]),
    ('料', 'ryou', None, 'liào', 'fee, materials', 'N3', 4, [('米','left','sem'),('斗','right','sem')]),
    ('飲', 'in', 'no(mu)', 'yǐn(饮)', 'drink', 'N5', None, [('食','left','sem'),('欠','right','phon')]),
    ('飯', 'han', 'meshi', 'fàn(饭)', 'cooked rice, meal', 'N5', None, [('食','left','sem'),('反','right','phon')]),
    ('館', 'kan', None, 'guǎn(馆)', 'building, hall', 'N4', 3, [('食','left','sem'),('官','right','phon')]),
    ('複', 'fuku', None, 'fù(复)', 'duplicate, complex', 'N2', 5, [('衣','left','sem'),('复','right','phon')]),
    ('祖', 'so', None, 'zǔ', 'ancestor', 'N3', 4, [('示','left','sem'),('且','right','phon')]),
    ('社', 'sha', 'yashiro', 'shè', 'shrine, company', 'N4', 3, [('示','left','sem'),('土','right','sem')]),
    ('神', 'shin', 'kami', 'shén', 'god, spirit', 'N3', 3, [('示','left','sem'),('申','right','phon')]),
    ('対', 'tai', None, 'duì(对)', 'opposing, versus', 'N3', 4, [('寸','right','sem')]),
    ('市', 'shi', 'ichi', 'shì', 'city, market', 'N4', 2, [('亠','top','mark'),('巾','bottom','sem')]),
]


def build():
    by_glyph = {d['glyph']: d for d in radicals_raw}
    n_of = lambda g: by_glyph[g]['n'] if g in by_glyph else 9999

    canonical = {}
    for rec in radicals_raw:
        g = rec['glyph']
        target = MERGE_INTO.get(g, g)
        node = canonical.setdefault(target, {
            'id': None, 'glyph': target, 'variants': [], 'isRadical': True,
            'strokeCount': None, 'category': None, 'tier': None,
            'onyomi': None, 'kunyomi': None, 'pinyin': None,
            'meaning': RADICAL_MEANING.get(target), 'n': n_of(target),
        })
        if g != target:
            node['variants'].append(g)
        if rec.get('strokeCount') is not None and node['strokeCount'] is None:
            node['strokeCount'] = rec['strokeCount']
        if rec.get('category') and node['category'] is None:
            node['category'] = rec['category']
            node['tier'] = rec.get('tier')
        if rec.get('onyomi') and node['onyomi'] is None:
            node['onyomi'] = rec['onyomi']
        if rec.get('kunyomi') and node['kunyomi'] is None:
            node['kunyomi'] = rec['kunyomi']
        if rec.get('pinyin') and node['pinyin'] is None:
            node['pinyin'] = rec['pinyin']
        if not node['meaning']:
            node['meaning'] = RADICAL_MEANING.get(target)

    for g, (on, kun, py, meaning, jlpt, hsk) in STANDALONE.items():
        node = canonical.get(g)
        if node is None:
            continue
        node['isCharacter'] = True
        node['onyomi'] = on or node['onyomi']
        node['kunyomi'] = kun or node['kunyomi']
        node['pinyin'] = py or node['pinyin']
        if meaning:
            node['meaning'] = meaning
        node['jlpt'] = jlpt
        node['hsk'] = hsk

    radicals_final = sorted(canonical.values(), key=lambda d: d['n'])
    for i, r in enumerate(radicals_final):
        r['id'] = f"r{i + 1:03d}"
    radical_id_by_glyph = {r['glyph']: r['id'] for r in radicals_final}

    characters_final, compound_id_by_glyph = [], {}
    for i, (glyph, on, kun, py, meaning, jlpt, hsk, comps) in enumerate(COMPOUNDS):
        cid = f"c{i + 1:03d}"
        langs = []
        if on or kun or jlpt:
            langs.append('ja')
        if py or hsk:
            langs.append('zh')
        characters_final.append({
            'id': cid, 'glyph': glyph, 'isCharacter': True, 'isRadical': False,
            'onyomi': on, 'kunyomi': kun, 'pinyin': py, 'meaning': meaning,
            'jlpt': jlpt, 'hsk': hsk, 'langs': langs,
        })
        compound_id_by_glyph[glyph] = cid

    extra_nodes = {}

    def resolve_component_id(glyph):
        glyph = MERGE_INTO.get(glyph, glyph)
        if glyph in radical_id_by_glyph:
            return radical_id_by_glyph[glyph]
        if glyph in compound_id_by_glyph:
            return compound_id_by_glyph[glyph]
        if glyph in extra_nodes:
            return extra_nodes[glyph]['id']
        eid = f"x{len(extra_nodes) + 1:03d}"
        extra_nodes[glyph] = {'id': eid, 'glyph': glyph}
        return eid

    edges_final = []
    for i, (glyph, on, kun, py, meaning, jlpt, hsk, comps) in enumerate(COMPOUNDS):
        cid = f"c{i + 1:03d}"
        for radical_glyph, pos, role in comps:
            edges_final.append({'from': cid, 'to': resolve_component_id(radical_glyph),
                                 'pos': pos, 'role': role})

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
    print(f"radicals={len(result['radicals'])} characters={len(result['characters'])} "
          f"extras={len(result['extras'])} edges={len(result['edges'])}")
    print(f"-> {OUT_PATH}")
