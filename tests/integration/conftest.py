"""
結合テスト用pytest設定

このモジュールは、結合テストの実行環境をセットアップします。
- テスト用の一時ディレクトリ作成
- 共通モックの設定
- テスト前後の環境クリーンアップ
"""

import pytest
import tempfile
import shutil
import os
import json
from datetime import datetime, timedelta
from unittest.mock import Mock
from pathlib import Path

# RecRadikoモジュールのインポート
from src.auth import AuthInfo
from src.program_info import Program

# 削除されたクラスの代替定義（テスト用）
class RecordingStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class RecordingJob:
    def __init__(self, id, station_id, program_title, start_time, end_time, output_path, status):
        self.id = id
        self.station_id = station_id
        self.program_title = program_title
        self.start_time = start_time
        self.end_time = end_time
        self.output_path = output_path
        self.status = status

class FileMetadata:
    def __init__(self, file_path, program_title, station_id, recorded_at, start_time, end_time, duration_seconds, file_size, format, bitrate):
        self.file_path = file_path
        self.program_title = program_title
        self.station_id = station_id
        self.recorded_at = recorded_at
        self.start_time = start_time
        self.end_time = end_time
        self.duration_seconds = duration_seconds
        self.file_size = file_size
        self.format = format
        self.bitrate = bitrate

class StorageInfo:
    def __init__(self, total_space, used_space, free_space, recording_files_size, file_count):
        self.total_space = total_space
        self.used_space = used_space
        self.free_space = free_space
        self.recording_files_size = recording_files_size
        self.file_count = file_count


@pytest.fixture(scope="session")
def integration_test_config():
    """結合テスト用の共通設定"""
    return {
        "prefecture": "東京",  # area_id JP13 に対応
        "max_concurrent_recordings": 2,
        "default_format": "aac",
        "default_bitrate": 128,
        "notification_enabled": False,
        "log_level": "ERROR",  # テスト中はログを最小化
        "test_mode": True
    }


@pytest.fixture(scope="function")
def temp_test_environment(integration_test_config):
    """テスト用の一時環境"""
    # 一時ディレクトリの作成
    temp_dir = tempfile.mkdtemp(prefix="recradiko_integration_test_")
    
    # 必要なディレクトリの作成
    output_dir = os.path.join(temp_dir, "recordings")
    config_dir = os.path.join(temp_dir, "config")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(config_dir, exist_ok=True)
    
    # 設定ファイルの作成
    config_path = os.path.join(config_dir, "config.json")
    test_config = integration_test_config.copy()
    test_config["output_dir"] = output_dir
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(test_config, f, ensure_ascii=False, indent=2)
    
    # 環境情報をまとめて返す
    env = {
        'temp_dir': temp_dir,
        'output_dir': output_dir,
        'config_dir': config_dir,
        'config_path': config_path,
        'config': test_config
    }
    
    yield env
    
    # クリーンアップ
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def mock_auth_info():
    """認証情報のモック"""
    import time
    return AuthInfo(
        auth_token="test_integration_token",
        area_id="JP13",
        expires_at=time.time() + 3600,  # 1時間後に期限切れ
        premium_user=False
    )


@pytest.fixture(scope="function")
def mock_program():
    """番組情報のモック"""
    return Program(
        id="INTEGRATION_TEST_PROGRAM",
        station_id="TBS",
        title="結合テスト番組",
        start_time=datetime(2024, 1, 1, 20, 0, 0),
        end_time=datetime(2024, 1, 1, 21, 0, 0),
        duration=60,
        description="結合テスト用の番組データ",
        performers=["結合テスト出演者"],
        genre="テスト"
    )


@pytest.fixture(scope="function")
def mock_recording_job(temp_test_environment):
    """録音ジョブのモック"""
    return RecordingJob(
        id="integration_test_job",
        station_id="TBS",
        program_title="結合テスト録音",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(minutes=30),
        output_path=os.path.join(temp_test_environment['output_dir'], "integration_test.aac"),
        status=RecordingStatus.COMPLETED
    )


@pytest.fixture(scope="function")
def mock_file_metadata(mock_recording_job):
    """ファイルメタデータのモック"""
    return FileMetadata(
        file_path=mock_recording_job.output_path,
        program_title=mock_recording_job.program_title,
        station_id=mock_recording_job.station_id,
        recorded_at=mock_recording_job.start_time,
        start_time=mock_recording_job.start_time,
        end_time=mock_recording_job.end_time,
        duration_seconds=1800,
        file_size=1024000,
        format="aac",
        bitrate=128
    )


