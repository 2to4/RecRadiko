"""
Test for RecordingWorkflow error handling improvements

Tests the enhanced error handling functionality including:
- Station selection error handling
- Date selection error handling
- Program selection error handling
- Recording execution error handling
- Workflow interruption handling
- Requirements validation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import date, datetime
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.recording_workflow import RecordingWorkflow
from src.ui.screens import MainMenuScreen, StationSelectScreen, DateSelectScreen, ProgramSelectScreen
from src.ui.menu_manager import MenuManager
from src.ui.services.ui_service import UIService


class TestRecordingWorkflowErrorHandling:
    """Test RecordingWorkflow error handling improvements"""
    
    @pytest.fixture
    def mock_ui_service(self):
        """Create mock UIService"""
        return Mock(spec=UIService)
    
    @pytest.fixture
    def mock_menu_manager(self):
        """Create mock MenuManager"""
        return Mock(spec=MenuManager)
    
    @pytest.fixture
    def mock_timefree_recorder(self):
        """Create mock TimeFreeRecorder"""
        recorder = Mock()
        recorder.record_program.return_value = True
        return recorder
    
    @pytest.fixture
    def mock_region_mapper(self):
        """Create mock RegionMapper"""
        mapper = Mock()
        mapper.get_current_prefecture.return_value = "東京"
        mapper.get_area_id.return_value = "JP13"
        return mapper
    
    @pytest.fixture
    def workflow(self, mock_ui_service, mock_menu_manager, mock_timefree_recorder, mock_region_mapper):
        """Create RecordingWorkflow instance with mocks"""
        with patch('src.ui.recording_workflow.UIService', return_value=mock_ui_service), \
             patch('src.ui.recording_workflow.MenuManager', return_value=mock_menu_manager), \
             patch('src.ui.recording_workflow.TimeFreeRecorder', return_value=mock_timefree_recorder), \
             patch('src.ui.recording_workflow.RegionMapper', return_value=mock_region_mapper):
            return RecordingWorkflow()
    
    def test_station_selection_error_handling(self, workflow):
        """Test error handling in station selection"""
        # Mock station selection screen to raise exception
        workflow.station_select_screen.load_stations = Mock(side_effect=Exception("Station load error"))
        
        # Run station selection
        result = workflow._run_station_selection()
        
        # Verify error handling
        assert result is None
        workflow.ui_service.display_error.assert_called()
        assert "放送局選択でエラーが発生しました" in workflow.ui_service.display_error.call_args[0][0]
    
    def test_station_selection_load_failure(self, workflow):
        """Test handling of station load failure"""
        # Mock station selection screen to return False
        workflow.station_select_screen.load_stations = Mock(return_value=False)
        
        # Run station selection
        result = workflow._run_station_selection()
        
        # Verify error handling
        assert result is None
        workflow.ui_service.display_error.assert_called()
        # Check if any of the error calls contains the expected message
        error_calls = workflow.ui_service.display_error.call_args_list
        error_messages = [call[0][0] for call in error_calls]
        assert any("放送局の読み込みに失敗しました" in msg for msg in error_messages)
    
    def test_date_selection_error_handling(self, workflow):
        """Test error handling in date selection"""
        # Set up station selection
        workflow.selected_station = {"id": "TBS", "name": "TBSラジオ"}
        
        # Mock date selection screen to raise exception
        workflow.date_select_screen.set_station = Mock(side_effect=Exception("Date selection error"))
        
        # Run date selection
        result = workflow._run_date_selection()
        
        # Verify error handling
        assert result is None
        workflow.ui_service.display_error.assert_called()
        assert "日付選択でエラーが発生しました" in workflow.ui_service.display_error.call_args[0][0]
    
    def test_date_selection_missing_station(self, workflow):
        """Test date selection without station selection"""
        # Don't set station
        workflow.selected_station = None
        
        # Run date selection
        result = workflow._run_date_selection()
        
        # Verify error handling
        assert result is None
        workflow.ui_service.display_error.assert_called()
        assert "日付選択の前に放送局を選択してください" in workflow.ui_service.display_error.call_args[0][0]
    
    def test_program_selection_error_handling(self, workflow):
        """Test error handling in program selection"""
        # Set up station and date selection
        workflow.selected_station = {"id": "TBS", "name": "TBSラジオ"}
        workflow.selected_date = date(2025, 7, 15)
        
        # Mock program selection screen to raise exception
        workflow.program_select_screen.set_station_and_date = Mock(side_effect=Exception("Program selection error"))
        
        # Run program selection
        result = workflow._run_program_selection()
        
        # Verify error handling
        assert result is None
        workflow.ui_service.display_error.assert_called()
        assert "番組選択でエラーが発生しました" in workflow.ui_service.display_error.call_args[0][0]
    
    def test_program_selection_load_failure(self, workflow):
        """Test handling of program load failure"""
        # Set up station and date selection
        workflow.selected_station = {"id": "TBS", "name": "TBSラジオ"}
        workflow.selected_date = date(2025, 7, 15)
        
        # Mock program selection screen to return False for load_programs
        workflow.program_select_screen.set_station_and_date = Mock()
        workflow.program_select_screen.load_programs = Mock(return_value=False)
        
        # Run program selection
        result = workflow._run_program_selection()
        
        # Verify error handling
        assert result is None
        workflow.ui_service.display_error.assert_called()
        # Check if any of the error calls contains the expected message
        error_calls = workflow.ui_service.display_error.call_args_list
        error_messages = [call[0][0] for call in error_calls]
        assert any("番組の読み込みに失敗しました" in msg for msg in error_messages)
    
    def test_program_selection_missing_requirements(self, workflow):
        """Test program selection without required selections"""
        # Don't set station or date
        workflow.selected_station = None
        workflow.selected_date = None
        
        # Run program selection
        result = workflow._run_program_selection()
        
        # Verify error handling
        assert result is None
        workflow.ui_service.display_error.assert_called()
        assert "番組選択の前に放送局と日付を選択してください" in workflow.ui_service.display_error.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_recording_execution_missing_selection(self, workflow):
        """Test recording execution with missing selection data"""
        # Set up incomplete selection
        workflow.selected_station = {"id": "TBS", "name": "TBSラジオ"}
        workflow.selected_date = None  # Missing date
        workflow.selected_program = None  # Missing program
        
        # Run recording execution
        result = await workflow._execute_recording()
        
        # Verify error handling
        assert result is False
        workflow.ui_service.display_error.assert_called()
        assert "録音実行に必要な選択が不足しています" in workflow.ui_service.display_error.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_recording_execution_program_info_creation_failure(self, workflow):
        """Test recording execution with program info creation failure"""
        # Set up complete selection
        workflow.selected_station = {"id": "TBS", "name": "TBSラジオ"}
        workflow.selected_date = date(2025, 7, 15)
        workflow.selected_program = {"id": "program_123", "title": "テスト番組"}
        
        # Mock confirmation to return True
        workflow._confirm_recording = Mock(return_value=True)
        
        # Mock program info creation to fail
        workflow._create_program_info = Mock(return_value=None)
        
        # Run recording execution
        result = await workflow._execute_recording()
        
        # Verify error handling
        assert result is False
        workflow.ui_service.display_error.assert_called()
        # Check if any of the error calls contains the expected message
        error_calls = workflow.ui_service.display_error.call_args_list
        error_messages = [call[0][0] for call in error_calls]
        assert any("番組情報の作成に失敗しました" in msg for msg in error_messages)
    
    @pytest.mark.asyncio
    async def test_recording_execution_permission_error(self, workflow):
        """Test recording execution with permission error"""
        # Set up complete selection
        workflow.selected_station = {"id": "TBS", "name": "TBSラジオ"}
        workflow.selected_date = date(2025, 7, 15)
        workflow.selected_program = {"id": "program_123", "title": "テスト番組"}
        
        # Mock confirmation to return True
        workflow._confirm_recording = Mock(return_value=True)
        
        # Mock program info creation to succeed
        workflow._create_program_info = Mock(return_value=Mock())
        
        # Mock output filename generation
        workflow._generate_output_filename = Mock(return_value="test_output.mp3")
        
        # Mock display methods
        workflow._display_recording_start = Mock()
        
        # Mock TimeFreeRecorder to raise PermissionError
        workflow.timefree_recorder.record_program = AsyncMock(side_effect=PermissionError("Permission denied"))
        
        # Run recording execution
        result = await workflow._execute_recording()
        
        # Verify error handling
        assert result is False
        workflow.ui_service.display_error.assert_called()
        # Check if any of the error calls contains the expected message
        error_calls = workflow.ui_service.display_error.call_args_list
        error_messages = [call[0][0] for call in error_calls]
        assert any("ファイルの書き込み権限がありません" in msg for msg in error_messages)
    
    @pytest.mark.asyncio
    async def test_recording_execution_connection_error(self, workflow):
        """Test recording execution with connection error"""
        # Set up complete selection
        workflow.selected_station = {"id": "TBS", "name": "TBSラジオ"}
        workflow.selected_date = date(2025, 7, 15)
        workflow.selected_program = {"id": "program_123", "title": "テスト番組"}
        
        # Mock confirmation to return True
        workflow._confirm_recording = Mock(return_value=True)
        
        # Mock program info creation to succeed
        workflow._create_program_info = Mock(return_value=Mock())
        
        # Mock output filename generation
        workflow._generate_output_filename = Mock(return_value="test_output.mp3")
        
        # Mock display methods
        workflow._display_recording_start = Mock()
        
        # Mock TimeFreeRecorder to raise ConnectionError
        workflow.timefree_recorder.record_program = AsyncMock(side_effect=ConnectionError("Connection failed"))
        
        # Run recording execution
        result = await workflow._execute_recording()
        
        # Verify error handling
        assert result is False
        workflow.ui_service.display_error.assert_called()
        # Check if any of the error calls contains the expected message
        error_calls = workflow.ui_service.display_error.call_args_list
        error_messages = [call[0][0] for call in error_calls]
        assert any("ネットワーク接続エラーが発生しました" in msg for msg in error_messages)
    
    @pytest.mark.asyncio
    async def test_workflow_interruption_handling(self, workflow):
        """Test workflow interruption handling"""
        # Mock station selection to raise KeyboardInterrupt
        workflow._run_station_selection = Mock(side_effect=KeyboardInterrupt())
        
        # Mock interruption handler
        workflow._handle_workflow_interruption = Mock()
        
        # Run workflow
        result = await workflow.start_recording_workflow()
        
        # Verify interruption handling
        assert result is False
        workflow._handle_workflow_interruption.assert_called_once()
    
    @patch('subprocess.run')
    def test_validate_workflow_requirements_ffmpeg_missing(self, mock_subprocess, workflow):
        """Test workflow requirements validation with missing FFmpeg"""
        # Mock FFmpeg check to fail
        mock_subprocess.return_value.returncode = 1
        
        # Run validation
        result = workflow._validate_workflow_requirements()
        
        # Verify validation failure
        assert result is False
        workflow.ui_service.display_error.assert_called()
        # Check if any of the error calls contains the expected message
        error_calls = workflow.ui_service.display_error.call_args_list
        error_messages = [call[0][0] for call in error_calls]
        assert any("FFmpegがインストールされていません" in msg for msg in error_messages)
    
    @patch('urllib.request.urlopen')
    @patch('subprocess.run')
    def test_validate_workflow_requirements_no_internet(self, mock_subprocess, mock_urlopen, workflow):
        """Test workflow requirements validation with no internet connection"""
        # Mock FFmpeg check to succeed
        mock_subprocess.return_value.returncode = 0
        
        # Mock internet check to fail
        mock_urlopen.side_effect = Exception("Connection failed")
        
        # Run validation
        result = workflow._validate_workflow_requirements()
        
        # Verify validation failure
        assert result is False
        workflow.ui_service.display_error.assert_called()
        # Check if any of the error calls contains the expected message
        error_calls = workflow.ui_service.display_error.call_args_list
        error_messages = [call[0][0] for call in error_calls]
        assert any("インターネット接続が必要です" in msg for msg in error_messages)
    
    def test_display_error_summary(self, workflow):
        """Test error summary display"""
        # Mock keyboard handler
        mock_keyboard_handler = Mock()
        mock_keyboard_handler.get_key = Mock()
        workflow.ui_service.keyboard_handler = mock_keyboard_handler
        
        # Display error summary
        workflow._display_error_summary()
        
        # Verify keyboard handler was called
        mock_keyboard_handler.get_key.assert_called_once()
    
    def test_handle_workflow_interruption(self, workflow):
        """Test workflow interruption handling"""
        # Run interruption handler
        workflow._handle_workflow_interruption()
        
        # Verify selections were reset
        assert workflow.selected_station is None
        assert workflow.selected_date is None
        assert workflow.selected_program is None
    
    def test_get_current_area_with_region_mapper(self, workflow):
        """Test getting current area with region mapper"""
        # Mock region mapper to return valid area
        workflow.region_mapper.get_current_prefecture.return_value = "東京"
        workflow.region_mapper.get_area_id.return_value = "JP13"
        
        # Get current area
        area = workflow._get_current_area()
        
        # Verify result
        assert area == "JP13"
    
    def test_get_current_area_fallback(self, workflow):
        """Test getting current area with fallback"""
        # Mock region mapper to return None
        workflow.region_mapper.get_current_prefecture.return_value = None
        workflow.region_mapper.get_area_id.return_value = None
        
        # Get current area
        area = workflow._get_current_area()
        
        # Verify fallback
        assert area == "JP13"
    
    def test_get_current_area_exception_handling(self, workflow):
        """Test getting current area with exception handling"""
        # Mock region mapper to raise exception
        workflow.region_mapper.get_current_prefecture.side_effect = Exception("Region mapper error")
        
        # Get current area
        area = workflow._get_current_area()
        
        # Verify exception handling and fallback
        assert area == "JP13"