"""Backup and restore functionality for Unbound."""

import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt

from .constants import UNBOUND_DIR, BACKUP_DIR
from .utils import ensure_directory, prompt_yes_no

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
        """Interactive backup restoration."""
        console.print(Panel.fit(
            "[bold cyan]Restore Configuration Backup[/bold cyan]",
            border_style="cyan"
        ))
        
        backups = self.list_backups()
        
        if not backups:
            console.print("[yellow]No backups found[/yellow]")
            return
        
        # Display available backups
        table = Table(title="Available Backups", title_style="bold cyan")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Filename")
        table.add_column("Date", justify="center")
        table.add_column("Size", justify="right")
        
        for i, backup in enumerate(backups[:10], 1):  # Show only last 10
            stats = backup.stat()
            date = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M")
            size = self._format_size(stats.st_size)
            table.add_row(str(i), backup.name, date, size)
        
        console.print(table)
        
        # Select backup
        choice = IntPrompt.ask(
            "Select backup to restore (0 to cancel)",
            choices=[str(i) for i in range(len(backups[:10]) + 1)]
        )
        
        if choice == 0:
            console.print("[yellow]Restore cancelled[/yellow]")
            return
        
        selected_backup = backups[choice - 1]
        
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
                tar.extractall(temp_dir)
            
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
            console.print("[cyan]Restarting Unbound service...[/cyan]")
            if restart_service("unbound"):
                console.print("[green]✓[/green] Unbound service restarted")
            else:
                console.print("[yellow]⚠[/yellow] Please restart Unbound manually")
            
            return True
            
        except Exception as e:
            console.print(f"[red]Restore failed: {e}[/red]")
            return False
    
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