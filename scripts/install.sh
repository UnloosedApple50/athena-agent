#!/bin/bash
# Athena Agent Installation Script
# Usage: ./scripts/install.sh

set -e

echo "╔══════════════════════════════════════════╗"
echo "║     Athena Agent — Installation Script    ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python installation..."
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
        echo -e "${RED}Error: Python 3.11+ required. Found: $PYTHON_VERSION${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
else
    echo -e "${RED}Error: Python 3 not found. Please install Python 3.11+${NC}"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}! Virtual environment already exists${NC}"
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo -e "${GREEN}✓ pip upgraded${NC}"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -e . --quiet
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Install dev dependencies
echo ""
read -p "Install development dependencies? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install -e ".[dev]" --quiet
    echo -e "${GREEN}✓ Dev dependencies installed${NC}"
fi

# Create .env file
echo ""
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created from template${NC}"
else
    echo -e "${YELLOW}! .env file already exists${NC}"
fi

# Create data directory
mkdir -p data logs
echo -e "${GREEN}✓ Data and logs directories created${NC}"

# Initialize database
echo ""
echo "Initializing database..."
python3 -m athena db init
echo -e "${GREEN}✓ Database initialized${NC}"

# Check for Ollama
echo ""
echo "Checking for Ollama..."
if command -v ollama &>/dev/null; then
    echo -e "${GREEN}✓ Ollama found${NC}"
    echo ""
    echo "To start Ollama:"
    echo "  ollama serve"
    echo "  ollama pull llama3.2"
else
    echo -e "${YELLOW}! Ollama not found — Athena will use rule-based fallback${NC}"
    echo "  Install from: https://ollama.ai"
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo -e "${GREEN}║     Installation Complete!               ║${NC}"
echo "╠══════════════════════════════════════════╣"
echo "║                                          ║"
echo "║  Start Athena:                           ║"
echo "║    source .venv/bin/activate             ║"
echo "║    python -m athena run                  ║"
echo "║                                          ║"
echo "║  Dashboard: http://localhost:8585        ║"
echo "║                                          ║"
echo "╚══════════════════════════════════════════╝"
