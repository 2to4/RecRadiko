"""
CLIモジュールの単体テスト（タイムフリー専用版）
2025年7月13日作成: タイムフリー専用CLI対応・ライブ録音機能削除
"""

import unittest
import tempfile
import sys
import io
import json
import argparse
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from src.cli import RecRadikoCLI
from src.auth import AuthInfo
from src.program_info import Station, ProgramInfo
from src.timefree_recorder import TimeFreeRecorder, RecordingResult
from src.program_history import ProgramHistoryManager


class TestTimeFreeRecRadikoCLI(unittest.TestCase):
    """RecRadikoCLI クラスのテスト（タイムフリー専用版）"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        # モックオブジェクトの作成
        self.mock_auth = Mock()
        self.mock_program_info = Mock()
        self.mock_file_manager = Mock()
        self.mock_error_handler = Mock()
        
        # タイムフリー専用モック
        self.mock_timefree_recorder = Mock(spec=TimeFreeRecorder)
        self.mock_program_history = Mock(spec=ProgramHistoryManager)
        
        # テスト用設定ファイルを作成（タイムフリー専用）
        test_config = {
            "area_id": "JP13",
            "premium_username": "",
            "premium_password": "",
            "output_dir": f"{self.temp_dir}/recordings",
            "default_format": "mp3",
            "notification_enabled": True,
            "log_level": "INFO",
            "log_file": f"{self.temp_dir}/test.log"
        }
        
        config_file = f"{self.temp_dir}/test_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f)
        
        # CLIインスタンスの作成（依存性注入）
        self.cli = RecRadikoCLI(
            config_file=config_file,
            auth_manager=self.mock_auth,
            program_info_manager=self.mock_program_info,
            file_manager=self.mock_file_manager,
            error_handler=self.mock_error_handler
        )
        
        # タイムフリー専用コンポーネントを手動注入
        self.cli.timefree_recorder = self.mock_timefree_recorder
        self.cli.program_history_manager = self.mock_program_history
        
        # サンプル番組情報
        self.sample_program_info = ProgramInfo(
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
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cli_creation(self):
        """RecRadikoCLI の作成テスト"""
        self.assertIsInstance(self.cli, RecRadikoCLI)
        self.assertEqual(self.cli.auth_manager, self.mock_auth)
        self.assertEqual(self.cli.program_info_manager, self.mock_program_info)
        self.assertEqual(self.cli.file_manager, self.mock_file_manager)
        self.assertEqual(self.cli.error_handler, self.mock_error_handler)
        
        # タイムフリー専用コンポーネント確認
        self.assertEqual(self.cli.timefree_recorder, self.mock_timefree_recorder)
        self.assertEqual(self.cli.program_history_manager, self.mock_program_history)
    
    def test_timefree_interactive_commands(self):
        """タイムフリー専用対話型コマンド確認"""
        expected_commands = [
            'list-programs', 'record', 'record-id', 'search-programs',
            'list-stations', 'show-region', 'list-prefectures', 
            'status', 'help', 'exit', 'quit'
        ]
        
        for command in expected_commands:
            self.assertIn(command, self.cli.INTERACTIVE_COMMANDS)
        
        # 削除されたコマンドが含まれていないことを確認
        removed_commands = ['schedule', 'list-schedules', 'list-recordings']
        for command in removed_commands:
            self.assertNotIn(command, self.cli.INTERACTIVE_COMMANDS)
    
    def test_timefree_command_options(self):
        """タイムフリー専用コマンドオプション確認"""
        expected_options = {
            'list-programs': ['--date', '--station'],
            'record': ['--date', '--station', '--title', '--format', '--output'],
            'record-id': ['--program-id', '--format', '--output'],
            'search-programs': ['--keyword', '--date-range', '--station']
        }
        
        for command, options in expected_options.items():
            self.assertIn(command, self.cli.COMMAND_OPTIONS)
            for option in options:
                self.assertIn(option, self.cli.COMMAND_OPTIONS[command])
    
    @patch('src.cli.RecRadikoCLI._run_interactive')
    def test_interactive_mode_default(self, mock_interactive):
        """デフォルトで対話型モードが起動することのテスト"""
        mock_interactive.return_value = 0
        
        exit_code = self.cli.run([])
        
        self.assertEqual(exit_code, 0)
        mock_interactive.assert_called_once()
    
    def test_print_interactive_help(self):
        """対話型ヘルプ表示テスト"""
        with redirect_stdout(io.StringIO()) as captured_output:
            self.cli._print_interactive_help()
            
            help_text = captured_output.getvalue()
            
            # タイムフリー専用コマンドが表示されることを確認
            self.assertIn('list-programs', help_text)
            self.assertIn('record', help_text)
            self.assertIn('record-id', help_text) 
            self.assertIn('search-programs', help_text)
            
            # タイムフリー専用の説明が含まれることを確認
            self.assertIn('タイムフリー専用', help_text)
            self.assertIn('過去7日間', help_text)
            
            # 削除されたコマンドが表示されないことを確認
            self.assertNotIn('schedule', help_text)
            self.assertNotIn('list-schedules', help_text)


class TestTimeFreeListProgramsCommand(unittest.TestCase):
    """list-programsコマンドのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.cli = self._create_test_cli()
        
        self.sample_programs = [
            ProgramInfo(
                program_id="TBS_20250710_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 10, 6, 0, 0),
                end_time=datetime(2025, 7, 10, 8, 30, 0),
                description="朝の情報番組",
                is_timefree_available=True
            ),
            ProgramInfo(
                program_id="TBS_20250710_090000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="ジェーン・スー 生活は踊る",
                start_time=datetime(2025, 7, 10, 9, 0, 0),
                end_time=datetime(2025, 7, 10, 12, 0, 0),
                description="平日お昼の番組",
                is_timefree_available=True
            )
        ]
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_cli(self):
        """テスト用CLIインスタンス作成"""
        config_file = f"{self.temp_dir}/test_config.json"
        with open(config_file, 'w') as f:
            json.dump({"area_id": "JP13"}, f)
        
        cli = RecRadikoCLI(config_file=config_file)
        cli.program_history_manager = Mock(spec=ProgramHistoryManager)
        return cli
    
    def test_execute_list_programs_command_success(self):
        """list-programsコマンド実行成功"""
        command_args = ['list-programs', '2025-07-10', '--station', 'TBS']
        
        self.cli.program_history_manager.get_programs_by_date.return_value = self.sample_programs
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 0)
            output = captured_output.getvalue()
            
            # 番組情報が表示されることを確認
            self.assertIn("森本毅郎・スタンバイ!", output)
            self.assertIn("ジェーン・スー 生活は踊る", output)
            self.assertIn("TBSラジオ", output)
            
            # 正しい引数でメソッドが呼ばれることを確認
            self.cli.program_history_manager.get_programs_by_date.assert_called_once_with("2025-07-10", "TBS")
    
    def test_execute_list_programs_command_missing_date(self):
        """list-programsコマンド日付指定なしエラー"""
        command_args = ['list-programs']
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 1)
            output = captured_output.getvalue()
            self.assertIn("使用法", output)
            self.assertIn("list-programs", output)
    
    def test_execute_list_programs_command_no_results(self):
        """list-programsコマンド結果なし"""
        command_args = ['list-programs', '2025-07-10']
        
        self.cli.program_history_manager.get_programs_by_date.return_value = []
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 0)
            output = captured_output.getvalue()
            self.assertIn("番組が見つかりません", output)


