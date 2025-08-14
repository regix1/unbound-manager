"""Troubleshooting tools for Unbound."""

import time
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

from .constants import UNBOUND_DIR, UNBOUND_CONF_D
from .utils import run_command, check_service_status, check_port_listening

console = Console()


class Troubleshooter:
    """Troubleshooting tools for Unbound issues."""
    
    def run_diagnostics(self) -> None:
        """Run comprehensive diagnostics."""
        console.print(Panel.fit(
            "[bold cyan]Unbound Diagnostics[/bold cyan]\n\n"
            "Running comprehensive system checks...",
            border_style="cyan"
        ))
        
        issues = []
        
        # Check services
        console.print("\n[cyan]Checking services...[/cyan]")
        if not check_service_status("unbound"):
            issues.append("Unbound service is not running")
            console.print("[red]✗[/red] Unbound service is not running")
        else:
            console.print("[green]✓[/green] Unbound service is running")
        
        if not check_service_status("redis-server"):
            issues.append("Redis service is not running")
            console.print("[yellow]⚠[/yellow] Redis service is not running")
        else:
            console.print("[green]✓[/green] Redis service is running")
        
        # Check ports
        console.print("\n[cyan]Checking network ports...[/cyan]")
        if not check_port_listening(53):
            issues.append("Port 53 is not listening")
            console.print("[red]✗[/red] Port 53 is not listening")
        else:
            console.print("[green]✓[/green] Port 53 is listening")
        
        if not check_port_listening(8953, "127.0.0.1"):
            console.print("[yellow]⚠[/yellow] Control port 8953 is not listening")
        else:
            console.print("[green]✓[/green] Control port 8953 is listening")
        
        # Check configuration
        console.print("\n[cyan]Checking configuration...[/cyan]")
        try:
            result = run_command(["unbound-checkconf"], check=False)
            if result.returncode == 0:
                console.print("[green]✓[/green] Configuration is valid")
            else:
                issues.append("Configuration is invalid")
                console.print("[red]✗[/red] Configuration is invalid")
                if result.stderr:
                    console.print(f"[red]{result.stderr}[/red]")
        except Exception as e:
            issues.append(f"Could not check configuration: {e}")
            console.print(f"[red]✗[/red] Could not check configuration: {e}")
        
        # Check files
        console.print("\n[cyan]Checking required files...[/cyan]")
        required_files = [
            (UNBOUND_DIR / "unbound.conf", "Main configuration"),
            (UNBOUND_DIR / "root.key", "DNSSEC trust anchor"),
            (UNBOUND_DIR / "root.hints", "Root hints"),
            (UNBOUND_DIR / "unbound_server.key", "Server key"),
            (UNBOUND_DIR / "unbound_control.key", "Control key"),
        ]
        
        for file_path, description in required_files:
            if file_path.exists():
                console.print(f"[green]✓[/green] {description} exists")
            else:
                issues.append(f"{description} missing: {file_path}")
                console.print(f"[red]✗[/red] {description} missing")
        
        # Check permissions
        console.print("\n[cyan]Checking permissions...[/cyan]")
        self._check_permissions()
        
        # Check DNS resolution
        console.print("\n[cyan]Testing DNS resolution...[/cyan]")
        self._test_dns_resolution()
        
        # Summary
        console.print("\n" + "=" * 50)
        if issues:
            console.print(Panel.fit(
                f"[bold red]Found {len(issues)} issue(s):[/bold red]\n\n" +
                "\n".join(f"• {issue}" for issue in issues),
                border_style="red"
            ))
            console.print("\n[yellow]Run 'Fix Existing Installation' from the main menu to resolve these issues[/yellow]")
        else:
            console.print(Panel.fit(
                "[bold green]✓ All diagnostics passed![/bold green]\n\n"
                "No issues detected.",
                border_style="green"
            ))
    
    def _check_permissions(self) -> None:
        """Check file and directory permissions."""
        import pwd
        import grp
        
        try:
            unbound_uid = pwd.getpwnam("unbound").pw_uid
            unbound_gid = grp.getgrnam("unbound").gr_gid
            
            # Check directory ownership
            if UNBOUND_DIR.exists():
                stats = UNBOUND_DIR.stat()
                if stats.st_uid != unbound_uid:
                    console.print(f"[yellow]⚠[/yellow] {UNBOUND_DIR} not owned by unbound user")
                else:
                    console.print(f"[green]✓[/green] Directory ownership correct")
        except KeyError:
            console.print("[red]✗[/red] Unbound user does not exist")
    
    def _test_dns_resolution(self) -> None:
        """Test DNS resolution."""
        try:
            result = run_command(
                ["dig", "@127.0.0.1", "+short", "example.com"],
                check=False
            )
            
            if result.returncode == 0 and result.stdout.strip():
                console.print("[green]✓[/green] DNS resolution working")
            else:
                console.print("[red]✗[/red] DNS resolution failed")
        except Exception as e:
            console.print(f"[red]✗[/red] Could not test DNS: {e}")
    
    def view_logs(self, lines: int = 50) -> None:
        """View Unbound logs."""
        console.print(Panel.fit(
            "[bold cyan]Unbound Logs[/bold cyan]",
            border_style="cyan"
        ))
        
        try:
            result = run_command(
                ["journalctl", "-u", "unbound", "-n", str(lines), "--no-pager"],
                check=False
            )
            
            if result.returncode == 0:
                syntax = Syntax(result.stdout, "log", theme="monokai", line_numbers=True)
                console.print(syntax)
            else:
                console.print("[red]Could not retrieve logs[/red]")
        except Exception as e:
            console.print(f"[red]Error viewing logs: {e}[/red]")
    
    def show_statistics(self) -> None:
        """Show Unbound statistics."""
        console.print(Panel.fit(
            "[bold cyan]Unbound Statistics[/bold cyan]",
            border_style="cyan"
        ))
        
        try:
            result = run_command(["unbound-control", "stats"], check=False)
            
            if result.returncode != 0:
                console.print("[red]Could not retrieve statistics[/red]")
                console.print("[yellow]Make sure Unbound is running and control is configured[/yellow]")
                return
            
            # Parse statistics
            stats = {}
            for line in result.stdout.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    stats[key] = value
            
            # Create statistics table
            table = Table(title="Query Statistics", title_style="bold cyan")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")
            
            # Add important metrics
            metrics = [
                ("Total Queries", stats.get("total.num.queries", "0")),
                ("Cache Hits", stats.get("total.num.cachehits", "0")),
                ("Cache Misses", stats.get("total.num.cachemiss", "0")),
                ("Recursive Queries", stats.get("total.num.recursivereplies", "0")),
                ("Average Recursion Time", f"{float(stats.get('total.recursion.time.avg', 0)):.3f}s"),
                ("SERVFAIL Responses", stats.get("num.answer.rcode.SERVFAIL", "0")),
                ("NXDOMAIN Responses", stats.get("num.answer.rcode.NXDOMAIN", "0")),
            ]
            
            for metric, value in metrics:
                table.add_row(metric, value)
            
            console.print(table)
            
            # Calculate cache hit rate
            hits = int(stats.get("total.num.cachehits", 0))
            queries = int(stats.get("total.num.queries", 0))
            if queries > 0:
                hit_rate = (hits / queries) * 100
                console.print(f"\n[cyan]Cache Hit Rate:[/cyan] [green]{hit_rate:.2f}%[/green]")
            
            # Show memory usage
            console.print(f"\n[cyan]Memory Usage:[/cyan]")
            console.print(f"  Message Cache: {stats.get('mem.cache.message', 'N/A')} bytes")
            console.print(f"  RRset Cache: {stats.get('mem.cache.rrset', 'N/A')} bytes")
            
        except Exception as e:
            console.print(f"[red]Error getting statistics: {e}[/red]")
    
    def check_connectivity(self) -> None:
        """Check network connectivity."""
        console.print("[cyan]Checking network connectivity...[/cyan]\n")
        
        # Check root servers
        root_servers = [
            "a.root-servers.net",
            "b.root-servers.net",
            "c.root-servers.net",
        ]
        
        for server in root_servers:
            try:
                result = run_command(
                    ["dig", f"@{server}", ".", "NS", "+short"],
                    check=False,
                    timeout=5
                )
                
                if result.returncode == 0:
                    console.print(f"[green]✓[/green] Can reach {server}")
                else:
                    console.print(f"[red]✗[/red] Cannot reach {server}")
            except Exception:
                console.print(f"[red]✗[/red] Cannot reach {server}")
        
        # Check upstream DNS
        console.print("\n[cyan]Checking upstream DNS servers...[/cyan]")
        upstream_servers = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
        
        for server in upstream_servers:
            try:
                result = run_command(
                    ["dig", f"@{server}", "example.com", "+short"],
                    check=False,
                    timeout=5
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    console.print(f"[green]✓[/green] {server} is reachable")
                else:
                    console.print(f"[red]✗[/red] {server} is not reachable")
            except Exception:
                console.print(f"[red]✗[/red] {server} is not reachable")