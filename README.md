# 🔒 Unbound Manager

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux-orange?style=for-the-badge&logo=linux)](https://www.linux.org/)
[![Unbound](https://img.shields.io/badge/Unbound-DNS-red?style=for-the-badge)](https://nlnetlabs.nl/projects/unbound/about/)

### **A Modern DNS Server Management Tool with Beautiful Terminal UI**

*Simplify your Unbound DNS server deployment and management*

</div>

## 🔄 Updates

### Update Everything (Manager + Unbound)

```bash
cd ~/unbound-manager && \
git pull && \
sudo pip3 install -e . --upgrade && \
echo "✅ Update complete"
```

---

## 🎯 What is Unbound Manager?

**Unbound Manager** is a comprehensive tool that makes installing, configuring, and managing Unbound DNS servers simple and intuitive. With its beautiful terminal interface powered by Rich, it transforms complex DNS operations into easy, menu-driven workflows.

### ✨ Key Features

- 🚀 **One-Command Installation** - Compile and configure Unbound from source
- 🔒 **DNSSEC Ready** - Automatic DNSSEC validation and key management
- ⚡ **Redis Caching** - High-performance caching with Redis integration
- 💾 **Auto Backups** - Automatic configuration backups before changes
- 📊 **Real-time Stats** - Monitor queries, cache hits, and performance
- 🔧 **Auto-Fix Issues** - Built-in troubleshooting and repair tools
- 🎨 **Beautiful UI** - Rich terminal interface with colors and progress bars

---

## 📦 Installation

### Requirements

- **OS**: Ubuntu/Debian-based Linux
- **Python**: 3.7 or higher
- **Access**: Root or sudo privileges

### Quick Install

Copy and paste this command to install Unbound Manager:

```bash
# Download and install Unbound Manager
git clone https://github.com/regix1/unbound-manager.git && \
cd unbound-manager && \
sudo pip3 install -e . && \
echo "✅ Installation complete! Run 'sudo unbound-manager' to start"
```

### Step-by-Step Install

If you prefer to install step by step:

```bash
# Step 1: Clone the repository
git clone https://github.com/regix1/unbound-manager.git

# Step 2: Enter the directory
cd unbound-manager

# Step 3: Install the package
sudo pip3 install -e .

# Step 4: Run the manager
sudo unbound-manager
```

---

## 🚀 Usage

### Starting the Manager

```bash
sudo unbound-manager
```

### Main Menu Overview

```
╔════════════════════════════════════════════════════════════════╗
║                UNBOUND DNS SERVER MANAGER                      ║
║                     Version 2.0.1                              ║
╚════════════════════════════════════════════════════════════════╝

┌─ INSTALLATION & SETUP ──────────┐
│ 1. Install Unbound              │
│ 2. Fix Existing Installation    │
│ 3. Update Unbound Version       │
└─────────────────────────────────┘

┌─ CONFIGURATION ─────────────────┐
│ 4. Manage Configuration         │
│ 5. Configure Redis Integration  │
│ 6. DNSSEC Management           │
└─────────────────────────────────┘
```

### Quick Start - First Time Setup

```bash
# 1. Run the manager
sudo unbound-manager

# 2. Select option 1 to install Unbound
# 3. Select option 5 to configure Redis caching
# 4. Select option 11 to test your setup
```

---

## 🗑️ Uninstallation

### Complete Uninstall (Remove Everything)

Copy and paste this command to completely remove Unbound Manager and Unbound:

```bash
# Complete removal of Unbound Manager and Unbound DNS
cd ~/unbound-manager && \
sudo python3 -c "
from unbound_manager.cli import UnboundManagerCLI
cli = UnboundManagerCLI()
cli.uninstall_manager()
" || \
(sudo pip3 uninstall -y unbound-manager && \
sudo rm -rf ~/unbound-manager && \
echo '✅ Unbound Manager removed')
```

### Remove Only Unbound Manager (Keep DNS Server)

```bash
# Remove only the manager, keep Unbound DNS running
sudo pip3 uninstall -y unbound-manager && \
sudo rm -rf ~/unbound-manager && \
echo "✅ Manager removed. Unbound DNS still running"
```

### Remove Only Unbound DNS (Keep Manager)

```bash
# Stop and remove Unbound, keep the manager
sudo systemctl stop unbound && \
sudo systemctl disable unbound && \
sudo rm -f /usr/sbin/unbound* && \
sudo rm -rf /etc/unbound && \
echo "✅ Unbound DNS removed. Manager still installed"
```

---

## 📊 Features in Detail

### What Can It Do?

| Feature | Description |
|---------|-------------|
| **Auto Install** | Downloads and compiles Unbound from source |
| **DNSSEC** | Automatic DNSSEC validation with trust anchor updates |
| **Redis Cache** | High-performance caching backend integration |
| **Auto Backup** | Creates backups before any configuration change |
| **Troubleshoot** | Diagnoses and fixes common issues automatically |
| **Performance Test** | Benchmarks DNS query performance |
| **Service Control** | Start/stop/restart Unbound and Redis from UI |
| **Update Manager** | Built-in updater for both Unbound and the manager |

---

## 🆘 Troubleshooting

### Common Issues and Solutions

#### ❌ "Must be run as root"
```bash
# Always run with sudo
sudo unbound-manager
```

#### ❌ "Unbound service not running"
```bash
# The manager will detect this and offer to fix it
sudo systemctl start unbound
```

#### ❌ "Redis connection failed"
```bash
# Restart Redis service
sudo systemctl restart redis-server
```

#### ❌ "DNS resolution not working"
```bash
# Quick test
dig @127.0.0.1 google.com
```

---

## 📁 File Locations

```
/etc/unbound/               # Main configuration directory
├── unbound.conf           # Main config file
├── unbound.conf.d/        # Modular configs
├── root.key               # DNSSEC trust anchor
├── root.hints             # Root servers list
└── backups/               # Automatic backups

~/unbound-manager/          # Manager source code
```

---

## 🔄 Updates

### Update Unbound Manager

```bash
sudo unbound-manager
# Select: 15 (Update Unbound Manager)
```

### Update Unbound DNS

```bash
sudo unbound-manager
# Select: 3 (Update Unbound Version)
```

### Manual Update

```bash
cd ~/unbound-manager && \
git pull && \
sudo pip3 install -e . --upgrade && \
echo "✅ Update complete"
```

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

```bash
# Fork and clone your fork
git clone https://github.com/YOUR_USERNAME/unbound-manager.git
cd unbound-manager

# Create a feature branch
git checkout -b feature/your-feature

# Make changes and commit
git commit -m "Add your feature"

# Push and create PR
git push origin feature/your-feature
```

---

## 🙏 Acknowledgments

- **[NLnet Labs](https://nlnetlabs.nl/)** - For creating Unbound DNS
- **[Rich](https://github.com/Textualize/rich)** - For the beautiful terminal UI
- **[Redis](https://redis.io/)** - For the caching backend

---

<div align="center">

### ⭐ Star this project if you find it helpful!

**[Report Issues](https://github.com/regix1/unbound-manager/issues)** • **[Discussions](https://github.com/regix1/unbound-manager/discussions)**

Made with ❤️ for the DNS community

</div>