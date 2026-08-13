#!/usr/bin/env bash
set -eu

TOOL_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$TOOL_DIR/.venv"

if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install -U pip setuptools wheel
"$VENV/bin/python" -m pip install -r "$TOOL_DIR/requirements.txt"

echo "Ready: $VENV/bin/python $TOOL_DIR/todo.py"
