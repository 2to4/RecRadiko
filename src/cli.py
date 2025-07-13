"""
CLIインターフェースモジュール

このモジュールはRecRadikoのコマンドライン操作を提供します。
- 録音コマンド
- スケジュール管理
- 設定管理
- 情報表示
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

# タブ補完機能のためのreadlineライブラリ
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False
import os

from .auth import RadikoAuthenticator, AuthenticationError
from .program_info import ProgramInfoManager, ProgramInfoError
from .streaming import StreamingManager, StreamingError
from .recording import RecordingManager, RecordingJob, RecordingStatus, RecordingError
from .file_manager import FileManager, FileManagerError
from .scheduler import RecordingScheduler, RepeatPattern, ScheduleStatus, SchedulerError
from .error_handler import ErrorHandler, handle_error
from .logging_config import setup_logging, get_logger
from .region_mapper import RegionMapper
from .timefree_recorder import TimeFreeRecorder
from .program_history import ProgramHistoryManager


class RecRadikoCLI:
    """RecRadiko CLIメインクラス"""
    
    VERSION = "1.0.0"
    
    # 対話型モードで利用可能なコマンド一覧（タイムフリー専用）
    INTERACTIVE_COMMANDS = [
        'list-programs', 'record', 'record-id', 'search-programs',
        'list-stations', 'show-region', 'list-prefectures', 
        'status', 'help', 'exit', 'quit'
    ]
    
    # コマンドのオプション一覧（タイムフリー専用）
    COMMAND_OPTIONS = {
        'list-programs': ['--date', '--station'],
        'record': ['--date', '--station', '--title', '--format', '--output'],
        'record-id': ['--program-id', '--format', '--output'],
        'search-programs': ['--keyword', '--date-range', '--station'],
        'list-stations': [],
        'show-region': [],
        'list-prefectures': [],
        'status': [],
        'help': [],
        'exit': [],
        'quit': []
    }
    
    def __init__(self, 
                 config_path: str = "config.json",
                 auth_manager: Optional[RadikoAuthenticator] = None,
                 program_info_manager: Optional[ProgramInfoManager] = None,
                 streaming_manager: Optional[StreamingManager] = None,
                 recording_manager: Optional[RecordingManager] = None,
                 file_manager: Optional[FileManager] = None,
                 scheduler: Optional[RecordingScheduler] = None,
                 error_handler: Optional[ErrorHandler] = None,
                 config_file: Optional[str] = None):
        
        # 設定ファイルパス（テスト用）
        if config_file:
            self.config_path = Path(config_file)
        else:
            self.config_path = Path(config_path)
        
        # 基本ログ設定（設定ロード前に必要）
        self.logger = get_logger(__name__)
        
        # 警告フィルター設定（UserWarning抑制）
        self._setup_warning_filters()
        
        # タブ補完機能の初期化
        self._setup_readline()
        
        self.config = self._load_config()
        
        # 詳細ログ設定
        self._setup_logging()
        
        # コンポーネント初期化（依存性注入対応）
        self.auth_manager = auth_manager
        self.program_info_manager = program_info_manager  
        self.streaming_manager = streaming_manager
        self.recording_manager = recording_manager
        self.file_manager = file_manager
        self.scheduler = scheduler
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
            self.recording_manager,
            self.file_manager,
            self.scheduler,
            self.error_handler
        ])
        
        # 停止フラグ
        self.stop_event = threading.Event()
        
        # シグナルハンドラー設定
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _initialize_default_components(self):
        """デフォルトコンポーネントを初期化"""
        # デフォルトの実装では、実際のコンポーネントを作成
        # テスト時にはモックが注入される
        self._initialize_components()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込み（都道府県名→地域ID自動変換対応）"""
        default_config = {
            "area_id": "JP13",
            "prefecture": "",  # 都道府県名（日本語・英語対応）
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
                # デフォルト値とマージ
                default_config.update(config)
                
                # 都道府県名から地域IDを自動設定
                self._process_prefecture_setting(default_config)
            else:
                # デフォルト設定ファイルを作成
                self._save_config(default_config)
                
            return default_config
            
        except Exception as e:
            self.logger.error(f"設定ファイル読み込みエラー: {e}")
            return default_config
    
    def _process_prefecture_setting(self, config: Dict[str, Any]) -> None:
        """都道府県名から地域IDを自動設定"""
        try:
            prefecture = config.get("prefecture", "").strip()
            
            # 都道府県名が設定されている場合
            if prefecture:
                area_id = RegionMapper.get_area_id(prefecture)
                
                if area_id:
                    # 地域IDをメモリ内でのみ自動設定（ファイルには書き込まない）
                    original_area_id = config.get("area_id", "")
                    config["area_id"] = area_id
                    
                    prefecture_ja = RegionMapper.get_prefecture_name(area_id)
                    self.logger.info(f"都道府県設定から地域ID自動設定: {prefecture} -> {area_id} ({prefecture_ja})")
                    
                    # 既存のarea_idと異なる場合は警告
                    if original_area_id and original_area_id != area_id:
                        self.logger.warning(
                            f"地域ID設定を上書き: {original_area_id} -> {area_id} "
                            f"(都道府県設定: {prefecture})"
                        )
                    
                else:
                    self.logger.warning(f"不明な都道府県名: '{prefecture}' - 利用可能な都道府県名を確認してください")
                    self._show_available_prefectures()
            
            # area_idの妥当性チェック
            elif config.get("area_id"):
                area_id = config["area_id"]
                if not RegionMapper.validate_area_id(area_id):
                    self.logger.warning(f"不正な地域ID: {area_id} - デフォルト地域ID（JP13：東京）を使用")
                    config["area_id"] = RegionMapper.get_default_area_id()
            
            # 都道府県名もarea_idも設定されていない場合はデフォルト地域IDを使用
            else:
                config["area_id"] = RegionMapper.get_default_area_id()
                self.logger.info(f"地域設定がありません - デフォルト地域ID（JP13：東京）を使用")
            
        except Exception as e:
            self.logger.error(f"都道府県設定処理エラー: {e}")
            # エラー時もデフォルト地域IDを設定
            config["area_id"] = RegionMapper.get_default_area_id()
    
    def _update_config_file(self, config: Dict[str, Any]) -> None:
        """設定ファイルを更新"""
        try:
            # 現在の設定ファイルを読み込み
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                
                # area_idのみ更新
                file_config["area_id"] = config["area_id"]
                
                # ファイルに書き戻し
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(file_config, f, ensure_ascii=False, indent=2)
                
                self.logger.debug("設定ファイルを更新しました")
        
        except Exception as e:
            self.logger.warning(f"設定ファイル更新エラー: {e}")
    
    def _show_available_prefectures(self) -> None:
        """利用可能な都道府県名を表示"""
        try:
            prefectures = RegionMapper.list_all_prefectures()
            self.logger.info("利用可能な都道府県名:")
            
            # 地方別にグループ化して表示
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
            
            # verboseモード時のみコンソール出力を有効化
            console_output = verbose
            
            # 統一ログ設定を使用
            setup_logging(
                log_level=log_level,
                log_file=log_file,
                max_log_size=max_log_size,
                console_output=console_output
            )
        except Exception:
            # エラー時はデフォルト設定（コンソール出力は抑制）
            setup_logging(console_output=False)
    
    def _setup_warning_filters(self):
        """警告フィルターの設定"""
        try:
            # UserWarningを抑制（urllib3、readline等からの警告）
            warnings.filterwarnings('ignore', category=UserWarning)
            
            # 特定のライブラリからの警告を抑制
            warnings.filterwarnings('ignore', category=UserWarning, module='urllib3.*')
            warnings.filterwarnings('ignore', category=UserWarning, module='readline.*')
            warnings.filterwarnings('ignore', category=UserWarning, module='requests.*')
            
            # 非推奨警告も抑制
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
            
            # SSL関連の警告を抑制
            warnings.filterwarnings('ignore', message='.*SSL.*')
            warnings.filterwarnings('ignore', message='.*certificate.*')
            
        except Exception as e:
            # 警告フィルター設定エラーは無視（重要度低）
            pass
    
    def _setup_readline(self):
        """readlineの設定とタブ補完の初期化"""
        if not READLINE_AVAILABLE:
            return
        
        try:
            # 補完機能の設定
            readline.set_completer(self._completer)
            readline.parse_and_bind("tab: complete")
            
            # 履歴ファイルの設定
            history_file = Path.home() / ".recradiko_history"
            try:
                readline.read_history_file(str(history_file))
                # 履歴の最大数を設定
                readline.set_history_length(1000)
            except FileNotFoundError:
                pass
            except Exception as e:
                self.logger.debug(f"履歴ファイル読み込みエラー: {e}")
            
            # 終了時の履歴保存を設定
            atexit.register(self._save_history, str(history_file))
            
        except Exception as e:
            self.logger.debug(f"readline設定エラー: {e}")
    
    def _save_history(self, history_file: str):
        """履歴ファイルを保存"""
        if READLINE_AVAILABLE:
            try:
                readline.write_history_file(history_file)
            except Exception as e:
                self.logger.debug(f"履歴ファイル保存エラー: {e}")
    
    def _completer(self, text: str, state: int) -> Optional[str]:
        """タブ補完の実装"""
        if not READLINE_AVAILABLE:
            return None
        
        try:
            line = readline.get_line_buffer()
            line_parts = line.split()
            
            # 現在の入力行を解析
            if not line_parts or (len(line_parts) == 1 and not line.endswith(' ')):
                # コマンドレベルの補完
                matches = [cmd for cmd in self.INTERACTIVE_COMMANDS 
                          if cmd.startswith(text)]
            else:
                # 引数・オプションレベルの補完
                matches = self._get_argument_completions(line, text)
            
            try:
                return matches[state]
            except IndexError:
                return None
                
        except Exception as e:
            self.logger.debug(f"補完エラー: {e}")
            return None
    
    def _get_argument_completions(self, line: str, text: str) -> List[str]:
        """引数・オプションレベルのタブ補完"""
        line_parts = line.split()
        command = line_parts[0] if line_parts else ""
        
        matches = []
        
        # コマンド別の補完
        if command == "record":
            if text.startswith('--'):
                # オプション補完
                options = ['--format', '--bitrate']
                matches = [opt for opt in options if opt.startswith(text)]
            elif len(line_parts) == 1 or (len(line_parts) == 2 and not line.endswith(' ')):
                # 放送局ID補完
                try:
                    stations = self._get_available_stations()
                    matches = [station for station in stations if station.startswith(text)]
                except Exception:
                    matches = []
                    
        elif command == "list-programs":
            if text.startswith('--'):
                options = ['--station', '--date']
                matches = [opt for opt in options if opt.startswith(text)]
                
        elif command == "list-recordings":
            if text.startswith('--'):
                options = ['--date', '--station', '--search']
                matches = [opt for opt in options if opt.startswith(text)]
        
        return matches
    
    def _get_available_stations(self) -> List[str]:
        """利用可能な放送局IDの一覧を取得"""
        try:
            if hasattr(self, 'program_info_manager') and self.program_info_manager:
                stations = self.program_info_manager.get_stations()
                return [station.id for station in stations]
        except Exception:
            pass
        
        # フォールバック: 一般的な放送局ID
        return ['TBS', 'QRR', 'LFR', 'RN1', 'RN2', 'INT', 'FMT', 'FMJ', 'JORF']
    
    def _signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        self.logger.info(f"シグナル受信: {signum}")
        self.stop_event.set()
        self._cleanup()
        sys.exit(0)
    
    def _initialize_components(self):
        """コンポーネントを初期化"""
        try:
            # エラーハンドラー（依存性注入されていない場合のみ）
            if self.error_handler is None:
                self.error_handler = ErrorHandler(
                    log_file="error.log",
                    notification_enabled=self.config.get('notification_enabled', True)
                )
            
            # 認証（依存性注入されていない場合のみ）
            if self.auth_manager is None:
                self.authenticator = RadikoAuthenticator()
                self.auth_manager = self.authenticator
            else:
                self.authenticator = self.auth_manager
            
            # 番組情報管理（依存性注入されていない場合のみ）
            if self.program_info_manager is None:
                self.program_manager = ProgramInfoManager(
                    area_id=self.config.get('area_id', 'JP13'),
                    authenticator=self.authenticator
                )
                self.program_info_manager = self.program_manager
            else:
                self.program_manager = self.program_info_manager
            
            # ストリーミング管理（依存性注入されていない場合のみ）
            # 実際にストリーミングが必要になるまで遅延初期化
            if self.streaming_manager is None:
                # ストリーミング管理は実際に必要時に初期化
                pass
            
            # ファイル管理（依存性注入されていない場合のみ）
            if self.file_manager is None:
                self.file_manager = FileManager(
                    base_dir=self.config.get('output_dir', './recordings'),
                    retention_days=self.config.get('retention_days', 30),
                    min_free_space_gb=self.config.get('min_free_space_gb', 10.0),
                    auto_cleanup_enabled=self.config.get('auto_cleanup_enabled', True)
                )
            
            # 録音管理（依存性注入されていない場合のみ）
            # 実際に録音が必要になるまで遅延初期化
            if self.recording_manager is None:
                # 録音管理は実際に録音時に初期化
                pass
            
            # タイムフリー専用コンポーネント初期化
            if self.timefree_recorder is None:
                self.timefree_recorder = TimeFreeRecorder(self.authenticator)
            
            if self.program_history_manager is None:
                self.program_history_manager = ProgramHistoryManager(self.authenticator)
            
            # スケジューラー（依存性注入されていない場合のみ）
            # 対話型モードでは通常不要なので、遅延初期化とする
            if self.scheduler is None:
                # スケジューラーは実際に必要になるまで初期化しない
                pass
            
            # コールバック設定（実際のインスタンスの場合のみ）
            if self.scheduler and hasattr(self.scheduler, 'set_recording_callback'):
                self.scheduler.set_recording_callback(self._on_scheduled_recording)
            
            self.logger.info("コンポーネント初期化完了")
            
        except Exception as e:
            print(f"コンポーネント初期化エラー: {e}")
            if self.error_handler:
                handle_error(e)
            sys.exit(1)
    
    def _ensure_scheduler_initialized(self):
        """スケジューラーが必要な時に初期化"""
        if self.scheduler is None:
            try:
                from src.scheduler import RecordingScheduler
                self.scheduler = RecordingScheduler(
                    max_concurrent_recordings=self.config.get('max_concurrent_recordings', 4)
                )
                # コールバック設定
                if hasattr(self.scheduler, 'set_recording_callback'):
                    self.scheduler.set_recording_callback(self._on_scheduled_recording)
                self.logger.info("スケジューラーを初期化しました")
            except Exception as e:
                self.logger.error(f"スケジューラー初期化エラー: {e}")
                raise
    
    def _ensure_recording_manager_initialized(self):
        """録音管理が必要な時に初期化"""
        if self.recording_manager is None:
            try:
                # 依存するストリーミング管理を先に初期化
                self._ensure_streaming_manager_initialized()
                
                from src.recording import RecordingManager
                self.recording_manager = RecordingManager(
                    authenticator=self.authenticator,
                    program_manager=self.program_manager,
                    streaming_manager=self.streaming_manager,
                    output_dir=self.config.get('output_dir', './recordings'),
                    max_concurrent_jobs=self.config.get('max_concurrent_recordings', 4)
                )
                self.logger.info("録音管理を初期化しました")
            except Exception as e:
                self.logger.error(f"録音管理初期化エラー: {e}")
                raise
    
    def _ensure_streaming_manager_initialized(self):
        """ストリーミング管理が必要な時に初期化"""
        if self.streaming_manager is None:
            try:
                from src.streaming import StreamingManager
                self.streaming_manager = StreamingManager(
                    authenticator=self.authenticator,
                    max_workers=self.config.get('max_concurrent_recordings', 4)
                )
                self.logger.info("ストリーミング管理を初期化しました")
            except Exception as e:
                self.logger.error(f"ストリーミング管理初期化エラー: {e}")
                raise
    
    def _on_scheduled_recording(self, schedule):
        """スケジュール録音コールバック"""
        try:
            self.logger.info(f"スケジュール録音開始: {schedule.program_title}")
            
            # 録音ジョブを作成
            job_id = self.recording_manager.create_recording_job(
                station_id=schedule.station_id,
                program_title=schedule.program_title,
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                format=schedule.format,
                bitrate=schedule.bitrate
            )
            
            # 録音をスケジュール
            self.recording_manager.schedule_recording(job_id)
            
        except Exception as e:
            self.logger.error(f"スケジュール録音エラー: {e}")
            if self.error_handler:
                handle_error(e, {'schedule_id': schedule.schedule_id})
    
    def _cleanup(self):
        """リソースのクリーンアップ"""
        try:
            if self.recording_manager:
                try:
                    self.recording_manager.shutdown()
                except Exception as e:
                    self.logger.debug(f"録音管理のクリーンアップエラー: {e}")
            
            if self.scheduler:
                try:
                    self.scheduler.shutdown()
                except Exception as e:
                    self.logger.debug(f"スケジューラーのクリーンアップエラー: {e}")
            
            if self.file_manager:
                try:
                    self.file_manager.shutdown()
                except Exception as e:
                    self.logger.debug(f"ファイル管理のクリーンアップエラー: {e}")
            
            if self.error_handler:
                try:
                    self.error_handler.shutdown()
                except Exception as e:
                    self.logger.debug(f"エラーハンドラーのクリーンアップエラー: {e}")
        except Exception as e:
            # 最後の手段としてprintを使用（loggerが利用できない場合）
            print(f"クリーンアップエラー: {e}")
        finally:
            pass
            
            # ログハンドラーをクリーンアップ
            try:
                import logging
                logging.shutdown()
            except:
                pass
            
            # 最後の手段：残りのスレッドを強制終了
            try:
                import threading
                import time
                
                # 少し待って、残りのスレッドが自然終了するのを待つ
                time.sleep(0.1)
                
                # まだアクティブなスレッドがあるかチェック
                active_threads = threading.active_count()
                if active_threads > 1:
                    # プロセス終了を強制（メッセージなし）
                    import os
                    os._exit(0)
            except:
                pass
    
    def create_parser(self) -> argparse.ArgumentParser:
        """コマンドライン引数パーサーを作成（対話型モード専用）"""
        parser = argparse.ArgumentParser(
            prog='RecRadiko',
            description='Radikoの録音・録画を自動化するアプリケーション（対話型モード）',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用方法:
  python RecRadiko.py           # 対話型モードで起動
  python RecRadiko.py --daemon  # デーモンモードで起動
  
対話型モードでは以下のコマンドが利用可能です:
  record <放送局ID> <時間(分)>  # 即座に録音開始
  schedule <放送局ID> "<番組名>" <開始時刻> <終了時刻>  # 録音予約
  list-stations                # 放送局一覧表示
  list-programs <放送局ID>     # 番組表表示
  list-schedules               # 録音予約一覧表示
  status                       # システム状態表示
  help                         # ヘルプ表示
  exit                         # 終了
            """
        )
        
        # グローバルオプション（対話型モード専用に簡素化）
        parser.add_argument('--version', action='version', version=f'RecRadiko {self.VERSION}')
        parser.add_argument('--config', help='設定ファイルパス', default='config.json')
        parser.add_argument('--verbose', '-v', action='store_true', help='詳細ログを表示')
        parser.add_argument('--daemon', action='store_true', help='デーモンモードで実行')
        
        return parser
    
    def run(self, args: List[str] = None) -> int:
        """CLIメインエントリーポイント（対話型モード専用）"""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        # 詳細ログ設定
        if parsed_args.verbose:
            # verboseモード時はコンソール出力を有効化し、DEBUGレベルに設定
            self._setup_logging(verbose=True)
            logging.getLogger().setLevel(logging.DEBUG)
        
        # 設定ファイルパス更新
        if parsed_args.config != 'config.json':
            self.config_path = Path(parsed_args.config)
            self.config = self._load_config()
        
        # デーモンモード
        if parsed_args.daemon:
            self._run_daemon()
            return 0
        
        # デフォルトで対話型モードを開始
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return self._run_interactive()
                
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
    
    def _run_daemon(self):
        """デーモンモードで実行"""
        print("デーモンモードで実行中...")
        print("Ctrl+C で終了")
        
        # コンポーネント初期化
        self._initialize_components()
        
        try:
            # メインループ
            while not self.stop_event.is_set():
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\\n終了中...")
        finally:
            self._cleanup()
            print("アプリケーションを終了しました")
    
    def _cmd_record(self, args):
        """録音コマンド"""
        print(f"録音開始: {args.station_id} ({args.duration}分)")
        
        try:
            # 録音管理が必要な時に初期化
            self._ensure_recording_manager_initialized()
            
            # 現在時刻から録音時間を計算
            now = datetime.now()
            end_time = now + timedelta(minutes=args.duration)
            
            # フォーマットとビットレートの設定
            format_str = getattr(args, 'format', None) or self.config.get('default_format', 'aac')
            bitrate = getattr(args, 'bitrate', None) or self.config.get('default_bitrate', 128)
            
            # 出力パスの設定
            if not getattr(args, 'output', None):
                output_path = f"./recordings/{args.station_id}_{now.strftime('%Y%m%d_%H%M%S')}.{format_str}"
            else:
                output_path = args.output
            
            # 録音ジョブを作成
            job_id = self.recording_manager.create_recording_job(
                station_id=args.station_id,
                program_title=f"{args.station_id}番組",
                start_time=now,
                end_time=end_time,
                output_path=output_path,
                format=format_str,
                bitrate=bitrate
            )
            
            # ジョブオブジェクトを取得
            job = self.recording_manager.get_job_status(job_id)
            if job:
                # 通常使用時はジョブオブジェクトの詳細は表示しない
                print(f"録音を開始しました")
                if hasattr(job, 'duration_seconds') and job.duration_seconds:
                    try:
                        duration_seconds = int(job.duration_seconds)
                        duration_minutes = duration_seconds // 60
                        print(f"録音時間: {duration_seconds}秒 ({duration_minutes}分)")
                    except (TypeError, ValueError, AttributeError):
                        # テスト時やMockオブジェクトの場合は時間表示をスキップ
                        pass
            else:
                print(f"録音ジョブを作成しました: {job_id}")
            
            # 録音開始
            self.recording_manager.schedule_recording(job_id)
            
            # テスト時は進捗監視をスキップ
            if self._all_components_injected:
                print(f"録音ジョブを開始しました")
            else:
                # 進捗監視（実際の実行時のみ）
                # プログレスバーの初期化
                try:
                    from tqdm import tqdm
                    pbar = tqdm(total=100, desc="録音中", unit="%", 
                              bar_format="{l_bar}{bar}| {n:.1f}% [{elapsed}<{remaining}]")
                    
                    last_progress = 0
                    while True:
                        current_job = self.recording_manager.get_job_status(job_id)
                        if not current_job:
                            break
                        
                        progress = self.recording_manager.get_job_progress(job_id)
                        if progress and hasattr(progress, 'progress_percent'):
                            # プログレスバーの更新
                            try:
                                progress_diff = float(progress.progress_percent) - last_progress
                                if progress_diff > 0:
                                    pbar.update(progress_diff)
                                    last_progress = float(progress.progress_percent)
                                
                                # 詳細情報の更新
                                eta_seconds = getattr(progress, 'estimated_remaining_seconds', 0)
                                bytes_written = getattr(progress, 'bytes_written', 0)
                                
                                if eta_seconds and eta_seconds > 0:
                                    eta_str = f"ETA: {eta_seconds}s"
                                else:
                                    eta_str = "計算中..."
                                
                                kb_written = bytes_written // 1024 if isinstance(bytes_written, int) else 0
                                pbar.set_postfix_str(f"書込: {kb_written}KB, {eta_str}")
                            except (TypeError, AttributeError, ValueError):
                                # テスト時やMockオブジェクトの場合は無視
                                pass
                        
                        if hasattr(current_job, 'status') and current_job.status in [RecordingStatus.COMPLETED, RecordingStatus.FAILED, RecordingStatus.CANCELLED]:
                            # 完了時は100%に設定
                            if hasattr(current_job, 'status') and current_job.status == RecordingStatus.COMPLETED:
                                try:
                                    remaining_progress = 100 - last_progress
                                    if remaining_progress > 0:
                                        pbar.update(remaining_progress)
                                except (TypeError, ValueError):
                                    pass
                            break
                        
                        time.sleep(2)
                    
                    pbar.close()
                    
                except ImportError:
                    # tqdmが利用できない場合は従来の表示方式にフォールバック
                    while True:
                        current_job = self.recording_manager.get_job_status(job_id)
                        if not current_job:
                            break
                        
                        progress = self.recording_manager.get_job_progress(job_id)
                        if progress and hasattr(progress, 'progress_percent'):
                            try:
                                progress_value = float(progress.progress_percent)
                                print(f"\\r進捗: {progress_value:.1f}%", end="", flush=True)
                            except (TypeError, ValueError, AttributeError):
                                # テスト時やMockオブジェクトの場合は無視
                                pass
                        
                        if hasattr(current_job, 'status') and current_job.status in [RecordingStatus.COMPLETED, RecordingStatus.FAILED, RecordingStatus.CANCELLED]:
                            break
                        
                        time.sleep(2)
                
                if hasattr(current_job, 'status'):
                    status_value = getattr(current_job.status, 'value', str(current_job.status))
                    print(f"\\n録音完了: {status_value}")
                    if current_job.status == RecordingStatus.COMPLETED and hasattr(current_job, 'output_path'):
                        print(f"保存先: {current_job.output_path}")
                else:
                    print(f"\\n録音完了")
            
        except Exception as e:
            print(f"録音エラー: {e}")
            return 1
        
        return 0
    
    def _cmd_schedule(self, args):
        """録音予約コマンド"""
        try:
            # スケジューラーが必要な時に初期化
            self._ensure_scheduler_initialized()
            
            # 時刻解析
            start_time = datetime.fromisoformat(args.start_time)
            end_time = datetime.fromisoformat(args.end_time)
            
            # 繰り返しパターン
            repeat_pattern = RepeatPattern.NONE
            if args.repeat:
                repeat_pattern = RepeatPattern(args.repeat)
            
            # 繰り返し終了日
            repeat_end_date = None
            if args.repeat_end:
                repeat_end_date = datetime.fromisoformat(args.repeat_end + "T23:59:59")
            
            # スケジュール追加
            schedule_id = self.scheduler.add_schedule(
                args.station_id,  # 位置引数として渡す
                program_title=args.program_title,
                start_time=start_time,
                end_time=end_time,
                repeat_pattern=repeat_pattern,
                repeat_end_date=repeat_end_date,
                format=args.format,
                bitrate=args.bitrate,
                notes=args.notes or ""
            )
            
            # add_scheduleが失敗した場合の処理
            if not schedule_id:
                print(f"予約エラー: 録音予約の追加に失敗しました")
                return 1
            
            print(f"録音予約を追加しました: {schedule_id}")
            print(f"番組: {args.program_title}")
            print(f"放送局: {args.station_id}")
            print(f"時間: {start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%H:%M')}")
            
            if repeat_pattern != RepeatPattern.NONE:
                print(f"繰り返し: {repeat_pattern.value}")
                if repeat_end_date:
                    print(f"終了日: {repeat_end_date.strftime('%Y-%m-%d')}")
            
        except ValueError as e:
            print(f"日時形式エラー: {e}")
            print("正しい形式: YYYY-MM-DDTHH:MM (例: 2024-01-01T20:00)")
            return 1
        except Exception as e:
            print(f"予約エラー: {e}")
            return 1
        
        return 0
    
    def _cmd_list_stations(self, args):
        """放送局一覧コマンド"""
        try:
            stations = self.program_info_manager.fetch_station_list()
            
            print(f"放送局一覧 ({len(stations)} 局)")
            print("-" * 50)
            
            for station in stations:
                print(f"{station.id:10} {station.name}")
            
        except Exception as e:
            print(f"放送局一覧取得エラー: {e}")
            return 1
        
        return 0
    
    def _cmd_list_programs(self, args):
        """番組表コマンド"""
        try:
            # 日付解析
            if args.date:
                date = datetime.strptime(args.date, '%Y-%m-%d')
            else:
                date = datetime.now()
            
            if not args.station_id:
                print("エラー: 放送局IDが指定されていません")
                print("使用法: list-programs --station <放送局ID>")
                return 1
            
            programs = self.program_info_manager.fetch_program_guide(date, args.station_id)
            
            print(f"{args.station_id} 番組表 ({date.strftime('%Y-%m-%d')})")
            print("-" * 70)
            
            for program in programs:
                start_str = program.start_time.strftime('%H:%M')
                end_str = program.end_time.strftime('%H:%M')
                print(f"{start_str}-{end_str} {program.title}")
                
                if program.performers:
                    print(f"           出演: {', '.join(program.performers)}")
            
        except ValueError as e:
            print(f"日付形式エラー: {e}")
            print("正しい形式: YYYY-MM-DD (例: 2024-01-01)")
            return 1
        except Exception as e:
            print(f"番組表取得エラー: {e}")
            return 1
        
        return 0
    
    def _cmd_list_schedules(self, args):
        """録音予約一覧コマンド"""
        try:
            # スケジューラーが必要な時に初期化
            self._ensure_scheduler_initialized()
            
            # フィルター設定
            status_filter = None
            if getattr(args, 'status', None):
                status_filter = ScheduleStatus(args.status)
            
            schedules = self.scheduler.list_schedules(
                status=status_filter,
                station_id=getattr(args, 'station', None)
            )
            
            print(f"録音予約一覧 ({len(schedules)} 件)")
            print("-" * 80)
            
            for schedule in schedules:
                start_str = schedule.start_time.strftime('%Y-%m-%d %H:%M')
                end_str = schedule.end_time.strftime('%H:%M')
                
                print(f"ID: {schedule.schedule_id}")
                print(f"番組: {schedule.program_title} ({schedule.station_id})")
                print(f"時間: {start_str} - {end_str}")
                print(f"ステータス: {schedule.status.value}")
                
                if schedule.repeat_pattern != RepeatPattern.NONE:
                    print(f"繰り返し: {schedule.repeat_pattern.value}")
                
                if schedule.notes:
                    print(f"メモ: {schedule.notes}")
                
                print()
            
        except Exception as e:
            print(f"予約一覧取得エラー: {e}")
            return 1
        
        return 0
    
    def _cmd_remove_schedule(self, args):
        """録音予約削除コマンド"""
        try:
            if self.scheduler.remove_schedule(args.schedule_id):
                print(f"スケジュールを削除しました: {args.schedule_id}")
                return 0
            else:
                print(f"スケジュールが見つかりません: {args.schedule_id}")
                return 1
            
        except Exception as e:
            print(f"予約削除エラー: {e}")
            raise
    
    def _cmd_list_recordings(self, args):
        """録音ファイル一覧コマンド"""
        try:
            # フィルター設定
            start_date = None
            if args.date:
                start_date = datetime.strptime(args.date, '%Y-%m-%d')
            
            if args.search:
                files = self.file_manager.search_files(args.search)
            else:
                files = self.file_manager.list_files(
                    station_id=args.station,
                    start_date=start_date
                )
            
            print(f"録音ファイル一覧 ({len(files)} 件)")
            print("-" * 80)
            
            for file_metadata in files:
                start_str = file_metadata.start_time.strftime('%Y-%m-%d %H:%M')
                duration_str = f"{file_metadata.duration_seconds // 60}分"
                size_mb = file_metadata.file_size / (1024 * 1024)
                
                print(f"番組: {file_metadata.program_title}")
                print(f"放送局: {file_metadata.station_id}")
                print(f"録音日時: {start_str} ({duration_str})")
                print(f"ファイル: {file_metadata.file_path}")
                print(f"サイズ: {size_mb:.1f} MB ({file_metadata.format})")
                print()
            
        except ValueError as e:
            print(f"日付形式エラー: {e}")
            print("正しい形式: YYYY-MM-DD (例: 2024-01-01)")
            return 1
        except Exception as e:
            print(f"ファイル一覧取得エラー: {e}")
            return 1
        
        return 0
    
    def _cmd_show_config(self, args):
        """設定表示コマンド"""
        print("現在の設定:")
        print("-" * 40)
        
        try:
            for key, value in self.config.items():
                if 'password' in key.lower():
                    value = '*' * len(str(value)) if value else ''
                print(f"{key:25} = {value}")
        except Exception as e:
            print(f"設定表示エラー: {e}")
            return 1
        
        return 0
    
    def _cmd_show_region(self, args):
        """地域情報表示コマンド"""
        try:
            prefecture_info = self.get_current_prefecture_info()
            
            print("現在の地域設定:")
            print("-" * 40)
            print(f"地域ID:         {prefecture_info['area_id']}")
            print(f"都道府県名:     {prefecture_info['prefecture_ja']}")
            print(f"英語名:         {prefecture_info['prefecture_en']}")
            print(f"地方:           {prefecture_info['region_name']}")
            print(f"主要放送局:     {', '.join(prefecture_info['major_stations'])}")
            
            # 設定方法の説明
            print("\n地域設定の変更方法:")
            print("-" * 40)
            print("config.jsonの 'prefecture' フィールドに都道府県名を設定してください")
            print("例: \"prefecture\": \"大阪\" または \"prefecture\": \"Osaka\"")
            
        except Exception as e:
            print(f"地域情報表示エラー: {e}")
            return 1
        
        return 0
    
    def _cmd_list_prefectures(self, args):
        """全都道府県一覧表示コマンド"""
        try:
            print("利用可能な都道府県一覧:")
            print("=" * 50)
            
            # 地方別にグループ化して表示
            regions = {}
            for area_id, info in RegionMapper.REGION_INFO.items():
                region = info.region_name
                if region not in regions:
                    regions[region] = []
                regions[region].append({
                    'prefecture_ja': info.prefecture_ja,
                    'prefecture_en': info.prefecture_en,
                    'area_id': area_id,
                    'stations': info.major_stations
                })
            
            for region, prefs in regions.items():
                print(f"\n【{region}】")
                print("-" * 20)
                for pref in prefs:
                    stations_str = f" ({', '.join(pref['stations'][:3])}{'...' if len(pref['stations']) > 3 else ''})"
                    print(f"  {pref['prefecture_ja']:8} ({pref['area_id']}) / {pref['prefecture_en']:12}{stations_str}")
            
            print("\n設定例:")
            print("  \"prefecture\": \"大阪\"     # 日本語名")
            print("  \"prefecture\": \"Osaka\"    # 英語名")
            print("  \"prefecture\": \"osaka\"    # 小文字でも可")
            
        except Exception as e:
            print(f"都道府県一覧表示エラー: {e}")
            return 1
        
        return 0
    
    def _cmd_config(self, args):
        """設定変更コマンド"""
        changes = {}
        
        if args.area_id:
            changes['area_id'] = args.area_id
        if args.premium_user:
            changes['premium_username'] = args.premium_user
        if args.premium_pass:
            changes['premium_password'] = args.premium_pass
        if args.output_dir:
            changes['output_dir'] = args.output_dir
        if args.format:
            changes['default_format'] = args.format
        if args.bitrate:
            changes['default_bitrate'] = args.bitrate
        if args.retention_days:
            changes['retention_days'] = args.retention_days
        if args.notification_enabled is not None:
            changes['notification_enabled'] = args.notification_enabled
        
        try:
            if not changes:
                print("変更する設定がありません")
                return 0
            
            # 設定を更新
            self.config.update(changes)
            self._save_config(self.config)
            
            print("設定を更新しました:")
            for key, value in changes.items():
                if 'password' in key.lower():
                    value = '*' * len(str(value))
                print(f"  {key} = {value}")
        except Exception as e:
            print(f"設定更新エラー: {e}")
            return 1
        
        return 0
    
    def _cmd_status(self, args):
        """システム状態コマンド"""
        try:
            print("システム状態:")
            print("-" * 40)
            
            # 認証状態
            auth_status = "OK" if self.authenticator.is_authenticated() else "未認証"
            print(f"認証状態: {auth_status}")
            
            # アクティブな録音（遅延初期化対応）
            try:
                if self.recording_manager:
                    active_jobs = self.recording_manager.get_active_jobs()
                    job_count = len(active_jobs) if active_jobs else 0
                else:
                    job_count = 0
            except Exception:
                job_count = 0
            print(f"録音状況: {job_count} 件のジョブ")
            
            # スケジュール統計（遅延初期化対応）
            try:
                if self.scheduler:
                    schedule_stats = self.scheduler.get_statistics()
                    active_count = schedule_stats.get('active_schedules', 0) if schedule_stats else 0
                else:
                    active_count = 0
            except Exception:
                active_count = 0
            print(f"アクティブなスケジュール: {active_count} 件")
            
            # ストレージ情報
            storage_info = self.file_manager.get_storage_info()
            print(f"ストレージ使用状況:")
            print(f"  録音ファイル: {storage_info.file_count} 件")
            print(f"  使用容量: {storage_info.recording_files_size / (1024**3):.2f} GB")
            print(f"  空き容量: {storage_info.free_space_gb:.2f} GB")
            
            # スケジュール予定
            try:
                next_schedules = self.scheduler.get_next_schedules()
                schedule_count = len(next_schedules) if hasattr(next_schedules, '__len__') else 0
                print(f"次のスケジュール: {schedule_count} 件")
            except (TypeError, AttributeError):
                print(f"次のスケジュール: 0 件")
            
        except Exception as e:
            print(f"状態取得エラー: {e}")
            return 1
        
        return 0
    
    def _cmd_stats(self, args):
        """統計情報コマンド"""
        try:
            print("統計情報:")
            print("-" * 40)
            
            # ファイル統計
            file_stats = self.file_manager.get_statistics()
            if file_stats:
                print(f"総録音ファイル: {file_stats['total_files']} 件")
                print(f"総録音時間: {file_stats['total_duration_hours']:.1f} 時間")
                print(f"総ファイルサイズ: {file_stats['total_size_gb']:.2f} GB")
                print(f"平均ファイルサイズ: {file_stats['average_file_size_mb']:.1f} MB")
                
                # 放送局別統計
                if file_stats['stations']:
                    print("\\n放送局別統計:")
                    for station, stats in file_stats['stations'].items():
                        print(f"  {station}: {stats['count']} 件, {stats['duration'] / 3600:.1f} 時間")
            
            # スケジュール統計（遅延初期化対応）
            try:
                if self.scheduler:
                    schedule_stats = self.scheduler.get_statistics()
                    print(f"\\n総スケジュール: {schedule_stats['total_schedules']} 件")
                    print(f"アクティブ: {schedule_stats['active_schedules']} 件")
                    print(f"完了: {schedule_stats['completed_schedules']} 件")
                else:
                    print(f"\\n総スケジュール: 0 件")
                    print(f"アクティブ: 0 件")
                    print(f"完了: 0 件")
            except Exception:
                print(f"\\n総スケジュール: 0 件")
                print(f"アクティブ: 0 件")
                print(f"完了: 0 件")
            
            # エラー統計
            error_stats = self.error_handler.get_error_statistics()
            if error_stats:
                print(f"\\n総エラー: {error_stats.get('total_errors', 0)} 件")
                print(f"未解決エラー: {error_stats.get('unresolved_errors', 0)} 件")
                print(f"最近のエラー(24h): {error_stats.get('recent_errors_24h', 0)} 件")
            
        except Exception as e:
            print(f"統計取得エラー: {e}")
            return 1
        
        return 0
    
    def _run_interactive(self):
        """対話型モードで実行"""
        print("RecRadiko 対話型モード")
        print("利用可能なコマンド: record, schedule, list-stations, list-programs, list-schedules, status, stats, help, exit")
        print("例: record TBS 60")
        if READLINE_AVAILABLE:
            print("💡 タブキーでコマンド補完、↑↓キーで履歴操作が利用できます")
        print("終了するには 'exit' または Ctrl+C を入力してください")
        print("-" * 60)
        
        # コンポーネント初期化
        if not self._all_components_injected:
            self._initialize_components()
        
        while True:
            try:
                # プロンプト表示
                user_input = input("RecRadiko> ").strip()
                
                if not user_input:
                    continue
                
                # 終了コマンド
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("RecRadikoを終了します")
                    # 終了時の警告を抑制
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        return 0
                
                # ヘルプコマンド
                if user_input.lower() in ['help', 'h', '?']:
                    self._print_interactive_help()
                    continue
                
                # コマンドを解析
                command_args = user_input.split()
                
                # 仮のargparse名前空間を作成
                try:
                    result = self._execute_interactive_command(command_args)
                    if result != 0:
                        print(f"コマンドの実行でエラーが発生しました (終了コード: {result})")
                    print()  # 空行を追加
                except Exception as e:
                    print(f"エラー: {e}")
                    print()
                    
            except KeyboardInterrupt:
                print("\nRecRadikoを終了します")
                # 終了時の警告を抑制
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    return 0
            except EOFError:
                print("\nRecRadikoを終了します")
                # 終了時の警告を抑制
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    return 0
        
        # 通常ここには到達しないが、念のため
        return 0
    
    def _print_interactive_help(self):
        """対話型モードのヘルプを表示（タイムフリー専用）"""
        print("""
RecRadiko タイムフリー専用版 - 利用可能なコマンド:

  list-programs <日付> [--station <ID>]                - 過去番組表を表示
  record <日付> <放送局ID> "<番組名>"                    - 番組名指定で録音
  record-id <番組ID>                                   - 番組ID指定で録音
  search-programs <キーワード> [--station <ID>]        - 番組検索
  list-stations                                        - 放送局一覧を表示
  show-region                                          - 現在の地域設定を表示
  list-prefectures                                     - 全都道府県一覧を表示
  status                                               - システム状態を表示
  help                                                 - このヘルプを表示
  exit                                                 - プログラムを終了

例:
  list-programs 2025-07-10 --station TBS              - 7月10日のTBS番組表
  record 2025-07-10 TBS "森本毅郎・スタンバイ!"       - 番組名で録音
  record-id TBS_20250710_060000                        - 番組IDで録音
  search-programs "森本毅郎" --station TBS             - TBSで森本毅郎検索

注意: 本バージョンはタイムフリー専用です（過去7日間の番組のみ対応）
        """)
    
    def _execute_interactive_command(self, command_args):
        """対話型コマンドを実行"""
        if not command_args:
            return 0
        
        command = command_args[0]
        
        # 簡易的なargparse名前空間を作成
        class SimpleArgs:
            pass
        
        args = SimpleArgs()
        
        try:
            # 終了コマンド
            if command in ['exit', 'quit', 'q']:
                print("RecRadikoを終了します")
                return 0
            
            # ヘルプコマンド
            if command in ['help', 'h', '?']:
                self._print_interactive_help()
                return 0
            
            if command == 'record':
                if len(command_args) < 4:
                    print("使用法: record <日付> <放送局ID> \"<番組名>\" [--format <形式>] [--output <ファイル名>]")
                    print("例: record 2025-07-10 TBS \"森本毅郎・スタンバイ!\"")
                    return 1
                
                args.date = command_args[1]
                args.station_id = command_args[2]
                args.title = command_args[3]
                args.format = 'mp3'  # デフォルト
                args.output = None
                
                # オプション解析
                i = 4
                while i < len(command_args):
                    if command_args[i] == '--format' and i + 1 < len(command_args):
                        args.format = command_args[i + 1]
                        i += 2
                    elif command_args[i] == '--output' and i + 1 < len(command_args):
                        args.output = command_args[i + 1]
                        i += 2
                    else:
                        i += 1
                
                return self._cmd_timefree_record(args)
            
            elif command == 'record-id':
                if len(command_args) < 2:
                    print("使用法: record-id <番組ID> [--format <形式>] [--output <ファイル名>]")
                    print("例: record-id TBS_20250710_060000")
                    return 1
                
                args.program_id = command_args[1]
                args.format = 'mp3'  # デフォルト
                args.output = None
                
                # オプション解析
                i = 2
                while i < len(command_args):
                    if command_args[i] == '--format' and i + 1 < len(command_args):
                        args.format = command_args[i + 1]
                        i += 2
                    elif command_args[i] == '--output' and i + 1 < len(command_args):
                        args.output = command_args[i + 1]
                        i += 2
                    else:
                        i += 1
                
                return self._cmd_timefree_record_by_id(args)
            
            elif command == 'search-programs':
                if len(command_args) < 2:
                    print("使用法: search-programs <キーワード> [--date-range <開始日> <終了日>] [--station <放送局ID>]")
                    print("例: search-programs \"森本毅郎\" --station TBS")
                    return 1
                
                args.keyword = command_args[1]
                args.date_range = None
                args.station_ids = None
                
                # オプション解析
                i = 2
                while i < len(command_args):
                    if command_args[i] == '--date-range' and i + 2 < len(command_args):
                        args.date_range = (command_args[i + 1], command_args[i + 2])
                        i += 3
                    elif command_args[i] == '--station' and i + 1 < len(command_args):
                        args.station_ids = [command_args[i + 1]]
                        i += 2
                    else:
                        i += 1
                
                return self._cmd_search_programs(args)
            
            elif command == 'list-stations':
                return self._cmd_list_stations(args)
            
            elif command == 'list-programs':
                if len(command_args) < 2:
                    print("使用法: list-programs <日付> [--station <放送局ID>]")
                    print("例: list-programs 2025-07-10 --station TBS")
                    return 1
                
                args.date = command_args[1]
                args.station_id = None
                
                # オプション解析
                i = 2
                while i < len(command_args):
                    if command_args[i] == '--station' and i + 1 < len(command_args):
                        args.station_id = command_args[i + 1]
                        i += 2
                    else:
                        i += 1
                
                return self._cmd_timefree_list_programs(args)
            
            
            elif command == 'show-region':
                return self._cmd_show_region(args)
            
            elif command == 'list-prefectures':
                return self._cmd_list_prefectures(args)
            
            elif command == 'status':
                return self._cmd_status(args)
            
            else:
                print(f"不明なコマンド: {command}")
                print("'help' でヘルプを表示")
                return 1
                
        except ValueError as e:
            print(f"パラメータエラー: {e}")
            return 1
        except Exception as e:
            print(f"コマンド実行エラー: {e}")
            return 1


def main():
    """メインエントリーポイント"""
    cli = RecRadikoCLI()
    cli.run()


if __name__ == "__main__":
    main()