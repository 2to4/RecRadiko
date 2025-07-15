"""
Test for UIService class

Tests keyboard navigation UI service with highlight display and selection management.
Following TDD approach: tests first, then implementation.
"""

import pytest
from unittest.mock import Mock, patch, call
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.ui.services.ui_service import UIService
from src.ui.input.keyboard_handler import KeyboardHandler


class TestUIService:
    """UIService unit tests"""
    
    @pytest.fixture
    def ui_service(self):
        """Create UIService instance for testing"""
        return UIService()
        
    @pytest.fixture
    def mock_keyboard_handler(self):
        """Create mock KeyboardHandler for testing"""
        return Mock(spec=KeyboardHandler)
        
    def test_ui_service_initialization(self, ui_service):
        """Test UIService initialization"""
        assert ui_service is not None
        assert hasattr(ui_service, 'keyboard_handler')
        assert hasattr(ui_service, 'current_selection')
        assert hasattr(ui_service, 'menu_items')
        assert ui_service.current_selection == 0
        assert ui_service.menu_items == []
        
    def test_set_menu_items(self, ui_service):
        """Test setting menu items"""
        items = ['Item 1', 'Item 2', 'Item 3']
        ui_service.set_menu_items(items)
        
        assert ui_service.menu_items == items
        assert ui_service.current_selection == 0
        
    def test_move_selection_down(self, ui_service):
        """Test moving selection down"""
        ui_service.set_menu_items(['Item 1', 'Item 2', 'Item 3'])
        
        ui_service.move_selection_down()
        assert ui_service.current_selection == 1
        
        ui_service.move_selection_down()
        assert ui_service.current_selection == 2
        
    def test_move_selection_down_circular(self, ui_service):
        """Test moving selection down with circular navigation"""
        ui_service.set_menu_items(['Item 1', 'Item 2', 'Item 3'])
        ui_service.current_selection = 2  # Last item
        
        ui_service.move_selection_down()
        assert ui_service.current_selection == 0  # Wrap to first
        
    def test_move_selection_up(self, ui_service):
        """Test moving selection up"""
        ui_service.set_menu_items(['Item 1', 'Item 2', 'Item 3'])
        ui_service.current_selection = 2
        
        ui_service.move_selection_up()
        assert ui_service.current_selection == 1
        
        ui_service.move_selection_up()
        assert ui_service.current_selection == 0
        
    def test_move_selection_up_circular(self, ui_service):
        """Test moving selection up with circular navigation"""
        ui_service.set_menu_items(['Item 1', 'Item 2', 'Item 3'])
        ui_service.current_selection = 0  # First item
        
        ui_service.move_selection_up()
        assert ui_service.current_selection == 2  # Wrap to last
        
    def test_get_current_item(self, ui_service):
        """Test getting current selected item"""
        items = ['Item 1', 'Item 2', 'Item 3']
        ui_service.set_menu_items(items)
        ui_service.current_selection = 1
        
        current_item = ui_service.get_current_item()
        assert current_item == 'Item 2'
        
    def test_get_current_item_empty_menu(self, ui_service):
        """Test getting current item from empty menu"""
        current_item = ui_service.get_current_item()
        assert current_item is None
        
    @patch('builtins.print')
    def test_display_menu_with_highlight(self, mock_print, ui_service):
        """Test displaying menu with highlight"""
        items = ['Item 1', 'Item 2', 'Item 3']
        ui_service.set_menu_items(items)
        ui_service.current_selection = 1
        
        ui_service.display_menu_with_highlight()
        
        # Check that print was called with highlighted menu
        expected_calls = [
            call('  Item 1'),
            call('→ \033[7mItem 2\033[0m'),  # Highlighted with arrow and reverse video
            call('  Item 3')
        ]
        mock_print.assert_has_calls(expected_calls)
        
    @patch('builtins.print')
    def test_clear_screen(self, mock_print, ui_service):
        """Test clearing screen"""
        ui_service.clear_screen()
        
        # Check that ANSI clear sequence was printed
        mock_print.assert_called_with('\033[2J\033[H', end='')
        
    def test_get_user_selection_enter(self, ui_service, mock_keyboard_handler):
        """Test getting user selection with Enter key"""
        ui_service.keyboard_handler = mock_keyboard_handler
        ui_service.set_menu_items(['Item 1', 'Item 2', 'Item 3'])
        ui_service.current_selection = 1
        
        # Mock keyboard input: Enter key
        mock_keyboard_handler.get_key.return_value = 'ENTER'
        
        with patch.object(ui_service, 'display_menu_with_highlight'):
            result = ui_service.get_user_selection()
            
        assert result == 'Item 2'
        
    def test_get_user_selection_navigation(self, ui_service, mock_keyboard_handler):
        """Test getting user selection with navigation keys"""
        ui_service.keyboard_handler = mock_keyboard_handler
        ui_service.set_menu_items(['Item 1', 'Item 2', 'Item 3'])
        ui_service.current_selection = 0
        
        # Mock keyboard input: DOWN, DOWN, ENTER
        mock_keyboard_handler.get_key.side_effect = ['DOWN', 'DOWN', 'ENTER']
        
        with patch.object(ui_service, 'display_menu_with_highlight'):
            result = ui_service.get_user_selection()
            
        assert result == 'Item 3'
        assert ui_service.current_selection == 2
        
    def test_get_user_selection_escape(self, ui_service, mock_keyboard_handler):
        """Test getting user selection with Escape key"""
        ui_service.keyboard_handler = mock_keyboard_handler
        ui_service.set_menu_items(['Item 1', 'Item 2', 'Item 3'])
        
        # Mock keyboard input: ESCAPE
        mock_keyboard_handler.get_key.return_value = 'ESCAPE'
        
        with patch.object(ui_service, 'display_menu_with_highlight'):
            result = ui_service.get_user_selection()
            
        assert result is None
        
    def test_format_highlight_text(self, ui_service):
        """Test formatting text with highlight"""
        result = ui_service.format_highlight_text("Test Item")
        expected = "→ \033[7mTest Item\033[0m"
        assert result == expected
        
    def test_format_normal_text(self, ui_service):
        """Test formatting text without highlight"""
        result = ui_service.format_normal_text("Test Item")
        expected = "  Test Item"
        assert result == expected