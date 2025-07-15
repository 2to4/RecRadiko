"""
Test for ProgramSelectScreen class

Tests program selection screen with keyboard navigation for RecRadiko timefree recording.
Following TDD approach: tests first, then implementation.
"""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta, date
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.ui.screens.program_select_screen import ProgramSelectScreen
from src.ui.services.ui_service import UIService


class TestProgramSelectScreen:
    """ProgramSelectScreen unit tests"""
    
    @pytest.fixture
    def program_select_screen(self):
        """Create ProgramSelectScreen instance for testing"""
        return ProgramSelectScreen()
        
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
        
    @pytest.fixture
    def sample_date(self):
        """Create sample date"""
        return datetime(2025, 7, 15).date()
        
    @pytest.fixture
    def mock_programs(self):
        """Create mock program data"""
        return [
            {
                "title": "森本毅郎・スタンバイ!",
                "start_time": "06:30",
                "end_time": "09:00",
                "performer": "森本毅郎",
                "description": "朝の情報番組"
            },
            {
                "title": "荻上チキ・Session",
                "start_time": "22:00",
                "end_time": "23:55",
                "performer": "荻上チキ",
                "description": "ニュース情報番組"
            },
            {
                "title": "爆笑問題の日曜サンデー",
                "start_time": "13:00",
                "end_time": "15:00",
                "performer": "爆笑問題",
                "description": "バラエティ番組"
            }
        ]
        
    def test_program_select_screen_initialization(self, program_select_screen):
        """Test ProgramSelectScreen initialization"""
        assert program_select_screen is not None
        assert program_select_screen.title == "番組選択"
        assert hasattr(program_select_screen, 'selected_station')
        assert hasattr(program_select_screen, 'selected_date')
        assert hasattr(program_select_screen, 'programs')
        assert hasattr(program_select_screen, 'current_page')
        assert hasattr(program_select_screen, 'items_per_page')
        assert program_select_screen.selected_station is None
        assert program_select_screen.selected_date is None
        assert program_select_screen.programs == []
        assert program_select_screen.current_page == 0
        assert program_select_screen.items_per_page == 10
        
    def test_set_station_and_date(self, program_select_screen, sample_station, sample_date):
        """Test setting selected station and date"""
        program_select_screen.set_station_and_date(sample_station, sample_date)
        
        assert program_select_screen.selected_station == sample_station
        assert program_select_screen.selected_date == sample_date
        assert program_select_screen.title == "番組選択 - TBSラジオ (2025-07-15)"
        
    def test_load_programs_success(self, program_select_screen, sample_station, sample_date, mock_programs):
        """Test loading programs successfully"""
        program_select_screen.set_station_and_date(sample_station, sample_date)
        
        with patch.object(program_select_screen, '_fetch_programs_from_api') as mock_fetch:
            mock_fetch.return_value = mock_programs
            
            result = program_select_screen.load_programs()
            
            assert result == True
            assert len(program_select_screen.programs) == 3
            mock_fetch.assert_called_once_with(sample_station["id"], sample_date)
            
    def test_load_programs_failure(self, program_select_screen, sample_station, sample_date):
        """Test loading programs with API failure"""
        program_select_screen.set_station_and_date(sample_station, sample_date)
        
        with patch.object(program_select_screen, '_fetch_programs_from_api') as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")
            
            result = program_select_screen.load_programs()
            
            assert result == False
            assert len(program_select_screen.programs) == 0
            
    def test_display_content_with_programs(self, program_select_screen, mock_ui_service, 
                                          sample_station, sample_date, mock_programs):
        """Test displaying content with programs loaded"""
        program_select_screen.ui_service = mock_ui_service
        program_select_screen.set_station_and_date(sample_station, sample_date)
        program_select_screen.programs = mock_programs
        
        program_select_screen.display_content()
        
        # Should display program titles
        expected_displays = [
            "06:30-09:00 森本毅郎・スタンバイ!",
            "22:00-23:55 荻上チキ・Session",
            "13:00-15:00 爆笑問題の日曜サンデー"
        ]
        mock_ui_service.set_menu_items.assert_called_once_with(expected_displays)
        mock_ui_service.display_menu_with_highlight.assert_called_once()
        
    def test_display_content_no_programs(self, program_select_screen, mock_ui_service,
                                        sample_station, sample_date):
        """Test displaying content with no programs"""
        program_select_screen.ui_service = mock_ui_service
        program_select_screen.set_station_and_date(sample_station, sample_date)
        program_select_screen.programs = []
        mock_keyboard_handler = Mock()
        mock_ui_service.keyboard_handler = mock_keyboard_handler
        
        program_select_screen.display_content()
        
        # Should show error message and wait for key
        mock_ui_service.display_error.assert_called()
        mock_keyboard_handler.get_key.assert_called_once()
        
    def test_display_content_no_selection(self, program_select_screen, mock_ui_service):
        """Test displaying content without station/date set"""
        program_select_screen.ui_service = mock_ui_service
        mock_keyboard_handler = Mock()
        mock_ui_service.keyboard_handler = mock_keyboard_handler
        
        program_select_screen.display_content()
        
        # Should show error message
        mock_ui_service.display_error.assert_called()
        mock_keyboard_handler.get_key.assert_called_once()
        
    def test_run_program_selection_loop_success(self, program_select_screen, mock_ui_service,
                                               sample_station, sample_date, mock_programs):
        """Test running program selection loop with successful selection"""
        program_select_screen.ui_service = mock_ui_service
        program_select_screen.set_station_and_date(sample_station, sample_date)
        program_select_screen.programs = mock_programs
        
        selected_display = "06:30-09:00 森本毅郎・スタンバイ!"
        mock_ui_service.get_user_selection.return_value = selected_display
        
        result = program_select_screen.run_program_selection_loop()
        
        expected_program = mock_programs[0]
        assert result == expected_program
        
    def test_run_program_selection_loop_cancelled(self, program_select_screen, mock_ui_service,
                                                 sample_station, sample_date, mock_programs):
        """Test running program selection loop when cancelled"""
        program_select_screen.ui_service = mock_ui_service
        program_select_screen.set_station_and_date(sample_station, sample_date)
        program_select_screen.programs = mock_programs
        mock_ui_service.get_user_selection.return_value = None  # User cancelled
        
        result = program_select_screen.run_program_selection_loop()
        
        assert result is None
        
    def test_format_program_for_display(self, program_select_screen, mock_programs):
        """Test formatting program for display"""
        program = mock_programs[0]
        
        display_text = program_select_screen.format_program_for_display(program)
        
        assert display_text == "06:30-09:00 森本毅郎・スタンバイ!"
        
    def test_get_program_by_display_text(self, program_select_screen, mock_programs):
        """Test getting program by display text"""
        program_select_screen.programs = mock_programs
        display_text = "06:30-09:00 森本毅郎・スタンバイ!"
        
        program = program_select_screen.get_program_by_display_text(display_text)
        
        expected = mock_programs[0]
        assert program == expected
        
    def test_get_program_by_display_text_not_found(self, program_select_screen, mock_programs):
        """Test getting program by display text when not found"""
        program_select_screen.programs = mock_programs
        display_text = "存在しない番組"
        
        program = program_select_screen.get_program_by_display_text(display_text)
        
        assert program is None
        
    def test_pagination_get_current_page_programs(self, program_select_screen):
        """Test getting current page programs with pagination"""
        # Create 25 mock programs (more than one page)
        programs = []
        for i in range(25):
            programs.append({
                "title": f"番組{i+1}",
                "start_time": f"{i:02d}:00",
                "end_time": f"{i:02d}:30",
                "performer": f"出演者{i+1}",
                "description": f"説明{i+1}"
            })
        
        program_select_screen.programs = programs
        program_select_screen.items_per_page = 10
        
        # Test page 0 (first page)
        program_select_screen.current_page = 0
        page_programs = program_select_screen.get_current_page_programs()
        assert len(page_programs) == 10
        assert page_programs[0]["title"] == "番組1"
        assert page_programs[9]["title"] == "番組10"
        
        # Test page 1 (second page)
        program_select_screen.current_page = 1
        page_programs = program_select_screen.get_current_page_programs()
        assert len(page_programs) == 10
        assert page_programs[0]["title"] == "番組11"
        assert page_programs[9]["title"] == "番組20"
        
        # Test page 2 (last page, partial)
        program_select_screen.current_page = 2
        page_programs = program_select_screen.get_current_page_programs()
        assert len(page_programs) == 5
        assert page_programs[0]["title"] == "番組21"
        assert page_programs[4]["title"] == "番組25"
        
    def test_pagination_get_total_pages(self, program_select_screen):
        """Test getting total pages"""
        # Test with 25 programs, 10 per page = 3 pages
        program_select_screen.programs = [{"title": f"番組{i}"} for i in range(25)]
        program_select_screen.items_per_page = 10
        
        total_pages = program_select_screen.get_total_pages()
        assert total_pages == 3
        
        # Test with 30 programs, 10 per page = 3 pages
        program_select_screen.programs = [{"title": f"番組{i}"} for i in range(30)]
        total_pages = program_select_screen.get_total_pages()
        assert total_pages == 3
        
        # Test with 0 programs
        program_select_screen.programs = []
        total_pages = program_select_screen.get_total_pages()
        assert total_pages == 0
        
    def test_pagination_next_page(self, program_select_screen):
        """Test moving to next page"""
        program_select_screen.programs = [{"title": f"番組{i}"} for i in range(25)]
        program_select_screen.items_per_page = 10
        program_select_screen.current_page = 0
        
        # Test normal next page
        result = program_select_screen.next_page()
        assert result == True
        assert program_select_screen.current_page == 1
        
        # Test next page from page 1
        result = program_select_screen.next_page()
        assert result == True
        assert program_select_screen.current_page == 2
        
        # Test next page from last page (should not advance)
        result = program_select_screen.next_page()
        assert result == False
        assert program_select_screen.current_page == 2
        
    def test_pagination_previous_page(self, program_select_screen):
        """Test moving to previous page"""
        program_select_screen.programs = [{"title": f"番組{i}"} for i in range(25)]
        program_select_screen.items_per_page = 10
        program_select_screen.current_page = 2
        
        # Test normal previous page
        result = program_select_screen.previous_page()
        assert result == True
        assert program_select_screen.current_page == 1
        
        # Test previous page from page 1
        result = program_select_screen.previous_page()
        assert result == True
        assert program_select_screen.current_page == 0
        
        # Test previous page from first page (should not go back)
        result = program_select_screen.previous_page()
        assert result == False
        assert program_select_screen.current_page == 0
        
    def test_fetch_programs_from_api(self, program_select_screen, sample_station, sample_date):
        """Test fetching programs from API"""
        mock_program_history = Mock()
        mock_program_history.get_programs_for_date.return_value = [
            {"title": "テスト番組", "start_time": "12:00", "end_time": "13:00"}
        ]
        
        with patch('src.ui.screens.program_select_screen.ProgramHistoryManager', return_value=mock_program_history):
            programs = program_select_screen._fetch_programs_from_api(sample_station["id"], sample_date)
            
            assert len(programs) == 1
            assert programs[0]["title"] == "テスト番組"
            mock_program_history.get_programs_for_date.assert_called_once_with(sample_station["id"], sample_date)
            
    def test_show_program_info(self, program_select_screen, mock_ui_service, mock_programs):
        """Test showing program information"""
        program_select_screen.ui_service = mock_ui_service
        mock_keyboard_handler = Mock()
        mock_ui_service.keyboard_handler = mock_keyboard_handler
        
        program = mock_programs[0]
        program_select_screen.show_program_info(program)
        
        # Should display program info and wait for key
        mock_keyboard_handler.get_key.assert_called_once()
        
    def test_handle_shortcut_key_info(self, program_select_screen, mock_ui_service, mock_programs):
        """Test handling info shortcut key"""
        program_select_screen.ui_service = mock_ui_service
        program_select_screen.programs = mock_programs
        mock_ui_service.get_current_item.return_value = "06:30-09:00 森本毅郎・スタンバイ!"
        
        with patch.object(program_select_screen, 'show_program_info') as mock_show_info:
            result = program_select_screen.handle_shortcut_key('i')
            
            mock_show_info.assert_called_once()
            assert result == True
            
    def test_handle_shortcut_key_next_page(self, program_select_screen, mock_ui_service):
        """Test handling next page shortcut key"""
        program_select_screen.ui_service = mock_ui_service
        
        with patch.object(program_select_screen, 'next_page') as mock_next:
            mock_next.return_value = True
            
            result = program_select_screen.handle_shortcut_key('n')
            
            mock_next.assert_called_once()
            mock_ui_service.display_status.assert_called_with("次のページに移動しました")
            assert result == True
            
    def test_handle_shortcut_key_previous_page(self, program_select_screen, mock_ui_service):
        """Test handling previous page shortcut key"""
        program_select_screen.ui_service = mock_ui_service
        
        with patch.object(program_select_screen, 'previous_page') as mock_prev:
            mock_prev.return_value = True
            
            result = program_select_screen.handle_shortcut_key('p')
            
            mock_prev.assert_called_once()
            mock_ui_service.display_status.assert_called_with("前のページに移動しました")
            assert result == True
            
    def test_handle_shortcut_key_unknown(self, program_select_screen):
        """Test handling unknown shortcut key"""
        result = program_select_screen.handle_shortcut_key('x')
        
        assert result == False
        
    def test_get_pagination_info(self, program_select_screen):
        """Test getting pagination information"""
        program_select_screen.programs = [{"title": f"番組{i}"} for i in range(25)]
        program_select_screen.items_per_page = 10
        program_select_screen.current_page = 1
        
        info = program_select_screen.get_pagination_info()
        
        assert "ページ 2/3" in info
        assert "11-20" in info
        assert "25" in info
        
    def test_validate_program_data(self, program_select_screen, mock_programs):
        """Test validating program data"""
        valid_program = mock_programs[0]
        invalid_program = {"title": "テスト番組"}  # Missing required fields
        
        assert program_select_screen.validate_program_data(valid_program) == True
        assert program_select_screen.validate_program_data(invalid_program) == False
        
    def test_get_program_count(self, program_select_screen, mock_programs):
        """Test getting program count"""
        program_select_screen.programs = mock_programs
        
        count = program_select_screen.get_program_count()
        
        assert count == 3
        
    def test_has_programs(self, program_select_screen, mock_programs):
        """Test checking if programs are loaded"""
        # Test with programs
        program_select_screen.programs = mock_programs
        assert program_select_screen.has_programs() == True
        
        # Test without programs
        program_select_screen.programs = []
        assert program_select_screen.has_programs() == False
        
    def test_refresh_programs(self, program_select_screen, sample_station, sample_date):
        """Test refreshing program list"""
        program_select_screen.set_station_and_date(sample_station, sample_date)
        
        with patch.object(program_select_screen, 'load_programs') as mock_load:
            mock_load.return_value = True
            
            result = program_select_screen.refresh_programs()
            
            assert result == True
            mock_load.assert_called_once()