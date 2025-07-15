"""
Test SearchScreen implementation

Tests the program search functionality including:
- Search method selection (title, performer, time, station, date)
- Keyword input handling
- Search result display with pagination
- Selection and navigation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timedelta
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.screens.search_screen import SearchScreen
from src.program_info import ProgramInfo


class TestSearchScreen:
    """Test SearchScreen functionality"""
    
    @pytest.fixture
    def search_screen(self):
        """Create SearchScreen instance for testing"""
        with patch('src.ui.screens.search_screen.UIService') as mock_ui_service, \
             patch('src.ui.screens.search_screen.ProgramHistoryManager') as mock_history_manager:
            
            screen = SearchScreen()
            screen.ui_service = mock_ui_service.return_value
            screen.program_history_manager = mock_history_manager.return_value
            
            return screen
    
    def test_search_screen_initialization(self, search_screen):
        """Test SearchScreen initialization"""
        assert search_screen.title == "番組検索"
        assert len(search_screen.search_methods) == 5
        assert "番組名で検索" in search_screen.search_methods
        assert "出演者で検索" in search_screen.search_methods
        assert "時間帯で検索" in search_screen.search_methods
        assert "放送局で絞り込み" in search_screen.search_methods
        assert "日付範囲で絞り込み" in search_screen.search_methods
    
    def test_display_search_menu(self, search_screen):
        """Test search menu display"""
        search_screen.ui_service.set_menu_items = Mock()
        
        # Test display
        search_screen.display_content()
        
        # Verify menu items were set
        search_screen.ui_service.set_menu_items.assert_called_once()
        call_args = search_screen.ui_service.set_menu_items.call_args[0][0]
        assert len(call_args) == 5
        assert "番組名で検索" in call_args
    
    def test_search_by_title(self, search_screen):
        """Test title search functionality"""
        # Mock user input
        search_screen.ui_service.get_text_input = Mock(return_value="森本毅郎")
        
        # Mock search results
        mock_programs = [
            ProgramInfo(
                program_id="TBS_20250714_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 14, 6, 0),
                end_time=datetime(2025, 7, 14, 8, 30),
                is_timefree_available=True
            )
        ]
        search_screen.program_history_manager.search_programs = Mock(return_value=mock_programs)
        
        # Execute search
        result = search_screen.search_by_title()
        
        # Verify search was called with correct parameters
        search_screen.program_history_manager.search_programs.assert_called_once_with("森本毅郎")
        assert result == mock_programs
    
    def test_search_by_performer(self, search_screen):
        """Test performer search functionality"""
        # Mock user input
        search_screen.ui_service.get_text_input = Mock(return_value="森本毅郎")
        
        # Mock search results
        mock_programs = [
            ProgramInfo(
                program_id="TBS_20250714_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 14, 6, 0),
                end_time=datetime(2025, 7, 14, 8, 30),
                performers=["森本毅郎"],
                is_timefree_available=True
            )
        ]
        search_screen.program_history_manager.search_programs = Mock(return_value=mock_programs)
        
        # Execute search
        result = search_screen.search_by_performer()
        
        # Verify search was called
        search_screen.program_history_manager.search_programs.assert_called_once_with("森本毅郎")
        assert result == mock_programs
    
    def test_search_by_time_range(self, search_screen):
        """Test time range search functionality"""
        # Mock user input for time range
        search_screen.ui_service.get_text_input = Mock(side_effect=["06:00", "08:30"])
        
        # Mock search results
        mock_programs = [
            ProgramInfo(
                program_id="TBS_20250714_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 14, 6, 0),
                end_time=datetime(2025, 7, 14, 8, 30),
                is_timefree_available=True
            )
        ]
        search_screen.program_history_manager.search_programs = Mock(return_value=mock_programs)
        
        # Execute search
        result = search_screen.search_by_time_range()
        
        # Verify search was called
        search_screen.program_history_manager.search_programs.assert_called_once()
        assert result == mock_programs
    
    def test_search_by_station(self, search_screen):
        """Test station filter search functionality"""
        # Mock station selection
        search_screen.ui_service.get_user_selection = Mock(return_value=1)  # Select first station
        
        # Mock available stations
        mock_stations = [
            {"id": "TBS", "name": "TBSラジオ"},
            {"id": "QRR", "name": "文化放送"},
            {"id": "LFR", "name": "ニッポン放送"}
        ]
        search_screen.program_history_manager.get_available_stations = Mock(return_value=mock_stations)
        
        # Mock search results
        mock_programs = [
            ProgramInfo(
                program_id="TBS_20250714_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 14, 6, 0),
                end_time=datetime(2025, 7, 14, 8, 30),
                is_timefree_available=True
            )
        ]
        search_screen.program_history_manager.search_programs = Mock(return_value=mock_programs)
        
        # Execute search
        result = search_screen.search_by_station()
        
        # Verify search was called with station filter
        search_screen.program_history_manager.search_programs.assert_called_once()
        assert result == mock_programs
    
    def test_search_by_date_range(self, search_screen):
        """Test date range search functionality"""
        # Mock date selection
        start_date = date(2025, 7, 10)
        end_date = date(2025, 7, 15)
        search_screen.ui_service.get_date_input = Mock(side_effect=[start_date, end_date])
        
        # Mock search results
        mock_programs = [
            ProgramInfo(
                program_id="TBS_20250714_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 14, 6, 0),
                end_time=datetime(2025, 7, 14, 8, 30),
                is_timefree_available=True
            )
        ]
        search_screen.program_history_manager.search_programs = Mock(return_value=mock_programs)
        
        # Execute search
        result = search_screen.search_by_date_range()
        
        # Verify search was called with date range
        search_screen.program_history_manager.search_programs.assert_called_once()
        assert result == mock_programs
    
    def test_display_search_results(self, search_screen):
        """Test search results display"""
        # Mock search results
        mock_programs = [
            ProgramInfo(
                program_id="TBS_20250714_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 14, 6, 0),
                end_time=datetime(2025, 7, 14, 8, 30),
                is_timefree_available=True
            ),
            ProgramInfo(
                program_id="TBS_20250713_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 13, 6, 0),
                end_time=datetime(2025, 7, 13, 8, 30),
                is_timefree_available=True
            )
        ]
        
        # Mock UI service
        search_screen.ui_service.set_menu_items = Mock()
        search_screen.ui_service.get_user_selection = Mock(return_value=1)  # First result (1-indexed)
        
        # Execute display
        selected_program = search_screen.display_search_results(mock_programs, "森本毅郎")
        
        # Verify results were displayed
        search_screen.ui_service.set_menu_items.assert_called_once()
        call_args = search_screen.ui_service.set_menu_items.call_args[0][0]
        assert len(call_args) >= 2  # At least 2 programs
        assert "森本毅郎・スタンバイ!" in call_args[0]
        
        # Verify selected program
        assert selected_program == mock_programs[0]
    
    def test_search_results_pagination(self, search_screen):
        """Test search results pagination"""
        # Create many mock programs (more than page size)
        mock_programs = []
        for i in range(25):  # More than typical page size
            mock_programs.append(ProgramInfo(
                program_id=f"TBS_2025071{i:02d}_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title=f"テスト番組 {i+1}",
                start_time=datetime(2025, 7, 14, 6, 0),
                end_time=datetime(2025, 7, 14, 8, 30),
                is_timefree_available=True
            ))
        
        # Mock UI service with pagination
        search_screen.ui_service.set_menu_items = Mock()
        search_screen.ui_service.get_user_selection = Mock(return_value=1)  # Select first item
        
        # Execute display
        selected_program = search_screen.display_search_results(mock_programs, "テスト")
        
        # Verify pagination was handled
        search_screen.ui_service.set_menu_items.assert_called_once()
        call_args = search_screen.ui_service.set_menu_items.call_args[0][0]
        
        # Should have pagination controls
        assert len(call_args) <= 15  # Page size limit
        assert selected_program == mock_programs[0]
    
    def test_search_no_results(self, search_screen):
        """Test search with no results"""
        # Mock empty search results
        search_screen.program_history_manager.search_programs = Mock(return_value=[])
        search_screen.ui_service.get_text_input = Mock(return_value="存在しない番組")
        
        # Execute search
        result = search_screen.search_by_title()
        
        # Verify empty results
        assert result == []
        search_screen.program_history_manager.search_programs.assert_called_once_with("存在しない番組")
    
    def test_search_error_handling(self, search_screen):
        """Test search error handling"""
        # Mock search exception
        search_screen.program_history_manager.search_programs = Mock(side_effect=Exception("Search error"))
        search_screen.ui_service.get_text_input = Mock(return_value="テスト")
        search_screen.ui_service.display_error = Mock()
        
        # Execute search
        result = search_screen.search_by_title()
        
        # Verify error handling
        assert result == []
        search_screen.ui_service.display_error.assert_called_once()
    
    def test_run_search_workflow(self, search_screen):
        """Test complete search workflow"""
        # Mock search method selection
        search_screen.ui_service.get_user_selection = Mock(return_value=1)  # Title search (1-indexed)
        
        # Mock search execution
        mock_programs = [
            ProgramInfo(
                program_id="TBS_20250714_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 14, 6, 0),
                end_time=datetime(2025, 7, 14, 8, 30),
                is_timefree_available=True
            )
        ]
        search_screen.search_by_title = Mock(return_value=mock_programs)
        search_screen.display_search_results = Mock(return_value=mock_programs[0])
        
        # Execute workflow
        result = search_screen.run_search_workflow()
        
        # Verify workflow execution
        search_screen.search_by_title.assert_called_once()
        search_screen.display_search_results.assert_called_once_with(mock_programs, None)
        assert result == mock_programs[0]
    
    def test_search_workflow_cancellation(self, search_screen):
        """Test search workflow cancellation"""
        # Mock search method cancellation
        search_screen.ui_service.get_user_selection = Mock(return_value=None)  # Cancel
        
        # Execute workflow
        result = search_screen.run_search_workflow()
        
        # Verify cancellation
        assert result is None