import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "painel.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.now().isoformat(timespec="seconds")


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                registration TEXT NOT NULL,
                status TEXT NOT NULL,
                destination TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                called_at TEXT
            )
            """
        )
        conn.commit()


def _row_to_dict(row):
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def create_call(name, registration):
    now = _now()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO calls (name, registration, status, destination, created_at, updated_at)
            VALUES (?, ?, 'waiting', NULL, ?, ?)
            """,
            (name.strip(), registration.strip(), now, now),
        )
        conn.commit()
        return cursor.lastrowid


def update_call(call_id, name, registration):
    now = _now()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE calls
            SET name = ?, registration = ?, updated_at = ?
            WHERE id = ?
            """,
            (name.strip(), registration.strip(), now, call_id),
        )
        conn.commit()
        return cursor.rowcount


def dispatch_call(call_id, destination):
    now = _now()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE calls
            SET status = 'called', destination = ?, updated_at = ?, called_at = ?
            WHERE id = ?
            """,
            (destination.strip(), now, now, call_id),
        )
        conn.commit()
        return cursor.rowcount


def list_waiting():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM calls
            WHERE status = 'waiting'
            ORDER BY created_at ASC
            """
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def list_history(limit):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM calls
            WHERE status = 'called'
            ORDER BY called_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_call(call_id):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM calls
            WHERE id = ?
            """,
            (call_id,),
        ).fetchone()
    return _row_to_dict(row)
