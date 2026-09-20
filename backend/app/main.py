"""
API de Grapheme.

Sirve el grafo estatico (radicales, caracteres compuestos, aristas,
generado por data/build_dataset.py a partir de Pictograms.xlsx) y las
notas personales por nodo, guardadas en SQLite.

Ejecutar:
    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8055

Docs interactivas: http://localhost:8055/docs
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import db

DATA_PATH = Path(__file__).resolve().parent / "data" / "graph_data.json"
STROKES_PATH = Path(__file__).resolve().parent / "data" / "strokes.json"
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
MANUAL_COMPONENTS_PATH = _DATA_DIR / "radical_components_manual.json"
STROKE_DERIVATION_PATH = _DATA_DIR / "stroke_derivation_manual.json"

# Los del bloque oficial "CJK Strokes" (U+31C0-U+31E5) que ya NO
# duplican a un radical existente (unica fuente de verdad para esta
# lista: el frontend la consume via GET /admin/strokes, no tiene su
# propia copia). Excluidos hasta ahora, todos por duplicar visualmente
# un radical de un solo trazo: ㇐=一, ㇑=｜, ㇔=丶, ㇒=ノ, ㇚=亅 (horizontal,
# vertical, punto, diagonal-izquierda, gancho vertical), y ㇠=乙 (HXWG,
# el mismo doblez compuesto que 乙 -- confirmado visualmente).
CJK_STROKES = [
    '㇀', '㇁', '㇂', '㇃', '㇄', '㇅', '㇆', '㇇', '㇈', '㇉', '㇊', '㇋', '㇌', '㇍', '㇎', '㇏',
    '㇓', '㇕', '㇖', '㇗', '㇘', '㇙', '㇛', '㇜', '㇝', '㇞', '㇟',
    '㇡', '㇢', '㇣', '㇤', '㇥',
]

app = FastAPI(
    title="Grapheme API",
    description="Grafo de radicales kanji/hanzi y notas personales por nodo",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5190", "http://127.0.0.1:5190"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_graph_cache = None
_strokes_cache = None


@app.on_event("startup")
def startup():
    db.init_db()
    global _graph_cache, _strokes_cache
    if not DATA_PATH.exists():
        raise RuntimeError(
            f"No se encontro {DATA_PATH}. Corre 'python data/build_dataset.py' "
            "desde la raiz del proyecto antes de levantar la API."
        )
    with open(DATA_PATH, encoding="utf-8") as f:
        _graph_cache = json.load(f)
    _strokes_cache = {}
    if STROKES_PATH.exists():
        with open(STROKES_PATH, encoding="utf-8") as f:
            _strokes_cache = json.load(f)


@app.get("/")
def root():
    return {"name": "Grapheme API", "status": "ok", "docs": "/docs"}


@app.get("/graph")
def get_graph():
    """Radicales + caracteres compuestos + componentes fonéticos + aristas."""
    return _graph_cache


@app.get("/strokes")
def get_strokes():
    """Trazos reales (KanjiVG) por glifo del catalogo: {glifo: [[[x,y]x12] x trazos]},
    normalizados a un cuadrado 0-1 compartido por todo el glifo. Solo cubre
    los glifos que KanjiVG tiene (ver data/build_strokes.py); un glifo
    ausente aqui no tiene datos de trazo reales, no se debe inventar."""
    return _strokes_cache


class NoteIn(BaseModel):
    text: str
    glyph: str | None = None


@app.get("/notes")
def notes_list():
    """Todas las notas no vacias, mas recientes primero (la 'bóveda')."""
    return db.list_notes()


@app.get("/notes/{node_id}")
def notes_get(node_id: str):
    note = db.get_note(node_id)
    if note is None:
        return {"id": node_id, "glyph": None, "text": "", "updated_at": None}
    return note


@app.put("/notes/{node_id}")
def notes_put(node_id: str, body: NoteIn):
    updated_at = datetime.now(timezone.utc).isoformat()
    return db.upsert_note(node_id, body.glyph, body.text, updated_at)


# ---------------------------------------------------------------------------
# Lista de estudio + repeticion espaciada
# ---------------------------------------------------------------------------
class StudyAddIn(BaseModel):
    glyph: str | None = None


class StudyAddManyIn(BaseModel):
    items: list[dict]  # [{"id": "...", "glyph": "..."}, ...]


class ReviewIn(BaseModel):
    grade: int  # 0 otra vez, 1 dificil, 2 bien, 3 facil
    glyph: str | None = None


@app.get("/study/list")
def study_list():
    """Todos los nodos en la lista de estudio, con su estado SM-2."""
    return db.list_study_list()


@app.get("/study/due")
def study_due():
    """Los que ya tocan repasar hoy (next_review <= hoy)."""
    return db.list_due()


@app.get("/study/{node_id}")
def study_get(node_id: str):
    srs = db.get_srs(node_id)
    return srs or {"id": node_id, "in_study": False}


@app.post("/study/add-many")
def study_add_many(body: StudyAddManyIn):
    # declarada ANTES de /study/{node_id}: FastAPI matchea rutas en orden
    # de declaracion, asi que si esto fuera despues, "add-many" se leeria
    # como un node_id y nunca llegaria aqui.
    items = [(it["id"], it.get("glyph")) for it in body.items]
    db.add_many_to_study(items)
    return {"added": len(items)}


@app.post("/study/{node_id}")
def study_add(node_id: str, body: StudyAddIn):
    db.add_to_study(node_id, body.glyph)
    return db.get_srs(node_id)


@app.delete("/study/{node_id}")
def study_remove(node_id: str):
    db.remove_from_study(node_id)
    return {"ok": True}


@app.post("/study/{node_id}/review")
def study_review(node_id: str, body: ReviewIn):
    if body.grade not in (0, 1, 2, 3):
        raise HTTPException(status_code=422, detail="grade debe ser 0, 1, 2 o 3")
    return db.record_review(node_id, body.glyph, body.grade)


# ---------------------------------------------------------------------------
# Curacion manual de componentes de radicales (herramienta local, no para
# el usuario final: ver frontend/src/components/RadicalCurator.jsx, montada
# en /?curate=radicals). Guarda en data/radical_components_manual.json, que
# data/build_dataset.py lee en la siguiente corrida para reemplazar la
# descomposicion automatica de ese radical (ver seccion 11 de
# docs/METODOLOGIA.md: la fuente etimologica marca 111 de los 242 radicales
# como "pictograficos" y por eso atomicos, correcto para la mayoria pero no
# para todos, y no hay forma automatica de distinguir los dos casos).
# ---------------------------------------------------------------------------
def _nodes_by_id():
    by_id = {}
    for coll in ("radicals", "characters", "extras"):
        for n in _graph_cache.get(coll, []):
            by_id[n["id"]] = n
    return by_id


def _load_manual_components():
    if not MANUAL_COMPONENTS_PATH.exists():
        return {}
    with open(MANUAL_COMPONENTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_manual_components(data):
    MANUAL_COMPONENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANUAL_COMPONENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


@app.get("/admin/radicals")
def admin_radicals():
    """Los 242 radicales con sus componentes actuales (automaticos o ya
    curados a mano) y la entrada manual guardada, si existe (None = no
    revisado todavia; lista vacia = revisado y confirmado atomico)."""
    by_id = _nodes_by_id()
    manual = _load_manual_components()
    out = []
    for r in _graph_cache.get("radicals", []):
        comp_edges = [e for e in _graph_cache["edges"] if e["to"] == r["id"]]
        components = [
            {"id": other["id"], "glyph": other["glyph"], "role": e["role"]}
            for e in comp_edges
            if (other := by_id.get(e["from"]))
        ]
        out.append({
            "id": r["id"],
            "glyph": r["glyph"],
            "meaning": r["meaning"],
            "strokeCount": r["strokeCount"],
            "components": components,
            "manual": manual.get(r["glyph"]),
        })
    return out


class RadicalComponentsIn(BaseModel):
    components: list[str]


@app.post("/admin/radical-components/{glyph}")
def admin_set_radical_components(glyph: str, body: RadicalComponentsIn):
    manual = _load_manual_components()
    manual[glyph] = body.components
    _save_manual_components(manual)
    return {"glyph": glyph, "components": body.components}


@app.delete("/admin/radical-components/{glyph}")
def admin_clear_radical_components(glyph: str):
    manual = _load_manual_components()
    manual.pop(glyph, None)
    _save_manual_components(manual)
    return {"ok": True}


@app.get("/admin/auxiliares")
def admin_auxiliares():
    """Los nodos 'extra' que son componentes reales sin pronunciacion y
    fuera de los 242 (todos menos los 4 'isExample', que si tienen
    pronunciacion real: esos no son auxiliares, son ejemplos ilustrativos
    de radicales aislados, ver seccion 4.1 de docs/METODOLOGIA.md).
    Reusa /admin/radical-components/{glyph} para editar sus componentes
    (ya soporta cualquier glifo, no solo los 242, desde la seccion 11)."""
    by_id = _nodes_by_id()
    manual = _load_manual_components()
    out = []
    for x in _graph_cache.get("extras", []):
        if x.get("isExample") or x.get("pinyin"):
            continue
        comp_edges = [e for e in _graph_cache["edges"] if e["to"] == x["id"]]
        components = [
            {"id": other["id"], "glyph": other["glyph"], "role": e["role"]}
            for e in comp_edges
            if (other := by_id.get(e["from"]))
        ]
        out.append({
            "id": x["id"],
            "glyph": x["glyph"],
            "meaning": None,
            "strokeCount": None,
            "components": components,
            "manual": manual.get(x["glyph"]),
        })
    return out


def _load_stroke_derivations():
    if not STROKE_DERIVATION_PATH.exists():
        return {}
    with open(STROKE_DERIVATION_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_stroke_derivations(data):
    STROKE_DERIVATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STROKE_DERIVATION_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


@app.get("/admin/strokes")
def admin_strokes():
    """Los 33 trazos del bloque oficial CJK Strokes (ver CJK_STROKES
    arriba), con el radical del que ya se dijo que derivan, si existe."""
    derivations = _load_stroke_derivations()
    return [{"glyph": g, "derivesFrom": derivations.get(g)} for g in CJK_STROKES]


class StrokeDerivationIn(BaseModel):
    derivesFrom: str | None = None


@app.post("/admin/stroke-derivation/{glyph}")
def admin_set_stroke_derivation(glyph: str, body: StrokeDerivationIn):
    derivations = _load_stroke_derivations()
    if body.derivesFrom:
        derivations[glyph] = body.derivesFrom
    else:
        derivations.pop(glyph, None)
    _save_stroke_derivations(derivations)
    return {"glyph": glyph, "derivesFrom": body.derivesFrom}


@app.get("/admin/kanji")
def admin_kanji():
    """Los 3668 caracteres del catalogo (jouyou+HSK), solo lo minimo
    para ofrecerlos como opcion en el buscador de componentes -- a
    veces la descomposicion real de un radical/auxiliar SI es un kanji
    completo, no solo otro radical (ej. 巷 usa 共, que ni es de los 242
    ni es un auxiliar sin pronunciacion: es un caracter real). No se
    revisan/editan aqui, solo se listan para poder elegirlos."""
    return [
        {"id": c["id"], "glyph": c["glyph"], "meaning": c["meaning"]}
        for c in _graph_cache.get("characters", [])
    ]
