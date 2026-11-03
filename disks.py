"""Список дисков и свойства ФС (psutil, если есть; иначе stdlib)."""
import os
import shutil


def _mounts():
    try:
        import psutil
        return [(p.mountpoint, p.fstype, p.device) for p in psutil.disk_partitions(all=False)]
    except ImportError:
        pass
    if os.name == "nt":
        import ctypes
        import string
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        return [(f"{c}:\\", "", "") for i, c in enumerate(string.ascii_uppercase) if mask >> i & 1]
    if os.path.exists("/proc/mounts"):
        out = []
        with open("/proc/mounts") as f:
            for line in f:
                dev, mp, fs = line.split()[:3]
                if dev.startswith("/dev/"):
                    out.append((mp.replace("\\040", " "), fs, dev))
        return out
    return []


def list_disks():
    seen, result = set(), []
    for mp, fs, dev in _mounts() or [(os.path.abspath(os.sep), "", "")]:
        if mp in seen:
            continue
        seen.add(mp)
        try:
            u = shutil.disk_usage(mp)
        except OSError:  # пустой картридер и прочие призраки
            continue
        result.append({"mount": mp, "fs": fs or "?", "device": dev or "?",
                       "total": u.total, "used": u.used, "free": u.free})
    return result


def human(n):
    n = float(n)
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} ТБ"


def print_disks():
    print(f"{'Точка':<22}{'ФС':<8}{'Устройство':<20}{'Всего':>10}{'Занято':>10}{'Свободно':>10}{'%':>6}")
    for d in list_disks():
        pct = d["used"] * 100 / d["total"] if d["total"] else 0
        print(f"{d['mount']:<22}{d['fs']:<8}{d['device']:<20}{human(d['total']):>10}"
              f"{human(d['used']):>10}{human(d['free']):>10}{pct:>5.0f}%")
