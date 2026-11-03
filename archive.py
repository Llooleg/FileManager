"""ZIP с лимитами: число файлов, суммарный размер, степень сжатия, zip-slip."""
import zipfile
from pathlib import Path

from .security import safe_path

MAX_FILES = 1000
MAX_TOTAL = 100 * 1024 * 1024  # байт после распаковки
MAX_RATIO = 100


def create_zip(dst: Path, files: list[tuple[Path, str]]):
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for src, arcname in files:
            z.write(src, arcname)


def safe_extract(src: Path, dest: Path) -> list[Path]:
    created, total = [], 0
    with zipfile.ZipFile(src) as z:
        infos = z.infolist()
        if len(infos) > MAX_FILES:
            raise ValueError(f"В архиве больше {MAX_FILES} записей")
        if sum(i.file_size for i in infos) > MAX_TOTAL:
            raise ValueError("Распакованный размер превышает лимит (zip-бомба?)")
        try:
            for i in infos:
                target = safe_path(dest, i.filename)  # zip-slip -> PermissionError
                if i.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if i.file_size > 1_048_576 and i.file_size > MAX_RATIO * max(i.compress_size, 1):
                    raise ValueError(f"Подозрительная степень сжатия: {i.filename}")
                if target.exists():
                    raise FileExistsError(f"Файл уже существует: {i.filename}")
                target.parent.mkdir(parents=True, exist_ok=True)
                created.append(target)
                with z.open(i) as s, open(target, "wb") as d:
                    while chunk := s.read(65536):  # считаем реальные байты, а не заголовок
                        total += len(chunk)
                        if total > MAX_TOTAL:
                            raise ValueError("Превышен лимит распакованных данных")
                        d.write(chunk)
        except Exception:
            for f in created:  # откат: не оставляем половину архива
                f.unlink(missing_ok=True)
            raise
    return created
