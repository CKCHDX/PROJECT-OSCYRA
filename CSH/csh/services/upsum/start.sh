#!/bin/bash
# Upsum — Linux/WSL start script
# Equivalent of RUNME.bat but for WSL/Linux environments

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo "==============================================="
echo "  Upsum — Project Nexus"
echo "  Starting backend..."
echo "==============================================="
echo

cd "$BACKEND_DIR" || { echo "ERROR: backend/ directory not found at $BACKEND_DIR"; exit 1; }

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "[1/3] Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
echo "[2/3] Installing dependencies..."
pip install -q -r requirements.txt

# Start backend
echo "[3/3] Starting backend on http://0.0.0.0:80"
exec uvicorn main:app --host 0.0.0.0 --port 80
