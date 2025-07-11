"""
エラーハンドリングモジュールの単体テスト
"""

import unittest
import tempfile
import json
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.error_handler import (
    ErrorHandler, ErrorRecord, ErrorSeverity, ErrorCategory,
    RecRadikoError, AuthenticationError, NetworkError, StreamingError,
    RecordingError, FileSystemError, SchedulingError, ConfigurationError, SystemError,
    handle_error, setup_error_handler, get_error_handler
)


class TestErrorSeverity(unittest.TestCase):
    """ErrorSeverity Enum のテスト"""
    
    def test_error_severity_values(self):
        """ErrorSeverity の値テスト"""
        self.assertEqual(ErrorSeverity.LOW.value, "low")
        self.assertEqual(ErrorSeverity.MEDIUM.value, "medium")
        self.assertEqual(ErrorSeverity.HIGH.value, "high")
        self.assertEqual(ErrorSeverity.CRITICAL.value, "critical")


class TestErrorCategory(unittest.TestCase):
    """ErrorCategory Enum のテスト"""
    
    def test_error_category_values(self):
        """ErrorCategory の値テスト"""
        self.assertEqual(ErrorCategory.AUTHENTICATION.value, "authentication")
        self.assertEqual(ErrorCategory.NETWORK.value, "network")
        self.assertEqual(ErrorCategory.STREAMING.value, "streaming")
        self.assertEqual(ErrorCategory.RECORDING.value, "recording")
        self.assertEqual(ErrorCategory.FILE_SYSTEM.value, "file_system")
        self.assertEqual(ErrorCategory.SCHEDULING.value, "scheduling")
        self.assertEqual(ErrorCategory.CONFIGURATION.value, "configuration")
        self.assertEqual(ErrorCategory.SYSTEM.value, "system")
        self.assertEqual(ErrorCategory.UNKNOWN.value, "unknown")


class TestCustomExceptions(unittest.TestCase):
    """カスタム例外クラスのテスト"""
    
    def test_recradiko_error(self):
        """RecRadikoError の基本テスト"""
        error = RecRadikoError("Test error message")
        
        self.assertEqual(str(error), "Test error message")
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(error.category, ErrorCategory.UNKNOWN)
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
        self.assertEqual(error.context, {})
    
    def test_recradiko_error_with_context(self):
        """RecRadikoError のコンテキスト付きテスト"""
        context = {"station_id": "TBS", "timestamp": "2024-01-01T20:00:00"}
        error = RecRadikoError(
            "Test error with context",
            category=ErrorCategory.STREAMING,
            severity=ErrorSeverity.HIGH,
            context=context
        )
        
        self.assertEqual(error.category, ErrorCategory.STREAMING)
        self.assertEqual(error.severity, ErrorSeverity.HIGH)
        self.assertEqual(error.context, context)
    
    def test_authentication_error(self):
        """AuthenticationError のテスト"""
        error = AuthenticationError("Login failed")
        
        self.assertEqual(str(error), "Login failed")
        self.assertEqual(error.category, ErrorCategory.AUTHENTICATION)
        self.assertEqual(error.severity, ErrorSeverity.HIGH)
    
    def test_network_error(self):
        """NetworkError のテスト"""
        error = NetworkError("Connection timeout")
        
        self.assertEqual(str(error), "Connection timeout")
        self.assertEqual(error.category, ErrorCategory.NETWORK)
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
    
    def test_streaming_error(self):
        """StreamingError のテスト"""
        error = StreamingError("Stream unavailable")
        
        self.assertEqual(str(error), "Stream unavailable")
        self.assertEqual(error.category, ErrorCategory.STREAMING)
        self.assertEqual(error.severity, ErrorSeverity.HIGH)
    
    def test_recording_error(self):
        """RecordingError のテスト"""
        error = RecordingError("Recording failed")
        
        self.assertEqual(str(error), "Recording failed")
        self.assertEqual(error.category, ErrorCategory.RECORDING)
        self.assertEqual(error.severity, ErrorSeverity.HIGH)
    
    def test_file_system_error(self):
        """FileSystemError のテスト"""
        error = FileSystemError("Disk full")
        
        self.assertEqual(str(error), "Disk full")
        self.assertEqual(error.category, ErrorCategory.FILE_SYSTEM)
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
    
    def test_scheduling_error(self):
        """SchedulingError のテスト"""
        error = SchedulingError("Schedule conflict")
        
        self.assertEqual(str(error), "Schedule conflict")
        self.assertEqual(error.category, ErrorCategory.SCHEDULING)
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
    
    def test_configuration_error(self):
        """ConfigurationError のテスト"""
        error = ConfigurationError("Invalid config")
        
        self.assertEqual(str(error), "Invalid config")
        self.assertEqual(error.category, ErrorCategory.CONFIGURATION)
        self.assertEqual(error.severity, ErrorSeverity.HIGH)
    
    def test_system_error(self):
        """SystemError のテスト"""
        error = SystemError("System failure")
        
        self.assertEqual(str(error), "System failure")
        self.assertEqual(error.category, ErrorCategory.SYSTEM)
        self.assertEqual(error.severity, ErrorSeverity.CRITICAL)


