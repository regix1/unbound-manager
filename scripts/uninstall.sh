#!/bin/bash

# Unbound Manager Uninstaller
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Unbound Manager Uninstaller       ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
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

# Ask about removing Redis
echo
echo -e "${YELLOW}Do you want to remove Redis server?${NC}"
echo -e "${CYAN}Redis was installed for caching support${NC}"
read -p "Remove Redis? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl stop redis-server 2>/dev/null || true
    systemctl disable redis-server 2>/dev/null || true
    
    # Remove Redis
    apt-get remove -y redis-server redis-tools 2>/dev/null || true
    apt-get autoremove -y 2>/dev/null || true
    
    # Remove Redis configuration
    rm -rf /etc/redis
    rm -rf /var/lib/redis
    rm -rf /var/log/redis
    rm -rf /var/run/redis
    
    echo -e "${GREEN}✓${NC} Redis removed"
fi

# Ask about removing other dependencies
echo
echo -e "${YELLOW}Do you want to remove build dependencies?${NC}"
echo -e "${CYAN}These include: build-essential, libssl-dev, libexpat1-dev, etc.${NC}"
echo -e "${RED}WARNING: Other applications may depend on these packages!${NC}"
read -p "Remove build dependencies? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # List of packages installed by unbound-manager
    PACKAGES=(
        "build-essential"
        "libssl-dev"
        "libexpat1-dev"
        "libevent-dev"
        "libhiredis-dev"
        "libnghttp2-dev"
        "libsystemd-dev"
        "swig"
        "protobuf-c-compiler"
        "libprotobuf-c-dev"
    )
    
    echo -e "${YELLOW}Removing development packages...${NC}"
    for pkg in "${PACKAGES[@]}"; do
        apt-get remove -y "$pkg" 2>/dev/null || true
    done
    
    apt-get autoremove -y 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Development packages removed"
fi

# Clean up Python packages
echo
echo -e "${YELLOW}Do you want to remove Python dependencies?${NC}"
echo -e "${CYAN}These include: rich, jinja2, pyyaml, dnspython, etc.${NC}"
echo -e "${RED}WARNING: Other Python applications may use these!${NC}"
read -p "Remove Python dependencies? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip3 uninstall -y rich typer jinja2 pyyaml requests dnspython redis psutil 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Python dependencies removed"
fi

echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        Uninstall Complete!             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"

# Final summary
echo
echo -e "${CYAN}Summary of actions:${NC}"
echo -e "  • Unbound Manager package removed"
[[ ! -d ~/unbound-manager ]] && echo -e "  • Source directory removed"
[[ ! -f /usr/sbin/unbound ]] && echo -e "  • Unbound DNS server removed"
[[ ! -f /usr/bin/redis-server ]] && echo -e "  • Redis server removed"

echo
echo -e "${YELLOW}Thank you for using Unbound Manager!${NC}"