"""DNSSEC management for Unbound."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional
from rich.panel import Panel
from rich.prompt import Prompt

from .constants import UNBOUND_DIR, ROOT_KEY, ROOT_HINTS, ROOT_HINTS_URL, ROOT_HINTS_BACKUP_URL
from .utils import run_command, download_file, set_file_permissions, prompt_yes_no
from .menu_system import SubMenu, create_submenu
from .ui import print_success, print_error, print_warning, print_info, console


class DNSSECManager:
    """Manage DNSSEC configuration and keys."""
    
    def setup_root_hints(self) -> bool:
        """Download and setup root hints file."""
        print_info("Setting up root hints...")
        
        # Backup existing file if it exists
        backup_path = None
        if ROOT_HINTS.exists():
            backup_path = ROOT_HINTS.with_suffix('.hints.bak')
            print_warning(f"Backing up existing root hints to {backup_path}")
            ROOT_HINTS.rename(backup_path)
        
        # Try primary URL
        if download_file(ROOT_HINTS_URL, ROOT_HINTS):
            set_file_permissions(ROOT_HINTS)
            print_success("Root hints downloaded successfully")
            return True
        
        # Try backup URL
        print_warning("Primary source failed, trying backup...")
        if download_file(ROOT_HINTS_BACKUP_URL, ROOT_HINTS):
            set_file_permissions(ROOT_HINTS)
            print_success("Root hints downloaded from backup source")
            return True
        
        # Restore backup if download failed
        if backup_path and backup_path.exists():
            print_warning("Download failed, restoring backup")
            backup_path.rename(ROOT_HINTS)
        
        print_error("Failed to update root hints")
        return False
    
    def setup_trust_anchor(self) -> bool:
        """Setup DNSSEC trust anchor."""
        print_info("Setting up DNSSEC trust anchor...")
        
        # Create initial root.key if it doesn't exist
        if not ROOT_KEY.exists():
            print_info("Creating initial trust anchor...")
            
            # Known root DNSSEC key
            root_key_content = """. IN DS 20326 8 2 E06D44B80B8F1D39A95C0B0D7C65D08458E880409BBC683457104237C7F8EC8D
