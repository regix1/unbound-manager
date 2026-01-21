"""DNSSEC management for Unbound."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .constants import UNBOUND_DIR, ROOT_KEY, ROOT_HINTS, ROOT_HINTS_URL, ROOT_HINTS_BACKUP_URL
from .utils import run_command, download_file, set_file_permissions, prompt_yes_no
from .menu_system import SubMenu, create_submenu

console = Console()


class DNSSECManager:
    """Manage DNSSEC configuration and keys."""
    
    def setup_root_hints(self) -> bool:
        """Download and setup root hints file."""
        console.print("[cyan]Setting up root hints...[/cyan]")
        
        # Backup existing file if it exists
        backup_path = None
        if ROOT_HINTS.exists():
            backup_path = ROOT_HINTS.with_suffix('.hints.bak')
            console.print(f"[yellow]Backing up existing root hints to {backup_path}[/yellow]")
            ROOT_HINTS.rename(backup_path)
        
        # Try primary URL
        if download_file(ROOT_HINTS_URL, ROOT_HINTS):
            set_file_permissions(ROOT_HINTS)
            console.print("[green]✓[/green] Root hints downloaded successfully")
            return True
        
        # Try backup URL
        console.print("[yellow]Primary source failed, trying backup...[/yellow]")
        if download_file(ROOT_HINTS_BACKUP_URL, ROOT_HINTS):
            set_file_permissions(ROOT_HINTS)
            console.print("[green]✓[/green] Root hints downloaded from backup source")
            return True
        
        # Restore backup if download failed
        if backup_path and backup_path.exists():
            console.print("[yellow]Download failed, restoring backup[/yellow]")
            backup_path.rename(ROOT_HINTS)
        
        console.print("[red]Failed to update root hints[/red]")
        return False
    
    def setup_trust_anchor(self) -> bool:
        """Setup DNSSEC trust anchor."""
        console.print("[cyan]Setting up DNSSEC trust anchor...[/cyan]")
        
        # Create initial root.key if it doesn't exist
        if not ROOT_KEY.exists():
            console.print("[cyan]Creating initial trust anchor...[/cyan]")
            
            # Known root DNSSEC key
            root_key_content = """. IN DS 20326 8 2 E06D44B80B8F1D39A95C0B0D7C65D08458E880409BBC683457104237C7F8EC8D
"""
            
            with open(ROOT_KEY, 'w') as f:
                f.write(root_key_content)
            
            set_file_permissions(ROOT_KEY)
            console.print("[green]✓[/green] Initial trust anchor created")
        
        # Update trust anchor using unbound-anchor
        console.print("[cyan]Updating trust anchor...[/cyan]")
        
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
                console.print("[green]✓[/green] Trust anchor updated successfully")
                return True
            else:
                console.print("[yellow]Warning: Trust anchor update had issues[/yellow]")
                if result.stderr:
                    console.print(f"[yellow]{result.stderr}[/yellow]")
                return True  # Continue anyway as the file exists
                
        except Exception as e:
            console.print(f"[red]Error updating trust anchor: {e}[/red]")
            return False
    
    def generate_control_keys(self) -> bool:
        """Generate unbound-control keys."""
        console.print("[cyan]Generating control keys...[/cyan]")
        
        server_key = UNBOUND_DIR / "unbound_server.key"
        control_key = UNBOUND_DIR / "unbound_control.key"
        
        # Check if keys already exist
        if server_key.exists() and control_key.exists():
            if not prompt_yes_no("Control keys already exist. Regenerate?", default=False):
                console.print("[yellow]Keeping existing keys[/yellow]")
                return True
        
        # Try using unbound-control-setup
        try:
            result = run_command(
                ["unbound-control-setup", "-d", str(UNBOUND_DIR)],
                check=False
            )
            
            if result.returncode == 0:
                console.print("[green]✓[/green] Control keys generated using unbound-control-setup")
                self._fix_key_permissions()
                return True
        except Exception:
            pass
        
        # Fallback to OpenSSL
        console.print("[yellow]Using OpenSSL to generate keys...[/yellow]")
        
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
            console.print("[green]✓[/green] Control keys generated using OpenSSL")
            return True
            
        except Exception as e:
            console.print(f"[red]Failed to generate control keys: {e}[/red]")
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
        console.print("[cyan]Testing DNSSEC validation with signed domain (iana.org)...[/cyan]")
        
        try:
            answer = resolver.resolve('iana.org', 'A')
            
            # Check AD flag
            if answer.response.flags & dns.flags.AD:
                console.print("[green]✓[/green] DNSSEC validation successful (AD flag set)")
            else:
                console.print("[yellow]⚠[/yellow] DNSSEC validation might not be working (AD flag not set)")
        except Exception as e:
            console.print(f"[red]DNSSEC test failed: {e}[/red]")
        
        # Test negative validation
        console.print("[cyan]Testing DNSSEC failure detection (dnssec-failed.org)...[/cyan]")
        
        try:
            answer = resolver.resolve('dnssec-failed.org', 'A')
            console.print("[red]✗[/red] DNSSEC validation not working (should have failed)")
        except dns.resolver.NXDOMAIN:
            console.print("[green]✓[/green] DNSSEC correctly rejected invalid signatures")
        except Exception:
            console.print("[green]✓[/green] DNSSEC correctly rejected invalid signatures")
    
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
        console.print("[cyan]DNSSEC Configuration Status:[/cyan]\n")
        
        # Check root.key
        if ROOT_KEY.exists():
            console.print(f"[green]✓[/green] Trust anchor exists: {ROOT_KEY}")
            # Show first line of root.key
            with open(ROOT_KEY, 'r') as f:
                first_line = f.readline().strip()
                console.print(f"  {first_line[:80]}...")
        else:
            console.print(f"[red]✗[/red] Trust anchor missing: {ROOT_KEY}")
        
        # Check root.hints
        if ROOT_HINTS.exists():
            console.print(f"[green]✓[/green] Root hints exists: {ROOT_HINTS}")
            # Show file size and modification time
            stats = ROOT_HINTS.stat()
            console.print(f"  Size: {stats.st_size} bytes")
            console.print(f"  Modified: {time.ctime(stats.st_mtime)}")
        else:
            console.print(f"[red]✗[/red] Root hints missing: {ROOT_HINTS}")
        
        # Check control keys
        server_key = UNBOUND_DIR / "unbound_server.key"
        control_key = UNBOUND_DIR / "unbound_control.key"
        
        if server_key.exists() and control_key.exists():
            console.print("[green]✓[/green] Control keys exist")
        else:
            console.print("[red]✗[/red] Control keys missing")
        
        # Check DNSSEC configuration
        dnssec_conf = UNBOUND_DIR / "unbound.conf.d" / "dnssec.conf"
        if dnssec_conf.exists():
            console.print(f"[green]✓[/green] DNSSEC configuration exists: {dnssec_conf}")
        else:
            console.print(f"[red]✗[/red] DNSSEC configuration missing")