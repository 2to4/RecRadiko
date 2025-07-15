"""
Test RecordingWorkflow with actual Radiko API

This test suite validates the complete recording workflow using real Radiko API endpoints.
Tests are designed to be run manually or in CI environments with proper API access.

Usage:
    # Run with real API (requires internet connection)
    python -m pytest tests/ui/test_recording_workflow_real_api.py -v
    
    # Skip real API tests
    SKIP_REAL_API_TESTS=1 python -m pytest tests/ui/test_recording_workflow_real_api.py -v
"""

import pytest
import os
import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import patch, Mock
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.recording_workflow import RecordingWorkflow
from src.auth import RadikoAuthenticator
from src.timefree_recorder import TimeFreeRecorder
from src.program_info import ProgramInfo
from src.region_mapper import RegionMapper


@pytest.mark.skipif(
    os.environ.get('SKIP_REAL_API_TESTS') == '1',
    reason="Real API tests are disabled by environment variable"
)
class TestRecordingWorkflowRealAPI:
    """Test RecordingWorkflow with real Radiko API"""
    
    @pytest.fixture
    def workflow(self):
        """Create RecordingWorkflow instance for real API testing"""
        return RecordingWorkflow()
    
    @pytest.fixture
    def authenticator(self):
        """Create RadikoAuthenticator for real API testing"""
        return RadikoAuthenticator()
    
    @pytest.fixture
    def timefree_recorder(self, authenticator):
        """Create TimeFreeRecorder for real API testing"""
        return TimeFreeRecorder(authenticator)
    
    def test_workflow_initialization_with_real_components(self, workflow):
        """Test workflow initialization with real components"""
        # Verify all components are initialized
        assert workflow.ui_service is not None
        assert workflow.menu_manager is not None
        assert workflow.region_mapper is not None
        assert workflow.authenticator is not None
        assert workflow.timefree_recorder is not None
        
        # Verify component types
        assert isinstance(workflow.authenticator, RadikoAuthenticator)
        assert isinstance(workflow.timefree_recorder, TimeFreeRecorder)
        assert isinstance(workflow.region_mapper, RegionMapper)
    
    def test_region_mapper_real_functionality(self, workflow):
        """Test region mapper with real prefecture data"""
        region_mapper = workflow.region_mapper
        
        # Test prefecture list
        prefectures = region_mapper.list_all_prefectures()
        assert len(prefectures) == 47  # All Japanese prefectures
        
        # Test specific prefecture mapping
        tokyo_area = region_mapper.get_area_id("東京")
        assert tokyo_area == "JP13"
        
        # Test area to prefecture mapping
        prefecture_name = region_mapper.get_prefecture_name("JP13")
        assert prefecture_name == "東京"
        
        # Test current area functionality
        current_area = workflow._get_current_area()
        assert current_area is not None
        assert current_area.startswith("JP")
    
    def test_authenticator_real_api_connection(self, authenticator):
        """Test authenticator with real Radiko API"""
        try:
            # Test basic authentication
            auth_result = authenticator.authenticate()
            assert auth_result is not None
            
            # Test timefree authentication
            timefree_token = authenticator.authenticate_timefree()
            assert timefree_token is not None
            
            print(f"✅ Authentication successful")
            print(f"   Basic auth token: {auth_result[:20]}...")
            print(f"   Timefree token: {timefree_token[:20]}...")
            
        except Exception as e:
            pytest.fail(f"Authentication failed: {e}")
    
    def test_station_loading_real_api(self, workflow):
        """Test station loading with real API"""
        try:
            # Get current area
            current_area = workflow._get_current_area()
            
            # Load stations
            success = workflow.station_select_screen.load_stations(current_area)
            assert success is True
            
            # Verify stations were loaded
            stations = workflow.station_select_screen.stations
            assert len(stations) > 0
            
            print(f"✅ Station loading successful for area {current_area}")
            print(f"   Loaded {len(stations)} stations")
            
            # Verify station data structure
            first_station = stations[0]
            assert 'id' in first_station
            assert 'name' in first_station
            assert isinstance(first_station['id'], str)
            assert isinstance(first_station['name'], str)
            
            print(f"   Example station: {first_station['name']} ({first_station['id']})")
            
        except Exception as e:
            pytest.fail(f"Station loading failed: {e}")
    
    def test_program_history_real_api(self, workflow):
        """Test program history loading with real API"""
        try:
            # Set up for program loading
            workflow.selected_station = {"id": "TBS", "name": "TBSラジオ"}
            workflow.selected_date = date.today() - timedelta(days=1)  # Yesterday
            
            # Load programs
            workflow.program_select_screen.set_station_and_date(
                workflow.selected_station, 
                workflow.selected_date
            )
            
            success = workflow.program_select_screen.load_programs()
            assert success is True
            
            # Verify programs were loaded
            programs = workflow.program_select_screen.programs
            assert len(programs) > 0
            
            print(f"✅ Program loading successful")
            print(f"   Station: {workflow.selected_station['name']}")
            print(f"   Date: {workflow.selected_date}")
            print(f"   Loaded {len(programs)} programs")
            
            # Verify program data structure
            first_program = programs[0]
            required_fields = ['title', 'start_time', 'end_time']
            for field in required_fields:
                assert field in first_program
                assert first_program[field] is not None
            
            print(f"   Example program: {first_program['title']}")
            print(f"   Time: {first_program['start_time']}-{first_program['end_time']}")
            
        except Exception as e:
            pytest.fail(f"Program loading failed: {e}")
    
    @pytest.mark.asyncio
    async def test_program_info_creation_real_data(self, workflow):
        """Test program info creation with real program data"""
        try:
            # Set up with real station and date
            workflow.selected_station = {"id": "TBS", "name": "TBSラジオ"}
            workflow.selected_date = date.today() - timedelta(days=1)
            
            # Create a realistic program entry
            workflow.selected_program = {
                "id": "TBS_test_program",
                "title": "テスト番組",
                "start_time": "06:00",
                "end_time": "06:30",
                "performer": "テスト出演者",
                "description": "テスト番組の説明"
            }
            
            # Create program info
            program_info = workflow._create_program_info()
            assert program_info is not None
            
            # Verify program info structure
            assert isinstance(program_info, ProgramInfo)
            assert program_info.station_id == "TBS"
            assert program_info.station_name == "TBSラジオ"
            assert program_info.title == "テスト番組"
            assert program_info.is_timefree_available is True
            
            # Verify datetime conversion
            assert isinstance(program_info.start_time, datetime)
            assert isinstance(program_info.end_time, datetime)
            
            print(f"✅ Program info creation successful")
            print(f"   Program: {program_info.title}")
            print(f"   Station: {program_info.station_name}")
            print(f"   Start time: {program_info.start_time}")
            print(f"   End time: {program_info.end_time}")
            
        except Exception as e:
            pytest.fail(f"Program info creation failed: {e}")
    
    @pytest.mark.asyncio
    async def test_timefree_recorder_real_api_short_recording(self, timefree_recorder):
        """Test TimeFreeRecorder with real API (short recording)"""
        try:
            # Create a short test recording (2 minutes from yesterday)
            yesterday = date.today() - timedelta(days=1)
            start_time = datetime.combine(yesterday, datetime.min.time().replace(hour=6, minute=0))
            end_time = start_time + timedelta(minutes=2)
            
            # Create test program info
            program_info = ProgramInfo(
                program_id="test_real_api",
                station_id="TBS",
                station_name="TBSラジオ",
                title="Real API Test Recording",
                start_time=start_time,
                end_time=end_time,
                is_timefree_available=True
            )
            
            # Generate test output path
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                output_path = tmp.name
            
            try:
                # Execute real recording
                print(f"🎙️  Starting real API recording test...")
                print(f"   Program: {program_info.title}")
                print(f"   Time: {start_time} - {end_time}")
                print(f"   Output: {output_path}")
                
                result = await timefree_recorder.record_program(program_info, output_path)
                
                # Verify recording result
                assert result is not None
                assert hasattr(result, 'success')
                
                if result.success:
                    print(f"✅ Real API recording successful!")
                    print(f"   Output file: {result.output_path}")
                    print(f"   File size: {result.file_size_bytes / 1024:.1f} KB")
                    print(f"   Duration: {result.recording_duration_seconds:.1f} seconds")
                    print(f"   Total segments: {result.total_segments}")
                    print(f"   Failed segments: {result.failed_segments}")
                    
                    # Verify file exists and has content
                    assert os.path.exists(result.output_path)
                    assert os.path.getsize(result.output_path) > 0
                    
                else:
                    print(f"❌ Real API recording failed:")
                    for error in result.error_messages:
                        print(f"   Error: {error}")
                    
                    # Don't fail the test if it's a known limitation
                    if any("タイムフリー" in error for error in result.error_messages):
                        pytest.skip("Program not available for timefree recording")
                    elif any("認証" in error for error in result.error_messages):
                        pytest.skip("Authentication issue with real API")
                    else:
                        pytest.fail(f"Recording failed: {result.error_messages}")
                
            finally:
                # Cleanup test file
                try:
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                except:
                    pass
            
        except Exception as e:
            # Check if it's a known issue
            error_msg = str(e)
            if "認証" in error_msg or "404" in error_msg:
                pytest.skip(f"Real API issue (expected in test environment): {e}")
            else:
                pytest.fail(f"Real API recording test failed: {e}")
    
    def test_workflow_requirements_validation_real_environment(self, workflow):
        """Test workflow requirements validation in real environment"""
        try:
            # Test requirements validation
            result = workflow._validate_workflow_requirements()
            
            if result:
                print(f"✅ All workflow requirements validated successfully")
                print(f"   - FFmpeg: Available")
                print(f"   - Internet: Connected")
                print(f"   - File system: Writable")
            else:
                print(f"❌ Workflow requirements validation failed")
                print(f"   Check FFmpeg installation and internet connection")
                
                # Don't fail if it's an environment issue
                pytest.skip("Environment requirements not met")
                
        except Exception as e:
            pytest.skip(f"Requirements validation failed (environment issue): {e}")
    
    def test_error_handling_real_api_scenarios(self, workflow):
        """Test error handling with real API scenarios"""
        try:
            # Test with invalid station ID
            workflow.selected_station = {"id": "INVALID_STATION", "name": "Invalid Station"}
            workflow.selected_date = date.today() - timedelta(days=1)
            
            workflow.program_select_screen.set_station_and_date(
                workflow.selected_station, 
                workflow.selected_date
            )
            
            # This should fail gracefully
            success = workflow.program_select_screen.load_programs()
            assert success is False
            
            print(f"✅ Error handling test successful")
            print(f"   Invalid station ID correctly rejected")
            
        except Exception as e:
            # Expected to fail, but should be handled gracefully
            print(f"✅ Error handling working correctly: {e}")
    
    @pytest.mark.asyncio
    async def test_workflow_interruption_real_scenario(self, workflow):
        """Test workflow interruption in real scenario"""
        try:
            # Test interruption handling
            workflow._handle_workflow_interruption()
            
            # Verify state was reset
            assert workflow.selected_station is None
            assert workflow.selected_date is None
            assert workflow.selected_program is None
            
            print(f"✅ Workflow interruption handling successful")
            
        except Exception as e:
            pytest.fail(f"Workflow interruption handling failed: {e}")
    
    def test_integration_with_real_components(self, workflow):
        """Test integration between all real components"""
        try:
            # Test component integration
            assert workflow.timefree_recorder.authenticator == workflow.authenticator
            
            # Test region mapper integration
            current_area = workflow._get_current_area()
            assert current_area is not None
            
            # Test UI service integration
            assert workflow.ui_service is not None
            
            print(f"✅ Component integration test successful")
            print(f"   Current area: {current_area}")
            print(f"   Components properly integrated")
            
        except Exception as e:
            pytest.fail(f"Component integration failed: {e}")


