#!/usr/bin/env python3
"""Гейт Stage 3 (SAST): находки уровня High/Critical роняют сборку.

Остальные уровни (Low/Medium) допускаются и остаются в отчёте.
Используется в .github/workflows/main.yml после `semgrep scan --json`.
"""
import json
import sys

BLOCKING = {"HIGH", "CRITICAL"}
DEFAULT_REPORT = "reports/semgrep.json"


def main(report_path: str) -> None:
    with open(report_path, encoding="utf-8") as f:
        data = json.load(f)

    if data.get("errors"):
        print("Semgrep завершился с внутренними ошибками:")
        for err in data["errors"]:
            print(f"  - {err.get('message', err)}")
        sys.exit(2)

    findings = data.get("results", [])
    blocking = [
        r for r in findings
        if str(r.get("extra", {}).get("severity", "")).upper() in BLOCKING
    ]

    for r in blocking:
        path, line = r.get("path", "?"), r.get("start", {}).get("line", 0)
        sev = r["extra"]["severity"].upper()
        print(f"::error file={path},line={line}::[SAST] {sev} {r['check_id']} в {path}:{line}")

    print(f"Semgrep: всего находок {len(findings)}, из них High/Critical: {len(blocking)}")
    if blocking:
        print("Сборка прервана: обнаружены уязвимости уровня High/Critical.")
        sys.exit(1)
    print("Гейт SAST пройден.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPORT)
