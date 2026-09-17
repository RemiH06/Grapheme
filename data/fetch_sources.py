# -*- coding: utf-8 -*-
"""
Descarga (una sola vez) los cuatro datasets abiertos que alimentan el
catalogo completo de kanji/hanzi. Si el archivo ya existe en
data/sources/ no se vuelve a descargar -- borralo a mano si quieres
refrescarlo.

Fuentes:
  - kanji-jouyou.json: los 2136 kanji joyo (MEXT) con JLPT, grado,
    frecuencia real (corpus de periodico) y lecturas.
    https://github.com/davidluzgouveia/kanji-data (MIT)
  - mega_hanzi_compilation.csv: ~11k caracteres chinos con nivel HSK
    3.0, frecuencia real (Jun Da, corpus moderno de ~200M caracteres),
    pinyin y descomposicion en componentes.
    https://github.com/alyssabedard/chinese-hsk-and-frequency-lists
  - dictionary.txt (Make Me a Hanzi): descomposicion IDS + etimologia
    (marca componente semantico/fonetico) para ~9500 caracteres. Fuente
    principal de descomposicion.
    https://github.com/skishore/makemeahanzi (MIT)
  - kanjivg.xml (KanjiVG): descomposicion posicional real (izquierda/
    derecha/arriba/abajo/etc.) especifica de Japon, para ~6700 kanji
    incluyendo formas shinjitai que las fuentes de origen chino no
    cubren (図, 対, 悪, 様...). Respaldo cuando makemeahanzi y
    mega_hanzi no tienen el caracter.
    https://github.com/KanjiVG/kanjivg (CC BY-SA 3.0)
  - graphics.txt (Make Me a Hanzi): trazos reales por caracter (orden +
    linea central de cada trazo, campo "medians"), para ~9500
    caracteres. KanjiVG es de origen japones y no cubre bien los
    simplificados que se alejaron mucho de su forma tradicional (ej.
    飞 vs 飛); graphics.txt si, porque es un dataset chino. Usado por
    data/build_strokes.py como respaldo cuando KanjiVG no tiene el
    caracter.
    https://github.com/skishore/makemeahanzi (MIT)
"""
import gzip
import urllib.request
from pathlib import Path

SOURCES_DIR = Path(__file__).resolve().parent / "sources"

FILES = {
    "kanji-jouyou.json": "https://raw.githubusercontent.com/davidluzgouveia/kanji-data/master/kanji-jouyou.json",
    "mega_hanzi_compilation.csv": "https://raw.githubusercontent.com/alyssabedard/chinese-hsk-and-frequency-lists/master/mega_hanzi_compilation.csv",
    "makemeahanzi_dictionary.txt": "https://raw.githubusercontent.com/skishore/makemeahanzi/master/dictionary.txt",
    "makemeahanzi_graphics.txt": "https://raw.githubusercontent.com/skishore/makemeahanzi/master/graphics.txt",
}

# Version fija del release de KanjiVG (no "latest" para que la build sea
# reproducible sin que un release nuevo cambie el dataset por sorpresa).
KANJIVG_URL = "https://github.com/KanjiVG/kanjivg/releases/download/r20250816/kanjivg-20250816.xml.gz"


def fetch_all():
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        dest = SOURCES_DIR / name
        if dest.exists():
            print(f"ya existe: {name}")
            continue
        print(f"descargando {name} ...")
        urllib.request.urlretrieve(url, dest)
        print(f"  -> {dest.stat().st_size} bytes")

    kanjivg_dest = SOURCES_DIR / "kanjivg.xml"
    if kanjivg_dest.exists():
        print("ya existe: kanjivg.xml")
    else:
        print("descargando kanjivg.xml.gz ...")
        gz_path = SOURCES_DIR / "kanjivg.xml.gz"
        urllib.request.urlretrieve(KANJIVG_URL, gz_path)
        with gzip.open(gz_path, "rt", encoding="utf-8") as f_in, open(kanjivg_dest, "w", encoding="utf-8") as f_out:
            f_out.write(f_in.read())
        gz_path.unlink()
        print(f"  -> {kanjivg_dest.stat().st_size} bytes (descomprimido)")


if __name__ == "__main__":
    fetch_all()
