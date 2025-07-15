"""
Settings Screen for RecRadiko

Provides keyboard navigation interface for system settings management.
Supports region settings, audio quality, file paths, notifications, and more.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import tempfile
import shutil
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.ui.screen_base import ScreenBase
from src.ui.services.ui_service import UIService
from src.region_mapper import RegionMapper
from src.utils.base import LoggerMixin


class SettingType(Enum):
    """Setting types for different UI handling"""
    REGION = "region"
    AUDIO_QUALITY = "audio"
    FILE_PATH = "path"
    BOOLEAN = "boolean"
    SELECTION = "selection"
    ACTION = "action"


@dataclass
class SettingItem:
    """Setting item definition"""
    id: str
    title: str
    description: str
    current_value: Any
    default_value: Any
    setting_type: SettingType
    options: Optional[List[str]] = None
    validator: Optional[Callable] = None


class ConfigManager(LoggerMixin):
    """Configuration file management with real file operations"""
    
    DEFAULT_CONFIG = {
        "version": "2.0",
        "prefecture": "東京",
        "audio": {
            "format": "mp3",
            "bitrate": 256,
            "sample_rate": 48000
        },
        "recording": {
            "save_path": "~/Downloads/RecRadiko/",
            "id3_tags_enabled": True,
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
    
    def __init__(self, config_file: str = "~/.recradiko/config.json"):
        super().__init__()
        self.config_file = Path(config_file).expanduser()
        self.config_data: Dict[str, Any] = {}
        # Don't auto-load in constructor to allow setting config_file first
        # self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                    self.logger.info(f"Configuration loaded from {self.config_file}")
            else:
                # Create default config
                self.config_data = self.DEFAULT_CONFIG.copy()
                self._ensure_config_directory()
                self.save_config()
                self.logger.info(f"Created default configuration at {self.config_file}")
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Error loading config: {e}")
            # Fall back to defaults
            self.config_data = self.DEFAULT_CONFIG.copy()
            self._ensure_config_directory()
            try:
                self.save_config()
            except Exception:
                # If save fails, continue with defaults in memory
                pass
        
        return self.config_data
    
    def save_config(self) -> bool:
        """Save configuration to file"""
        try:
            self._ensure_config_directory()
            
            # Add timestamp
            self.config_data["updated_at"] = datetime.now().isoformat()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
        except IOError as e:
            self.logger.error(f"Error saving config: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting value using dot notation"""
        keys = key.split('.')
        value = self.config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set setting value using dot notation"""
        keys = key.split('.')
        target = self.config_data
        
        # Navigate to parent
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        # Set final value
        target[keys[-1]] = value
        self.logger.debug(f"Setting {key} = {value}")
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults"""
        try:
            self.config_data = self.DEFAULT_CONFIG.copy()
            return self.save_config()
        except Exception as e:
            self.logger.error(f"Error resetting to defaults: {e}")
            return False
    
    def export_settings(self, export_path: str) -> bool:
        """Export settings to file"""
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Settings exported to {export_path}")
            return True
        except IOError as e:
            self.logger.error(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, import_path: str) -> bool:
        """Import settings from file"""
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                self.logger.error(f"Import file not found: {import_path}")
                return False
            
            with open(import_file, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            # Validate imported data structure
            if not isinstance(imported_data, dict):
                self.logger.error("Invalid import file format")
                return False
            
            # Merge with current config
            self.config_data.update(imported_data)
            result = self.save_config()
            
            if result:
                self.logger.info(f"Settings imported from {import_path}")
            
            return result
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Error importing settings: {e}")
            return False
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate current configuration"""
        errors = []
        
        # Check required keys
        required_keys = ["prefecture", "audio", "recording", "notification"]
        for key in required_keys:
            if key not in self.config_data:
                errors.append(f"Missing required key: {key}")
        
        # Validate prefecture
        if "prefecture" in self.config_data:
            region_mapper = RegionMapper()
            if not region_mapper.get_area_id(self.config_data["prefecture"]):
                errors.append("Invalid prefecture setting")
        
        # Validate audio settings
        if "audio" in self.config_data:
            audio = self.config_data["audio"]
            if "format" in audio and audio["format"] not in ["mp3", "aac"]:
                errors.append("Invalid audio format")
            if "bitrate" in audio and not isinstance(audio["bitrate"], int):
                errors.append("Invalid audio bitrate")
        
        return len(errors) == 0, errors
    
    def _ensure_config_directory(self) -> None:
        """Ensure configuration directory exists"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)


class SettingValidator(LoggerMixin):
    """Setting value validation"""
    
    def __init__(self):
        super().__init__()
        self.region_mapper = RegionMapper()
    
    def validate_region(self, prefecture: str) -> Tuple[bool, str]:
        """Validate region setting"""
        if not prefecture or not isinstance(prefecture, str):
            return False, "都道府県名が指定されていません"
        
        area_id = self.region_mapper.get_area_id(prefecture)
        if not area_id:
            return False, f"無効な都道府県名です: {prefecture}"
        
        return True, ""
    
    def validate_audio_quality(self, format_str: str) -> Tuple[bool, str]:
        """Validate audio quality setting"""
        if not format_str or not isinstance(format_str, str):
            return False, "音質設定が指定されていません"
        
        try:
            # Parse format string like "MP3 256kbps, 48kHz"
            parts = format_str.replace(",", "").split()
            if len(parts) < 3:
                return False, "音質設定の形式が正しくありません"
            
            format_type = parts[0].lower()
            bitrate_str = parts[1]
            sample_rate_str = parts[2]
            
            # Validate format
            if format_type not in ["mp3", "aac"]:
                return False, f"サポートされていない音声フォーマットです: {format_type}"
            
            # Validate bitrate
            if not bitrate_str.endswith("kbps"):
                return False, "ビットレートの形式が正しくありません"
            
            bitrate = int(bitrate_str[:-4])
            if bitrate not in [128, 256, 320]:
                return False, f"サポートされていないビットレートです: {bitrate}"
            
            # Validate sample rate
            if not sample_rate_str.endswith("kHz"):
                return False, "サンプルレートの形式が正しくありません"
            
            sample_rate = int(sample_rate_str[:-3]) * 1000
            # Allow both 44000 (44kHz) and 44100 (44.1kHz) 
            if sample_rate not in [44000, 44100, 48000]:
                return False, f"サポートされていないサンプルレートです: {sample_rate}"
            
            return True, ""
        except (ValueError, IndexError) as e:
            return False, f"音質設定の解析に失敗しました: {e}"
    
    def validate_file_path(self, path: str) -> Tuple[bool, str]:
        """Validate file path setting"""
        if not path or not isinstance(path, str):
            return False, "ファイルパスが指定されていません"
        
        try:
            # Expand user path
            expanded_path = Path(path).expanduser()
            
            # Check if directory exists
            if not expanded_path.exists():
                return False, f"指定されたパスが存在しません: {path}"
            
            # Check if it's a directory
            if not expanded_path.is_dir():
                return False, f"指定されたパスはディレクトリではありません: {path}"
            
            # Check write permissions
            if not os.access(expanded_path, os.W_OK):
                return False, f"指定されたパスに書き込み権限がありません: {path}"
            
            return True, ""
        except Exception as e:
            return False, f"ファイルパスの検証中にエラーが発生しました: {e}"
    
    def validate_notification_setting(self, setting: str) -> Tuple[bool, str]:
        """Validate notification setting"""
        if not setting or not isinstance(setting, str):
            return False, "通知設定が指定されていません"
        
        valid_settings = ["無効", "macos_standard", "sound", "email"]
        if setting not in valid_settings:
            return False, f"無効な通知設定です: {setting}"
        
        return True, ""
    
    def validate_boolean_setting(self, value: Any) -> Tuple[bool, str]:
        """Validate boolean setting"""
        if value is None:
            return False, "設定値が指定されていません"
        
        if isinstance(value, bool):
            return True, ""
        
        if isinstance(value, str):
            if value.lower() in ["true", "false"]:
                return True, ""
        
        if isinstance(value, int):
            if value in [0, 1]:
                return True, ""
        
        return False, f"無効なブール値です: {value}"


class SettingsScreen(ScreenBase):
    """Settings management screen with keyboard navigation"""
    
    def __init__(self, config_file: str = "~/.recradiko/config.json"):
        super().__init__()
        self.set_title("設定管理")
        self.config_file = config_file
        self.config_manager = ConfigManager(config_file)
        self.config_manager.load_config()  # Explicitly load config
        self.region_mapper = RegionMapper()
        self.validator = SettingValidator()
        self.ui_service = UIService()
        self.setting_items: List[SettingItem] = []
        self.current_settings: Dict[str, Any] = {}
    
    def display_content(self) -> None:
        """Display settings menu content"""
        self.load_settings()
        
        # Create menu items from settings
        menu_items = []
        for item in self.setting_items:
            if item.setting_type == SettingType.ACTION:
                menu_items.append(f"{item.title}")
            else:
                menu_items.append(f"{item.title}: {item.current_value}")
        
        self.ui_service.set_menu_items(menu_items)
        self.ui_service.display_menu_with_highlight()
    
    def load_settings(self) -> bool:
        """Load settings from configuration file"""
        try:
            self.current_settings = self.config_manager.load_config()
            self.setting_items = self._initialize_setting_items()
            self.logger.info("Settings loaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            return False
    
    def save_settings(self) -> bool:
        """Save current settings to configuration file"""
        try:
            # Update config manager's data directly
            self.config_manager.config_data = self.current_settings.copy()
            
            result = self.config_manager.save_config()
            if result:
                self.logger.info("Settings saved successfully")
            return result
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset settings to default values"""
        try:
            result = self.config_manager.reset_to_defaults()
            if result:
                self.current_settings = self.config_manager.load_config()
                self.setting_items = self._initialize_setting_items()
                self.logger.info("Settings reset to defaults")
            return result
        except Exception as e:
            self.logger.error(f"Error resetting to defaults: {e}")
            return False
    
    def export_settings(self, export_path: str) -> bool:
        """Export settings to file"""
        return self.config_manager.export_settings(export_path)
    
    def import_settings(self, import_path: str) -> bool:
        """Import settings from file"""
        result = self.config_manager.import_settings(import_path)
        if result:
            self.current_settings = self.config_manager.load_config()
            self.setting_items = self._initialize_setting_items()
        return result
    
    def validate_all_settings(self) -> Tuple[bool, List[str]]:
        """Validate all current settings"""
        return self.config_manager.validate_config()
    
    def run_settings_workflow(self) -> bool:
        """Run settings management workflow"""
        try:
            while True:
                self.display_content()
                
                # Get user selection
                selected_option = self.ui_service.get_user_selection()
                if selected_option is None:
                    break
                
                # Handle selection
                if selected_option == "地域設定":
                    self.handle_region_setting()
                elif selected_option == "音質設定":
                    self.handle_audio_quality_setting()
                elif selected_option == "保存先":
                    self.handle_save_path_setting()
                elif selected_option == "録音後処理":
                    self.handle_id3_tags_setting()
                elif selected_option == "通知設定":
                    self.handle_notification_setting()
                elif selected_option == "設定をデフォルトに戻す":
                    self.handle_reset_defaults()
                elif selected_option == "設定ファイルエクスポート":
                    self.handle_export_settings()
                elif selected_option == "設定ファイルインポート":
                    self.handle_import_settings()
                else:
                    break
            
            return True
        except Exception as e:
            self.logger.error(f"Settings workflow error: {e}")
            return False
    
    def handle_region_setting(self) -> bool:
        """Handle region setting change"""
        try:
            current_region = self.current_settings.get("prefecture", "東京")
            self.ui_service.display_info(f"現在の地域: {current_region}")
            
            # Get new region input
            new_region = self.ui_service.get_text_input("新しい地域を入力してください（例: 大阪、北海道）: ")
            if not new_region:
                return False
            
            # Validate region
            is_valid, error = self.validator.validate_region(new_region)
            if not is_valid:
                self.ui_service.display_error(error)
                return False
            
            # Get normalized prefecture name
            area_id = self.region_mapper.get_area_id(new_region)
            normalized_name = self.region_mapper.get_prefecture_name(area_id)
            
            # Confirm change
            if self.ui_service.confirm_action(f"地域を「{normalized_name}」に変更しますか？"):
                self.current_settings["prefecture"] = normalized_name
                self.save_settings()
                self.ui_service.display_success(f"地域を「{normalized_name}」に変更しました")
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"Region setting error: {e}")
            self.ui_service.display_error("地域設定の変更中にエラーが発生しました")
            return False
    
    def handle_audio_quality_setting(self) -> bool:
        """Handle audio quality setting change"""
        # Implementation placeholder
        self.ui_service.display_info("音質設定機能は実装中です")
        return False
    
    def handle_save_path_setting(self) -> bool:
        """Handle save path setting change"""
        # Implementation placeholder
        self.ui_service.display_info("保存先設定機能は実装中です")
        return False
    
    def handle_id3_tags_setting(self) -> bool:
        """Handle ID3 tags setting change"""
        # Implementation placeholder
        self.ui_service.display_info("ID3タグ設定機能は実装中です")
        return False
    
    def handle_notification_setting(self) -> bool:
        """Handle notification setting change"""
        # Implementation placeholder
        self.ui_service.display_info("通知設定機能は実装中です")
        return False
    
    def handle_reset_defaults(self) -> bool:
        """Handle reset to defaults"""
        if self.ui_service.confirm_action("全ての設定をデフォルトに戻しますか？"):
            result = self.reset_to_defaults()
            if result:
                self.ui_service.display_success("設定をデフォルトに戻しました")
            else:
                self.ui_service.display_error("設定のリセットに失敗しました")
            return result
        return False
    
    def handle_export_settings(self) -> bool:
        """Handle settings export"""
        export_path = self.ui_service.get_text_input("エクスポート先パス: ")
        if export_path:
            result = self.export_settings(export_path)
            if result:
                self.ui_service.display_success(f"設定をエクスポートしました: {export_path}")
            else:
                self.ui_service.display_error("設定のエクスポートに失敗しました")
            return result
        return False
    
    def handle_import_settings(self) -> bool:
        """Handle settings import"""
        import_path = self.ui_service.get_text_input("インポート元パス: ")
        if import_path:
            result = self.import_settings(import_path)
            if result:
                self.ui_service.display_success(f"設定をインポートしました: {import_path}")
            else:
                self.ui_service.display_error("設定のインポートに失敗しました")
            return result
        return False
    
    def _initialize_setting_items(self) -> List[SettingItem]:
        """Initialize setting items"""
        return [
            SettingItem(
                id="region",
                title="地域設定",
                description="録音可能な地域を設定",
                current_value=self._get_current_region_display(),
                default_value="東京",
                setting_type=SettingType.REGION
            ),
            SettingItem(
                id="audio_quality",
                title="音質設定",
                description="録音音質を設定",
                current_value=self._get_current_audio_quality(),
                default_value="MP3 256kbps, 48kHz",
                setting_type=SettingType.AUDIO_QUALITY,
                options=["MP3 128kbps, 44kHz", "MP3 256kbps, 48kHz", "AAC 128kbps, 44kHz", "AAC 256kbps, 48kHz"]
            ),
            SettingItem(
                id="save_path",
                title="保存先",
                description="録音ファイルの保存先",
                current_value=self._get_current_save_path(),
                default_value="~/Downloads/RecRadiko/",
                setting_type=SettingType.FILE_PATH
            ),
            SettingItem(
                id="id3_tags",
                title="録音後処理",
                description="ID3タグの自動付与",
                current_value=self._get_current_id3_setting(),
                default_value=True,
                setting_type=SettingType.BOOLEAN
            ),
            SettingItem(
                id="notifications",
                title="通知設定",
                description="完了通知の設定",
                current_value=self._get_current_notification_setting(),
                default_value="macos_standard",
                setting_type=SettingType.SELECTION,
                options=["無効", "macos_standard", "sound", "email"]
            ),
            SettingItem(
                id="reset_defaults",
                title="設定をデフォルトに戻す",
                description="全設定を初期値に戻す",
                current_value=None,
                default_value=None,
                setting_type=SettingType.ACTION
            ),
            SettingItem(
                id="export_settings",
                title="設定ファイルエクスポート",
                description="設定をファイルに保存",
                current_value=None,
                default_value=None,
                setting_type=SettingType.ACTION
            ),
            SettingItem(
                id="import_settings",
                title="設定ファイルインポート",
                description="設定をファイルから読み込み",
                current_value=None,
                default_value=None,
                setting_type=SettingType.ACTION
            )
        ]
    
    def _get_current_region_display(self) -> str:
        """Get current region display name"""
        return self.current_settings.get("prefecture", "東京")
    
    def _get_current_audio_quality(self) -> str:
        """Get current audio quality display"""
        audio = self.current_settings.get("audio", {})
        format_type = audio.get("format", "mp3").upper()
        bitrate = audio.get("bitrate", 256)
        sample_rate = audio.get("sample_rate", 48000) // 1000
        return f"{format_type} {bitrate}kbps, {sample_rate}kHz"
    
    def _get_current_save_path(self) -> str:
        """Get current save path display"""
        recording = self.current_settings.get("recording", {})
        return recording.get("save_path", "~/Downloads/RecRadiko/")
    
    def _get_current_id3_setting(self) -> bool:
        """Get current ID3 tags setting"""
        recording = self.current_settings.get("recording", {})
        return recording.get("id3_tags_enabled", True)
    
    def _get_current_notification_setting(self) -> str:
        """Get current notification setting"""
        notification = self.current_settings.get("notification", {})
        return notification.get("type", "macos_standard")