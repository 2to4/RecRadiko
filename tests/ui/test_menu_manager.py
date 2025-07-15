"""
Test for MenuManager class

Tests central menu navigation and screen management.
Following TDD approach: tests first, then implementation.
"""

import pytest
from unittest.mock import Mock, patch, call
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.menu_manager import MenuManager
from src.ui.screen_base import ScreenBase


class MockScreen(ScreenBase):
    """Mock screen for testing"""
    
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.display_content_called = False
        self.cleanup_called = False
        
    def display_content(self):
        self.display_content_called = True
        
    def cleanup(self):
        self.cleanup_called = True


class TestMenuManager:
    """MenuManager unit tests"""
    
    @pytest.fixture
    def menu_manager(self):
        """Create MenuManager instance for testing"""
        return MenuManager()
        
    @pytest.fixture
    def mock_screens(self):
        """Create mock screens for testing"""
        return {
            'main': MockScreen('main'),
            'station_select': MockScreen('station_select'),
            'date_select': MockScreen('date_select')
        }
        
    def test_menu_manager_initialization(self, menu_manager):
        """Test MenuManager initialization"""
        assert menu_manager is not None
        assert hasattr(menu_manager, 'screens')
        assert hasattr(menu_manager, 'current_screen')
        assert hasattr(menu_manager, 'screen_stack')
        assert menu_manager.screens == {}
        assert menu_manager.current_screen is None
        assert menu_manager.screen_stack == []
        
    def test_register_screen(self, menu_manager, mock_screens):
        """Test registering a screen"""
        screen = mock_screens['main']
        menu_manager.register_screen('main', screen)
        
        assert 'main' in menu_manager.screens
        assert menu_manager.screens['main'] == screen
        
    def test_register_multiple_screens(self, menu_manager, mock_screens):
        """Test registering multiple screens"""
        for name, screen in mock_screens.items():
            menu_manager.register_screen(name, screen)
            
        assert len(menu_manager.screens) == 3
        assert all(name in menu_manager.screens for name in mock_screens.keys())
        
    def test_navigate_to_screen_first_time(self, menu_manager, mock_screens):
        """Test navigating to screen for first time"""
        main_screen = mock_screens['main']
        menu_manager.register_screen('main', main_screen)
        
        result = menu_manager.navigate_to('main')
        
        assert result == True
        assert menu_manager.current_screen == main_screen
        assert main_screen.is_active == True
        assert main_screen.display_content_called == True
        
    def test_navigate_to_nonexistent_screen(self, menu_manager):
        """Test navigating to non-existent screen"""
        result = menu_manager.navigate_to('nonexistent')
        
        assert result == False
        assert menu_manager.current_screen is None
        
    def test_navigate_with_screen_stack(self, menu_manager, mock_screens):
        """Test navigation with screen stack management"""
        main_screen = mock_screens['main']
        station_screen = mock_screens['station_select']
        
        menu_manager.register_screen('main', main_screen)
        menu_manager.register_screen('station_select', station_screen)
        
        # Navigate to main
        menu_manager.navigate_to('main')
        assert len(menu_manager.screen_stack) == 0
        
        # Navigate to station_select (should push main to stack)
        menu_manager.navigate_to('station_select')
        assert len(menu_manager.screen_stack) == 1
        assert menu_manager.screen_stack[0] == 'main'
        assert menu_manager.current_screen == station_screen
        
    def test_go_back_with_stack(self, menu_manager, mock_screens):
        """Test going back using screen stack"""
        main_screen = mock_screens['main']
        station_screen = mock_screens['station_select']
        
        menu_manager.register_screen('main', main_screen)
        menu_manager.register_screen('station_select', station_screen)
        
        # Setup navigation
        menu_manager.navigate_to('main')
        menu_manager.navigate_to('station_select')
        
        # Go back
        result = menu_manager.go_back()
        
        assert result == True
        assert menu_manager.current_screen == main_screen
        assert len(menu_manager.screen_stack) == 0
        assert station_screen.is_active == False
        assert station_screen.cleanup_called == True
        
    def test_go_back_empty_stack(self, menu_manager, mock_screens):
        """Test going back with empty stack"""
        main_screen = mock_screens['main']
        menu_manager.register_screen('main', main_screen)
        menu_manager.navigate_to('main')
        
        result = menu_manager.go_back()
        
        assert result == False
        assert menu_manager.current_screen == main_screen
        
    def test_clear_navigation_stack(self, menu_manager, mock_screens):
        """Test clearing navigation stack"""
        main_screen = mock_screens['main']
        station_screen = mock_screens['station_select']
        date_screen = mock_screens['date_select']
        
        for name, screen in mock_screens.items():
            menu_manager.register_screen(name, screen)
            
        # Build up stack
        menu_manager.navigate_to('main')
        menu_manager.navigate_to('station_select')
        menu_manager.navigate_to('date_select')
        
        assert len(menu_manager.screen_stack) == 2
        
        # Clear stack
        menu_manager.clear_navigation_stack()
        
        assert len(menu_manager.screen_stack) == 0
        
    def test_get_current_screen_name(self, menu_manager, mock_screens):
        """Test getting current screen name"""
        main_screen = mock_screens['main']
        menu_manager.register_screen('main', main_screen)
        
        # No current screen
        assert menu_manager.get_current_screen_name() is None
        
        # With current screen
        menu_manager.navigate_to('main')
        assert menu_manager.get_current_screen_name() == 'main'
        
    def test_is_screen_registered(self, menu_manager, mock_screens):
        """Test checking if screen is registered"""
        main_screen = mock_screens['main']
        
        assert menu_manager.is_screen_registered('main') == False
        
        menu_manager.register_screen('main', main_screen)
        assert menu_manager.is_screen_registered('main') == True
        
    def test_get_navigation_history(self, menu_manager, mock_screens):
        """Test getting navigation history"""
        for name, screen in mock_screens.items():
            menu_manager.register_screen(name, screen)
            
        # Build navigation history
        menu_manager.navigate_to('main')
        menu_manager.navigate_to('station_select')
        menu_manager.navigate_to('date_select')
        
        history = menu_manager.get_navigation_history()
        expected = ['main', 'station_select']  # Current screen not in stack
        
        assert history == expected
        
    def test_shutdown_cleanup(self, menu_manager, mock_screens):
        """Test shutdown cleanup"""
        main_screen = mock_screens['main']
        menu_manager.register_screen('main', main_screen)
        menu_manager.navigate_to('main')
        
        menu_manager.shutdown()
        
        assert main_screen.is_active == False
        assert main_screen.cleanup_called == True
        assert menu_manager.current_screen is None
        assert len(menu_manager.screen_stack) == 0
        
    def test_navigation_to_same_screen(self, menu_manager, mock_screens):
        """Test navigating to the same screen"""
        main_screen = mock_screens['main']
        menu_manager.register_screen('main', main_screen)
        
        menu_manager.navigate_to('main')
        first_call_status = main_screen.display_content_called
        main_screen.display_content_called = False  # Reset
        
        # Navigate to same screen again
        result = menu_manager.navigate_to('main')
        
        assert result == True
        assert menu_manager.current_screen == main_screen
        assert main_screen.display_content_called == True  # Should refresh display
        
    def test_screen_deactivation_on_navigation(self, menu_manager, mock_screens):
        """Test that previous screen is deactivated on navigation"""
        main_screen = mock_screens['main']
        station_screen = mock_screens['station_select']
        
        menu_manager.register_screen('main', main_screen)
        menu_manager.register_screen('station_select', station_screen)
        
        # Navigate to main, then to station_select
        menu_manager.navigate_to('main')
        menu_manager.navigate_to('station_select')
        
        # Main screen should be deactivated but not cleaned up (it's in stack)
        assert main_screen.is_active == False
        assert main_screen.cleanup_called == False  # Still in stack, no cleanup