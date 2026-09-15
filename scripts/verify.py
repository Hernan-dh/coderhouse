"""Verificaciones locales usadas también por el hook de pre-commit."""

from __future__ import annotations

import ast
import subprocess
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESSENTIAL_FILES = (
    "README.md",
    ".env.example",
    "base.py",
    "manager.py",
    "providers.py",
    "schemas.py",
    "main.py",
    "requirements.txt",
    "pyproject.toml",
)
IGNORED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def python_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*.py")
        if not ({part.lower() for part in path.relative_to(ROOT).parts} & IGNORED_PARTS)
    ]


def main() -> int:
    errors: list[str] = []

    print("[check] archivos requeridos")
    for relative in ESSENTIAL_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"Falta el archivo requerido: {relative}")

    print("[check] sintaxis Python")
    for path in python_files():
        try:
            with tokenize.open(path) as source:
                ast.parse(source.read(), filename=str(path))
        except (SyntaxError, UnicodeError) as exc:
            errors.append(f"Python inválido en {path.relative_to(ROOT)}: {exc}")

    if (ROOT / ".git").exists():
        print("[check] integridad del diff")
        for args in (("diff", "--check"), ("diff", "--cached", "--check")):
            result = git(*args)
            if result.returncode:
                errors.append(result.stderr.strip() or f"git {' '.join(args)} falló")

    print("[check] importaciones")
    result = subprocess.run(
        [sys.executable, "-c", "import base, manager, providers, schemas"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        errors.append(f"Fallaron las importaciones: {result.stderr.strip()}")

    if errors:
        print("\nVerificación fallida:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("\nVerificación completada correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
