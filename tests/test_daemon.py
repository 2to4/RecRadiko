"""
デーモンモジュールの単体テスト
"""

import unittest
import tempfile
import os
import signal
import time
import threading
import json
import subprocess
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta

from src.daemon import (
    DaemonManager, DaemonStatus, DaemonError, HealthStatus, MonitoringInfo
)


class TestDaemonStatus(unittest.TestCase):
    """DaemonStatus Enum のテスト"""
    
    def test_daemon_status_values(self):
        """DaemonStatus の値テスト"""
        self.assertEqual(DaemonStatus.STOPPED.value, "stopped")
        self.assertEqual(DaemonStatus.STARTING.value, "starting")
        self.assertEqual(DaemonStatus.RUNNING.value, "running")
        self.assertEqual(DaemonStatus.STOPPING.value, "stopping")
        self.assertEqual(DaemonStatus.ERROR.value, "error")


class TestHealthStatus(unittest.TestCase):
    """HealthStatus Enum のテスト"""
    
    def test_health_status_values(self):
        """HealthStatus の値テスト"""
        self.assertEqual(HealthStatus.HEALTHY.value, "healthy")
        self.assertEqual(HealthStatus.WARNING.value, "warning")
        self.assertEqual(HealthStatus.CRITICAL.value, "critical")
        self.assertEqual(HealthStatus.UNKNOWN.value, "unknown")


class TestMonitoringInfo(unittest.TestCase):
    """MonitoringInfo クラスのテスト"""
    
    def test_monitoring_info_creation(self):
        """MonitoringInfo の作成テスト"""
        timestamp = datetime.now()
        
        info = MonitoringInfo(
            timestamp=timestamp,
            daemon_status=DaemonStatus.RUNNING,
            health_status=HealthStatus.HEALTHY,
            uptime_seconds=3600,
            cpu_usage_percent=15.5,
            memory_usage_mb=256.8,
            active_recordings=2,
            scheduled_recordings=5,
            error_count=0,
            last_error_time=None,
            storage_free_gb=10.5
        )
        
        self.assertEqual(info.timestamp, timestamp)
        self.assertEqual(info.daemon_status, DaemonStatus.RUNNING)
        self.assertEqual(info.health_status, HealthStatus.HEALTHY)
        self.assertEqual(info.uptime_seconds, 3600)
        self.assertEqual(info.cpu_usage_percent, 15.5)
        self.assertEqual(info.memory_usage_mb, 256.8)
        self.assertEqual(info.active_recordings, 2)
        self.assertEqual(info.scheduled_recordings, 5)
        self.assertEqual(info.error_count, 0)
        self.assertIsNone(info.last_error_time)
        self.assertEqual(info.storage_free_gb, 10.5)
    
    def test_monitoring_info_to_dict(self):
        """MonitoringInfo の辞書変換テスト"""
        timestamp = datetime.now()
        
        info = MonitoringInfo(
            timestamp=timestamp,
            daemon_status=DaemonStatus.RUNNING,
            health_status=HealthStatus.HEALTHY,
            uptime_seconds=3600,
            cpu_usage_percent=15.5,
            memory_usage_mb=256.8,
            active_recordings=2,
            scheduled_recordings=5,
            error_count=0,
            last_error_time=None,
            storage_free_gb=10.5
        )
        
        info_dict = info.to_dict()
        
        self.assertEqual(info_dict['daemon_status'], "running")
        self.assertEqual(info_dict['health_status'], "healthy")
        self.assertEqual(info_dict['uptime_seconds'], 3600)
        self.assertEqual(info_dict['cpu_usage_percent'], 15.5)
        self.assertEqual(info_dict['memory_usage_mb'], 256.8)
        self.assertEqual(info_dict['active_recordings'], 2)
        self.assertEqual(info_dict['scheduled_recordings'], 5)
        self.assertEqual(info_dict['error_count'], 0)
        self.assertIsNone(info_dict['last_error_time'])
        self.assertEqual(info_dict['storage_free_gb'], 10.5)
        self.assertIn('timestamp', info_dict)


