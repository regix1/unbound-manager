"""Redis integration management for Unbound."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional
from rich.panel import Panel
from rich.table import Table

from .constants import REDIS_SOCKET, REDIS_CONF, UNBOUND_CONF_D, REDIS_SERVICE
from .utils import (
    run_command, check_service_status, restart_service,
    check_package_installed, install_packages, set_file_permissions
)
from .ui import print_success, print_error, console


class RedisManager:
    """Manage Redis integration with Unbound."""
    
    def configure_redis(self) -> bool:
        """Configure Redis for Unbound integration."""
        console.print(Panel.fit(
            "[bold cyan]Redis Configuration[/bold cyan]\n\n"
            "Configuring Redis for caching integration with Unbound.",
            border_style="cyan"
        ))
        
        # Install Redis if needed
        if not check_package_installed("redis-server"):
            console.print("[yellow]Redis is not installed. Installing...[/yellow]")
            if not install_packages(["redis-server"]):
                console.print("[red]Failed to install Redis[/red]")
                return False
        
        # Backup original configuration
        if REDIS_CONF.exists() and not Path(f"{REDIS_CONF}.bak").exists():
            console.print("[cyan]Backing up Redis configuration...[/cyan]")
            run_command(["cp", str(REDIS_CONF), f"{REDIS_CONF}.bak"])
        
        # Configure Redis for Unix socket
        console.print("[cyan]Configuring Redis for Unix socket...[/cyan]")
        
        redis_config = []
        with open(REDIS_CONF, 'r') as f:
            for line in f:
                # Disable TCP port
                if line.startswith("port "):
                    redis_config.append("port 0\n")
                # Skip existing socket config to avoid duplicates
                elif line.startswith("unixsocket") or line.startswith("unixsocketperm"):
                    continue
                else:
                    redis_config.append(line)
        
        # Add Unix socket configuration
        redis_config.extend([
            "\n# Unix socket configuration for Unbound\n",
            "unixsocket /var/run/redis/redis.sock\n",
            "unixsocketperm 770\n",
        ])
        
        # Write updated configuration
        with open(REDIS_CONF, 'w') as f:
            f.writelines(redis_config)
        
        # Create Redis run directory
        redis_run_dir = Path("/var/run/redis")
        if not redis_run_dir.exists():
            redis_run_dir.mkdir(parents=True)
            run_command(["chown", "redis:redis", str(redis_run_dir)])
            run_command(["chmod", "775", str(redis_run_dir)])
        
        # Add unbound user to redis group
        console.print("[cyan]Adding unbound user to redis group...[/cyan]")
        run_command(["usermod", "-a", "-G", "redis", "unbound"])
        
        # Create Unbound Redis configuration
        self._create_unbound_redis_config()
        
        # Restart Redis
        console.print("[cyan]Restarting Redis service...[/cyan]")
        if restart_service(REDIS_SERVICE):
            print_success("Redis service restarted")
        else:
            console.print("[red]Failed to restart Redis[/red]")
            return False
        
        # Test Redis connection
        if self.test_redis_connection():
            print_success("Redis configured successfully")
            return True
        else:
            console.print("[red]Redis configuration failed[/red]")
            return False
    
    def _create_unbound_redis_config(self) -> None:
        """Create Unbound Redis configuration file."""
        from .config_manager import ConfigManager
        config_manager = ConfigManager()
        
        config_manager.render_template(
            "redis.conf.j2",
            UNBOUND_CONF_D / "redis.conf",
            {}
        )
    
    def test_redis_connection(self) -> bool:
        """Test Redis connection via Unix socket."""
        console.print("[cyan]Testing Redis connection...[/cyan]")
        
        try:
            result = run_command(
                ["redis-cli", "-s", str(REDIS_SOCKET), "ping"],
                check=False
            )
            
            if result.returncode == 0 and "PONG" in result.stdout:
                print_success("Redis connection successful")
                return True
            else:
                print_error("Redis connection failed")
                return False
        except Exception as e:
            console.print(f"[red]Error testing Redis: {e}[/red]")
            return False
    
    def show_redis_stats(self) -> None:
        """Show Redis statistics."""
        console.print(Panel.fit(
            "[bold cyan]Redis Cache Statistics[/bold cyan]",
            border_style="cyan"
        ))
        
        if not check_service_status(REDIS_SERVICE):
            console.print("[red]Redis is not running[/red]")
            return
        
        try:
            # Get Redis info
            result = run_command(
                ["redis-cli", "-s", str(REDIS_SOCKET), "info"],
                check=False
            )
            
            if result.returncode != 0:
                console.print("[red]Could not get Redis statistics[/red]")
                return
            
            # Parse and display relevant stats
            stats = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    stats[key] = value.strip()
            
            # Create stats table
            table = Table(title="Redis Statistics", title_style="bold cyan")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")
            
            # Add relevant metrics
            metrics = [
                ("Redis Version", stats.get("redis_version", "N/A")),
                ("Uptime (days)", str(int(stats.get("uptime_in_seconds", 0)) // 86400)),
                ("Connected Clients", stats.get("connected_clients", "N/A")),
                ("Used Memory", stats.get("used_memory_human", "N/A")),
                ("Peak Memory", stats.get("used_memory_peak_human", "N/A")),
                ("Total Keys", stats.get("db0", "").split("keys=")[1].split(",")[0] if "db0" in stats else "0"),
                ("Evicted Keys", stats.get("evicted_keys", "0")),
                ("Keyspace Hits", stats.get("keyspace_hits", "0")),
                ("Keyspace Misses", stats.get("keyspace_misses", "0")),
            ]
            
            for metric, value in metrics:
                table.add_row(metric, value)
            
            console.print(table)
            
            # Calculate hit rate
            hits = int(stats.get("keyspace_hits", 0))
            misses = int(stats.get("keyspace_misses", 0))
            if hits + misses > 0:
                hit_rate = (hits / (hits + misses)) * 100
                console.print(f"\n[cyan]Cache Hit Rate:[/cyan] [green]{hit_rate:.2f}%[/green]")
            
        except Exception as e:
            console.print(f"[red]Error getting Redis stats: {e}[/red]")
    
    def clear_redis_cache(self) -> None:
        """Clear Redis cache."""
        console.print("[yellow]Warning: This will clear all cached DNS records[/yellow]")
        
        try:
            result = run_command(
                ["redis-cli", "-s", str(REDIS_SOCKET), "flushall"],
                check=False
            )
            
            if result.returncode == 0:
                print_success("Redis cache cleared")
            else:
                console.print("[red]Failed to clear cache[/red]")
        except Exception as e:
            console.print(f"[red]Error clearing cache: {e}[/red]")
    
    def fix_redis_integration(self) -> None:
        """Fix common Redis integration issues."""
        console.print("[cyan]Fixing Redis integration...[/cyan]")
        
        # Ensure Redis is installed
        if not check_package_installed("redis-server"):
            install_packages(["redis-server"])
        
        # Fix socket permissions
        redis_run_dir = Path("/var/run/redis")
        if redis_run_dir.exists():
            run_command(["chown", "-R", "redis:redis", str(redis_run_dir)])
            run_command(["chmod", "775", str(redis_run_dir)])
        
        # Ensure unbound is in redis group
        run_command(["usermod", "-a", "-G", "redis", "unbound"])
        
        # Restart Redis
        restart_service(REDIS_SERVICE)
        
        # Test connection
        if self.test_redis_connection():
            print_success("Redis integration fixed")
        else:
            console.print("[red]Could not fix Redis integration[/red]")
            console.print("[yellow]Try running troubleshooting for more details[/yellow]")