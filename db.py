"""Слой БД: только параметризованные запросы, никакой конкатенации SQL."""
import os
import sqlite3

OPS = ("create", "read", "modify", "delete", "archive", "extract",
       "login", "login_failed", "denied")
_OPS_SQL = ", ".join(f"'{o}'" for o in OPS)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS Files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    size INTEGER,
    location TEXT NOT NULL,
    deleted INTEGER NOT NULL DEFAULT 0,
    owner_id INTEGER NOT NULL REFERENCES Users(id)
);
CREATE TABLE IF NOT EXISTS Operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    operation_type TEXT NOT NULL CHECK (operation_type IN ({_OPS_SQL})),
    file_id INTEGER REFERENCES Files(id),
    user_id INTEGER REFERENCES Users(id),
    details TEXT
);
"""


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def _run(self, sql, params=()):
        with self.conn:  # commit / rollback
            return self.conn.execute(sql, params)

    def add_user(self, username, pw_hash):
        return self._run("INSERT INTO Users (username, password_hash) VALUES (?, ?)",
                         (username, pw_hash)).lastrowid

    def get_user(self, username):
        return self.conn.execute("SELECT * FROM Users WHERE username = ?", (username,)).fetchone()

    def _active(self, user_id, location):
        return self.conn.execute(
            "SELECT id FROM Files WHERE owner_id = ? AND location = ? AND deleted = 0",
            (user_id, location)).fetchone()

    def track(self, user_id, location, size):
        row = self._active(user_id, location)
        if row:
            self._run("UPDATE Files SET size = ? WHERE id = ?", (size, row["id"]))
            return row["id"]
        return self._run(
            "INSERT INTO Files (filename, size, location, owner_id) VALUES (?, ?, ?, ?)",
            (os.path.basename(location), size, location, user_id)).lastrowid

    def untrack(self, user_id, location):
        row = self._active(user_id, location)
        if not row:
            return None
        self._run("UPDATE Files SET deleted = 1 WHERE id = ?", (row["id"],))
        return row["id"]

    def log(self, user_id, op, file_id=None, details=None):
        self._run("INSERT INTO Operations (operation_type, file_id, user_id, details) "
                  "VALUES (?, ?, ?, ?)", (op, file_id, user_id, details))

    def list_files(self, user_id):
        return self.conn.execute(
            "SELECT id, size, created_at, location FROM Files "
            "WHERE owner_id = ? AND deleted = 0 ORDER BY location", (user_id,)).fetchall()

    def history(self, user_id, limit=20):
        return self.conn.execute(
            "SELECT o.timestamp, o.operation_type, f.location, o.details "
            "FROM Operations o LEFT JOIN Files f ON f.id = o.file_id "
            "WHERE o.user_id = ? ORDER BY o.id DESC LIMIT ?", (user_id, limit)).fetchall()
