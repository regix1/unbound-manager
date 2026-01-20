"""Constants used throughout the application."""

import os
from pathlib import Path

def get_app_version():
    """Get application version from VERSION file."""
    import glob
    
    # Try multiple paths to find VERSION file
    possible_paths = [
        Path(__file__).parent.parent / "VERSION",  # Development
        Path.home() / "unbound-manager" / "VERSION",  # User install
    ]
    
    # Dynamically find Python site-packages directories
    for base_path in ["/usr/local/lib", "/usr/lib"]:
        python_dirs = glob.glob(f"{base_path}/python3.*")
        for python_dir in python_dirs:
            possible_paths.extend([
                Path(python_dir) / "dist-packages/unbound_manager" / "VERSION",
                Path(python_dir) / "site-packages/unbound_manager" / "VERSION",
            ])
    
    for version_path in possible_paths:
        if version_path.exists():
            return version_path.read_text().strip()
    
    return "unknown"

# Version
APP_VERSION = get_app_version()

# Data directories
DATA_DIR = Path(__file__).parent.parent / "data"
TEMPLATES_DIR = DATA_DIR / "templates"
CONFIGS_DIR = DATA_DIR / "configs"
SYSTEMD_DIR = DATA_DIR / "systemd"

# Paths
UNBOUND_DIR = Path("/etc/unbound")
UNBOUND_CONF = UNBOUND_DIR / "unbound.conf"
UNBOUND_CONF_D = UNBOUND_DIR / "unbound.conf.d"
BACKUP_DIR = UNBOUND_DIR / "backups"
ROOT_KEY = UNBOUND_DIR / "root.key"
ROOT_HINTS = UNBOUND_DIR / "root.hints"

# Redis
REDIS_SOCKET = Path("/var/run/redis/redis.sock")
REDIS_CONF = Path("/etc/redis/redis.conf")

# Systemd
SYSTEMD_SERVICE = Path("/etc/systemd/system/unbound.service")

# Service names (to avoid typos and make changes easy)
UNBOUND_SERVICE = "unbound"
REDIS_SERVICE = "redis-server"

# URLs
UNBOUND_RELEASES_URL = "https://api.github.com/repos/NLnetLabs/unbound/releases"
ROOT_HINTS_URL = "https://www.internic.net/domain/named.cache"
ROOT_HINTS_BACKUP_URL = "https://www.dns.icann.org/services/tools/internic/domain/named.cache"

# Default configuration
DEFAULT_CONFIG = {
    "server_ip": "127.0.0.1",
    "num_threads": os.cpu_count() or 1,
    "msg_cache_size": "64m",
    "rrset_cache_size": "128m",
    "cache_min_ttl": 300,
    "cache_max_ttl": 86400,
    "verbosity": 1,
    "do_ip4": True,
    "do_ip6": False,
    "do_udp": True,
    "do_tcp": True,
    "prefer_ip6": False,
}

# Terminal colors (for compatibility with existing features)
COLORS = {
    "RED": "[red]",
    "GREEN": "[green]",
    "YELLOW": "[yellow]",
    "BLUE": "[blue]",
    "MAGENTA": "[magenta]",
    "CYAN": "[cyan]",
    "WHITE": "[white]",
    "BOLD": "[bold]",
    "NC": "[/]",  # No color / reset
}

# Test domains
TEST_DOMAINS = {
    "basic": "google.com",
    "dnssec": "iana.org",
    "dnssec_fail": "dnssec-failed.org",
    "ipv4": "example.com",
    "ipv6": "google.com",
    "mx": "gmail.com",
    "txt": "google.com",
}

