"""Unbound installation and management module."""

import os
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
    UNBOUND_RELEASES_URL, SYSTEMD_SERVICE
)
from .utils import (
    run_command, ensure_user_exists, ensure_directory,
    install_packages, check_package_installed, prompt_yes_no,
    get_server_ip
)
from .config_manager import ConfigManager
from .redis_manager import RedisManager
from .dnssec import DNSSECManager

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
        """Let user select an Unbound version."""
        versions = self.get_available_versions()
        
        console.print(Panel.fit(
            "[bold cyan]Available Unbound Versions[/bold cyan]",
            border_style="cyan"
        ))
        
        for i, version in enumerate(versions, 1):
            console.print(f"  [green]{i}[/green]. {version}")
        
        console.print()
        choice = Prompt.ask(
            "Select a version",
            choices=[str(i) for i in range(1, len(versions) + 1)],
            default="1"
        )
        
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
    
    def setup_directories(self) -> None:
        """Create necessary directories with proper permissions."""
        console.print("[cyan]Setting up directories...[/cyan]")
        
        ensure_directory(UNBOUND_DIR)
        ensure_directory(UNBOUND_CONF_D)
        ensure_directory(UNBOUND_DIR / "backups")
        
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
        run_command(["systemctl", "enable", "unbound"])
        run_command(["systemctl", "start", "unbound"])
        
        # Verify installation
        from .tester import UnboundTester
        tester = UnboundTester()
        if tester.verify_installation():
            console.print(Panel.fit(
                "[bold green]✓ Unbound installed successfully![/bold green]\n\n"
                f"Version: {version}\n"
                f"Configuration: /etc/unbound/\n"
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
        backup_manager.create_backup()
        
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
        run_command(["systemctl", "restart", "redis-server"])
        run_command(["systemctl", "restart", "unbound"])
        
        console.print("[green]✓[/green] Installation fixes applied")
        
        # Run diagnostics
        from .troubleshooter import Troubleshooter
        troubleshooter = Troubleshooter()
        troubleshooter.run_diagnostics()
    
    def update_unbound(self) -> None:
        """Update Unbound to a newer version."""
        console.print(Panel.fit(
            "[bold cyan]Update Unbound[/bold cyan]\n\n"
            "This will update Unbound to a newer version while preserving your configuration.",
            border_style="cyan"
        ))
        
        # Check current version
        try:
            result = run_command(["unbound", "-V"], check=False)
            if result.returncode == 0:
                console.print(f"[cyan]Current version:[/cyan] {result.stdout.split()[1]}")
        except Exception:
            pass
        
        # Backup configuration
        from .backup import BackupManager
        backup_manager = BackupManager()
        backup_path = backup_manager.create_backup("before_update")
        
        # Select new version
        version = self.select_version()
        
        # IMPORTANT: Save current DNS settings and set temporary resolver
        console.print("[cyan]Configuring temporary DNS resolver...[/cyan]")
        
        # Save current resolv.conf
        resolv_backup = Path("/etc/resolv.conf.unbound_backup")
        resolv_conf = Path("/etc/resolv.conf")
        
        try:
            # Backup current resolv.conf
            if resolv_conf.exists():
                shutil.copy(str(resolv_conf), str(resolv_backup))
            
            # Set temporary DNS servers (Google and Cloudflare)
            temp_resolv = """# Temporary DNS for Unbound update
    nameserver 8.8.8.8
    nameserver 8.8.4.4
    nameserver 1.1.1.1
    """
            with open(resolv_conf, 'w') as f:
                f.write(temp_resolv)
            
            console.print("[green]✓[/green] Temporary DNS configured")
            
            # Test DNS resolution before stopping Unbound
            test_result = run_command(
                ["nslookup", "nlnetlabs.nl", "8.8.8.8"],
                check=False,
                timeout=5
            )
            if test_result.returncode != 0:
                console.print("[yellow]Warning: DNS resolution test failed, but continuing...[/yellow]")
            
            # Stop service
            console.print("[cyan]Stopping Unbound service...[/cyan]")
            run_command(["systemctl", "stop", "unbound"])
            
            # Wait a moment for service to fully stop
            time.sleep(2)
            
            # Compile and install new version
            update_successful = False
            try:
                if self.compile_unbound(version):
                    update_successful = True
                    console.print("[green]✓[/green] Unbound updated successfully")
            except Exception as e:
                console.print(f"[red]Update failed: {e}[/red]")
                update_successful = False
            
            # Always restore DNS configuration
            console.print("[cyan]Restoring DNS configuration...[/cyan]")
            if resolv_backup.exists():
                shutil.copy(str(resolv_backup), str(resolv_conf))
                resolv_backup.unlink()  # Remove backup
                console.print("[green]✓[/green] DNS configuration restored")
            
            # Restart service
            console.print("[cyan]Starting Unbound service...[/cyan]")
            run_command(["systemctl", "start", "unbound"])
            
            # Wait for service to be ready
            time.sleep(3)
            
            # Verify service is running
            if check_service_status("unbound"):
                console.print("[green]✓[/green] Unbound service started successfully")
                
                # Test DNS resolution through Unbound
                test_result = run_command(
                    ["dig", "@127.0.0.1", "+short", "example.com"],
                    check=False,
                    timeout=5
                )
                if test_result.returncode == 0 and test_result.stdout.strip():
                    console.print("[green]✓[/green] DNS resolution working through Unbound")
            else:
                console.print("[yellow]⚠[/yellow] Unbound service may not be running properly")
            
            if not update_successful:
                console.print("[red]Update failed, restoring from backup...[/red]")
                backup_manager.restore_specific_backup(backup_path)
                run_command(["systemctl", "start", "unbound"])
                
        except Exception as e:
            console.print(f"[red]Critical error during update: {e}[/red]")
            
            # Emergency recovery
            console.print("[yellow]Attempting emergency recovery...[/yellow]")
            
            # Restore resolv.conf if backup exists
            if resolv_backup.exists():
                try:
                    shutil.copy(str(resolv_backup), str(resolv_conf))
                    resolv_backup.unlink()
                    console.print("[green]✓[/green] DNS configuration restored")
                except Exception as restore_error:
                    console.print(f"[red]Could not restore DNS: {restore_error}[/red]")
            
            # Restore Unbound from backup
            try:
                backup_manager.restore_specific_backup(backup_path)
                run_command(["systemctl", "start", "unbound"])
                console.print("[green]✓[/green] Unbound restored from backup")
            except Exception as restore_error:
                console.print(f"[red]Could not restore Unbound: {restore_error}[/red]")
                console.print("[red]Manual intervention may be required[/red]")
                console.print("[cyan]Try running: systemctl start unbound[/cyan]")