"""
Almacen de notas personales por nodo (radical, kanji/hanzi o componente).

Un archivo SQLite en disco (backend/app/data/notes.db), sin servidor de
base de datos aparte: el dataset del grafo es estatico (viene de
graph_data.json) y lo unico que de verdad necesita persistencia es lo
que el usuario escribe.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "notes.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            glyph TEXT,
            text TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def list_notes():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, glyph, text, updated_at FROM notes WHERE text != '' ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_note(node_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, glyph, text, updated_at FROM notes WHERE id = ?", (node_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_note(node_id, glyph, text, updated_at):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO notes (id, glyph, text, updated_at) VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET glyph = excluded.glyph,
            text = excluded.text, updated_at = excluded.updated_at
        """,
        (node_id, glyph, text, updated_at),
    )
    conn.commit()
    conn.close()
    return {"id": node_id, "glyph": glyph, "text": text, "updated_at": updated_at}
