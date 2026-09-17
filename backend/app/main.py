"""
API de Atlas de Radicales.

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

app = FastAPI(
    title="Atlas de Radicales API",
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


@app.on_event("startup")
def startup():
    db.init_db()
    global _graph_cache
    if not DATA_PATH.exists():
        raise RuntimeError(
            f"No se encontro {DATA_PATH}. Corre 'python data/build_dataset.py' "
            "desde la raiz del proyecto antes de levantar la API."
        )
    with open(DATA_PATH, encoding="utf-8") as f:
        _graph_cache = json.load(f)


@app.get("/")
def root():
    return {"name": "Atlas de Radicales API", "status": "ok", "docs": "/docs"}


@app.get("/graph")
def get_graph():
    """Radicales + caracteres compuestos + componentes fonéticos + aristas."""
    return _graph_cache


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
