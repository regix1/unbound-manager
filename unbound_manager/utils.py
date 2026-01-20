"""Utility functions for the Unbound Manager."""

from __future__ import annotations

import os
import sys
import subprocess
import socket
import time
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import psutil
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def check_root() -> None:
    """Check if the script is running as root."""
    if os.geteuid() != 0:
        console.print("[red]✗ This application must be run as root[/red]")
        sys.exit(1)


def run_command(
    command: List[str],
    check: bool = True,
    capture_output: bool = True,
    text: bool = True,
    timeout: Optional[int] = 30,
    cwd: Optional[Path] = None,
) -> subprocess.CompletedProcess:
    """
    Run a shell command and return the result.
    
    Args:
        command: Command to run as list of strings
        check: Whether to raise exception on non-zero exit
        capture_output: Whether to capture stdout/stderr
        text: Whether to return output as text
        timeout: Command timeout in seconds
        cwd: Working directory for the command
    
    Returns:
        CompletedProcess instance
    """
    try:
        result = subprocess.run(
            command,
            check=check,
            capture_output=capture_output,
            text=text,
            timeout=timeout,
            cwd=cwd,
        )
        return result
    except FileNotFoundError:
        console.print(f"[red]Command not found: {command[0]}[/red]")
        raise
    except subprocess.TimeoutExpired:
        console.print(f"[red]Command timed out: {' '.join(command)}[/red]")
        raise
    except subprocess.CalledProcessError as e:
        if check:
            console.print(f"[red]Command failed: {' '.join(command)}[/red]")
            if e.stderr:
                console.print(f"[red]Error: {e.stderr}[/red]")
        raise


def check_service_status(service: str) -> bool:
    """Check if a systemd service is running."""
    try:
        result = run_command(
            ["systemctl", "is-active", "--quiet", service],
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def restart_service(service: str) -> bool:
    """Restart a systemd service."""
    try:
        run_command(["systemctl", "restart", service])
        time.sleep(2)  # Give service time to start
        return check_service_status(service)
    except Exception as e:
        console.print(f"[red]Failed to restart {service}: {e}[/red]")
        return False


def get_server_ip() -> str:
    """Get the server's primary IP address."""
    try:
        # Try to get IP from network interfaces
        result = run_command(
            ["ip", "-4", "addr", "show", "scope", "global"],
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            import re
            matches = re.findall(r'inet\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
            if matches:
                return matches[0]
    except Exception:
        pass
    
    # Fallback to socket method
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def check_port_listening(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is listening."""
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == 'LISTEN' and conn.laddr.port == port:
                if host == "0.0.0.0" or conn.laddr.ip == host or conn.laddr.ip == "0.0.0.0":
                    return True
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        pass
    return False


def ensure_directory(path: Path, owner: str = "unbound", group: str = "unbound", mode: int = 0o755) -> None:
    """Ensure a directory exists with proper permissions."""
    path.mkdir(parents=True, exist_ok=True)
    if owner and group:
        try:
            import pwd
            import grp
            uid = pwd.getpwnam(owner).pw_uid
            gid = grp.getgrnam(group).gr_gid
            os.chown(path, uid, gid)
        except (KeyError, OSError) as e:
            console.print(f"[yellow]Warning: Could not set ownership for {path}: {e}[/yellow]")
    path.chmod(mode)


def ensure_user_exists(username: str = "unbound", home: str = "/var/lib/unbound", shell: str = "/usr/sbin/nologin") -> None:
    """Ensure the unbound user exists."""
    try:
        import pwd
        pwd.getpwnam(username)
    except KeyError:
        console.print(f"[yellow]Creating user {username}...[/yellow]")
        run_command([
            "useradd",
            "-r",  # System user
            "-d", home,  # Home directory
            "-s", shell,  # Shell
            "-c", "Unbound DNS resolver",
            username
        ])


def set_file_permissions(path: Path, owner: str = "unbound", group: str = "unbound", mode: int = 0o644) -> None:
    """Set file ownership and permissions."""
    if not path.exists():
        return
    
    try:
        import pwd
        import grp
        uid = pwd.getpwnam(owner).pw_uid
        gid = grp.getgrnam(group).gr_gid
        os.chown(path, uid, gid)
        path.chmod(mode)
    except (KeyError, OSError) as e:
        console.print(f"[yellow]Warning: Could not set permissions for {path}: {e}[/yellow]")


def download_file(url: str, destination: Path, timeout: int = 30) -> bool:
    """Download a file from a URL."""
    import requests
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(f"Downloading {destination.name}...", total=None)
            
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            progress.update(task, completed=True)
        return True
    except Exception as e:
        console.print(f"[red]Failed to download {url}: {e}[/red]")
        return False


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """
    Prompt the user for a yes/no answer.
    
    Args:
        question: The question to ask
        default: Default answer if user just presses Enter
    
    Returns:
        bool: True for yes, False for no
    """
    from rich.prompt import Confirm
    return Confirm.ask(question, default=default)


def get_system_info() -> Dict[str, Any]:
    """Get system information."""
    return {
        "cpu_count": os.cpu_count() or 1,
        "memory_total": psutil.virtual_memory().total,
        "memory_available": psutil.virtual_memory().available,
        "disk_usage": psutil.disk_usage('/').percent,
        "load_average": os.getloadavg(),
        "hostname": socket.gethostname(),
    }


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def print_header(title: str, width: int = 58) -> None:
    """Print a consistent ASCII header for CLI screens."""
    console.print("┌" + "─" * width + "┐")
    console.print(f"│  [bold cyan]{title:^{width-4}}[/bold cyan]  │")
    console.print("└" + "─" * width + "┘")
    console.print()


def parse_unbound_stats(raw: str) -> Dict[str, str]:
    """Parse unbound-control stats output into a dictionary."""
    stats: Dict[str, str] = {}
    for line in raw.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            stats[key] = value.strip()
    return stats


def validate_ip_address(ip: str) -> bool:
    """Validate an IP address."""
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def check_package_installed(package: str) -> bool:
    """Check if a system package is installed."""
    try:
        result = run_command(
            ["dpkg", "-l", package],
            check=False,
            capture_output=True,
        )
        return result.returncode == 0 and "ii" in result.stdout
    except Exception:
        return False


def install_packages(packages: List[str]) -> bool:
    """Install system packages using apt."""
    try:
        console.print(f"[cyan]Installing packages: {', '.join(packages)}[/cyan]")
        
        # Update package list
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Updating package list...", total=None)
            run_command(["apt", "update"], check=True)
            progress.update(task, completed=True)
        
        # Install packages
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(f"Installing {len(packages)} packages...", total=None)
            run_command(
                ["apt", "install", "-y"] + packages,
                check=True,
            )
            progress.update(task, completed=True)
        
        console.print("[green]✓[/green] Packages installed")
        return True
    except Exception as e:
        console.print(f"[red]Failed to install packages: {e}[/red]")
        return False