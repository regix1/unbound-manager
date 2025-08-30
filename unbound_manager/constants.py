"""Constants used throughout the application."""

import os
from pathlib import Path

def get_app_version():
    """Get application version from VERSION file."""
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "2.0.5"  # Updated fallback version

# Version
APP_VERSION = get_app_version()

# Paths
UNBOUND_DIR = Path("/etc/unbound")
UNBOUND_CONF = UNBOUND_DIR / "unbound.conf"
UNBOUND_CONF_D = UNBOUND_DIR / "unbound.conf.d"
BACKUP_DIR = UNBOUND_DIR / "backups"
ROOT_KEY = UNBOUND_DIR / "root.key"
ROOT_HINTS = UNBOUND_DIR / "root.hints"
DATA_DIR = Path(__file__).parent.parent / "data"
TEMPLATES_DIR = DATA_DIR / "templates"
CONFIGS_DIR = DATA_DIR / "configs"
SYSTEMD_DIR = DATA_DIR / "systemd"

# Redis
REDIS_SOCKET = Path("/var/run/redis/redis.sock")
REDIS_CONF = Path("/etc/redis/redis.conf")

# Systemd
SYSTEMD_SERVICE = Path("/etc/systemd/system/unbound.service")

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