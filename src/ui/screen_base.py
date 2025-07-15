"""
Base Screen Class for RecRadiko Keyboard Navigation UI

Provides common functionality for all screens in the keyboard navigation interface.
Implements template method pattern with keyboard event handling.

Based on DETAILED_DESIGN.md specifications:
- Abstract base class with template methods
- Keyboard navigation event handling
- Screen lifecycle management (activate, show, deactivate)
- UI service integration for display operations
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Any
import logging
from src.ui.services.ui_service import UIService
from src.ui.performance_optimizer import optimize_performance, performance_optimizer


class ScreenBase(ABC):
    """
    Abstract base class for all keyboard navigation screens
    
    Provides common screen functionality including:
    - Screen lifecycle management
    - Keyboard navigation handling
    - UI service integration
    - Template methods for screen-specific behavior
    """
    
    def __init__(self):
        """Initialize base screen"""
        self.logger = logging.getLogger(__name__)
        self.ui_service = UIService()
        self.title = ""
        self.is_active = False
        
    def set_title(self, title: str) -> None:
        """
        Set screen title
        
        Args:
            title: Screen title to display
        """
        self.title = title
        
    def activate(self) -> None:
        """Activate the screen"""
        self.is_active = True
        self.logger.debug(f"Screen '{self.title}' activated")
        
    def deactivate(self) -> None:
        """Deactivate the screen and cleanup"""
        self.is_active = False
        self.cleanup()
        self.logger.debug(f"Screen '{self.title}' deactivated")
        
    @optimize_performance("screen_show")
    def show(self) -> None:
        """Display the screen (template method)"""
        self.ui_service.clear_screen()
        if self.title:
            self.ui_service.display_title(self.title)
        self.display_content()
        
    @abstractmethod
    def display_content(self) -> None:
        """
        Display screen-specific content (must be implemented by subclasses)
        """
        pass
        
    def cleanup(self) -> None:
        """
        Cleanup screen resources (can be overridden by subclasses)
        """
        pass
        
    def get_user_choice(self, options: List[Any]) -> Optional[Any]:
        """
        Get user choice from menu options using keyboard navigation
        
        Args:
            options: List of menu options to choose from
            
        Returns:
            Selected option or None if cancelled
        """
        if not options:
            return None
            
        self.ui_service.set_menu_items(options)
        return self.ui_service.get_user_selection()
        
    def display_message(self, message: str) -> None:
        """
        Display message to user
        
        Args:
            message: Message to display
        """
        self.ui_service.display_error(message)
        
    def confirm_action(self, message: str) -> bool:
        """
        Display confirmation dialog
        
        Args:
            message: Confirmation message
            
        Returns:
            True if confirmed, False if cancelled
        """
        return self.ui_service.confirm_action(message)
        
    def show_help(self) -> None:
        """Show keyboard navigation help"""
        self.ui_service.display_help()
        
    def handle_navigation_key(self, key: str) -> bool:
        """
        Handle keyboard navigation events
        
        Args:
            key: Key pressed by user
            
        Returns:
            True if key was handled, False otherwise
        """
        if key == 'UP':
            self.on_move_up()
            return True
        elif key == 'DOWN':
            self.on_move_down()
            return True
        elif key == 'ENTER':
            self.on_select()
            return True
        elif key == 'ESCAPE':
            self.on_back()
            return True
        else:
            return False
            
    def on_move_up(self) -> None:
        """Handle move up navigation (can be overridden by subclasses)"""
        pass
        
    def on_move_down(self) -> None:
        """Handle move down navigation (can be overridden by subclasses)"""
        pass
        
    def on_select(self) -> None:
        """Handle selection confirmation (can be overridden by subclasses)"""
        pass
        
    def on_back(self) -> None:
        """Handle back/cancel navigation (can be overridden by subclasses)"""
        pass
        
    def wait_for_key(self) -> str:
        """
        Wait for user key press
        
        Returns:
            Key pressed by user
        """
        return self.ui_service.keyboard_handler.get_key()
        
    def display_status(self, status: str) -> None:
        """
        Display status message
        
        Args:
            status: Status message to display
        """
        print(f"\nステータス: {status}")
        
    def display_options(self, options: List[str], selected_index: int = 0) -> None:
        """
        Display options with keyboard navigation highlighting
        
        Args:
            options: List of option strings
            selected_index: Currently selected option index
        """
        for i, option in enumerate(options):
            if i == selected_index:
                print(self.ui_service.format_highlight_text(option))
            else:
                print(self.ui_service.format_normal_text(option))
                
    def run_navigation_loop(self, options: List[Any]) -> Optional[Any]:
        """
        Run keyboard navigation loop for menu selection
        
        Args:
            options: List of menu options
            
        Returns:
            Selected option or None if cancelled
        """
        if not options:
            return None
            
        selected_index = 0
        
        while True:
            self.ui_service.clear_screen()
            if self.title:
                self.ui_service.display_title(self.title)
                
            self.display_options([str(option) for option in options], selected_index)
            
            key = self.wait_for_key()
            
            if key == 'UP':
                selected_index = (selected_index - 1) % len(options)
            elif key == 'DOWN':
                selected_index = (selected_index + 1) % len(options)
            elif key == 'ENTER':
                return options[selected_index]
            elif key in ('ESCAPE', 'q', 'Q'):
                return None