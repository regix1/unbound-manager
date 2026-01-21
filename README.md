# Unbound Manager

A friendly, interactive tool for managing your own Unbound DNS server. No more memorizing commands or editing config files by hand.

## What Is This?

Unbound Manager takes the pain out of running your own DNS server. It handles the tricky stuff like compiling from source, setting up DNSSEC, configuring Redis caching, and keeping everything updated. You get a clean menu interface that just works.

**Why run your own DNS?** Privacy, speed, and control. Your DNS queries stay on your server instead of going to your ISP or a third party. Plus, with local caching, repeated lookups are instant.

## Features

- **One-command Unbound installation** from source with all the optimizations enabled
- **Pick your upstream DNS** from providers like Cloudflare, Quad9, Google, AdGuard, or go full recursion and query root servers directly
- **DNS-over-TLS encryption** keeps your queries private when forwarding
- **DNSSEC validation** protects against DNS spoofing attacks
- **Redis caching** for faster repeat lookups (optional but recommended)
- **Automatic backups** before any changes, with easy restore
- **Built-in diagnostics** to troubleshoot problems quickly
- **Auto-updates** for both the manager and Unbound itself
- **Keyboard-friendly navigation** with arrow keys and shortcuts

## Requirements

- Ubuntu or Debian-based Linux
- Python 3.7+
- Root access
- Internet connection

## Installation

### Prerequisites

First, make sure you have Python 3, pip, and git installed:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

### Install Unbound Manager

Clone the repo and install as root:

```bash
sudo -i
git clone https://github.com/regix1/unbound-manager.git
cd unbound-manager
pip3 install .
```

That's it. Both `pip3 install .` and `pip3 install -e .` work fine. The manager can update itself either way.

> **Note about PEP 668:** On Ubuntu 22.04+ and Debian 12+, you may see an "externally-managed-environment" error. Since unbound-manager runs as root and manages system services, installing as root (with `sudo -i` first) avoids this issue. Alternatively, you can use `pip3 install . --break-system-packages` if you prefer.

## Getting Started

Launch the manager:

```bash
sudo unbound-manager
```

You'll see an interactive menu. Use arrow keys to navigate or press the shortcut keys shown in brackets.

### First Time Setup

1. **Install Unbound** - Select from Install/Update menu. This compiles Unbound from source with Redis support, DNSSEC, and other goodies enabled.

2. **Pick a DNS Provider** - Go to Configuration > DNS Upstream. Choose from:
   - **Full Recursion** - Query root servers directly (most private, slightly slower)
   - **Cloudflare** - Fast, privacy-focused
   - **Quad9** - Swiss non-profit, blocks malware
   - **Google** - Reliable classic
   - **AdGuard** - Blocks ads and trackers
   - Or set up your own custom upstream

3. **Set Up Redis** (optional) - Configuration > Redis Cache. This dramatically speeds up repeat lookups.

4. **Test Everything** - Testing > Run Diagnostics to make sure it's all working.

## Menu Overview

The main menu is organized into logical sections:

| Key | Section | What It Does |
|-----|---------|--------------|
| S | Services | Start, stop, restart Unbound and Redis |
| V | View | Status, statistics, and logs |
| C | Configuration | DNS upstream, server settings, access control, Redis, DNSSEC |
| T | Testing | Diagnostics, DNS tests, performance benchmarks |
| B | Backups | Create, restore, and clean up backups |
| I | Install/Update | Update Unbound, update the manager, fresh install, repairs |
| H | Help | Documentation and tips |
| Q | Quit | Exit the program |

Within submenus, press `r` to return or `q` to quit the app entirely.

## DNS Provider Options

When you configure your upstream DNS, you can choose:

| Provider | What You Get |
|----------|--------------|
| Full Recursion | Maximum privacy. Queries go directly to root servers. No middleman. |
| Cloudflare | Blazing fast. Privacy audited by KPMG. |
| Cloudflare Malware | Same speed, blocks known malicious domains. |
| Cloudflare Family | Blocks malware and adult content. |
| Quad9 | Swiss-based non-profit. Strong privacy stance. Blocks malware. |
| Google DNS | The reliable standby. Fast and stable. |
| OpenDNS | Cisco-backed with phishing protection. |
| AdGuard | Blocks ads and trackers at the DNS level. |
| AdGuard Family | AdGuard plus adult content filtering. |
| Custom | Bring your own DNS servers. |

