# Unbound Manager

A comprehensive DNS server management tool for Unbound with an interactive terminal interface.

## Overview

Unbound Manager simplifies the deployment and management of Unbound DNS servers by providing automated installation from source, configuration management, and ongoing maintenance through an intuitive menu-driven interface.

### Key Features

- Compile and install Unbound from source with optimized settings
- DNSSEC validation with automatic trust anchor management
- Redis integration for enhanced caching performance
- Configuration backup and restore capabilities
- Service health monitoring and diagnostics
- Interactive configuration editing
- Performance testing and benchmarking

## Requirements

- Ubuntu/Debian-based Linux distribution
- Python 3.7 or higher
- Root privileges
- Internet connection for downloading dependencies

## Installation

### Installation Methods

#### Development Install (Recommended - Supports Auto-Updates)

This method maintains the git repository connection, allowing automatic updates through the manager:

```bash
git clone https://github.com/regix1/unbound-manager.git
cd unbound-manager
pip3 install -e .
```

#### Production Install (Manual Updates Only)

This method copies files to Python's site-packages directory. Updates must be performed manually:

```bash
git clone https://github.com/regix1/unbound-manager.git
cd unbound-manager
pip3 install .
```

**Note:** All commands require root privileges. If not running as root, prefix commands with `sudo`.

## Usage

Launch the manager as root:

```bash
unbound-manager
```

If not running as root:
```bash
sudo unbound-manager
```

### First-Time Setup

1. Select **Option 1** - Install Unbound (compiles from source)
2. Select **Option 5** - Configure Redis Integration (optional but recommended)
3. Select **Option 11** - Test Unbound Functionality

### Menu Structure

The interface is organized into sections:

- **Installation & Setup** - Install, fix, or update Unbound
- **Configuration** - Manage DNS settings, Redis, and DNSSEC
- **Maintenance** - Backup, restore, and manage keys
- **Troubleshooting** - Diagnostics, testing, and log viewing
- **System** - Service control and statistics

## Configuration

Unbound Manager creates and manages configurations in `/etc/unbound/`:

```
/etc/unbound/
├── unbound.conf                 # Main configuration
├── unbound.conf.d/              # Modular configuration files
│   ├── server.conf              # Server settings
│   ├── dnssec.conf              # DNSSEC configuration
│   ├── redis.conf               # Redis cache settings
│   └── control.conf             # Remote control settings
├── root.key                     # DNSSEC trust anchor
├── root.hints                   # Root name servers
└── backups/                     # Automatic backups
```

## Updating

### Update Methods Based on Installation Type

#### For Development Installs

Automatic updates are available through the manager:

```bash
unbound-manager
# Select Option 15 - Update Unbound Manager
```

Or manually:
```bash
cd ~/unbound-manager
git pull
pip3 install -e . --upgrade
```

#### For Production Installs

Manual update required:

```bash
cd ~/unbound-manager
git pull
pip3 install . --upgrade
```

Or reinstall:
```bash
pip3 uninstall unbound-manager
cd ~
rm -rf unbound-manager
git clone https://github.com/regix1/unbound-manager.git
cd unbound-manager
pip3 install .
```

### Update Unbound DNS

The manager can update Unbound to newer versions while preserving configuration:

```bash
unbound-manager
# Select Option 3 - Update Unbound Version
```

## Uninstallation

### Remove Unbound Manager Only

Preserves Unbound DNS server and configurations:

```bash
pip3 uninstall unbound-manager
rm -rf ~/unbound-manager  # Optional: remove source directory
```

### Remove Everything

Complete removal including Unbound DNS:

```bash
unbound-manager
# Select Option 16 - Uninstall Unbound Manager
# Follow prompts to also remove Unbound DNS
```

Manual complete removal:
```bash
# Stop services
systemctl stop unbound
systemctl disable unbound

# Backup configuration (optional)
tar czf /root/unbound-backup-$(date +%Y%m%d).tar.gz /etc/unbound/

# Remove Unbound
rm -f /usr/sbin/unbound*
rm -rf /etc/unbound

# Remove manager
pip3 uninstall unbound-manager
rm -rf ~/unbound-manager
```

## Troubleshooting

### Common Issues

#### Service Won't Start

Check configuration syntax:
```bash
unbound-checkconf
```

View service status and logs:
```bash
systemctl status unbound
journalctl -u unbound -n 50
```

#### DNS Resolution Not Working

Test DNS resolution:
```bash
dig @127.0.0.1 example.com
```

Check if port 53 is listening:
```bash
netstat -tulpn | grep :53
```

#### Redis Connection Failed

Verify Redis service:
```bash
systemctl status redis-server
redis-cli -s /var/run/redis/redis.sock ping
```

#### Permission Denied

The manager requires root privileges. Use `sudo unbound-manager` or run as root.

#### Auto-Update Not Working

Auto-updates only work with development installs (`pip3 install -e .`). For production installs, updates must be performed manually.

## Performance Tuning

Default settings are conservative. For high-traffic servers, adjust these settings through the manager:

- **num-threads**: Set to number of CPU cores
- **msg-cache-size**: Increase based on available RAM (e.g., 256m, 512m)
- **rrset-cache-size**: Set to 2x msg-cache-size
- **prefetch**: Enable for proactive cache updates
- **serve-expired**: Enable to serve stale records during outages

## Project Structure

```
unbound-manager/
├── unbound_manager/          # Core Python package
├── data/
│   ├── templates/           # Jinja2 configuration templates
│   ├── configs/             # Default configurations
│   └── systemd/             # Service definitions
├── scripts/                 # Installation and maintenance scripts
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
├── setup.py                 # Package configuration
├── VERSION                  # Version tracking
└── README.md               # This file
```

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Support

- Report issues: https://github.com/regix1/unbound-manager/issues
- Discussions: https://github.com/regix1/unbound-manager/discussions

## Acknowledgments

- NLnet Labs for Unbound DNS
- Rich library for terminal UI
- Redis for caching backend