class TestTimeFreeRecordCommand(unittest.TestCase):
    """recordコマンドのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.cli = self._create_test_cli()
        
        self.sample_program = ProgramInfo(
            program_id="TBS_20250710_060000",
            station_id="TBS",
            station_name="TBSラジオ",
            title="森本毅郎・スタンバイ!",
            start_time=datetime(2025, 7, 10, 6, 0, 0),
            end_time=datetime(2025, 7, 10, 8, 30, 0),
            description="朝の情報番組",
            is_timefree_available=True
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_cli(self):
        """テスト用CLIインスタンス作成"""
        config_file = f"{self.temp_dir}/test_config.json"
        with open(config_file, 'w') as f:
            json.dump({"area_id": "JP13", "output_dir": self.temp_dir}, f)
        
        cli = RecRadikoCLI(config_file=config_file)
        cli.program_history_manager = Mock(spec=ProgramHistoryManager)
        cli.timefree_recorder = Mock(spec=TimeFreeRecorder)
        return cli
    
    @patch('asyncio.run')
    def test_execute_record_command_success(self, mock_asyncio_run):
        """recordコマンド実行成功"""
        command_args = ['record', '2025-07-10', 'TBS', '森本毅郎・スタンバイ!']
        
        # 番組検索結果をモック
        self.cli.program_history_manager.search_programs.return_value = [self.sample_program]
        
        # 録音結果をモック
        recording_result = RecordingResult(
            success=True,
            output_path=f"{self.temp_dir}/recording.mp3",
            file_size_bytes=1024000,
            recording_duration_seconds=120.0,
            total_segments=10,
            failed_segments=0,
            error_messages=[]
        )
        mock_asyncio_run.return_value = recording_result
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 0)
            output = captured_output.getvalue()
            
            # 録音開始・完了メッセージが表示されることを確認
            self.assertIn("録音開始", output)
            self.assertIn("録音完了", output)
            
            # 番組検索が実行されることを確認
            self.cli.program_history_manager.search_programs.assert_called_once()
            
            # 録音が実行されることを確認
            mock_asyncio_run.assert_called_once()
    
    def test_execute_record_command_missing_args(self):
        """recordコマンド引数不足エラー"""
        command_args = ['record', '2025-07-10']
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 1)
            output = captured_output.getvalue()
            self.assertIn("使用法", output)
    
    def test_execute_record_command_program_not_found(self):
        """recordコマンド番組見つからずエラー"""
        command_args = ['record', '2025-07-10', 'TBS', '存在しない番組']
        
        self.cli.program_history_manager.search_programs.return_value = []
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 1)
            output = captured_output.getvalue()
            self.assertIn("番組が見つかりません", output)
    
    @patch('asyncio.run')
    def test_execute_record_command_recording_failed(self, mock_asyncio_run):
        """recordコマンド録音失敗"""
        command_args = ['record', '2025-07-10', 'TBS', '森本毅郎・スタンバイ!']
        
        self.cli.program_history_manager.search_programs.return_value = [self.sample_program]
        
        # 録音失敗結果をモック
        recording_result = RecordingResult(
            success=False,
            output_path="",
            file_size_bytes=0,
            recording_duration_seconds=0,
            total_segments=0,
            failed_segments=0,
            error_messages=["録音エラーが発生しました"]
        )
        mock_asyncio_run.return_value = recording_result
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 1)
            output = captured_output.getvalue()
            self.assertIn("録音に失敗", output)


class TestTimeFreeRecordIdCommand(unittest.TestCase):
    """record-idコマンドのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.cli = self._create_test_cli()
        
        self.sample_program = ProgramInfo(
            program_id="TBS_20250710_060000",
            station_id="TBS",
            station_name="TBSラジオ",
            title="森本毅郎・スタンバイ!",
            start_time=datetime(2025, 7, 10, 6, 0, 0),
            end_time=datetime(2025, 7, 10, 8, 30, 0),
            description="朝の情報番組",
            is_timefree_available=True
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_cli(self):
        """テスト用CLIインスタンス作成"""
        config_file = f"{self.temp_dir}/test_config.json"
        with open(config_file, 'w') as f:
            json.dump({"area_id": "JP13", "output_dir": self.temp_dir}, f)
        
        cli = RecRadikoCLI(config_file=config_file)
        cli.program_history_manager = Mock(spec=ProgramHistoryManager)
        cli.timefree_recorder = Mock(spec=TimeFreeRecorder)
        return cli
    
    @patch('asyncio.run')
    def test_execute_record_id_command_success(self, mock_asyncio_run):
        """record-idコマンド実行成功"""
        command_args = ['record-id', 'TBS_20250710_060000']
        
        # 番組ID検索結果をモック
        self.cli.program_history_manager.get_program_by_id.return_value = self.sample_program
        
        # 録音結果をモック
        recording_result = RecordingResult(
            success=True,
            output_path=f"{self.temp_dir}/recording.mp3",
            file_size_bytes=1024000,
            recording_duration_seconds=120.0,
            total_segments=10,
            failed_segments=0,
            error_messages=[]
        )
        mock_asyncio_run.return_value = recording_result
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 0)
            output = captured_output.getvalue()
            
            # 録音開始・完了メッセージが表示されることを確認
            self.assertIn("録音開始", output)
            self.assertIn("録音完了", output)
            
            # 番組ID検索が実行されることを確認
            self.cli.program_history_manager.get_program_by_id.assert_called_once_with('TBS_20250710_060000')
    
    def test_execute_record_id_command_missing_args(self):
        """record-idコマンド引数不足エラー"""
        command_args = ['record-id']
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 1)
            output = captured_output.getvalue()
            self.assertIn("使用法", output)
    
    def test_execute_record_id_command_program_not_found(self):
        """record-idコマンド番組見つからずエラー"""
        command_args = ['record-id', 'INVALID_20250710_060000']
        
        self.cli.program_history_manager.get_program_by_id.return_value = None
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 1)
            output = captured_output.getvalue()
            self.assertIn("番組が見つかりません", output)


