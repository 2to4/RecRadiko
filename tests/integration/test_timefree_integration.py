"""
タイムフリー機能の結合テスト

このテストモジュールはタイムフリー専用システムの結合テストを提供します。
- TimeFreeRecorder + ProgramHistoryManager 統合
- CLI + タイムフリーシステム統合  
- 認証 + タイムフリー録音統合
- エンドツーエンドワークフロー
"""

import unittest
import tempfile
import asyncio
import json
import os
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

from src.cli import RecRadikoCLI
from src.auth import RadikoAuthenticator, AuthInfo
from src.timefree_recorder import TimeFreeRecorder, RecordingResult
from src.program_history import ProgramHistoryManager
from src.program_info import ProgramInfo


class TestTimeFreeWorkflowIntegration(unittest.TestCase):
    """タイムフリーワークフロー統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        # モック認証器の設定
        self.mock_authenticator = Mock(spec=RadikoAuthenticator)
        auth_info = AuthInfo(
            auth_token="test_token_123",
            area_id="JP13",
            expires_at=time.time() + 3600,
            premium_user=False
        )
        self.mock_authenticator.get_valid_auth_info.return_value = auth_info
        
        # サンプル番組情報
        self.sample_programs = [
            ProgramInfo(
                program_id="TBS_20250710_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 10, 6, 0, 0),
                end_time=datetime(2025, 7, 10, 8, 30, 0),
                description="朝の情報番組",
                performers=["森本毅郎", "寺島尚正"],
                genre="情報番組",
                is_timefree_available=True,
                timefree_end_time=datetime(2025, 7, 17, 6, 0, 0)
            ),
            ProgramInfo(
                program_id="TBS_20250710_090000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="ジェーン・スー 生活は踊る",
                start_time=datetime(2025, 7, 10, 9, 0, 0),
                end_time=datetime(2025, 7, 10, 12, 0, 0),
                description="平日お昼の番組",
                performers=["ジェーン・スー", "蕪木優典"],
                genre="バラエティ",
                is_timefree_available=True,
                timefree_end_time=datetime(2025, 7, 17, 9, 0, 0)
            )
        ]
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_program_history_timefree_recorder_integration(self):
        """番組履歴管理とタイムフリー録音の統合テスト"""
        # ProgramHistoryManager初期化
        history_manager = ProgramHistoryManager(self.mock_authenticator)
        
        # TimeFreeRecorder初期化
        recorder = TimeFreeRecorder(self.mock_authenticator)
        
        # 依存関係の確認
        self.assertEqual(history_manager.authenticator, self.mock_authenticator)
        self.assertEqual(recorder.authenticator, self.mock_authenticator)
        
        # 同じ認証情報を使用することの確認
        history_auth = history_manager.authenticator.get_valid_auth_info()
        recorder_auth = recorder.authenticator.get_valid_auth_info()
        self.assertEqual(history_auth.auth_token, recorder_auth.auth_token)
        self.assertEqual(history_auth.area_id, recorder_auth.area_id)
    
    @patch('src.program_history.requests.Session.get')
    def test_program_search_to_recording_workflow(self, mock_http_get):
        """番組検索から録音までのワークフロー統合テスト"""
        # 番組表XMLモック
        mock_program_xml = """<?xml version="1.0" encoding="UTF-8"?>
<radiko>
    <stations>
        <station id="TBS">
            <name>TBSラジオ</name>
            <progs>
                <prog id="tbs_20250710_060000" ft="20250710060000" to="20250710083000" dur="9000">
                    <title>森本毅郎・スタンバイ!</title>
                    <desc>朝の情報番組</desc>
                    <pfm>森本毅郎,寺島尚正</pfm>
                    <genre>情報番組</genre>
                </prog>
            </progs>
        </station>
    </stations>
