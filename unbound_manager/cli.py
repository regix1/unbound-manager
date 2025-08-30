#!/usr/bin/env python3
"""Main CLI interface for Unbound Manager with interactive menu."""

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

from .constants import APP_VERSION
from .utils import check_root, check_service_status, run_command, prompt_yes_no
from .installer import UnboundInstaller
from .config_manager import ConfigManager
from .redis_manager import RedisManager
from .dnssec import DNSSECManager
from .troubleshooter import Troubleshooter
from .tester import UnboundTester
from .backup import BackupManager
from .menu_system import InteractiveMenu, MenuItem, MenuCategory

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
        unbound_status = check_service_status("unbound")
        redis_status = check_service_status("redis-server")
        
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
        # Service Control (most important)
        self.menu.add_item(MenuItem(
            "Service Control",
            self.manage_services_quick,
            prefix="[S]",
            description="Start/Stop DNS services",
            key="s"
        ))
        
        self.menu.add_item(MenuItem(
            "System Status",
            self.show_detailed_status,
            prefix="[T]",
            description="View status and statistics",
            key="t"
        ))
        
        self.menu.add_item(MenuItem(
            "View Logs",
            lambda: self.view_logs_interactive(),
            prefix="[L]",
            description="View system logs",
            key="l"
        ))
        
        # Configuration category
        config_category = MenuCategory("Configuration", prefix="[C]")
        config_category.add_item(MenuItem(
            "Edit Configuration",
            self.wrap_action(self.config_manager.manage_configuration),
            description="Modify DNS settings"
        ))
        config_category.add_item(MenuItem(
            "Access Control",
            self.wrap_action(self.config_manager.edit_access_control),
            description="Manage allowed networks"
        ))
        config_category.add_item(MenuItem(
            "Redis Cache",
            self.wrap_action(self.redis_manager.configure_redis),
            description="Configure caching"
        ))
        config_category.add_item(MenuItem(
            "DNSSEC Settings",
            self.wrap_action(self.dnssec_manager.manage_dnssec),
            description="Security configuration"
        ))
        self.menu.add_category(config_category)
        
        # Maintenance category
        maintenance_category = MenuCategory("Maintenance", prefix="[M]")
        maintenance_category.add_item(MenuItem(
            "Backup Configuration",
            self.backup_configuration_interactive,
            description="Create configuration backup"
        ))
        maintenance_category.add_item(MenuItem(
            "Restore Configuration",
            self.wrap_action(self.backup_manager.restore_backup),
            description="Restore from backup"
        ))
        maintenance_category.add_item(MenuItem(
            "Update Unbound",
            self.wrap_action(self.installer.update_unbound),
            description="Update DNS server version"
        ))
        maintenance_category.add_item(MenuItem(
            "Clean Backups",
            self.cleanup_backups,
            description="Remove old backups"
        ))
        self.menu.add_category(maintenance_category)
        
        # Diagnostics category
        diagnostic_category = MenuCategory("Diagnostics", prefix="[D]")
        diagnostic_category.add_item(MenuItem(
            "Run Diagnostics",
            self.wrap_action(self.troubleshooter.run_diagnostics),
            description="Check for issues"
        ))
        diagnostic_category.add_item(MenuItem(
            "Test DNS Resolution",
            self.wrap_action(self.tester.run_all_tests),
            description="Test DNS functionality"
        ))
        diagnostic_category.add_item(MenuItem(
            "Performance Benchmark",
            self.wrap_action(lambda: self.tester.test_performance(100)),
            description="Test query performance"
        ))
        diagnostic_category.add_item(MenuItem(
            "Network Connectivity",
            self.wrap_action(self.troubleshooter.check_connectivity),
            description="Check network status"
        ))
        self.menu.add_category(diagnostic_category)
        
        # Advanced category
        advanced_category = MenuCategory("Advanced Options", prefix="[A]")
        advanced_category.add_item(MenuItem(
            "Installation Manager",
            self.installation_menu,
            description="Install/Reinstall Unbound"
        ))
        advanced_category.add_item(MenuItem(
            "Regenerate Keys",
            self.wrap_action(self.dnssec_manager.generate_control_keys),
            description="Regenerate security keys"
        ))
        advanced_category.add_item(MenuItem(
            "Update This Tool",
            self.update_manager,
            description="Update Unbound Manager"
        ))
        advanced_category.add_item(MenuItem(
            "Uninstall Manager",
            self.uninstall_manager,
            description="Remove this tool",
            style="red"
        ))
        self.menu.add_category(advanced_category)
        
        # Help and Exit
        self.menu.add_item(MenuItem(
            "Help",
            self.show_help,
            prefix="[H]",
            description="Show help information",
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
        unbound_status = check_service_status("unbound")
        if unbound_status:
            unbound_display = "[green]● Active[/green]"
            unbound_details = self._get_service_uptime("unbound")
        else:
            unbound_display = "[red]○ Inactive[/red]"
            unbound_details = "Service not running"
        table.add_row("Unbound DNS", unbound_display, unbound_details)
        
        # Redis status
        redis_status = check_service_status("redis-server")
        if redis_status:
            redis_display = "[green]● Active[/green]"
            redis_details = self._get_service_uptime("redis-server")
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
                stats = {}
                for line in result.stdout.split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        stats[key] = value.strip()
                
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
        """Quick service management."""
        console.clear()
        
        # Header
        console.print("┌" + "─" * 58 + "┐")
        console.print("│                  [bold cyan]SERVICE CONTROL[/bold cyan]                       │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        # Show current status
        unbound_running = check_service_status("unbound")
        redis_running = check_service_status("redis-server")
        
        console.print("[bold]Current Status:[/bold]")
        console.print(f"  Unbound : {'[green]● Running[/green]' if unbound_running else '[red]○ Stopped[/red]'}")
        console.print(f"  Redis   : {'[green]● Running[/green]' if redis_running else '[red]○ Stopped[/red]'}")
        console.print()
        console.print("─" * 60)
        console.print()
        
        # Quick actions
        if not unbound_running:
            console.print("  [1] Start All Services")
        else:
            console.print("  [1] Restart All Services")
        
        console.print("  [2] Stop All Services")
        console.print("  [3] Advanced Service Control")
        console.print("  [0] Back to Main Menu")
        console.print()
        
        choice = Prompt.ask("Select action", choices=["0", "1", "2", "3"], default="0")
        
        if choice == "1":
            console.print("\n[cyan]Starting services...[/cyan]")
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                task = progress.add_task("Starting Redis...", total=None)
                restart_service("redis-server")
                progress.update(task, description="Starting Unbound...")
                restart_service("unbound")
                progress.update(task, completed=True)
            console.print("[green]✓[/green] Services started")
            time.sleep(2)
        elif choice == "2":
            console.print("\n[cyan]Stopping services...[/cyan]")
            run_command(["systemctl", "stop", "unbound"])
            run_command(["systemctl", "stop", "redis-server"])
            console.print("[yellow]Services stopped[/yellow]")
            time.sleep(2)
        elif choice == "3":
            self.manage_services_advanced()
    
    def manage_services_advanced(self) -> None:
        """Advanced service management."""
        console.clear()
        
        console.print("┌" + "─" * 58 + "┐")
        console.print("│              [bold cyan]ADVANCED SERVICE CONTROL[/bold cyan]                  │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        console.print("  [1] Start Unbound")
        console.print("  [2] Stop Unbound")
        console.print("  [3] Restart Unbound")
        console.print("  [4] Start Redis")
        console.print("  [5] Stop Redis")
        console.print("  [6] Restart Redis")
        console.print("  [0] Back")
        console.print()
        
        choice = Prompt.ask("Select action", choices=["0", "1", "2", "3", "4", "5", "6"])
        
        from .utils import restart_service
        
        actions = {
            "1": ("Starting Unbound...", lambda: restart_service("unbound")),
            "2": ("Stopping Unbound...", lambda: run_command(["systemctl", "stop", "unbound"])),
            "3": ("Restarting Unbound...", lambda: restart_service("unbound")),
            "4": ("Starting Redis...", lambda: restart_service("redis-server")),
            "5": ("Stopping Redis...", lambda: run_command(["systemctl", "stop", "redis-server"])),
            "6": ("Restarting Redis...", lambda: restart_service("redis-server")),
        }
        
        if choice != "0":
            msg, action = actions[choice]
            console.print(f"\n[cyan]{msg}[/cyan]")
            action()
            console.print("[green]✓[/green] Action completed")
            time.sleep(2)
    
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
        """Interactive log viewer."""
        console.clear()
        
        console.print("┌" + "─" * 58 + "┐")
        console.print("│                    [bold cyan]VIEW LOGS[/bold cyan]                          │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        console.print("  [1] Last 50 lines")
        console.print("  [2] Last 100 lines")
        console.print("  [3] Last 200 lines")
        console.print("  [4] Follow logs (real-time)")
        console.print("  [0] Back")
        console.print()
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4"])
        
        if choice == "1":
            self.troubleshooter.view_logs(50)
        elif choice == "2":
            self.troubleshooter.view_logs(100)
        elif choice == "3":
            self.troubleshooter.view_logs(200)
        elif choice == "4":
            console.print("\n[cyan]Following logs... Press Ctrl+C to stop[/cyan]\n")
            try:
                run_command(["journalctl", "-u", "unbound", "-f"])
            except KeyboardInterrupt:
                pass
        
        if choice != "0":
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
    
    def installation_menu(self) -> None:
        """Installation submenu."""
        console.clear()
        
        console.print("┌" + "─" * 58 + "┐")
        console.print("│              [bold cyan]INSTALLATION MANAGER[/bold cyan]                      │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        console.print("  [1] Fresh Installation")
        console.print("  [2] Fix Existing Installation")
        console.print("  [3] Reinstall Unbound")
        console.print("  [0] Back")
        console.print()
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3"])
        
        if choice == "1":
            self.installer.install_unbound()
        elif choice == "2":
            self.installer.fix_existing_installation()
        elif choice == "3":
            if prompt_yes_no("This will reinstall Unbound. Continue?", default=False):
                self.installer.install_unbound()
    
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
                "h             Show this help",
                "q             Exit program"
            ]),
            ("[bold]Quick Keys:[/bold]", [
                "s             Service control",
                "t             Status",
                "l             View logs",
                "1-9           Quick select"
            ]),
            ("[bold]Common Tasks:[/bold]", [
                "Service Control    Start/stop DNS services",
                "System Status      Check service health",
                "View Logs          Monitor activity",
                "Configuration      Modify settings",
                "Diagnostics        Troubleshoot issues"
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
        console.print("│              [bold cyan]UPDATE UNBOUND MANAGER[/bold cyan]                   │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        console.print(f"Current version: {APP_VERSION}")
        console.print("\n[yellow]Checking for updates...[/yellow]")
        
        try:
            import requests
            response = requests.get(
                "https://raw.githubusercontent.com/regix1/unbound-manager/main/VERSION",
                timeout=5
            )
            
            if response.status_code == 200:
                remote_version = response.text.strip()
                console.print(f"Latest version:  {remote_version}")
                
                if remote_version != APP_VERSION:
                    console.print("\n[yellow]Update available![/yellow]")
                    if prompt_yes_no("\nUpdate now?", default=True):
                        self.perform_update()
                else:
                    console.print("\n[green]✓ Already up to date[/green]")
            else:
                console.print("[yellow]Could not check for updates[/yellow]")
                
        except Exception as e:
            console.print(f"[yellow]Update check failed: {e}[/yellow]")
        
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