All providers except Full Recursion and Custom use DNS-over-TLS for encrypted queries.

## Configuration Files

The manager creates a clean, modular config structure:

```
/etc/unbound/
├── unbound.conf              # Main config (includes the rest)
├── unbound.conf.d/           # Modular pieces
│   ├── server.conf           # Server settings
│   ├── dnssec.conf           # DNSSEC config
│   ├── redis.conf            # Cache settings
│   └── control.conf          # Remote control
├── root.key                  # DNSSEC trust anchor
├── root.hints                # Root server list
└── backups/                  # Your config backups
```

You can edit these files directly if you want, but the manager makes it easy to change common settings without touching config files.

## Updating

### Update the Manager

From the menu: Install/Update > Update Manager

Or manually:
```bash
cd ~/unbound-manager
git pull
pip3 install .
```

The manager automatically clones the repo to `~/unbound-manager` if it doesn't exist, so updates work regardless of how you originally installed.

### Update Unbound

From the menu: Install/Update > Update Unbound

This downloads and compiles the new version while your current DNS keeps running. The switchover only takes a few seconds, and your config is preserved. If anything goes wrong, it automatically restores from backup.

## Uninstalling

### Remove Just the Manager

Keep Unbound running, just remove the management tool:

```bash
pip3 uninstall unbound-manager
rm -rf ~/unbound-manager
```

### Remove Everything

From the menu: Install/Update > Uninstall

Or manually:
```bash
systemctl stop unbound
systemctl disable unbound
rm -f /usr/sbin/unbound*
rm -rf /etc/unbound
pip3 uninstall unbound-manager
rm -rf ~/unbound-manager
```

## Troubleshooting

### Unbound Won't Start

Check the config syntax:
```bash
unbound-checkconf
```

Check the logs:
```bash
journalctl -u unbound -n 50
```

### DNS Queries Failing

Test locally:
```bash
dig @127.0.0.1 example.com
```

Make sure port 53 is listening:
```bash
ss -tulpn | grep :53
```

### Redis Not Connecting

Check if Redis is running:
```bash
systemctl status redis-server
redis-cli -s /var/run/redis/redis.sock ping
```

### Permission Errors

The manager needs root. Use `sudo unbound-manager` or run as root.

### General Issues

Use Testing > Run Diagnostics from the menu. It checks services, ports, configs, permissions, and DNS resolution all at once.

## Performance Tips

The defaults work well for most setups. For busier servers, consider:

- **num-threads**: Match your CPU core count
- **msg-cache-size**: Increase to 256m or 512m if you have the RAM
- **rrset-cache-size**: Set to 2x your msg-cache-size
- **prefetch**: Enable this to refresh popular records before they expire
- **serve-expired**: Serve stale records briefly during upstream outages

All of these can be adjusted through Configuration > Server Settings.

## Project Layout

```
unbound-manager/
├── unbound_manager/          # Python package
│   ├── cli.py                # Main interface
│   ├── installer.py          # Unbound installation
│   ├── config_manager.py     # Configuration handling
│   ├── backup.py             # Backup and restore
│   ├── tester.py             # DNS testing
│   ├── troubleshooter.py     # Diagnostics
│   └── ...
├── data/
│   ├── templates/            # Config templates
│   └── systemd/              # Service files
├── VERSION                   # Current version
└── README.md                 # You are here
```

## License

MIT License. See [LICENSE](LICENSE) for details.

## Links

- **Issues:** https://github.com/regix1/unbound-manager/issues

## Credits

- [NLnet Labs](https://nlnetlabs.nl/) for Unbound
- [Rich](https://github.com/Textualize/rich) for the terminal UI
- [Redis](https://redis.io/) for caching
