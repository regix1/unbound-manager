"""Configuration management for Unbound with editing capabilities."""

from __future__ import annotations

import os
import shutil
import tempfile
import subprocess
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
from jinja2 import Template, Environment, FileSystemLoader, ChoiceLoader
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .constants import UNBOUND_DIR, UNBOUND_CONF, UNBOUND_CONF_D, DEFAULT_CONFIG
from .utils import set_file_permissions, ensure_directory, prompt_yes_no, get_server_ip
from .menu_system import SubMenu, create_submenu

console = Console()


@lru_cache(maxsize=1)
def _get_template_env() -> Environment:
    """Get cached Jinja2 template environment."""
    import glob
    import site
    
    # Setup Jinja2 environment with multiple possible paths
    possible_template_dirs = [
        Path(__file__).parent.parent / "data" / "templates",
        Path(__file__).parent.parent / "data" / "systemd",
        Path(__file__).parent.parent / "templates",
        Path.home() / "unbound-manager" / "data" / "templates",
        Path.home() / "unbound-manager" / "data" / "systemd",
        Path.home() / "unbound-manager" / "templates",
    ]
    
    # Dynamically find Python site-packages directories
    for base_path in ["/usr/local/lib", "/usr/lib"]:
        python_dirs = glob.glob(f"{base_path}/python3.*")
        for python_dir in python_dirs:
            possible_template_dirs.extend([
                Path(python_dir) / "dist-packages" / "data" / "templates",
                Path(python_dir) / "dist-packages" / "data" / "systemd",
                Path(python_dir) / "site-packages" / "data" / "templates",
                Path(python_dir) / "site-packages" / "data" / "systemd",
            ])
    
    # Also check system site-packages
    for site_dir in site.getsitepackages():
        possible_template_dirs.extend([
            Path(site_dir) / "data" / "templates",
            Path(site_dir) / "data" / "systemd",
        ])
    
    # Collect all existing directories
    loaders = []
    for path in possible_template_dirs:
        if path.exists():
            loaders.append(FileSystemLoader(str(path)))
    
    # Try package resources as fallback
    if not loaders:
        try:
            import pkg_resources
            for subdir in ["../data/templates", "../data/systemd", "../templates"]:
                if pkg_resources.resource_exists("unbound_manager", subdir):
                    resource_path = Path(pkg_resources.resource_filename("unbound_manager", subdir))
                    if resource_path.exists():
                        loaders.append(FileSystemLoader(str(resource_path)))
        except Exception:
            pass
    
    if not loaders:
        raise FileNotFoundError(
            f"Template directory not found. Searched {len(possible_template_dirs)} locations.\n"
            "Checked paths include:\n" + 
            "\n".join(str(p) for p in possible_template_dirs[:10]) +
            "\n... and more"
        )
    
    return Environment(
        loader=ChoiceLoader(loaders),
        trim_blocks=True,
        lstrip_blocks=True,
    )


