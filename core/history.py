"""Persistência local do histórico de downloads (SQLite)."""

import sqlite3
from datetime import datetime
from pathlib import Path

from config import APP_DATA_DIR, DEFAULT_HISTORY_LIMIT


class DownloadHistory:
    def __init__(self, database_path=None, limit=DEFAULT_HISTORY_LIMIT):
        self.database_path = Path(database_path or APP_DATA_DIR / "history.sqlite3")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.limit = max(1, int(limit))
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    quality TEXT NOT NULL,
                    status TEXT NOT NULL,
                    filename TEXT,
                    error TEXT,
                    completed_at TEXT NOT NULL
                )
                """
            )

    def add(self, job, result):
        status = "completed" if result.get("success") else (
            "cancelled" if result.get("cancelled") else "failed"
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO downloads
                    (url, title, media_type, quality, status, filename, error, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["url"],
                    result.get("title") or job.get("title") or job["url"],
                    job["media_type"],
                    job["quality"] if job["media_type"] == "video" else "mp3",
                    status,
                    result.get("filename"),
                    result.get("error"),
                    datetime.now().astimezone().isoformat(timespec="seconds"),
                ),
            )
            connection.execute(
                "DELETE FROM downloads WHERE id NOT IN "
                "(SELECT id FROM downloads ORDER BY id DESC LIMIT ?)",
                (self.limit,),
            )

    def recent(self, limit=None):
        row_limit = max(1, min(int(limit or self.limit), self.limit))
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM downloads ORDER BY id DESC LIMIT ?", (row_limit,)
            ).fetchall()
        return [dict(row) for row in rows]
