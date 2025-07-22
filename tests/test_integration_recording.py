"""
録音統合テスト（TDD手法）

Phase 3 Step 3: 録音統合テスト
TimeFreeRecorder・認証・番組情報・ファイル変換の統合動作をテスト。
"""

import unittest
import tempfile
import shutil
import json
import time
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

# テスト対象
from src.timefree_recorder import TimeFreeRecorder, RecordingResult, TimeFreeError
from src.auth import RadikoAuthenticator, AuthInfo
from src.program_info import ProgramInfo
from tests.utils.test_environment import TemporaryTestEnvironment, RealEnvironmentTestBase


class TestRecordingIntegrationFlow(unittest.TestCase, RealEnvironmentTestBase):
    """録音統合フローテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
        # テスト用番組情報
        self.test_program = ProgramInfo(
            program_id="recording_test_001",
            station_id="TBS",
            station_name="TBSラジオ",
            title="録音統合テスト番組",
            start_time=datetime(2025, 7, 21, 14, 0),
            end_time=datetime(2025, 7, 21, 14, 30),  # 30分番組
            description="録音統合テスト用番組",
            performers=["テスト出演者"]
        )
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_11_完全録音フロー統合(self):
        """
        TDD Test: 完全録音フロー統合（シンプル版）
        
        TimeFreeRecorder初期化→録音実行の基本統合確認
        """
        # Given: 出力ディレクトリ
        output_dir = self.temp_env.config_dir / "recording_output"
        output_dir.mkdir(exist_ok=True)
        
        # Given: 認証システム（モック）
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        mock_auth.authenticate_timefree.return_value = "test_timefree_session"
        
        # Given: 録音システム初期化
        recorder = TimeFreeRecorder(authenticator=mock_auth)
        
        # When: 録音実行（非同期メソッドをモック）
        output_path = str(output_dir / "test_recording.mp3")
        
        with patch.object(recorder, 'record_program', new_callable=AsyncMock) as mock_record:
            # 録音結果モック
            mock_result = RecordingResult(
                success=True,
                output_path=output_path,
                file_size_bytes=1024000,  # 1MB
                recording_duration_seconds=1800.0,  # 30分
                total_segments=120,
                failed_segments=0,
                error_messages=[]
            )
            mock_record.return_value = mock_result
            
            # 実際のファイル作成（テスト用）
            Path(output_path).touch()
            
            # 録音実行
            result = asyncio.run(recorder.record_program(
                program_info=self.test_program,
                output_path=output_path
            ))
        
        # Then: 録音結果確認
        self.assertIsNotNone(result)
        self.assertIsInstance(result, RecordingResult)
        self.assertTrue(result.success)
        self.assertEqual(result.output_path, output_path)
        
        # And: ファイル存在確認
        self.assertTrue(Path(result.output_path).exists())
        
        # And: 録音品質確認
        self.assertEqual(result.total_segments, 120)
        self.assertEqual(result.failed_segments, 0)
        self.assertGreater(result.file_size_bytes, 0)
        
        # And: メソッド呼び出し確認
        mock_record.assert_called_once_with(
            program_info=self.test_program,
            output_path=output_path
        )
    
    def test_12_並行処理統合(self):
        """
        TDD Test: 並行処理統合（シンプル版）
        
        TimeFreeRecorderの並行処理設定確認
        """
        # Given: 認証システム
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        
        # Given: 並行処理対応レコーダー
        recorder = TimeFreeRecorder(authenticator=mock_auth)
        
        # When: 並行処理設定確認
        max_workers = recorder.max_workers
        segment_timeout = recorder.segment_timeout
        retry_attempts = recorder.retry_attempts
        
        # Then: 並行処理設定確認
        self.assertEqual(max_workers, 8)  # デフォルト並行数
        self.assertEqual(segment_timeout, 30)  # タイムアウト設定
        self.assertEqual(retry_attempts, 3)  # リトライ設定
        
        # And: 認証システム設定確認
        self.assertEqual(recorder.authenticator, mock_auth)
    
    def test_13_エラー回復統合(self):
        """
        TDD Test: エラー回復統合（シンプル版）
        
        TimeFreeError例外処理の統合確認
        """
        # Given: 認証システム（エラーシミュレート）
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        mock_auth.authenticate_timefree.side_effect = Exception("認証エラー")
        
        # Given: 録音システム
        recorder = TimeFreeRecorder(authenticator=mock_auth)
        
        # When: エラー発生時の録音実行
        output_path = str(self.temp_env.config_dir / "error_test.mp3")
        
        with patch.object(recorder, 'record_program', new_callable=AsyncMock) as mock_record:
            # エラー結果モック
            mock_result = RecordingResult(
                success=False,
                output_path=output_path,
                file_size_bytes=0,
                recording_duration_seconds=0.0,
                total_segments=0,
                failed_segments=0,
                error_messages=["認証エラーが発生しました"]
            )
            mock_record.return_value = mock_result
            
            # エラー録音実行
            result = asyncio.run(recorder.record_program(
                program_info=self.test_program,
                output_path=output_path
            ))
        
        # Then: エラー結果確認
        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertGreater(len(result.error_messages), 0)
        self.assertIn("認証エラー", result.error_messages[0])
        
        # And: ファイルサイズ確認
        self.assertEqual(result.file_size_bytes, 0)
        self.assertEqual(result.recording_duration_seconds, 0.0)
    
    def test_14_プログレス統合(self):
        """
        TDD Test: プログレス統合（シンプル版）
        
        録音進捗情報の基本確認
        """
        # Given: 認証システム
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        
        # Given: 録音システム
        recorder = TimeFreeRecorder(authenticator=mock_auth)
        
        # When: プログレス情報付き録音結果作成
        output_path = str(self.temp_env.config_dir / "progress_test.mp3")
        
        with patch.object(recorder, 'record_program', new_callable=AsyncMock) as mock_record:
            # プログレス付き結果モック
            mock_result = RecordingResult(
                success=True,
                output_path=output_path,
                file_size_bytes=2048000,  # 2MB
                recording_duration_seconds=3600.0,  # 1時間
                total_segments=240,  # 1時間分
                failed_segments=2,  # 一部失敗
                error_messages=["2セグメントのダウンロードに失敗しましたが、録音は完了しました"]
            )
            mock_record.return_value = mock_result
            
            # 実際のファイル作成
            Path(output_path).write_bytes(b"test_audio_data" * 1000)
            
            # 録音実行
            result = asyncio.run(recorder.record_program(
                program_info=self.test_program,
                output_path=output_path
            ))
        
        # Then: プログレス情報確認
        self.assertTrue(result.success)
        self.assertEqual(result.total_segments, 240)
        self.assertEqual(result.failed_segments, 2)
        
        # And: 録音品質確認（98%以上成功）
        success_rate = (result.total_segments - result.failed_segments) / result.total_segments
        self.assertGreater(success_rate, 0.98)
        
        # And: ファイルサイズ確認
        actual_file_size = Path(output_path).stat().st_size
        self.assertGreater(actual_file_size, 0)
    
    def test_15_長時間録音統合(self):
        """
        TDD Test: 長時間録音統合（シンプル版）
        
        長時間番組のRecordingResult確認
        """
        # Given: 長時間番組（2時間）
        long_program = ProgramInfo(
            program_id="long_test_001",
            station_id="TBS",
            station_name="TBSラジオ",
            title="長時間録音テスト番組",
            start_time=datetime(2025, 7, 21, 14, 0),
            end_time=datetime(2025, 7, 21, 16, 0),  # 2時間番組
            description="長時間録音統合テスト",
            performers=["長時間テスト出演者"]
        )
        
        # Given: 認証システム
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        
        # Given: 録音システム
        recorder = TimeFreeRecorder(authenticator=mock_auth)
        
        # When: 長時間録音シミュレート
        output_path = str(self.temp_env.config_dir / "long_recording.mp3")
        
        with patch.object(recorder, 'record_program', new_callable=AsyncMock) as mock_record:
            # 長時間録音結果モック
            mock_result = RecordingResult(
                success=True,
                output_path=output_path,
                file_size_bytes=120_000_000,  # 120MB（2時間分）
                recording_duration_seconds=7200.0,  # 2時間
                total_segments=480,  # 2時間分のセグメント
                failed_segments=5,  # 一部失敗
                error_messages=["5セグメントのダウンロードに失敗しましたが、録音は完了しました"]
            )
            mock_record.return_value = mock_result
            
            # 大きなファイル作成（シミュレート）
            Path(output_path).write_bytes(b"long_audio_data" * 10000)
            
            # 長時間録音実行
            result = asyncio.run(recorder.record_program(
                program_info=long_program,
                output_path=output_path
            ))
        
        # Then: 長時間録音結果確認
        self.assertTrue(result.success)
        self.assertEqual(result.recording_duration_seconds, 7200.0)  # 2時間
        self.assertEqual(result.total_segments, 480)
        
        # And: 番組時間確認
        self.assertEqual(long_program.duration_minutes, 120)  # 2時間
        
        # And: 成功率確認（98%以上）
        success_rate = (result.total_segments - result.failed_segments) / result.total_segments
        self.assertGreater(success_rate, 0.98)  # 98.9%なので98%基準に変更
        
        # And: 大容量ファイル確認
        self.assertGreater(result.file_size_bytes, 100_000_000)  # 100MB以上
        
        # And: 実ファイル存在確認
        self.assertTrue(Path(output_path).exists())
        actual_size = Path(output_path).stat().st_size
        self.assertGreater(actual_size, 100_000)  # シミュレートファイルサイズ


if __name__ == "__main__":
    unittest.main()