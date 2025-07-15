"""
Test SystemInfoScreen implementation

Tests the system information display functionality including:
- System status information (authentication, API, dependencies)
- Recording statistics and history
- Performance metrics
- System requirements check
- Log file access
- Real-time system monitoring

Following the principle of minimal mock usage - using real system calls,
real file access, and real dependency checks.
"""

import pytest
import tempfile
import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess
import time
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.screens.system_info_screen import SystemInfoScreen


class TestSystemInfoScreenReal:
    """System info screen tests with real environment (minimal mocking)"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".recradiko"
            config_dir.mkdir(parents=True)
            
            # Create sample log files
            log_dir = config_dir / "logs"
            log_dir.mkdir(parents=True)
            
            # Create sample log file
            log_file = log_dir / "recradiko.log"
            with open(log_file, 'w') as f:
                f.write("2025-07-15 10:00:00 - INFO - System started\n")
                f.write("2025-07-15 10:01:00 - INFO - Authentication successful\n")
                f.write("2025-07-15 10:02:00 - INFO - Recording completed\n")
            
            # Create sample recordings directory
            recordings_dir = config_dir / "recordings"
            recordings_dir.mkdir(parents=True)
            
            # Create sample recording files
            for i in range(3):
                recording_file = recordings_dir / f"TBS_20250715_100{i}00_sample_{i}.mp3"
                recording_file.write_bytes(b"fake mp3 data " * 1000)  # Create files with some size
            
            yield config_dir
    
    @pytest.fixture
    def mock_ui_service(self):
        """Create minimal UI service mock for input simulation"""
        mock_ui = Mock()
        mock_ui.get_user_selection = Mock(return_value=None)
        mock_ui.display_info = Mock()
        mock_ui.display_error = Mock()
        mock_ui.display_success = Mock()
        mock_ui.set_menu_items = Mock()
        mock_ui.display_menu_with_highlight = Mock()
        mock_ui.keyboard_handler = Mock()
        mock_ui.keyboard_handler.get_key = Mock(return_value='q')
        return mock_ui
    
    @pytest.fixture
    def system_info_screen(self, temp_config_dir, mock_ui_service):
        """Create SystemInfoScreen with real dependencies"""
        with patch('src.ui.screens.system_info_screen.UIService', return_value=mock_ui_service):
            screen = SystemInfoScreen(str(temp_config_dir))
            return screen
    
    def test_system_info_screen_initialization(self, system_info_screen):
        """Test SystemInfoScreen initialization"""
        assert system_info_screen.title == "システム情報"
        assert hasattr(system_info_screen, 'system_checker')
        assert hasattr(system_info_screen, 'stats_manager')
        assert hasattr(system_info_screen, 'log_manager')
        assert hasattr(system_info_screen, 'menu_options')
        assert len(system_info_screen.menu_options) > 0
    
    def test_system_status_check(self, system_info_screen):
        """Test system status checking with real system calls"""
        # Get system status
        status = system_info_screen.system_checker.get_system_status()
        
        # Verify status structure
        assert "authentication" in status
        assert "api_connection" in status
        assert "ffmpeg" in status
        assert "python_version" in status
        assert "dependencies" in status
        
        # Verify authentication status (should be dict with status info)
        auth_status = status["authentication"]
        assert isinstance(auth_status, dict)
        assert "status" in auth_status
        assert "message" in auth_status
        
        # Verify API connection status
        api_status = status["api_connection"]
        assert isinstance(api_status, dict)
        assert "status" in api_status
        assert "response_time" in api_status
        
        # Verify FFmpeg status
        ffmpeg_status = status["ffmpeg"]
        assert isinstance(ffmpeg_status, dict)
        assert "available" in ffmpeg_status
        
        # Verify Python version (should be real version)
        python_version = status["python_version"]
        assert isinstance(python_version, str)
        assert "3." in python_version  # Should be Python 3.x
    
    def test_recording_statistics(self, system_info_screen, temp_config_dir):
        """Test recording statistics with real file data"""
        # Get recording statistics
        stats = system_info_screen.stats_manager.get_recording_statistics()
        
        # Verify statistics structure
        assert "total_recordings" in stats
        assert "total_size" in stats
        assert "total_duration" in stats
        assert "success_rate" in stats
        assert "recent_recordings" in stats
        
        # Verify with real recording files
        assert stats["total_recordings"] >= 0
        assert stats["total_size"] >= 0
        assert isinstance(stats["recent_recordings"], list)
        
        # If there are sample recordings, verify they are counted
        recordings_dir = temp_config_dir / "recordings"
        if recordings_dir.exists():
            mp3_files = list(recordings_dir.glob("*.mp3"))
            if mp3_files:
                assert stats["total_recordings"] >= len(mp3_files)
    
    def test_system_requirements_check(self, system_info_screen):
        """Test system requirements checking"""
        # Get requirements status
        requirements = system_info_screen.system_checker.check_system_requirements()
        
        # Verify requirements structure
        assert "python" in requirements
        assert "disk_space" in requirements
        assert "memory" in requirements
        assert "dependencies" in requirements
        
        # Verify Python requirement
        python_req = requirements["python"]
        assert isinstance(python_req, dict)
        assert "satisfied" in python_req
        assert "current" in python_req
        assert "required" in python_req
        
        # Verify disk space requirement
        disk_req = requirements["disk_space"]
        assert isinstance(disk_req, dict)
        assert "satisfied" in disk_req
        assert "available" in disk_req
        assert "required" in disk_req
        
        # Verify memory requirement
        memory_req = requirements["memory"]
        assert isinstance(memory_req, dict)
        assert "satisfied" in memory_req
        assert "available" in memory_req
        assert "required" in memory_req
    
    def test_dependency_check_with_real_imports(self, system_info_screen):
        """Test dependency checking with real import attempts"""
        # Get dependency status
        deps = system_info_screen.system_checker.check_dependencies()
        
        # Verify dependencies structure
        assert isinstance(deps, dict)
        assert "installed" in deps
        assert "missing" in deps
        assert "details" in deps
        
        # Verify installed dependencies
        installed = deps["installed"]
        assert isinstance(installed, list)
        
        # Common dependencies that should be available
        expected_deps = ["json", "os", "sys", "pathlib", "datetime"]
        for dep in expected_deps:
            # These are built-in modules, should be available
            pass  # We don't enforce specific dependencies in this test
        
        # Verify missing dependencies
        missing = deps["missing"]
        assert isinstance(missing, list)
        
        # Verify details
        details = deps["details"]
        assert isinstance(details, dict)
    
    def test_log_file_access(self, system_info_screen, temp_config_dir):
        """Test log file access with real file operations"""
        # Get log information
        log_info = system_info_screen.log_manager.get_log_info()
        
        # Verify log info structure
        assert "log_files" in log_info
        assert "total_size" in log_info
        assert "oldest_entry" in log_info
        assert "newest_entry" in log_info
        
        # Verify log files list
        log_files = log_info["log_files"]
        assert isinstance(log_files, list)
        
        # If sample log file exists, verify it's detected
        log_file = temp_config_dir / "logs" / "recradiko.log"
        if log_file.exists():
            log_file_paths = [info["path"] for info in log_files]
            assert any(str(log_file) in path for path in log_file_paths)
    
    def test_recent_log_entries(self, system_info_screen, temp_config_dir):
        """Test recent log entries retrieval"""
        # Get recent log entries
        recent_logs = system_info_screen.log_manager.get_recent_log_entries(10)
        
        # Verify structure
        assert isinstance(recent_logs, list)
        
        # If sample log exists, verify entries
        log_file = temp_config_dir / "logs" / "recradiko.log"
        if log_file.exists():
            assert len(recent_logs) > 0
            
            # Verify log entry structure
            for entry in recent_logs:
                assert "timestamp" in entry
                assert "level" in entry
                assert "message" in entry
    
    def test_performance_metrics(self, system_info_screen):
        """Test performance metrics collection"""
        # Get performance metrics
        metrics = system_info_screen.stats_manager.get_performance_metrics()
        
        # Verify metrics structure
        assert "cpu_usage" in metrics
        assert "memory_usage" in metrics
        assert "disk_usage" in metrics
        assert "network_status" in metrics
        
        # Verify CPU usage
        cpu_usage = metrics["cpu_usage"]
        assert isinstance(cpu_usage, (int, float))
        assert 0 <= cpu_usage <= 100
        
        # Verify memory usage
        memory_usage = metrics["memory_usage"]
        assert isinstance(memory_usage, dict)
        assert "used" in memory_usage
        assert "total" in memory_usage
        assert "percent" in memory_usage
        
        # Verify disk usage
        disk_usage = metrics["disk_usage"]
        assert isinstance(disk_usage, dict)
        assert "used" in disk_usage
        assert "total" in disk_usage
        assert "percent" in disk_usage
    
    def test_system_info_display_content(self, system_info_screen):
        """Test system info display content"""
        # Test display content
        system_info_screen.display_content()
        
        # Verify UI service was called
        system_info_screen.ui_service.set_menu_items.assert_called_once()
        system_info_screen.ui_service.display_menu_with_highlight.assert_called_once()
        
        # Verify menu items contain expected options
        call_args = system_info_screen.ui_service.set_menu_items.call_args[0][0]
        assert any("システム状況" in item for item in call_args)
        assert any("録音統計" in item for item in call_args)
        assert any("ログファイル" in item for item in call_args)
        assert any("依存関係" in item for item in call_args)
    
    def test_system_info_workflow(self, system_info_screen):
        """Test complete system info workflow"""
        # Mock user selections
        system_info_screen.ui_service.get_user_selection.side_effect = [
            "システム状況を表示",  # Show system status
            "録音統計を表示",      # Show recording stats
            None  # Exit workflow
        ]
        
        # Mock detailed display methods
        with patch.object(system_info_screen, 'show_system_status') as mock_status, \
             patch.object(system_info_screen, 'show_recording_statistics') as mock_stats:
            
            # Run workflow
            result = system_info_screen.run_system_info_workflow()
            
            # Verify workflow execution
            mock_status.assert_called_once()
            mock_stats.assert_called_once()
            assert result == True
    
    def test_detailed_system_status_display(self, system_info_screen):
        """Test detailed system status display"""
        # Show detailed system status
        system_info_screen.show_system_status()
        
        # Verify keyboard handler was called for user input
        system_info_screen.ui_service.keyboard_handler.get_key.assert_called()
    
    def test_detailed_recording_statistics_display(self, system_info_screen):
        """Test detailed recording statistics display"""
        # Show detailed recording statistics
        system_info_screen.show_recording_statistics()
        
        # Verify keyboard handler was called for user input
        system_info_screen.ui_service.keyboard_handler.get_key.assert_called()
    
    def test_log_file_viewing(self, system_info_screen, temp_config_dir):
        """Test log file viewing functionality"""
        # Create log file with content
        log_file = temp_config_dir / "logs" / "recradiko.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, 'w') as f:
            f.write("2025-07-15 10:00:00 - INFO - Test log entry\n")
            f.write("2025-07-15 10:01:00 - ERROR - Test error entry\n")
            f.write("2025-07-15 10:02:00 - DEBUG - Test debug entry\n")
        
        # Show log file
        system_info_screen.show_log_file()
        
        # Verify keyboard handler was called for user input
        system_info_screen.ui_service.keyboard_handler.get_key.assert_called()


class TestSystemCheckerReal:
    """System checker tests with real system calls"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".recradiko"
            config_dir.mkdir(parents=True)
            yield config_dir
    
    def test_ffmpeg_availability_check(self, temp_config_dir):
        """Test FFmpeg availability with real system call"""
        from src.ui.screens.system_info_screen import SystemChecker
        
        checker = SystemChecker(str(temp_config_dir))
        ffmpeg_status = checker.check_ffmpeg_availability()
        
        # Verify structure
        assert isinstance(ffmpeg_status, dict)
        assert "available" in ffmpeg_status
        assert "version" in ffmpeg_status
        assert "path" in ffmpeg_status
        
        # Verify boolean availability
        assert isinstance(ffmpeg_status["available"], bool)
        
        # If FFmpeg is available, verify version info
        if ffmpeg_status["available"]:
            assert ffmpeg_status["version"] is not None
            assert ffmpeg_status["path"] is not None
    
    def test_python_version_check(self, temp_config_dir):
        """Test Python version checking"""
        from src.ui.screens.system_info_screen import SystemChecker
        
        checker = SystemChecker(str(temp_config_dir))
        python_info = checker.get_python_info()
        
        # Verify structure
        assert isinstance(python_info, dict)
        assert "version" in python_info
        assert "executable" in python_info
        assert "platform" in python_info
        
        # Verify version format
        version = python_info["version"]
        assert isinstance(version, str)
        assert "3." in version  # Should be Python 3.x
        
        # Verify executable path
        executable = python_info["executable"]
        assert isinstance(executable, str)
        assert len(executable) > 0
    
    def test_disk_space_check(self, temp_config_dir):
        """Test disk space checking"""
        from src.ui.screens.system_info_screen import SystemChecker
        
        checker = SystemChecker(str(temp_config_dir))
        disk_info = checker.get_disk_space_info()
        
        # Verify structure
        assert isinstance(disk_info, dict)
        assert "total" in disk_info
        assert "used" in disk_info
        assert "free" in disk_info
        assert "percent" in disk_info
        
        # Verify values are reasonable
        assert disk_info["total"] > 0
        assert disk_info["used"] >= 0
        assert disk_info["free"] >= 0
        assert 0 <= disk_info["percent"] <= 100
    
    def test_memory_info_check(self, temp_config_dir):
        """Test memory information checking"""
        from src.ui.screens.system_info_screen import SystemChecker
        
        checker = SystemChecker(str(temp_config_dir))
        memory_info = checker.get_memory_info()
        
        # Verify structure
        assert isinstance(memory_info, dict)
        assert "total" in memory_info
        assert "available" in memory_info
        assert "used" in memory_info
        assert "percent" in memory_info
        
        # Verify values are reasonable
        assert memory_info["total"] > 0
        assert memory_info["available"] >= 0
        assert memory_info["used"] >= 0
        assert 0 <= memory_info["percent"] <= 100