# DNS Upstream Providers
# Each provider has: name, description, servers (with DoT info), and whether it's encrypted
DNS_PROVIDERS = {
    "cloudflare": {
        "name": "Cloudflare",
        "description": "Fastest public DNS, privacy-focused, KPMG audited",
        "encrypted": True,
        "servers": [
            {"ip": "1.1.1.1", "port": 853, "hostname": "cloudflare-dns.com"},
            {"ip": "1.0.0.1", "port": 853, "hostname": "cloudflare-dns.com"},
            {"ip": "2606:4700:4700::1111", "port": 853, "hostname": "cloudflare-dns.com", "ipv6": True},
            {"ip": "2606:4700:4700::1001", "port": 853, "hostname": "cloudflare-dns.com", "ipv6": True},
        ],
    },
    "cloudflare_malware": {
        "name": "Cloudflare (Malware Blocking)",
        "description": "Cloudflare with malware filtering enabled",
        "encrypted": True,
        "servers": [
            {"ip": "1.1.1.2", "port": 853, "hostname": "security.cloudflare-dns.com"},
            {"ip": "1.0.0.2", "port": 853, "hostname": "security.cloudflare-dns.com"},
        ],
    },
    "cloudflare_family": {
        "name": "Cloudflare (Family Safe)",
        "description": "Cloudflare with malware + adult content filtering",
        "encrypted": True,
        "servers": [
            {"ip": "1.1.1.3", "port": 853, "hostname": "family.cloudflare-dns.com"},
            {"ip": "1.0.0.3", "port": 853, "hostname": "family.cloudflare-dns.com"},
        ],
    },
    "quad9": {
        "name": "Quad9",
        "description": "Swiss non-profit, maximum privacy, malware blocking",
        "encrypted": True,
        "servers": [
            {"ip": "9.9.9.9", "port": 853, "hostname": "dns.quad9.net"},
            {"ip": "149.112.112.112", "port": 853, "hostname": "dns.quad9.net"},
            {"ip": "2620:fe::fe", "port": 853, "hostname": "dns.quad9.net", "ipv6": True},
            {"ip": "2620:fe::9", "port": 853, "hostname": "dns.quad9.net", "ipv6": True},
        ],
    },
    "quad9_unsecured": {
        "name": "Quad9 (No Filtering)",
        "description": "Quad9 without malware blocking",
        "encrypted": True,
        "servers": [
            {"ip": "9.9.9.10", "port": 853, "hostname": "dns10.quad9.net"},
            {"ip": "149.112.112.10", "port": 853, "hostname": "dns10.quad9.net"},
        ],
    },
    "google": {
        "name": "Google DNS",
        "description": "Fast and reliable, DNSSEC support",
        "encrypted": True,
        "servers": [
            {"ip": "8.8.8.8", "port": 853, "hostname": "dns.google"},
            {"ip": "8.8.4.4", "port": 853, "hostname": "dns.google"},
            {"ip": "2001:4860:4860::8888", "port": 853, "hostname": "dns.google", "ipv6": True},
            {"ip": "2001:4860:4860::8844", "port": 853, "hostname": "dns.google", "ipv6": True},
        ],
    },
    "opendns": {
        "name": "OpenDNS (Cisco)",
        "description": "Reliable with phishing protection",
        "encrypted": True,
        "servers": [
            {"ip": "208.67.222.222", "port": 853, "hostname": "dns.opendns.com"},
            {"ip": "208.67.220.220", "port": 853, "hostname": "dns.opendns.com"},
        ],
    },
    "adguard": {
        "name": "AdGuard DNS",
        "description": "Ad and tracker blocking built-in",
        "encrypted": True,
        "servers": [
            {"ip": "94.140.14.14", "port": 853, "hostname": "dns.adguard-dns.com"},
            {"ip": "94.140.15.15", "port": 853, "hostname": "dns.adguard-dns.com"},
        ],
    },
    "adguard_family": {
        "name": "AdGuard DNS (Family)",
        "description": "AdGuard with adult content filtering",
        "encrypted": True,
        "servers": [
            {"ip": "94.140.14.15", "port": 853, "hostname": "family.adguard-dns.com"},
            {"ip": "94.140.15.16", "port": 853, "hostname": "family.adguard-dns.com"},
        ],
    },
    "none": {
        "name": "Full Recursion (No Forwarding)",
        "description": "Query root servers directly - most private, slower",
        "encrypted": False,
        "servers": [],
    },
    "custom_unencrypted": {
        "name": "Custom Unencrypted DNS",
        "description": "Use your own DNS servers (unencrypted)",
        "encrypted": False,
        "servers": [],
    },
}

# Recommended providers shown first in selection menu
DNS_PROVIDER_ORDER = [
    "quad9",
    "cloudflare",
    "cloudflare_malware",
    "google",
    "adguard",
    "none",
    "cloudflare_family",
    "adguard_family",
    "quad9_unsecured",
    "opendns",
    "custom_unencrypted",
]