"""Рабочая область пользователя: CRUD, JSON/XML, ZIP + аудит каждой операции."""
import json
from pathlib import Path

from .archive import create_zip, safe_extract
from .formats import parse_json, parse_xml, xml_to_str
from .security import safe_path

MAX_IO = 5 * 1024 * 1024
MAX_ZIP_FILES = 1000


class Workspace:
    def __init__(self, db, user, root):
        self.db, self.user = db, user
        # у каждого пользователя своя песочница: чужие файлы недоступны by design
        self.base = (Path(root) / user["username"]).resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    def p(self, rel: str) -> Path:
        return safe_path(self.base, rel)

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.base).as_posix()

    def _audit(self, op, path, details=None):
        rel, uid = self._rel(path), self.user["id"]
        if op == "delete":
            fid = self.db.untrack(uid, rel)
        else:
            fid = self.db.track(uid, rel, path.stat().st_size)
        self.db.log(uid, op, fid, details)

    # --- текст ---
    def write_text(self, rel, text, append=False):
        p = self.p(rel)
        existed = p.exists()
        if existed and not p.is_file():
            raise IsADirectoryError(rel)
        old = p.stat().st_size if (append and existed) else 0
        if old + len(text.encode()) > MAX_IO:
            raise ValueError("Слишком большой объём данных")
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a" if append else "w", encoding="utf-8") as f:
            f.write(text)
        self._audit("modify" if existed else "create", p)

    def read_text(self, rel):
        p = self.p(rel)
        if not p.is_file():
            raise FileNotFoundError(rel)
        if p.stat().st_size > MAX_IO:
            raise ValueError("Файл слишком большой")
        text = p.read_bytes().decode("utf-8", errors="replace")
        self._audit("read", p)
        return text

    def delete(self, rel):
        p = self.p(rel)
        if not p.is_file():
            raise FileNotFoundError(rel)
        p.unlink()
        self._audit("delete", p)

    # --- JSON / XML ---
    def write_json(self, rel, raw):
        self.write_text(rel, json.dumps(parse_json(raw), ensure_ascii=False, indent=2))

    def read_json(self, rel):
        return parse_json(self.read_text(rel))

    def write_xml(self, rel, raw):
        root = parse_xml(raw.encode("utf-8"))
        self.write_text(rel, '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_to_str(root))

    def read_xml(self, rel):
        return xml_to_str(parse_xml(self.read_text(rel).encode("utf-8")))

    # --- ZIP ---
    def zip_create(self, archive_rel, rels):
        dst = self.p(archive_rel)
        if dst.exists():
            raise FileExistsError(archive_rel)
        sources = []
        for r in rels:
            s = self.p(r)
            sources += [s] if s.is_file() else [
                f for f in s.rglob("*") if f.is_file() and not f.is_symlink()]
        if not sources:
            raise ValueError("Нечего архивировать")
        if len(sources) > MAX_ZIP_FILES:
            raise ValueError(f"Больше {MAX_ZIP_FILES} файлов")
        dst.parent.mkdir(parents=True, exist_ok=True)
        create_zip(dst, [(f, self._rel(f)) for f in sources])
        self._audit("archive", dst, f"файлов: {len(sources)}")

    def zip_extract(self, archive_rel, dest_rel):
        src, dest = self.p(archive_rel), self.p(dest_rel)
        if not src.is_file():
            raise FileNotFoundError(archive_rel)
        dest.mkdir(parents=True, exist_ok=True)
        files = safe_extract(src, dest)
        for f in files:
            self._audit("extract", f, f"из {archive_rel}")
        return [self._rel(f) for f in files]
