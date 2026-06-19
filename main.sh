#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=python3
else
    PYTHON_BIN=python
fi

exec "$PYTHON_BIN" main.py "$@"
