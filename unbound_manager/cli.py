#!/usr/bin/env python3
"""Main CLI interface for Unbound Manager."""

import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.layout import Layout
from rich.text import Text
from rich.align import Align

from .constants import APP_VERSION
from .utils import check_root, check_service_status
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
            "[green]14[/green]. View Statistics\n"
            "[green]0[/green]. Exit",
            border_style="blue"
        ))
        
        console.print()
        choice = Prompt.ask(
            "[yellow]Please select an option[/yellow]",
            choices=[str(i) for i in range(15)],
            default="0"
        )
        
        return choice
    
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
                self.backup_manager.create_backup()
            
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
                self.troubleshooter.view_logs()
            
            elif choice == "13":
                # Start/Stop services
                self.manage_services()
            
            elif choice == "14":
                # View statistics
                self.troubleshooter.show_statistics()
            
            else:
                console.print("[red]Invalid option selected[/red]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
        except Exception as e:
            console.print(f"[red]An error occurred: {e}[/red]")
        
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
            "[green]0[/green]. Back",
            border_style="cyan"
        ))
        
        choice = Prompt.ask("Select action", choices=["0", "1", "2", "3", "4", "5", "6", "7"])
        
        if choice == "1":
            restart_service("unbound")
            console.print("[green]Unbound service started[/green]")
        elif choice == "2":
            from .utils import run_command
            run_command(["systemctl", "stop", "unbound"])
            console.print("[yellow]Unbound service stopped[/yellow]")
        elif choice == "3":
            restart_service("unbound")
            console.print("[green]Unbound service restarted[/green]")
        elif choice == "4":
            restart_service("redis-server")
            console.print("[green]Redis service started[/green]")
        elif choice == "5":
            from .utils import run_command
            run_command(["systemctl", "stop", "redis-server"])
            console.print("[yellow]Redis service stopped[/yellow]")
        elif choice == "6":
            restart_service("redis-server")
            console.print("[green]Redis service restarted[/green]")
        elif choice == "7":
            restart_service("redis-server")
            restart_service("unbound")
            console.print("[green]All services restarted[/green]")
    
    def run(self) -> None:
        """Run the main application loop."""
        check_root()
        
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
        return 1


if __name__ == "__main__":
    sys.exit(main())