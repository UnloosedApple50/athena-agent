#!/bin/bash
# Athena Agent Run Script
# Usage: ./scripts/run.sh [--host HOST] [--port PORT]

set -e

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Default values
HOST="${ATHENA_HOST:-0.0.0.0}"
PORT="${ATHENA_PORT:-8585}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo "╔══════════════════════════════════════════╗"
echo "║        Athena Agent v1.0.0               ║"
echo "╠══════════════════════════════════════════╣"
echo "║                                          ║"
echo "║  Server: http://${HOST}:${PORT}            ║"
echo "║  Docs:   http://${HOST}:${PORT}/docs      ║"
echo "║                                          ║"
echo "║  Press Ctrl+C to stop                    ║"
echo "║                                          ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Run the server
python3 -m athena run
