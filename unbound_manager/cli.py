#!/usr/bin/env python3
"""Main CLI interface for Unbound Manager."""

import sys
import os
import time
import shutil
import tempfile
from typing import Optional
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

console = Console()


class UnboundManagerCLI:
    """Main CLI class for Unbound Manager."""
    
    def __init__(self):
        """Initialize the CLI."""
        self.installer = UnboundInstaller()
        self.config_manager = ConfigManager()
        self.redis_manager = RedisManager()
        self.dnssec_manager = DNSSECManager()
        self.troubleshooter = Troubleshooter()
        self.tester = UnboundTester()
        self.backup_manager = BackupManager()
    
    def show_banner(self) -> None:
        """Display the application banner."""
        console.clear()
        
        banner_text = Text()
        banner_text.append("╔════════════════════════════════════════════════════════════════╗\n", style="blue")
        banner_text.append("║                                                                ║\n", style="blue")
        banner_text.append("║", style="blue")
        banner_text.append("                UNBOUND DNS SERVER MANAGER                  ", style="bold white")
        banner_text.append("║\n", style="blue")
        banner_text.append("║", style="blue")
        banner_text.append(f"                         Version {APP_VERSION}                        ", style="cyan")
        banner_text.append("║\n", style="blue")
        banner_text.append("║                                                                ║\n", style="blue")
        banner_text.append("╚════════════════════════════════════════════════════════════════╝", style="blue")
        
        console.print(Align.center(banner_text))
        console.print(Align.center("[yellow]A complete solution for Unbound DNS server management[/yellow]"))
        console.print(Align.center("[cyan]Secure, Reliable, and Easy to Configure[/cyan]\n"))
    
    def show_status(self) -> None:
        """Show current system status."""
        table = Table(title="System Status", title_style="bold cyan")
        table.add_column("Service", style="cyan")
        table.add_column("Status", justify="center")
        
        # Check Unbound status
        unbound_status = check_service_status("unbound")
        unbound_status_str = "[green]● Running[/green]" if unbound_status else "[red]○ Stopped[/red]"
        table.add_row("Unbound DNS", unbound_status_str)
        
        # Check Redis status
        redis_status = check_service_status("redis-server")
        redis_status_str = "[green]● Running[/green]" if redis_status else "[red]○ Stopped[/red]"
        table.add_row("Redis Cache", redis_status_str)
        
        console.print(table)
        console.print()
    
    def show_menu(self) -> Optional[str]:
        """Display the main menu and get user choice."""
        # Installation & Setup section
        console.print(Panel.fit(
            "[bold white]INSTALLATION & SETUP[/bold white]\n\n"
            "[green]1[/green]. Install Unbound (Fresh Installation)\n"
            "[green]2[/green]. Fix Existing Installation\n"
            "[green]3[/green]. Update Unbound Version",
            border_style="blue"
        ))
        
        # Configuration section
        console.print(Panel.fit(
            "[bold white]CONFIGURATION[/bold white]\n\n"
            "[green]4[/green]. Manage Configuration\n"
            "[green]5[/green]. Configure Redis Integration\n"
            "[green]6[/green]. DNSSEC Management",
            border_style="blue"
        ))
        
        # Maintenance section
        console.print(Panel.fit(
            "[bold white]MAINTENANCE[/bold white]\n\n"
            "[green]7[/green]. Backup Configuration\n"
            "[green]8[/green]. Restore Configuration\n"
            "[green]9[/green]. Regenerate Control Keys",
            border_style="blue"
        ))
        
        # Troubleshooting section
        console.print(Panel.fit(
            "[bold white]TROUBLESHOOTING[/bold white]\n\n"
            "[green]10[/green]. Troubleshoot Installation\n"
            "[green]11[/green]. Test Unbound Functionality\n"
            "[green]12[/green]. View Logs",
            border_style="blue"
        ))
        
        # System section
        console.print(Panel.fit(
            "[bold white]SYSTEM[/bold white]\n\n"
            "[green]13[/green]. Start/Stop Services\n"
            "[green]14[/green]. View Statistics",
            border_style="blue"
        ))
        
        # Manager Tools section
        console.print(Panel.fit(
            "[bold white]MANAGER TOOLS[/bold white]\n\n"
            "[green]15[/green]. Update Unbound Manager\n"
            "[green]16[/green]. Uninstall Unbound Manager\n"
            "[green]0[/green]. Exit",
            border_style="blue"
        ))
        
        console.print()
        choice = Prompt.ask(
            "[yellow]Please select an option[/yellow]",
            choices=[str(i) for i in range(17)],
            default="0"
        )
        
        return choice
    
    def uninstall_manager(self) -> None:
        """Uninstall Unbound Manager."""
        console.print(Panel.fit(
            "[bold red]Uninstall Unbound Manager[/bold red]\n\n"
            "This will remove the Unbound Manager Python package.\n"
            "Your Unbound DNS configuration will NOT be removed.",
            border_style="red"
        ))
        
        if not prompt_yes_no("Do you want to uninstall Unbound Manager?", default=False):
            console.print("[yellow]Uninstall cancelled[/yellow]")
            return
        
        # Create configuration backup first
        console.print("[cyan]Creating backup of configuration...[/cyan]")
        from .backup import BackupManager
        backup_manager = BackupManager()
        backup_path = backup_manager.create_backup("before_uninstall")
        console.print(f"[green]✓[/green] Configuration backed up to: {backup_path}")
        
        # Ask about removing Unbound itself
        remove_unbound = prompt_yes_no(
            "\n[yellow]Also remove Unbound DNS server?[/yellow]\n"
            "[red]WARNING: This will remove your DNS server![/red]",
            default=False
        )
        
        if remove_unbound:
            console.print("[yellow]Stopping Unbound service...[/yellow]")
            run_command(["systemctl", "stop", "unbound"], check=False)
            run_command(["systemctl", "disable", "unbound"], check=False)
            
            # Remove Unbound files
            console.print("[yellow]Removing Unbound...[/yellow]")
            files_to_remove = [
                "/usr/sbin/unbound",
                "/usr/sbin/unbound-anchor",
                "/usr/sbin/unbound-checkconf",
                "/usr/sbin/unbound-control",
                "/usr/sbin/unbound-control-setup",
                "/usr/sbin/unbound-host",
                "/etc/systemd/system/unbound.service",
            ]
            
            for file_path in files_to_remove:
                if Path(file_path).exists():
                    Path(file_path).unlink()
            
            run_command(["systemctl", "daemon-reload"], check=False)
            console.print("[green]✓[/green] Unbound removed")
        
        # Uninstall Python package
        console.print("[yellow]Removing Unbound Manager Python package...[/yellow]")
        try:
            run_command(["pip3", "uninstall", "-y", "unbound-manager"], check=False)
            console.print("[green]✓[/green] Unbound Manager package removed")
        except Exception as e:
            console.print(f"[yellow]Could not uninstall package: {e}[/yellow]")
        
        # Remove command from /usr/local/bin if it exists
        manager_cmd = Path("/usr/local/bin/unbound-manager")
        if manager_cmd.exists():
            manager_cmd.unlink()
            console.print("[green]✓[/green] Removed /usr/local/bin/unbound-manager")
        
        console.print(Panel.fit(
            "[bold green]Uninstall Complete![/bold green]\n\n"
            f"Configuration backup saved to: {backup_path}\n"
            "Source directory preserved at: ~/unbound-manager\n\n"
            "To remove source directory:\n"
            "  rm -rf ~/unbound-manager",
            border_style="green"
        ))
        
        console.print("\n[yellow]Exiting...[/yellow]")
        sys.exit(0)
    
    def update_manager(self) -> None:
        """Update Unbound Manager to the latest version."""
        console.print(Panel.fit(
            "[bold cyan]Update Unbound Manager[/bold cyan]\n\n"
            "This will update the Unbound Manager to the latest version.",
            border_style="cyan"
        ))
        
        # Check current version
        console.print(f"[cyan]Current version:[/cyan] {APP_VERSION}")
        
        # Check for updates first
        self.check_for_updates()
        
        # Ask if user wants to proceed with update
        if prompt_yes_no("\nProceed with update?", default=True):
            self.perform_update()
    
    def check_for_updates(self) -> None:
        """Check for updates from GitHub."""
        console.print(Panel.fit(
            "[bold cyan]Update Manager[/bold cyan]",
            border_style="cyan"
        ))
        
        try:
            # Check current version
            version_file = Path(__file__).parent.parent / "VERSION"
            if version_file.exists():
                current_version = version_file.read_text().strip()
            else:
                current_version = APP_VERSION
            
            console.print(f"[cyan]Current version:[/cyan] {current_version}")
            
            # Check for updates
            import requests
            
            console.print("[yellow]Checking for updates...[/yellow]")
            
            try:
                response = requests.get(
                    "https://api.github.com/repos/regix1/unbound-manager/releases/latest",
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    latest_version = data.get("tag_name", "").lstrip("v")
                    
                    if not latest_version:
                        # No releases yet, check commits
                        console.print("[yellow]No releases found, checking latest commits...[/yellow]")
                        self.check_git_updates()
                        return
                    
                    console.print(f"[cyan]Latest version:[/cyan] {latest_version}")
                    
                    if latest_version != current_version:
                        console.print("\n[yellow]⚠ An update is available![/yellow]")
                        
                        # Show release notes if available
                        if data.get("body"):
                            console.print("\n[cyan]Release Notes:[/cyan]")
                            console.print(Panel(data["body"][:500], border_style="dim"))
                        
                        if prompt_yes_no("Would you like to update now?"):
                            self.perform_update()
                    else:
                        console.print("\n[green]✓ You are running the latest version[/green]")
                elif response.status_code == 404:
                    console.print("[yellow]No releases found on GitHub[/yellow]")
                    self.check_git_updates()
                else:
                    console.print(f"[yellow]Could not check for updates (HTTP {response.status_code})[/yellow]")
                    
            except requests.exceptions.RequestException as e:
                console.print(f"[yellow]Could not connect to GitHub: {e}[/yellow]")
                console.print("[cyan]You can manually update with: cd ~/unbound-manager && git pull[/cyan]")
                
        except ImportError:
            console.print("[red]requests library not installed[/red]")
            console.print("[cyan]Install with: pip3 install requests[/cyan]")
        except Exception as e:
            console.print(f"[red]Error checking for updates: {e}[/red]")
    
    def check_git_updates(self) -> None:
        """Check for updates using git."""
        try:
            project_dir = Path(__file__).parent.parent
            
            # Fetch latest changes
            console.print("[cyan]Fetching latest changes from git...[/cyan]")
            result = run_command(
                ["git", "fetch"],
                cwd=project_dir,
                check=False
            )
            
            # Check if we're behind
            result = run_command(
                ["git", "status", "-uno"],
                cwd=project_dir,
                check=False
            )
            
            if "Your branch is behind" in result.stdout:
                console.print("\n[yellow]⚠ Updates are available![/yellow]")
                if prompt_yes_no("Would you like to update now?"):
                    self.perform_update()
            elif "Your branch is up to date" in result.stdout:
                console.print("\n[green]✓ You are running the latest version[/green]")
            else:
                console.print("\n[cyan]Repository status:[/cyan]")
                console.print(result.stdout)
                
        except Exception as e:
            console.print(f"[yellow]Could not check git status: {e}[/yellow]")
    
    def perform_update(self) -> None:
        """Perform auto-update."""
        console.print("\n[cyan]Starting update process...[/cyan]")
        
        try:
            project_dir = Path(__file__).parent.parent
            
            # Create backup first
            console.print("[cyan]Creating backup before update...[/cyan]")
            
            import time
            timestamp = int(time.time())
            backup_dir = project_dir.parent / f"unbound-manager.backup.{timestamp}"
            
            # Stash any local changes
            console.print("[cyan]Stashing local changes...[/cyan]")
            run_command(
                ["git", "stash"],
                cwd=project_dir,
                check=False
            )
            
            # Pull latest changes
            console.print("[cyan]Pulling latest changes from GitHub...[/cyan]")
            result = run_command(
                ["git", "pull", "origin", "main"],
                cwd=project_dir,
                check=False
            )
            
            if result.returncode != 0:
                # Try master branch if main doesn't exist
                result = run_command(
                    ["git", "pull", "origin", "master"],
                    cwd=project_dir,
                    check=False
                )
            
            if result.returncode == 0:
                console.print("[green]✓ Code updated successfully[/green]")
                
                # Reinstall pip package
                console.print("[cyan]Updating Python package...[/cyan]")
                result = run_command(
                    ["pip3", "install", "-e", "."],
                    cwd=project_dir,
                    check=False
                )
                
                if result.returncode == 0:
                    console.print("[green]✓ Python package updated[/green]")
                    
                    # Update VERSION file if needed
                    version_file = project_dir / "VERSION"
                    if not version_file.exists():
                        version_file.write_text(APP_VERSION)
                    
                    console.print("\n[green]✓ Update completed successfully![/green]")
                    console.print("[yellow]Please restart unbound-manager to use the new version[/yellow]")
                    
                    # Ask to restart
                    if prompt_yes_no("Restart now?"):
                        console.print("[cyan]Restarting...[/cyan]")
                        import os
                        import sys
                        os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    console.print("[yellow]Warning: Could not update Python package[/yellow]")
                    console.print("[cyan]Try manually: pip3 install -e ~/unbound-manager[/cyan]")
            else:
                console.print("[red]Update failed. Please check the error messages above.[/red]")
                console.print("[cyan]You can try updating manually:[/cyan]")
                console.print("  cd ~/unbound-manager")
                console.print("  git pull")
                console.print("  pip3 install -e .")
                
        except Exception as e:
            console.print(f"[red]Error during update: {e}[/red]")
            console.print("[yellow]Please update manually using the instructions above[/yellow]")
    
    def handle_choice(self, choice: str) -> bool:
        """
        Handle menu choice.
        
        Returns:
            bool: True to continue, False to exit
        """
        console.clear()
        
        try:
            if choice == "0":
                console.print("[cyan]Thank you for using Unbound Manager![/cyan]")
                return False
            
            elif choice == "1":
                # Fresh installation
                self.installer.install_unbound()
            
            elif choice == "2":
                # Fix existing installation
                self.installer.fix_existing_installation()
            
            elif choice == "3":
                # Update Unbound
                self.installer.update_unbound()
            
            elif choice == "4":
                # Manage configuration
                self.config_manager.manage_configuration()
            
            elif choice == "5":
                # Configure Redis
                self.redis_manager.configure_redis()
            
            elif choice == "6":
                # DNSSEC Management
                self.dnssec_manager.manage_dnssec()
            
            elif choice == "7":
                # Backup configuration
                description = Prompt.ask(
                    "[cyan]Enter backup description (optional)[/cyan]",
                    default=""
                )
                self.backup_manager.create_backup(description)
            
            elif choice == "8":
                # Restore configuration
                self.backup_manager.restore_backup()
            
            elif choice == "9":
                # Regenerate control keys
                self.dnssec_manager.generate_control_keys()
            
            elif choice == "10":
                # Troubleshoot
                self.troubleshooter.run_diagnostics()
            
            elif choice == "11":
                # Test functionality
                self.tester.run_all_tests()
            
            elif choice == "12":
                # View logs
                lines = IntPrompt.ask(
                    "[cyan]Number of log lines to show[/cyan]",
                    default=50
                )
                self.troubleshooter.view_logs(lines)
            
            elif choice == "13":
                # Start/Stop services
                self.manage_services()
            
            elif choice == "14":
                # View statistics
                self.troubleshooter.show_statistics()
            
            elif choice == "15":
                # Update Unbound Manager
                self.update_manager()
            
            elif choice == "16":
                # Uninstall Unbound Manager
                self.uninstall_manager()
            
            else:
                console.print("[red]Invalid option selected[/red]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
        except Exception as e:
            console.print(f"[red]An error occurred: {e}[/red]")
            import traceback
            if "--debug" in sys.argv:
                console.print("[dim]" + traceback.format_exc() + "[/dim]")
        
        console.print("\n[cyan]Press Enter to continue...[/cyan]")
        input()
        return True
    
    def manage_services(self) -> None:
        """Manage Unbound and Redis services."""
        from .utils import restart_service
        
        console.print(Panel.fit(
            "[bold]Service Management[/bold]\n\n"
            "[green]1[/green]. Start Unbound\n"
            "[green]2[/green]. Stop Unbound\n"
            "[green]3[/green]. Restart Unbound\n"
            "[green]4[/green]. Start Redis\n"
            "[green]5[/green]. Stop Redis\n"
            "[green]6[/green]. Restart Redis\n"
            "[green]7[/green]. Restart All Services\n"
            "[green]8[/green]. View Service Status\n"
            "[green]0[/green]. Back",
            border_style="cyan"
        ))
        
        choice = Prompt.ask("Select action", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8"])
        
        if choice == "1":
            if restart_service("unbound"):
                console.print("[green]✓ Unbound service started[/green]")
            else:
                console.print("[red]✗ Failed to start Unbound[/red]")
        elif choice == "2":
            run_command(["systemctl", "stop", "unbound"])
            console.print("[yellow]Unbound service stopped[/yellow]")
        elif choice == "3":
            if restart_service("unbound"):
                console.print("[green]✓ Unbound service restarted[/green]")
            else:
                console.print("[red]✗ Failed to restart Unbound[/red]")
        elif choice == "4":
            if restart_service("redis-server"):
                console.print("[green]✓ Redis service started[/green]")
            else:
                console.print("[red]✗ Failed to start Redis[/red]")
        elif choice == "5":
            run_command(["systemctl", "stop", "redis-server"])
            console.print("[yellow]Redis service stopped[/yellow]")
        elif choice == "6":
            if restart_service("redis-server"):
                console.print("[green]✓ Redis service restarted[/green]")
            else:
                console.print("[red]✗ Failed to restart Redis[/red]")
        elif choice == "7":
            redis_ok = restart_service("redis-server")
            unbound_ok = restart_service("unbound")
            if redis_ok and unbound_ok:
                console.print("[green]✓ All services restarted successfully[/green]")
            else:
                console.print("[yellow]⚠ Some services failed to restart[/yellow]")
        elif choice == "8":
            # Show detailed status
            console.print("\n[cyan]Service Status Details:[/cyan]\n")
            
            for service in ["unbound", "redis-server"]:
                result = run_command(
                    ["systemctl", "status", service, "--no-pager"],
                    check=False
                )
                console.print(f"[bold]{service}:[/bold]")
                console.print(result.stdout[:500])  # First 500 chars
                console.print()
    
    def run(self) -> None:
        """Run the main application loop."""
        check_root()
        
        # Check for updates on startup (optional)
        if "--no-update-check" not in sys.argv:
            try:
                import requests
                # Quick update check without blocking
                console.print("[dim]Checking for updates...[/dim]", end="\r")
                # This is done silently in background
            except ImportError:
                pass  # requests not installed, skip update check
        
        while True:
            self.show_banner()
            self.show_status()
            
            choice = self.show_menu()
            if choice is None:
                break
            
            if not self.handle_choice(choice):
                break


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