@pytest.fixture(scope="function")
def mock_storage_info():
    """ストレージ情報のモック"""
    return StorageInfo(
        total_space=100 * 1024**3,  # 100GB
        used_space=30 * 1024**3,    # 30GB
        free_space=70 * 1024**3,    # 70GB
        recording_files_size=25 * 1024**3,  # 25GB
        file_count=100
    )


@pytest.fixture(scope="function")
def mock_authenticator(mock_auth_info):
    """認証システムのモック"""
    authenticator = Mock()
    authenticator.authenticate.return_value = mock_auth_info
    authenticator.is_authenticated.return_value = True
    authenticator.get_auth_info.return_value = mock_auth_info
    return authenticator


@pytest.fixture(scope="function")
def mock_streaming_manager():
    """ストリーミング管理のモック"""
    streaming_manager = Mock()
    
    # ストリーム情報のモック
    mock_stream_info = Mock()
    mock_stream_info.stream_url = "https://example.com/integration_test.m3u8"
    mock_stream_info.station_id = "TBS"
    mock_stream_info.auth_token = "test_integration_token"
    
    streaming_manager.get_stream_url.return_value = "https://example.com/integration_test.m3u8"
    streaming_manager.parse_playlist.return_value = mock_stream_info
    return streaming_manager


@pytest.fixture(scope="function")
def mock_recording_manager(mock_recording_job):
    """録音管理のモック"""
    recording_manager = Mock()
    recording_manager.create_recording_job.return_value = mock_recording_job
    recording_manager.list_jobs.return_value = [mock_recording_job]
    recording_manager.get_job.return_value = mock_recording_job
    return recording_manager


@pytest.fixture(scope="function")
def mock_file_manager(mock_file_metadata, mock_storage_info):
    """ファイル管理のモック"""
    file_manager = Mock()
    file_manager.register_file.return_value = mock_file_metadata
    file_manager.get_storage_info.return_value = mock_storage_info
    file_manager.list_files.return_value = [mock_file_metadata]
    return file_manager


@pytest.fixture(scope="function")
def mock_scheduler():
    """スケジューラーのモック"""
    scheduler = Mock()
    scheduler.add_schedule.return_value = True
    scheduler.remove_schedule.return_value = True
    scheduler.list_schedules.return_value = []
    scheduler.get_next_schedules.return_value = []
    return scheduler


@pytest.fixture(scope="function")
def mock_error_handler():
    """エラーハンドラーのモック"""
    error_handler = Mock()
    error_handler.handle_error.return_value = None
    error_handler.get_error_statistics.return_value = {
        'total_errors': 0,
        'unresolved_errors': 0,
        'recent_errors_24h': 0
    }
    return error_handler


@pytest.fixture(scope="function")
def mock_notification_handler():
    """通知ハンドラーのモック"""
    notification_handler = Mock()
    notification_handler.notify.return_value = None
    return notification_handler


@pytest.fixture(scope="session", autouse=True)
def setup_integration_test_environment():
    """結合テスト環境の全体セットアップ"""
    # テスト開始前の環境設定
    print("\n🔧 結合テスト環境セットアップ中...")
    
    # 必要に応じて外部サービスのモック設定
    # 例: Radikoサーバーのモック、FFmpegのモック等
    
    yield
    
    # テスト完了後のクリーンアップ
    print("\n🧹 結合テスト環境クリーンアップ中...")


# カスタムマーカーの定義
def pytest_configure(config):
    """pytest設定の追加"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running test"
    )


# テスト収集のカスタマイズ
def pytest_collection_modifyitems(config, items):
    """テスト項目の修正"""
    # 結合テストには自動的にマーカーを追加
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # E2Eテストの識別
        if "e2e" in item.name.lower():
            item.add_marker(pytest.mark.e2e)
        
        # 長時間実行テストの識別
        if any(keyword in item.name.lower() for keyword in ["workflow", "daemon", "concurrent"]):
            item.add_marker(pytest.mark.slow)


# エラー時の追加情報
@pytest.fixture(autouse=True)
def log_test_info(request):
    """テスト情報のログ出力"""
    test_name = request.node.name
    print(f"\n🧪 実行中: {test_name}")
    
    yield
    
    # テスト終了後の処理
    if hasattr(request.node, 'rep_call') and hasattr(request.node.rep_call, 'failed') and request.node.rep_call.failed:
        print(f"❌ 失敗: {test_name}")


# テスト結果の記録
def pytest_runtest_makereport(item, call):
    """テスト結果の記録"""
    if call.when == "call":
        setattr(item, "rep_" + call.when, call)