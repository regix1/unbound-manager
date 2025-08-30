#!/bin/bash

# Unbound Manager Uninstaller
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Unbound Manager Uninstaller${NC}"
echo "=============================="
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}"
   exit 1
fi

echo -e "${YELLOW}This will uninstall Unbound Manager (Python package only).${NC}"
echo -e "${YELLOW}Your Unbound DNS configuration will NOT be removed.${NC}"
read -p "Continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstall cancelled."
    exit 0
fi

# Uninstall pip package
echo -e "${YELLOW}Removing Unbound Manager Python package...${NC}"
pip3 uninstall -y unbound-manager 2>/dev/null || true

# Remove command from /usr/local/bin if it exists
if [ -f /usr/local/bin/unbound-manager ]; then
    rm -f /usr/local/bin/unbound-manager
    echo -e "${GREEN}✓${NC} Removed /usr/local/bin/unbound-manager"
fi

# Ask about removing source directory
echo
read -p "Remove source directory ~/unbound-manager? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf ~/unbound-manager
    echo -e "${GREEN}✓${NC} Removed source directory"
fi

# Ask about removing Unbound itself
echo
echo -e "${YELLOW}Do you want to remove Unbound DNS server itself?${NC}"
echo -e "${RED}WARNING: This will remove your DNS server!${NC}"
read -p "Remove Unbound? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl stop unbound 2>/dev/null || true
    systemctl disable unbound 2>/dev/null || true
    
    # Backup configuration first
    if [ -d /etc/unbound ]; then
        backup_file="/root/unbound-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
        tar czf "$backup_file" /etc/unbound/
        echo -e "${GREEN}✓${NC} Configuration backed up to $backup_file"
    fi
    
    # Remove Unbound
    rm -f /usr/sbin/unbound
    rm -f /usr/sbin/unbound-*
    rm -rf /etc/unbound
    rm -f /etc/systemd/system/unbound.service
    systemctl daemon-reload
    
    echo -e "${GREEN}✓${NC} Unbound removed"
fi

echo
echo -e "${GREEN}Uninstall complete!${NC}"