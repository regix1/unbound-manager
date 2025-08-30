"""Interactive menu system for CLI navigation."""

import sys
import termios
import tty
from typing import List, Optional, Callable, Any
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


@dataclass
class MenuItem:
    """Represents a single menu item."""
    name: str
    action: Callable
    icon: str = "•"
    description: str = ""
    key: Optional[str] = None
    style: str = "cyan"


@dataclass
class MenuCategory:
    """Represents a category of menu items."""
    name: str
    items: List[MenuItem] = None
    icon: str = "📁"
    expanded: bool = False
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
    
    def add_item(self, item: MenuItem) -> None:
        """Add an item to this category."""
        self.items.append(item)


class InteractiveMenu:
    """Interactive arrow-key driven menu system."""
    
    def __init__(self):
        """Initialize the interactive menu."""
        self.items: List[Any] = []  # Can be MenuItem or MenuCategory
        self.current_index = 0
        self.in_category = False
        self.category_index = 0
        self.search_mode = False
        self.search_query = ""
    
    def add_item(self, item: MenuItem) -> None:
        """Add a top-level menu item."""
        self.items.append(item)
    
    def add_category(self, category: MenuCategory) -> None:
        """Add a category of items."""
        self.items.append(category)
    
    def get_key(self) -> str:
        """Get a single keypress from the user."""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            key = sys.stdin.read(1)
            
            # Handle special keys
            if key == '\x1b':  # ESC sequence
                key += sys.stdin.read(2)
                if key == '\x1b[A':  # Up arrow
                    return 'UP'
                elif key == '\x1b[B':  # Down arrow
                    return 'DOWN'
                elif key == '\x1b[C':  # Right arrow
                    return 'RIGHT'
                elif key == '\x1b[D':  # Left arrow
                    return 'LEFT'
                else:
                    return 'ESC'
            elif key == '\r' or key == '\n':
                return 'ENTER'
            elif key == '\x03':  # Ctrl+C
                raise KeyboardInterrupt
            else:
                return key
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def display_menu(self) -> None:
        """Display the current menu state."""
        console.clear()
        
        # Header
        console.print()
        console.print("[bold cyan]UNBOUND DNS MANAGER[/bold cyan] - Interactive Menu")
        console.print("━" * 50, style="dim")
        console.print("[dim]↑/↓: Navigate | Enter: Select | ESC: Back | q: Quit[/dim]")
        console.print()
        
        # Display items
        visible_items = self._get_visible_items()
        
        for idx, (item, is_category, parent_idx) in enumerate(visible_items):
            is_selected = idx == self.current_index
            
            if isinstance(item, MenuCategory):
                # Category display
                if is_selected:
                    prefix = "▶" if not item.expanded else "▼"
                    style = "bold yellow on blue"
                else:
                    prefix = "▶" if not item.expanded else "▼"
                    style = "bold cyan"
                
                text = f" {prefix} {item.icon} {item.name}"
                if is_selected:
                    console.print(f"[{style}]{text:<48}[/{style}]")
                else:
                    console.print(f"[{style}]{text}[/{style}]")
                    
            elif isinstance(item, MenuItem):
                # Item display
                indent = "    " if parent_idx is not None else ""
                
                if is_selected:
                    style = f"bold white on {item.style}" if item.style != "red" else "bold white on red"
                    marker = "→"
                else:
                    style = item.style
                    marker = " "
                
                # Build item text
                text = f"{indent}{marker} {item.icon} {item.name}"
                if item.key:
                    text += f" [{item.key}]"
                
                # Add description if selected
                if is_selected and item.description:
                    text = f"{text:<40} {item.description}"
                
                if is_selected:
                    console.print(f"[{style}]{text:<48}[/{style}]")
                else:
                    console.print(f"[{style}]{text}[/{style}]")
        
        # Show help hint at bottom
        console.print()
        console.print("━" * 50, style="dim")
        if self.current_index < len(visible_items):
            current_item = visible_items[self.current_index][0]
            if isinstance(current_item, MenuItem) and current_item.description:
                console.print(f"[dim]{current_item.description}[/dim]")
    
    def _get_visible_items(self) -> List[tuple]:
        """Get list of currently visible items with their metadata."""
        visible = []
        
        for idx, item in enumerate(self.items):
            if isinstance(item, MenuCategory):
                visible.append((item, True, None))
                if item.expanded:
                    for sub_item in item.items:
                        visible.append((sub_item, False, idx))
            else:
                visible.append((item, False, None))
        
        return visible
    
    def handle_selection(self) -> Any:
        """Handle the current selection."""
        visible_items = self._get_visible_items()
        
        if self.current_index >= len(visible_items):
            return None
        
        current_item, is_category, _ = visible_items[self.current_index]
        
        if isinstance(current_item, MenuCategory):
            # Toggle category expansion
            current_item.expanded = not current_item.expanded
            return None
        elif isinstance(current_item, MenuItem):
            # Execute action
            console.clear()
            try:
                result = current_item.action()
                return result
            except KeyboardInterrupt:
                console.print("\n[yellow]Operation cancelled[/yellow]")
                console.print("[dim]Press Enter to continue...[/dim]")
                input()
                return None
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
                console.print("[dim]Press Enter to continue...[/dim]")
                input()
                return None
    
    def navigate_up(self) -> None:
        """Navigate up in the menu."""
        if self.current_index > 0:
            self.current_index -= 1
    
    def navigate_down(self) -> None:
        """Navigate down in the menu."""
        visible_items = self._get_visible_items()
        if self.current_index < len(visible_items) - 1:
            self.current_index += 1
    
    def quick_select(self, number: int) -> Any:
        """Quick select an item by number."""
        visible_items = self._get_visible_items()
        
        # Filter only MenuItems (not categories)
        menu_items = [(idx, item) for idx, (item, _, _) in enumerate(visible_items) 
                      if isinstance(item, MenuItem)]
        
        if 0 < number <= len(menu_items):
            self.current_index = menu_items[number - 1][0]
            return self.handle_selection()
        
        return None
    
    def run(self) -> Any:
        """Run the interactive menu loop."""
        while True:
            self.display_menu()
            
            try:
                key = self.get_key()
                
                if key == 'UP' or key == 'k':
                    self.navigate_up()
                elif key == 'DOWN' or key == 'j':
                    self.navigate_down()
                elif key == 'ENTER' or key == ' ':
                    result = self.handle_selection()
                    if result is False:
                        return False
                elif key == 'ESC' or key == 'b':
                    # Collapse all categories and go to top
                    for item in self.items:
                        if isinstance(item, MenuCategory):
                            item.expanded = False
                    self.current_index = 0
                elif key == 'q' or key == 'Q':
                    return False
                elif key == 'h' or key == 'H' or key == '?':
                    # Find and execute help item
                    for item in self.items:
                        if isinstance(item, MenuItem) and item.key == 'h':
                            console.clear()
                            item.action()
                            break
                elif key.isdigit():
                    # Quick number selection
                    num = int(key)
                    result = self.quick_select(num)
                    if result is False:
                        return False
                elif key == '/':
                    # Search mode (future enhancement)
                    console.print("\n[yellow]Search not yet implemented[/yellow]")
                    console.print("[dim]Press Enter to continue...[/dim]")
                    input()
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'q' to quit or ESC to go back[/yellow]")
                console.print("[dim]Press Enter to continue...[/dim]")
                input()


