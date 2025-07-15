"""
Menu Manager for RecRadiko Keyboard Navigation UI

Central navigation controller for keyboard-enabled screen system.
Manages screen registration, navigation flow, and screen lifecycle.

Based on DETAILED_DESIGN.md specifications:
- Central navigation coordination
- Screen stack management for back navigation
- Screen lifecycle management (activate/deactivate)
- Integration with existing CLI system
"""

import logging
from typing import Dict, List, Optional
from src.ui.screen_base import ScreenBase


class MenuManager:
    """
    Central menu navigation manager
    
    Handles screen registration, navigation flow, and screen lifecycle
    for the keyboard navigation interface.
    """
    
    def __init__(self):
        """Initialize menu manager"""
        self.logger = logging.getLogger(__name__)
        self.screens: Dict[str, ScreenBase] = {}
        self.current_screen: Optional[ScreenBase] = None
        self.screen_stack: List[str] = []
        
    def register_screen(self, name: str, screen: ScreenBase) -> None:
        """
        Register a screen with the menu manager
        
        Args:
            name: Unique screen identifier
            screen: Screen instance to register
        """
        self.screens[name] = screen
        self.logger.debug(f"Screen '{name}' registered")
        
    def navigate_to(self, screen_name: str) -> bool:
        """
        Navigate to specified screen
        
        Args:
            screen_name: Name of screen to navigate to
            
        Returns:
            True if navigation successful, False otherwise
        """
        if screen_name not in self.screens:
            self.logger.error(f"Screen '{screen_name}' not registered")
            return False
            
        target_screen = self.screens[screen_name]
        
        # Handle current screen
        if self.current_screen is not None:
            current_screen_name = self.get_current_screen_name()
            
            # If navigating to same screen, just refresh
            if current_screen_name == screen_name:
                target_screen.show()
                return True
                
            # Just deactivate current screen without cleanup (for stack navigation)
            self.current_screen.is_active = False
            if current_screen_name:
                self.screen_stack.append(current_screen_name)
                
        # Activate and show new screen
        self.current_screen = target_screen
        self.current_screen.activate()
        self.current_screen.show()
        
        self.logger.debug(f"Navigated to screen '{screen_name}'")
        return True
        
    def go_back(self) -> bool:
        """
        Navigate back to previous screen
        
        Returns:
            True if back navigation successful, False if no previous screen
        """
        if not self.screen_stack:
            self.logger.debug("No previous screen to go back to")
            return False
            
        # Get previous screen name
        previous_screen_name = self.screen_stack.pop()
        
        # Deactivate and cleanup current screen (going back means leaving it)
        if self.current_screen:
            self.current_screen.deactivate()
            
        # Navigate to previous screen without adding to stack
        if previous_screen_name not in self.screens:
            return False
            
        target_screen = self.screens[previous_screen_name]
        self.current_screen = target_screen
        self.current_screen.activate()
        self.current_screen.show()
        
        self.logger.debug(f"Went back to screen '{previous_screen_name}'")
        return True
        
    def clear_navigation_stack(self) -> None:
        """Clear the navigation stack"""
        self.screen_stack.clear()
        self.logger.debug("Navigation stack cleared")
        
    def get_current_screen_name(self) -> Optional[str]:
        """
        Get name of current screen
        
        Returns:
            Current screen name or None if no current screen
        """
        if not self.current_screen:
            return None
            
        # Find screen name by instance
        for name, screen in self.screens.items():
            if screen == self.current_screen:
                return name
                
        return None
        
    def is_screen_registered(self, screen_name: str) -> bool:
        """
        Check if screen is registered
        
        Args:
            screen_name: Screen name to check
            
        Returns:
            True if screen is registered, False otherwise
        """
        return screen_name in self.screens
        
    def get_navigation_history(self) -> List[str]:
        """
        Get navigation history (screen stack)
        
        Returns:
            List of screen names in navigation stack
        """
        return self.screen_stack.copy()
        
    def shutdown(self) -> None:
        """Cleanup and shutdown menu manager"""
        if self.current_screen:
            self.current_screen.deactivate()
            self.current_screen = None
            
        self.clear_navigation_stack()
        self.logger.debug("Menu manager shutdown complete")
        
    def get_registered_screens(self) -> List[str]:
        """
        Get list of registered screen names
        
        Returns:
            List of registered screen names
        """
        return list(self.screens.keys())
        
    def refresh_current_screen(self) -> bool:
        """
        Refresh current screen display
        
        Returns:
            True if refresh successful, False if no current screen
        """
        if not self.current_screen:
            return False
            
        self.current_screen.show()
        return True
        
    def handle_global_shortcut(self, key: str) -> bool:
        """
        Handle global keyboard shortcuts
        
        Args:
            key: Key pressed by user
            
        Returns:
            True if shortcut was handled, False otherwise
        """
        if key in ('q', 'Q'):
            # Global quit
            self.shutdown()
            return True
        elif key == 'h' or key == 'H':
            # Global help
            if self.current_screen:
                self.current_screen.show_help()
            return True
        elif key == 'r' or key == 'R':
            # Refresh current screen
            return self.refresh_current_screen()
        else:
            return False
            
    def navigate_to_main(self) -> bool:
        """
        Navigate to main screen (convenience method)
        
        Returns:
            True if navigation successful, False otherwise
        """
        return self.navigate_to('main')
        
    def can_go_back(self) -> bool:
        """
        Check if back navigation is possible
        
        Returns:
            True if can go back, False otherwise
        """
        return len(self.screen_stack) > 0
        
    def get_screen_depth(self) -> int:
        """
        Get current navigation depth
        
        Returns:
            Number of screens in navigation stack
        """
        return len(self.screen_stack)
        
    def force_navigate_to(self, screen_name: str) -> bool:
        """
        Force navigate to screen without stack management
        
        Args:
            screen_name: Screen to navigate to
            
        Returns:
            True if navigation successful, False otherwise
        """
        if screen_name not in self.screens:
            return False
            
        # Deactivate current screen without stack management
        if self.current_screen:
            self.current_screen.deactivate()
            
        # Clear stack and navigate
        self.clear_navigation_stack()
        target_screen = self.screens[screen_name]
        self.current_screen = target_screen
        self.current_screen.activate()
        self.current_screen.show()
        
        self.logger.debug(f"Force navigated to screen '{screen_name}'")
        return True