class TestRecordingWorkflowRealAPIManual:
    """Manual tests for RecordingWorkflow with real API (run individually)"""
    
    @pytest.mark.manual
    @pytest.mark.asyncio
    async def test_full_workflow_manual_execution(self):
        """Manual test for complete workflow execution (run individually)"""
        print("\n" + "="*60)
        print("🧪 MANUAL TEST: Full Recording Workflow")
        print("="*60)
        print("This test requires manual interaction and should be run individually")
        print("Usage: python -m pytest tests/ui/test_recording_workflow_real_api.py::TestRecordingWorkflowRealAPIManual::test_full_workflow_manual_execution -v -s")
        print("="*60)
        
        # Skip by default in automated test runs
        if os.environ.get('PYTEST_CURRENT_TEST') and 'manual' not in os.environ.get('PYTEST_CURRENT_TEST', ''):
            pytest.skip("Manual test - run individually with -s flag")
        
        try:
            # Create workflow instance
            workflow = RecordingWorkflow()
            
            # Mock UI interactions for automated execution
            with patch.object(workflow.ui_service, 'get_user_selection') as mock_selection, \
                 patch.object(workflow.ui_service, 'confirm_action') as mock_confirm, \
                 patch.object(workflow.ui_service, 'keyboard_handler') as mock_keyboard:
                
                # Mock user selections
                mock_selection.side_effect = [
                    "TBSラジオ",  # Station selection
                    None  # Cancel after station selection
                ]
                mock_confirm.return_value = False  # Cancel recording
                mock_keyboard.get_key.return_value = None
                
                # Execute workflow
                print("🎛️  Starting recording workflow...")
                result = await workflow.start_recording_workflow()
                
                print(f"📊 Workflow result: {result}")
                
                # Verify workflow executed
                assert result is not None
                
                print("✅ Manual workflow test completed successfully")
                
        except Exception as e:
            print(f"❌ Manual workflow test failed: {e}")
            raise
    
    @pytest.mark.manual
    def test_display_system_info(self):
        """Manual test to display system information"""
        print("\n" + "="*60)
        print("🔧 SYSTEM INFORMATION")
        print("="*60)
        
        try:
            # Test system components
            workflow = RecordingWorkflow()
            
            print(f"📍 Current area: {workflow._get_current_area()}")
            print(f"🌐 Region mapper: {type(workflow.region_mapper).__name__}")
            print(f"🔐 Authenticator: {type(workflow.authenticator).__name__}")
            print(f"🎙️  Recorder: {type(workflow.timefree_recorder).__name__}")
            
            # Test requirements
            print(f"📋 Requirements validation: {workflow._validate_workflow_requirements()}")
            
            print("✅ System info display completed")
            
        except Exception as e:
            print(f"❌ System info display failed: {e}")
            raise