class TestDaemonManager(unittest.TestCase):
    """DaemonManager クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.pid_file = f"{self.temp_dir}/test_daemon.pid"
        self.log_file = f"{self.temp_dir}/test_daemon.log"
        self.status_file = f"{self.temp_dir}/test_status.json"
        
        # モックオブジェクトの作成
        self.mock_scheduler = Mock()
        self.mock_recording = Mock()
        self.mock_file_manager = Mock()
        self.mock_error_handler = Mock()
        self.mock_notification_handler = Mock()
        self.mock_authenticator = Mock()
        
        self.daemon = DaemonManager(
            scheduler=self.mock_scheduler,
            recording_manager=self.mock_recording,
            file_manager=self.mock_file_manager,
            error_handler=self.mock_error_handler,
            notification_handler=self.mock_notification_handler,
            authenticator=self.mock_authenticator,
            pid_file=self.pid_file,
            log_file=self.log_file,
            status_file=self.status_file,
            health_check_interval=1,  # テスト用に短い間隔
            monitoring_enabled=True
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        try:
            self.daemon.stop()
        except:
            pass
        
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_daemon_creation(self):
        """DaemonManager の作成テスト"""
        self.assertIsInstance(self.daemon, DaemonManager)
        self.assertEqual(str(self.daemon.pid_file), self.pid_file)
        self.assertEqual(str(self.daemon.log_file), self.log_file)
        self.assertEqual(str(self.daemon.status_file), self.status_file)
        self.assertEqual(self.daemon.health_check_interval, 1)
        self.assertTrue(self.daemon.monitoring_enabled)
        self.assertEqual(self.daemon.get_status(), DaemonStatus.STOPPED)
    
    def test_start_daemon_success(self):
        """デーモン開始成功のテスト"""
        result = self.daemon.start()
        
        self.assertTrue(result)
        self.assertEqual(self.daemon.status, DaemonStatus.RUNNING)
        self.assertIsNotNone(self.daemon.start_time)
        
        # PIDファイルが作成されることを確認
        self.assertTrue(os.path.exists(self.pid_file))
        
        # 少し待ってからステータスファイルが作成されることを確認
        time.sleep(0.1)
        self.assertTrue(os.path.exists(self.status_file))
        
        # 停止
        self.daemon.stop()
    
    def test_start_daemon_already_running(self):
        """既に実行中のデーモン開始のテスト"""
        # デーモンを開始
        self.daemon.start()
        
        # 再度開始を試行
        result = self.daemon.start()
        
        self.assertFalse(result)  # 既に実行中なので失敗
        
        # 停止
        self.daemon.stop()
    
    def test_stop_daemon_success(self):
        """デーモン停止成功のテスト"""
        # デーモンを開始
        self.daemon.start()
        time.sleep(0.1)  # 少し待つ
        
        # デーモンを停止
        result = self.daemon.stop()
        
        self.assertTrue(result)
        self.assertEqual(self.daemon.status, DaemonStatus.STOPPED)
        
        # PIDファイルが削除されることを確認
        self.assertFalse(os.path.exists(self.pid_file))
    
    def test_stop_daemon_not_running(self):
        """実行されていないデーモン停止のテスト"""
        # デーモンが実行されていない状態で停止を試行
        result = self.daemon.stop()
        
        self.assertFalse(result)  # 実行されていないので失敗
        self.assertEqual(self.daemon.status, DaemonStatus.STOPPED)
    
    def test_restart_daemon_success(self):
        """デーモン再起動成功のテスト"""
        # デーモンを開始
        self.daemon.start()
        original_start_time = self.daemon.start_time
        time.sleep(0.1)
        
        # デーモンを再起動
        result = self.daemon.restart()
        
        self.assertTrue(result)
        self.assertEqual(self.daemon.status, DaemonStatus.RUNNING)
        self.assertNotEqual(self.daemon.start_time, original_start_time)
        
        # 停止
        self.daemon.stop()
    
    def test_reload_config_success(self):
        """設定再読み込み成功のテスト"""
        # デーモンを開始
        self.daemon.start()
        time.sleep(0.1)
        
        # 設定再読み込み
        result = self.daemon.reload_config()
        
        self.assertTrue(result)
        
        # 停止
        self.daemon.stop()
    
    def test_get_status(self):
        """ステータス取得のテスト"""
        # 停止状態でのステータス
        status_stopped = self.daemon.get_status()
        self.assertEqual(status_stopped, DaemonStatus.STOPPED)
        
        # 実行状態でのステータス
        self.daemon.start()
        status_running = self.daemon.get_status()
        self.assertEqual(status_running, DaemonStatus.RUNNING)
        
        # 停止
        self.daemon.stop()
    
    def test_is_running(self):
        """実行状態判定のテスト"""
        # 停止状態
        self.assertFalse(self.daemon.is_running())
        
        # 実行状態
        self.daemon.start()
        self.assertTrue(self.daemon.is_running())
        
        # 停止
        self.daemon.stop()
        self.assertFalse(self.daemon.is_running())
    
    def test_get_pid(self):
        """PID取得のテスト"""
        # 停止状態
        self.assertIsNone(self.daemon.get_pid())
        
        # 実行状態
        self.daemon.start()
        pid = self.daemon.get_pid()
        self.assertIsNotNone(pid)
        self.assertIsInstance(pid, int)
        self.assertGreater(pid, 0)
        
        # 停止
        self.daemon.stop()
        self.assertIsNone(self.daemon.get_pid())
    
    def test_get_uptime(self):
        """稼働時間取得のテスト"""
        # 停止状態
        self.assertEqual(self.daemon.get_uptime(), 0)
        
        # 実行状態
        self.daemon.start()
        time.sleep(1.1)  # 1秒以上待機
        uptime = self.daemon.get_uptime()
        self.assertGreater(uptime, 0)
        self.assertLess(uptime, 2)  # 2秒未満
        
        # 停止
        self.daemon.stop()
    
    @patch('psutil.Process')
    def test_get_monitoring_info(self, mock_process_class):
        """監視情報取得のテスト"""
        # psutilのモック設定
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 15.5
        mock_process.memory_info.return_value.rss = 256 * 1024 * 1024  # 256MB
        mock_process_class.return_value = mock_process
        
        # レコーディングマネージャーのモック設定
        self.mock_recording.list_jobs.return_value = [Mock(), Mock()]  # 2つのアクティブ録音
        
        # スケジューラーのモック設定
        self.mock_scheduler.get_next_schedules.return_value = [Mock() for _ in range(5)]  # 5つの予定
        
        # ファイルマネージャーのモック設定
        from src.file_manager import StorageInfo
        mock_storage = StorageInfo(
            total_space=100 * 1024**3,  # 100GB
            used_space=90 * 1024**3,    # 90GB使用
            free_space=10 * 1024**3,    # 10GB空き
            recording_files_size=50 * 1024**3,  # 録音ファイル50GB
            file_count=100
        )
        self.mock_file_manager.get_storage_info.return_value = mock_storage
        
        # エラーハンドラーのモック設定
        self.mock_error_handler.get_error_statistics.return_value = {
            'unresolved_errors': 0,
            'recent_errors': []
        }
        
        # デーモンを開始
        self.daemon.start()
        time.sleep(0.1)
        
        # 監視情報を取得
        info = self.daemon.get_monitoring_info()
        
        self.assertIsInstance(info, MonitoringInfo)
        self.assertEqual(info.daemon_status, DaemonStatus.RUNNING)
        self.assertEqual(info.health_status, HealthStatus.HEALTHY)
        self.assertEqual(info.cpu_usage_percent, 15.5)
        self.assertAlmostEqual(info.memory_usage_mb, 256.0, places=1)
        self.assertEqual(info.active_recordings, 2)
        self.assertEqual(info.scheduled_recordings, 5)
        self.assertEqual(info.error_count, 0)
        self.assertAlmostEqual(info.storage_free_gb, 10.0, places=1)
        
        # 停止
        self.daemon.stop()
    
    @patch('psutil.Process')
    def test_assess_health_healthy(self, mock_process_class):
        """健全性評価 - 健全な状態のテスト"""
        # psutilのモック設定（正常な値）
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 10.0  # 低いCPU使用率
        mock_process.memory_info.return_value.rss = 128 * 1024 * 1024  # 128MB
        mock_process_class.return_value = mock_process
        
        # ストレージ情報のモック（十分な空き容量）
        from src.file_manager import StorageInfo
        mock_storage = StorageInfo(
            total_space=100 * 1024**3,
            used_space=50 * 1024**3,
            free_space=50 * 1024**3,  # 50GB空き
            recording_files_size=25 * 1024**3,
            file_count=50
        )
        self.mock_file_manager.get_storage_info.return_value = mock_storage
        
        # エラー統計のモック（エラーなし）
        self.mock_error_handler.get_error_statistics.return_value = {
            'unresolved_errors': 0,
            'recent_errors': []
        }
        
        # 認証状態のモック（認証成功）
        self.mock_authenticator.is_authenticated.return_value = True
        
        self.daemon.start()
        time.sleep(0.1)
        
        health = self.daemon._assess_health()
        self.assertEqual(health, HealthStatus.HEALTHY)
        
        self.daemon.stop()
    
    @patch('psutil.Process')
    def test_assess_health_warning(self, mock_process_class):
        """健全性評価 - 警告状態のテスト"""
        # psutilのモック設定（やや高いCPU使用率）
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 85.0  # 高いCPU使用率
        mock_process.memory_info.return_value.rss = 128 * 1024 * 1024
        mock_process_class.return_value = mock_process
        
        # ストレージ情報のモック（少ない空き容量）
        from src.file_manager import StorageInfo
        mock_storage = StorageInfo(
            total_space=100 * 1024**3,
            used_space=98 * 1024**3,
            free_space=2 * 1024**3,  # 2GB空き（少ない）
            recording_files_size=50 * 1024**3,
            file_count=100
        )
        self.mock_file_manager.get_storage_info.return_value = mock_storage
        
        # エラー統計のモック（少数のエラー）
        self.mock_error_handler.get_error_statistics.return_value = {
            'unresolved_errors': 2,
            'recent_errors': [Mock(), Mock()]
        }
        
        self.daemon.start()
        time.sleep(0.1)
        
        health = self.daemon._assess_health()
        self.assertEqual(health, HealthStatus.WARNING)
        
        self.daemon.stop()
    
    @patch('psutil.Process')
    def test_assess_health_critical(self, mock_process_class):
        """健全性評価 - 重篤状態のテスト"""
        # psutilのモック設定（非常に高いCPU使用率）
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 98.0  # 非常に高いCPU使用率
        mock_process.memory_info.return_value.rss = 2 * 1024**3  # 2GB（高いメモリ使用量）
        mock_process_class.return_value = mock_process
        
        # ストレージ情報のモック（非常に少ない空き容量）
        from src.file_manager import StorageInfo
        mock_storage = StorageInfo(
            total_space=100 * 1024**3,
            used_space=99.5 * 1024**3,
            free_space=0.5 * 1024**3,  # 0.5GB空き（非常に少ない）
            recording_files_size=80 * 1024**3,
            file_count=200
        )
        self.mock_file_manager.get_storage_info.return_value = mock_storage
        
        # エラー統計のモック（多数のエラー）
        self.mock_error_handler.get_error_statistics.return_value = {
            'unresolved_errors': 10,
            'recent_errors': [Mock() for _ in range(10)]
        }
        
        self.daemon.start()
        time.sleep(0.1)
        
        health = self.daemon._assess_health()
        self.assertEqual(health, HealthStatus.CRITICAL)
        
        self.daemon.stop()
    
    def test_signal_handling(self):
        """シグナルハンドリングのテスト"""
        # デーモンを開始
        self.daemon.start()
        time.sleep(0.1)
        
        # TERMシグナルを送信してみる（実際にはテスト環境では送信しない）
        # ここではシグナルハンドラーが正しく設定されているかをテスト
        self.assertTrue(hasattr(self.daemon, '_signal_handler'))
        
        # 通常の停止
        self.daemon.stop()
    
    def test_save_load_status(self):
        """ステータス保存・読み込みのテスト"""
        # デーモンを開始
        self.daemon.start()
        time.sleep(0.1)
        
        # ステータスを保存
        self.daemon._save_status()
        
        # ステータスファイルが作成されることを確認
        self.assertTrue(os.path.exists(self.status_file))
        
        # ステータスファイルの内容を確認
        with open(self.status_file, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        
        self.assertEqual(status_data['daemon_status'], "running")
        self.assertIn('timestamp', status_data)
        self.assertIn('uptime_seconds', status_data)
        
        # 停止
        self.daemon.stop()
    
    def test_health_check_thread(self):
        """ヘルスチェックスレッドのテスト"""
        # デーモンを開始（ヘルスチェックスレッドも開始される）
        self.daemon.start()
        
        # 少し待ってヘルスチェックが実行されることを確認
        time.sleep(1.5)  # health_check_interval が 1秒なので
        
        # ヘルスチェックスレッドが実行されていることを確認
        self.assertTrue(self.daemon._health_check_thread.is_alive())
        
        # 停止
        self.daemon.stop()
        
        # 少し待ってスレッドが終了することを確認
        time.sleep(0.1)
        self.assertFalse(self.daemon._health_check_thread.is_alive())
    
    def test_notification_on_health_change(self):
        """健全性変化時の通知のテスト"""
        # 通知ハンドラーのモック
        notification_calls = []
        
        def mock_notify(message, severity):
            notification_calls.append((message, severity))
        
        self.mock_notification_handler.notify = mock_notify
        
        # デーモンを開始
        self.daemon.start()
        
        # 健全性を変更する（モックの戻り値を変更）
        with patch.object(self.daemon, '_assess_health') as mock_assess:
            # 最初の状態を設定（まず健全で初期化）
            mock_assess.return_value = HealthStatus.HEALTHY
            self.daemon._perform_health_check()
            
            # 警告状態に変化
            mock_assess.return_value = HealthStatus.WARNING
            self.daemon._perform_health_check()
            
            # 重篤状態に変化
            mock_assess.return_value = HealthStatus.CRITICAL
            self.daemon._perform_health_check()
        
        # 通知が送信されたことを確認（2回の変化があるはず）
        self.assertGreaterEqual(len(notification_calls), 2)
        
        # 通知の内容確認
        warning_call = next((call for call in notification_calls if "WARNING" in call[0] or call[1] == "warning"), None)
        critical_call = next((call for call in notification_calls if "CRITICAL" in call[0] or call[1] == "error"), None)
        
        self.assertIsNotNone(warning_call, "警告状態への変化通知が見つかりません")
        self.assertIsNotNone(critical_call, "重篤状態への変化通知が見つかりません")
        
        # 停止
        self.daemon.stop()
    
    def test_daemon_error_handling(self):
        """デーモンエラーハンドリングのテスト"""
        # エラーを発生させるモック設定
        self.mock_scheduler.start.side_effect = Exception("スケジューラー開始エラー")
        
        # デーモン開始でエラーが発生
        result = self.daemon.start()
        
        # エラーのため開始に失敗
        self.assertFalse(result)
        self.assertEqual(self.daemon.status, DaemonStatus.ERROR)
        
        # エラーハンドラーが呼ばれたことを確認
        self.mock_error_handler.handle_error.assert_called()
    
    def test_graceful_shutdown(self):
        """優雅なシャットダウンのテスト"""
        # デーモンを開始
        self.daemon.start()
        time.sleep(0.1)
        
        # 進行中の録音をモック
        mock_active_jobs = [Mock(), Mock()]
        self.mock_recording.list_jobs.return_value = mock_active_jobs
        
        # 優雅なシャットダウン
        result = self.daemon.stop(graceful=True)
        
        self.assertTrue(result)
        
        # 録音の停止が呼ばれたことを確認
        self.mock_recording.stop_all_jobs.assert_called_once()
        
        # スケジューラーの停止が呼ばれたことを確認
        self.mock_scheduler.shutdown.assert_called_once()
    
    def test_export_monitoring_data(self):
        """監視データエクスポートのテスト"""
        export_path = f"{self.temp_dir}/monitoring_export.json"
        
        # デーモンを開始
        self.daemon.start()
        time.sleep(0.1)
        
        # 監視データをエクスポート
        result = self.daemon.export_monitoring_data(export_path)
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(export_path))
        
        # エクスポートファイルの内容を確認
        with open(export_path, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
        
        self.assertIn('daemon_info', exported_data)
        self.assertIn('current_status', exported_data)
        self.assertIn('export_timestamp', exported_data)
        
        # 停止
        self.daemon.stop()
    
    @patch('platform.system')
    @patch('subprocess.run')
    def test_macos_notification_system(self, mock_subprocess, mock_platform):
        """macOS通知システムのテスト"""
        # macOSプラットフォームを模擬
        mock_platform.return_value = "Darwin"
        mock_subprocess.return_value = None
        
        # デーモンを開始
        self.daemon.start()
        time.sleep(0.1)
        
        # 通知を送信
        self.daemon._send_notification("テストタイトル", "テストメッセージ")
        
        # osascriptが呼ばれたことを確認
        mock_subprocess.assert_called_with([
            "osascript", "-e", 
            'display notification "テストメッセージ" with title "RecRadiko - テストタイトル"'
        ], check=True, timeout=5)
        
        # 停止
        self.daemon.stop()
    
    @patch('platform.system')
    @patch('subprocess.run')
    def test_notification_fallback_system(self, mock_subprocess, mock_platform):
        """通知システムのフォールバック機能テスト"""
        # macOSプラットフォームを模擬
        mock_platform.return_value = "Darwin"
        # osascriptが失敗する場合を模擬
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'osascript')
        
        # デーモンを開始
        self.daemon.start()
        time.sleep(0.1)
        
        # 通知を送信（エラーが発生しないことを確認）
        try:
            self.daemon._send_notification("テストタイトル", "テストメッセージ")
            # 例外が発生しないことを確認
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"通知送信でエラーが発生: {e}")
        
        # 停止
        self.daemon.stop()
    
    @patch('platform.system')
    def test_notification_non_macos(self, mock_platform):
        """非macOS環境での通知テスト"""
        # 非macOSプラットフォームを模擬
        mock_platform.return_value = "Linux"
        
        # デーモンを開始
        self.daemon.start()
        time.sleep(0.1)
        
        # 通知を送信（エラーが発生しないことを確認）
        try:
            self.daemon._send_notification("テストタイトル", "テストメッセージ")
            # 例外が発生しないことを確認
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"通知送信でエラーが発生: {e}")
        
        # 停止
        self.daemon.stop()
    
    def test_notification_disabled(self):
        """通知無効化のテスト"""
        # 通知を無効化
        self.daemon.notification_enabled = False
        
        # デーモンを開始
        self.daemon.start()
        time.sleep(0.1)
        
        with patch('subprocess.run') as mock_subprocess:
            # 通知を送信
            self.daemon._send_notification("テストタイトル", "テストメッセージ")
            
            # osascriptが呼ばれていないことを確認
            mock_subprocess.assert_not_called()
        
        # 停止
        self.daemon.stop()


if __name__ == '__main__':
    unittest.main()