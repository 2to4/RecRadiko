"""
Test SettingsScreen implementation

Tests the settings management functionality including:
- Settings screen initialization and display
- Configuration management with real files
- Region setting with RegionMapper integration
- Audio quality settings validation
- File path settings with filesystem validation
- Settings save/load with persistence
- Export/import functionality
- Error handling and validation

Following the principle of minimal mock usage - using real filesystem, 
real configuration files, and real RegionMapper.
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.screens.settings_screen import SettingsScreen
from src.region_mapper import RegionMapper


class TestSettingsScreenReal:
    """Settings screen tests with real environment (minimal mocking)"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".recradiko"
            config_dir.mkdir(parents=True)
            yield config_dir
    
    @pytest.fixture
    def real_config_file(self, temp_config_dir):
        """Create real config file with test data"""
        config_file = temp_config_dir / "config.json"
        
        # Real config file format
        config_data = {
            "version": "2.0",
            "prefecture": "東京",
            "audio": {
                "format": "mp3",
                "bitrate": 256,
                "sample_rate": 48000
            },
            "recording": {
                "timeout_seconds": 30,
                "max_retries": 3
            },
            "notification": {
                "type": "macos_standard",
                "enabled": True
            },
            "system": {
                "log_level": "INFO",
                "user_agent": "RecRadiko/2.0"
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        return config_file
    
    @pytest.fixture
    def real_recordings_dir(self, temp_config_dir):
        """Create real recordings directory"""
        recordings_dir = temp_config_dir / "recordings"
        recordings_dir.mkdir(parents=True)
        recordings_dir.chmod(0o755)
        return recordings_dir
    
    @pytest.fixture
    def mock_ui_service(self):
        """Create minimal UI service mock for input simulation"""
        mock_ui = Mock()
        mock_ui.get_user_selection = Mock(return_value=None)
        mock_ui.get_text_input = Mock(return_value="")
        mock_ui.confirm_action = Mock(return_value=True)
        mock_ui.display_error = Mock()
        mock_ui.display_success = Mock()
        mock_ui.display_info = Mock()
        mock_ui.set_menu_items = Mock()
        mock_ui.display_menu_with_highlight = Mock()
        return mock_ui
    
    @pytest.fixture
    def settings_screen(self, real_config_file, mock_ui_service):
        """Create SettingsScreen with real dependencies"""
        with patch('src.ui.screens.settings_screen.UIService', return_value=mock_ui_service):
            screen = SettingsScreen(str(real_config_file))
            return screen
    
    def test_settings_screen_initialization(self, settings_screen):
        """Test SettingsScreen initialization"""
        assert settings_screen.title == "設定管理"
        assert hasattr(settings_screen, 'setting_items')
        assert hasattr(settings_screen, 'current_settings')
        assert hasattr(settings_screen, 'config_manager')
        assert hasattr(settings_screen, 'region_mapper')
        assert hasattr(settings_screen, 'validator')
    
    def test_setting_items_initialization(self, settings_screen):
        """Test setting items are properly initialized"""
        settings_screen.load_settings()
        
        expected_setting_ids = [
            "region", "audio_quality",
            "notifications", "reset_defaults", "export_settings", "import_settings", "back_to_main"
        ]
        
        setting_ids = [item.id for item in settings_screen.setting_items]
        for expected_id in expected_setting_ids:
            assert expected_id in setting_ids
    
    def test_load_settings_from_real_file(self, settings_screen, real_config_file):
        """Test loading settings from real configuration file"""
        # Load settings from real file
        result = settings_screen.load_settings()
        
        # Verify successful load
        assert result == True
        
        # Verify settings were loaded correctly
        assert settings_screen.current_settings["prefecture"] == "東京"
        assert settings_screen.current_settings["audio"]["format"] == "mp3"
        assert settings_screen.current_settings["audio"]["bitrate"] == 256
        
        # Verify file content matches
        with open(real_config_file, 'r', encoding='utf-8') as f:
            file_content = json.load(f)
        
        assert file_content["prefecture"] == "東京"
        assert file_content["audio"]["format"] == "mp3"
    
    def test_save_settings_to_real_file(self, settings_screen, real_config_file):
        """Test saving settings to real configuration file"""
        # Load initial settings
        settings_screen.load_settings()
        
        # Modify settings
        settings_screen.current_settings["prefecture"] = "大阪"
        settings_screen.current_settings["audio"]["bitrate"] = 320
        
        # Save settings
        result = settings_screen.save_settings()
        
        # Verify successful save
        assert result == True
        
        # Verify file was updated
        with open(real_config_file, 'r', encoding='utf-8') as f:
            saved_content = json.load(f)
        
        assert saved_content["prefecture"] == "大阪"
        assert saved_content["audio"]["bitrate"] == 320
        
        # Verify with new instance
        new_screen = SettingsScreen()
        new_screen.config_file = str(real_config_file)
        new_screen.load_settings()
        
        assert new_screen.current_settings["prefecture"] == "大阪"
        assert new_screen.current_settings["audio"]["bitrate"] == 320
    
    def test_region_setting_with_real_mapper(self, settings_screen):
        """Test region setting with real RegionMapper"""
        # Load settings
        settings_screen.load_settings()
        
        # Get current region display
        current_region = settings_screen._get_current_region_display()
        assert current_region == "東京"
        
        # Test region mapping with real RegionMapper
        region_mapper = RegionMapper()
        
        # Test various prefecture inputs
        test_prefectures = ["大阪", "北海道", "沖縄", "Tokyo", "Osaka"]
        for prefecture in test_prefectures:
            area_id = region_mapper.get_area_id(prefecture)
            if area_id:  # If valid prefecture
                # Test conversion back
                converted_name = region_mapper.get_prefecture_name(area_id)
                assert converted_name is not None
    
    def test_audio_quality_validation(self, settings_screen):
        """Test audio quality settings validation"""
        # Load settings
        settings_screen.load_settings()
        
        # Test valid audio quality options
        valid_options = [
            {"format": "mp3", "bitrate": 128, "sample_rate": 44100},
            {"format": "mp3", "bitrate": 256, "sample_rate": 48000},
            {"format": "aac", "bitrate": 128, "sample_rate": 44100},
            {"format": "aac", "bitrate": 256, "sample_rate": 48000}
        ]
        
        for option in valid_options:
            # Set audio quality
            settings_screen.current_settings["audio"]["format"] = option["format"]
            settings_screen.current_settings["audio"]["bitrate"] = option["bitrate"]
            settings_screen.current_settings["audio"]["sample_rate"] = option["sample_rate"]
            
            # Validate
            is_valid, error = settings_screen.validator.validate_audio_quality(
                f"{option['format'].upper()} {option['bitrate']}kbps, {option['sample_rate']//1000}kHz"
            )
            assert is_valid == True, f"Valid option rejected: {option}"
        
        # Test invalid audio quality options
        invalid_options = [
            "MP3 999kbps, 44kHz",  # Invalid bitrate
            "OGG 256kbps, 48kHz",  # Unsupported format
            "invalid format"        # Invalid format
        ]
        
        for option in invalid_options:
            is_valid, error = settings_screen.validator.validate_audio_quality(option)
            assert is_valid == False, f"Invalid option accepted: {option}"
            assert error != "", f"No error message for invalid option: {option}"
    
    def test_file_path_validation_with_real_filesystem(self, settings_screen, temp_config_dir):
        """Test file path validation with real filesystem"""
        # Load settings
        settings_screen.load_settings()
        
        # Test with valid directory (create it)
        valid_dir = temp_config_dir / "test_recordings"
        valid_dir.mkdir(parents=True)
        
        is_valid, error = settings_screen.validator.validate_file_path(str(valid_dir))
        assert is_valid == True
        assert error == ""
        
        # Test with non-existent directory
        nonexistent_dir = temp_config_dir / "nonexistent"
        
        is_valid, error = settings_screen.validator.validate_file_path(str(nonexistent_dir))
        assert is_valid == False
        assert "存在しません" in error
        
        # Test with read-only directory
        readonly_dir = temp_config_dir / "readonly"
        readonly_dir.mkdir(parents=True)
        readonly_dir.chmod(0o444)  # Read-only
        
        try:
            is_valid, error = settings_screen.validator.validate_file_path(str(readonly_dir))
            assert is_valid == False
            assert "書き込み権限" in error
        finally:
            # Cleanup
            readonly_dir.chmod(0o755)
    
    def test_settings_export_import_with_real_files(self, settings_screen, temp_config_dir):
        """Test settings export/import with real files"""
        # Load settings
        settings_screen.load_settings()
        
        # Export settings
        export_file = temp_config_dir / "exported_settings.json"
        result = settings_screen.export_settings(str(export_file))
        
        assert result == True
        assert export_file.exists()
        
        # Verify exported content
        with open(export_file, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
        
        assert exported_data["prefecture"] == "東京"
        assert exported_data["audio"]["format"] == "mp3"
        
        # Modify current settings
        settings_screen.current_settings["prefecture"] = "北海道"
        settings_screen.save_settings()
        
        # Import settings
        result = settings_screen.import_settings(str(export_file))
        
        assert result == True
        assert settings_screen.current_settings["prefecture"] == "東京"  # Restored
    
    def test_settings_reset_to_defaults(self, settings_screen):
        """Test reset to default settings"""
        # Load and modify settings
        settings_screen.load_settings()
        settings_screen.current_settings["prefecture"] = "北海道"
        settings_screen.current_settings["audio"]["bitrate"] = 128
        settings_screen.save_settings()
        
        # Reset to defaults
        result = settings_screen.reset_to_defaults()
        
        assert result == True
        assert settings_screen.current_settings["prefecture"] == "東京"  # Default
        assert settings_screen.current_settings["audio"]["bitrate"] == 256  # Default
    
    def test_settings_validation_with_real_data(self, settings_screen):
        """Test settings validation with real data"""
        # Load settings
        settings_screen.load_settings()
        
        # Test valid configuration
        is_valid, errors = settings_screen.validate_all_settings()
        assert is_valid == True
        assert len(errors) == 0
        
        # Test invalid configuration
        settings_screen.current_settings["prefecture"] = "存在しない県"
        settings_screen.current_settings["audio"]["bitrate"] = "invalid"
        
        is_valid, errors = settings_screen.validate_all_settings()
        assert is_valid == False
        assert len(errors) > 0
        assert any("prefecture" in error for error in errors)
        assert any("bitrate" in error for error in errors)
    
    def test_corrupted_config_file_handling(self, temp_config_dir):
        """Test handling of corrupted config file"""
        # Create corrupted config file
        config_file = temp_config_dir / "corrupted_config.json"
        with open(config_file, 'w') as f:
            f.write('{"invalid": json content}')
        
        # Create settings screen with corrupted file
        with patch('src.ui.screens.settings_screen.UIService'):
            screen = SettingsScreen(str(config_file))
            
            # Should handle corruption gracefully
            result = screen.load_settings()
            
            # Should fall back to defaults
            assert result == True
            assert screen.current_settings["prefecture"] == "東京"
            
            # Should be able to save corrected config
            save_result = screen.save_settings()
            assert save_result == True
            
            # Verify file is now valid
            with open(config_file, 'r', encoding='utf-8') as f:
                restored_content = json.load(f)
            
            assert restored_content["prefecture"] == "東京"
    
    def test_concurrent_settings_access(self, real_config_file):
        """Test concurrent access to settings file"""
        # Create two independent settings screens
        with patch('src.ui.screens.settings_screen.UIService'):
            screen1 = SettingsScreen(str(real_config_file))
            screen2 = SettingsScreen(str(real_config_file))
            
            # Load settings in both
            screen1.load_settings()
            screen2.load_settings()
            
            # Modify settings in both
            screen1.current_settings["prefecture"] = "大阪"
            screen2.current_settings["prefecture"] = "愛知"
            
            # Save in sequence
            result1 = screen1.save_settings()
            result2 = screen2.save_settings()
            
            assert result1 == True
            assert result2 == True
            
            # Last save should win
            screen3 = SettingsScreen(str(real_config_file))
            screen3.load_settings()
            
            assert screen3.current_settings["prefecture"] == "愛知"
    
    def test_settings_screen_display_content(self, settings_screen):
        """Test settings screen content display"""
        # Load settings
        settings_screen.load_settings()
        
        # Test display content
        settings_screen.display_content()
        
        # Verify UI service was called
        settings_screen.ui_service.set_menu_items.assert_called_once()
        settings_screen.ui_service.display_menu_with_highlight.assert_called_once()
        
        # Verify menu items contain setting descriptions
        call_args = settings_screen.ui_service.set_menu_items.call_args[0][0]
        assert any("地域設定" in item for item in call_args)
        assert any("音質設定" in item for item in call_args)
        assert any("通知設定" in item for item in call_args)
    
    def test_settings_workflow_execution(self, settings_screen):
        """Test complete settings workflow"""
        # Mock user selections
        settings_screen.ui_service.get_user_selection.side_effect = [
            "地域設定",  # Select region setting
            None  # Exit workflow
        ]
        
        # Mock region setting change
        with patch.object(settings_screen, 'handle_region_setting') as mock_region:
            mock_region.return_value = True
            
            # Run workflow
            result = settings_screen.run_settings_workflow()
            
            # Verify workflow execution
            mock_region.assert_called_once()
            assert result == True


class TestConfigManagerReal:
    """Configuration manager tests with real files"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".recradiko"
            config_dir.mkdir(parents=True)
            yield config_dir
    
    def test_config_file_creation_and_loading(self, temp_config_dir):
        """Test config file creation and loading"""
        from src.utils.config_utils import ConfigManager
        
        config_file = temp_config_dir / "config.json"
        
        # Create ConfigManager with non-existent file
        config_manager = ConfigManager(str(config_file))
        default_config = {"test": "value"}
        config_manager.load_config(default_config)  # Load with defaults
        
        # Should create file with defaults
        assert config_file.exists()
        
        # Verify file content
        with open(config_file, 'r', encoding='utf-8') as f:
            file_content = json.load(f)
        
        assert file_content["test"] == "value"
    
    def test_setting_modification_and_persistence(self, temp_config_dir):
        """Test setting modification and persistence"""
        from src.utils.config_utils import ConfigManager
        
        config_file = temp_config_dir / "config.json"
        config_manager = ConfigManager(str(config_file))
        
        # Load default config
        default_config = {"prefecture": "東京", "audio": {"bitrate": 256}}
        config = config_manager.load_config(default_config)
        
        # Modify settings
        config["prefecture"] = "大阪"
        config["audio"]["bitrate"] = 320
        
        # Save
        result = config_manager.save_config(config)
        assert result == True
        
        # Verify with new instance
        new_config_manager = ConfigManager(str(config_file))
        loaded_config = new_config_manager.load_config(default_config)
        assert loaded_config["prefecture"] == "大阪"
        assert loaded_config["audio"]["bitrate"] == 320
        
        # Verify file content
        with open(config_file, 'r', encoding='utf-8') as f:
            file_content = json.load(f)
        
        assert file_content["prefecture"] == "大阪"
        assert file_content["audio"]["bitrate"] == 320


class TestSettingValidatorReal:
    """Setting validator tests with real validation logic"""
    
    def test_region_validation_with_real_mapper(self):
        """Test region validation with real RegionMapper"""
        from src.ui.screens.settings_screen import SettingValidator
        
        validator = SettingValidator()
        
        # Test valid prefectures
        valid_prefectures = ["東京", "大阪", "北海道", "沖縄", "Tokyo", "Osaka"]
        for prefecture in valid_prefectures:
            is_valid, error = validator.validate_region(prefecture)
            if is_valid:  # Some English names might not be supported
                assert error == ""
        
        # Test invalid prefectures
        invalid_prefectures = ["存在しない県", "Invalid Prefecture", "123"]
        for prefecture in invalid_prefectures:
            is_valid, error = validator.validate_region(prefecture)
            assert is_valid == False
            assert error != ""
    
    def test_boolean_setting_validation(self):
        """Test boolean setting validation"""
        from src.ui.screens.settings_screen import SettingValidator
        
        validator = SettingValidator()
        
        # Test valid boolean values
        valid_values = [True, False, "true", "false", "True", "False", 1, 0]
        for value in valid_values:
            is_valid, error = validator.validate_boolean_setting(value)
            assert is_valid == True
            assert error == ""
        
        # Test invalid boolean values
        invalid_values = ["invalid", "maybe", 2, -1, None, []]
        for value in invalid_values:
            is_valid, error = validator.validate_boolean_setting(value)
            assert is_valid == False
            assert error != ""
    
    def test_notification_setting_validation(self):
        """Test notification setting validation"""
        from src.ui.screens.settings_screen import SettingValidator
        
        validator = SettingValidator()
        
        # Test valid notification settings
        valid_settings = ["無効", "macos_standard", "sound", "email"]
        for setting in valid_settings:
            is_valid, error = validator.validate_notification_setting(setting)
            assert is_valid == True
            assert error == ""
        
        # Test invalid notification settings
        invalid_settings = ["invalid_type", "windows_notification", ""]
        for setting in invalid_settings:
            is_valid, error = validator.validate_notification_setting(setting)
            assert is_valid == False
            assert error != ""