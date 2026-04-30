#!/bin/bash
set -e

echo "====================================="
echo "Checking uv..."
echo "====================================="

if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "uv already installed: $(uv --version)"
fi

echo ""
echo "====================================="
echo "Creating Python 3.10 virtual env..."
echo "====================================="

uv venv --python 3.10

echo ""
echo "====================================="
echo "Installing dependencies..."
echo "====================================="

uv pip install --python .venv/bin/python -r requirements.txt

echo ""
echo "Environment ready."
echo "Activate with:"
echo "source .venv/bin/activate"