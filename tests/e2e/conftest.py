"""
E2Eテスト用のpytestフィクスチャと設定

このモジュールは、エンドツーエンドテストで使用する共通フィクスチャ、
テストデータ生成、環境設定などを提供します。
"""

import pytest
import tempfile
import shutil
import os
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Generator
from unittest.mock import Mock, patch

# RecRadikoモジュール
from src.cli import RecRadikoCLI
from src.auth import RadikoAuthenticator, AuthInfo
from src.program_info import ProgramInfoManager, Program, Station
from src.streaming import StreamingManager, StreamInfo, StreamSegment
from src.recording import RecordingManager, RecordingJob, RecordingStatus
from src.file_manager import FileManager, FileMetadata, StorageInfo
from src.scheduler import RecordingScheduler, RecordingSchedule, RepeatPattern, ScheduleStatus
from src.daemon import DaemonManager, DaemonStatus
from src.error_handler import ErrorHandler, ErrorRecord
from src.live_streaming import (
    LivePlaylistMonitor, SegmentTracker, SegmentDownloader, 
    LiveRecordingSession, Segment, PlaylistUpdate
)
from src.live_streaming_config import get_config_for_environment


@pytest.fixture(scope="session")
def e2e_config():
    """E2Eテスト用の基本設定"""
    return {
        "test_mode": True,
        "time_acceleration": 100,  # テスト時間を100倍速にする
        "max_test_duration": 3600,  # 最大1時間でテスト終了
        "cleanup_on_failure": True,
        "detailed_logging": True,
        "resource_monitoring": True
    }


