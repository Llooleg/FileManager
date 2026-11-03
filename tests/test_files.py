"""Тесты рабочей области пользователя (files.py): CRUD, JSON/XML, ZIP, аудит."""
import json

import pytest

from FileManager import files as files_mod
from FileManager.db import Database
from FileManager.files import Workspace


@pytest.fixture()
def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    yield database
    database.conn.close()


@pytest.fixture()
def ws(db, tmp_path):
    db.add_user("alice", "scrypt$16384$8$1$00$00")
    user = db.get_user("alice")
    return Workspace(db, user, tmp_path / "ws")


class TestTextOps:
    def test_write_read_roundtrip(self, ws):
        ws.write_text("hello.txt", "привет, мир")
        assert ws.read_text("hello.txt") == "привет, мир"

    def test_append(self, ws):
        ws.write_text("log.txt", "one")
        ws.write_text("log.txt", " two", append=True)
        assert ws.read_text("log.txt") == "one two"

    def test_read_missing(self, ws):
        with pytest.raises(FileNotFoundError):
            ws.read_text("missing.txt")

    def test_escape_outside_workspace_denied(self, ws):
        with pytest.raises(PermissionError):
            ws.write_text("../escape.txt", "x")

    def test_delete_untracks_file(self, ws):
        ws.write_text("gone.txt", "x")
        ws.delete("gone.txt")
        assert ws.db.list_files(ws.user["id"]) == []
        with pytest.raises(FileNotFoundError):
            ws.read_text("gone.txt")

    def test_size_limit(self, ws, monkeypatch):
        monkeypatch.setattr(files_mod, "MAX_IO", 8)
        with pytest.raises(ValueError):
            ws.write_text("big.txt", "x" * 16)

    def test_audit_logged(self, ws):
        ws.write_text("a.txt", "data")
        ws.read_text("a.txt")
        kinds = [r["operation_type"] for r in ws.db.history(ws.user["id"], 10)]
        assert "create" in kinds and "read" in kinds


class TestFormats:
    def test_json_roundtrip(self, ws):
        ws.write_json("conf.json", '{"имя": "secfm", "n": 42}')
        assert ws.read_json("conf.json") == {"имя": "secfm", "n": 42}

    def test_invalid_json_rejected(self, ws):
        with pytest.raises(json.JSONDecodeError):
            ws.write_json("bad.json", "{not json")

    def test_xml_roundtrip(self, ws):
        ws.write_xml("doc.xml", "<root><item>1</item></root>")
        out = ws.read_xml("doc.xml")
        assert "<root>" in out and "<item>1</item>" in out

    def test_xxe_doctype_rejected(self, ws):
        with pytest.raises(ValueError):
            ws.write_xml("evil.xml", '<!DOCTYPE r [<!ENTITY xxe "pwned">]><r>&xxe;</r>')


class TestZip:
    def test_roundtrip(self, ws):
        ws.write_text("f1.txt", "one")
        ws.write_text("sub/f2.txt", "two")
        created = ws.zip_create("arch.zip", ["f1.txt", "sub"])
        assert (ws.base / "arch.zip").is_file()
        extracted = ws.zip_extract("arch.zip", "out")
        assert set(extracted) == {"out/f1.txt", "out/sub/f2.txt"}
        assert ws.read_text("out/f1.txt") == "one"
        assert ws.read_text("out/sub/f2.txt") == "two"

    def test_recreate_archive_denied(self, ws):
        ws.write_text("f.txt", "x")
        ws.zip_create("a.zip", ["f.txt"])
        with pytest.raises(FileExistsError):
            ws.zip_create("a.zip", ["f.txt"])

    def test_nothing_to_archive(self, ws):
        with pytest.raises(ValueError):
            ws.zip_create("empty.zip", ["missing.txt"])

    def test_extract_missing(self, ws):
        with pytest.raises(FileNotFoundError):
            ws.zip_extract("ghost.zip", "out")

    def test_audit_archive_and_extract(self, ws):
        ws.write_text("f.txt", "x")
        ws.zip_create("a.zip", ["f.txt"])
        ws.zip_extract("a.zip", "out")
        kinds = [r["operation_type"] for r in ws.db.history(ws.user["id"], 20)]
        assert "archive" in kinds and "extract" in kinds
