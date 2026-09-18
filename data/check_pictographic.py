import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import build_dataset as bd

mega_by_glyph = bd.load_mega_hanzi()
mmh_by_glyph = bd.load_mmh_dictionary()
kanjivg_by_glyph = bd.load_kanjivg()

lines = []
for g in ['竜', '魚', '岡', '龍', '鱼']:
    mmh = mmh_by_glyph.get(g)
    pic = bd.is_pictographic(g, mmh_by_glyph)
    lines.append(f"\n{g}:")
    lines.append(f"  is_pictographic={pic}")
    if mmh:
        lines.append(f"  mmh entry: decomposition={mmh.get('decomposition')!r} etymology={mmh.get('etymology')} radical={mmh.get('radical')!r}")
    else:
        lines.append("  no mmh entry")
    comps = list(bd.components_of(g, mmh_by_glyph, mega_by_glyph, kanjivg_by_glyph))
    lines.append(f"  components_of (raw, ignoring is_pictographic): {comps}")

Path('check_pictographic_out.txt').write_text('\n'.join(lines), encoding='utf-8')
print('done')
