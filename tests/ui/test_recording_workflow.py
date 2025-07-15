"""
Test for RecordingWorkflow integration

Tests the complete recording workflow integration including:
- Station selection → Date selection → Program selection → Recording execution
- Error handling and user feedback
- Integration with TimeFreeRecorder
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.recording_workflow import RecordingWorkflow
from src.ui.screens import MainMenuScreen, StationSelectScreen, DateSelectScreen, ProgramSelectScreen
from src.ui.menu_manager import MenuManager
from src.ui.services.ui_service import UIService


class TestRecordingWorkflow:
    """Test RecordingWorkflow integration"""
    
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
        return mapper
    
    @pytest.fixture
    def workflow(self, mock_ui_service, mock_menu_manager, mock_timefree_recorder, mock_region_mapper):
        """Create RecordingWorkflow instance with mocks"""
        with patch('src.ui.recording_workflow.UIService', return_value=mock_ui_service), \
             patch('src.ui.recording_workflow.MenuManager', return_value=mock_menu_manager), \
             patch('src.ui.recording_workflow.TimeFreeRecorder', return_value=mock_timefree_recorder), \
             patch('src.ui.recording_workflow.RegionMapper', return_value=mock_region_mapper):
            return RecordingWorkflow()
    
    def test_recording_workflow_initialization(self, workflow):
        """Test RecordingWorkflow initialization"""
        assert workflow.ui_service is not None
        assert workflow.menu_manager is not None
        assert workflow.region_mapper is not None
        assert workflow.selected_station is None
        assert workflow.selected_date is None
        assert workflow.selected_program is None
    
    def test_register_screens(self, workflow):
        """Test screen registration with menu manager"""
        workflow.menu_manager.register_screen.assert_any_call("main_menu", workflow.main_menu_screen)
        workflow.menu_manager.register_screen.assert_any_call("station_select", workflow.station_select_screen)
        workflow.menu_manager.register_screen.assert_any_call("date_select", workflow.date_select_screen)
        workflow.menu_manager.register_screen.assert_any_call("program_select", workflow.program_select_screen)
    
    def test_start_recording_workflow_success(self, workflow):
        """Test successful recording workflow"""
        # Mock station selection
        mock_station = {"id": "TBS", "name": "TBSラジオ"}
        workflow._run_station_selection = Mock(return_value=mock_station)
        
        # Mock date selection
        mock_date = date(2025, 7, 15)
        workflow._run_date_selection = Mock(return_value=mock_date)
        
        # Mock program selection
        mock_program = {"id": "program_123", "title": "テスト番組"}
        workflow._run_program_selection = Mock(return_value=mock_program)
        
        # Mock recording execution
        workflow._execute_recording = Mock(return_value=True)
        
        # Execute workflow
        result = workflow.start_recording_workflow()
        
        # Verify workflow execution
        assert result is True
        assert workflow.selected_station == mock_station
        assert workflow.selected_date == mock_date
        assert workflow.selected_program == mock_program
        
        # Verify method calls
        workflow._run_station_selection.assert_called_once()
        workflow._run_date_selection.assert_called_once()
        workflow._run_program_selection.assert_called_once()
        workflow._execute_recording.assert_called_once()
    
    def test_start_recording_workflow_cancelled_at_station(self, workflow):
        """Test workflow cancellation at station selection"""
        # Mock cancelled station selection
        workflow._run_station_selection = Mock(return_value=None)
        
        # Execute workflow
        result = workflow.start_recording_workflow()
        
        # Verify cancellation
        assert result is False
        assert workflow.selected_station is None
        assert workflow.selected_date is None
        assert workflow.selected_program is None
        
        # Verify only station selection was called
        workflow._run_station_selection.assert_called_once()
    
    def test_start_recording_workflow_cancelled_at_date(self, workflow):
        """Test workflow cancellation at date selection"""
        # Mock successful station selection
        mock_station = {"id": "TBS", "name": "TBSラジオ"}
        workflow._run_station_selection = Mock(return_value=mock_station)
        
        # Mock cancelled date selection
        workflow._run_date_selection = Mock(return_value=None)
        
        # Execute workflow
        result = workflow.start_recording_workflow()
        
        # Verify cancellation
        assert result is False
        assert workflow.selected_station == mock_station
        assert workflow.selected_date is None
        assert workflow.selected_program is None
        
        # Verify method calls
        workflow._run_station_selection.assert_called_once()
        workflow._run_date_selection.assert_called_once()
    
    def test_start_recording_workflow_cancelled_at_program(self, workflow):
        """Test workflow cancellation at program selection"""
        # Mock successful station selection
        mock_station = {"id": "TBS", "name": "TBSラジオ"}
        workflow._run_station_selection = Mock(return_value=mock_station)
        
        # Mock successful date selection
        mock_date = date(2025, 7, 15)
        workflow._run_date_selection = Mock(return_value=mock_date)
        
        # Mock cancelled program selection
        workflow._run_program_selection = Mock(return_value=None)
        
        # Execute workflow
        result = workflow.start_recording_workflow()
        
        # Verify cancellation
        assert result is False
        assert workflow.selected_station == mock_station
        assert workflow.selected_date == mock_date
        assert workflow.selected_program is None
        
        # Verify method calls
        workflow._run_station_selection.assert_called_once()
        workflow._run_date_selection.assert_called_once()
        workflow._run_program_selection.assert_called_once()
    
    def test_start_recording_workflow_recording_failed(self, workflow):
        """Test workflow with recording failure"""
        # Mock successful selections
        mock_station = {"id": "TBS", "name": "TBSラジオ"}
        workflow._run_station_selection = Mock(return_value=mock_station)
        
        mock_date = date(2025, 7, 15)
        workflow._run_date_selection = Mock(return_value=mock_date)
        
        mock_program = {"id": "program_123", "title": "テスト番組"}
        workflow._run_program_selection = Mock(return_value=mock_program)
        
        # Mock recording failure
        workflow._execute_recording = Mock(return_value=False)
        
        # Execute workflow
        result = workflow.start_recording_workflow()
        
        # Verify failure
        assert result is False
        assert workflow.selected_station == mock_station
        assert workflow.selected_date == mock_date
        assert workflow.selected_program == mock_program
        
        # Verify all methods were called
        workflow._run_station_selection.assert_called_once()
        workflow._run_date_selection.assert_called_once()
        workflow._run_program_selection.assert_called_once()
        workflow._execute_recording.assert_called_once()
    
    def test_start_recording_workflow_exception_handling(self, workflow):
        """Test workflow exception handling"""
        # Mock station selection to raise exception
        workflow._run_station_selection = Mock(side_effect=Exception("Test error"))
        
        # Execute workflow
        result = workflow.start_recording_workflow()
        
        # Verify exception handling
        assert result is False
        workflow._run_station_selection.assert_called_once()
    
    def test_reset_workflow_state(self, workflow):
        """Test workflow state reset"""
        # Set some state
        workflow.selected_station = {"id": "TBS", "name": "TBSラジオ"}
        workflow.selected_date = date(2025, 7, 15)
        workflow.selected_program = {"id": "program_123", "title": "テスト番組"}
        
        # Reset workflow
        workflow.reset_workflow_state()
        
        # Verify state reset
        assert workflow.selected_station is None
        assert workflow.selected_date is None
        assert workflow.selected_program is None
    
    def test_get_workflow_state(self, workflow):
        """Test workflow state retrieval"""
        # Set workflow state
        mock_station = {"id": "TBS", "name": "TBSラジオ"}
        mock_date = date(2025, 7, 15)
        mock_program = {"id": "program_123", "title": "テスト番組"}
        
        workflow.selected_station = mock_station
        workflow.selected_date = mock_date
        workflow.selected_program = mock_program
        
        # Get workflow state
        state = workflow.get_workflow_state()
        
        # Verify state
        assert state["station"] == mock_station
        assert state["date"] == mock_date
        assert state["program"] == mock_program
    
    def test_validate_workflow_state(self, workflow):
        """Test workflow state validation"""
        # Test empty state
        assert not workflow.is_workflow_complete()
        
        # Test partial state
        workflow.selected_station = {"id": "TBS", "name": "TBSラジオ"}
        assert not workflow.is_workflow_complete()
        
        workflow.selected_date = date(2025, 7, 15)
        assert not workflow.is_workflow_complete()
        
        # Test complete state
        workflow.selected_program = {"id": "program_123", "title": "テスト番組"}
        assert workflow.is_workflow_complete()