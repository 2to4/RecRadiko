"""
Test for MainMenuScreen class

Tests main menu screen with keyboard navigation for RecRadiko.
Following TDD approach: tests first, then implementation.
"""

import pytest
from unittest.mock import Mock, patch, call
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.ui.screens.main_menu_screen import MainMenuScreen
from src.ui.services.ui_service import UIService


class TestMainMenuScreen:
    """MainMenuScreen unit tests"""
    
    @pytest.fixture
    def main_menu_screen(self):
        """Create MainMenuScreen instance for testing"""
        return MainMenuScreen()
        
    @pytest.fixture
    def mock_ui_service(self):
        """Create mock UIService"""
        return Mock(spec=UIService)
        
    def test_main_menu_screen_initialization(self, main_menu_screen):
        """Test MainMenuScreen initialization"""
        assert main_menu_screen is not None
        assert main_menu_screen.title == "RecRadiko - メインメニュー"
        assert hasattr(main_menu_screen, 'menu_options')
        assert len(main_menu_screen.menu_options) > 0
        
    def test_main_menu_options(self, main_menu_screen):
        """Test main menu options are correctly defined"""
        expected_options = [
            "番組を録音する",
            "録音履歴を表示",
            "設定を変更",
            "ヘルプを表示",
            "終了"
        ]
        
        assert main_menu_screen.menu_options == expected_options
        
    def test_display_content(self, main_menu_screen, mock_ui_service):
        """Test displaying main menu content"""
        main_menu_screen.ui_service = mock_ui_service
        
        main_menu_screen.display_content()
        
        # Check that menu items are set and displayed
        mock_ui_service.set_menu_items.assert_called_once_with(main_menu_screen.menu_options)
        mock_ui_service.display_menu_with_highlight.assert_called_once()
        
    def test_handle_menu_selection_record_program(self, main_menu_screen, mock_ui_service):
        """Test handling '番組を録音する' selection"""
        main_menu_screen.ui_service = mock_ui_service
        
        with patch.object(main_menu_screen, 'start_recording_flow') as mock_start_recording:
            result = main_menu_screen.handle_menu_selection("番組を録音する")
            
            mock_start_recording.assert_called_once()
            assert result == "station_select"
            
    def test_handle_menu_selection_show_history(self, main_menu_screen, mock_ui_service):
        """Test handling '録音履歴を表示' selection"""
        main_menu_screen.ui_service = mock_ui_service
        
        with patch.object(main_menu_screen, 'show_recording_history') as mock_show_history:
            result = main_menu_screen.handle_menu_selection("録音履歴を表示")
            
            mock_show_history.assert_called_once()
            assert result is None  # Stay on main menu
            
    def test_handle_menu_selection_settings(self, main_menu_screen, mock_ui_service):
        """Test handling '設定を変更' selection"""
        main_menu_screen.ui_service = mock_ui_service
        
        with patch.object(main_menu_screen, 'show_settings') as mock_show_settings:
            result = main_menu_screen.handle_menu_selection("設定を変更")
            
            mock_show_settings.assert_called_once()
            assert result == "settings"
            
    def test_handle_menu_selection_help(self, main_menu_screen, mock_ui_service):
        """Test handling 'ヘルプを表示' selection"""
        main_menu_screen.ui_service = mock_ui_service
        mock_keyboard_handler = Mock()
        mock_ui_service.keyboard_handler = mock_keyboard_handler
        
        result = main_menu_screen.handle_menu_selection("ヘルプを表示")
        
        mock_ui_service.display_help.assert_called_once()
        mock_keyboard_handler.get_key.assert_called_once()
        assert result is None  # Stay on main menu
        
    def test_handle_menu_selection_exit(self, main_menu_screen, mock_ui_service):
        """Test handling '終了' selection"""
        main_menu_screen.ui_service = mock_ui_service
        
        with patch.object(main_menu_screen, 'confirm_exit') as mock_confirm_exit:
            mock_confirm_exit.return_value = True
            
            result = main_menu_screen.handle_menu_selection("終了")
            
            mock_confirm_exit.assert_called_once()
            assert result == "exit"
            
    def test_handle_menu_selection_exit_cancelled(self, main_menu_screen, mock_ui_service):
        """Test handling '終了' selection when cancelled"""
        main_menu_screen.ui_service = mock_ui_service
        
        with patch.object(main_menu_screen, 'confirm_exit') as mock_confirm_exit:
            mock_confirm_exit.return_value = False
            
            result = main_menu_screen.handle_menu_selection("終了")
            
            mock_confirm_exit.assert_called_once()
            assert result is None  # Stay on main menu
            
    def test_handle_menu_selection_unknown(self, main_menu_screen, mock_ui_service):
        """Test handling unknown selection"""
        main_menu_screen.ui_service = mock_ui_service
        
        result = main_menu_screen.handle_menu_selection("Unknown Option")
        
        assert result is None
        
    def test_run_main_menu_loop(self, main_menu_screen, mock_ui_service):
        """Test running main menu loop"""
        main_menu_screen.ui_service = mock_ui_service
        mock_ui_service.get_user_selection.return_value = "番組を録音する"
        
        with patch.object(main_menu_screen, 'handle_menu_selection') as mock_handle:
            mock_handle.return_value = "station_select"
            
            result = main_menu_screen.run_main_menu_loop()
            
            mock_ui_service.set_menu_items.assert_called_with(main_menu_screen.menu_options)
            mock_ui_service.get_user_selection.assert_called_once()
            mock_handle.assert_called_once_with("番組を録音する")
            assert result == "station_select"
            
    def test_run_main_menu_loop_cancelled(self, main_menu_screen, mock_ui_service):
        """Test running main menu loop when cancelled"""
        main_menu_screen.ui_service = mock_ui_service
        mock_ui_service.get_user_selection.return_value = None  # User cancelled
        
        result = main_menu_screen.run_main_menu_loop()
        
        assert result is None
        
    def test_confirm_exit_yes(self, main_menu_screen, mock_ui_service):
        """Test exit confirmation - Yes"""
        main_menu_screen.ui_service = mock_ui_service
        mock_ui_service.confirm_action.return_value = True
        
        result = main_menu_screen.confirm_exit()
        
        mock_ui_service.confirm_action.assert_called_once_with("RecRadikoを終了しますか？")
        assert result == True
        
    def test_confirm_exit_no(self, main_menu_screen, mock_ui_service):
        """Test exit confirmation - No"""
        main_menu_screen.ui_service = mock_ui_service
        mock_ui_service.confirm_action.return_value = False
        
        result = main_menu_screen.confirm_exit()
        
        mock_ui_service.confirm_action.assert_called_once_with("RecRadikoを終了しますか？")
        assert result == False
        
    def test_start_recording_flow(self, main_menu_screen):
        """Test starting recording flow"""
        # This method should prepare for navigation to station selection
        main_menu_screen.start_recording_flow()
        # No specific assertions needed - just verify no exceptions
        
    def test_show_recording_history(self, main_menu_screen, mock_ui_service):
        """Test showing recording history"""
        main_menu_screen.ui_service = mock_ui_service
        mock_keyboard_handler = Mock()
        mock_ui_service.keyboard_handler = mock_keyboard_handler
        
        with patch('os.listdir') as mock_listdir:
            mock_listdir.return_value = ['recording1.mp3', 'recording2.mp3']
            
            main_menu_screen.show_recording_history()
            
            # Should call keyboard handler for user input
            mock_keyboard_handler.get_key.assert_called_once()
            
    def test_show_settings(self, main_menu_screen):
        """Test showing settings"""
        # This method should prepare for navigation to settings
        main_menu_screen.show_settings()
        # No specific assertions needed - just verify no exceptions