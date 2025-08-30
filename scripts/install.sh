#!/bin/bash
# Installation script for Unbound Manager
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Unbound Manager Installer          ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

# Check for VERSION file
if [ ! -f "VERSION" ]; then
    echo -e "${RED}VERSION file not found!${NC}"
    exit 1
fi

VERSION=$(cat VERSION)
echo -e "${CYAN}Installing Unbound Manager v${VERSION}${NC}"
echo

# Determine installation type
echo "Select installation type:"
echo "1) Development (editable, for testing/development)"
echo "2) System-wide (production)"
read -p "Choice (1-2): " choice

case $choice in
    1)
        echo -e "${YELLOW}Installing in development mode...${NC}"
        pip3 install -e .
        ;;
    2)
        echo -e "${YELLOW}Installing system-wide...${NC}"
        pip3 install .
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

# Verify installation
if command -v unbound-manager &> /dev/null; then
    echo -e "${GREEN}✓ Installation complete!${NC}"
    echo -e "${GREEN}Unbound Manager v${VERSION} installed successfully${NC}"
    echo -e "${GREEN}Run 'unbound-manager' to start.${NC}"
else
    echo -e "${RED}Installation may have failed. Check for errors above.${NC}"
    exit 1
fi