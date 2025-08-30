#!/usr/bin/env python3
"""Quick fix for boolean values in existing Unbound configurations."""

import re
from pathlib import Path

def fix_boolean_values():
    """Fix boolean values in server.conf."""
    server_conf = Path("/etc/unbound/unbound.conf.d/server.conf")
    
    if not server_conf.exists():
        print("Server configuration not found")
        return False
    
    with open(server_conf, 'r') as f:
        content = f.read()
    
    # Replace boolean values
    replacements = [
        (r'do-ip4:\s+true', 'do-ip4: yes'),
        (r'do-ip4:\s+false', 'do-ip4: no'),
        (r'do-ip6:\s+true', 'do-ip6: yes'),
        (r'do-ip6:\s+false', 'do-ip6: no'),
        (r'do-udp:\s+true', 'do-udp: yes'),
        (r'do-udp:\s+false', 'do-udp: no'),
        (r'do-tcp:\s+true', 'do-tcp: yes'),
        (r'do-tcp:\s+false', 'do-tcp: no'),
        (r'prefer-ip6:\s+true', 'prefer-ip6: yes'),
        (r'prefer-ip6:\s+false', 'prefer-ip6: no'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    
    # Backup original
    backup_path = server_conf.with_suffix('.conf.backup')
    server_conf.rename(backup_path)
    print(f"Backup created: {backup_path}")
    
    # Write fixed content
    with open(server_conf, 'w') as f:
        f.write(content)
    
    print("Configuration fixed")
    return True

if __name__ == "__main__":
    import sys
    import os
    
    if os.geteuid() != 0:
        print("This script must be run as root")
        sys.exit(1)
    
    if fix_boolean_values():
        print("Run 'systemctl restart unbound' to apply changes")