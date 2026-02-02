#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Tark Backend Setup${NC}\n"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 required${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python $(python3 --version | cut -d' ' -f2)"

# Check uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv required: https://github.com/astral-sh/uv${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} uv $(uv --version)"

# Install deps
echo -e "${BLUE}→${NC} Installing dependencies..."
uv sync

# Setup .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠${NC}  Edit .env and add MAPBOX_ACCESS_TOKEN"
    echo -e "   ${BLUE}https://account.mapbox.com/access-tokens/${NC}"
fi

echo -e "\n${GREEN}✅ Done!${NC}\n"
echo -e "Test: ${BLUE}uv run python tests/test_mapbox.py${NC}"
echo -e "Run:  ${BLUE}uv run uvicorn app.main:app${NC}"

