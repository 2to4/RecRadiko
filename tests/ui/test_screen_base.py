"""
Test for ScreenBase class

Tests keyboard-enabled base screen class with navigation and lifecycle management.
Following TDD approach: tests first, then implementation.
"""

import pytest
from unittest.mock import Mock, patch, call
from abc import ABC
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.screen_base import ScreenBase
from src.ui.services.ui_service import UIService


class TestScreenImplementation(ScreenBase):
    """Test implementation of ScreenBase for testing"""
    
    def __init__(self):
        super().__init__()
        self.display_called = False
        self.cleanup_called = False
        
    def display_content(self):
        """Test implementation of abstract method"""
        self.display_called = True
        
    def cleanup(self):
        """Test implementation of cleanup"""
        self.cleanup_called = True


class TestScreenBase:
    """ScreenBase unit tests"""
    
    @pytest.fixture
    def screen(self):
        """Create test screen instance"""
        return TestScreenImplementation()
        
    @pytest.fixture
    def mock_ui_service(self):
        """Create mock UIService"""
        return Mock(spec=UIService)
        
    def test_screen_base_initialization(self, screen):
        """Test ScreenBase initialization"""
        assert screen is not None
        assert hasattr(screen, 'ui_service')
        assert hasattr(screen, 'title')
        assert hasattr(screen, 'is_active')
        assert screen.title == ""
        assert screen.is_active == False
        
    def test_screen_base_abstract_methods(self):
        """Test that ScreenBase is abstract"""
        with pytest.raises(TypeError):
            ScreenBase()  # Should raise TypeError for abstract class
            
    def test_set_title(self, screen):
        """Test setting screen title"""
        screen.set_title("Test Screen")
        assert screen.title == "Test Screen"
        
    def test_activate_screen(self, screen):
        """Test activating screen"""
        screen.activate()
        assert screen.is_active == True
        
    def test_deactivate_screen(self, screen):
        """Test deactivating screen"""
        screen.activate()
        screen.deactivate()
        assert screen.is_active == False
        assert screen.cleanup_called == True
        
    def test_show_screen(self, screen, mock_ui_service):
        """Test showing screen with content display"""
        screen.ui_service = mock_ui_service
        screen.set_title("Test Screen")
        
        screen.show()
        
        # Check that UI service methods were called
        mock_ui_service.clear_screen.assert_called_once()
        mock_ui_service.display_title.assert_called_once_with("Test Screen")
        assert screen.display_called == True
        
    def test_get_user_choice_with_options(self, screen, mock_ui_service):
        """Test getting user choice with menu options"""
        screen.ui_service = mock_ui_service
        options = ["Option 1", "Option 2", "Option 3"]
        mock_ui_service.get_user_selection.return_value = "Option 2"
        
        result = screen.get_user_choice(options)
        
        mock_ui_service.set_menu_items.assert_called_once_with(options)
        mock_ui_service.get_user_selection.assert_called_once()
        assert result == "Option 2"
        
    def test_get_user_choice_empty_options(self, screen, mock_ui_service):
        """Test getting user choice with empty options"""
        screen.ui_service = mock_ui_service
        
        result = screen.get_user_choice([])
        
        assert result is None
        mock_ui_service.set_menu_items.assert_not_called()
        
    def test_display_message(self, screen, mock_ui_service):
        """Test displaying message"""
        screen.ui_service = mock_ui_service
        
        screen.display_message("Test message")
        
        mock_ui_service.display_error.assert_called_once_with("Test message")
        
    def test_confirm_action(self, screen, mock_ui_service):
        """Test confirmation dialog"""
        screen.ui_service = mock_ui_service
        mock_ui_service.confirm_action.return_value = True
        
        result = screen.confirm_action("Continue?")
        
        mock_ui_service.confirm_action.assert_called_once_with("Continue?")
        assert result == True
        
    def test_show_help(self, screen, mock_ui_service):
        """Test showing help"""
        screen.ui_service = mock_ui_service
        
        screen.show_help()
        
        mock_ui_service.display_help.assert_called_once()
        
    def test_handle_navigation_key_up(self, screen):
        """Test handling UP navigation key"""
        with patch.object(screen, 'on_move_up') as mock_move_up:
            result = screen.handle_navigation_key('UP')
            mock_move_up.assert_called_once()
            assert result == True
            
    def test_handle_navigation_key_down(self, screen):
        """Test handling DOWN navigation key"""
        with patch.object(screen, 'on_move_down') as mock_move_down:
            result = screen.handle_navigation_key('DOWN')
            mock_move_down.assert_called_once()
            assert result == True
            
    def test_handle_navigation_key_enter(self, screen):
        """Test handling ENTER key"""
        with patch.object(screen, 'on_select') as mock_select:
            result = screen.handle_navigation_key('ENTER')
            mock_select.assert_called_once()
            assert result == True
            
    def test_handle_navigation_key_escape(self, screen):
        """Test handling ESCAPE key"""
        with patch.object(screen, 'on_back') as mock_back:
            result = screen.handle_navigation_key('ESCAPE')
            mock_back.assert_called_once()
            assert result == True
            
    def test_handle_navigation_key_unknown(self, screen):
        """Test handling unknown key"""
        result = screen.handle_navigation_key('UNKNOWN')
        assert result == False
        
    def test_on_navigation_methods_default(self, screen):
        """Test default navigation method implementations"""
        # Default implementations should do nothing
        screen.on_move_up()
        screen.on_move_down() 
        screen.on_select()
        screen.on_back()
        # No assertions needed - just verify no exceptions
        
    def test_screen_lifecycle(self, screen, mock_ui_service):
        """Test complete screen lifecycle"""
        screen.ui_service = mock_ui_service
        screen.set_title("Lifecycle Test")
        
        # Activate
        screen.activate()
        assert screen.is_active == True
        
        # Show
        screen.show()
        assert screen.display_called == True
        mock_ui_service.clear_screen.assert_called()
        mock_ui_service.display_title.assert_called_with("Lifecycle Test")
        
        # Deactivate
        screen.deactivate()
        assert screen.is_active == False
        assert screen.cleanup_called == True