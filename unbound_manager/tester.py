"""Testing suite for Unbound functionality."""

from __future__ import annotations

import time
import statistics
from typing import List, Tuple, Optional
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .constants import TEST_DOMAINS, UNBOUND_SERVICE
from .utils import run_command, check_service_status
from .ui import print_success, print_error, print_warning, print_info, console


class UnboundTester:
    """Test Unbound DNS functionality."""
    
    def verify_installation(self) -> bool:
        """Quick verification of Unbound installation."""
        print_info("Verifying Unbound installation...")
        
        # Check if unbound is installed
        try:
            result = run_command(["which", "unbound"], check=False)
            if result.returncode != 0:
                print_error("Unbound is not installed")
                return False
        except Exception:
            print_error("Unbound is not installed")
            return False
        
        # Check configuration
        try:
            result = run_command(["unbound-checkconf"], check=False)
            if result.returncode != 0:
                print_error("Configuration is invalid")
                return False
        except Exception:
            print_error("Could not validate configuration")
            return False
        
        # Check service
        if not check_service_status(UNBOUND_SERVICE):
            print_error("Unbound service is not running")
            return False
        
        # Test basic resolution
        try:
            result = run_command(
                ["dig", "@127.0.0.1", "+short", "example.com"],
                check=False,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                print_success("DNS resolution working")
                return True
            else:
                print_error("DNS resolution not working")
                return False
        except Exception:
            print_error("DNS resolution test failed")
            return False
    
    def test_dns_resolution(self) -> None:
        """Test various DNS record types."""
        console.print(Panel.fit(
            "[bold cyan]DNS Resolution Tests[/bold cyan]",
            border_style="cyan"
        ))
        
        tests = [
            ("A", TEST_DOMAINS["ipv4"], "IPv4 Address"),
            ("AAAA", TEST_DOMAINS["ipv6"], "IPv6 Address"),
            ("MX", TEST_DOMAINS["mx"], "Mail Exchange"),
            ("TXT", TEST_DOMAINS["txt"], "Text Record"),
            ("NS", "example.com", "Name Server"),
            ("SOA", "example.com", "Start of Authority"),
        ]
        
        table = Table(title="DNS Record Tests", title_style="bold cyan")
        table.add_column("Record Type", style="cyan")
        table.add_column("Domain")
        table.add_column("Status", justify="center")
        table.add_column("Response Time", justify="right")
        
        for record_type, domain, description in tests:
            start_time = time.time()
            
            try:
                result = run_command(
                    ["dig", "@127.0.0.1", "+short", record_type, domain],
                    check=False,
                    timeout=5
                )
                
                elapsed = (time.time() - start_time) * 1000  # Convert to ms
                
                if result.returncode == 0 and result.stdout.strip():
                    status = "[green]✓ Pass[/green]"
                else:
                    status = "[red]✗ Fail[/red]"
                
                table.add_row(
                    f"{record_type} ({description})",
                    domain,
                    status,
                    f"{elapsed:.2f} ms"
                )
                
            except Exception as e:
                table.add_row(
                    f"{record_type} ({description})",
                    domain,
                    "[red]✗ Error[/red]",
                    "N/A"
                )
        
        console.print(table)
    
    def test_dnssec(self) -> None:
        """Test DNSSEC validation."""
        console.print(Panel.fit(
            "[bold cyan]DNSSEC Validation Tests[/bold cyan]",
            border_style="cyan"
        ))
        
        # Test positive validation
        print_info("Testing DNSSEC-signed domain (iana.org)...")
        
        try:
            result = run_command(
                ["dig", "@127.0.0.1", "+dnssec", "+short", "iana.org"],
                check=False
            )
            
            if result.returncode == 0:
                # Check for AD flag in full output
                result_full = run_command(
                    ["dig", "@127.0.0.1", "+dnssec", "iana.org"],
                    check=False
                )
                
                if "flags:" in result_full.stdout and "ad" in result_full.stdout:
                    print_success("DNSSEC validation successful (AD flag present)")
                else:
                    print_warning("DNSSEC validation unclear (AD flag not detected)")
            else:
                print_error("DNSSEC query failed")
                
        except Exception as e:
            print_error(f"DNSSEC test error: {e}")
        
        # Test negative validation
        print_info("Testing DNSSEC-failed domain (dnssec-failed.org)...")
        
        try:
            result = run_command(
                ["dig", "@127.0.0.1", "+dnssec", "dnssec-failed.org"],
                check=False
            )
            
            if "SERVFAIL" in result.stdout:
                print_success("DNSSEC correctly rejected invalid signatures")
            else:
                print_error("DNSSEC did not reject invalid signatures")
                
        except Exception as e:
            print_error(f"DNSSEC test error: {e}")
    
    def test_performance(self, iterations: int = 100) -> None:
        """Test DNS query performance."""
        console.print(Panel.fit(
            f"[bold cyan]Performance Test ({iterations} queries)[/bold cyan]",
            border_style="cyan"
        ))
        
        domains = ["google.com", "cloudflare.com", "example.com", "github.com", "stackoverflow.com"]
        response_times = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(f"Running {iterations} queries...", total=iterations)
            
            for i in range(iterations):
                domain = domains[i % len(domains)]
                start_time = time.time()
                
                try:
                    result = run_command(
                        ["dig", "@127.0.0.1", "+short", domain],
                        check=False,
                        timeout=5
                    )
                    
                    if result.returncode == 0:
                        elapsed = (time.time() - start_time) * 1000  # ms
                        response_times.append(elapsed)
                
                except Exception:
                    pass
                
                progress.update(task, advance=1)
        
        if response_times:
            # Calculate statistics
            avg_time = statistics.mean(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            median_time = statistics.median(response_times)
            
            if len(response_times) > 1:
                stdev_time = statistics.stdev(response_times)
            else:
                stdev_time = 0
            
            # Display results
            table = Table(title="Performance Statistics", title_style="bold cyan")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")
            
            table.add_row("Queries Successful", f"{len(response_times)}/{iterations}")
            table.add_row("Average Response Time", f"{avg_time:.2f} ms")
            table.add_row("Minimum Response Time", f"{min_time:.2f} ms")
            table.add_row("Maximum Response Time", f"{max_time:.2f} ms")
            table.add_row("Median Response Time", f"{median_time:.2f} ms")
            table.add_row("Standard Deviation", f"{stdev_time:.2f} ms")
            
            console.print(table)
            
            # Performance rating
            if avg_time < 10:
                rating = "[green]Excellent[/green]"
            elif avg_time < 50:
                rating = "[green]Good[/green]"
            elif avg_time < 100:
                rating = "[yellow]Fair[/yellow]"
            else:
                rating = "[red]Poor[/red]"
            
            console.print(f"\n[cyan]Performance Rating:[/cyan] {rating}")
        else:
            console.print("[red]No successful queries completed[/red]")
    
    def test_cache(self) -> None:
        """Test caching functionality."""
        console.print(Panel.fit(
            "[bold cyan]Cache Performance Test[/bold cyan]",
            border_style="cyan"
        ))
        
        test_domain = "example.com"
        
        # Clear cache first (if Redis is configured)
        print_info("Clearing cache...")
        try:
            run_command(
                ["redis-cli", "-s", "/var/run/redis/redis.sock", "flushall"],
                check=False
            )
        except Exception:
            pass
        
        # First query (cache miss)
        print_info(f"First query to {test_domain} (cache miss)...")
        start_time = time.time()
        
        try:
            result = run_command(
                ["dig", "@127.0.0.1", "+short", test_domain],
                check=False
            )
            first_time = (time.time() - start_time) * 1000
            console.print(f"  Response time: {first_time:.2f} ms")
        except Exception as e:
            console.print(f"[red]First query failed: {e}[/red]")
            return
        
        # Second query (should be cached)
        print_info(f"Second query to {test_domain} (should be cached)...")
        start_time = time.time()
        
        try:
            result = run_command(
                ["dig", "@127.0.0.1", "+short", test_domain],
                check=False
            )
            second_time = (time.time() - start_time) * 1000
            console.print(f"  Response time: {second_time:.2f} ms")
        except Exception as e:
            console.print(f"[red]Second query failed: {e}[/red]")
            return
        
        # Compare times
        if second_time < first_time:
            improvement = ((first_time - second_time) / first_time) * 100
            print_success(f"Cache working! Second query {improvement:.1f}% faster")
        else:
            print_warning("Cache may not be working optimally")
    
    def run_all_tests(self) -> None:
        """Run all tests."""
        console.print(Panel.fit(
            "[bold cyan]Comprehensive Unbound Test Suite[/bold cyan]\n\n"
            "Running all tests to verify functionality...",
            border_style="cyan"
        ))
        
        # Service status
        console.print("\n[bold]1. Service Status[/bold]")
        if check_service_status(UNBOUND_SERVICE):
            print_success("Unbound service is running")
        else:
            print_error("Unbound service is not running")
            print_warning("Cannot continue with tests")
            return
        
        # DNS resolution
        console.print("\n[bold]2. DNS Resolution[/bold]")
        self.test_dns_resolution()
        
        # DNSSEC
        console.print("\n[bold]3. DNSSEC Validation[/bold]")
        self.test_dnssec()
        
        # Cache
        console.print("\n[bold]4. Cache Performance[/bold]")
        self.test_cache()
        
        # Performance
        console.print("\n[bold]5. Query Performance[/bold]")
        self.test_performance(50)  # Reduced for quicker testing
        
        console.print("\n" + "=" * 50)
        print_success("All tests completed")