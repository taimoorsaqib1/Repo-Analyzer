"""
Workspace persistence — saves named analysis sessions using SQLite so users
never need to re-clone or re-index the same repositories twice.

Schema
------
  workspaces
    name        TEXT PRIMARY KEY   -- user-defined workspace label
    repos_json  TEXT               -- JSON array of repo metadata dicts
    collection  TEXT               -- ChromaDB collection name
    created_at  TEXT               -- ISO 8601 timestamp (UTC)
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_DB_PATH = Path(__file__).parent.parent / "data" / "workspaces.db"


def _get_conn() -> sqlite3.Connection:
    """Open (and initialise) the SQLite database, creating it if needed."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(_DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            name        TEXT PRIMARY KEY,
            repos_json  TEXT NOT NULL,
            collection  TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)
    con.commit()
    return con


def save_workspace(name: str, repos: list[dict], collection: str) -> None:
    """Create or overwrite a named workspace record."""
    with _get_conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO workspaces VALUES (?, ?, ?, ?)",
            (
                name,
                json.dumps(repos),
                collection,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def list_workspaces() -> list[dict]:
    """Return all saved workspaces, newest first."""
    with _get_conn() as con:
        rows = con.execute(
            "SELECT name, repos_json, collection, created_at "
            "FROM workspaces ORDER BY created_at DESC"
        ).fetchall()
    return [
        {
            "name": r["name"],
            "repos": json.loads(r["repos_json"]),
            "collection": r["collection"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def load_workspace(name: str) -> Optional[dict]:
    """Return a single workspace by name, or None if not found."""
    with _get_conn() as con:
        row = con.execute(
            "SELECT * FROM workspaces WHERE name = ?", (name,)
        ).fetchone()
    if not row:
        return None
    return {
        "name": row["name"],
        "repos": json.loads(row["repos_json"]),
        "collection": row["collection"],
        "created_at": row["created_at"],
    }


def delete_workspace(name: str) -> bool:
    """Delete a workspace record. Returns True if a row was deleted."""
    with _get_conn() as con:
        cur = con.execute("DELETE FROM workspaces WHERE name = ?", (name,))
        return cur.rowcount > 0
