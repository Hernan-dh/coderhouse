"""Activa los hooks Git administrados por el proyecto."""

import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".githooks" / "pre-commit"

if not (ROOT / ".git").exists():
    raise SystemExit("No hay un repositorio Git local. Inicializalo antes con: git init")

HOOK.chmod(HOOK.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
subprocess.run(
    ["git", "-C", str(ROOT), "config", "core.hooksPath", ".githooks"],
    check=True,
)
print("Hooks activados: .githooks")
