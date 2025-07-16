"""
Settings Screen for RecRadiko

Provides keyboard navigation interface for system settings management.
Supports region settings, audio quality, file paths, and more.
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
from src.utils.config_utils import ConfigManager


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

# ConfigManagerクラスは統一設定管理（src/utils/config_utils.py）に移行しました


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
    
    DEFAULT_CONFIG = {
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
        "system": {
            "log_level": "INFO",
            "user_agent": "RecRadiko/2.0"
        }
    }
    
    def __init__(self, config_file: str = "config.json"):
        super().__init__()
        self.set_title("設定管理")
        self.config_file = Path(config_file).expanduser()
        # 統一設定管理を使用
        self.config_manager = ConfigManager(self.config_file)
        self.config_data = self.config_manager.load_config({})
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
            self.current_settings = self.config_data.copy()
            self.setting_items = self._initialize_setting_items()
            self.logger.info("Settings loaded successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            return False
    
    def save_settings(self) -> bool:
        """Save current settings to configuration file"""
        try:
            # 統一設定管理を使用して保存
            result = self.config_manager.save_config(self.current_settings)
            if result:
                self.config_data = self.current_settings.copy()
                self.logger.info("Settings saved successfully")
            return result
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """Reset settings to default values"""
        try:
            # デフォルト設定を設定
            self.current_settings = self.DEFAULT_CONFIG.copy()
            result = self.config_manager.save_config(self.current_settings)
            if result:
                self.config_data = self.current_settings.copy()
                self.setting_items = self._initialize_setting_items()
                self.logger.info("Settings reset to defaults")
            return result
        except Exception as e:
            self.logger.error(f"Error resetting to defaults: {e}")
            return False
    
    def export_settings(self, export_path: str) -> bool:
        """Export settings to file"""
        return self.config_manager.export_config(export_path, self.current_settings)
    
    def import_settings(self, import_path: str) -> bool:
        """Import settings from file"""
        imported_config = self.config_manager.import_config(import_path)
        if imported_config:
            self.current_settings = imported_config
            self.config_data = imported_config.copy()
            self.setting_items = self._initialize_setting_items()
            return True
        return False
    
    def validate_all_settings(self) -> Tuple[bool, List[str]]:
        """Validate all current settings"""
        return self._validate_config_data(self.current_settings)
    
    def _validate_config_data(self, config_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration data"""
        errors = []
        
        # Check required keys
        required_keys = ["prefecture", "audio", "recording"]
        for key in required_keys:
            if key not in config_data:
                errors.append(f"Missing required key: {key}")
        
        # Validate prefecture
        if "prefecture" in config_data:
            if not self.region_mapper.get_area_id(config_data["prefecture"]):
                errors.append("Invalid prefecture setting")
        
        # Validate audio settings
        if "audio" in config_data:
            audio = config_data["audio"]
            if "format" in audio and audio["format"] not in ["mp3", "aac"]:
                errors.append("Invalid audio format")
            if "bitrate" in audio and not isinstance(audio["bitrate"], int):
                errors.append("Invalid audio bitrate")
        
        return len(errors) == 0, errors
    
    def run_settings_workflow(self) -> bool:
        """Run settings management workflow"""
        try:
            while True:
                self.display_content()
                
                # Get user selection
                selected_option = self.ui_service.get_user_selection()
                if selected_option is None:
                    break
                
                # Get the selected index to find the corresponding setting item
                selected_index = self.ui_service.get_selected_index()
                if selected_index < len(self.setting_items):
                    selected_item = self.setting_items[selected_index]
                    
                    # Handle selection based on setting ID
                    if selected_item.id == "region":
                        self.handle_region_setting()
                    elif selected_item.id == "audio_quality":
                        self.handle_audio_quality_setting()
                    elif selected_item.id == "reset_defaults":
                        self.handle_reset_defaults()
                    elif selected_item.id == "export_settings":
                        self.handle_export_settings()
                    elif selected_item.id == "import_settings":
                        self.handle_import_settings()
                    elif selected_item.id == "back_to_main":
                        break  # メインメニューに戻る
                    else:
                        break
                else:
                    break
            
            return True
        except Exception as e:
            self.logger.error(f"Settings workflow error: {e}")
            return False
    
    def handle_region_setting(self) -> bool:
        """Handle region setting change using region selection screen"""
        try:
            from .region_select_screen import RegionSelectScreen
            
            # 地域選択画面を起動
            region_screen = RegionSelectScreen(str(self.config_file))
            result = region_screen.run_region_selection_workflow()
            
            if result:
                # 設定が変更された可能性があるので、設定を再読み込み
                self.config_data = self.config_manager.load_config({})
                self.current_settings = self.config_data.copy()
                self.logger.info("地域設定画面から復帰、設定を再読み込み")
                return True
            else:
                self.logger.info("地域設定画面がキャンセルされました")
                return False
            
        except Exception as e:
            self.logger.error(f"Region setting error: {e}")
            self.ui_service.display_error("地域設定の変更中にエラーが発生しました")
            return False
    
    def handle_audio_quality_setting(self) -> bool:
        """Handle audio quality setting change using audio quality selection screen"""
        try:
            from .audio_quality_screen import AudioQualityScreen
            
            # 音質設定画面を起動
            audio_screen = AudioQualityScreen(str(self.config_file))
            result = audio_screen.run_audio_quality_workflow()
            
            if result:
                # 設定が変更された可能性があるので、設定を再読み込み
                self.config_data = self.config_manager.load_config({})
                self.current_settings = self.config_data.copy()
                self.logger.info("音質設定画面から復帰、設定を再読み込み")
                return True
            else:
                self.logger.info("音質設定画面がキャンセルされました")
                return False
            
        except Exception as e:
            self.logger.error(f"Audio quality setting error: {e}")
            self.ui_service.display_error("音質設定の変更中にエラーが発生しました")
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
            ),
            SettingItem(
                id="back_to_main",
                title="メインメニューに戻る",
                description="設定画面を終了してメインメニューに戻る",
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
    
    
