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

### Standard Installation

Clone the repository and install:

```bash
git clone https://github.com/regix1/unbound-manager.git
cd unbound-manager
sudo pip3 install -e .
```

### System-wide Installation

For production deployments:

```bash
git clone https://github.com/regix1/unbound-manager.git
cd unbound-manager
sudo pip3 install .
```

## Usage

Launch the manager with root privileges:

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

## Configuration Files

Unbound Manager creates and manages configurations in:

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

### Update Unbound Manager

From within the application:
```bash
sudo unbound-manager
# Select Option 15 - Update Unbound Manager
```

Or manually:
```bash
cd ~/unbound-manager
git pull
sudo pip3 install -e . --upgrade
```

### Update Unbound DNS

The manager can update Unbound to newer versions while preserving configuration:
```bash
sudo unbound-manager
# Select Option 3 - Update Unbound Version
```

## Uninstallation

### Remove Unbound Manager Only

Preserves Unbound DNS server and configurations:

```bash
sudo pip3 uninstall unbound-manager
# Optional: remove source directory
rm -rf ~/unbound-manager
```

### Remove Everything

Complete removal including Unbound DNS:

```bash
sudo unbound-manager
# Select Option 16 - Uninstall Unbound Manager
# Follow prompts to also remove Unbound DNS
```

Or manually:
```bash
# Stop services
sudo systemctl stop unbound
sudo systemctl disable unbound

# Backup configuration (optional)
sudo tar czf /root/unbound-backup-$(date +%Y%m%d).tar.gz /etc/unbound/

# Remove Unbound
sudo rm -f /usr/sbin/unbound*
sudo rm -rf /etc/unbound

# Remove manager
sudo pip3 uninstall unbound-manager
rm -rf ~/unbound-manager
```

## Troubleshooting

### Service Issues

If Unbound fails to start after configuration changes:
```bash
# Check configuration syntax
sudo unbound-checkconf

# View service status
sudo systemctl status unbound

# Check logs
sudo journalctl -u unbound -n 50
```

### DNS Resolution Problems

Test DNS resolution:
```bash
# Test using Unbound
dig @127.0.0.1 example.com

# Check if port 53 is listening
sudo netstat -tulpn | grep :53
```

### Redis Connection Issues

Verify Redis integration:
```bash
# Check Redis service
sudo systemctl status redis-server

# Test Redis socket
sudo redis-cli -s /var/run/redis/redis.sock ping
```

### Permission Errors

The manager must run as root:
```bash
sudo unbound-manager
```

## Performance Tuning

Default settings are conservative. For high-traffic servers, adjust in the manager:

- Increase `num-threads` to match CPU cores
- Increase `msg-cache-size` and `rrset-cache-size` based on available RAM
- Enable `prefetch` and `prefetch-key` for proactive cache updates
- Configure `serve-expired` to serve stale records during outages

## Project Structure

```
unbound-manager/
├── unbound_manager/          # Core Python package
├── data/
│   ├── templates/           # Jinja2 configuration templates
│   ├── configs/             # Default configurations
│   └── systemd/             # Service definitions
├── scripts/                 # Installation and maintenance scripts
├── requirements.txt         # Python dependencies
└── VERSION                  # Version tracking
```

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Support

Report issues: https://github.com/regix1/unbound-manager/issues

## Acknowledgments

- NLnet Labs for Unbound DNS
- Rich library for terminal UI
- Redis for caching backend