class TestTimeFreeSearchProgramsCommand(unittest.TestCase):
    """search-programsコマンドのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.cli = self._create_test_cli()
        
        self.sample_programs = [
            ProgramInfo(
                program_id="TBS_20250710_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 10, 6, 0, 0),
                end_time=datetime(2025, 7, 10, 8, 30, 0),
                performers=["森本毅郎", "寺島尚正"],
                is_timefree_available=True
            ),
            ProgramInfo(
                program_id="QRR_20250710_060000",
                station_id="QRR",
                station_name="文化放送",
                title="おはよう寺ちゃん",
                start_time=datetime(2025, 7, 10, 6, 0, 0),
                end_time=datetime(2025, 7, 10, 8, 30, 0),
                performers=["寺島尚正"],
                is_timefree_available=True
            )
        ]
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_cli(self):
        """テスト用CLIインスタンス作成"""
        config_file = f"{self.temp_dir}/test_config.json"
        with open(config_file, 'w') as f:
            json.dump({"area_id": "JP13"}, f)
        
        cli = RecRadikoCLI(config_file=config_file)
        cli.program_history_manager = Mock(spec=ProgramHistoryManager)
        return cli
    
    def test_execute_search_programs_command_success(self):
        """search-programsコマンド実行成功"""
        command_args = ['search-programs', '森本毅郎']
        
        self.cli.program_history_manager.search_programs.return_value = [self.sample_programs[0]]
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 0)
            output = captured_output.getvalue()
            
            # 検索結果が表示されることを確認
            self.assertIn("森本毅郎・スタンバイ!", output)
            self.assertIn("TBSラジオ", output)
            
            # 正しい引数でメソッドが呼ばれることを確認
            self.cli.program_history_manager.search_programs.assert_called_once_with(
                "森本毅郎", date_range=None, station_ids=None
            )
    
    def test_execute_search_programs_command_with_station_filter(self):
        """search-programsコマンド放送局フィルター付き実行"""
        command_args = ['search-programs', '寺島尚正', '--station', 'TBS']
        
        self.cli.program_history_manager.search_programs.return_value = [self.sample_programs[0]]
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 0)
            
            # 放送局フィルターが適用されることを確認
            self.cli.program_history_manager.search_programs.assert_called_once_with(
                "寺島尚正", date_range=None, station_ids=["TBS"]
            )
    
    def test_execute_search_programs_command_missing_keyword(self):
        """search-programsコマンドキーワード指定なしエラー"""
        command_args = ['search-programs']
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 1)
            output = captured_output.getvalue()
            self.assertIn("使用法", output)
    
    def test_execute_search_programs_command_no_results(self):
        """search-programsコマンド検索結果なし"""
        command_args = ['search-programs', '存在しないキーワード']
        
        self.cli.program_history_manager.search_programs.return_value = []
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 0)
            output = captured_output.getvalue()
            self.assertIn("番組が見つかりません", output)


class TestTimeFreeErrorHandling(unittest.TestCase):
    """タイムフリー関連エラーハンドリングテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.cli = self._create_test_cli()
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_cli(self):
        """テスト用CLIインスタンス作成"""
        config_file = f"{self.temp_dir}/test_config.json"
        with open(config_file, 'w') as f:
            json.dump({"area_id": "JP13"}, f)
        
        cli = RecRadikoCLI(config_file=config_file)
        cli.program_history_manager = Mock(spec=ProgramHistoryManager)
        cli.timefree_recorder = Mock(spec=TimeFreeRecorder)
        return cli
    
    def test_list_programs_command_exception_handling(self):
        """list-programsコマンド例外処理テスト"""
        command_args = ['list-programs', '2025-07-10']
        
        self.cli.program_history_manager.get_programs_by_date.side_effect = Exception("API エラー")
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 1)
            output = captured_output.getvalue()
            self.assertIn("エラー", output)
    
    def test_search_programs_command_exception_handling(self):
        """search-programsコマンド例外処理テスト"""
        command_args = ['search-programs', 'キーワード']
        
        self.cli.program_history_manager.search_programs.side_effect = Exception("検索エラー")
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 1)
            output = captured_output.getvalue()
            self.assertIn("エラー", output)
    
    def test_unknown_command_handling(self):
        """不明なコマンドの処理テスト"""
        command_args = ['unknown-command']
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._execute_interactive_command(command_args)
            
            self.assertEqual(result, 1)
            output = captured_output.getvalue()
            self.assertIn("不明なコマンド", output)


if __name__ == "__main__":
    unittest.main()