@pytest.fixture
def temp_environment():
    """一時テスト環境の作成・削除"""
    temp_dir = tempfile.mkdtemp(prefix="recradiko_e2e_")
    
    # テスト環境構造の作成
    test_env = {
        "base_dir": temp_dir,
        "config_dir": os.path.join(temp_dir, "config"),
        "output_dir": os.path.join(temp_dir, "recordings"),
        "log_dir": os.path.join(temp_dir, "logs"),
        "data_dir": os.path.join(temp_dir, "data"),
        "cache_dir": os.path.join(temp_dir, "cache")
    }
    
    # ディレクトリ作成
    for dir_path in test_env.values():
        if isinstance(dir_path, str):
            os.makedirs(dir_path, exist_ok=True)
    
    yield test_env
    
    # クリーンアップ
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_config(temp_environment):
    """E2Eテスト用の設定ファイル生成"""
    config = {
        "prefecture": "東京",  # area_id JP13 に対応
        "output_dir": temp_environment["output_dir"],
        "max_concurrent_recordings": 8,
        "auto_cleanup_enabled": True,
        "retention_days": 7,
        "min_free_space_gb": 1.0,
        "notification_enabled": False,
        "log_level": "DEBUG",
        "daemon": {
            "health_check_interval": 10,
            "monitoring_enabled": True,
            "pid_file": os.path.join(temp_environment["config_dir"], "daemon.pid")
        },
        "recording": {
            "default_format": "aac",
            "default_bitrate": 128,
            "max_concurrent_jobs": 3,
            "auto_metadata_enabled": True,
            "quality_check_enabled": True
        },
        "streaming": {
            "max_workers": 4,
            "segment_buffer_size": 50,
            "connection_timeout": 30,
            "retry_segment_attempts": 3
        },
        "file_manager": {
            "metadata_file": os.path.join(temp_environment["data_dir"], "metadata.json"),
            "auto_cleanup_enabled": True,
            "checksum_verification": True
        },
        "error_handler": {
            "max_error_records": 1000,
            "notification_enabled": False
        },
        "e2e_test": {
            "time_acceleration": 100,
            "mock_external_apis": True,
            "simulate_network_conditions": True
        },
        "live_streaming": get_config_for_environment('test')
    }
    
    config_path = os.path.join(temp_environment["config_dir"], "config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    return config_path, config


class TimeAccelerator:
    """時間加速機能を提供するクラス"""
    
    def __init__(self, acceleration_factor: int = 100):
        self.acceleration_factor = acceleration_factor
        self.start_time = time.time()
        self.accelerated_time = 0
    
    def accelerated_sleep(self, seconds: float):
        """加速された sleep"""
        actual_sleep = seconds / self.acceleration_factor
        time.sleep(actual_sleep)
    
    def accelerated_datetime(self, base_time: datetime = None) -> datetime:
        """加速された現在時刻"""
        if base_time is None:
            base_time = datetime.now()
        
        elapsed = time.time() - self.start_time
        accelerated_elapsed = elapsed * self.acceleration_factor
        return base_time + timedelta(seconds=accelerated_elapsed)


@pytest.fixture
def time_accelerator(e2e_config):
    """時間加速フィクスチャ"""
    return TimeAccelerator(e2e_config["time_acceleration"])


class TestDataGenerator:
    """テストデータ生成クラス"""
    
    @staticmethod
    def generate_stations(count: int = 50) -> List[Station]:
        """テスト用放送局データ生成"""
        stations = []
        base_stations = [
            ("TBS", "TBSラジオ", "JP13"),
            ("QRR", "文化放送", "JP13"),
            ("LFR", "ニッポン放送", "JP13"),
            ("RN1", "ラジオNIKKEI第1", "JP13"),
            ("FMT", "TOKYO FM", "JP13"),
        ]
        
        for i in range(count):
            base_idx = i % len(base_stations)
            station_id, name, area = base_stations[base_idx]
            
            if i >= len(base_stations):
                station_id = f"{station_id}_{i}"
                name = f"{name}_{i}"
            
            stations.append(Station(
                id=station_id,
                name=name,
                ascii_name=station_id,
                area_id=area,
                logo_url=f"https://example.com/logo/{station_id}.png",
                banner_url=f"https://example.com/banner/{station_id}.png"
            ))
        
        return stations
    
    @staticmethod
    def generate_programs(stations: List[Station], days: int = 7) -> List[Program]:
        """テスト用番組データ生成"""
        programs = []
        base_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        program_templates = [
            ("朝のニュース", 6, 8, "ニュース・報道"),
            ("音楽番組", 8, 10, "音楽"),
            ("トーク番組", 10, 12, "バラエティ"),
            ("ランチタイム", 12, 13, "音楽"),
            ("午後の情報番組", 13, 15, "情報"),
            ("夕方ニュース", 17, 19, "ニュース・報道"),
            ("ゴールデンタイム", 20, 22, "バラエティ"),
            ("深夜番組", 23, 25, "音楽"),
        ]
        
        program_id = 1
        for day in range(days):
            current_date = base_time + timedelta(days=day)
            
            for station in stations:
                for title, start_hour, end_hour, genre in program_templates:
                    start_time = current_date + timedelta(hours=start_hour)
                    end_time = current_date + timedelta(hours=end_hour)
                    
                    programs.append(Program(
                        id=f"{station.id}_{current_date.strftime('%Y%m%d')}_{start_hour:02d}00",
                        station_id=station.id,
                        title=f"{title}@{station.name}",
                        start_time=start_time,
                        end_time=end_time,
                        duration=(end_hour - start_hour) * 60,
                        description=f"{station.name}の{title}",
                        performers=[f"出演者{program_id}", f"ゲスト{program_id}"],
                        genre=genre
                    ))
                    program_id += 1
        
        return programs
    
    @staticmethod
    def generate_schedules(stations: List[Station], count: int = 100) -> List[RecordingSchedule]:
        """テスト用録音スケジュール生成"""
        schedules = []
        base_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        repeat_patterns = [
            RepeatPattern.NONE,
            RepeatPattern.DAILY, 
            RepeatPattern.WEEKLY,
            RepeatPattern.WEEKDAYS,
            RepeatPattern.WEEKENDS,
            RepeatPattern.MONTHLY
        ]
        
        for i in range(count):
            station = stations[i % len(stations)]
            pattern = repeat_patterns[i % len(repeat_patterns)]
            
            start_time = base_time + timedelta(
                days=i % 30,
                hours=(6 + i * 2) % 24,
                minutes=(i * 15) % 60
            )
            end_time = start_time + timedelta(hours=1 + (i % 3))
            
            schedules.append(RecordingSchedule(
                schedule_id=f"schedule_{i:04d}",
                station_id=station.id,
                program_title=f"テスト番組_{i:04d}",
                start_time=start_time,
                end_time=end_time,
                repeat_pattern=pattern,
                repeat_end_date=base_time + timedelta(days=365) if pattern != RepeatPattern.NONE else None,
                status=ScheduleStatus.ACTIVE,
                format="aac",
                bitrate=128 + (i % 4) * 64,
                notification_enabled=i % 2 == 0,
                notification_minutes=5 if i % 3 == 0 else 1
            ))
        
        return schedules
    
    @staticmethod
    def generate_large_file_set(base_dir: str, file_count: int = 10000) -> List[str]:
        """大量ファイルセット生成（テスト用ダミーファイル）"""
        files = []
        
        for i in range(file_count):
            # 日付ベースのディレクトリ構造
            date = datetime.now() - timedelta(days=i // 50)
            year_dir = os.path.join(base_dir, str(date.year))
            month_dir = os.path.join(year_dir, f"{date.month:02d}")
            day_dir = os.path.join(month_dir, f"{date.day:02d}")
            
            os.makedirs(day_dir, exist_ok=True)
            
            # ファイル作成
            station_id = f"STATION_{(i % 10) + 1:02d}"
            filename = f"{station_id}_program_{i:05d}_{date.strftime('%Y%m%d_%H%M%S')}.aac"
            file_path = os.path.join(day_dir, filename)
            
            # ダミーファイル作成（サイズを調整）
            file_size = 1024 * 1024 * (5 + (i % 10))  # 5-15MB
            with open(file_path, 'wb') as f:
                f.write(b'0' * file_size)
            
            files.append(file_path)
        
        return files


@pytest.fixture
def test_data_generator():
    """テストデータジェネレータ"""
    return TestDataGenerator()


@pytest.fixture
def large_test_dataset(test_data_generator, temp_environment):
    """大規模テストデータセット"""
    stations = test_data_generator.generate_stations(50)
    programs = test_data_generator.generate_programs(stations, 30)  # 30日分
    schedules = test_data_generator.generate_schedules(stations, 5000)  # 5000スケジュール
    
    return {
        "stations": stations,
        "programs": programs,
        "schedules": schedules,
        "station_count": len(stations),
        "program_count": len(programs),
        "schedule_count": len(schedules)
    }


class ResourceMonitor:
    """リソース監視クラス"""
    
    def __init__(self):
        self.monitoring = False
        self.stats = {
            "cpu_usage": [],
            "memory_usage": [],
            "disk_usage": [],
            "network_io": [],
            "process_count": []
        }
        self.monitor_thread = None
    
    def start_monitoring(self, interval: float = 1.0):
        """監視開始"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """監視停止"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self, interval: float):
        """監視ループ"""
        try:
            import psutil
        except ImportError:
            return
        
        while self.monitoring:
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.stats["cpu_usage"].append({
                    "timestamp": time.time(),
                    "value": cpu_percent
                })
                
                # メモリ使用量
                memory = psutil.virtual_memory()
                self.stats["memory_usage"].append({
                    "timestamp": time.time(),
                    "value": memory.percent,
                    "available_gb": memory.available / (1024**3)
                })
                
                # ディスク使用量
                disk = psutil.disk_usage('/')
                self.stats["disk_usage"].append({
                    "timestamp": time.time(),
                    "value": (disk.used / disk.total) * 100,
                    "free_gb": disk.free / (1024**3)
                })
                
                # プロセス数
                process_count = len(psutil.pids())
                self.stats["process_count"].append({
                    "timestamp": time.time(),
                    "value": process_count
                })
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"監視エラー: {e}")
                break
    
    def get_summary(self) -> Dict[str, Any]:
        """監視結果サマリー"""
        summary = {}
        
        for metric, values in self.stats.items():
            if not values:
                continue
            
            numeric_values = [v["value"] for v in values]
            summary[metric] = {
                "count": len(numeric_values),
                "min": min(numeric_values),
                "max": max(numeric_values),
                "avg": sum(numeric_values) / len(numeric_values),
                "latest": numeric_values[-1] if numeric_values else 0
            }
        
        return summary


@pytest.fixture
def resource_monitor():
    """リソース監視フィクスチャ"""
    monitor = ResourceMonitor()
    yield monitor
    monitor.stop_monitoring()


@pytest.fixture
def mock_external_services():
    """外部サービスのモック"""
    with patch('src.auth.RadikoAuthenticator.authenticate') as mock_auth, \
         patch('src.streaming.StreamingManager.get_stream_url') as mock_stream, \
         patch('src.program_info.ProgramInfoManager.fetch_station_list') as mock_stations, \
         patch('src.program_info.ProgramInfoManager.fetch_program_guide') as mock_programs:
        
        # 認証モック
        mock_auth.return_value = AuthInfo(
            auth_token="test_token_e2e",
            area_id="JP13",
            expires_at=time.time() + 7200,
            premium_user=False
        )
        
        # ストリーミングモック
        mock_stream.return_value = "https://example.com/test_stream.m3u8"
        
        # 放送局・番組モックは動的に設定
        yield {
            "auth": mock_auth,
            "stream": mock_stream,
            "stations": mock_stations,
            "programs": mock_programs
        }


@pytest.fixture
def network_simulator():
    """ネットワーク状態シミュレータ"""
    class NetworkSimulator:
        def __init__(self):
            self.conditions = {
                "latency": 0,  # ms
                "packet_loss": 0,  # %
                "bandwidth_limit": None,  # Mbps
                "connection_drops": False
            }
        
        def set_poor_connection(self):
            """低品質接続をシミュレート"""
            self.conditions = {
                "latency": 1000,
                "packet_loss": 5,
                "bandwidth_limit": 1,
                "connection_drops": False
            }
        
        def set_unstable_connection(self):
            """不安定接続をシミュレート"""
            self.conditions = {
                "latency": 500,
                "packet_loss": 2,
                "bandwidth_limit": 5,
                "connection_drops": True
            }
        
        def set_normal_connection(self):
            """正常接続をリストア"""
            self.conditions = {
                "latency": 50,
                "packet_loss": 0,
                "bandwidth_limit": None,
                "connection_drops": False
            }
        
        def simulate_network_error(self):
            """ネットワークエラーをシミュレート"""
            import requests
            raise requests.exceptions.ConnectionError("Simulated network error")
    
    return NetworkSimulator()


@pytest.fixture
def live_streaming_environment(temp_environment):
    """ライブストリーミングテスト用環境"""
    # ライブストリーミング専用ディレクトリ
    live_dirs = {
        "segment_cache_dir": os.path.join(temp_environment["cache_dir"], "segments"),
        "playlist_cache_dir": os.path.join(temp_environment["cache_dir"], "playlists"),
        "live_output_dir": os.path.join(temp_environment["output_dir"], "live")
    }
    
    for dir_path in live_dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    # ライブストリーミング設定
    live_config = get_config_for_environment('test')
    
    return {
        **temp_environment,
        **live_dirs,
        "live_config": live_config
    }


@pytest.fixture
def mock_live_streaming_services():
    """ライブストリーミング用外部サービスモック"""
    mock_playlist_content = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:12345
#EXTINF:10.0,
https://example.com/segment_001.ts
#EXTINF:10.0,
https://example.com/segment_002.ts
#EXTINF:10.0,
https://example.com/segment_003.ts"""
    
    mock_segment_data = b'test_segment_data_' + b'0' * 1024  # 1KB of test data
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        # セッションモック
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # プレイリスト取得モック
        async def mock_get_playlist(*args, **kwargs):
            mock_response = Mock()
            mock_response.status = 200
            mock_response.text = Mock(return_value=mock_playlist_content)
            
            # context manager の模擬
            mock_context = Mock()
            mock_context.__aenter__ = Mock(return_value=mock_response)
            mock_context.__aexit__ = Mock(return_value=None)
            return mock_context
        
        # セグメント取得モック
        async def mock_get_segment(*args, **kwargs):
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read = Mock(return_value=mock_segment_data)
            
            mock_context = Mock()
            mock_context.__aenter__ = Mock(return_value=mock_response)
            mock_context.__aexit__ = Mock(return_value=None)
            return mock_context
        
        mock_session.get.side_effect = [mock_get_playlist, mock_get_segment, mock_get_segment]
        
        yield {
            "session_class": mock_session_class,
            "session": mock_session,
            "playlist_content": mock_playlist_content,
            "segment_data": mock_segment_data
        }


# E2Eテスト用のマーカー定義
def pytest_configure(config):
    """pytestマーカーの設定"""
    config.addinivalue_line(
        "markers", "e2e: エンドツーエンドテスト"
    )
    config.addinivalue_line(
        "markers", "user_journey: ユーザージャーニーテスト"
    )
    config.addinivalue_line(
        "markers", "system_operation: システム稼働テスト"
    )
    config.addinivalue_line(
        "markers", "failure_recovery: 障害復旧テスト"
    )
    config.addinivalue_line(
        "markers", "performance: パフォーマンステスト"
    )
    config.addinivalue_line(
        "markers", "slow: 長時間実行テスト"
    )
    config.addinivalue_line(
        "markers", "resource_intensive: リソース集約テスト"
    )
    config.addinivalue_line(
        "markers", "live_streaming: ライブストリーミングテスト"
    )
    config.addinivalue_line(
        "markers", "real_api: 実際のAPI使用テスト"
    )