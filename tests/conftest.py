# Bootstrap импорта пакета.
# Корень репозитория сам является python-пакетом FileManager. При обычном
# клонировании каталог называется "FileManager", но локальный раннер (act)
# может выложить код в каталог с другим именем — учитываем оба случая.
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if ROOT.name == "FileManager":
    sys.path.insert(0, str(ROOT.parent))
else:  # каталог выгрузки назван иначе — регистрируем пакет вручную
    spec = importlib.util.spec_from_file_location(
        "FileManager", ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)])
    _pkg = importlib.util.module_from_spec(spec)
    sys.modules["FileManager"] = _pkg
    spec.loader.exec_module(_pkg)
