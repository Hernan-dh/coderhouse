#!/usr/bin/env sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if [ -f "$root/.venv/Scripts/python.exe" ]; then
    python="$root/.venv/Scripts/python.exe"
elif [ -f "$root/.venv/bin/python" ]; then
    python="$root/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    python=python3
elif command -v python >/dev/null 2>&1; then
    python=python
else
    echo "No se encontró Python 3." >&2
    exit 1
fi

exec "$python" "$root/scripts/verify.py"
