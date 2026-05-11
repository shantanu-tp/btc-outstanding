"""SQLite-backed comments store."""

from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass

DB_PATH = Path(__file__).parent.parent / "comments.db"


@dataclass
class Comment:
    id: int
    client_id: str
    author: str
    comment: str
    created_at: str
    is_pinned: bool


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id   TEXT    NOT NULL,
                author      TEXT    NOT NULL,
                comment     TEXT    NOT NULL,
                created_at  TEXT    NOT NULL,
                is_pinned   INTEGER NOT NULL DEFAULT 0
            )
        """)
        con.commit()


def add_comment(client_id: str, author: str, text: str) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO comments (client_id, author, comment, created_at, is_pinned) "
            "VALUES (?, ?, ?, ?, 0)",
            (str(client_id), author, text, datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")),
        )
        con.commit()


def get_comments(client_id: str) -> list[Comment]:
    with sqlite3.connect(DB_PATH) as con:
        rows = con.execute(
            "SELECT id, client_id, author, comment, created_at, is_pinned "
            "FROM comments WHERE client_id = ? ORDER BY is_pinned DESC, created_at DESC",
            (str(client_id),),
        ).fetchall()
    return [Comment(*r) for r in rows]


def toggle_pin(comment_id: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "UPDATE comments SET is_pinned = CASE WHEN is_pinned=1 THEN 0 ELSE 1 END "
            "WHERE id = ?",
            (comment_id,),
        )
        con.commit()


def delete_comment(comment_id: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
        con.commit()
