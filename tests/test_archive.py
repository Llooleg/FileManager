"""Тесты ZIP-защиты (archive.py): zip-slip, лимиты файлов и объёма."""
import zipfile

import pytest

from FileManager import archive as archive_mod
from FileManager.archive import create_zip, safe_extract


def _make_zip(path, entries: dict[str, str]):
    with zipfile.ZipFile(path, "w") as z:
        for name, content in entries.items():
            z.writestr(name, content)


class TestRoundtrip:
    def test_create_and_extract(self, tmp_path):
        src = tmp_path / "src"
        (src / "sub").mkdir(parents=True)
        (src / "a.txt").write_text("A")
        (src / "sub" / "b.txt").write_text("B")
        z = tmp_path / "ok.zip"
        create_zip(z, [(src / "a.txt", "a.txt"), (src / "sub" / "b.txt", "sub/b.txt")])

        dest = tmp_path / "out"
        files = safe_extract(z, dest)
        assert (dest / "a.txt").read_text() == "A"
        assert (dest / "sub" / "b.txt").read_text() == "B"
        assert len(files) == 2


class TestZipSlip:
    def test_traversal_entry_denied(self, tmp_path):
        evil = tmp_path / "evil.zip"
        _make_zip(evil, {"../evil.txt": "boom"})
        with pytest.raises(PermissionError):
            safe_extract(evil, tmp_path / "dest")
        assert not (tmp_path / "evil.txt").exists()

    def test_nested_traversal_denied(self, tmp_path):
        evil = tmp_path / "evil2.zip"
        _make_zip(evil, {"good/../../evil.txt": "boom"})
        with pytest.raises(PermissionError):
            safe_extract(evil, tmp_path / "dest")


class TestLimits:
    def test_too_many_entries(self, tmp_path, monkeypatch):
        monkeypatch.setattr(archive_mod, "MAX_FILES", 3)
        z = tmp_path / "many.zip"
        _make_zip(z, {f"f{i}.txt": "x" for i in range(4)})
        with pytest.raises(ValueError):
            safe_extract(z, tmp_path / "out")

    def test_zip_bomb_total_size(self, tmp_path, monkeypatch):
        monkeypatch.setattr(archive_mod, "MAX_TOTAL", 1024)
        z = tmp_path / "bomb.zip"
        _make_zip(z, {"big.txt": "x" * 4096})
        with pytest.raises(ValueError):
            safe_extract(z, tmp_path / "out")