class TestErrorRecord(unittest.TestCase):
    """ErrorRecord クラスのテスト"""
    
    def test_error_record_creation(self):
        """ErrorRecord の作成テスト"""
        timestamp = datetime.now()
        
        record = ErrorRecord(
            id="error_123",
            timestamp=timestamp,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.NETWORK,
            error_type="ConnectionError",
            message="Network connection failed",
            details="Connection timeout after 30 seconds",
            context={"url": "http://example.com"},
            stack_trace="Traceback...",
            resolved=False,
            resolution_notes="",
            occurrence_count=1
        )
        
        self.assertEqual(record.id, "error_123")
        self.assertEqual(record.severity, ErrorSeverity.HIGH)
        self.assertEqual(record.category, ErrorCategory.NETWORK)
        self.assertEqual(record.error_type, "ConnectionError")
        self.assertEqual(record.message, "Network connection failed")
        self.assertEqual(record.occurrence_count, 1)
        self.assertFalse(record.resolved)
    
    def test_error_record_to_dict(self):
        """ErrorRecord の辞書変換テスト"""
        timestamp = datetime.now()
        
        record = ErrorRecord(
            id="error_123",
            timestamp=timestamp,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.NETWORK,
            error_type="ConnectionError",
            message="Network connection failed"
        )
        
        record_dict = record.to_dict()
        
        self.assertEqual(record_dict['id'], "error_123")
        self.assertEqual(record_dict['severity'], "high")
        self.assertEqual(record_dict['category'], "network")
        self.assertEqual(record_dict['error_type'], "ConnectionError")
        self.assertIn('timestamp', record_dict)
        self.assertIn('first_occurred', record_dict)
        self.assertIn('last_occurred', record_dict)
    
    def test_error_record_from_dict(self):
        """ErrorRecord の辞書からの復元テスト"""
        timestamp = datetime.now()
        
        record_dict = {
            'id': "error_123",
            'timestamp': timestamp.isoformat(),
            'severity': "high",
            'category': "network",
            'error_type': "ConnectionError",
            'message': "Network connection failed",
            'details': "",
            'context': {},
            'stack_trace': "",
            'resolved': False,
            'resolution_notes': "",
            'occurrence_count': 1,
            'first_occurred': timestamp.isoformat(),
            'last_occurred': timestamp.isoformat()
        }
        
        record = ErrorRecord.from_dict(record_dict)
        
        self.assertEqual(record.id, "error_123")
        self.assertEqual(record.severity, ErrorSeverity.HIGH)
        self.assertEqual(record.category, ErrorCategory.NETWORK)
        self.assertEqual(record.error_type, "ConnectionError")