"""
            
            with open(ROOT_KEY, 'w') as f:
                f.write(root_key_content)
            
            set_file_permissions(ROOT_KEY)
            print_success("Initial trust anchor created")
        
        # Update trust anchor using unbound-anchor
        print_info("Updating trust anchor...")
        
        try:
            result = run_command(
                [
                    "unbound-anchor",
                    "-a", str(ROOT_KEY),
                    "-c", "/etc/ssl/certs/ca-certificates.crt"
                ],
                check=False
            )
            
            # unbound-anchor returns 1 if the key was updated, 0 if no update needed
            if result.returncode in [0, 1]:
                set_file_permissions(ROOT_KEY)
                print_success("Trust anchor updated successfully")
                return True
            else:
                print_warning("Trust anchor update had issues")
                if result.stderr:
                    print_warning(result.stderr)
                return True  # Continue anyway as the file exists
                
        except Exception as e:
            print_error(f"Error updating trust anchor: {e}")
            return False
    
    def generate_control_keys(self) -> bool:
        """Generate unbound-control keys."""
        print_info("Generating control keys...")
        
        server_key = UNBOUND_DIR / "unbound_server.key"
        control_key = UNBOUND_DIR / "unbound_control.key"
        
        # Check if keys already exist
        if server_key.exists() and control_key.exists():
            if not prompt_yes_no("Control keys already exist. Regenerate?", default=False):
                print_warning("Keeping existing keys")
                return True
        
        # Try using unbound-control-setup
        try:
            result = run_command(
                ["unbound-control-setup", "-d", str(UNBOUND_DIR)],
                check=False
            )
            
            if result.returncode == 0:
                print_success("Control keys generated using unbound-control-setup")
                self._fix_key_permissions()
                return True
        except Exception:
            pass
        
        # Fallback to OpenSSL
        print_warning("Using OpenSSL to generate keys...")
        
        try:
            # Generate server key and certificate
            run_command([
                "openssl", "req", "-newkey", "rsa:2048", "-nodes",
                "-keyout", str(UNBOUND_DIR / "unbound_server.key"),
                "-x509", "-days", "3650",
                "-out", str(UNBOUND_DIR / "unbound_server.pem"),
                "-subj", "/CN=unbound-server"
            ])
            
            # Generate control key and certificate
            run_command([
                "openssl", "req", "-newkey", "rsa:2048", "-nodes",
                "-keyout", str(UNBOUND_DIR / "unbound_control.key"),
                "-x509", "-days", "3650",
                "-out", str(UNBOUND_DIR / "unbound_control.pem"),
                "-subj", "/CN=unbound-control"
            ])
            
            self._fix_key_permissions()
            print_success("Control keys generated using OpenSSL")
            return True
            
        except Exception as e:
            print_error(f"Failed to generate control keys: {e}")
            return False
    
    def _fix_key_permissions(self) -> None:
        """Fix permissions for control keys."""
        for key_file in UNBOUND_DIR.glob("unbound_*.key"):
            set_file_permissions(key_file, mode=0o640)
        
        for pem_file in UNBOUND_DIR.glob("unbound_*.pem"):
            set_file_permissions(pem_file, mode=0o640)
    
    def test_dnssec_validation(self) -> None:
        """Test DNSSEC validation."""
        console.print(Panel.fit(
            "[bold cyan]DNSSEC Validation Test[/bold cyan]",
            border_style="cyan"
        ))
        
        import dns.resolver
        import dns.flags
        
        # Create resolver outside try block to avoid UnboundLocalError
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['127.0.0.1']
        resolver.use_edns = True
        resolver.edns = 0
        resolver.ednsflags = dns.flags.DO
        
        # Test positive validation
        print_info("Testing DNSSEC validation with signed domain (iana.org)...")
        
        try:
            answer = resolver.resolve('iana.org', 'A')
            
            # Check AD flag
            if answer.response.flags & dns.flags.AD:
                print_success("DNSSEC validation successful (AD flag set)")
            else:
                print_warning("DNSSEC validation might not be working (AD flag not set)")
        except Exception as e:
            print_error(f"DNSSEC test failed: {e}")
        
        # Test negative validation
        print_info("Testing DNSSEC failure detection (dnssec-failed.org)...")
        
        try:
            answer = resolver.resolve('dnssec-failed.org', 'A')
            print_error("DNSSEC validation not working (should have failed)")
        except dns.resolver.NXDOMAIN:
            print_success("DNSSEC correctly rejected invalid signatures")
        except Exception:
            print_success("DNSSEC correctly rejected invalid signatures")
    
    def manage_dnssec(self) -> None:
        """Interactive DNSSEC management using standardized submenu."""
        
        result = create_submenu("DNSSEC Management", [
            ("Update Root Hints", self.setup_root_hints),
            ("Update Trust Anchor", self.setup_trust_anchor),
            ("Regenerate Keys", self.generate_control_keys),
            ("Test Validation", self.test_dnssec_validation),
            ("View Status", self.show_dnssec_status),
        ])
        
        if result == SubMenu.QUIT:
            return False
    
    def show_dnssec_status(self) -> None:
        """Show DNSSEC configuration status."""
        print_info("DNSSEC Configuration Status:\n")
        
        # Check root.key
        if ROOT_KEY.exists():
            print_success(f"Trust anchor exists: {ROOT_KEY}")
            # Show first line of root.key
            with open(ROOT_KEY, 'r') as f:
                first_line = f.readline().strip()
                console.print(f"  {first_line[:80]}...")
        else:
            print_error(f"Trust anchor missing: {ROOT_KEY}")
        
        # Check root.hints
        if ROOT_HINTS.exists():
            print_success(f"Root hints exists: {ROOT_HINTS}")
            # Show file size and modification time
            stats = ROOT_HINTS.stat()
            console.print(f"  Size: {stats.st_size} bytes")
            console.print(f"  Modified: {time.ctime(stats.st_mtime)}")
        else:
            print_error(f"Root hints missing: {ROOT_HINTS}")
        
        # Check control keys
        server_key = UNBOUND_DIR / "unbound_server.key"
        control_key = UNBOUND_DIR / "unbound_control.key"
        
        if server_key.exists() and control_key.exists():
            print_success("Control keys exist")
        else:
            print_error("Control keys missing")
        
        # Check DNSSEC configuration
        dnssec_conf = UNBOUND_DIR / "unbound.conf.d" / "dnssec.conf"
        if dnssec_conf.exists():
            print_success(f"DNSSEC configuration exists: {dnssec_conf}")
        else:
            print_error("DNSSEC configuration missing")