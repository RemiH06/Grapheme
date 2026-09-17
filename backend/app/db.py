"""
Almacen de notas personales y de progreso de estudio por nodo (radical,
kanji/hanzi o componente).

Un archivo SQLite en disco (backend/app/data/notes.db), sin servidor de
base de datos aparte: el dataset del grafo es estatico (viene de
graph_data.json) y lo unico que de verdad necesita persistencia es lo
que el usuario escribe y su progreso de repaso.
"""
import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "notes.db"

# SM-2 simplificado (4 niveles en vez de la escala 0-5 original de
# SuperMemo): 0=otra vez, 1=dificil, 2=bien, 3=facil.
MIN_EASE = 1.3
DEFAULT_EASE = 2.5


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
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS srs (
            id TEXT PRIMARY KEY,
            glyph TEXT,
            ease REAL NOT NULL DEFAULT {DEFAULT_EASE},
            interval_days REAL NOT NULL DEFAULT 0,
            reps INTEGER NOT NULL DEFAULT 0,
            next_review TEXT NOT NULL,
            last_reviewed TEXT,
            added_at TEXT NOT NULL
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


# ---------------------------------------------------------------------------
# Lista de estudio + repeticion espaciada (SM-2 simplificado: 4 niveles en
# vez de la escala 0-5 original -- 0=otra vez, 1=dificil, 2=bien, 3=facil).
# ---------------------------------------------------------------------------
def add_to_study(node_id, glyph):
    """Agrega un nodo a la lista de estudio si no estaba ya (no reinicia
    el progreso de uno que ya se estaba repasando)."""
    today = date.today().isoformat()
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO srs (id, glyph, ease, interval_days, reps, next_review, last_reviewed, added_at)
        VALUES (?, ?, ?, 0, 0, ?, NULL, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        (node_id, glyph, DEFAULT_EASE, today, today),
    )
    conn.commit()
    conn.close()


def add_many_to_study(items):
    """items: lista de (node_id, glyph). Usado por "agregar todos" desde
    el panel (ej. todos los caracteres que usan un radical)."""
    today = date.today().isoformat()
    conn = get_connection()
    conn.executemany(
        """
        INSERT INTO srs (id, glyph, ease, interval_days, reps, next_review, last_reviewed, added_at)
        VALUES (?, ?, ?, 0, 0, ?, NULL, ?)
        ON CONFLICT(id) DO NOTHING
        """,
        [(node_id, glyph, DEFAULT_EASE, today, today) for node_id, glyph in items],
    )
    conn.commit()
    conn.close()


def remove_from_study(node_id):
    conn = get_connection()
    conn.execute("DELETE FROM srs WHERE id = ?", (node_id,))
    conn.commit()
    conn.close()


def get_srs(node_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM srs WHERE id = ?", (node_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_study_list():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM srs ORDER BY next_review ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_due():
    today = date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM srs WHERE next_review <= ? ORDER BY next_review ASC", (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_review(node_id, glyph, grade):
    """grade: 0 otra vez, 1 dificil, 2 bien, 3 facil. SM-2 simplificado:
    "otra vez" resetea reps y castiga la facilidad; el resto avanza el
    intervalo (1 dia -> 6 dias -> intervalo*facilidad...) y solo mueve
    la facilidad hacia arriba o abajo segun que tan facil resulto."""
    today = date.today().isoformat()
    conn = get_connection()
    row = conn.execute("SELECT * FROM srs WHERE id = ?", (node_id,)).fetchone()
    ease = row["ease"] if row else DEFAULT_EASE
    interval = row["interval_days"] if row else 0
    reps = row["reps"] if row else 0

    if grade <= 0:
        reps = 0
        interval = 1
        ease = max(MIN_EASE, ease - 0.2)
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = round(interval * ease, 1)
        reps += 1
        if grade == 1:
            ease = max(MIN_EASE, ease - 0.15)
        elif grade == 3:
            ease = ease + 0.15

    next_review = date.fromordinal(date.today().toordinal() + max(0, round(interval))).isoformat()
    conn.execute(
        """
        INSERT INTO srs (id, glyph, ease, interval_days, reps, next_review, last_reviewed, added_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET glyph = excluded.glyph, ease = excluded.ease,
            interval_days = excluded.interval_days, reps = excluded.reps,
            next_review = excluded.next_review, last_reviewed = excluded.last_reviewed
        """,
        (node_id, glyph, ease, interval, reps, next_review, today, today),
    )
    conn.commit()
    result = dict(conn.execute("SELECT * FROM srs WHERE id = ?", (node_id,)).fetchone())
    conn.close()
    return result
