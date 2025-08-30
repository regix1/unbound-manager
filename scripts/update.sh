#!/bin/bash

# Unbound Manager Updater
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

REPO_URL="https://github.com/regix1/unbound-manager.git"
INSTALL_DIR="$HOME/unbound-manager"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Unbound Manager Update/Reinstall    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

# Function to check version
check_version() {
    if [ -f "$INSTALL_DIR/VERSION" ]; then
        cat "$INSTALL_DIR/VERSION"
    else
        echo "unknown"
    fi
}

# Function to get latest version from GitHub
get_latest_version() {
    curl -s https://api.github.com/repos/regix1/unbound-manager/releases/latest | grep tag_name | cut -d '"' -f 4 2>/dev/null || echo "latest"
}

CURRENT_VERSION=$(check_version)
LATEST_VERSION=$(get_latest_version)

echo -e "${CYAN}Current version: ${CURRENT_VERSION}${NC}"
echo -e "${CYAN}Latest version: ${LATEST_VERSION}${NC}"
echo

echo "Select an option:"
echo "1) Update to latest version (pull from git)"
echo "2) Reinstall current version (fix issues)"
echo "3) Force reinstall (complete reinstall)"
echo "4) Cancel"
echo
read -p "Choice (1-4): " choice

case $choice in
    1)
        echo -e "${YELLOW}Updating to latest version...${NC}"
        
        # Backup current installation
        if [ -d "$INSTALL_DIR" ]; then
            backup_dir="$INSTALL_DIR.backup.$(date +%Y%m%d-%H%M%S)"
            cp -r "$INSTALL_DIR" "$backup_dir"
            echo -e "${GREEN}✓${NC} Backup created: $backup_dir"
        fi
        
        # Pull latest changes
        cd "$INSTALL_DIR"
        
        # Stash any local changes
        git stash 2>/dev/null || true
        
        # Pull latest
        echo -e "${YELLOW}Pulling latest changes...${NC}"
        git pull origin main || git pull origin master
        
        # Update pip package
        echo -e "${YELLOW}Updating Python package...${NC}"
        pip3 install -e . --upgrade
        
        # Show new version
        NEW_VERSION=$(cat VERSION)
        echo -e "${GREEN}✓ Update complete! Now running v${NEW_VERSION}${NC}"
        ;;
        
    2)
        echo -e "${YELLOW}Reinstalling current version v${CURRENT_VERSION}...${NC}"
        
        # Reinstall pip package
        cd "$INSTALL_DIR"
        pip3 uninstall -y unbound-manager 2>/dev/null || true
        pip3 install -e .
        
        echo -e "${GREEN}✓ Reinstall complete!${NC}"
        ;;
        
    3)
        echo -e "${YELLOW}Force reinstalling...${NC}"
        
        # Backup configuration
        if [ -d /etc/unbound ]; then
            backup_file="/root/unbound-config-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
            tar czf "$backup_file" /etc/unbound/
            echo -e "${GREEN}✓${NC} Configuration backed up to $backup_file"
        fi
        
        # Remove old installation
        pip3 uninstall -y unbound-manager 2>/dev/null || true
        
        # Backup and remove directory
        if [ -d "$INSTALL_DIR" ]; then
            mv "$INSTALL_DIR" "$INSTALL_DIR.old.$(date +%Y%m%d-%H%M%S)"
        fi
        
        # Clone fresh
        echo -e "${YELLOW}Cloning fresh repository...${NC}"
        cd "$HOME"
        git clone "$REPO_URL"
        
        # Install
        cd "$INSTALL_DIR"
        pip3 install -e .
        
        NEW_VERSION=$(cat VERSION)
        echo -e "${GREEN}✓ Force reinstall complete! Now running v${NEW_VERSION}${NC}"
        ;;
        
    4)
        echo "Cancelled."
        exit 0
        ;;
        
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo
echo -e "${GREEN}Done! Run 'unbound-manager' to start.${NC}"