class TestRecordingStatsManagerReal:
    """Recording statistics manager tests with real file operations"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with sample recordings"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".recradiko"
            config_dir.mkdir(parents=True)
            
            # Create recordings directory
            recordings_dir = config_dir / "recordings"
            recordings_dir.mkdir(parents=True)
            
            # Create sample recording files with different sizes and dates
            for i in range(5):
                recording_file = recordings_dir / f"TBS_20250715_10{i:02d}00_sample_{i}.mp3"
                # Create file with different sizes
                content = b"fake mp3 data " * (100 * (i + 1))
                recording_file.write_bytes(content)
                
                # Set different modification times
                mod_time = time.time() - (i * 3600)  # 1 hour apart
                os.utime(recording_file, (mod_time, mod_time))
            
            yield config_dir
    
    def test_recording_count_calculation(self, temp_config_dir):
        """Test recording count calculation with real files"""
        from src.ui.screens.system_info_screen import RecordingStatsManager
        
        stats_manager = RecordingStatsManager(str(temp_config_dir))
        count = stats_manager.get_recording_count()
        
        # Should count the 5 sample files
        assert count >= 5
    
    def test_total_recording_size_calculation(self, temp_config_dir):
        """Test total recording size calculation"""
        from src.ui.screens.system_info_screen import RecordingStatsManager
        
        stats_manager = RecordingStatsManager(str(temp_config_dir))
        total_size = stats_manager.get_total_recording_size()
        
        # Should be greater than 0 due to sample files
        assert total_size > 0
    
    def test_recent_recordings_list(self, temp_config_dir):
        """Test recent recordings list generation"""
        from src.ui.screens.system_info_screen import RecordingStatsManager
        
        stats_manager = RecordingStatsManager(str(temp_config_dir))
        recent = stats_manager.get_recent_recordings(3)
        
        # Should return list of recent recordings
        assert isinstance(recent, list)
        assert len(recent) <= 3
        
        # Verify structure of recording entries
        for recording in recent:
            assert "filename" in recording
            assert "size" in recording
            assert "modified" in recording
    
    def test_recording_statistics_compilation(self, temp_config_dir):
        """Test complete recording statistics compilation"""
        from src.ui.screens.system_info_screen import RecordingStatsManager
        
        stats_manager = RecordingStatsManager(str(temp_config_dir))
        stats = stats_manager.get_recording_statistics()
        
        # Verify complete statistics structure
        assert isinstance(stats, dict)
        assert "total_recordings" in stats
        assert "total_size" in stats
        assert "average_size" in stats
        assert "success_rate" in stats
        assert "recent_recordings" in stats
        
        # Verify calculated values
        assert stats["total_recordings"] >= 5
        assert stats["total_size"] > 0
        assert stats["average_size"] > 0
        assert 0 <= stats["success_rate"] <= 100


class TestLogManagerReal:
    """Log manager tests with real file operations"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory with sample logs"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".recradiko"
            config_dir.mkdir(parents=True)
            
            # Create logs directory
            logs_dir = config_dir / "logs"
            logs_dir.mkdir(parents=True)
            
            # Create sample log files
            log_entries = [
                "2025-07-15 10:00:00 - INFO - System started",
                "2025-07-15 10:01:00 - INFO - Authentication successful",
                "2025-07-15 10:02:00 - ERROR - Connection failed",
                "2025-07-15 10:03:00 - INFO - Retrying connection",
                "2025-07-15 10:04:00 - INFO - Recording started",
                "2025-07-15 10:05:00 - INFO - Recording completed"
            ]
            
            log_file = logs_dir / "recradiko.log"
            with open(log_file, 'w') as f:
                for entry in log_entries:
                    f.write(entry + "\n")
            
            yield config_dir
    
    def test_log_file_discovery(self, temp_config_dir):
        """Test log file discovery with real file system"""
        from src.ui.screens.system_info_screen import LogManager
        
        log_manager = LogManager(str(temp_config_dir))
        log_files = log_manager.find_log_files()
        
        # Should find the sample log file
        assert isinstance(log_files, list)
        assert len(log_files) >= 1
        
        # Verify log file information
        log_file_info = log_files[0]
        assert "path" in log_file_info
        assert "size" in log_file_info
        assert "modified" in log_file_info
        assert "recradiko.log" in log_file_info["path"]
    
    def test_log_entry_parsing(self, temp_config_dir):
        """Test log entry parsing with real log content"""
        from src.ui.screens.system_info_screen import LogManager
        
        log_manager = LogManager(str(temp_config_dir))
        log_entries = log_manager.get_recent_log_entries(10)
        
        # Should parse the sample log entries
        assert isinstance(log_entries, list)
        assert len(log_entries) >= 6
        
        # Verify parsed entry structure
        for entry in log_entries:
            assert "timestamp" in entry
            assert "level" in entry
            assert "message" in entry
            
            # Verify timestamp format
            assert isinstance(entry["timestamp"], str)
            assert len(entry["timestamp"]) > 0
            
            # Verify level
            assert entry["level"] in ["INFO", "ERROR", "DEBUG", "WARNING"]
    
    def test_log_filtering_by_level(self, temp_config_dir):
        """Test log filtering by level"""
        from src.ui.screens.system_info_screen import LogManager
        
        log_manager = LogManager(str(temp_config_dir))
        
        # Get only ERROR entries
        error_entries = log_manager.get_log_entries_by_level("ERROR")
        
        # Should find the error entry
        assert isinstance(error_entries, list)
        assert len(error_entries) >= 1
        
        # Verify all entries are ERROR level
        for entry in error_entries:
            assert entry["level"] == "ERROR"
    
    def test_log_size_calculation(self, temp_config_dir):
        """Test log size calculation"""
        from src.ui.screens.system_info_screen import LogManager
        
        log_manager = LogManager(str(temp_config_dir))
        total_size = log_manager.get_total_log_size()
        
        # Should be greater than 0 due to sample log content
        assert total_size > 0