class SimpleMenu:
    """Simple numbered menu for fallback or specific use cases."""
    
    def __init__(self, title: str = "Menu"):
        self.title = title
        self.items: List[tuple] = []  # (name, action, description)
    
    def add_item(self, name: str, action: Callable, description: str = "") -> None:
        """Add a menu item."""
        self.items.append((name, action, description))
    
    def display(self) -> None:
        """Display the menu."""
        console.print(Panel.fit(
            f"[bold cyan]{self.title}[/bold cyan]",
            border_style="cyan"
        ))
        
        for idx, (name, _, desc) in enumerate(self.items, 1):
            if desc:
                console.print(f"[green]{idx}[/green]. {name} - [dim]{desc}[/dim]")
            else:
                console.print(f"[green]{idx}[/green]. {name}")
        
        console.print("[green]0[/green]. Back")
    
    def run(self) -> Any:
        """Run the menu and get selection."""
        self.display()
        
        choices = ["0"] + [str(i) for i in range(1, len(self.items) + 1)]
        from rich.prompt import Prompt
        choice = Prompt.ask("Select option", choices=choices, default="0")
        
        if choice == "0":
            return None
        
        idx = int(choice) - 1
        if 0 <= idx < len(self.items):
            _, action, _ = self.items[idx]
            return action()
        
        return None