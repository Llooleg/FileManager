"""Хеширование паролей и защита путей."""
import hashlib
import hmac
import os
import re
from pathlib import Path

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, dk = stored.split("$")
        calc = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt),
                              n=int(n), r=int(r), p=int(p), dklen=len(dk) // 2)
        return hmac.compare_digest(calc.hex(), dk)
    except ValueError:
        return False


def safe_path(base: Path, rel: str) -> Path:
    """Путь обязан остаться внутри base (защита от ../, абсолютных путей и симлинков)."""
    base = base.resolve()
    target = (base / rel).resolve()
    if not target.is_relative_to(base):
        raise PermissionError(f"Путь выходит за пределы рабочей папки: {rel!r}")
    return target
