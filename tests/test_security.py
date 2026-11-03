"""Тесты хеширования паролей и защиты путей (security.py)."""
from pathlib import Path

import pytest

from FileManager.security import USERNAME_RE, hash_password, safe_path, verify_password


class TestPasswords:
    def test_hash_verify_roundtrip(self):
        stored = hash_password("S3cret-pass")
        assert stored.startswith("scrypt$")
        assert verify_password("S3cret-pass", stored) is True

    def test_wrong_password_rejected(self):
        stored = hash_password("S3cret-pass")
        assert verify_password("wrong-pass", stored) is False

    def test_malformed_hash_rejected(self):
        assert verify_password("x", "garbage-without-dollars") is False
        assert verify_password("x", "scrypt$1$2$3$zz$yy") is False

    def test_hashes_are_salted(self):
        assert hash_password("same") != hash_password("same")


class TestUsernameRegex:
    @pytest.mark.parametrize("name", ["alice", "user_2024", "A1b"])
    def test_valid(self, name):
        assert USERNAME_RE.match(name)

    @pytest.mark.parametrize("name", ["ab", "x" * 33, "кириллица", "bad name", ""])
    def test_invalid(self, name):
        assert not USERNAME_RE.match(name)


class TestSafePath:
    def test_inside_ok(self, tmp_path):
        assert safe_path(tmp_path, "docs/a.txt") == (tmp_path / "docs" / "a.txt").resolve()

    def test_traversal_denied(self, tmp_path):
        with pytest.raises(PermissionError):
            safe_path(tmp_path, "../escape.txt")

    def test_absolute_path_denied(self, tmp_path):
        with pytest.raises(PermissionError):
            safe_path(tmp_path, "/etc/passwd")

    def test_sneaky_traversal_denied(self, tmp_path):
        with pytest.raises(PermissionError):
            safe_path(tmp_path, "docs/../../escape.txt")
