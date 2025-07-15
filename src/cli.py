"""
CLIインターフェースモジュール

このモジュールはRecRadikoのキーボードナビゲーションUIを提供します。
- キーボードナビゲーションUI
- 設定管理
- システム情報表示
"""

import argparse
import sys
import json
import logging
import signal
import threading
import time
import atexit
import warnings
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from .auth import RadikoAuthenticator, AuthenticationError
from .program_info import ProgramInfoManager, ProgramInfoError
from .streaming import StreamingManager, StreamingError
from .error_handler import ErrorHandler, handle_error
from .logging_config import setup_logging
from .utils.base import LoggerMixin
from .region_mapper import RegionMapper
from .timefree_recorder import TimeFreeRecorder
from .program_history import ProgramHistoryManager


class RecRadikoCLI(LoggerMixin):
    """RecRadiko CLIメインクラス（キーボードUI専用）"""
    
    VERSION = "1.0.0"
    UI_VERSION = "2.0.0"
    
    def __init__(self, 
                 config_path: str = "config.json",
                 auth_manager: Optional[RadikoAuthenticator] = None,
                 program_info_manager: Optional[ProgramInfoManager] = None,
                 streaming_manager: Optional[StreamingManager] = None,
                 error_handler: Optional[ErrorHandler] = None,
                 config_file: Optional[str] = None):
        
        super().__init__()  # LoggerMixin初期化
        
        # 設定ファイルパス（テスト用）
        if config_file:
            self.config_path = Path(config_file)
        else:
            self.config_path = Path(config_path)
        
        # 警告フィルター設定（UserWarning抑制）
        self._setup_warning_filters()
        
        self.config = self._load_config()
        
        # 詳細ログ設定
        self._setup_logging()
        
        # コンポーネント初期化（依存性注入対応）
        self.auth_manager = auth_manager
        self.program_info_manager = program_info_manager  
        self.streaming_manager = streaming_manager
        self.error_handler = error_handler
        
        # タイムフリー専用コンポーネント
        self.timefree_recorder = None
        self.program_history_manager = None
        
        # 後方互換性のため
        self.authenticator = self.auth_manager
        self.program_manager = self.program_info_manager
        
        # 依存性注入されていない場合はデフォルト初期化
        if not self.auth_manager:
            self._initialize_default_components()
        
        # 全てのコンポーネントが注入されている場合は初期化をスキップ
        self._all_components_injected = all([
            self.auth_manager,
            self.program_info_manager,
            self.streaming_manager,
            self.error_handler
        ])
        
        # 停止フラグ
        self.stop_event = threading.Event()
        
        # シグナルハンドラー設定
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _initialize_default_components(self):
        """デフォルトコンポーネントを初期化"""
        self._initialize_components()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込み（都道府県名→地域ID自動変換対応）"""
        default_config = {
            "area_id": "JP13",
            "prefecture": "",
            "premium_username": "",
            "premium_password": "",
            "output_dir": "./recordings",
            "default_format": "mp3",
            "default_bitrate": 128,
            "max_concurrent_recordings": 4,
            "auto_cleanup_enabled": True,
            "retention_days": 30,
            "min_free_space_gb": 10.0,
            "notification_enabled": True,
            "notification_minutes": [5, 1],
            "log_level": "INFO",
            "log_file": "recradiko.log",
            "max_log_size_mb": 100,
            "request_timeout": 30,
            "max_retries": 3
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                default_config.update(config)
                self._process_prefecture_setting(default_config)
            else:
                self._save_config(default_config)
                
            return default_config
            
        except Exception as e:
            self.logger.error(f"設定ファイル読み込みエラー: {e}")
            return default_config
    
    def _process_prefecture_setting(self, config: Dict[str, Any]) -> None:
        """都道府県名から地域IDを自動設定"""
        try:
            prefecture = config.get("prefecture", "").strip()
            
            if prefecture:
                area_id = RegionMapper.get_area_id(prefecture)
                
                if area_id:
                    original_area_id = config.get("area_id", "")
                    config["area_id"] = area_id
                    
                    prefecture_ja = RegionMapper.get_prefecture_name(area_id)
                    self.logger.info(f"都道府県設定から地域ID自動設定: {prefecture} -> {area_id} ({prefecture_ja})")
                    
                    if original_area_id and original_area_id != area_id:
                        self.logger.warning(
                            f"地域ID設定を上書き: {original_area_id} -> {area_id} "
                            f"(都道府県設定: {prefecture})"
                        )
                    
                else:
                    self.logger.warning(f"不明な都道府県名: '{prefecture}' - 利用可能な都道府県名を確認してください")
                    self._show_available_prefectures()
            
            elif config.get("area_id"):
                area_id = config["area_id"]
                if not RegionMapper.validate_area_id(area_id):
                    self.logger.warning(f"不正な地域ID: {area_id} - デフォルト地域ID（JP13：東京）を使用")
                    config["area_id"] = RegionMapper.get_default_area_id()
            
            else:
                config["area_id"] = RegionMapper.get_default_area_id()
                self.logger.info(f"地域設定がありません - デフォルト地域ID（JP13：東京）を使用")
            
        except Exception as e:
            self.logger.error(f"都道府県設定処理エラー: {e}")
            config["area_id"] = RegionMapper.get_default_area_id()
    
    def _show_available_prefectures(self) -> None:
        """利用可能な都道府県名を表示"""
        try:
            prefectures = RegionMapper.list_all_prefectures()
            self.logger.info("利用可能な都道府県名:")
            
            regions = {}
            for area_id, info in RegionMapper.REGION_INFO.items():
                region = info.region_name
                if region not in regions:
                    regions[region] = []
                regions[region].append(f"{info.prefecture_ja} ({area_id})")
            
            for region, prefs in regions.items():
                self.logger.info(f"  {region}: {', '.join(prefs)}")
            
            self.logger.info("設定例: \"prefecture\": \"大阪\" または \"prefecture\": \"Osaka\"")
            
        except Exception as e:
            self.logger.error(f"都道府県一覧表示エラー: {e}")
    
    def get_current_prefecture_info(self) -> Dict[str, str]:
        """現在の地域設定情報を取得"""
        area_id = self.config.get("area_id", "JP13")
        region_info = RegionMapper.get_region_info(area_id)
        
        if region_info:
            return {
                "area_id": area_id,
                "prefecture_ja": region_info.prefecture_ja,
                "prefecture_en": region_info.prefecture_en,
                "region_name": region_info.region_name,
                "major_stations": region_info.major_stations
            }
        else:
            return {
                "area_id": area_id,
                "prefecture_ja": "不明",
                "prefecture_en": "Unknown",
                "region_name": "不明",
                "major_stations": []
            }
    
    def _save_config(self, config: Dict[str, Any]):
        """設定ファイルを保存"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"設定ファイル保存エラー: {e}")
    
    def _setup_logging(self, verbose=False):
        """ログ設定"""
        try:
            log_level = self.config.get('log_level', 'INFO')
            log_file = self.config.get('log_file', 'recradiko.log')
            max_log_size = self.config.get('max_log_size_mb', 100) * 1024 * 1024
            
            console_output = verbose
            
            setup_logging(
                log_level=log_level,
                log_file=log_file,
                max_log_size=max_log_size,
                console_output=console_output
            )
        except Exception:
            setup_logging(console_output=False)
    
    def _setup_warning_filters(self):
        """警告フィルターの設定"""
        try:
            warnings.filterwarnings('ignore', category=UserWarning)
            warnings.filterwarnings('ignore', category=UserWarning, module='urllib3.*')
            warnings.filterwarnings('ignore', category=UserWarning, module='readline.*')
            warnings.filterwarnings('ignore', category=UserWarning, module='requests.*')
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
            warnings.filterwarnings('ignore', message='.*SSL.*')
            warnings.filterwarnings('ignore', message='.*certificate.*')
            
        except Exception as e:
            pass
    
    def _signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        self.logger.info(f"シグナル受信: {signum}")
        self.stop_event.set()
        self._cleanup()
        sys.exit(0)
    
    def _initialize_components(self):
        """コンポーネントを初期化"""
        try:
            if self.error_handler is None:
                self.error_handler = ErrorHandler(
                    log_file="error.log",
                    notification_enabled=self.config.get('notification_enabled', True)
                )
            
            if self.auth_manager is None:
                self.authenticator = RadikoAuthenticator()
                self.auth_manager = self.authenticator
            else:
                self.authenticator = self.auth_manager
            
            if self.program_info_manager is None:
                self.program_manager = ProgramInfoManager(
                    area_id=self.config.get('area_id', 'JP13'),
                    authenticator=self.authenticator
                )
                self.program_info_manager = self.program_manager
            else:
                self.program_manager = self.program_info_manager
            
            if self.timefree_recorder is None:
                self.timefree_recorder = TimeFreeRecorder(self.authenticator)
            
            if self.program_history_manager is None:
                self.program_history_manager = ProgramHistoryManager(self.authenticator)
            
            self.logger.info("コンポーネント初期化完了")
            
        except Exception as e:
            print(f"コンポーネント初期化エラー: {e}")
            if self.error_handler:
                handle_error(e)
            sys.exit(1)
    
    def _cleanup(self):
        """リソースのクリーンアップ"""
        try:
            if self.error_handler:
                try:
                    self.error_handler.shutdown()
                except Exception as e:
                    self.logger.debug(f"エラーハンドラーのクリーンアップエラー: {e}")
        except Exception as e:
            print(f"クリーンアップエラー: {e}")
        finally:
            try:
                import logging
                logging.shutdown()
            except:
                pass
            
            try:
                import threading
                import time
                import os
                
                time.sleep(0.1)
                
                active_threads = threading.active_count()
                if active_threads > 1:
                    os._exit(0)
            except:
                pass
    
    def create_parser(self) -> argparse.ArgumentParser:
        """コマンドライン引数パーサーを作成（キーボードUI専用）"""
        parser = argparse.ArgumentParser(
            prog='RecRadiko',
            description='Radikoタイムフリー専用録音システム（キーボードナビゲーション）',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用方法:
  python RecRadiko.py           # キーボードナビゲーションUIで起動
  
キーボードナビゲーション操作:
  ↑↓キー                        # メニュー選択
  Enterキー                     # 決定・実行
  Escキー                       # 戻る・キャンセル
  Ctrl+C                        # 終了
            """
        )
        
        # グローバルオプション（キーボードUI専用）
        parser.add_argument('--version', action='version', version=f'RecRadiko {self.UI_VERSION}')
        parser.add_argument('--config', help='設定ファイルパス', default='config.json')
        parser.add_argument('--verbose', '-v', action='store_true', help='詳細ログを表示')
        
        return parser
    
    def run(self, args: List[str] = None) -> int:
        """CLIメインエントリーポイント（キーボードUIモード専用）"""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        # 詳細ログ設定
        if parsed_args.verbose:
            self._setup_logging(verbose=True)
            logging.getLogger().setLevel(logging.DEBUG)
        
        # 設定ファイルパス更新
        if parsed_args.config != 'config.json':
            self.config_path = Path(parsed_args.config)
            self.config = self._load_config()
        
        # デフォルトでキーボードUIモードを開始
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return self._run_keyboard_ui()
                
        except KeyboardInterrupt:
            print("\\n操作がキャンセルされました")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return 1
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            if self.error_handler:
                handle_error(e)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return 1
        finally:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._cleanup()
    
    def _run_keyboard_ui(self):
        """キーボードUIモードで実行"""
        print("🎛️  RecRadiko キーボードナビゲーション UI")
        print("終了するには Ctrl+C を押してください。")
        print("")
        
        try:
            # RecordingWorkflowのインポート
            from .ui.recording_workflow import RecordingWorkflow
            from .ui.screens.main_menu_screen import MainMenuScreen
            
            # RecordingWorkflowの初期化と実行
            with RecordingWorkflow() as workflow:
                # メインメニュー表示
                print("📻 RecRadiko キーボードナビゲーション UI")
                print("=" * 50)
                
                # メインメニューループ
                while True:
                    main_menu = MainMenuScreen()
                    menu_result = main_menu.run_main_menu_loop()
                    
                    if menu_result == "station_select":
                        # 通常の録音ワークフロー
                        result = workflow.run_sync()
                        if result:
                            print("✅ 録音ワークフローが完了しました")
                            
                    elif menu_result == "search":
                        # 検索ワークフロー
                        result = workflow.run_sync(mode="search")
                        if result:
                            print("✅ 検索からの録音が完了しました")
                            
                    elif menu_result == "settings":
                        # 設定画面
                        from .ui.screens.settings_screen import SettingsScreen
                        settings_screen = SettingsScreen()
                        settings_result = settings_screen.run_settings_workflow()
                        if settings_result:
                            print("✅ 設定が更新されました")
                            
                    elif menu_result == "system_info":
                        # システム情報画面
                        from .ui.screens.system_info_screen import SystemInfoScreen
                        system_info_screen = SystemInfoScreen()
                        system_info_result = system_info_screen.run_system_info_workflow()
                        if system_info_result:
                            print("✅ システム情報を表示しました")
                            
                    elif menu_result is None or menu_result == "exit":
                        # 終了
                        print("\n👋 RecRadikoを終了します。")
                        break
                    
                    # ワークフロー状態をリセット
                    workflow.reset_workflow_state()
                    
            return 0
                        
        except KeyboardInterrupt:
            print("\n\n🛑 キーボードUIを終了します")
            return 0
        except ImportError as e:
            print(f"❌ UIモジュールのインポートに失敗しました: {e}")
            print("キーボードナビゲーションUIは利用できません。")
            return 1
        except Exception as e:
            print(f"❌ キーボードUIでエラーが発生しました: {e}")
            return 1


def main():
    """メインエントリーポイント"""
    cli = RecRadikoCLI()
    cli.run()


if __name__ == "__main__":
    main()