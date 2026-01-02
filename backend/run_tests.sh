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

# activate venv
if [ -f "venv/bin/activate" ]; then
    echo -e "${BLUE}activating venv...${NC}"
    source venv/bin/activate
else
    echo -e "${BLUE}creating venv...${NC}"
    python3 -m venv venv
    source venv/bin/activate
fi

# install dependencies
echo -e "${BLUE}installing dependencies...${NC}"
pip install -r requirements.txt -q

# run tests
echo -e "${BLUE}running pytest...${NC}"
python -m pytest tests/

echo -e "\n${GREEN}tests completed!${NC}"
