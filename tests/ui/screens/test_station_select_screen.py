"""
Test for StationSelectScreen class

Tests station selection screen with keyboard navigation for RecRadiko.
Following TDD approach: tests first, then implementation.
"""

import pytest
from unittest.mock import Mock, patch, call
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.ui.screens.station_select_screen import StationSelectScreen
from src.ui.services.ui_service import UIService


class TestStationSelectScreen:
    """StationSelectScreen unit tests"""
    
    @pytest.fixture
    def station_select_screen(self):
        """Create StationSelectScreen instance for testing"""
        return StationSelectScreen()
        
    @pytest.fixture
    def mock_ui_service(self):
        """Create mock UIService"""
        return Mock(spec=UIService)
        
    @pytest.fixture
    def mock_stations(self):
        """Create mock station data"""
        return [
            {"id": "TBS", "name": "TBSラジオ", "logo": "https://example.com/tbs.jpg"},
            {"id": "QRR", "name": "文化放送", "logo": "https://example.com/qrr.jpg"},
            {"id": "LFR", "name": "ニッポン放送", "logo": "https://example.com/lfr.jpg"},
            {"id": "RN1", "name": "ラジオNIKKEI第1", "logo": "https://example.com/rn1.jpg"},
            {"id": "RN2", "name": "ラジオNIKKEI第2", "logo": "https://example.com/rn2.jpg"}
        ]
        
    def test_station_select_screen_initialization(self, station_select_screen):
        """Test StationSelectScreen initialization"""
        assert station_select_screen is not None
        assert station_select_screen.title == "放送局選択"
        assert hasattr(station_select_screen, 'stations')
        assert hasattr(station_select_screen, 'current_area')
        assert station_select_screen.stations == []
        
    def test_load_stations_success(self, station_select_screen, mock_stations):
        """Test loading stations successfully"""
        with patch.object(station_select_screen, '_fetch_stations_from_api') as mock_fetch:
            mock_fetch.return_value = mock_stations
            
            result = station_select_screen.load_stations("JP13")
            
            assert result == True
            assert len(station_select_screen.stations) == 5
            assert station_select_screen.current_area == "JP13"
            mock_fetch.assert_called_once_with("JP13")
            
    def test_load_stations_failure(self, station_select_screen):
        """Test loading stations with API failure"""
        with patch.object(station_select_screen, '_fetch_stations_from_api') as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")
            
            result = station_select_screen.load_stations("JP13")
            
            assert result == False
            assert len(station_select_screen.stations) == 0
            
    def test_display_content_with_stations(self, station_select_screen, mock_ui_service, mock_stations):
        """Test displaying content with stations loaded"""
        station_select_screen.ui_service = mock_ui_service
        station_select_screen.stations = mock_stations
        station_select_screen.current_area = "JP13"
        
        station_select_screen.display_content()
        
        # Should display station names
        expected_names = ["TBSラジオ", "文化放送", "ニッポン放送", "ラジオNIKKEI第1", "ラジオNIKKEI第2"]
        mock_ui_service.set_menu_items.assert_called_once_with(expected_names)
        mock_ui_service.display_menu_with_highlight.assert_called_once()
        
    def test_display_content_no_stations(self, station_select_screen, mock_ui_service):
        """Test displaying content with no stations"""
        station_select_screen.ui_service = mock_ui_service
        station_select_screen.stations = []
        mock_keyboard_handler = Mock()
        mock_ui_service.keyboard_handler = mock_keyboard_handler
        
        station_select_screen.display_content()
        
        # Should show error message and wait for key
        mock_ui_service.display_error.assert_called()
        mock_keyboard_handler.get_key.assert_called_once()
        
    def test_run_station_selection_loop_success(self, station_select_screen, mock_ui_service, mock_stations):
        """Test running station selection loop with successful selection"""
        station_select_screen.ui_service = mock_ui_service
        station_select_screen.stations = mock_stations
        mock_ui_service.get_user_selection.return_value = "TBSラジオ"
        
        result = station_select_screen.run_station_selection_loop()
        
        expected_station = {"id": "TBS", "name": "TBSラジオ", "logo": "https://example.com/tbs.jpg"}
        assert result == expected_station
        
    def test_run_station_selection_loop_cancelled(self, station_select_screen, mock_ui_service, mock_stations):
        """Test running station selection loop when cancelled"""
        station_select_screen.ui_service = mock_ui_service
        station_select_screen.stations = mock_stations
        mock_ui_service.get_user_selection.return_value = None  # User cancelled
        
        result = station_select_screen.run_station_selection_loop()
        
        assert result is None
        
    def test_get_station_by_name(self, station_select_screen, mock_stations):
        """Test getting station by name"""
        station_select_screen.stations = mock_stations
        
        station = station_select_screen.get_station_by_name("TBSラジオ")
        
        expected = {"id": "TBS", "name": "TBSラジオ", "logo": "https://example.com/tbs.jpg"}
        assert station == expected
        
    def test_get_station_by_name_not_found(self, station_select_screen, mock_stations):
        """Test getting station by name when not found"""
        station_select_screen.stations = mock_stations
        
        station = station_select_screen.get_station_by_name("存在しない放送局")
        
        assert station is None
        
    def test_fetch_stations_from_api(self, station_select_screen):
        """Test fetching stations from API"""
        mock_program_info_manager = Mock()
        mock_program_info_manager.get_stations.return_value = [
            {"id": "TBS", "name": "TBSラジオ", "logo": "https://example.com/tbs.jpg"}
        ]
        
        with patch('src.ui.screens.station_select_screen.ProgramInfoManager', return_value=mock_program_info_manager):
            stations = station_select_screen._fetch_stations_from_api("JP13")
            
            assert len(stations) == 1
            assert stations[0]["id"] == "TBS"
            mock_program_info_manager.get_stations.assert_called_once()
            
    def test_format_station_display_name(self, station_select_screen):
        """Test formatting station display name"""
        station = {"id": "TBS", "name": "TBSラジオ", "logo": "https://example.com/tbs.jpg"}
        
        display_name = station_select_screen.format_station_display_name(station)
        
        assert display_name == "TBSラジオ (TBS)"
        
    def test_refresh_stations(self, station_select_screen, mock_ui_service):
        """Test refreshing station list"""
        station_select_screen.ui_service = mock_ui_service
        station_select_screen.current_area = "JP13"
        
        with patch.object(station_select_screen, 'load_stations') as mock_load:
            mock_load.return_value = True
            
            result = station_select_screen.refresh_stations()
            
            assert result == True
            mock_load.assert_called_once_with("JP13")
            
    def test_show_station_info(self, station_select_screen, mock_ui_service, mock_stations):
        """Test showing station information"""
        station_select_screen.ui_service = mock_ui_service
        station_select_screen.stations = mock_stations
        mock_keyboard_handler = Mock()
        mock_ui_service.keyboard_handler = mock_keyboard_handler
        
        station = mock_stations[0]  # TBSラジオ
        station_select_screen.show_station_info(station)
        
        # Should display station info and wait for key
        mock_keyboard_handler.get_key.assert_called_once()
        
    def test_change_area(self, station_select_screen, mock_ui_service):
        """Test changing area"""
        station_select_screen.ui_service = mock_ui_service
        mock_ui_service.get_user_selection.return_value = "大阪"
        
        with patch.object(station_select_screen, 'load_stations') as mock_load:
            mock_load.return_value = True
            
            result = station_select_screen.change_area()
            
            assert result == True
            # Should load stations for the new area
            mock_load.assert_called()
            
    def test_get_area_options(self, station_select_screen):
        """Test getting area options"""
        options = station_select_screen.get_area_options()
        
        # Should return list of area names
        assert isinstance(options, list)
        assert len(options) > 0
        assert "東京都" in options or "北海道" in options  # Should contain major areas
        
    def test_on_back_navigation(self, station_select_screen):
        """Test back navigation handling"""
        # Should return to main menu
        result = station_select_screen.on_back()
        # on_back is inherited from ScreenBase and doesn't return anything by default
        # This test just verifies no exceptions are raised
        assert result is None
        
    def test_display_loading_message(self, station_select_screen):
        """Test displaying loading message"""
        # This method should display loading indication
        station_select_screen.display_loading_message()
        # No specific assertions - just verify no exceptions
        
    def test_display_no_stations_message(self, station_select_screen, mock_ui_service):
        """Test displaying no stations message"""
        station_select_screen.ui_service = mock_ui_service
        mock_keyboard_handler = Mock()
        mock_ui_service.keyboard_handler = mock_keyboard_handler
        
        station_select_screen.display_no_stations_message()
        
        # Should display error and wait for key
        mock_ui_service.display_error.assert_called()
        mock_keyboard_handler.get_key.assert_called_once()