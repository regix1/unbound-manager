"""Interactive menu system for CLI navigation."""

from __future__ import annotations

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
    prefix: str = ""
    description: str = ""
    key: Optional[str] = None
    style: str = "cyan"


@dataclass
class MenuCategory:
    """Represents a category of menu items."""
    name: str
    items: List[MenuItem] = None
    prefix: str = ""
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
                next_chars = sys.stdin.read(2)
                if next_chars == '[A':  # Up arrow
                    return 'UP'
                elif next_chars == '[B':  # Down arrow
                    return 'DOWN'
                elif next_chars == '[C':  # Right arrow
                    return 'RIGHT'
                elif next_chars == '[D':  # Left arrow
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
        console.print("╔" + "═" * 78 + "╗")
        console.print("║ [bold cyan]UNBOUND DNS MANAGER[/bold cyan] - Interactive Menu" + " " * 35 + "║")
        console.print("╠" + "═" * 78 + "╣")
        console.print("║ [dim]↑↓ Navigate │ Enter: Select │ ESC: Back │ h: Help │ q: Exit[/dim]" + " " * 15 + "║")
        console.print("╚" + "═" * 78 + "╝")
        console.print()
        
        # Display items
        visible_items = self._get_visible_items()
        
        for idx, (item, is_category, parent_idx) in enumerate(visible_items):
            is_selected = idx == self.current_index
            
            if isinstance(item, MenuCategory):
                # Category display
                if is_selected:
                    arrow = "▼" if item.expanded else "►"
                    console.print(f"  [bold yellow on blue] {arrow} {item.prefix} {item.name:<50}[/bold yellow on blue]")
                else:
                    arrow = "▼" if item.expanded else "►"
                    console.print(f"  [bold cyan]{arrow} {item.prefix} {item.name}[/bold cyan]")
                    
            elif isinstance(item, MenuItem):
                # Item display
                indent = "    " if parent_idx is not None else "  "
                
                if is_selected:
                    # Build display text
                    display_text = f"{item.prefix} {item.name}" if item.prefix else item.name
                    if item.key:
                        display_text = f"{display_text}"
                    
                    # Show with selection highlight
                    if item.style == "red":
                        console.print(f"{indent}[bold white on red] → {display_text:<52}[/bold white on red]")
                    else:
                        console.print(f"{indent}[bold white on blue] → {display_text:<52}[/bold white on blue]")
                    
                    # Show description below if available
                    if item.description:
                        console.print(f"{indent}   [dim]{item.description}[/dim]")
                else:
                    display_text = f"{item.prefix} {item.name}" if item.prefix else item.name
                    console.print(f"{indent}[{item.style}]  {display_text}[/{item.style}]")
        
        # Footer with current item info
        console.print()
        console.print("─" * 80)
        
        if self.current_index < len(visible_items):
            current_item = visible_items[self.current_index][0]
            if isinstance(current_item, MenuCategory):
                console.print("[dim]Press Enter to expand/collapse category[/dim]")
            elif isinstance(current_item, MenuItem) and current_item.description and self.current_index < len(visible_items):
                # Description already shown inline, so just show quick key hint
                if current_item.key:
                    console.print(f"[dim]Quick key: {current_item.key}[/dim]")
    
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
    
    def collapse_all(self) -> None:
        """Collapse all categories."""
        for item in self.items:
            if isinstance(item, MenuCategory):
                item.expanded = False
    
    def quick_select_by_key(self, key: str) -> Any:
        """Quick select an item by its shortcut key."""
        visible_items = self._get_visible_items()
        
        for idx, (item, _, _) in enumerate(visible_items):
            if isinstance(item, MenuItem) and item.key == key.lower():
                self.current_index = idx
                return self.handle_selection()
        
        return None
    
    def quick_select_by_number(self, number: int) -> Any:
        """Quick select an item by number."""
        visible_items = self._get_visible_items()
        
        # Get numbered items (MenuItems only, not categories)
        numbered_items = []
        item_count = 0
        
        for idx, (item, _, parent_idx) in enumerate(visible_items):
            if isinstance(item, MenuItem):
                item_count += 1
                numbered_items.append((item_count, idx))
        
        # Find and select the item
        for num, idx in numbered_items:
            if num == number:
                self.current_index = idx
                return self.handle_selection()
        
        return None
    
    def run(self) -> Any:
        """Run the interactive menu loop."""
        while True:
            self.display_menu()
            
            try:
                key = self.get_key()
                
                # Navigation
                if key == 'UP' or key == 'k':
                    self.navigate_up()
                elif key == 'DOWN' or key == 'j':
                    self.navigate_down()
                elif key == 'ENTER' or key == ' ':
                    result = self.handle_selection()
                    if result is False:
                        return False
                elif key == 'ESC' or key == 'b':
                    # Go back: collapse categories and return to top
                    self.collapse_all()
                    self.current_index = 0
                
                # Quick keys
                elif key == 'q' or key == 'Q':
                    return False
                elif key == 'h' or key == 'H' or key == '?':
                    # Find and execute help
                    result = self.quick_select_by_key('h')
                    if result is False:
                        return False
                
                # Letter shortcuts
                elif key.lower() in 'stlcdma':
                    result = self.quick_select_by_key(key.lower())
                    if result is False:
                        return False
                
                # Number selection
                elif key.isdigit() and key != '0':
                    num = int(key)
                    result = self.quick_select_by_number(num)
                    if result is False:
                        return False
                    
            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully
                console.print("\n\n[yellow]Use 'q' to quit or ESC to go back[/yellow]")
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
        console.print("┌" + "─" * 58 + "┐")
        console.print(f"│  [bold cyan]{self.title:^54}[/bold cyan]  │")
        console.print("└" + "─" * 58 + "┘")
        console.print()
        
        for idx, (name, _, desc) in enumerate(self.items, 1):
            if desc:
                console.print(f"  [{idx}] {name}")
                console.print(f"      [dim]{desc}[/dim]")
            else:
                console.print(f"  [{idx}] {name}")
        
        console.print("  [0] Back")
        console.print()
    
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