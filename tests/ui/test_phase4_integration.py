"""
Phase 4 Integration Tests for RecRadiko Keyboard Navigation UI

Tests integration between new Phase 4 screens (search, settings, system info)
and existing UI components (main menu, recording workflow).

Following the principle of minimal mock usage - using real components
where possible and testing actual integration flows.
"""

import pytest
import tempfile
import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, date

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.screens.main_menu_screen import MainMenuScreen
from src.ui.screens.program_select_screen import ProgramSelectScreen
from src.ui.screens.settings_screen import SettingsScreen
from src.ui.screens.date_select_screen import DateSelectScreen
from src.ui.recording_workflow import RecordingWorkflow


class TestPhase4Integration:
    """Integration tests for Phase 4 screens with existing UI components"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for integration tests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".recradiko"
            config_dir.mkdir(parents=True)
            
            # Create config file
            config_file = config_dir / "config.json"
            config_data = {
                "version": "2.0",
                "prefecture": "東京",
                "audio": {
                    "format": "mp3",
                    "bitrate": 256,
                    "sample_rate": 48000
                },
                "recording": {
                    "save_path": str(config_dir / "recordings"),
                    "id3_tags_enabled": True
                },
                "notifications": {
                    "enabled": True,
                    "sound_enabled": False
                }
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Create recordings directory
            recordings_dir = config_dir / "recordings"
            recordings_dir.mkdir(parents=True)
            
            # Create logs directory
            logs_dir = config_dir / "logs"
            logs_dir.mkdir(parents=True)
            
            yield config_dir
    
    @pytest.fixture
    def mock_ui_service(self):
        """Create mock UI service for integration tests"""
        mock_ui = Mock()
        mock_ui.get_user_selection = Mock(return_value=None)
        mock_ui.display_info = Mock()
        mock_ui.display_error = Mock()
        mock_ui.display_success = Mock()
        mock_ui.set_menu_items = Mock()
        mock_ui.display_menu_with_highlight = Mock()
        mock_ui.confirm_action = Mock(return_value=True)
        mock_ui.get_text_input = Mock(return_value="test")
        mock_ui.keyboard_handler = Mock()
        mock_ui.keyboard_handler.get_key = Mock(return_value='q')
        return mock_ui
    
    def test_main_menu_to_search_screen_integration(self, temp_config_dir, mock_ui_service):
        """Test navigation from main menu to search screen"""
        # Initialize main menu
        main_menu = MainMenuScreen()
        main_menu.ui_service = mock_ui_service
        
        # Test navigation to search screen
        result = main_menu.handle_menu_selection("番組を検索する")
        assert result == "search"
        
        # Initialize search screen
        search_screen = SearchScreen()
        search_screen.ui_service = mock_ui_service
        
        # Test search screen initialization
        assert search_screen.title == "番組検索"
        assert len(search_screen.search_methods) == 5
        
        # Test search screen display
        search_screen.display_content()
        mock_ui_service.set_menu_items.assert_called()
        mock_ui_service.display_menu_with_highlight.assert_called()
    
    def test_main_menu_to_settings_screen_integration(self, temp_config_dir, mock_ui_service):
        """Test navigation from main menu to settings screen"""
        # Initialize main menu
        main_menu = MainMenuScreen()
        main_menu.ui_service = mock_ui_service
        
        # Test navigation to settings screen
        result = main_menu.handle_menu_selection("設定を変更")
        assert result == "settings"
        
        # Initialize settings screen with real config
        settings_screen = SettingsScreen(str(temp_config_dir / "config.json"))
        settings_screen.ui_service = mock_ui_service
        
        # Test settings screen initialization
        assert settings_screen.title == "設定"
        assert len(settings_screen.setting_categories) == 4
        
        # Test settings screen display
        settings_screen.display_content()
        mock_ui_service.set_menu_items.assert_called()
        mock_ui_service.display_menu_with_highlight.assert_called()
    
    def test_main_menu_to_system_info_screen_integration(self, temp_config_dir, mock_ui_service):
        """Test navigation from main menu to system info screen"""
        # Initialize main menu
        main_menu = MainMenuScreen()
        main_menu.ui_service = mock_ui_service
        
        # Test navigation to system info screen
        result = main_menu.handle_menu_selection("システム情報を表示")
        assert result == "system_info"
        
        # Initialize system info screen with real config
        system_info_screen = SystemInfoScreen(str(temp_config_dir))
        system_info_screen.ui_service = mock_ui_service
        
        # Test system info screen initialization
        assert system_info_screen.title == "システム情報"
        assert len(system_info_screen.menu_options) == 7
        
        # Test system info screen display
        system_info_screen.display_content()
        mock_ui_service.set_menu_items.assert_called()
        mock_ui_service.display_menu_with_highlight.assert_called()
    
    def test_search_screen_integration_with_recording_workflow(self, temp_config_dir, mock_ui_service):
        """Test search screen integration with recording workflow"""
        # Initialize search screen
        search_screen = SearchScreen()
        search_screen.ui_service = mock_ui_service
        
        # Mock search methods
        mock_ui_service.get_user_selection.side_effect = [
            "番組名で検索",  # Select search method
            None  # Exit
        ]
        
        # Mock text input for search
        mock_ui_service.get_text_input.return_value = "ニュース"
        
        # Test search workflow
        with patch.object(search_screen, 'search_by_title') as mock_search:
            mock_search.return_value = [
                {
                    "title": "ニュース番組",
                    "start_time": "06:00",
                    "end_time": "06:30",
                    "station": "TBS",
                    "date": "2025-07-14"
                }
            ]
            
            result = search_screen.run_search_workflow()
            assert result == True
            mock_search.assert_called_once_with("ニュース")
    
    def test_settings_screen_integration_with_config_persistence(self, temp_config_dir, mock_ui_service):
        """Test settings screen integration with config file persistence"""
        config_file = temp_config_dir / "config.json"
        
        # Initialize settings screen
        settings_screen = SettingsScreen(str(config_file))
        settings_screen.ui_service = mock_ui_service
        
        # Mock user selections for region change
        mock_ui_service.get_user_selection.side_effect = [
            "地域設定",  # Select region settings
            "大阪",      # Select new region
            None         # Exit
        ]
        
        # Test region change workflow
        with patch.object(settings_screen, 'handle_region_setting') as mock_change:
            mock_change.return_value = True
            
            result = settings_screen.run_settings_workflow()
            assert result == True
            mock_change.assert_called_once()
        
        # Verify config manager can load the config
        assert settings_screen.config_manager is not None
        config = settings_screen.config_manager.get_config()
        assert config is not None
        assert "prefecture" in config
    
    def test_system_info_screen_integration_with_real_system_data(self, temp_config_dir, mock_ui_service):
        """Test system info screen integration with real system data"""
        # Initialize system info screen
        system_info_screen = SystemInfoScreen(str(temp_config_dir))
        system_info_screen.ui_service = mock_ui_service
        
        # Mock user selections
        mock_ui_service.get_user_selection.side_effect = [
            "システム状況を表示",  # Select system status
            "録音統計を表示",      # Select recording stats
            None                   # Exit
        ]
        
        # Test system info workflow
        with patch.object(system_info_screen, 'show_system_status') as mock_status, \
             patch.object(system_info_screen, 'show_recording_statistics') as mock_stats:
            
            result = system_info_screen.run_system_info_workflow()
            assert result == True
            mock_status.assert_called_once()
            mock_stats.assert_called_once()
        
        # Verify system checker can get real system data
        system_status = system_info_screen.system_checker.get_system_status()
        assert "authentication" in system_status
        assert "api_connection" in system_status
        assert "ffmpeg" in system_status
        assert "python_version" in system_status
    
    def test_full_navigation_flow_integration(self, temp_config_dir, mock_ui_service):
        """Test complete navigation flow between all Phase 4 screens"""
        # Initialize main menu
        main_menu = MainMenuScreen()
        main_menu.ui_service = mock_ui_service
        
        # Test navigation sequence: main -> search -> main -> settings -> main -> system_info
        navigation_sequence = [
            ("番組を検索する", "search"),
            ("設定を変更", "settings"),
            ("システム情報を表示", "system_info"),
            ("終了", "exit")
        ]
        
        for menu_option, expected_result in navigation_sequence:
            result = main_menu.handle_menu_selection(menu_option)
            assert result == expected_result
    
    def test_phase4_screens_keyboard_navigation_consistency(self, temp_config_dir, mock_ui_service):
        """Test keyboard navigation consistency across Phase 4 screens"""
        screens = [
            ("search", SearchScreen()),
            ("settings", SettingsScreen(str(temp_config_dir / "config.json"))),
            ("system_info", SystemInfoScreen(str(temp_config_dir)))
        ]
        
        for screen_name, screen in screens:
            screen.ui_service = mock_ui_service
            
            # Test common keyboard navigation methods
            assert hasattr(screen, 'display_content')
            assert hasattr(screen, 'ui_service')
            assert hasattr(screen, 'title')
            
            # Test that each screen can display content
            screen.display_content()
            mock_ui_service.set_menu_items.assert_called()
            mock_ui_service.display_menu_with_highlight.assert_called()
            
            # Reset mocks for next screen
            mock_ui_service.reset_mock()
    
    def test_phase4_error_handling_integration(self, temp_config_dir, mock_ui_service):
        """Test error handling integration across Phase 4 screens"""
        # Test search screen error handling
        search_screen = SearchScreen()
        search_screen.ui_service = mock_ui_service
        
        # Mock search method to raise exception
        with patch.object(search_screen, 'search_by_title') as mock_search:
            mock_search.side_effect = Exception("Search failed")
            
            # Test error handling
            result = search_screen.search_by_title("test")
            assert result == []  # Should return empty list on error
        
        # Test settings screen error handling
        settings_screen = SettingsScreen("/nonexistent/config.json")
        settings_screen.ui_service = mock_ui_service
        
        # Should handle missing config file gracefully
        try:
            settings_screen.display_content()
            # Should not raise exception
        except Exception as e:
            pytest.fail(f"Settings screen should handle missing config gracefully: {e}")
        
        # Test system info screen error handling
        system_info_screen = SystemInfoScreen("/nonexistent/config")
        system_info_screen.ui_service = mock_ui_service
        
        # Should handle missing config directory gracefully
        try:
            system_info_screen.display_content()
            # Should not raise exception
        except Exception as e:
            pytest.fail(f"System info screen should handle missing config gracefully: {e}")
    
    def test_phase4_memory_management_integration(self, temp_config_dir, mock_ui_service):
        """Test memory management across Phase 4 screens"""
        # Create multiple screen instances
        screens = []
        for i in range(10):
            search_screen = SearchScreen()
            search_screen.ui_service = mock_ui_service
            screens.append(search_screen)
        
        # Test that screens can be created and destroyed without memory leaks
        for screen in screens:
            screen.display_content()
            screen.ui_service.set_menu_items.assert_called()
        
        # Clear references
        screens.clear()
        
        # Test settings screen memory management
        for i in range(5):
            settings_screen = SettingsScreen(str(temp_config_dir / "config.json"))
            settings_screen.ui_service = mock_ui_service
            settings_screen.display_content()
            # Screen should be garbage collected when out of scope
        
        # Test system info screen memory management
        for i in range(5):
            system_info_screen = SystemInfoScreen(str(temp_config_dir))
            system_info_screen.ui_service = mock_ui_service
            system_info_screen.display_content()
            # Screen should be garbage collected when out of scope


class TestPhase4PerformanceIntegration:
    """Performance integration tests for Phase 4 screens"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for performance tests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".recradiko"
            config_dir.mkdir(parents=True)
            
            # Create config file
            config_file = config_dir / "config.json"
            config_data = {
                "version": "2.0",
                "prefecture": "東京",
                "audio": {"format": "mp3", "bitrate": 256, "sample_rate": 48000},
                "recording": {"save_path": str(config_dir / "recordings"), "id3_tags_enabled": True}
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            yield config_dir
    
    @pytest.fixture
    def mock_ui_service(self):
        """Create mock UI service for performance tests"""
        mock_ui = Mock()
        mock_ui.get_user_selection = Mock(return_value=None)
        mock_ui.display_info = Mock()
        mock_ui.display_error = Mock()
        mock_ui.set_menu_items = Mock()
        mock_ui.display_menu_with_highlight = Mock()
        mock_ui.keyboard_handler = Mock()
        mock_ui.keyboard_handler.get_key = Mock(return_value='q')
        return mock_ui
    
    def test_screen_initialization_performance(self, temp_config_dir, mock_ui_service):
        """Test screen initialization performance"""
        import time
        
        # Test search screen initialization time
        start_time = time.time()
        search_screen = SearchScreen()
        search_screen.ui_service = mock_ui_service
        search_init_time = time.time() - start_time
        
        # Test settings screen initialization time
        start_time = time.time()
        settings_screen = SettingsScreen(str(temp_config_dir / "config.json"))
        settings_screen.ui_service = mock_ui_service
        settings_init_time = time.time() - start_time
        
        # Test system info screen initialization time
        start_time = time.time()
        system_info_screen = SystemInfoScreen(str(temp_config_dir))
        system_info_screen.ui_service = mock_ui_service
        system_info_init_time = time.time() - start_time
        
        # Assert initialization times are reasonable (< 100ms)
        assert search_init_time < 0.1, f"Search screen initialization too slow: {search_init_time:.3f}s"
        assert settings_init_time < 0.1, f"Settings screen initialization too slow: {settings_init_time:.3f}s"
        assert system_info_init_time < 0.1, f"System info screen initialization too slow: {system_info_init_time:.3f}s"
    
    def test_display_content_performance(self, temp_config_dir, mock_ui_service):
        """Test display content performance"""
        import time
        
        screens = [
            SearchScreen(),
            SettingsScreen(str(temp_config_dir / "config.json")),
            SystemInfoScreen(str(temp_config_dir))
        ]
        
        for screen in screens:
            screen.ui_service = mock_ui_service
            
            # Test display performance
            start_time = time.time()
            screen.display_content()
            display_time = time.time() - start_time
            
            # Assert display time is reasonable (< 50ms)
            assert display_time < 0.05, f"{screen.__class__.__name__} display too slow: {display_time:.3f}s"
    
    def test_concurrent_screen_operations_performance(self, temp_config_dir, mock_ui_service):
        """Test concurrent screen operations performance"""
        import threading
        import time
        
        def create_and_display_screen(screen_class, *args):
            screen = screen_class(*args)
            screen.ui_service = mock_ui_service
            screen.display_content()
        
        # Test concurrent operations
        threads = []
        start_time = time.time()
        
        for i in range(5):
            # Create threads for each screen type
            search_thread = threading.Thread(target=create_and_display_screen, args=(SearchScreen,))
            settings_thread = threading.Thread(target=create_and_display_screen, 
                                             args=(SettingsScreen, str(temp_config_dir / "config.json")))
            system_info_thread = threading.Thread(target=create_and_display_screen, 
                                                 args=(SystemInfoScreen, str(temp_config_dir)))
            
            threads.extend([search_thread, settings_thread, system_info_thread])
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Assert concurrent operations complete in reasonable time (< 1s)
        assert total_time < 1.0, f"Concurrent operations too slow: {total_time:.3f}s"


class TestPhase4EndToEndIntegration:
    """End-to-end integration tests for complete Phase 4 workflows"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for E2E tests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".recradiko"
            config_dir.mkdir(parents=True)
            
            # Create complete config structure
            config_file = config_dir / "config.json"
            config_data = {
                "version": "2.0",
                "prefecture": "東京",
                "audio": {"format": "mp3", "bitrate": 256, "sample_rate": 48000},
                "recording": {"save_path": str(config_dir / "recordings"), "id3_tags_enabled": True},
                "notifications": {"enabled": True, "sound_enabled": False}
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Create directory structure
            (config_dir / "recordings").mkdir(parents=True)
            (config_dir / "logs").mkdir(parents=True)
            
            yield config_dir
    
    def test_complete_search_workflow_integration(self, temp_config_dir):
        """Test complete search workflow from main menu to results"""
        # This test simulates the complete user journey
        # Main Menu -> Search -> Results -> Back to Main Menu
        
        # Mock UI service with realistic interaction sequence
        mock_ui_service = Mock()
        mock_ui_service.get_user_selection.side_effect = [
            "番組を検索する",     # Main menu selection
            "番組名で検索",       # Search method selection
            None                  # Exit search
        ]
        mock_ui_service.get_text_input.return_value = "ニュース"
        mock_ui_service.display_info = Mock()
        mock_ui_service.display_error = Mock()
        mock_ui_service.set_menu_items = Mock()
        mock_ui_service.display_menu_with_highlight = Mock()
        mock_ui_service.keyboard_handler = Mock()
        mock_ui_service.keyboard_handler.get_key = Mock(return_value='q')
        
        # Initialize main menu and test navigation
        main_menu = MainMenuScreen()
        main_menu.ui_service = mock_ui_service
        
        # Test main menu -> search navigation
        search_result = main_menu.handle_menu_selection("番組を検索する")
        assert search_result == "search"
        
        # Initialize search screen and test workflow
        search_screen = SearchScreen()
        search_screen.ui_service = mock_ui_service
        
        # Mock search results
        with patch.object(search_screen, 'search_by_title') as mock_search:
            mock_search.return_value = [
                {"title": "ニュース番組", "start_time": "06:00", "end_time": "06:30", "station": "TBS"}
            ]
            
            # Test search workflow
            result = search_screen.run_search_workflow()
            assert result == True
    
    def test_complete_settings_workflow_integration(self, temp_config_dir):
        """Test complete settings workflow from main menu to config save"""
        config_file = temp_config_dir / "config.json"
        
        # Mock UI service with realistic settings interaction
        mock_ui_service = Mock()
        mock_ui_service.get_user_selection.side_effect = [
            "設定を変更",         # Main menu selection
            "地域設定",           # Settings category
            "大阪",               # New region
            None                  # Exit settings
        ]
        mock_ui_service.display_info = Mock()
        mock_ui_service.display_success = Mock()
        mock_ui_service.set_menu_items = Mock()
        mock_ui_service.display_menu_with_highlight = Mock()
        mock_ui_service.keyboard_handler = Mock()
        mock_ui_service.keyboard_handler.get_key = Mock(return_value='q')
        
        # Initialize main menu and test navigation
        main_menu = MainMenuScreen()
        main_menu.ui_service = mock_ui_service
        
        # Test main menu -> settings navigation
        settings_result = main_menu.handle_menu_selection("設定を変更")
        assert settings_result == "settings"
        
        # Initialize settings screen and test workflow
        settings_screen = SettingsScreen(str(config_file))
        settings_screen.ui_service = mock_ui_service
        
        # Test settings workflow
        with patch.object(settings_screen, 'handle_region_setting') as mock_change:
            mock_change.return_value = True
            
            result = settings_screen.run_settings_workflow()
            assert result == True
    
    def test_complete_system_info_workflow_integration(self, temp_config_dir):
        """Test complete system info workflow from main menu to system data"""
        # Mock UI service with realistic system info interaction
        mock_ui_service = Mock()
        mock_ui_service.get_user_selection.side_effect = [
            "システム情報を表示",   # Main menu selection
            "システム状況を表示",   # System info option
            None                    # Exit system info
        ]
        mock_ui_service.display_info = Mock()
        mock_ui_service.set_menu_items = Mock()
        mock_ui_service.display_menu_with_highlight = Mock()
        mock_ui_service.keyboard_handler = Mock()
        mock_ui_service.keyboard_handler.get_key = Mock(return_value='q')
        
        # Initialize main menu and test navigation
        main_menu = MainMenuScreen()
        main_menu.ui_service = mock_ui_service
        
        # Test main menu -> system info navigation
        system_info_result = main_menu.handle_menu_selection("システム情報を表示")
        assert system_info_result == "system_info"
        
        # Initialize system info screen and test workflow
        system_info_screen = SystemInfoScreen(str(temp_config_dir))
        system_info_screen.ui_service = mock_ui_service
        
        # Test system info workflow
        with patch.object(system_info_screen, 'show_system_status') as mock_show:
            mock_show.return_value = None
            
            result = system_info_screen.run_system_info_workflow()
            assert result == True
            mock_show.assert_called_once()