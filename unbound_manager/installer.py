"""Unbound installation and management module."""

from __future__ import annotations

import os
import time
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.prompt import Prompt

from .constants import (
    UNBOUND_DIR, UNBOUND_CONF, UNBOUND_CONF_D,
    UNBOUND_RELEASES_URL, SYSTEMD_SERVICE,
    UNBOUND_SERVICE, REDIS_SERVICE
)
from .utils import (
    run_command, ensure_user_exists, ensure_directory,
    install_packages, check_package_installed, prompt_yes_no,
    get_server_ip, check_service_status, restart_service
)
from .config_manager import ConfigManager
from .redis_manager import RedisManager
from .dnssec import DNSSECManager
from .menu_system import SubMenu

console = Console()


class UnboundInstaller:
    """Handle Unbound installation and updates."""
    
    def __init__(self):
        """Initialize the installer."""
        self.config_manager = ConfigManager()
        self.redis_manager = RedisManager()
        self.dnssec_manager = DNSSECManager()
    
    def get_available_versions(self) -> List[str]:
        """Fetch available Unbound versions from GitHub."""
        try:
            response = requests.get(UNBOUND_RELEASES_URL, timeout=10)
            response.raise_for_status()
            releases = response.json()
            
            versions = []
            for release in releases[:5]:  # Get last 5 releases
                tag = release.get('tag_name', '')
                if tag.startswith('release-'):
                    version = tag.replace('release-', '')
                    versions.append(version)
            
            return versions
        except Exception as e:
            console.print(f"[yellow]Could not fetch versions from GitHub: {e}[/yellow]")
            # Return default versions as fallback
            return ["1.22.0", "1.21.1", "1.21.0", "1.20.0", "1.19.3"]
    
    def select_version(self) -> str:
        """Let user select an Unbound version with standard navigation."""
        versions = self.get_available_versions()
        
        console.clear()
        console.print("┌" + "─" * 58 + "┐")
        console.print("│          [bold cyan]SELECT UNBOUND VERSION[/bold cyan]                       │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        for i, version in enumerate(versions, 1):
            console.print(f"  [{i}] {version}")
        
        console.print()
        console.print("  ─" * 20)
        console.print("  [r] Return to menu")
        console.print("  [q] Quit")
        console.print()
        
        valid_choices = ["r", "q"] + [str(i) for i in range(1, len(versions) + 1)]
        choice = Prompt.ask("Select version", choices=valid_choices, default="1", show_choices=False)
        
        if choice == "q":
            return SubMenu.QUIT
        if choice == "r":
            return SubMenu.RETURN
        
        selected = versions[int(choice) - 1]
        console.print(f"[green]✓[/green] Selected Unbound version: [bold]{selected}[/bold]")
        return selected
    
    def install_dependencies(self) -> bool:
        """Install required system dependencies."""
        console.print("[cyan]Installing dependencies...[/cyan]")
        
        packages = [
            "build-essential",
            "libssl-dev",
            "libexpat1-dev",
            "libevent-dev",
            "libhiredis-dev",
            "curl",
            "wget",  # Add wget as dependency
            "jq",
            "libnghttp2-dev",
            "python3-dev",
            "libsystemd-dev",
            "swig",
            "protobuf-c-compiler",
            "libprotobuf-c-dev",
            "redis-server",
            "ca-certificates",
            "openssl",
            "ntpdate",
            "bc",
            "net-tools",
        ]
        
        missing_packages = []
        for package in packages:
            if not check_package_installed(package):
                missing_packages.append(package)
        
        if missing_packages:
            if not install_packages(missing_packages):
                console.print("[red]Failed to install dependencies[/red]")
                return False
        
        console.print("[green]✓[/green] Dependencies installed")
        return True
    
    def compile_unbound(self, version: str) -> bool:
        """Download and compile Unbound from source."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Download source
            url = f"https://nlnetlabs.nl/downloads/unbound/unbound-{version}.tar.gz"
            tarball = tmppath / f"unbound-{version}.tar.gz"
            
            console.print(f"[cyan]Downloading Unbound {version}...[/cyan]")
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                ) as progress:
                    task = progress.add_task(f"Downloading...", total=total_size)
                    
                    with open(tarball, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))
            
            except Exception as e:
                console.print(f"[red]Failed to download Unbound: {e}[/red]")
                return False
            
            # Extract
            console.print("[cyan]Extracting source code...[/cyan]")
            run_command(["tar", "-xzf", str(tarball)], cwd=tmpdir)
            
            source_dir = tmppath / f"unbound-{version}"
            
            # Configure
            console.print("[cyan]Configuring Unbound...[/cyan]")
            configure_args = [
                "./configure",
                "--prefix=/usr",
                "--sysconfdir=/etc",
                "--with-libevent",
                "--with-libhiredis",
                "--with-libnghttp2",
                "--with-pidfile=/run/unbound.pid",
                "--with-rootkey-file=/etc/unbound/root.key",
                "--enable-subnet",
                "--enable-tfo-client",
                "--enable-tfo-server",
                "--enable-cachedb",
                "--enable-ipsecmod",
                "--with-ssl",
            ]
            
            try:
                run_command(configure_args, cwd=source_dir, timeout=120)
            except Exception as e:
                console.print(f"[red]Configuration failed: {e}[/red]")
                return False
            
            # Compile
            console.print("[cyan]Compiling Unbound (this may take several minutes)...[/cyan]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Compiling...", total=None)
                
                try:
                    # Get number of CPU cores for parallel compilation
                    cpu_count = os.cpu_count() or 1
                    run_command(["make", f"-j{cpu_count}"], cwd=source_dir, timeout=600)
                    progress.update(task, completed=True)
                except Exception as e:
                    console.print(f"[red]Compilation failed: {e}[/red]")
                    return False
            
            # Install
            console.print("[cyan]Installing Unbound...[/cyan]")
            try:
                run_command(["make", "install"], cwd=source_dir)
                run_command(["ldconfig"])
            except Exception as e:
                console.print(f"[red]Installation failed: {e}[/red]")
                return False
            
            console.print("[green]✓[/green] Unbound compiled and installed successfully")
            return True
    
    def update_unbound(self) -> None:
        """Update Unbound to a newer version."""
        console.print(Panel.fit(
            "[bold cyan]Update Unbound[/bold cyan]\n\n"
            "This will update Unbound to a newer version while preserving your configuration.",
            border_style="cyan"
        ))
        
        # Check current version
        current_version = None
        try:
            result = run_command(["unbound", "-V"], check=False)
            if result.returncode == 0:
                current_version = result.stdout.split()[1]
                console.print(f"[cyan]Current version:[/cyan] {current_version}")
        except Exception:
            pass
        
        # Backup configuration FIRST
        from .backup import BackupManager
        backup_manager = BackupManager()
        backup_path = backup_manager.create_backup("before_update")
        
        # Select new version
        version = self.select_version()
        
        # Check if same version
        if current_version and version in current_version:
            console.print(f"[yellow]You are already running version {version}[/yellow]")
            if not prompt_yes_no("Continue anyway?", default=False):
                console.print("[yellow]Update cancelled[/yellow]")
                return
        
        # IMPORTANT: Download and compile BEFORE stopping Unbound
        console.print("[cyan]Pre-downloading and compiling Unbound (DNS still working)...[/cyan]")
        
        # Create temp directory for compilation
        temp_dir = Path(tempfile.mkdtemp(prefix="unbound_update_"))
        tarball = temp_dir / f"unbound-{version}.tar.gz"
        download_successful = False
        compilation_successful = False
        
        try:
            # Download while DNS is working
            url = f"https://nlnetlabs.nl/downloads/unbound/unbound-{version}.tar.gz"
            console.print(f"[cyan]Downloading from {url}...[/cyan]")
            
            # Try method 1: requests
            try:
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                ) as progress:
                    task = progress.add_task(f"Downloading {version}...", total=total_size)
                    
                    with open(tarball, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))
                
                download_successful = True
                console.print("[green]✓[/green] Download successful")
                
            except Exception as e:
                console.print(f"[yellow]Download with requests failed: {e}[/yellow]")
                
                # Try method 2: wget
                console.print("[cyan]Trying wget...[/cyan]")
                result = run_command(
                    ["wget", "-O", str(tarball), url],
                    check=False,
                    timeout=60
                )
                if result.returncode == 0:
                    download_successful = True
                    console.print("[green]✓[/green] Download successful with wget")
                else:
                    # Try method 3: curl
                    console.print("[cyan]Trying curl...[/cyan]")
                    result = run_command(
                        ["curl", "-L", "-o", str(tarball), url],
                        check=False,
                        timeout=60
                    )
                    if result.returncode == 0:
                        download_successful = True
                        console.print("[green]✓[/green] Download successful with curl")
            
            if not download_successful:
                console.print("[red]Failed to download Unbound source[/red]")
                shutil.rmtree(temp_dir)
                return
            
            # Extract source
            console.print("[cyan]Extracting source code...[/cyan]")
            run_command(["tar", "-xzf", str(tarball)], cwd=temp_dir)
            
            source_dir = temp_dir / f"unbound-{version}"
            if not source_dir.exists():
                console.print("[red]Failed to extract source[/red]")
                shutil.rmtree(temp_dir)
                return
            
            # Configure
            console.print("[cyan]Configuring Unbound build...[/cyan]")
            configure_args = [
                "./configure",
                "--prefix=/usr",
                "--sysconfdir=/etc",
                "--with-libevent",
                "--with-libhiredis",
                "--with-libnghttp2",
                "--with-pidfile=/run/unbound.pid",
                "--with-rootkey-file=/etc/unbound/root.key",
                "--enable-subnet",
                "--enable-tfo-client",
                "--enable-tfo-server",
                "--enable-cachedb",
                "--enable-ipsecmod",
                "--with-ssl",
            ]
            
            run_command(configure_args, cwd=source_dir, timeout=120)
            console.print("[green]✓[/green] Configuration successful")
            
            # Compile
            console.print("[cyan]Compiling Unbound (this may take several minutes)...[/cyan]")
            cpu_count = os.cpu_count() or 1
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Compiling...", total=None)
                run_command(["make", f"-j{cpu_count}"], cwd=source_dir, timeout=600)
                progress.update(task, completed=True)
            
            console.print("[green]✓[/green] Compilation successful")
            compilation_successful = True
            
            # NOW stop Unbound for the quick install
            console.print("[cyan]Stopping Unbound service for installation...[/cyan]")
            run_command(["systemctl", "stop", UNBOUND_SERVICE])
            
            # Install (should be quick since already compiled)
            console.print("[cyan]Installing new Unbound version...[/cyan]")
            run_command(["make", "install"], cwd=source_dir)
            run_command(["ldconfig"])
            console.print("[green]✓[/green] Installation successful")
            
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
            # Start service immediately
            console.print("[cyan]Starting Unbound service...[/cyan]")
            run_command(["systemctl", "start", UNBOUND_SERVICE])
            
            # Wait for service to be ready
            time.sleep(3)
            
            # Verify service is running
            if check_service_status(UNBOUND_SERVICE):
                console.print("[green]✓[/green] Unbound service started successfully")
                
                # Test DNS resolution
                test_result = run_command(
                    ["dig", "@127.0.0.1", "+short", "example.com"],
                    check=False,
                    timeout=5
                )
                if test_result.returncode == 0 and test_result.stdout.strip():
                    console.print("[green]✓[/green] DNS resolution working")
                    
                    # Show new version
                    try:
                        result = run_command(["unbound", "-V"], check=False)
                        if result.returncode == 0:
                            new_version = result.stdout.split()[1]
                            console.print(f"[green]✓[/green] Successfully updated to version: [bold]{new_version}[/bold]")
                    except Exception:
                        pass
                else:
                    console.print("[yellow]⚠[/yellow] DNS resolution test failed")
            else:
                console.print("[red]Unbound service failed to start[/red]")
                raise Exception("Service failed to start after update")
                
        except Exception as e:
            console.print(f"[red]Update failed: {e}[/red]")
            
            # Clean up temp directory if it exists
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
            
            # Restore from backup
            console.print("[yellow]Restoring from backup...[/yellow]")
            backup_manager.restore_specific_backup(backup_path)
            run_command(["systemctl", "start", UNBOUND_SERVICE])
            console.print("[green]✓[/green] Restored from backup")
    
    def setup_directories(self) -> None:
        """Create necessary directories with proper permissions."""
        console.print("[cyan]Setting up directories...[/cyan]")
        
        ensure_directory(UNBOUND_DIR)
        ensure_directory(UNBOUND_CONF_D)
        ensure_directory(UNBOUND_DIR / "backups")
        ensure_directory(Path("/var/lib/unbound"))
        
        console.print("[green]✓[/green] Directories created")
    
    def create_systemd_service(self) -> None:
        """Create systemd service file."""
        console.print("[cyan]Creating systemd service...[/cyan]")
        
        self.config_manager.render_template(
            "unbound.service.j2",
            SYSTEMD_SERVICE,
            {}
        )
        
        run_command(["systemctl", "daemon-reload"])
        console.print("[green]✓[/green] Systemd service created")
    
    def install_unbound(self) -> None:
        """Perform fresh Unbound installation."""
        console.print(Panel.fit(
            "[bold cyan]Unbound DNS Server Installation[/bold cyan]\n\n"
            "This will install and configure Unbound DNS server on your system.",
            border_style="cyan"
        ))
        
        if not prompt_yes_no("Do you want to proceed with the installation?", default=True):
            console.print("[yellow]Installation cancelled[/yellow]")
            return
        
        # Check if already installed
        try:
            result = run_command(["which", "unbound"], check=False)
            if result.returncode == 0:
                if not prompt_yes_no("Unbound is already installed. Do you want to reinstall?", default=False):
                    console.print("[yellow]Installation cancelled[/yellow]")
                    return
        except Exception:
            pass
        
        # Install dependencies
        if not self.install_dependencies():
            console.print("[red]Installation failed: Could not install dependencies[/red]")
            return
        
        # Select version
        version = self.select_version()
        
        # Compile and install
        if not self.compile_unbound(version):
            console.print("[red]Installation failed: Could not compile Unbound[/red]")
            return
        
        # Create user
        ensure_user_exists()
        
        # Setup directories
        self.setup_directories()
        
        # Create configuration
        console.print("[cyan]Creating configuration...[/cyan]")
        server_ip = get_server_ip()
        
        if prompt_yes_no(f"Use detected server IP ({server_ip})?", default=True):
            self.config_manager.create_full_configuration(server_ip)
        else:
            server_ip = Prompt.ask("Enter server IP address")
            self.config_manager.create_full_configuration(server_ip)
        
        # Select and configure DNS upstream provider
        console.print()
        dns_provider = self.config_manager.select_dns_upstream()
        self.config_manager.create_forwarding_config(dns_provider)
        
        # Setup DNSSEC
        self.dnssec_manager.setup_root_hints()
        self.dnssec_manager.setup_trust_anchor()
        self.dnssec_manager.generate_control_keys()
        
        # Configure Redis
        if prompt_yes_no("Configure Redis integration?", default=True):
            self.redis_manager.configure_redis()
        
        # Create systemd service
        self.create_systemd_service()
        
        # Enable and start service
        console.print("[cyan]Starting Unbound service...[/cyan]")
        run_command(["systemctl", "enable", UNBOUND_SERVICE])
        run_command(["systemctl", "start", UNBOUND_SERVICE])
        
        # Verify installation
        from .tester import UnboundTester
        tester = UnboundTester()
        if tester.verify_installation():
            # Show summary with DNS provider info
            dns_mode = "Encrypted (DoT)" if dns_provider.get("encrypted") else "Unencrypted"
            if dns_provider.get("key") == "none":
                dns_mode = "Full Recursion"
            
            console.print(Panel.fit(
                "[bold green]✓ Unbound installed successfully![/bold green]\n\n"
                f"Version: {version}\n"
                f"Configuration: /etc/unbound/\n"
                f"DNS Provider: {dns_provider.get('name', 'Unknown')}\n"
                f"DNS Mode: {dns_mode}\n"
                f"Service: systemctl status unbound",
                border_style="green"
            ))
        else:
            console.print("[yellow]Installation completed but verification failed[/yellow]")
            console.print("[yellow]Run troubleshooting from the main menu[/yellow]")
    
    def fix_existing_installation(self) -> None:
        """Fix problems with existing Unbound installation."""
        console.print(Panel.fit(
            "[bold cyan]Fix Existing Installation[/bold cyan]\n\n"
            "This will attempt to fix common issues with your Unbound installation.",
            border_style="cyan"
        ))
        
        # Backup first
        from .backup import BackupManager
        backup_manager = BackupManager()
        backup_manager.create_backup("before_fix")
        
        # Ensure user exists
        ensure_user_exists()
        
        # Fix directories
        self.setup_directories()
        
        # Fix configuration
        if not UNBOUND_CONF.exists():
            console.print("[yellow]Main configuration missing, creating...[/yellow]")
            server_ip = get_server_ip()
            self.config_manager.create_full_configuration(server_ip)
        
        # Fix DNSSEC
        if not (UNBOUND_DIR / "root.hints").exists():
            console.print("[yellow]Root hints missing, downloading...[/yellow]")
            self.dnssec_manager.setup_root_hints()
        
        if not (UNBOUND_DIR / "root.key").exists():
            console.print("[yellow]Trust anchor missing, creating...[/yellow]")
            self.dnssec_manager.setup_trust_anchor()
        
        # Fix control keys
        if not (UNBOUND_DIR / "unbound_server.key").exists():
            console.print("[yellow]Control keys missing, generating...[/yellow]")
            self.dnssec_manager.generate_control_keys()
        
        # Fix Redis
        self.redis_manager.fix_redis_integration()
        
        # Fix systemd service
        if not SYSTEMD_SERVICE.exists():
            self.create_systemd_service()
        
        # Fix permissions
        self.config_manager.fix_permissions()
        
        # Restart services
        console.print("[cyan]Restarting services...[/cyan]")
        run_command(["systemctl", "daemon-reload"])
        run_command(["systemctl", "restart", REDIS_SERVICE])
        run_command(["systemctl", "restart", UNBOUND_SERVICE])
        
        console.print("[green]✓[/green] Installation fixes applied")
        
        # Run diagnostics
        from .troubleshooter import Troubleshooter
        troubleshooter = Troubleshooter()
        troubleshooter.run_diagnostics()