class TestErrorHandler(unittest.TestCase):
    """ErrorHandler クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = f"{self.temp_dir}/test_error.log"
        self.error_db_file = f"{self.temp_dir}/test_errors.json"
        
        self.error_handler = ErrorHandler(
            log_file=self.log_file,
            error_db_file=self.error_db_file,
            max_error_records=100,
            notification_enabled=False
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.error_handler.shutdown()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_error_handler_creation(self):
        """ErrorHandler の作成テスト"""
        self.assertIsInstance(self.error_handler, ErrorHandler)
        self.assertEqual(len(self.error_handler.error_records), 0)
        self.assertFalse(self.error_handler.notification_enabled)
    
    def test_handle_custom_error(self):
        """カスタム例外処理のテスト"""
        error = NetworkError("Connection failed", context={"url": "http://example.com"})
        
        error_id = self.error_handler.handle_error(error)
        
        self.assertIsInstance(error_id, str)
        self.assertIn(error_id, self.error_handler.error_records)
        
        record = self.error_handler.error_records[error_id]
        self.assertEqual(record.category, ErrorCategory.NETWORK)
        self.assertEqual(record.severity, ErrorSeverity.MEDIUM)
        self.assertEqual(record.error_type, "NetworkError")
        self.assertEqual(record.message, "Connection failed")
        self.assertEqual(record.context["url"], "http://example.com")
    
    def test_handle_standard_exception(self):
        """標準例外処理のテスト"""
        error = ValueError("Invalid value")
        
        error_id = self.error_handler.handle_error(error)
        
        self.assertIsInstance(error_id, str)
        self.assertIn(error_id, self.error_handler.error_records)
        
        record = self.error_handler.error_records[error_id]
        self.assertEqual(record.error_type, "ValueError")
        self.assertEqual(record.message, "Invalid value")
        # 標準例外はカテゴリが推定される
        self.assertIsInstance(record.category, ErrorCategory)
    
    def test_duplicate_error_handling(self):
        """重複エラー処理のテスト"""
        error1 = NetworkError("Connection failed")
        error2 = NetworkError("Connection failed")
        
        error_id1 = self.error_handler.handle_error(error1)
        error_id2 = self.error_handler.handle_error(error2)
        
        # 同じエラーは同じIDを持つべき
        self.assertEqual(error_id1, error_id2)
        
        # 発生回数がインクリメントされるべき
        record = self.error_handler.error_records[error_id1]
        self.assertEqual(record.occurrence_count, 2)
    
    def test_categorize_error(self):
        """エラーカテゴリ推定のテスト"""
        # ネットワーク関連
        network_error = Exception("connection timeout")
        category = self.error_handler._categorize_error(network_error)
        self.assertEqual(category, ErrorCategory.NETWORK)
        
        # ファイルシステム関連
        file_error = Exception("file not found")
        category = self.error_handler._categorize_error(file_error)
        self.assertEqual(category, ErrorCategory.FILE_SYSTEM)
        
        # 認証関連
        auth_error = Exception("authentication failed")
        category = self.error_handler._categorize_error(auth_error)
        self.assertEqual(category, ErrorCategory.AUTHENTICATION)
        
        # 不明なエラー
        unknown_error = Exception("some unknown error")
        category = self.error_handler._categorize_error(unknown_error)
        self.assertEqual(category, ErrorCategory.UNKNOWN)
    
    def test_assess_severity(self):
        """エラー重要度評価のテスト"""
        # 致命的エラー
        critical_error = Exception("critical system failure")
        severity = self.error_handler._assess_severity(critical_error)
        self.assertEqual(severity, ErrorSeverity.CRITICAL)
        
        # 高重要度エラー
        high_error = Exception("operation failed")
        severity = self.error_handler._assess_severity(high_error)
        self.assertEqual(severity, ErrorSeverity.HIGH)
        
        # 警告レベル
        warning_error = Exception("deprecated function warning")
        severity = self.error_handler._assess_severity(warning_error)
        self.assertEqual(severity, ErrorSeverity.LOW)
        
        # デフォルト
        normal_error = Exception("some error")
        severity = self.error_handler._assess_severity(normal_error)
        self.assertEqual(severity, ErrorSeverity.MEDIUM)
    
    def test_get_error_record(self):
        """エラー記録取得のテスト"""
        error = NetworkError("Test error")
        error_id = self.error_handler.handle_error(error)
        
        # 存在するエラー記録
        record = self.error_handler.get_error_record(error_id)
        self.assertIsNotNone(record)
        self.assertEqual(record.id, error_id)
        
        # 存在しないエラー記録
        nonexistent = self.error_handler.get_error_record("nonexistent_id")
        self.assertIsNone(nonexistent)
    
    def test_list_errors(self):
        """エラー一覧取得のテスト"""
        # 複数のエラーを生成（自動復旧無効化）
        network_error = NetworkError("Network error")
        auth_error = AuthenticationError("Auth error")
        config_error = ConfigurationError("Config error")
        
        self.error_handler.handle_error(network_error, auto_recovery=False)
        self.error_handler.handle_error(auth_error, auto_recovery=False)
        self.error_handler.handle_error(config_error, auto_recovery=False)
        
        # 全エラー取得
        all_errors = self.error_handler.list_errors()
        self.assertEqual(len(all_errors), 3)
        
        # カテゴリでフィルター
        network_errors = self.error_handler.list_errors(category=ErrorCategory.NETWORK)
        self.assertEqual(len(network_errors), 1)
        self.assertEqual(network_errors[0].category, ErrorCategory.NETWORK)
        
        # 重要度でフィルター
        high_errors = self.error_handler.list_errors(severity=ErrorSeverity.HIGH)
        self.assertEqual(len(high_errors), 2)  # auth_error と config_error
        
        # 解決済みでフィルター（解決済みがないのでゼロ）
        resolved_errors = self.error_handler.list_errors(resolved_only=True)
        self.assertEqual(len(resolved_errors), 0)
    
    def test_mark_resolved(self):
        """エラー解決マークのテスト"""
        error = NetworkError("Test error")
        error_id = self.error_handler.handle_error(error)
        
        # 解決マーク
        result = self.error_handler.mark_resolved(error_id, "Fixed by reconnection")
        self.assertTrue(result)
        
        # 解決済みになっていることを確認
        record = self.error_handler.get_error_record(error_id)
        self.assertTrue(record.resolved)
        self.assertEqual(record.resolution_notes, "Fixed by reconnection")
        
        # 存在しないエラーIDの解決マーク
        result_nonexistent = self.error_handler.mark_resolved("nonexistent", "notes")
        self.assertFalse(result_nonexistent)
    
    def test_error_statistics(self):
        """エラー統計のテスト"""
        # 複数のエラーを生成（自動復旧無効化）
        errors = [
            NetworkError("Network error 1"),
            NetworkError("Network error 2"),
            AuthenticationError("Auth error"),
            ConfigurationError("Config error")
        ]
        
        for error in errors:
            self.error_handler.handle_error(error, auto_recovery=False)
        
        # 1つのエラーを手動で解決済みにマーク
        network_error_id = list(self.error_handler.error_records.keys())[0]
        self.error_handler.mark_resolved(network_error_id)
        
        stats = self.error_handler.get_error_statistics()
        
        self.assertEqual(stats['total_errors'], 4)
        self.assertEqual(stats['resolved_errors'], 1)
        self.assertEqual(stats['unresolved_errors'], 3)
        
        # カテゴリ別統計
        self.assertEqual(stats['category_breakdown']['network'], 2)
        self.assertEqual(stats['category_breakdown']['authentication'], 1)
        self.assertEqual(stats['category_breakdown']['configuration'], 1)
        
        # 重要度別統計
        self.assertEqual(stats['severity_breakdown']['medium'], 2)  # Network errors
        self.assertEqual(stats['severity_breakdown']['high'], 2)    # Auth and Config errors
    
    def test_notification_callback(self):
        """通知コールバックのテスト"""
        # 通知を有効にした新しいエラーハンドラーを作成
        notification_handler = ErrorHandler(
            log_file=f"{self.temp_dir}/test_notification.log",
            error_db_file=f"{self.temp_dir}/test_notification.json",
            notification_enabled=True
        )
        
        callback_called = []
        
        def test_callback(record):
            callback_called.append(record)
        
        notification_handler.add_notification_callback(test_callback)
        
        # 高重要度エラーで通知が呼ばれることをテスト（自動復旧無効化）
        error = AuthenticationError("High severity error")
        error_id = notification_handler.handle_error(error, auto_recovery=False)
        
        # コールバックが呼ばれたことを確認
        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0].id, error_id)
        
        # クリーンアップ
        notification_handler.shutdown()
        
        # コールバック削除
        self.error_handler.remove_notification_callback(test_callback)
        
        # 別のエラーでコールバックが呼ばれないことを確認
        another_error = AuthenticationError("Another error")
        self.error_handler.handle_error(another_error)
        self.assertEqual(len(callback_called), 1)  # まだ1つだけ
    
    def test_recovery_handler(self):
        """復旧ハンドラーのテスト"""
        recovery_called = []
        
        def network_recovery_handler(error):
            recovery_called.append(error)
            return True  # 復旧成功
        
        # 復旧ハンドラーを登録
        self.error_handler.register_recovery_handler(NetworkError, network_recovery_handler)
        
        # ネットワークエラーを発生させる
        error = NetworkError("Connection failed")
        error_id = self.error_handler.handle_error(error)
        
        # 復旧ハンドラーが呼ばれたことを確認
        self.assertEqual(len(recovery_called), 1)
        self.assertEqual(recovery_called[0], error)
        
        # エラーが解決済みになっていることを確認
        record = self.error_handler.get_error_record(error_id)
        self.assertTrue(record.resolved)
        self.assertEqual(record.resolution_notes, "自動復旧成功")
    
    def test_save_and_load_error_records(self):
        """エラー記録保存・読み込みのテスト"""
        # エラーを生成
        error = NetworkError("Test error for save/load")
        error_id = self.error_handler.handle_error(error)
        
        # 保存
        self.error_handler._save_error_records()
        
        # 新しいエラーハンドラーで読み込み
        new_handler = ErrorHandler(
            log_file=f"{self.temp_dir}/new_error.log",
            error_db_file=self.error_db_file,
            notification_enabled=False
        )
        
        # エラー記録が復元されることを確認
        self.assertIn(error_id, new_handler.error_records)
        restored_record = new_handler.get_error_record(error_id)
        self.assertEqual(restored_record.message, "Test error for save/load")
        
        new_handler.shutdown()
    
    def test_cleanup_old_errors(self):
        """古いエラー削除のテスト"""
        # 古いエラーを作成
        error = NetworkError("Old error")
        error_id = self.error_handler.handle_error(error)
        
        # エラーを解決済みにして、古い日付に設定
        record = self.error_handler.error_records[error_id]
        record.resolved = True
        record.last_occurred = datetime.now() - timedelta(days=60)
        
        # クリーンアップ実行（30日より古いものを削除）
        self.error_handler.cleanup_old_errors(30)
        
        # 古いエラーが削除されることを確認
        self.assertNotIn(error_id, self.error_handler.error_records)
    
    def test_export_errors_json(self):
        """エラー記録JSON エクスポートのテスト"""
        error = NetworkError("Test error for export")
        self.error_handler.handle_error(error)
        
        export_path = f"{self.temp_dir}/exported_errors.json"
        self.error_handler.export_errors(export_path, "json")
        
        # エクスポートされたファイルを確認
        import os
        self.assertTrue(os.path.exists(export_path))
        
        with open(export_path, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
        
        self.assertEqual(len(exported_data), 1)
        self.assertEqual(exported_data[0]['message'], "Test error for export")


class TestGlobalFunctions(unittest.TestCase):
    """グローバル関数のテスト"""
    
    def test_setup_error_handler(self):
        """setup_error_handler のテスト"""
        handler = setup_error_handler(notification_enabled=False)
        
        self.assertIsInstance(handler, ErrorHandler)
        self.assertFalse(handler.notification_enabled)
        
        # グローバルハンドラーが設定されることを確認
        global_handler = get_error_handler()
        self.assertEqual(handler, global_handler)
        
        handler.shutdown()
    
    def test_handle_error_global(self):
        """handle_error グローバル関数のテスト"""
        setup_error_handler(notification_enabled=False)
        
        error = NetworkError("Global error test")
        context = {"test": True}
        
        error_id = handle_error(error, context)
        
        self.assertIsInstance(error_id, str)
        
        # グローバルハンドラーでエラーが処理されることを確認
        global_handler = get_error_handler()
        record = global_handler.get_error_record(error_id)
        self.assertIsNotNone(record)
        self.assertEqual(record.message, "Global error test")
        self.assertEqual(record.context["test"], True)
        
        global_handler.shutdown()


if __name__ == '__main__':
    unittest.main()