class ConfigManager:
    """Manage Unbound configuration files with editing capabilities."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        # Use cached template environment
        self.env = _get_template_env()
        
        # Define editable configuration parameters
        self.editable_params = {
            "server.conf": {
                "interface": "Network interface IP (e.g., 192.168.1.1)",
                "port": "DNS port (default: 53)",
                "num-threads": "Number of threads (based on CPU cores)",
                "msg-cache-size": "Message cache size (e.g., 64m, 256m)",
                "rrset-cache-size": "RRset cache size (e.g., 128m, 512m)",
                "verbosity": "Log verbosity (0-5, default: 1)",
                "do-ip4": "Enable IPv4 (yes/no)",
                "do-ip6": "Enable IPv6 (yes/no)",
                "prefetch": "Enable prefetching (yes/no)",
                "serve-expired": "Serve expired records (yes/no)",
            },
            "dnssec.conf": {
                "val-permissive-mode": "DNSSEC permissive mode (yes/no)",
                "val-log-level": "DNSSEC validation log level (0-2)",
                "trust-anchor-signaling": "Trust anchor signaling (yes/no)",
                "harden-dnssec-stripped": "Harden against DNSSEC stripping (yes/no)",
            },
            "redis.conf": {
                "redis-server-path": "Redis socket path",
                "redis-timeout": "Redis timeout in milliseconds",
                "redis-expire-records": "Let Redis expire records (yes/no)",
            }
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load current configuration or defaults."""
        config_file = UNBOUND_DIR / "config.yaml"
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    return config if config else DEFAULT_CONFIG.copy()
            except yaml.YAMLError as e:
                console.print(f"[red]Invalid YAML in config.yaml: {e}[/red]")
                console.print("[yellow]Using default configuration[/yellow]")
                return DEFAULT_CONFIG.copy()
        
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
    
    def edit_configuration_interactive(self, file_name: str) -> None:
        """Interactive configuration editor using standardized submenu."""
        file_path = UNBOUND_CONF_D / file_name
        
        if not file_path.exists():
            console.print(f"[red]Configuration file {file_name} does not exist[/red]")
            return
        
        result = create_submenu(f"Edit {file_name}", [
            ("Quick Edit", lambda: self.quick_edit_config(file_name)),
            ("Open in Nano", lambda: self.open_in_editor(file_path, "nano")),
            ("Open in Vim", lambda: self.open_in_editor(file_path, "vim")),
            ("View Only", lambda: self.view_configuration_file(file_path)),
        ])
        
        if result == SubMenu.QUIT:
            return False
    
    def quick_edit_config(self, file_name: str) -> None:
        """Quick edit common configuration parameters."""
        file_path = UNBOUND_CONF_D / file_name
        
        if file_name not in self.editable_params:
            console.print(f"[yellow]Quick edit not available for {file_name}[/yellow]")
            self.open_in_editor(file_path, "nano")
            return
        
        # Read current configuration
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Parse current values
        current_values = {}
        for param in self.editable_params[file_name]:
            import re
            # Look for the parameter in the config
            pattern = rf'^\s*{re.escape(param)}:\s*(.+)$'
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                current_values[param] = match.group(1).strip().strip('"')
            else:
                current_values[param] = "not set"
        
        # Display current values
        console.print(Panel.fit(
            f"[bold cyan]Current Configuration - {file_name}[/bold cyan]",
            border_style="cyan"
        ))
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Parameter", style="cyan", width=25)
        table.add_column("Current Value", style="yellow")
        table.add_column("Description", style="dim")
        
        for param, desc in self.editable_params[file_name].items():
            table.add_row(param, current_values.get(param, "not set"), desc)
        
        console.print(table)
        console.print()
        
        # Edit parameters
        changes = {}
        console.print("[cyan]Enter new values (press Enter to keep current):[/cyan]\n")
        
        for param, desc in self.editable_params[file_name].items():
            current = current_values.get(param, "not set")
            
            # Show current value and description
            console.print(f"[bold]{param}[/bold]: {desc}")
            console.print(f"Current: [yellow]{current}[/yellow]")
            
            # Get new value
            if param in ["port", "num-threads", "verbosity", "val-log-level"]:
                # Numeric values
                try:
                    if current != "not set":
                        new_value = Prompt.ask("New value", default=current)
                    else:
                        new_value = Prompt.ask("New value")
                    
                    if new_value and new_value != current:
                        changes[param] = new_value
                except Exception:
                    pass
            elif param in ["do-ip4", "do-ip6", "prefetch", "serve-expired", "val-permissive-mode", 
                         "trust-anchor-signaling", "harden-dnssec-stripped", "redis-expire-records"]:
                # Boolean values
                current_bool = current.lower() == "yes" if current != "not set" else False
                new_value = Confirm.ask(f"Enable {param}?", default=current_bool)
                new_str = "yes" if new_value else "no"
                if new_str != current:
                    changes[param] = new_str
            else:
                # String values
                if current != "not set":
                    new_value = Prompt.ask("New value", default=current)
                else:
                    new_value = Prompt.ask("New value", default="")
                
                if new_value and new_value != current:
                    changes[param] = new_value
            
            console.print()  # Add spacing
        
        # Apply changes if any
        if changes:
            console.print(Panel.fit(
                "[bold yellow]Proposed Changes:[/bold yellow]",
                border_style="yellow"
            ))
            
            for param, value in changes.items():
                console.print(f"  {param}: [green]{value}[/green]")
            
            if prompt_yes_no("\nApply these changes?", default=True):
                # Backup current config
                backup_path = file_path.with_suffix(f'.conf.backup.{int(time.time())}')
                shutil.copy2(file_path, backup_path)
                console.print(f"[green]✓[/green] Backup created: {backup_path.name}")
                
                # Apply changes
                new_content = content
                for param, value in changes.items():
                    import re
                    pattern = rf'^(\s*){re.escape(param)}:\s*.+$'
                    replacement = rf'\1{param}: {value}'
                    
                    if re.search(pattern, new_content, re.MULTILINE):
                        new_content = re.sub(pattern, replacement, new_content, flags=re.MULTILINE)
                    else:
                        # Add parameter if it doesn't exist
                        new_content += f"\n    {param}: {value}"
                
                # Write new configuration
                with open(file_path, 'w') as f:
                    f.write(new_content)
                
                set_file_permissions(file_path)
                console.print("[green]✓[/green] Configuration updated successfully")
                
                # Validate configuration
                self.validate_configuration()
            else:
                console.print("[yellow]Changes cancelled[/yellow]")
        else:
            console.print("[yellow]No changes made[/yellow]")
    
    def open_in_editor(self, file_path: Path, editor: str = "nano") -> None:
        """Open configuration file in external editor."""
        # Create backup before editing
        backup_path = file_path.with_suffix(f'.conf.backup.{int(time.time())}')
        shutil.copy2(file_path, backup_path)
        console.print(f"[green]✓[/green] Backup created: {backup_path.name}")
        
        # Check if editor is available
        editor_check = subprocess.run(["which", editor], capture_output=True, text=True)
        if editor_check.returncode != 0:
            console.print(f"[yellow]{editor} not found, trying nano...[/yellow]")
            editor = "nano"
        
        console.print(f"[cyan]Opening {file_path.name} in {editor}...[/cyan]")
        console.print("[dim]Press Ctrl+X to exit nano, or :wq to exit vim[/dim]\n")
        
        # Open editor
        try:
            subprocess.run([editor, str(file_path)])
            console.print("\n[green]✓[/green] Editor closed")
            
            # Validate configuration after editing
            if prompt_yes_no("Validate configuration now?", default=True):
                self.validate_configuration()
        except Exception as e:
            console.print(f"[red]Error opening editor: {e}[/red]")
    
    def view_configuration_file(self, file_path: Path) -> None:
        """View configuration file with syntax highlighting."""
        with open(file_path, 'r') as f:
            content = f.read()
        
        syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"[bold cyan]{file_path.name}[/bold cyan]", border_style="cyan"))
    
    def edit_access_control(self) -> None:
        """Edit access control rules using standardized submenu."""
        server_conf = UNBOUND_CONF_D / "server.conf"
        
        # Read current access control rules
        current_rules = []
        if server_conf.exists():
            with open(server_conf, 'r') as f:
                for line in f:
                    if 'access-control:' in line:
                        parts = line.strip().split('access-control:')[1].strip().split()
                        if len(parts) >= 2:
                            current_rules.append((parts[0], parts[1]))
        
        # Display current rules
        console.clear()
        console.print("┌" + "─" * 58 + "┐")
        console.print("│           [bold cyan]ACCESS CONTROL RULES[/bold cyan]                        │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        if current_rules:
            table = Table(show_header=True, header_style="bold magenta", box=None)
            table.add_column("#", style="cyan", width=5)
            table.add_column("Network", style="yellow")
            table.add_column("Action", style="green")
            
            for i, (network, action) in enumerate(current_rules, 1):
                table.add_row(str(i), network, action)
            
            console.print(table)
        else:
            console.print("[yellow]No rules configured[/yellow]")
        
        console.print()
        
        def add_rule():
            network = Prompt.ask("Network (e.g., 192.168.1.0/24)")
            action = Prompt.ask("Action", choices=["allow", "deny", "refuse"], default="allow")
            current_rules.append((network, action))
            self._update_access_control(current_rules)
        
        def remove_rule():
            if not current_rules:
                console.print("[yellow]No rules to remove[/yellow]")
                return
            rule_num = IntPrompt.ask(
                "Rule # to remove",
                choices=[str(i) for i in range(1, len(current_rules) + 1)]
            )
            del current_rules[rule_num - 1]
            self._update_access_control(current_rules)
        
        def reset_rules():
            default_rules = [
                ("127.0.0.0/8", "allow"),
                ("10.0.0.0/8", "allow"),
                ("172.16.0.0/12", "allow"),
                ("192.168.0.0/16", "allow"),
            ]
            self._update_access_control(default_rules)
        
        # Show options after the table
        console.print("  [1] Add Rule")
        console.print("  [2] Remove Rule")
        console.print("  [3] Reset Defaults")
        console.print()
        console.print("  ─" * 20)
        console.print("  [r] Return to menu")
        console.print("  [q] Quit")
        console.print()
        
        choice = Prompt.ask("Select", choices=["1", "2", "3", "r", "q"], default="r", show_choices=False)
        
        if choice == "q":
            return False
        elif choice == "1":
            add_rule()
        elif choice == "2":
            remove_rule()
        elif choice == "3":
            reset_rules()
    
    def _update_access_control(self, rules: List[tuple]) -> None:
        """Update access control rules in configuration."""
        server_conf = UNBOUND_CONF_D / "server.conf"
        
        if not server_conf.exists():
            console.print("[red]Server configuration not found[/red]")
            return
        
        # Read current config
        with open(server_conf, 'r') as f:
            lines = f.readlines()
        
        # Remove old access-control lines
        new_lines = []
        skip_next = False
        for line in lines:
            if 'access-control:' not in line and not skip_next:
                new_lines.append(line)
            skip_next = False
        
        # Find where to insert new rules (after "# Access Control" comment)
        insert_index = -1
        for i, line in enumerate(new_lines):
            if '# Access Control' in line:
                insert_index = i + 1
                break
        
        if insert_index == -1:
            # Add at the end of server section
            for i, line in enumerate(new_lines):
                if line.strip() == '' and i > 0:
                    insert_index = i
                    new_lines.insert(insert_index, "    # Access Control\n")
                    insert_index += 1
                    break
        
        # Insert new rules
        for network, action in rules:
            new_lines.insert(insert_index, f"    access-control: {network} {action}\n")
            insert_index += 1
        
        # Write back
        with open(server_conf, 'w') as f:
            f.writelines(new_lines)
        
        console.print("[green]✓[/green] Access control rules updated")
        self.validate_configuration()
    
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
    
    def manage_configuration(self) -> None:
        """Interactive configuration management using standardized submenu."""
        
        result = create_submenu("Configuration", [
            ("View Config", self.view_configuration),
            ("Edit Server", lambda: self.edit_configuration_interactive("server.conf")),
            ("Edit DNSSEC", lambda: self.edit_configuration_interactive("dnssec.conf")),
            ("Edit Redis", lambda: self.edit_configuration_interactive("redis.conf")),
            ("Access Control", self.edit_access_control),
            ("Validate", self.validate_configuration),
            ("Reset Defaults", self.reset_to_defaults),
        ])
        
        if result == SubMenu.QUIT:
            return False
    
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
        backup_manager.create_backup("before_reset")
        
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

    
    def select_dns_upstream(self) -> dict:
        """Interactive DNS upstream provider selection with standard navigation."""
        from .constants import DNS_PROVIDERS, DNS_PROVIDER_ORDER
        
        console.clear()
        console.print("┌" + "─" * 58 + "┐")
        console.print("│           [bold cyan]SELECT DNS PROVIDER[/bold cyan]                         │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        console.print("[dim]Encrypted (DoT) = Protected from eavesdropping[/dim]")
        console.print("[dim]Unencrypted = Faster but visible to ISP[/dim]")
        console.print()
        
        # Display options in a table
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Provider", width=25)
        table.add_column("Security", width=12)
        
        for i, provider_key in enumerate(DNS_PROVIDER_ORDER, 1):
            provider = DNS_PROVIDERS[provider_key]
            security = "[green]Encrypted[/green]" if provider["encrypted"] else "[yellow]Unencrypted[/yellow]"
            if provider_key == "none":
                security = "[blue]Direct[/blue]"
            table.add_row(str(i), provider["name"], security)
        
        console.print(table)
        console.print()
        console.print("  ─" * 20)
        console.print("  [r] Return to menu")
        console.print("  [q] Quit")
        console.print()
        
        # Get selection
        valid_choices = ["r", "q"] + [str(i) for i in range(1, len(DNS_PROVIDER_ORDER) + 1)]
        choice = Prompt.ask("Select provider", choices=valid_choices, default="r", show_choices=False)
        
        if choice == "q":
            return SubMenu.QUIT
        if choice == "r":
            return SubMenu.RETURN
        
        selected_key = DNS_PROVIDER_ORDER[int(choice) - 1]
        selected_provider = DNS_PROVIDERS[selected_key].copy()
        selected_provider["key"] = selected_key
        
        # Handle custom unencrypted option
        if selected_key == "custom_unencrypted":
            selected_provider = self._configure_custom_dns()
        
        console.print(f"\n[green]✓[/green] Selected: [bold]{selected_provider['name']}[/bold]")
        
        if selected_provider.get("encrypted"):
            console.print("[green]  DNS queries will be encrypted (DNS-over-TLS)[/green]")
        elif selected_key == "none":
            console.print("[blue]  Unbound will query root servers directly (most private)[/blue]")
        else:
            console.print("[yellow]  DNS queries will NOT be encrypted[/yellow]")
        
        return selected_provider
    
    def _configure_custom_dns(self) -> dict:
        """Configure custom DNS servers."""
        console.print("\n[cyan]Configure Custom DNS Servers[/cyan]")
        console.print("[dim]Enter IP addresses of your DNS servers[/dim]\n")
        
        servers = []
        
        primary = Prompt.ask("Primary DNS server IP", default="8.8.8.8")
        servers.append({"ip": primary, "port": 53, "hostname": None})
        
        secondary = Prompt.ask("Secondary DNS server IP (optional)", default="")
        if secondary:
            servers.append({"ip": secondary, "port": 53, "hostname": None})
        
        return {
            "name": "Custom DNS",
            "description": f"Custom servers: {primary}" + (f", {secondary}" if secondary else ""),
            "encrypted": False,
            "servers": servers,
            "key": "custom_unencrypted",
        }
    
    def create_forwarding_config(self, provider: dict) -> None:
        """Create DNS forwarding configuration based on selected provider."""
        console.print("[cyan]Creating DNS forwarding configuration...[/cyan]")
        
        forward_conf = UNBOUND_CONF_D / "forward.conf"
        
        # If no forwarding (full recursion), remove forward config if exists
        if provider.get("key") == "none" or not provider.get("servers"):
            if forward_conf.exists():
                forward_conf.unlink()
                console.print("[green]✓[/green] Configured for full recursion (no forwarding)")
            else:
                console.print("[green]✓[/green] Using full recursion (no forwarding)")
            return
        
        # Build forwarding configuration
        is_encrypted = provider.get("encrypted", False)
        servers = provider.get("servers", [])
        
        lines = [
            "# DNS Forwarding Configuration",
            f"# Provider: {provider.get('name', 'Custom')}",
            f"# Encrypted: {'Yes (DNS-over-TLS)' if is_encrypted else 'No'}",
            "#",
            "# Generated by Unbound Manager",
            "",
            "forward-zone:",
            '    name: "."',
        ]
        
        if is_encrypted:
            lines.append("    forward-tls-upstream: yes")
        
        # Add servers
        for server in servers:
            ip = server.get("ip", "")
            port = server.get("port", 853 if is_encrypted else 53)
            hostname = server.get("hostname")
            is_ipv6 = server.get("ipv6", False)
            
            # Skip IPv6 by default (can be enabled later)
            if is_ipv6:
                continue
            
            if is_encrypted and hostname:
                lines.append(f"    forward-addr: {ip}@{port}#{hostname}")
            else:
                lines.append(f"    forward-addr: {ip}@{port}" if port != 53 else f"    forward-addr: {ip}")
        
        # Write configuration
        content = "\n".join(lines) + "\n"
        
        with open(forward_conf, 'w') as f:
            f.write(content)
        
        set_file_permissions(forward_conf)
        console.print(f"[green]✓[/green] Forwarding configuration created: {forward_conf.name}")
    
    def show_current_dns_config(self) -> None:
        """Display current DNS forwarding configuration."""
        forward_conf = UNBOUND_CONF_D / "forward.conf"
        
        console.print(Panel.fit(
            "[bold cyan]Current DNS Configuration[/bold cyan]",
            border_style="cyan"
        ))
        
        if not forward_conf.exists():
            console.print("[blue]Mode:[/blue] Full Recursion (no forwarding)")
            console.print("[dim]Unbound queries root servers directly[/dim]")
            return
        
        with open(forward_conf, 'r') as f:
            content = f.read()
        
        # Parse and display
        is_encrypted = "forward-tls-upstream: yes" in content
        
        console.print(f"[blue]Mode:[/blue] {'Encrypted Forwarding (DoT)' if is_encrypted else 'Unencrypted Forwarding'}")
        
        # Extract provider name from comment
        for line in content.split('\n'):
            if line.startswith('# Provider:'):
                provider_name = line.replace('# Provider:', '').strip()
                console.print(f"[blue]Provider:[/blue] {provider_name}")
                break
        
        # Extract servers
        console.print("[blue]Upstream Servers:[/blue]")
        for line in content.split('\n'):
            if 'forward-addr:' in line:
                addr = line.split('forward-addr:')[1].strip()
                console.print(f"  • {addr}")
