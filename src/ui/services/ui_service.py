"""
UI Service for RecRadiko Keyboard Navigation

Provides business logic for keyboard navigation interface with highlight display.
Handles menu selection, navigation state, and visual feedback.

Based on DETAILED_DESIGN.md specifications:
- Keyboard navigation with arrow keys
- Circular selection support
- ANSI escape sequence for highlighting
- Visual feedback with → marker and reverse video
"""

import logging
from typing import List, Optional, Any
from src.ui.input.keyboard_handler import KeyboardHandler
from src.ui.performance_optimizer import optimize_performance, cache_result


class UIService:
    """
    UI Service for keyboard navigation interface
    
    Manages menu display, user input, and selection state for the
    keyboard navigation system.
    """
    
    def __init__(self):
        """Initialize UI service"""
        self.logger = logging.getLogger(__name__)
        self.keyboard_handler = KeyboardHandler()
        self.current_selection = 0
        self.menu_items: List[Any] = []
        
    def set_menu_items(self, items: List[Any]) -> None:
        """
        Set menu items for display and selection
        
        Args:
            items: List of menu items to display
        """
        self.menu_items = items
        self.current_selection = 0  # Reset selection to first item
        
    def move_selection_down(self) -> None:
        """Move selection down with circular navigation"""
        if not self.menu_items:
            return
            
        self.current_selection = (self.current_selection + 1) % len(self.menu_items)
        
    def move_selection_up(self) -> None:
        """Move selection up with circular navigation"""
        if not self.menu_items:
            return
            
        self.current_selection = (self.current_selection - 1) % len(self.menu_items)
        
    def get_current_item(self) -> Optional[Any]:
        """
        Get currently selected menu item
        
        Returns:
            Currently selected item or None if no items
        """
        if not self.menu_items or self.current_selection >= len(self.menu_items):
            return None
            
        return self.menu_items[self.current_selection]
        
    def display_menu_with_highlight(self) -> None:
        """Display menu with current selection highlighted"""
        if not self.menu_items:
            print("メニュー項目がありません")
            return
            
        for i, item in enumerate(self.menu_items):
            if i == self.current_selection:
                # Highlighted item with arrow and reverse video
                print(self.format_highlight_text(str(item)))
            else:
                # Normal item with spacing
                print(self.format_normal_text(str(item)))
                
    def clear_screen(self) -> None:
        """Clear terminal screen using ANSI escape sequences"""
        print('\033[2J\033[H', end='')  # Clear screen and move cursor to top
        
    @optimize_performance("ui_get_user_selection")
    def get_user_selection(self) -> Optional[Any]:
        """
        Get user selection using keyboard navigation
        
        Returns:
            Selected item or None if cancelled (Escape key)
        """
        if not self.menu_items:
            return None
            
        while True:
            self.clear_screen()
            self.display_menu_with_highlight()
            
            key = self.keyboard_handler.get_key()
            
            if key == 'UP':
                self.move_selection_up()
            elif key == 'DOWN':
                self.move_selection_down()
            elif key == 'ENTER':
                return self.get_current_item()
            elif key == 'ESCAPE':
                return None
            elif key in ('q', 'Q'):  # Quit shortcut
                return None
            # Ignore other keys
            
    def format_highlight_text(self, text: str) -> str:
        """
        Format text with highlight (arrow + reverse video)
        
        Args:
            text: Text to format
            
        Returns:
            Formatted text with ANSI highlighting
        """
        return f"→ \033[7m{text}\033[0m"  # Arrow + reverse video + reset
        
    def format_normal_text(self, text: str) -> str:
        """
        Format text without highlight (normal display)
        
        Args:
            text: Text to format
            
        Returns:
            Formatted text with normal spacing
        """
        return f"  {text}"  # Two spaces for alignment with arrow
        
    def display_title(self, title: str) -> None:
        """
        Display screen title
        
        Args:
            title: Title text to display
        """
        print(f"\n{title}")
        print("=" * len(title))
        print()
        
    def display_help(self) -> None:
        """Display keyboard navigation help"""
        print("\nキーボード操作:")
        print("  ↑/↓: 選択項目移動")
        print("  Enter: 選択確定")
        print("  Esc/Q: キャンセル・戻る")
        print()
        
    def display_error(self, message: str) -> None:
        """
        Display error message
        
        Args:
            message: Error message to display
        """
        print(f"\nエラー: {message}")
        print("任意のキーを押して続行してください...")
        self.keyboard_handler.get_key()
        
    def display_status(self, message: str) -> None:
        """
        Display status message
        
        Args:
            message: Status message to display
        """
        print(f"\n✓ {message}")
        print("")
        
    def confirm_action(self, message: str) -> bool:
        """
        Display confirmation dialog
        
        Args:
            message: Confirmation message
            
        Returns:
            True if confirmed, False if cancelled
        """
        print(f"\n{message}")
        print("続行しますか？ (y/N): ", end="")
        
        key = self.keyboard_handler.get_key()
        return key.lower() == 'y'