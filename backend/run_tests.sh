#!/bin/bash
set -e

# colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # no color

echo -e "${BLUE}running tests...${NC}\n"

# navigate to backend directory if running from root
if [ -d "backend" ]; then
    cd backend
fi

# check uv
if ! command -v uv &> /dev/null; then
    echo -e "${BLUE}installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# sync dependencies
echo -e "${BLUE}syncing dependencies...${NC}"
uv sync

# run tests
echo -e "${BLUE}running pytest...${NC}"
uv run pytest tests/

echo -e "\n${GREEN}tests completed!${NC}"