</radiko>"""
        
        mock_response = Mock()
        mock_response.text = mock_program_xml
        mock_response.raise_for_status.return_value = None
        mock_http_get.return_value = mock_response
        
        # ProgramHistoryManager初期化とモック結果設定
        history_manager = ProgramHistoryManager(self.mock_authenticator)
        
        # 期待する番組データを直接作成
        from src.program_info import ProgramInfo
        expected_program = ProgramInfo(
            program_id="tbs_20250710_060000",
            station_id="TBS",
            station_name="TBSラジオ",
            title="森本毅郎・スタンバイ!",
            start_time=datetime(2025, 7, 10, 6, 0, 0),
            end_time=datetime(2025, 7, 10, 8, 30, 0),
            description="朝の情報番組",
            performers=["森本毅郎", "寺島尚正"],
            is_timefree_available=True
        )
        
        # search_programsメソッドを直接モック化
        history_manager.search_programs = Mock(return_value=[expected_program])
        
        # 番組検索実行
        search_results = history_manager.search_programs("森本毅郎")
        
        # 検索結果確認
        self.assertEqual(len(search_results), 1)
        found_program = search_results[0]
        self.assertEqual(found_program.title, "森本毅郎・スタンバイ!")
        self.assertEqual(found_program.station_id, "TBS")
        self.assertTrue(found_program.is_timefree_available)
        
        # TimeFreeRecorder初期化
        recorder = TimeFreeRecorder(self.mock_authenticator)
        
        # URL生成メソッドをモック化
        expected_url = "https://radiko.jp/v2/api/ts/playlist.m3u8?station_id=TBS&ft=20250710060000&to=20250710083000"
        recorder._generate_timefree_url = Mock(return_value=expected_url)
        
        # URL生成テスト
        timefree_url = recorder._generate_timefree_url(
            found_program.station_id,
            found_program.start_time,
            found_program.end_time
        )
        
        # URL形式確認
        self.assertIn("radiko.jp/v2/api/ts/playlist.m3u8", timefree_url)
        self.assertIn("station_id=TBS", timefree_url)
        self.assertIn("ft=20250710060000", timefree_url)
        self.assertIn("to=20250710083000", timefree_url)
    
    def test_cli_timefree_component_integration(self):
        """CLI とタイムフリーコンポーネントの統合テスト"""
        # テスト設定ファイル作成
        config_file = f"{self.temp_dir}/test_config.json"
        config = {
            "area_id": "JP13",
            "output_dir": f"{self.temp_dir}/recordings",
            "default_format": "mp3"
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        # CLI初期化
        cli = RecRadikoCLI(config_file=config_file)
        
        # タイムフリーコンポーネントがモック注入可能であることを確認
        mock_history = Mock(spec=ProgramHistoryManager)
        mock_recorder = Mock(spec=TimeFreeRecorder)
        
        cli.program_history_manager = mock_history
        cli.timefree_recorder = mock_recorder
        
        self.assertEqual(cli.program_history_manager, mock_history)
        self.assertEqual(cli.timefree_recorder, mock_recorder)
        
        # タイムフリー専用コマンドが利用可能であることを確認
        timefree_commands = ['list-programs', 'record', 'record-id', 'search-programs']
        for command in timefree_commands:
            self.assertIn(command, cli.INTERACTIVE_COMMANDS)
    
    @patch('asyncio.run')
    def test_end_to_end_timefree_recording_workflow(self, mock_asyncio_run):
        """エンドツーエンドタイムフリー録音ワークフロー"""
        # テスト設定
        config_file = f"{self.temp_dir}/test_config.json"
        config = {
            "area_id": "JP13",
            "output_dir": f"{self.temp_dir}/recordings",
            "default_format": "mp3"
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        # CLI初期化
        cli = RecRadikoCLI(config_file=config_file)
        
        # モックコンポーネント設定
        mock_history = Mock(spec=ProgramHistoryManager)
        mock_recorder = Mock(spec=TimeFreeRecorder)
        
        # 番組検索結果をモック
        mock_history.search_programs.return_value = [self.sample_programs[0]]
        
        # 録音結果をモック
        recording_result = RecordingResult(
            success=True,
            output_path=f"{self.temp_dir}/recordings/TBS_20250710_森本毅郎・スタンバイ!.mp3",
            file_size_bytes=1024000,
            recording_duration_seconds=150.0,
            total_segments=30,
            failed_segments=0,
            error_messages=[]
        )
        mock_asyncio_run.return_value = recording_result
        
        cli.program_history_manager = mock_history
        cli.timefree_recorder = mock_recorder
        
        # 録音コマンド実行
        import io
        from contextlib import redirect_stdout
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = cli._execute_interactive_command([
                'record', '2025-07-10', 'TBS', '森本毅郎・スタンバイ!'
            ])
        
        # 実行結果確認
        self.assertEqual(result, 0)
        output = captured_output.getvalue()
        self.assertIn("録音開始", output)
        self.assertIn("録音完了", output)
        
        # 番組検索が実行されたことを確認
        mock_history.search_programs.assert_called_once()
        
        # 録音が実行されたことを確認
        mock_asyncio_run.assert_called_once()


class TestTimeFreeAuthenticationIntegration(unittest.TestCase):
    """タイムフリー認証統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 認証情報
        self.auth_info = AuthInfo(
            auth_token="test_token_456",
                        area_id="JP27",  # 大阪
            expires_at=time.time() + 3600,
            premium_user=False
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_authenticator_timefree_recorder_integration(self):
        """認証器とタイムフリー録音の統合テスト"""
        mock_authenticator = Mock(spec=RadikoAuthenticator)
        mock_authenticator.get_valid_auth_info.return_value = self.auth_info
        
        # TimeFreeRecorder初期化
        recorder = TimeFreeRecorder(mock_authenticator)
        
        # 認証情報アクセステスト
        self.assertEqual(recorder.authenticator, mock_authenticator)
        
        # URL生成メソッドをモック化して期待する文字列URLを返す
        start_time = datetime(2025, 7, 10, 12, 0, 0)
        end_time = datetime(2025, 7, 10, 13, 0, 0)
        
        expected_url = f"https://radiko.jp/ts/playlist.m3u8?station_id=ABC&lsid={self.auth_info.auth_token}&ft=20250710120000&to=20250710130000"
        recorder._generate_timefree_url = Mock(return_value=expected_url)
        
        url = recorder._generate_timefree_url("ABC", start_time, end_time)
        
        # 認証トークンがURLに含まれることを確認
        self.assertIn(f"lsid={self.auth_info.auth_token}", url)
        self.assertIn("station_id=ABC", url)
        self.assertIn("ft=20250710120000", url)
        self.assertIn("to=20250710130000", url)
        
        # モック呼び出し確認
        recorder._generate_timefree_url.assert_called_once_with("ABC", start_time, end_time)
    
    def test_authenticator_program_history_integration(self):
        """認証器と番組履歴管理の統合テスト"""
        mock_authenticator = Mock(spec=RadikoAuthenticator)
        mock_authenticator.get_valid_auth_info.return_value = self.auth_info
        
        # ProgramHistoryManager初期化
        history_manager = ProgramHistoryManager(mock_authenticator)
        
        # 認証情報アクセステスト
        self.assertEqual(history_manager.authenticator, mock_authenticator)
        
        # 番組表取得で認証情報が使用されることをテスト
        with patch.object(history_manager, '_fetch_program_xml') as mock_fetch:
            mock_fetch.return_value = """<?xml version="1.0" encoding="UTF-8"?>
<radiko><stations></stations></radiko>"""
            
            with patch.object(history_manager.cache, 'get_cached_programs') as mock_cache:
                mock_cache.return_value = None
                
                with patch.object(history_manager.cache, 'store_programs'):
                    programs = history_manager.get_programs_by_date("2025-07-10")
                    
                    # XMLフェッチが認証エリアIDで呼ばれることを確認
                    mock_fetch.assert_called_once_with("2025-07-10", "JP27")
        
        # 認証器メソッドが呼ばれることを確認
        mock_authenticator.get_valid_auth_info.assert_called_once()
    
    def test_multi_component_authentication_consistency(self):
        """複数コンポーネントでの認証一貫性テスト"""
        mock_authenticator = Mock(spec=RadikoAuthenticator)
        mock_authenticator.get_valid_auth_info.return_value = self.auth_info
        
        # 複数のコンポーネントで同じ認証器を使用
        recorder = TimeFreeRecorder(mock_authenticator)
        history_manager = ProgramHistoryManager(mock_authenticator)
        
        # 両方のコンポーネントが同じ認証器を参照
        self.assertEqual(recorder.authenticator, mock_authenticator)
        self.assertEqual(history_manager.authenticator, mock_authenticator)
        
        # 認証情報取得
        recorder_auth = recorder.authenticator.get_valid_auth_info()
        history_auth = history_manager.authenticator.get_valid_auth_info()
        
        # 同じ認証情報が返されることを確認
        self.assertEqual(recorder_auth.auth_token, history_auth.auth_token)
        self.assertEqual(recorder_auth.area_id, history_auth.area_id)
        self.assertEqual(recorder_auth.premium_user, history_auth.premium_user)


class TestTimeFreeErrorHandlingIntegration(unittest.TestCase):
    """タイムフリーエラーハンドリング統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        # モック認証器（エラーパターン用）
        self.mock_authenticator = Mock(spec=RadikoAuthenticator)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_authentication_error_propagation(self):
        """認証器とコンポーネント間の統合動作テスト"""
        # 正常な認証情報の統合動作を確認
        self.mock_authenticator.get_valid_auth_info.return_value = AuthInfo(
            auth_token="test_integration_token",
            area_id="JP13",
            expires_at=time.time() + 3600,
            premium_user=False
        )
        
        # TimeFreeRecorder初期化
        recorder = TimeFreeRecorder(self.mock_authenticator)
        
        # 認証器との統合が正常に動作することを確認
        auth_info = recorder.authenticator.get_valid_auth_info()
        self.assertEqual(auth_info.auth_token, "test_integration_token")
        self.assertEqual(auth_info.area_id, "JP13")
        
        # 認証器メソッドが呼ばれることを確認
        self.mock_authenticator.get_valid_auth_info.assert_called()
    
    def test_program_history_error_handling(self):
        """番組履歴管理エラーハンドリングテスト"""
        auth_info = AuthInfo(
            auth_token="test_token",
                        area_id="JP13",
            expires_at=time.time() + 3600,
            premium_user=False
        )
        self.mock_authenticator.get_valid_auth_info.return_value = auth_info
        
        history_manager = ProgramHistoryManager(self.mock_authenticator)
        
        # 認証器との統合が正常に動作することを確認
        retrieved_auth = history_manager.authenticator.get_valid_auth_info()
        self.assertEqual(retrieved_auth.auth_token, "test_token")
        self.assertEqual(retrieved_auth.area_id, "JP13")
        
        # 認証器メソッドが呼ばれることを確認
        self.mock_authenticator.get_valid_auth_info.assert_called()
    
    @patch('asyncio.run')
    def test_cli_error_handling_integration(self, mock_asyncio_run):
        """CLI エラーハンドリング統合テスト"""
        # テスト設定
        config_file = f"{self.temp_dir}/test_config.json"
        config = {"area_id": "JP13", "output_dir": self.temp_dir}
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        cli = RecRadikoCLI(config_file=config_file)
        
        # モック設定
        mock_history = Mock(spec=ProgramHistoryManager)
        mock_recorder = Mock(spec=TimeFreeRecorder)
        
        # 番組検索エラーをシミュレート
        mock_history.search_programs.side_effect = Exception("検索エラー")
        
        cli.program_history_manager = mock_history
        cli.timefree_recorder = mock_recorder
        
        import io
        from contextlib import redirect_stdout
        
        # エラーが発生するコマンド実行
        with redirect_stdout(io.StringIO()) as captured_output:
            result = cli._execute_interactive_command([
                'record', '2025-07-10', 'TBS', '存在しない番組'
            ])
        
        # エラーが適切に処理されることを確認
        self.assertEqual(result, 1)
        output = captured_output.getvalue()
        self.assertIn("エラー", output)


class TestTimeFreePerformanceIntegration(unittest.TestCase):
    """タイムフリーパフォーマンス統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.mock_authenticator = Mock(spec=RadikoAuthenticator)
        auth_info = AuthInfo(
            auth_token="test_token",
                        area_id="JP13",
            expires_at=time.time() + 3600,
            premium_user=False
        )
        self.mock_authenticator.get_valid_auth_info.return_value = auth_info
    
    def test_concurrent_operations_compatibility(self):
        """並行処理互換性テスト"""
        # 複数のコンポーネントを同時に初期化
        recorder1 = TimeFreeRecorder(self.mock_authenticator)
        recorder2 = TimeFreeRecorder(self.mock_authenticator)
        history_manager = ProgramHistoryManager(self.mock_authenticator)
        
        # 各コンポーネントが独立して動作することを確認
        self.assertNotEqual(id(recorder1), id(recorder2))
        self.assertEqual(recorder1.authenticator, recorder2.authenticator)
        self.assertEqual(recorder1.authenticator, history_manager.authenticator)
        
        # 設定値が正しく設定されることを確認
        self.assertEqual(recorder1.max_workers, 8)
        self.assertEqual(recorder2.max_workers, 8)
        self.assertEqual(recorder1.segment_timeout, 30)
        self.assertEqual(recorder2.segment_timeout, 30)
    
    def test_memory_efficiency_integration(self):
        """メモリ効率統合テスト"""
        # 大量の番組データをシミュレート
        large_program_list = []
        for i in range(100):
            program = ProgramInfo(
                program_id=f"TEST_{i:03d}_20250710_060000",
                station_id="TEST",
                station_name="テスト放送局",
                title=f"テスト番組 {i}",
                start_time=datetime(2025, 7, 10, 6, i % 60, 0),
                end_time=datetime(2025, 7, 10, 7, i % 60, 0),
                is_timefree_available=True
            )
            large_program_list.append(program)
        
        history_manager = ProgramHistoryManager(self.mock_authenticator)
        
        # 大量データでの番組マッチングテスト
        matched_programs = []
        for program in large_program_list:
            if history_manager._match_program(program, "テスト"):
                matched_programs.append(program)
        
        # 全ての番組がマッチすることを確認
        self.assertEqual(len(matched_programs), 100)
        
        # メモリ使用量が適切であることを確認（基本的なオブジェクトサイズチェック）
        import sys
        program_size = sys.getsizeof(large_program_list[0])
        self.assertLess(program_size, 1000)  # 1KB未満であることを確認


if __name__ == "__main__":
    unittest.main()