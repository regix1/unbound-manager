"""Configuration management for Unbound."""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from jinja2 import Template, Environment, FileSystemLoader
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.syntax import Syntax

from .constants import UNBOUND_DIR, UNBOUND_CONF, UNBOUND_CONF_D, DEFAULT_CONFIG
from .utils import set_file_permissions, ensure_directory, prompt_yes_no, get_server_ip

console = Console()


class ConfigManager:
    """Manage Unbound configuration files."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    
    def load_config(self) -> Dict[str, Any]:
        """Load current configuration or defaults."""
        config_file = UNBOUND_DIR / "config.yaml"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                return yaml.safe_load(f) or DEFAULT_CONFIG.copy()
        
        return DEFAULT_CONFIG.copy()
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to YAML file."""
        config_file = UNBOUND_DIR / "config.yaml"
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        set_file_permissions(config_file)
    
    def render_template(self, template_name: str, output_path: Path, context: Dict[str, Any]) -> None:
        """Render a Jinja2 template to a file."""
        template = self.env.get_template(template_name)
        content = template.render(**context)
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(output_path, 'w') as f:
            f.write(content)
        
        # Set permissions
        set_file_permissions(output_path)
    
    def create_main_config(self) -> None:
        """Create main unbound.conf file."""
        console.print("[cyan]Creating main configuration file...[/cyan]")
        
        self.render_template(
            "unbound.conf.j2",
            UNBOUND_CONF,
            {"version": "2.0.0"}
        )
        
        console.print("[green]✓[/green] Main configuration created")
    
    def create_server_config(self, server_ip: str) -> None:
        """Create server configuration."""
        console.print("[cyan]Creating server configuration...[/cyan]")
        
        config = self.load_config()
        config['server_ip'] = server_ip
        
        self.render_template(
            "server.conf.j2",
            UNBOUND_CONF_D / "server.conf",
            config
        )
        
        self.save_config(config)
        console.print("[green]✓[/green] Server configuration created")
    
    def create_control_config(self) -> None:
        """Create remote control configuration."""
        console.print("[cyan]Creating control configuration...[/cyan]")
        
        self.render_template(
            "control.conf.j2",
            UNBOUND_CONF_D / "control.conf",
            {}
        )
        
        console.print("[green]✓[/green] Control configuration created")
    
    def create_dnssec_config(self) -> None:
        """Create DNSSEC configuration."""
        console.print("[cyan]Creating DNSSEC configuration...[/cyan]")
        
        self.render_template(
            "dnssec.conf.j2",
            UNBOUND_CONF_D / "dnssec.conf",
            {}
        )
        
        console.print("[green]✓[/green] DNSSEC configuration created")
    
    def create_redis_config(self) -> None:
        """Create Redis cachedb configuration."""
        console.print("[cyan]Creating Redis configuration...[/cyan]")
        
        self.render_template(
            "redis.conf.j2",
            UNBOUND_CONF_D / "redis.conf",
            {}
        )
        
        console.print("[green]✓[/green] Redis configuration created")
    
    def create_root_hints_config(self) -> None:
        """Create root hints configuration."""
        console.print("[cyan]Creating root hints configuration...[/cyan]")
        
        self.render_template(
            "root-hints.conf.j2",
            UNBOUND_CONF_D / "root-hints.conf",
            {}
        )
        
        console.print("[green]✓[/green] Root hints configuration created")
    
    def create_full_configuration(self, server_ip: str) -> None:
        """Create all configuration files."""
        ensure_directory(UNBOUND_CONF_D)
        
        self.create_main_config()
        self.create_server_config(server_ip)
        self.create_control_config()
        self.create_dnssec_config()
        self.create_redis_config()
        self.create_root_hints_config()
        
        console.print("[green]✓[/green] Full configuration created")
    
    def validate_configuration(self) -> bool:
        """Validate Unbound configuration."""
        from .utils import run_command
        
        console.print("[cyan]Validating configuration...[/cyan]")
        
        try:
            result = run_command(["unbound-checkconf"], check=False)
            if result.returncode == 0:
                console.print("[green]✓[/green] Configuration is valid")
                return True
            else:
                console.print("[red]✗[/red] Configuration is invalid")
                if result.stderr:
                    console.print(f"[red]{result.stderr}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]Could not validate configuration: {e}[/red]")
            return False
    
    def edit_configuration(self, file_name: str) -> None:
        """Edit a configuration file."""
        file_path = UNBOUND_CONF_D / file_name
        
        if not file_path.exists():
            console.print(f"[red]Configuration file {file_name} does not exist[/red]")
            return
        
        # Show current content
        with open(file_path, 'r') as f:
            content = f.read()
        
        syntax = Syntax(content, "ini", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"Current {file_name}", border_style="cyan"))
        
        # For now, just show the file
        # In a real implementation, you might want to use a text editor
        console.print("[yellow]Note: Direct editing not implemented in this version[/yellow]")
        console.print(f"[cyan]Edit manually: sudo nano {file_path}[/cyan]")
    
    def manage_configuration(self) -> None:
        """Interactive configuration management."""
        console.print(Panel.fit(
            "[bold cyan]Configuration Management[/bold cyan]",
            border_style="cyan"
        ))
        
        options = [
            "View current configuration",
            "Edit server configuration",
            "Edit DNSSEC configuration",
            "Edit Redis configuration",
            "Validate configuration",
            "Reset to defaults",
            "Back to main menu",
        ]
        
        for i, option in enumerate(options, 1):
            console.print(f"[green]{i}[/green]. {option}")
        
        choice = IntPrompt.ask(
            "Select option",
            choices=[str(i) for i in range(1, len(options) + 1)]
        )
        
        if choice == 1:
            self.view_configuration()
        elif choice == 2:
            self.edit_configuration("server.conf")
        elif choice == 3:
            self.edit_configuration("dnssec.conf")
        elif choice == 4:
            self.edit_configuration("redis.conf")
        elif choice == 5:
            self.validate_configuration()
        elif choice == 6:
            self.reset_to_defaults()
    
    def view_configuration(self) -> None:
        """View current configuration files."""
        console.print("[cyan]Current configuration files:[/cyan]\n")
        
        for conf_file in UNBOUND_CONF_D.glob("*.conf"):
            console.print(f"[green]→[/green] {conf_file.name}")
            
            with open(conf_file, 'r') as f:
                # Show first 10 lines
                lines = f.readlines()[:10]
                for line in lines:
                    console.print(f"  {line.rstrip()}")
                if len(lines) == 10:
                    console.print("  ...")
            console.print()
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        if not prompt_yes_no("Are you sure you want to reset to default configuration?", default=False):
            console.print("[yellow]Reset cancelled[/yellow]")
            return
        
        # Backup current configuration
        from .backup import BackupManager
        backup_manager = BackupManager()
        backup_manager.create_backup()
        
        # Get server IP
        server_ip = get_server_ip()
        
        # Recreate configuration
        self.create_full_configuration(server_ip)
        
        console.print("[green]✓[/green] Configuration reset to defaults")
    
    def fix_permissions(self) -> None:
        """Fix configuration file permissions."""
        console.print("[cyan]Fixing configuration permissions...[/cyan]")
        
        # Fix main config
        if UNBOUND_CONF.exists():
            set_file_permissions(UNBOUND_CONF)
        
        # Fix all config files
        for conf_file in UNBOUND_CONF_D.glob("*.conf"):
            set_file_permissions(conf_file)
        
        # Fix keys
        for key_file in UNBOUND_DIR.glob("*.key"):
            set_file_permissions(key_file, mode=0o640)
        
        for pem_file in UNBOUND_DIR.glob("*.pem"):
            set_file_permissions(pem_file, mode=0o640)
        
        console.print("[green]✓[/green] Permissions fixed")