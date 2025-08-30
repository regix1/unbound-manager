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
    
    def show_banner(self) -> None:
        """Display the application banner with status."""
        console.clear()
        
        # Get service status
        unbound_status = check_service_status("unbound")
        redis_status = check_service_status("redis-server")
        
        # Build status line
        if unbound_status and redis_status:
            status_color = "green"
            status_text = "All Services Running"
        elif unbound_status:
            status_color = "yellow"
            status_text = "Unbound Running | Redis Stopped"
        elif redis_status:
            status_color = "yellow"
            status_text = "Unbound Stopped | Redis Running"
        else:
            status_color = "red"
            status_text = "All Services Stopped"
        
        # Simple, clean banner
        console.print()
        console.print(f"[bold cyan]UNBOUND DNS MANAGER[/bold cyan] [dim]v{APP_VERSION}[/dim]")
        console.print("━" * 40, style="dim")
        console.print(f"[{status_color}]● {status_text}[/{status_color}]")
        console.print()
    
    def setup_menu(self) -> None:
        """Setup the interactive menu structure."""
        # Quick Actions (most common tasks)
        self.menu.add_item(MenuItem(
            "Start/Stop Services",
            self.manage_services_quick,
            icon="⚡",
            description="Quick service control"
        ))
        
        self.menu.add_item(MenuItem(
            "View Status",
            self.show_detailed_status,
            icon="📊",
            description="System status and statistics"
        ))
        
        self.menu.add_item(MenuItem(
            "View Logs",
            lambda: self.view_logs_interactive(),
            icon="📜",
            description="View recent logs"
        ))
        
        # Configuration category
        config_category = MenuCategory("Configuration", icon="⚙️")
        config_category.add_item(MenuItem(
            "Edit Configuration",
            self.config_manager.manage_configuration,
            description="Modify DNS settings"
        ))
        config_category.add_item(MenuItem(
            "Access Control",
            self.config_manager.edit_access_control,
            description="Manage allowed networks"
        ))
        config_category.add_item(MenuItem(
            "Redis Settings",
            self.redis_manager.configure_redis,
            description="Configure caching"
        ))
        config_category.add_item(MenuItem(
            "DNSSEC",
            self.dnssec_manager.manage_dnssec,
            description="DNSSEC configuration"
        ))
        self.menu.add_category(config_category)
        
        # Maintenance category
        maintenance_category = MenuCategory("Maintenance", icon="🔧")
        maintenance_category.add_item(MenuItem(
            "Backup Configuration",
            self.backup_configuration_interactive,
            description="Create backup"
        ))
        maintenance_category.add_item(MenuItem(
            "Restore Configuration",
            self.backup_manager.restore_backup,
            description="Restore from backup"
        ))
        maintenance_category.add_item(MenuItem(
            "Update Unbound",
            self.installer.update_unbound,
            description="Update DNS server"
        ))
        self.menu.add_category(maintenance_category)
        
        # Troubleshooting category
        troubleshoot_category = MenuCategory("Troubleshooting", icon="🔍")
        troubleshoot_category.add_item(MenuItem(
            "Run Diagnostics",
            self.troubleshooter.run_diagnostics,
            description="Check for issues"
        ))
        troubleshoot_category.add_item(MenuItem(
            "Test DNS",
            self.tester.run_all_tests,
            description="Test functionality"
        ))
        troubleshoot_category.add_item(MenuItem(
            "Performance Test",
            lambda: self.tester.test_performance(100),
            description="Benchmark DNS"
        ))
        self.menu.add_category(troubleshoot_category)
        
        # Advanced category (less common tasks)
        advanced_category = MenuCategory("Advanced", icon="🚀")
        advanced_category.add_item(MenuItem(
            "Install/Reinstall",
            self.installation_menu,
            description="Installation options"
        ))
        advanced_category.add_item(MenuItem(
            "Regenerate Keys",
            self.dnssec_manager.generate_control_keys,
            description="Regenerate control keys"
        ))
        advanced_category.add_item(MenuItem(
            "Update Manager",
            self.update_manager,
            description="Update this tool"
        ))
        advanced_category.add_item(MenuItem(
            "Uninstall Manager",
            self.uninstall_manager,
            description="Remove this tool",
            style="red"
        ))
        self.menu.add_category(advanced_category)
        
        # Add help and exit
        self.menu.add_item(MenuItem(
            "Help",
            self.show_help,
            icon="❓",
            description="Show help",
            key="h"
        ))
        
        self.menu.add_item(MenuItem(
            "Exit",
            lambda: False,
            icon="🚪",
            description="Exit program",
            key="q",
            style="red"
        ))
    
    def show_detailed_status(self) -> None:
        """Show detailed system status."""
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]System Status[/bold cyan]",
            border_style="cyan"
        ))
        
        # Service status
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Service", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details")
        
        # Unbound status
        unbound_status = check_service_status("unbound")
        if unbound_status:
            unbound_display = "[green]● Running[/green]"
            unbound_details = self._get_service_uptime("unbound")
        else:
            unbound_display = "[red]○ Stopped[/red]"
            unbound_details = "Service not running"
        table.add_row("Unbound DNS", unbound_display, unbound_details)
        
        # Redis status
        redis_status = check_service_status("redis-server")
        if redis_status:
            redis_display = "[green]● Running[/green]"
            redis_details = self._get_service_uptime("redis-server")
        else:
            redis_display = "[red]○ Stopped[/red]"
            redis_details = "Service not running"
        table.add_row("Redis Cache", redis_display, redis_details)
        
        console.print(table)
        
        # Show statistics if services are running
        if unbound_status:
            console.print("\n[cyan]DNS Statistics:[/cyan]")
            self._show_quick_stats()
        
        if redis_status:
            console.print("\n[cyan]Cache Statistics:[/cyan]")
            self._show_cache_stats()
        
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
                    # Parse and calculate uptime
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
                
                # Calculate hit rate
                if int(queries) > 0:
                    hit_rate = (int(cache_hits) / int(queries)) * 100
                    console.print(f"  Total queries: {queries}")
                    console.print(f"  Cache hits: {cache_hits}")
                    console.print(f"  Hit rate: [green]{hit_rate:.1f}%[/green]")
                else:
                    console.print("  No queries yet")
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
                for line in result.stdout.split('\n'):
                    if 'keyspace_hits:' in line:
                        hits = line.split(':')[1].strip()
                        console.print(f"  Keyspace hits: {hits}")
                    elif 'keyspace_misses:' in line:
                        misses = line.split(':')[1].strip()
                        console.print(f"  Keyspace misses: {misses}")
        except Exception:
            console.print("  [yellow]Cache statistics unavailable[/yellow]")
    
    def manage_services_quick(self) -> None:
        """Quick service management."""
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]Service Management[/bold cyan]",
            border_style="cyan"
        ))
        
        # Show current status
        unbound_running = check_service_status("unbound")
        redis_running = check_service_status("redis-server")
        
        console.print("Current Status:")
        console.print(f"  Unbound: {'[green]Running[/green]' if unbound_running else '[red]Stopped[/red]'}")
        console.print(f"  Redis: {'[green]Running[/green]' if redis_running else '[red]Stopped[/red]'}")
        console.print()
        
        # Quick actions based on status
        if not unbound_running:
            console.print("[green]1[/green]. Start All Services")
        else:
            console.print("[green]1[/green]. Restart All Services")
        
        console.print("[green]2[/green]. Stop All Services")
        console.print("[green]3[/green]. Advanced Service Control")
        console.print("[green]0[/green]. Back")
        
        choice = Prompt.ask("Select action", choices=["0", "1", "2", "3"], default="0")
        
        if choice == "1":
            console.print("[cyan]Starting services...[/cyan]")
            restart_service("redis-server")
            restart_service("unbound")
            console.print("[green]✓[/green] Services started")
            time.sleep(2)
        elif choice == "2":
            console.print("[cyan]Stopping services...[/cyan]")
            run_command(["systemctl", "stop", "unbound"])
            run_command(["systemctl", "stop", "redis-server"])
            console.print("[yellow]Services stopped[/yellow]")
            time.sleep(2)
        elif choice == "3":
            self.manage_services_advanced()
    
    def manage_services_advanced(self) -> None:
        """Advanced service management."""
        from .utils import restart_service
        
        console.clear()
        console.print(Panel.fit(
            "[bold]Advanced Service Control[/bold]",
            border_style="cyan"
        ))
        
        console.print("[green]1[/green]. Start Unbound")
        console.print("[green]2[/green]. Stop Unbound")
        console.print("[green]3[/green]. Restart Unbound")
        console.print("[green]4[/green]. Start Redis")
        console.print("[green]5[/green]. Stop Redis")
        console.print("[green]6[/green]. Restart Redis")
        console.print("[green]0[/green]. Back")
        
        choice = Prompt.ask("Select action", choices=["0", "1", "2", "3", "4", "5", "6"])
        
        actions = {
            "1": lambda: restart_service("unbound"),
            "2": lambda: run_command(["systemctl", "stop", "unbound"]),
            "3": lambda: restart_service("unbound"),
            "4": lambda: restart_service("redis-server"),
            "5": lambda: run_command(["systemctl", "stop", "redis-server"]),
            "6": lambda: restart_service("redis-server"),
        }
        
        if choice != "0":
            actions[choice]()
            console.print("[green]✓[/green] Action completed")
            time.sleep(2)
    
    def backup_configuration_interactive(self) -> None:
        """Interactive backup creation."""
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]Create Backup[/bold cyan]",
            border_style="cyan"
        ))
        
        description = Prompt.ask(
            "[cyan]Enter backup description (optional)[/cyan]",
            default=""
        )
        
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
    
    def view_logs_interactive(self) -> None:
        """Interactive log viewer."""
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]View Logs[/bold cyan]",
            border_style="cyan"
        ))
        
        console.print("[green]1[/green]. Last 50 lines")
        console.print("[green]2[/green]. Last 100 lines")
        console.print("[green]3[/green]. Last 200 lines")
        console.print("[green]4[/green]. Follow logs (real-time)")
        console.print("[green]0[/green]. Back")
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4"])
        
        if choice == "1":
            self.troubleshooter.view_logs(50)
        elif choice == "2":
            self.troubleshooter.view_logs(100)
        elif choice == "3":
            self.troubleshooter.view_logs(200)
        elif choice == "4":
            console.print("[cyan]Following logs... Press Ctrl+C to stop[/cyan]\n")
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
        console.print(Panel.fit(
            "[bold cyan]Installation Options[/bold cyan]",
            border_style="cyan"
        ))
        
        console.print("[green]1[/green]. Fresh Installation")
        console.print("[green]2[/green]. Fix Existing Installation")
        console.print("[green]3[/green]. Reinstall Unbound")
        console.print("[green]0[/green]. Back")
        
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
        console.print(Panel.fit(
            "[bold cyan]Unbound Manager Help[/bold cyan]",
            border_style="cyan"
        ))
        
        help_text = """
[bold]Navigation:[/bold]
  ↑/↓ or j/k  : Navigate menu
  Enter       : Select item
  Esc or b    : Go back
  h           : Show this help
  q           : Exit program

[bold]Quick Keys:[/bold]
  1-9         : Quick select menu item
  /           : Search (if available)

[bold]Common Tasks:[/bold]
  • Start Services: Quick way to get Unbound running
  • View Status: Check if everything is working
  • View Logs: See what's happening
  • Edit Configuration: Modify DNS settings
  • Run Diagnostics: Check for problems

[bold]First Time Setup:[/bold]
  1. Run 'Installation Options' → 'Fresh Installation'
  2. Configure your settings in 'Configuration'
  3. Start services from main menu

[bold]Documentation:[/bold]
  GitHub: https://github.com/regix1/unbound-manager
  
[bold]Support:[/bold]
  Report issues on GitHub
        """
        console.print(help_text)
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()
    
    def update_manager(self) -> None:
        """Update Unbound Manager to the latest version."""
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]Update Unbound Manager[/bold cyan]",
            border_style="cyan"
        ))
        
        console.print(f"[cyan]Current version:[/cyan] {APP_VERSION}")
        
        # Check for updates
        console.print("[yellow]Checking for updates...[/yellow]")
        
        try:
            import requests
            response = requests.get(
                "https://raw.githubusercontent.com/regix1/unbound-manager/main/VERSION",
                timeout=5
            )
            
            if response.status_code == 200:
                remote_version = response.text.strip()
                console.print(f"[cyan]Latest version:[/cyan] {remote_version}")
                
                if remote_version != APP_VERSION:
                    console.print("\n[yellow]⚠ An update is available![/yellow]")
                    if prompt_yes_no("\nUpdate now?", default=True):
                        self.perform_update()
                else:
                    console.print("\n[green]✓ You are running the latest version[/green]")
            else:
                console.print("[yellow]Could not check for updates[/yellow]")
                
        except Exception as e:
            console.print(f"[yellow]Could not check for updates: {e}[/yellow]")
        
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()
    
    def perform_update(self) -> None:
        """Perform the update."""
        console.print("\n[cyan]Updating Unbound Manager...[/cyan]")
        
        try:
            # Find the source directory
            source_dir = Path.home() / "unbound-manager"
            
            if source_dir.exists() and (source_dir / ".git").exists():
                # Git pull
                console.print("[cyan]Pulling latest changes...[/cyan]")
                run_command(["git", "pull"], cwd=source_dir)
                
                # Reinstall
                console.print("[cyan]Reinstalling package...[/cyan]")
                run_command(["pip3", "install", "-e", "."], cwd=source_dir)
                
                console.print("[green]✓ Update complete! Please restart the program.[/green]")
            else:
                console.print("[yellow]Source directory not found. Please update manually.[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Update failed: {e}[/red]")
    
    def uninstall_manager(self) -> None:
        """Uninstall Unbound Manager."""
        console.clear()
        console.print(Panel.fit(
            "[bold red]Uninstall Unbound Manager[/bold red]\n\n"
            "This will remove the Unbound Manager tool.\n"
            "Your DNS configuration will be preserved.",
            border_style="red"
        ))
        
        if not prompt_yes_no("Are you sure you want to uninstall?", default=False):
            return
        
        # Backup configuration first
        console.print("[cyan]Creating backup...[/cyan]")
        backup_path = self.backup_manager.create_backup("before_uninstall")
        console.print(f"[green]✓[/green] Backup saved to: {backup_path}")
        
        # Uninstall
        console.print("[yellow]Uninstalling Unbound Manager...[/yellow]")
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
                console.print("\n[cyan]Thank you for using Unbound Manager![/cyan]")
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
        console.print("\n[yellow]Application terminated by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        import traceback
        if "--debug" in sys.argv:
            console.print("[dim]" + traceback.format_exc() + "[/dim]")
        return 1


if __name__ == "__main__":
    sys.exit(main())