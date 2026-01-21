"""Backup and restore functionality for Unbound."""

from __future__ import annotations

import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from .constants import UNBOUND_DIR, BACKUP_DIR
from .utils import ensure_directory, prompt_yes_no
from .menu_system import SubMenu

console = Console()


class BackupManager:
    """Manage Unbound configuration backups."""
    
    def __init__(self):
        """Initialize backup manager."""
        ensure_directory(BACKUP_DIR, owner=None, group=None)
    
    def create_backup(self, description: str = "") -> Path:
        """Create a backup of current configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        
        if description:
            backup_name += f"_{description.replace(' ', '_')}"
        
        backup_path = BACKUP_DIR / f"{backup_name}.tar.gz"
        
        console.print(f"[cyan]Creating backup: {backup_path.name}[/cyan]")
        
        # Create tar archive
        with tarfile.open(backup_path, "w:gz") as tar:
            # Add configuration files
            for item in UNBOUND_DIR.iterdir():
                if item.name != "backups":  # Don't backup the backup directory
                    tar.add(item, arcname=item.name)
        
        console.print(f"[green]✓[/green] Backup created: {backup_path}")
        return backup_path
    
    def list_backups(self) -> List[Path]:
        """List available backups."""
        backups = sorted(BACKUP_DIR.glob("backup_*.tar.gz"), reverse=True)
        return backups
    
    def restore_backup(self) -> None:
        """Interactive backup restoration with standard navigation."""
        console.clear()
        
        # Header
        console.print("┌" + "─" * 58 + "┐")
        console.print("│              [bold cyan]RESTORE BACKUP[/bold cyan]                           │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        backups = self.list_backups()
        
        if not backups:
            console.print("[yellow]No backups found[/yellow]")
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()
            return
        
        # Display available backups
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Filename")
        table.add_column("Date", justify="center")
        table.add_column("Size", justify="right")
        
        for i, backup in enumerate(backups[:10], 1):
            stats = backup.stat()
            date = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
            size = self._format_size(stats.st_size)
            table.add_row(str(i), backup.name, date, size)
        
        console.print(table)
        console.print()
        console.print("  ─" * 20)
        console.print("  [r] Return to menu")
        console.print("  [q] Quit")
        console.print()
        
        # Get selection
        valid_choices = ["r", "q"] + [str(i) for i in range(1, min(len(backups), 10) + 1)]
        choice = Prompt.ask("Select backup #", choices=valid_choices, default="r", show_choices=False)
        
        if choice == "q":
            return False
        if choice == "r":
            return
        
        selected_backup = backups[int(choice) - 1]
        
        if not prompt_yes_no(f"Restore from {selected_backup.name}?", default=False):
            console.print("[yellow]Restore cancelled[/yellow]")
            return
        
        # Create backup of current config before restoring
        console.print("[cyan]Creating backup of current configuration...[/cyan]")
        self.create_backup("before_restore")
        
        # Restore selected backup
        self.restore_specific_backup(selected_backup)
    
    def restore_specific_backup(self, backup_path: Path) -> bool:
        """Restore a specific backup."""
        console.print(f"[cyan]Restoring from {backup_path.name}...[/cyan]")
        
        try:
            # Extract to temporary directory first
            temp_dir = BACKUP_DIR / "temp_restore"
            temp_dir.mkdir(exist_ok=True)
            
            with tarfile.open(backup_path, "r:gz") as tar:
                self._safe_extract(tar, temp_dir)
            
            # Move files to Unbound directory
            for item in temp_dir.iterdir():
                target = UNBOUND_DIR / item.name
                
                # Remove existing file/directory
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                
                # Move restored file/directory
                shutil.move(str(item), str(target))
            
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
            # Fix permissions
            from .config_manager import ConfigManager
            config_manager = ConfigManager()
            config_manager.fix_permissions()
            
            console.print(f"[green]✓[/green] Backup restored successfully")
            
            # Restart Unbound
            from .utils import restart_service
            from .constants import UNBOUND_SERVICE
            console.print("[cyan]Restarting Unbound service...[/cyan]")
            if restart_service(UNBOUND_SERVICE):
                console.print("[green]✓[/green] Unbound service restarted")
            else:
                console.print("[yellow]⚠[/yellow] Please restart Unbound manually")
            
            return True
            
        except ValueError as e:
            console.print(f"[red]Security error: {e}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Restore failed: {e}[/red]")
            return False
    

    def _safe_extract(self, tar: tarfile.TarFile, dest: Path) -> None:
        """Safely extract tar archive, preventing path traversal attacks."""
        dest = dest.resolve()
        for member in tar.getmembers():
            target = (dest / member.name).resolve()
            if not str(target).startswith(str(dest)):
                raise ValueError(f"Blocked path traversal attempt in backup: {member.name}")
        tar.extractall(dest)

    def _format_size(self, size: int) -> str:
        """Format file size to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def cleanup_old_backups(self, keep: int = 10) -> None:
        """Remove old backups, keeping only the most recent ones."""
        console.print(f"[cyan]Cleaning up old backups (keeping {keep} most recent)...[/cyan]")
        
        backups = self.list_backups()
        
        if len(backups) <= keep:
            console.print("[green]No old backups to remove[/green]")
            return
        
        to_remove = backups[keep:]
        
        for backup in to_remove:
            console.print(f"[yellow]Removing: {backup.name}[/yellow]")
            backup.unlink()
        
        console.print(f"[green]✓[/green] Removed {len(to_remove)} old backup(s)")