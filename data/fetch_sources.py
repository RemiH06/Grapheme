# -*- coding: utf-8 -*-
"""
Descarga (una sola vez) los tres datasets abiertos que alimentan el
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
    (marca componente semantico/fonetico) para ~9500 caracteres, usado
    como respaldo cuando un kanji joyo no aparece en el csv anterior
    (formas shinjitai japonesas que no coinciden con el simplificado
    ni el tradicional chino).
    https://github.com/skishore/makemeahanzi (MIT)
"""
import urllib.request
from pathlib import Path

SOURCES_DIR = Path(__file__).resolve().parent / "sources"

FILES = {
    "kanji-jouyou.json": "https://raw.githubusercontent.com/davidluzgouveia/kanji-data/master/kanji-jouyou.json",
    "mega_hanzi_compilation.csv": "https://raw.githubusercontent.com/alyssabedard/chinese-hsk-and-frequency-lists/master/mega_hanzi_compilation.csv",
    "makemeahanzi_dictionary.txt": "https://raw.githubusercontent.com/skishore/makemeahanzi/master/dictionary.txt",
}


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


if __name__ == "__main__":
    fetch_all()
