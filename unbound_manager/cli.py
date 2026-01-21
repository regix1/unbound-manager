#!/usr/bin/env python3
"""Main CLI interface for Unbound Manager with interactive menu."""

from __future__ import annotations

import sys
import os
import time
import shutil
import tempfile
from typing import Optional, List, Tuple, Callable
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.layout import Layout
from rich.text import Text
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .constants import APP_VERSION, UNBOUND_SERVICE, REDIS_SERVICE
from .utils import check_root, check_service_status, run_command, prompt_yes_no, print_header, parse_unbound_stats
from .installer import UnboundInstaller
from .config_manager import ConfigManager
from .redis_manager import RedisManager
from .dnssec import DNSSECManager
from .troubleshooter import Troubleshooter
from .tester import UnboundTester
from .backup import BackupManager
from .menu_system import InteractiveMenu, MenuItem, MenuCategory, SubMenu, create_submenu

console = Console()


class UnboundManagerCLI:
    """Main CLI class for Unbound Manager with interactive menu."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.installer = UnboundInstaller()
        self.config_manager = ConfigManager()
        self.redis_manager = RedisManager()
        self.dnssec_manager = DNSSECManager()
        self.troubleshooter = Troubleshooter()
        self.tester = UnboundTester()
        self.backup_manager = BackupManager()
        self.menu = InteractiveMenu()
        self.setup_menu()
    
    def wrap_action(self, func: Callable) -> Callable:
        """Wrap an action to ensure it pauses before returning."""
        def wrapped():
            try:
                result = func()
                # Always add pause for wrapped functions
                console.print("\n[dim]Press Enter to continue...[/dim]")
                input()
                return result
            except KeyboardInterrupt:
                console.print("\n[yellow]Operation cancelled[/yellow]")
                console.print("[dim]Press Enter to continue...[/dim]")
                input()
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
                console.print("[dim]Press Enter to continue...[/dim]")
                input()
        return wrapped
    
    def show_banner(self) -> None:
        """Display the application banner with status."""
        console.clear()
        
        # Get service status
        unbound_status = check_service_status(UNBOUND_SERVICE)
        redis_status = check_service_status(REDIS_SERVICE)
        
        # Build status indicators
        unbound_indicator = "[green]●[/green]" if unbound_status else "[red]○[/red]"
        redis_indicator = "[green]●[/green]" if redis_status else "[red]○[/red]"
        
        # Display header
        console.print("┌" + "─" * 58 + "┐")
        console.print(f"│  [bold cyan]UNBOUND DNS MANAGER[/bold cyan]  v{APP_VERSION:<30} │")
        console.print("├" + "─" * 58 + "┤")
        console.print(f"│  Status: Unbound {unbound_indicator}  Redis {redis_indicator}                             │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
    
    def setup_menu(self) -> None:
        """Setup the interactive menu structure."""
        # ===== TOP-LEVEL QUICK ACCESS =====
        
        # Service Control - most used
        self.menu.add_item(MenuItem(
            "Services",
            self.manage_services_quick,
            prefix="[S]",
            description="Start/Stop/Restart DNS services",
            key="s"
        ))
        
        # View - Status, Stats, Logs combined
        self.menu.add_item(MenuItem(
            "View",
            self.view_menu,
            prefix="[V]",
            description="Status, statistics, and logs",
            key="v"
        ))
        
        # ===== CONFIGURATION =====
        config_category = MenuCategory("Configuration", prefix="[C]")
        config_category.add_item(MenuItem(
            "DNS Upstream",
            self.change_dns_upstream,
            description="Change DNS provider"
        ))
        config_category.add_item(MenuItem(
            "Server Settings",
            self.wrap_action(self.config_manager.manage_configuration),
            description="Edit server config"
        ))
        config_category.add_item(MenuItem(
            "Access Control",
            self.wrap_action(self.config_manager.edit_access_control),
            description="Allowed networks"
        ))
        config_category.add_item(MenuItem(
            "Redis Cache",
            self.wrap_action(self.redis_manager.configure_redis),
            description="Cache settings"
        ))
        config_category.add_item(MenuItem(
            "DNSSEC",
            self.wrap_action(self.dnssec_manager.manage_dnssec),
            description="Security settings"
        ))
        self.menu.add_category(config_category)
        
        # ===== TESTING & DIAGNOSTICS =====
        test_category = MenuCategory("Testing", prefix="[T]")
        test_category.add_item(MenuItem(
            "Run Diagnostics",
            self.wrap_action(self.troubleshooter.run_diagnostics),
            description="Check for issues"
        ))
        test_category.add_item(MenuItem(
            "Test DNS",
            self.wrap_action(self.tester.run_all_tests),
            description="DNS resolution tests"
        ))
        test_category.add_item(MenuItem(
            "Performance",
            self.wrap_action(lambda: self.tester.test_performance(100)),
            description="Query benchmark"
        ))
        test_category.add_item(MenuItem(
            "Network",
            self.wrap_action(self.troubleshooter.check_connectivity),
            description="Connectivity check"
        ))
        self.menu.add_category(test_category)
        
        # ===== BACKUPS =====
        backup_category = MenuCategory("Backups", prefix="[B]")
        backup_category.add_item(MenuItem(
            "Create Backup",
            self.backup_configuration_interactive,
            description="Backup current config"
        ))
        backup_category.add_item(MenuItem(
            "Restore Backup",
            self.wrap_action(self.backup_manager.restore_backup),
            description="Restore from backup"
        ))
        backup_category.add_item(MenuItem(
            "Cleanup",
            self.cleanup_backups,
            description="Remove old backups"
        ))
        self.menu.add_category(backup_category)
        
        # ===== INSTALLATION & UPDATES =====
        install_category = MenuCategory("Install/Update", prefix="[I]")
        install_category.add_item(MenuItem(
            "Update Unbound",
            self.wrap_action(self.installer.update_unbound),
            description="Update DNS server"
        ))
        install_category.add_item(MenuItem(
            "Update Manager",
            self.update_manager,
            description="Update this tool"
        ))
        install_category.add_item(MenuItem(
            "Fresh Install",
            self.wrap_action(self.installer.install_unbound),
            description="New installation"
        ))
        install_category.add_item(MenuItem(
            "Fix Installation",
            self.wrap_action(self.installer.fix_existing_installation),
            description="Repair issues"
        ))
        install_category.add_item(MenuItem(
            "Regenerate Keys",
            self.wrap_action(self.dnssec_manager.generate_control_keys),
            description="New control keys"
        ))
        install_category.add_item(MenuItem(
            "Uninstall",
            self.uninstall_manager,
            description="Remove manager",
            style="red"
        ))
        self.menu.add_category(install_category)
        
        # ===== HELP & EXIT =====
        self.menu.add_item(MenuItem(
            "Help",
            self.show_help,
            prefix="[H]",
            description="Help & documentation",
            key="h"
        ))
        
        self.menu.add_item(MenuItem(
            "Exit",
            lambda: False,
            prefix="[Q]",
            description="Exit program",
            key="q",
            style="red"
        ))
    
    def show_detailed_status(self) -> None:
        """Show detailed system status."""
        console.clear()
        
        # Header
        console.print("┌" + "─" * 58 + "┐")
        console.print("│                    [bold cyan]SYSTEM STATUS[/bold cyan]                        │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        # Service status table
        table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
        table.add_column("Service", style="cyan", width=20)
        table.add_column("Status", justify="center", width=12)
        table.add_column("Details", width=26)
        
        # Unbound status
        unbound_status = check_service_status(UNBOUND_SERVICE)
        if unbound_status:
            unbound_display = "[green]● Active[/green]"
            unbound_details = self._get_service_uptime(UNBOUND_SERVICE)
        else:
            unbound_display = "[red]○ Inactive[/red]"
            unbound_details = "Service not running"
        table.add_row("Unbound DNS", unbound_display, unbound_details)
        
        # Redis status
        redis_status = check_service_status(REDIS_SERVICE)
        if redis_status:
            redis_display = "[green]● Active[/green]"
            redis_details = self._get_service_uptime(REDIS_SERVICE)
        else:
            redis_display = "[red]○ Inactive[/red]"
            redis_details = "Service not running"
        table.add_row("Redis Cache", redis_display, redis_details)
        
        console.print(table)
        console.print()
        
        # Show statistics if services are running
        if unbound_status:
            console.print("─" * 60)
            console.print("[bold]DNS Statistics:[/bold]")
            self._show_quick_stats()
            console.print()
        
        if redis_status:
            console.print("─" * 60)
            console.print("[bold]Cache Statistics:[/bold]")
            self._show_cache_stats()
            console.print()
        
        console.print("─" * 60)
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()

    def view_menu(self) -> None:
        """View menu combining status, statistics, and logs."""
        
        def show_stats():
            self.troubleshooter.show_statistics()
        
        def show_extended():
            self.troubleshooter.show_extended_statistics()
        
        def show_redis():
            self.redis_manager.show_redis_stats()
        
        result = create_submenu("View", [
            ("Service Status", self.show_detailed_status),
            ("DNS Statistics", show_stats),
            ("Extended Stats", show_extended),
            ("Redis Stats", show_redis),
            ("View Logs", self.view_logs_interactive),
        ])
        
        if result == SubMenu.QUIT:
            return False
    
    def _get_service_uptime(self, service: str) -> str:
        """Get service uptime."""
        try:
            result = run_command(
                ["systemctl", "show", service, "--property=ActiveEnterTimestamp"],
                check=False
            )
            if result.returncode == 0 and "=" in result.stdout:
                timestamp = result.stdout.split("=")[1].strip()
                if timestamp:
                    import datetime
                    start_time = datetime.datetime.strptime(
                        timestamp.split()[1] + " " + timestamp.split()[2],
                        "%Y-%m-%d %H:%M:%S"
                    )
                    uptime = datetime.datetime.now() - start_time
                    days = uptime.days
                    hours = uptime.seconds // 3600
                    minutes = (uptime.seconds % 3600) // 60
                    
                    if days > 0:
                        return f"Up {days}d {hours}h {minutes}m"
                    elif hours > 0:
                        return f"Up {hours}h {minutes}m"
                    else:
                        return f"Up {minutes}m"
        except Exception:
            pass
        return "Unknown"
    
    def _show_quick_stats(self) -> None:
        """Show quick DNS statistics."""
        try:
            result = run_command(["unbound-control", "stats"], check=False)
            if result.returncode == 0:
                stats = parse_unbound_stats(result.stdout)
                
                queries = stats.get("total.num.queries", "0")
                cache_hits = stats.get("total.num.cachehits", "0")
                
                if int(queries) > 0:
                    hit_rate = (int(cache_hits) / int(queries)) * 100
                    console.print(f"  Total queries     : {queries}")
                    console.print(f"  Cache hits        : {cache_hits}")
                    console.print(f"  Hit rate          : [green]{hit_rate:.1f}%[/green]")
                else:
                    console.print("  No queries processed yet")
        except Exception:
            console.print("  [yellow]Statistics unavailable[/yellow]")
    
    def _show_cache_stats(self) -> None:
        """Show quick cache statistics."""
        try:
            result = run_command(
                ["redis-cli", "-s", "/var/run/redis/redis.sock", "info", "stats"],
                check=False
            )
            if result.returncode == 0:
                hits = misses = 0
                for line in result.stdout.split('\n'):
                    if 'keyspace_hits:' in line:
                        hits = int(line.split(':')[1].strip())
                    elif 'keyspace_misses:' in line:
                        misses = int(line.split(':')[1].strip())
                
                if hits + misses > 0:
                    rate = (hits / (hits + misses)) * 100
                    console.print(f"  Keyspace hits     : {hits}")
                    console.print(f"  Keyspace misses   : {misses}")
                    console.print(f"  Cache efficiency  : [green]{rate:.1f}%[/green]")
                else:
                    console.print("  No cache activity yet")
        except Exception:
            console.print("  [yellow]Cache statistics unavailable[/yellow]")
    
    def manage_services_quick(self) -> None:
        """Quick service management using standardized submenu."""
        from .utils import restart_service
        
        # Get current status for display
        unbound_running = check_service_status(UNBOUND_SERVICE)
        redis_running = check_service_status(REDIS_SERVICE)
        
        status_desc = (
            f"Unbound: {'● Running' if unbound_running else '○ Stopped'} | "
            f"Redis: {'● Running' if redis_running else '○ Stopped'}"
        )
        
        def start_all():
            console.print("[cyan]Starting services...[/cyan]")
            restart_service(REDIS_SERVICE)
            restart_service(UNBOUND_SERVICE)
            console.print("[green]✓[/green] Services started")
        
        def stop_all():
            console.print("[cyan]Stopping services...[/cyan]")
            run_command(["systemctl", "stop", UNBOUND_SERVICE])
            run_command(["systemctl", "stop", REDIS_SERVICE])
            console.print("[yellow]Services stopped[/yellow]")
        
        menu = SubMenu("Service Control", status_desc)
        menu.add_option("Start All" if not unbound_running else "Restart All", start_all, "s")
        menu.add_option("Stop All", stop_all, "x")
        menu.add_option("Advanced Options", self.manage_services_advanced, "a")
        
        result = menu.run()
        if result == SubMenu.QUIT:
            return False
    
    def manage_services_advanced(self) -> None:
        """Advanced service management using standardized submenu."""
        from .utils import restart_service
        
        def start_unbound():
            console.print("[cyan]Starting Unbound...[/cyan]")
            restart_service(UNBOUND_SERVICE)
            console.print("[green]✓[/green] Unbound started")
        
        def stop_unbound():
            console.print("[cyan]Stopping Unbound...[/cyan]")
            run_command(["systemctl", "stop", UNBOUND_SERVICE])
            console.print("[yellow]Unbound stopped[/yellow]")
        
        def restart_unbound():
            console.print("[cyan]Restarting Unbound...[/cyan]")
            restart_service(UNBOUND_SERVICE)
            console.print("[green]✓[/green] Unbound restarted")
        
        def start_redis():
            console.print("[cyan]Starting Redis...[/cyan]")
            restart_service(REDIS_SERVICE)
            console.print("[green]✓[/green] Redis started")
        
        def stop_redis():
            console.print("[cyan]Stopping Redis...[/cyan]")
            run_command(["systemctl", "stop", REDIS_SERVICE])
            console.print("[yellow]Redis stopped[/yellow]")
        
        def restart_redis():
            console.print("[cyan]Restarting Redis...[/cyan]")
            restart_service(REDIS_SERVICE)
            console.print("[green]✓[/green] Redis restarted")
        
        result = create_submenu("Advanced Service Control", [
            ("Start Unbound", start_unbound),
            ("Stop Unbound", stop_unbound),
            ("Restart Unbound", restart_unbound),
            ("Start Redis", start_redis),
            ("Stop Redis", stop_redis),
            ("Restart Redis", restart_redis),
        ])
        
        if result == SubMenu.QUIT:
            return False
    
    def backup_configuration_interactive(self) -> None:
        """Interactive backup creation."""
        console.clear()
        
        console.print("┌" + "─" * 58 + "┐")
        console.print("│                 [bold cyan]CREATE BACKUP[/bold cyan]                         │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        description = Prompt.ask(
            "Enter backup description (optional)",
            default=""
        )
        
        console.print()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Creating backup...", total=None)
            backup_path = self.backup_manager.create_backup(description)
            progress.update(task, completed=True)
        
        console.print(f"[green]✓[/green] Backup created: {backup_path.name}")
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()
    
    def cleanup_backups(self) -> None:
        """Clean up old backups."""
        console.clear()
        console.print("┌" + "─" * 58 + "┐")
        console.print("│                 [bold cyan]CLEANUP BACKUPS[/bold cyan]                       │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        backups = self.backup_manager.list_backups()
        console.print(f"Found {len(backups)} backup(s)")
        
        if len(backups) > 10:
            console.print(f"\n[yellow]You have {len(backups)} backups. Recommended to keep only 10.[/yellow]")
            if prompt_yes_no("Clean up old backups?", default=True):
                self.backup_manager.cleanup_old_backups(10)
        else:
            console.print("\n[green]No cleanup needed[/green]")
        
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()
    
    def view_logs_interactive(self) -> None:
        """Interactive log viewer using standardized submenu."""
        
        def view_50():
            self.troubleshooter.view_logs(50)
        
        def view_100():
            self.troubleshooter.view_logs(100)
        
        def view_200():
            self.troubleshooter.view_logs(200)
        
        def follow_logs():
            console.print("[cyan]Following logs... Press Ctrl+C to stop[/cyan]\n")
            try:
                run_command(["journalctl", "-u", UNBOUND_SERVICE, "-f"], check=False, capture_output=False)
            except KeyboardInterrupt:
                pass
        
        result = create_submenu("View Logs", [
            ("Last 50 lines", view_50),
            ("Last 100 lines", view_100),
            ("Last 200 lines", view_200),
            ("Follow (real-time)", follow_logs, "f"),
        ])
        
        if result == SubMenu.QUIT:
            return False
    
    def installation_menu(self) -> None:
        """Installation submenu using standardized submenu."""
        
        def fresh_install():
            self.installer.install_unbound()
        
        def fix_install():
            self.installer.fix_existing_installation()
        
        def reinstall():
            if prompt_yes_no("This will reinstall Unbound. Continue?", default=False):
                self.installer.install_unbound()
        
        result = create_submenu("Installation Manager", [
            ("Fresh Install", fresh_install),
            ("Fix Installation", fix_install),
            ("Reinstall Unbound", reinstall),
        ])
        
        if result == SubMenu.QUIT:
            return False
    
    def show_help(self) -> None:
        """Show help information."""
        console.clear()
        
        console.print("┌" + "─" * 58 + "┐")
        console.print("│                      [bold cyan]HELP[/bold cyan]                              │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        help_sections = [
            ("[bold]Navigation:[/bold]", [
                "↑/↓ or j/k    Navigate menu",
                "Enter         Select item",
                "ESC or b      Go back",
                "r             Return (in submenus)",
                "q             Quit program"
            ]),
            ("[bold]Quick Keys:[/bold]", [
                "s             Services (start/stop)",
                "v             View (status/logs)",
                "h             Help",
                "1-9           Quick select"
            ]),
            ("[bold]Menu Categories:[/bold]", [
                "Services       Start/Stop/Restart DNS",
                "View           Status, Stats, Logs",
                "Configuration  DNS, Server, Access, Cache",
                "Testing        Diagnostics & benchmarks",
                "Backups        Create/Restore backups",
                "Install/Update Unbound & Manager updates"
            ])
        ]
        
        for title, items in help_sections:
            console.print(title)
            for item in items:
                console.print(f"  {item}")
            console.print()
        
        console.print("─" * 60)
        console.print("\n[bold]Documentation:[/bold]")
        console.print("  https://github.com/regix1/unbound-manager")
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()
    
    def update_manager(self) -> None:
        """Update Unbound Manager."""
        console.clear()
        
        console.print("┌" + "─" * 58 + "┐")
        console.print("│              [bold cyan]UPDATE MANAGER[/bold cyan]                            │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        console.print(f"Current version: [cyan]{APP_VERSION}[/cyan]")
        console.print()
        
        # Quick check with short timeout
        try:
            import requests
            response = requests.get(
                "https://raw.githubusercontent.com/regix1/unbound-manager/main/VERSION",
                timeout=(2, 3)  # (connect timeout, read timeout)
            )
            
            if response.status_code == 200:
                remote_version = response.text.strip()
                if remote_version != APP_VERSION:
                    console.print(f"[yellow]Update available: {remote_version}[/yellow]")
                else:
                    console.print("[green]✓ Up to date[/green]")
        except Exception:
            console.print("[dim]Could not check latest version[/dim]")
        
        console.print()
        if prompt_yes_no("Pull latest from git?", default=False):
            self.perform_update()
        
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()
    
    def perform_update(self) -> None:
        """Perform the update."""
        console.print("\n[cyan]Updating...[/cyan]")
        
        try:
            source_dir = Path.home() / "unbound-manager"
            
            if source_dir.exists() and (source_dir / ".git").exists():
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                    task = progress.add_task("Pulling latest changes...", total=None)
                    run_command(["git", "pull"], cwd=source_dir)
                    progress.update(task, description="Reinstalling package...")
                    run_command(["pip3", "install", "-e", "."], cwd=source_dir)
                    progress.update(task, completed=True)
                
                console.print("[green]✓ Update complete! Please restart the program.[/green]")
            else:
                console.print("[yellow]Source directory not found. Manual update required.[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Update failed: {e}[/red]")
    

    def change_dns_upstream(self) -> None:
        """Change DNS upstream provider."""
        console.clear()
        
        console.print("┌" + "─" * 58 + "┐")
        console.print("│              [bold cyan]DNS UPSTREAM CONFIGURATION[/bold cyan]              │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        # Show current configuration
        self.config_manager.show_current_dns_config()
        console.print()
        
        if not prompt_yes_no("Change DNS upstream provider?", default=True):
            console.print("[yellow]No changes made[/yellow]")
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
            return
        
        # Select new provider
        dns_provider = self.config_manager.select_dns_upstream()
        
        # Create backup before changes
        console.print("\n[cyan]Creating backup...[/cyan]")
        self.backup_manager.create_backup("before_dns_change")
        
        # Apply new configuration
        self.config_manager.create_forwarding_config(dns_provider)
        
        # Restart Unbound to apply changes
        console.print("\n[cyan]Restarting Unbound...[/cyan]")
        from .utils import restart_service
        if restart_service(UNBOUND_SERVICE):
            console.print("[green]✓[/green] Unbound restarted successfully")
            
            # Test DNS resolution
            console.print("\n[cyan]Testing DNS resolution...[/cyan]")
            try:
                result = run_command(
                    ["dig", "@127.0.0.1", "+short", "example.com"],
                    check=False,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    console.print("[green]✓[/green] DNS resolution working!")
                else:
                    console.print("[yellow]⚠[/yellow] DNS test inconclusive")
            except Exception:
                console.print("[yellow]⚠[/yellow] Could not test DNS")
        else:
            console.print("[red]Failed to restart Unbound[/red]")
        
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()

    def uninstall_manager(self) -> None:
        """Uninstall Unbound Manager."""
        console.clear()
        
        console.print("┌" + "─" * 58 + "┐")
        console.print("│            [bold red]UNINSTALL UNBOUND MANAGER[/bold red]                  │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        console.print("[yellow]Warning: This will remove the Unbound Manager tool.[/yellow]")
        console.print("Your DNS configuration will be preserved.")
        console.print()
        
        if not prompt_yes_no("Are you sure you want to uninstall?", default=False):
            return
        
        console.print("\n[cyan]Creating backup...[/cyan]")
        backup_path = self.backup_manager.create_backup("before_uninstall")
        console.print(f"[green]✓[/green] Backup saved to: {backup_path}")
        
        console.print("\n[yellow]Uninstalling...[/yellow]")
        try:
            run_command(["pip3", "uninstall", "-y", "unbound-manager"])
            console.print("[green]✓ Unbound Manager uninstalled[/green]")
        except Exception as e:
            console.print(f"[red]Uninstall failed: {e}[/red]")
        
        console.print("\n[yellow]Exiting...[/yellow]")
        sys.exit(0)
    
    def run(self) -> None:
        """Run the main application loop."""
        check_root()
        
        while True:
            self.show_banner()
            
            # Run the interactive menu
            result = self.menu.run()
            
            # Check if we should exit
            if result is False:
                console.print("\n[cyan]Goodbye![/cyan]")
                break
            
            # Handle other results
            if result is None:
                continue


def main():
    """Main entry point for the application."""
    try:
        cli = UnboundManagerCLI()
        cli.run()
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        if "--debug" in sys.argv:
            console.print("[dim]" + traceback.format_exc() + "[/dim]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
