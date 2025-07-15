"""
Test for DateSelectScreen class

Tests date selection screen with keyboard navigation for RecRadiko timefree recording.
Following TDD approach: tests first, then implementation.
"""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.ui.screens.date_select_screen import DateSelectScreen
from src.ui.services.ui_service import UIService


class TestDateSelectScreen:
    """DateSelectScreen unit tests"""
    
    @pytest.fixture
    def date_select_screen(self):
        """Create DateSelectScreen instance for testing"""
        return DateSelectScreen()
        
    @pytest.fixture
    def mock_ui_service(self):
        """Create mock UIService"""
        return Mock(spec=UIService)
        
    @pytest.fixture
    def sample_station(self):
        """Create sample station data"""
        return {
            "id": "TBS",
            "name": "TBSラジオ",
            "logo": "https://example.com/tbs.jpg"
        }
        
    def test_date_select_screen_initialization(self, date_select_screen):
        """Test DateSelectScreen initialization"""
        assert date_select_screen is not None
        assert date_select_screen.title == "録音日付選択"
        assert hasattr(date_select_screen, 'selected_station')
        assert hasattr(date_select_screen, 'available_dates')
        assert date_select_screen.selected_station is None
        assert date_select_screen.available_dates == []
        
    def test_set_station(self, date_select_screen, sample_station):
        """Test setting selected station"""
        date_select_screen.set_station(sample_station)
        
        assert date_select_screen.selected_station == sample_station
        assert date_select_screen.title == "録音日付選択 - TBSラジオ"
        
    def test_calculate_available_dates(self, date_select_screen):
        """Test calculating available dates for timefree recording"""
        today = datetime.now().date()
        
        available_dates = date_select_screen.calculate_available_dates()
        
        # Should return 7 days (including today and 6 days back)
        assert len(available_dates) == 7
        
        # Should include today
        assert today in available_dates
        
        # Should include 6 days back
        six_days_ago = today - timedelta(days=6)
        assert six_days_ago in available_dates
        
        # Should be sorted in descending order (newest first)
        assert available_dates == sorted(available_dates, reverse=True)
        
    def test_format_date_for_display(self, date_select_screen):
        """Test formatting date for display"""
        test_date = datetime(2025, 7, 15).date()
        
        formatted = date_select_screen.format_date_for_display(test_date)
        
        # Should include date, day of week, and relative description
        assert "2025-07-15" in formatted
        assert "火" in formatted  # Tuesday in Japanese
        
    def test_is_date_available_valid(self, date_select_screen):
        """Test checking if date is available for timefree recording"""
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        assert date_select_screen.is_date_available(today) == True
        assert date_select_screen.is_date_available(yesterday) == True
        
    def test_is_date_available_too_old(self, date_select_screen):
        """Test checking date that's too old"""
        old_date = datetime.now().date() - timedelta(days=8)
        
        assert date_select_screen.is_date_available(old_date) == False
        
    def test_is_date_available_future(self, date_select_screen):
        """Test checking future date"""
        future_date = datetime.now().date() + timedelta(days=1)
        
        assert date_select_screen.is_date_available(future_date) == False
        
    def test_display_content_with_station(self, date_select_screen, mock_ui_service, sample_station):
        """Test displaying content with station set"""
        date_select_screen.ui_service = mock_ui_service
        date_select_screen.set_station(sample_station)
        date_select_screen.available_dates = date_select_screen.calculate_available_dates()
        
        date_select_screen.display_content()
        
        # Should set menu items with formatted dates
        mock_ui_service.set_menu_items.assert_called_once()
        args = mock_ui_service.set_menu_items.call_args[0][0]
        assert len(args) == 7  # 7 available dates
        
        mock_ui_service.display_menu_with_highlight.assert_called_once()
        
    def test_display_content_no_station(self, date_select_screen, mock_ui_service):
        """Test displaying content without station set"""
        date_select_screen.ui_service = mock_ui_service
        mock_keyboard_handler = Mock()
        mock_ui_service.keyboard_handler = mock_keyboard_handler
        
        date_select_screen.display_content()
        
        # Should show error message
        mock_ui_service.display_error.assert_called()
        mock_keyboard_handler.get_key.assert_called_once()
        
    def test_run_date_selection_loop_success(self, date_select_screen, mock_ui_service, sample_station):
        """Test running date selection loop with successful selection"""
        date_select_screen.ui_service = mock_ui_service
        date_select_screen.set_station(sample_station)
        date_select_screen.available_dates = date_select_screen.calculate_available_dates()
        
        today = datetime.now().date()
        formatted_today = date_select_screen.format_date_for_display(today)
        mock_ui_service.get_user_selection.return_value = formatted_today
        
        result = date_select_screen.run_date_selection_loop()
        
        assert result == today
        
    def test_run_date_selection_loop_cancelled(self, date_select_screen, mock_ui_service, sample_station):
        """Test running date selection loop when cancelled"""
        date_select_screen.ui_service = mock_ui_service
        date_select_screen.set_station(sample_station)
        mock_ui_service.get_user_selection.return_value = None  # User cancelled
        
        result = date_select_screen.run_date_selection_loop()
        
        assert result is None
        
    def test_parse_date_from_display_string(self, date_select_screen):
        """Test parsing date from display string"""
        today = datetime.now().date()
        formatted = date_select_screen.format_date_for_display(today)
        
        parsed_date = date_select_screen.parse_date_from_display_string(formatted)
        
        assert parsed_date == today
        
    def test_parse_date_from_display_string_invalid(self, date_select_screen):
        """Test parsing invalid date string"""
        invalid_string = "Invalid Date String"
        
        result = date_select_screen.parse_date_from_display_string(invalid_string)
        
        assert result is None
        
    def test_get_relative_date_description_today(self, date_select_screen):
        """Test getting relative description for today"""
        today = datetime.now().date()
        
        description = date_select_screen.get_relative_date_description(today)
        
        assert "今日" in description
        
    def test_get_relative_date_description_yesterday(self, date_select_screen):
        """Test getting relative description for yesterday"""
        yesterday = datetime.now().date() - timedelta(days=1)
        
        description = date_select_screen.get_relative_date_description(yesterday)
        
        assert "昨日" in description
        
    def test_get_relative_date_description_other(self, date_select_screen):
        """Test getting relative description for other dates"""
        three_days_ago = datetime.now().date() - timedelta(days=3)
        
        description = date_select_screen.get_relative_date_description(three_days_ago)
        
        assert "3日前" in description
        
    def test_refresh_available_dates(self, date_select_screen):
        """Test refreshing available dates"""
        old_dates = [datetime(2025, 1, 1).date()]
        date_select_screen.available_dates = old_dates
        
        date_select_screen.refresh_available_dates()
        
        # Should have recalculated dates
        assert len(date_select_screen.available_dates) == 7
        assert datetime.now().date() in date_select_screen.available_dates
        
    def test_show_date_info(self, date_select_screen, mock_ui_service):
        """Test showing date information"""
        date_select_screen.ui_service = mock_ui_service
        mock_keyboard_handler = Mock()
        mock_ui_service.keyboard_handler = mock_keyboard_handler
        
        today = datetime.now().date()
        date_select_screen.show_date_info(today)
        
        # Should display info and wait for key
        mock_keyboard_handler.get_key.assert_called_once()
        
    def test_get_timefree_period_info(self, date_select_screen):
        """Test getting timefree period information"""
        info = date_select_screen.get_timefree_period_info()
        
        assert "タイムフリー" in info
        assert "7日間" in info or "1週間" in info
        
    def test_handle_shortcut_key_info(self, date_select_screen, mock_ui_service):
        """Test handling info shortcut key"""
        date_select_screen.ui_service = mock_ui_service
        mock_ui_service.get_current_item.return_value = "2025-07-15 (火) - 今日"
        
        with patch.object(date_select_screen, 'show_date_info') as mock_show_info:
            result = date_select_screen.handle_shortcut_key('i')
            
            mock_show_info.assert_called_once()
            assert result == True
            
    def test_handle_shortcut_key_refresh(self, date_select_screen):
        """Test handling refresh shortcut key"""
        with patch.object(date_select_screen, 'refresh_available_dates') as mock_refresh:
            result = date_select_screen.handle_shortcut_key('r')
            
            mock_refresh.assert_called_once()
            assert result == True
            
    def test_handle_shortcut_key_unknown(self, date_select_screen):
        """Test handling unknown shortcut key"""
        result = date_select_screen.handle_shortcut_key('x')
        
        assert result == False
        
    def test_validate_selected_date(self, date_select_screen):
        """Test validating selected date"""
        today = datetime.now().date()
        old_date = today - timedelta(days=10)
        
        assert date_select_screen.validate_selected_date(today) == True
        assert date_select_screen.validate_selected_date(old_date) == False