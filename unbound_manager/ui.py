"""Shared UI components for consistent display across the application."""

from rich.console import Console
from rich.prompt import Prompt

console = Console()

# Box drawing constants
BOX_WIDTH = 58


def print_header(title: str, clear: bool = True) -> None:
    """Print a standardized header box.
    
    Args:
        title: Title text (will be centered and uppercased)
        clear: Whether to clear screen first (default True)
    """
    if clear:
        console.clear()
    
    title_centered = title.upper().center(BOX_WIDTH - 4)
    console.print("┌" + "─" * BOX_WIDTH + "┐")
    console.print(f"│  [bold cyan]{title_centered}[/bold cyan]  │")
    console.print("└" + "─" * BOX_WIDTH + "┘")
    console.print()


def print_separator() -> None:
    """Print a horizontal separator line."""
    console.print("  ─" * 20)


def print_nav_options() -> None:
    """Print standard navigation options for submenus."""
    print_separator()
    console.print("  [r] Return to menu")
    console.print("  [q] Quit")
    console.print()


def pause() -> None:
    """Pause and wait for Enter key."""
    console.print("\n[dim]Press Enter to continue...[/dim]")
    input()


def get_choice(prompt_text: str, valid_choices: list, default: str = "r") -> str:
    """Get user choice with standard formatting.
    
    Args:
        prompt_text: Text to show in prompt
        valid_choices: List of valid choice strings
        default: Default choice (default "r" for return)
    
    Returns:
        User's choice as string
    """
    return Prompt.ask(prompt_text, choices=valid_choices, default=default, show_choices=False)


def print_status(service_name: str, is_running: bool) -> str:
    """Return formatted status string for a service.
    
    Args:
        service_name: Name of the service
        is_running: Whether service is running
    
    Returns:
        Formatted status string
    """
    if is_running:
        return f"{service_name}: [green]● Running[/green]"
    return f"{service_name}: [red]○ Stopped[/red]"


def print_success(message: str) -> None:
    """Print a success message with checkmark."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[cyan]{message}[/cyan]")
