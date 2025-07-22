"""
実環境テスト用共通ユーティリティ

モック使用を最小化し、実際のファイル・設定・システムリソースを使用する
統合テスト環境を提供します。
"""

import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.auth import RadikoAuthenticator
from src.timefree_recorder import TimeFreeRecorder
from src.cli import RecRadikoCLI
from src.program_info import ProgramInfo, Station, Program


class TemporaryTestEnvironment:
    """統合テスト用実環境管理"""
    
    def __init__(self):
        self.temp_dir = None
        self.config_dir = None
        self.recordings_dir = None
        self.logs_dir = None
        self.auth_file = None
        self.config_file = None
        self.encryption_key_file = None
        
    def __enter__(self):
        """一時環境セットアップ"""
        # 一時ディレクトリ構築
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / ".recradiko"
        self.recordings_dir = self.config_dir / "recordings"
        self.logs_dir = self.config_dir / "logs"
        
        # ディレクトリ作成
        self.config_dir.mkdir(parents=True)
        self.recordings_dir.mkdir(parents=True)
        self.logs_dir.mkdir(parents=True)
        
        # デフォルト設定ファイル作成
        self.config_file = self.config_dir / "config.json"
        default_config = {
            "version": "2.0",
            "prefecture": "東京",
            "area_id": "JP13",
            "audio": {
                "format": "mp3",
                "bitrate": 256,
                "sample_rate": 48000
            },
            "recording": {
                "save_path": str(self.recordings_dir),
                "id3_tags_enabled": True,
                "concurrent_downloads": 8
            }
        }
        self.config_file.write_text(json.dumps(default_config, indent=2))
        
        # 認証ファイル作成
        self.auth_file = self.config_dir / "auth_token"
        auth_data = {
            "auth_token": "test_auth_token_123",
            "area_id": "JP13",
            "expires_at": time.time() + 3600,
            "premium_user": False,
            "timefree_session": "test_timefree_token_123",
            "timefree_expires_at": time.time() + 1800
        }
        self.auth_file.write_text(json.dumps(auth_data))
        
        # 暗号化キーファイル作成
        self.encryption_key_file = self.config_dir / "encryption.key"
        # 実際の暗号化キーを生成（テスト用）
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        self.encryption_key_file.write_bytes(key)
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """一時環境クリーンアップ"""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_sample_recording(self, name: str, size: int = 1024, 
                               station_id: str = "TBS", 
                               recorded_at: Optional[datetime] = None) -> Path:
        """サンプル録音ファイル作成"""
        file_path = self.recordings_dir / f"{name}.mp3"
        
        # 実際のMP3ヘッダー風データ（テスト用）
        mp3_header = b'\xff\xfb\x90\x00'  # MP3フレームヘッダー
        content = mp3_header + b"fake mp3 audio data" * (size // 20)
        file_path.write_bytes(content)
        
        # ファイルのタイムスタンプ設定
        if recorded_at:
            timestamp = recorded_at.timestamp()
            os.utime(file_path, (timestamp, timestamp))
        
        return file_path
    
    def create_sample_playlist(self, station_id: str, segments: int = 5,
                              segment_duration: int = 5) -> Path:
        """サンプルプレイリストファイル作成"""
        playlist_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
        playlist_content += f"#EXT-X-TARGETDURATION:{segment_duration}\n"
        
        for i in range(segments):
            playlist_content += f"#EXTINF:{segment_duration}.0,\n"
            playlist_content += f"https://radiko.jp/v2/api/ts/chunklist/{station_id}_segment_{i}.ts\n"
        
        playlist_content += "#EXT-X-ENDLIST\n"
        
        playlist_file = self.config_dir / f"{station_id}_playlist.m3u8"
        playlist_file.write_text(playlist_content)
        return playlist_file
    
    def create_sample_program_info(self, station_id: str = "TBS", 
                                  program_title: str = "テスト番組",
                                  start_time: Optional[datetime] = None,
                                  duration: int = 3600) -> ProgramInfo:
        """サンプル番組情報作成"""
        if start_time is None:
            start_time = datetime.now()
        
        end_time = start_time + timedelta(seconds=duration)
        
        return ProgramInfo(
            station_id=station_id,
            program_title=program_title,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            description=f"{program_title}の説明",
            performer="テスト出演者",
            genre="テスト"
        )
    
    def create_sample_station(self, station_id: str = "TBS",
                             name: str = "TBSラジオ",
                             area_id: str = "JP13") -> Station:
        """サンプル放送局作成"""
        return Station(
            station_id=station_id,
            name=name,
            area_id=area_id,
            logo_url=f"https://radiko.jp/v3/station/logo/{station_id}.png",
            banner_url=f"https://radiko.jp/v3/station/banner/{station_id}.png"
        )
    
    def create_sample_log_file(self, name: str = "recradiko.log",
                              entries: int = 10) -> Path:
        """サンプルログファイル作成"""
        log_file = self.logs_dir / name
        
        log_content = ""
        for i in range(entries):
            timestamp = datetime.now() - timedelta(hours=i)
            level = ["INFO", "WARNING", "ERROR", "DEBUG"][i % 4]
            message = f"Test log entry {i}"
            log_content += f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {level} - {message}\n"
        
        log_file.write_text(log_content)
        return log_file
    
    def get_config_data(self) -> Dict[str, Any]:
        """設定データ取得"""
        return json.loads(self.config_file.read_text())
    
    def update_config_data(self, updates: Dict[str, Any]) -> None:
        """設定データ更新"""
        config = self.get_config_data()
        config.update(updates)
        self.config_file.write_text(json.dumps(config, indent=2))
    
    def get_auth_data(self) -> Dict[str, Any]:
        """認証データ取得"""
        return json.loads(self.auth_file.read_text())
    
    def update_auth_data(self, updates: Dict[str, Any]) -> None:
        """認証データ更新"""
        auth_data = self.get_auth_data()
        auth_data.update(updates)
        self.auth_file.write_text(json.dumps(auth_data))


class RealEnvironmentTestBase:
    """
    実環境テストベースクラス（TDD手法対応）
    
    TEST_REDESIGN_PLANに基づく実環境重視テスト基盤。
    モック使用最小限（10%以下）、実ファイル・実データベース・実暗号化処理を使用。
    """
    
    def setUp(self):
        """実環境テストセットアップ"""
        # 実ファイルシステム使用
        # 実SQLiteデータベース使用
        # 実暗号化処理使用
        # 一時ディレクトリ管理
        pass
    
    def tearDown(self):
        """実環境テストクリーンアップ"""
        # リソース解放
        # 一時ファイル削除
        # データベース閉鎖
        pass
    
    def setup_real_authenticator(self, temp_env: TemporaryTestEnvironment) -> RadikoAuthenticator:
        """実環境認証器セットアップ"""
        return RadikoAuthenticator(config_path=str(temp_env.config_file))
    
    def setup_real_recorder(self, temp_env: TemporaryTestEnvironment) -> TimeFreeRecorder:
        """実環境録音器セットアップ"""
        authenticator = self.setup_real_authenticator(temp_env)
        return TimeFreeRecorder(authenticator)
    
    def setup_real_cli(self, temp_env: TemporaryTestEnvironment) -> RecRadikoCLI:
        """実環境CLIセットアップ"""
        return RecRadikoCLI(config_file=str(temp_env.config_file))
    
    def verify_file_operations(self, temp_env: TemporaryTestEnvironment) -> bool:
        """ファイル操作検証"""
        # 設定ファイル検証
        assert temp_env.config_file.exists()
        config_data = temp_env.get_config_data()
        assert config_data["version"] == "2.0"
        assert config_data["prefecture"] == "東京"
        
        # 認証ファイル検証
        assert temp_env.auth_file.exists()
        auth_data = temp_env.get_auth_data()
        assert "auth_token" in auth_data
        assert "area_id" in auth_data
        
        # ディレクトリ構造検証
        assert temp_env.recordings_dir.exists()
        assert temp_env.logs_dir.exists()
        
        return True
    
    def verify_recording_operations(self, temp_env: TemporaryTestEnvironment) -> bool:
        """録音操作検証"""
        # サンプル録音ファイル作成
        recording_file = temp_env.create_sample_recording("test_recording")
        assert recording_file.exists()
        assert recording_file.stat().st_size > 0
        
        # プレイリストファイル作成
        playlist_file = temp_env.create_sample_playlist("TBS", 5)
        assert playlist_file.exists()
        assert "#EXTM3U" in playlist_file.read_text()
        
        return True
    
    def verify_configuration_operations(self, temp_env: TemporaryTestEnvironment) -> bool:
        """設定操作検証"""
        # 設定データ更新
        original_config = temp_env.get_config_data()
        temp_env.update_config_data({"prefecture": "大阪"})
        
        updated_config = temp_env.get_config_data()
        assert updated_config["prefecture"] == "大阪"
        assert updated_config["version"] == original_config["version"]
        
        # 認証データ更新
        original_auth = temp_env.get_auth_data()
        temp_env.update_auth_data({"area_id": "JP27"})
        
        updated_auth = temp_env.get_auth_data()
        assert updated_auth["area_id"] == "JP27"
        assert updated_auth["auth_token"] == original_auth["auth_token"]
        
        return True


class MockReductionPatterns:
    """モック削減パターン集"""
    
    @staticmethod
    def get_external_api_mocks() -> List[str]:
        """外部API通信で必要なモック（削減不可）"""
        return [
            "requests.get",
            "requests.post",
            "aiohttp.ClientSession",
            "urllib.request.urlopen"
        ]
    
    @staticmethod
    def get_system_interaction_mocks() -> List[str]:
        """システム操作で必要なモック（削減不可）"""
        return [
            "subprocess.run",
            "subprocess.Popen",
            "os.system",
            "shutil.which"
        ]
    
    @staticmethod
    def get_ui_interaction_mocks() -> List[str]:
        """UI操作で必要なモック（削減不可）"""
        return [
            "builtins.input",
            "sys.stdout",
            "sys.stderr",
            "keyboard.get_key"
        ]
    
    @staticmethod
    def get_replaceable_mocks() -> List[str]:
        """実環境で置き換え可能なモック"""
        return [
            "pathlib.Path.exists",
            "pathlib.Path.read_text",
            "pathlib.Path.write_text",
            "json.load",
            "json.dump",
            "tempfile.mkdtemp",
            "time.sleep"  # 短時間待機は実際に実行
        ]


# テスト実行時の環境変数設定
def setup_test_environment():
    """テスト実行環境設定"""
    os.environ["RECRADIKO_TEST_MODE"] = "true"
    os.environ["RECRADIKO_CONSOLE_OUTPUT"] = "true"
    os.environ["RECRADIKO_LOG_LEVEL"] = "DEBUG"


# pytest fixtures
import pytest

@pytest.fixture
def temp_env():
    """一時テスト環境fixture"""
    setup_test_environment()
    with TemporaryTestEnvironment() as env:
        yield env


@pytest.fixture
def real_test_base():
    """実環境テストベースfixture"""
    return RealEnvironmentTestBase()