"""Тесты слоя БД (db.py): параметризованные запросы, аудит."""
import sqlite3

import pytest

from FileManager.db import Database


@pytest.fixture()
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    yield database
    database.conn.close()


@pytest.fixture()
def user(db):
    db.add_user("alice", "scrypt$16384$8$1$00$00")
    return db.get_user("alice")


class TestUsers:
    def test_add_and_get(self, db, user):
        assert user["username"] == "alice"

    def test_get_missing(self, db):
        assert db.get_user("nobody") is None

    def test_duplicate_username(self, db):
        db.add_user("bob", "h1")
        with pytest.raises(sqlite3.IntegrityError):
            db.add_user("bob", "h2")


class TestFileTracking:
    def test_track_insert_then_update(self, db, user):
        fid = db.track(user["id"], "a.txt", 10)
        db.track(user["id"], "a.txt", 25)  # тот же location -> UPDATE
        rows = db.list_files(user["id"])
        assert len(rows) == 1
        assert rows[0]["size"] == 25
        assert rows[0]["location"] == "a.txt"

    def test_untrack_marks_deleted(self, db, user):
        db.track(user["id"], "a.txt", 10)
        assert db.untrack(user["id"], "a.txt") is not None
        assert db.list_files(user["id"]) == []
        assert db.untrack(user["id"], "ghost") is None

    def test_files_isolated_per_user(self, db, user):
        db.add_user("mallory", "h2")
        other = db.get_user("mallory")
        db.track(user["id"], "a.txt", 1)
        assert db.list_files(other["id"]) == []


class TestAuditLog:
    def test_history_newest_first_and_limit(self, db, user):
        fid = db.track(user["id"], "a.txt", 1)
        db.log(user["id"], "create", fid)
        db.log(user["id"], "read", fid)
        db.log(user["id"], "delete", None)
        history = db.history(user["id"], 2)
        assert len(history) == 2
        assert history[0]["operation_type"] == "delete"
        assert history[1]["operation_type"] == "read"

    def test_unknown_operation_rejected_by_schema(self, db, user):
        with pytest.raises(sqlite3.IntegrityError):
            db.log(user["id"], "hacked", None, "' OR 1=1 --")
