"""Troubleshooting tools for Unbound."""

import sys
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
                    stats[key] = value.strip()
            
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
            
            # Show memory usage with better handling
            self._show_memory_stats(stats)
            
            # Show thread statistics if available
            self._show_thread_stats(stats)
            
        except Exception as e:
            console.print(f"[red]Error getting statistics: {e}[/red]")
    
    def _show_memory_stats(self, stats: Dict[str, str]) -> None:
        """Display memory statistics in a readable format."""
        console.print(f"\n[cyan]Memory Usage:[/cyan]")
        
        # Try different memory stat keys that might exist
        memory_keys = [
            ("mem.cache.message", "Message Cache"),
            ("mem.cache.rrset", "RRset Cache"),
            ("mem.total.sbrk", "Total Memory (sbrk)"),
            ("mem.mod.iterator", "Iterator Module"),
            ("mem.mod.validator", "Validator Module"),
            ("mem.mod.respip", "Response IP Module"),
            ("mem.streamwait", "Stream Wait"),
            ("mem.http.query_buffer", "HTTP Query Buffer"),
        ]
        
        memory_found = False
        for key, label in memory_keys:
            if key in stats:
                try:
                    bytes_val = int(stats[key])
                    if bytes_val > 0:
                        memory_found = True
                        size = self._format_bytes(bytes_val)
                        console.print(f"  {label}: {size}")
                except (ValueError, TypeError):
                    # Some memory values might not be integers
                    if stats[key] and stats[key] != "0":
                        memory_found = True
                        console.print(f"  {label}: {stats[key]}")
        
        if not memory_found:
            # Try to show any memory-related stats
            any_mem_stats = False
            for key, value in stats.items():
                if 'mem.' in key and value != "0":
                    if not any_mem_stats:
                        console.print("  [yellow]Available memory statistics:[/yellow]")
                        any_mem_stats = True
                    # Format the key nicely
                    formatted_key = key.replace('mem.', '').replace('.', ' ').replace('_', ' ').title()
                    try:
                        bytes_val = int(value)
                        console.print(f"  {formatted_key}: {self._format_bytes(bytes_val)}")
                    except ValueError:
                        console.print(f"  {formatted_key}: {value}")
            
            if not any_mem_stats:
                console.print("  [yellow]Memory statistics not available in current Unbound version[/yellow]")
                console.print("  [dim]Try running with more verbosity or check Unbound compilation options[/dim]")
    
    def _show_thread_stats(self, stats: Dict[str, str]) -> None:
        """Display thread statistics if available."""
        thread_stats = []
        for key, value in stats.items():
            if key.startswith("thread") and value != "0":
                thread_stats.append((key, value))
        
        if thread_stats:
            console.print(f"\n[cyan]Thread Statistics:[/cyan]")
            for key, value in thread_stats[:5]:  # Show first 5 thread stats
                formatted_key = key.replace('thread', 'Thread ').replace('.', ' ').replace('_', ' ').title()
                console.print(f"  {formatted_key}: {value}")
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    def show_extended_statistics(self) -> None:
        """Show all available Unbound statistics for debugging."""
        console.print(Panel.fit(
            "[bold cyan]Extended Unbound Statistics[/bold cyan]",
            border_style="cyan"
        ))
        
        try:
            # Use stats_noreset to not reset counters
            result = run_command(["unbound-control", "stats_noreset"], check=False)
            
            if result.returncode != 0:
                # Fallback to regular stats
                result = run_command(["unbound-control", "stats"], check=False)
                
            if result.returncode != 0:
                console.print("[red]Could not retrieve statistics[/red]")
                return
            
            # Parse and categorize statistics
            categories = {
                "Query Statistics": [],
                "Cache Statistics": [],
                "Memory Statistics": [],
                "Thread Statistics": [],
                "Time Statistics": [],
                "DNS Response Codes": [],
                "Other Statistics": []
            }
            
            for line in result.stdout.split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip()
                    
                    # Skip zero values for cleaner output (optional)
                    if value == "0" or value == "0.000000":
                        continue
                    
                    # Categorize
                    if "num.queries" in key or "num.answer" in key:
                        categories["Query Statistics"].append((key, value))
                    elif "cache" in key:
                        categories["Cache Statistics"].append((key, value))
                    elif "mem." in key:
                        categories["Memory Statistics"].append((key, value))
                    elif "thread" in key:
                        categories["Thread Statistics"].append((key, value))
                    elif "time" in key:
                        categories["Time Statistics"].append((key, value))
                    elif "rcode" in key:
                        categories["DNS Response Codes"].append((key, value))
                    else:
                        categories["Other Statistics"].append((key, value))
            
            # Display each category
            for category, items in categories.items():
                if items:
                    console.print(f"\n[cyan]{category}:[/cyan]")
                    for key, value in sorted(items)[:10]:  # Limit to 10 items per category
                        # Format the key for readability
                        formatted_key = key.replace(".", " ").replace("_", " ").title()
                        # Truncate long keys
                        if len(formatted_key) > 40:
                            formatted_key = formatted_key[:37] + "..."
                        console.print(f"  {formatted_key}: {value}")
                    
                    if len(items) > 10:
                        console.print(f"  [dim]... and {len(items) - 10} more[/dim]")
                        
        except Exception as e:
            console.print(f"[red]Error getting extended statistics: {e}[/red]")
    
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