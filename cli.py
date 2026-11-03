"""Консольный интерфейс: аутентификация + REPL."""
import argparse
import json
import shlex
import sqlite3
import time
from getpass import getpass

from .db import Database
from .disks import print_disks
from .files import Workspace
from .security import USERNAME_RE, hash_password, verify_password

_DUMMY = hash_password("dummy")  # чтобы вход несуществующего юзера занимал столько же времени
MAX_FAILS = 5


def _ls(ws, a):
    rows = ws.db.list_files(ws.user["id"])
    for r in rows:
        print(f"{r['id']:>4}  {r['size']:>10}  {r['created_at']}  {r['location']}")
    if not rows:
        print("(пусто)")


def _history(ws, a):
    n = min(max(int(a[0]), 1), 500) if a else 20
    for r in ws.db.history(ws.user["id"], n):
        print(f"{r['timestamp']}  {r['operation_type']:<12} {r['location'] or '-':<28} {r['details'] or ''}")


COMMANDS = {
    "disks": (0, "disks", lambda ws, a: print_disks()),
    "ls": (0, "ls", _ls),
    "write": (2, "write <путь> <текст>", lambda ws, a: ws.write_text(a[0], " ".join(a[1:]))),
    "append": (2, "append <путь> <текст>", lambda ws, a: ws.write_text(a[0], " ".join(a[1:]), append=True)),
    "cat": (1, "cat <путь>", lambda ws, a: print(ws.read_text(a[0]))),
    "rm": (1, "rm <путь>", lambda ws, a: ws.delete(a[0])),
    "json-write": (2, "json-write <путь> '<json>'", lambda ws, a: ws.write_json(a[0], " ".join(a[1:]))),
    "json-read": (1, "json-read <путь>",
                  lambda ws, a: print(json.dumps(ws.read_json(a[0]), ensure_ascii=False, indent=2))),
    "xml-write": (2, "xml-write <путь> '<xml>'", lambda ws, a: ws.write_xml(a[0], " ".join(a[1:]))),
    "xml-read": (1, "xml-read <путь>", lambda ws, a: print(ws.read_xml(a[0]))),
    "zip": (2, "zip <архив.zip> <путь...>", lambda ws, a: ws.zip_create(a[0], a[1:])),
    "unzip": (1, "unzip <архив.zip> [папка]",
              lambda ws, a: print("\n".join(ws.zip_extract(a[0], a[1] if len(a) > 1 else a[0] + "_extracted")))),
    "history": (0, "history [N]", _history),
}


def authenticate(db):
    fails = 0
    while True:
        choice = input("1) Вход  2) Регистрация  3) Выход > ").strip()
        if choice == "3":
            return None
        if choice not in ("1", "2"):
            continue
        name = input("Логин: ").strip()
        if choice == "2":
            if not USERNAME_RE.match(name):
                print("Логин: 3-32 символа, латиница, цифры, _")
                continue
            pw = getpass("Пароль (мин. 8 символов): ")
            if len(pw) < 8 or pw != getpass("Ещё раз: "):
                print("Пароль короткий или не совпал.")
                continue
            try:
                db.add_user(name, hash_password(pw))
                print("Готово, теперь войдите.")
            except sqlite3.IntegrityError:
                print("Логин занят.")
            continue
        pw = getpass("Пароль: ")
        user = db.get_user(name)
        valid = verify_password(pw, user["password_hash"] if user else _DUMMY)
        if user and valid:
            db.log(user["id"], "login")
            return user
        db.log(user["id"] if user else None, "login_failed", None, f"login={name[:50]}")
        fails += 1
        print("Неверный логин или пароль.")
        if fails >= MAX_FAILS:
            print("Слишком много попыток.")
            return None
        time.sleep(fails)


def repl(ws):
    print("Команды:", ", ".join(COMMANDS), "| exit")
    while True:
        try:
            line = input(f"{ws.user['username']}> ")
            parts = shlex.split(line)
        except (EOFError, KeyboardInterrupt):
            break
        except ValueError as e:
            print(e)
            continue
        if not parts:
            continue
        cmd, args = parts[0], parts[1:]
        if cmd in ("exit", "quit"):
            break
        if cmd not in COMMANDS:
            print("Неизвестная команда.")
            continue
        min_args, usage, func = COMMANDS[cmd]
        if len(args) < min_args:
            print("Использование:", usage)
            continue
        try:
            func(ws, args)
        except PermissionError as e:
            ws.db.log(ws.user["id"], "denied", None, line[:200])
            print(f"Отказано: {e}")
        except Exception as e:
            print(f"Ошибка ({type(e).__name__}): {e}")


def main():
    ap = argparse.ArgumentParser(prog="secfm")
    ap.add_argument("--db", default="secfm.db")
    ap.add_argument("--root", default="workspace")
    a = ap.parse_args()
    db = Database(a.db)
    user = authenticate(db)
    if user:
        repl(Workspace(db, user, a.root))
