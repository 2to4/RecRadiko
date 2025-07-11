"""
CLIモジュールの単体テスト（再設計版）
実際のCLI実装に基づいたテスト
"""

import unittest
import tempfile
import sys
import io
import json
import argparse
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from src.cli import RecRadikoCLI
from src.auth import AuthInfo
from src.program_info import Station, Program
from src.recording import RecordingJob, RecordingStatus
from src.scheduler import RecordingSchedule, RepeatPattern, ScheduleStatus


class TestRecRadikoCLI(unittest.TestCase):
    """RecRadikoCLI クラスのテスト（再設計版）"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        # モックオブジェクトの作成
        self.mock_auth = Mock()
        self.mock_program_info = Mock()
        self.mock_streaming = Mock()
        self.mock_recording = Mock()
        self.mock_file_manager = Mock()
        self.mock_scheduler = Mock()
        self.mock_error_handler = Mock()
        
        # テスト用設定ファイルを作成
        test_config = {
            "area_id": "JP13",
            "premium_username": "",
            "premium_password": "",
            "output_dir": f"{self.temp_dir}/recordings",
            "default_format": "aac",
            "default_bitrate": 128,
            "max_concurrent_recordings": 4,
            "auto_cleanup_enabled": True,
            "retention_days": 30,
            "min_free_space_gb": 10.0,
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
            streaming_manager=self.mock_streaming,
            recording_manager=self.mock_recording,
            file_manager=self.mock_file_manager,
            scheduler=self.mock_scheduler,
            error_handler=self.mock_error_handler
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
        self.assertEqual(self.cli.streaming_manager, self.mock_streaming)
        self.assertEqual(self.cli.recording_manager, self.mock_recording)
        self.assertEqual(self.cli.file_manager, self.mock_file_manager)
        self.assertEqual(self.cli.scheduler, self.mock_scheduler)
        self.assertEqual(self.cli.error_handler, self.mock_error_handler)
    
    def test_create_parser(self):
        """引数パーサー作成のテスト（対話型モード専用）"""
        parser = self.cli.create_parser()
        
        self.assertIsInstance(parser, argparse.ArgumentParser)
        self.assertEqual(parser.prog, 'RecRadiko')
        
        # ヘルプテキストに対話型モードの説明が含まれることを確認
        help_text = parser.format_help()
        self.assertIn('対話型モード', help_text)
        self.assertIn('--daemon', help_text)
        self.assertIn('--verbose', help_text)
    
    @patch('src.cli.RecRadikoCLI._run_interactive')
    def test_interactive_mode_default(self, mock_interactive):
        """デフォルトで対話型モードが起動することのテスト"""
        mock_interactive.return_value = 0
        
        exit_code = self.cli.run([])
        
        self.assertEqual(exit_code, 0)
        mock_interactive.assert_called_once()
    
    @unittest.skip("対話型モード専用に変更されたため、サブコマンドのパーサーテストは無効")
    def test_parser_record_command(self):
        """recordコマンドの引数解析テスト（無効化）"""
        pass
    
    @unittest.skip("対話型モード専用に変更されたため、サブコマンドのパーサーテストは無効")
    def test_parser_schedule_command(self):
        """scheduleコマンドの引数解析テスト（無効化）"""
        pass
    
    @unittest.skip("対話型モード専用に変更されたため、サブコマンドのパーサーテストは無効")
    def test_parser_list_stations_command(self):
        """list-stationsコマンドの引数解析テスト（無効化）"""
        pass
    
    def test_parser_invalid_command(self):
        """無効なコマンドのテスト"""
        parser = self.cli.create_parser()
        
        with self.assertRaises(SystemExit):
            parser.parse_args(['invalid-command'])
    
    @unittest.skip("対話型モード専用に変更されたため、サブコマンド実行テストは無効")
    def test_run_record_command(self):
        """recordコマンド実行のテスト"""
        # 録音ジョブをモック
        mock_job = RecordingJob(
            id="test_job_001",
            station_id="TBS",
            program_title="即時録音",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=60),
            output_path="/tmp/test_recording.aac",
            status=RecordingStatus.PENDING
        )
        
        self.mock_recording.create_recording_job.return_value = mock_job
        
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = self.cli.run(['record', 'TBS', '60'])
        
        self.assertEqual(exit_code, 0)
        self.mock_recording.create_recording_job.assert_called_once()
        output = captured_output.getvalue()
        self.assertIn("録音を開始しました", output)
    
    @unittest.skip("対話型モード専用に変更されたため、サブコマンド実行テストは無効")
    def test_run_schedule_command(self):
        """scheduleコマンド実行のテスト"""
        # スケジュール追加成功をモック
        self.mock_scheduler.add_schedule.return_value = True
        
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = self.cli.run([
                'schedule', 'TBS', '番組名', 
                '2024-01-01T20:00', '2024-01-01T21:00'
            ])
        
        self.assertEqual(exit_code, 0)
        self.mock_scheduler.add_schedule.assert_called_once()
        output = captured_output.getvalue()
        self.assertIn("録音予約を追加", output)
    
    @unittest.skip("対話型モード専用に変更されたため、サブコマンド実行テストは無効")
    def test_run_list_stations_command(self):
        """list-stationsコマンド実行のテスト"""
        # 放送局リストをモック
        mock_stations = [
            Station(
                id="TBS",
                name="TBSラジオ",
                area_id="JP13",
                ascii_name="TBS",
                logo_url="https://radiko.jp/res/images/TBS_logo.png"
            ),
            Station(
                id="QRR",
                name="文化放送",
                area_id="JP13", 
                ascii_name="QRR",
                logo_url="https://radiko.jp/res/images/QRR_logo.png"
            )
        ]
        
        self.mock_program_info.fetch_station_list.return_value = mock_stations
        
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = self.cli.run(['list-stations'])
        
        self.assertEqual(exit_code, 0)
        self.mock_program_info.fetch_station_list.assert_called_once()
        output = captured_output.getvalue()
        self.assertIn("TBS", output)
        self.assertIn("QRR", output)
    
    @unittest.skip("対話型モード専用に変更されたため、サブコマンド実行テストは無効")
    def test_run_list_programs_command(self):
        """list-programsコマンド実行のテスト"""
        # 番組リストをモック
        mock_programs = [
            Program(
                id="TBS_20240101_2000",
                title="テスト番組1",
                start_time=datetime(2024, 1, 1, 20, 0, 0),
                end_time=datetime(2024, 1, 1, 21, 0, 0),
                duration=60,
                station_id="TBS",
                performers=["出演者1"],
                description="テスト番組の説明",
                genre="音楽"
            )
        ]
        
        self.mock_program_info.fetch_program_guide.return_value = mock_programs
        
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = self.cli.run(['list-programs', 'TBS', '--date', '2024-01-01'])
        
        self.assertEqual(exit_code, 0)
        self.mock_program_info.fetch_program_guide.assert_called_once()
        output = captured_output.getvalue()
        self.assertIn("テスト番組1", output)
    
    @unittest.skip("対話型モード専用に変更されたため、サブコマンド実行テストは無効")
    def test_run_list_schedules_command(self):
        """list-schedulesコマンド実行のテスト"""
        # スケジュールリストをモック
        mock_schedules = [
            RecordingSchedule(
                schedule_id="schedule_001",
                station_id="TBS",
                program_title="定期番組1",
                start_time=datetime(2024, 1, 1, 20, 0, 0),
                end_time=datetime(2024, 1, 1, 21, 0, 0),
                repeat_pattern=RepeatPattern.WEEKLY,
                status=ScheduleStatus.SCHEDULED
            )
        ]
        
        self.mock_scheduler.list_schedules.return_value = mock_schedules
        
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = self.cli.run(['list-schedules'])
        
        self.assertEqual(exit_code, 0)
        self.mock_scheduler.list_schedules.assert_called_once()
        output = captured_output.getvalue()
        self.assertIn("定期番組1", output)
    
    @unittest.skip("対話型モード専用に変更されたため、サブコマンド実行テストは無効")
    def test_run_remove_schedule_command(self):
        """remove-scheduleコマンド実行のテスト"""
        # スケジュール削除成功をモック
        self.mock_scheduler.remove_schedule.return_value = True
        
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = self.cli.run(['remove-schedule', 'schedule_001'])
        
        self.assertEqual(exit_code, 0)
        self.mock_scheduler.remove_schedule.assert_called_once_with('schedule_001')
        output = captured_output.getvalue()
        self.assertIn("スケジュールを削除", output)
    
    @unittest.skip("対話型モード専用に変更されたため、サブコマンド実行テストは無効")
    def test_run_remove_schedule_failure(self):
        """remove-scheduleコマンド失敗のテスト"""
        # スケジュール削除失敗をモック
        self.mock_scheduler.remove_schedule.return_value = False
        
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = self.cli.run(['remove-schedule', 'nonexistent'])
        
        self.assertEqual(exit_code, 1)
        output = captured_output.getvalue()
        self.assertIn("スケジュールが見つかりません", output)
    
    @unittest.skip("対話型モード専用に変更されたため、サブコマンド実行テストは無効")
    def test_run_show_config_command(self):
        """show-configコマンド実行のテスト"""
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = self.cli.run(['show-config'])
        
        self.assertEqual(exit_code, 0)
        output = captured_output.getvalue()
        self.assertIn("area_id", output)
        self.assertIn("output_dir", output)
    
    @unittest.skip("対話型モード専用に変更されたため、サブコマンド実行テストは無効")
    def test_run_status_command(self):
        """statusコマンド実行のテスト"""
        # 各種ステータス情報をモック
        self.mock_recording.list_jobs.return_value = []
        self.mock_scheduler.get_next_schedules.return_value = []
        
        from src.file_manager import StorageInfo
        mock_storage = StorageInfo(
            total_space=1000000000,
            used_space=400000000,
            free_space=600000000,
            recording_files_size=200000000,
            file_count=50
        )
        self.mock_file_manager.get_storage_info.return_value = mock_storage
        
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = self.cli.run(['status'])
        
        self.assertEqual(exit_code, 0)
        output = captured_output.getvalue()
        self.assertIn("録音状況", output)
        self.assertIn("ストレージ", output)
    
    def test_run_with_invalid_args(self):
        """無効な引数でのテスト"""
        with redirect_stderr(io.StringIO()) as captured_error:
            try:
                exit_code = self.cli.run(['invalid-command'])
            except SystemExit as e:
                exit_code = e.code
        
        self.assertEqual(exit_code, 2)  # argparseのエラー
    
    @patch('src.cli.RecRadikoCLI._run_interactive')
    def test_run_with_exception(self, mock_interactive):
        """例外発生時のテスト（対話型モード専用）"""
        # 対話型モードで例外を発生させる
        mock_interactive.side_effect = Exception("Test exception")
        
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = self.cli.run([])
        
        self.assertEqual(exit_code, 1)
        output = captured_output.getvalue()
        self.assertIn("エラー", output)
    
    def test_config_loading(self):
        """設定ファイル読み込みのテスト"""
        # テスト用設定ファイルを作成
        test_config = {
            "area_id": "JP27",
            "output_dir": "/tmp/recordings",
            "default_format": "mp3"
        }
        
        config_file = Path(self.temp_dir) / "test_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f)
        
        # 新しいCLIインスタンスで設定読み込み
        cli = RecRadikoCLI(config_file=str(config_file))
        
        self.assertEqual(cli.config["area_id"], "JP27")
        self.assertEqual(cli.config["output_dir"], "/tmp/recordings")
        self.assertEqual(cli.config["default_format"], "mp3")
    
    def test_config_saving(self):
        """設定ファイル保存のテスト"""
        # 設定を変更
        self.cli.config["area_id"] = "JP14"
        self.cli.config["output_dir"] = "/new/path"
        
        # 設定を保存
        self.cli._save_config(self.cli.config)
        
        # 設定ファイルが更新されることを確認
        self.assertTrue(self.cli.config_path.exists())
        
        with open(self.cli.config_path, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
        
        self.assertEqual(saved_config["area_id"], "JP14")
        self.assertEqual(saved_config["output_dir"], "/new/path")
    
    def test_daemon_mode_flag(self):
        """デーモンモードフラグのテスト（対話型モード専用）"""
        parser = self.cli.create_parser()
        
        # デーモンモードフラグ
        args = parser.parse_args(['--daemon'])
        self.assertTrue(args.daemon)
        
        # 通常モード（引数なし）
        args = parser.parse_args([])
        self.assertFalse(args.daemon)
    
    @patch('src.cli.RecRadikoCLI._run_daemon')
    def test_daemon_mode_execution(self, mock_run_daemon):
        """デーモンモード実行のテスト"""
        mock_run_daemon.return_value = None
        
        exit_code = self.cli.run(['--daemon'])
        
        self.assertEqual(exit_code, 0)
        mock_run_daemon.assert_called_once()
    
    def test_verbose_mode(self):
        """詳細モードのテスト（対話型モード専用）"""
        parser = self.cli.create_parser()
        
        # 詳細モード
        args = parser.parse_args(['--verbose'])
        self.assertTrue(args.verbose)
        
        # 短縮形
        args = parser.parse_args(['-v'])
        self.assertTrue(args.verbose)
        
        # 通常モード
        args = parser.parse_args([])
        self.assertFalse(args.verbose)


class TestCLICommands(unittest.TestCase):
    """CLIコマンド個別テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        # モックオブジェクトの作成
        self.mock_auth = Mock()
        self.mock_program_info = Mock()
        self.mock_streaming = Mock()
        self.mock_recording = Mock()
        self.mock_file_manager = Mock()
        self.mock_scheduler = Mock()
        self.mock_error_handler = Mock()
        
        self.cli = RecRadikoCLI(
            config_file=f"{self.temp_dir}/test_config.json",
            auth_manager=self.mock_auth,
            program_info_manager=self.mock_program_info,
            streaming_manager=self.mock_streaming,
            recording_manager=self.mock_recording,
            file_manager=self.mock_file_manager,
            scheduler=self.mock_scheduler,
            error_handler=self.mock_error_handler
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cmd_record_with_options(self):
        """recordコマンドのオプション処理テスト"""
        # 録音ジョブをモック
        mock_job = RecordingJob(
            id="test_job_002",
            station_id="QRR",
            program_title="カスタム録音",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=30),
            output_path="/tmp/custom_output.mp3",
            status=RecordingStatus.PENDING
        )
        
        self.mock_recording.create_recording_job.return_value = mock_job
        
        # 模擬args作成
        class MockArgs:
            station_id = "QRR"
            duration = 30
            format = "mp3"
            bitrate = 192
            output = "/tmp/custom_output.mp3"
        
        args = MockArgs()
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._cmd_record(args)
        
        self.assertEqual(result, 0)
        self.mock_recording.create_recording_job.assert_called_once()
        
        # 呼び出された引数を確認
        call_args = self.mock_recording.create_recording_job.call_args
        self.assertEqual(call_args[1]['station_id'], 'QRR')
        self.assertEqual(call_args[1]['format'], 'mp3')
        self.assertEqual(call_args[1]['bitrate'], 192)
    
    def test_cmd_schedule_with_repeat(self):
        """scheduleコマンドの繰り返し処理テスト"""
        self.mock_scheduler.add_schedule.return_value = True
        
        class MockArgs:
            station_id = "TBS"
            program_title = "週間番組"
            start_time = "2024-01-01T20:00"
            end_time = "2024-01-01T21:00"
            repeat = "weekly"
            repeat_end = "2024-12-31"
            format = "aac"
            bitrate = 128
            notes = "毎週録音"
        
        args = MockArgs()
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._cmd_schedule(args)
        
        self.assertEqual(result, 0)
        self.mock_scheduler.add_schedule.assert_called_once()
        
        # スケジュール追加の引数確認
        call_args = self.mock_scheduler.add_schedule.call_args
        call_kwargs = call_args.kwargs if call_args.kwargs else {}
        
        # 引数の確認（位置引数または名前付き引数を確認）
        if 'repeat_pattern' in call_kwargs:
            self.assertEqual(call_kwargs['repeat_pattern'], RepeatPattern.WEEKLY)
        if 'program_title' in call_kwargs:
            self.assertEqual(call_kwargs['program_title'], "週間番組")
    
    def test_cmd_list_programs_with_date(self):
        """list-programsコマンドの日付指定テスト"""
        mock_programs = [
            Program(
                id="TBS_20240101_2000",
                title="元日番組",
                start_time=datetime(2024, 1, 1, 20, 0, 0),
                end_time=datetime(2024, 1, 1, 22, 0, 0),
                duration=120,  # 分単位
                station_id="TBS",
                performers=["司会者"],
                description="元日特別番組",
                genre="バラエティ"
            )
        ]
        
        self.mock_program_info.fetch_program_guide.return_value = mock_programs
        
        class MockArgs:
            station_id = "TBS"
            date = "2024-01-01"
        
        args = MockArgs()
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._cmd_list_programs(args)
        
        self.assertEqual(result, 0)
        self.mock_program_info.fetch_program_guide.assert_called_once()
        
        output = captured_output.getvalue()
        self.assertIn("元日番組", output)
        self.assertIn("2024-01-01", output)
    
    def test_schedule_command_positional_args(self):
        """scheduleコマンドの位置引数テスト"""
        # 修正後のadd_scheduleメソッドで位置引数が正しく処理されることを確認
        self.mock_scheduler.add_schedule.return_value = "test_schedule_id"
        
        class MockArgs:
            station_id = "TBS"
            program_title = "位置引数テスト"
            start_time = "2024-01-01T20:00"
            end_time = "2024-01-01T21:00"
            repeat = None
            repeat_end = None
            format = "aac"
            bitrate = 128
            notes = "位置引数テスト"
        
        args = MockArgs()
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._cmd_schedule(args)
        
        self.assertEqual(result, 0)
        self.mock_scheduler.add_schedule.assert_called_once()
        
        # 呼び出し引数の確認
        call_args = self.mock_scheduler.add_schedule.call_args
        
        # 最初の引数（位置引数）がstation_idであることを確認
        self.assertEqual(call_args[0][0], "TBS")
        
        # キーワード引数の確認
        call_kwargs = call_args.kwargs if call_args.kwargs else {}
        self.assertEqual(call_kwargs.get('program_title'), "位置引数テスト")
        self.assertEqual(call_kwargs.get('format'), "aac")
        self.assertEqual(call_kwargs.get('bitrate'), 128)
        self.assertEqual(call_kwargs.get('notes'), "位置引数テスト")
        
        # 出力の確認
        output = captured_output.getvalue()
        self.assertIn("録音予約を追加しました", output)
        self.assertIn("位置引数テスト", output)
        self.assertIn("TBS", output)
    
    def test_schedule_command_with_repeat_pattern(self):
        """scheduleコマンドの繰り返しパターンテスト"""
        self.mock_scheduler.add_schedule.return_value = "test_schedule_id_repeat"
        
        class MockArgs:
            station_id = "QRR"
            program_title = "繰り返しテスト"
            start_time = "2024-01-01T18:00"
            end_time = "2024-01-01T19:00"
            repeat = "daily"
            repeat_end = "2024-01-31"
            format = "mp3"
            bitrate = 192
            notes = "毎日録音"
        
        args = MockArgs()
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._cmd_schedule(args)
        
        self.assertEqual(result, 0)
        self.mock_scheduler.add_schedule.assert_called_once()
        
        # 呼び出し引数の確認
        call_args = self.mock_scheduler.add_schedule.call_args
        
        # 最初の引数（位置引数）がstation_idであることを確認
        self.assertEqual(call_args[0][0], "QRR")
        
        # キーワード引数の確認
        call_kwargs = call_args.kwargs if call_args.kwargs else {}
        self.assertEqual(call_kwargs.get('program_title'), "繰り返しテスト")
        self.assertEqual(call_kwargs.get('format'), "mp3")
        self.assertEqual(call_kwargs.get('bitrate'), 192)
        self.assertEqual(call_kwargs.get('notes'), "毎日録音")
        
        # 繰り返しパターンの確認
        self.assertEqual(call_kwargs.get('repeat_pattern'), RepeatPattern.DAILY)
        
        # 繰り返し終了日の確認
        repeat_end_date = call_kwargs.get('repeat_end_date')
        self.assertIsNotNone(repeat_end_date)
        self.assertEqual(repeat_end_date.year, 2024)
        self.assertEqual(repeat_end_date.month, 1)
        self.assertEqual(repeat_end_date.day, 31)
        
        # 出力の確認
        output = captured_output.getvalue()
        self.assertIn("録音予約を追加しました", output)
        self.assertIn("繰り返しテスト", output)
        self.assertIn("QRR", output)
    
    def test_schedule_command_error_handling(self):
        """scheduleコマンドのエラーハンドリングテスト"""
        # add_scheduleが失敗した場合
        self.mock_scheduler.add_schedule.return_value = False
        
        class MockArgs:
            station_id = "INVALID"
            program_title = "エラーテスト"
            start_time = "2024-01-01T20:00"
            end_time = "2024-01-01T21:00"
            repeat = None
            repeat_end = None
            format = "aac"
            bitrate = 128
            notes = ""
        
        args = MockArgs()
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._cmd_schedule(args)
        
        # エラーが発生した場合の戻り値確認
        self.assertEqual(result, 1)
        
        # エラーメッセージの確認
        output = captured_output.getvalue()
        self.assertIn("予約エラー", output)
    
    def test_schedule_command_exception_handling(self):
        """scheduleコマンドの例外処理テスト"""
        # add_scheduleで例外が発生した場合
        self.mock_scheduler.add_schedule.side_effect = Exception("スケジュールエラー")
        
        class MockArgs:
            station_id = "TBS"
            program_title = "例外テスト"
            start_time = "2024-01-01T20:00"
            end_time = "2024-01-01T21:00"
            repeat = None
            repeat_end = None
            format = "aac"
            bitrate = 128
            notes = ""
        
        args = MockArgs()
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result = self.cli._cmd_schedule(args)
        
        # 例外が発生した場合の戻り値確認
        self.assertEqual(result, 1)
        
        # エラーメッセージの確認
        output = captured_output.getvalue()
        self.assertIn("予約エラー", output)
        self.assertIn("スケジュールエラー", output)


class TestRecRadikoCLILazyInitialization(unittest.TestCase):
    """RecRadikoCLI 遅延初期化のテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        # テスト用設定ファイルを作成
        test_config = {
            "area_id": "JP13",
            "output_dir": f"{self.temp_dir}/recordings",
            "max_concurrent_recordings": 4
        }
        
        self.config_path = Path(self.temp_dir) / "test_config.json"
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)
    
    def test_initial_components_not_created(self):
        """初期化時にスケジューラーや録音管理が作成されないことをテスト"""
        cli = RecRadikoCLI(config_path=str(self.config_path))
        
        # コンポーネント初期化を実行
        cli._initialize_components()
        
        # 遅延初期化対象のコンポーネントがNoneであることを確認
        self.assertIsNone(cli.scheduler)
        self.assertIsNone(cli.recording_manager)
        self.assertIsNone(cli.streaming_manager)
        
        # 必須コンポーネントは初期化されていることを確認
        self.assertIsNotNone(cli.authenticator)
        self.assertIsNotNone(cli.program_manager)
        self.assertIsNotNone(cli.file_manager)
        self.assertIsNotNone(cli.error_handler)
    
    def test_ensure_scheduler_initialized(self):
        """スケジューラー遅延初期化のテスト"""
        with patch('src.scheduler.RecordingScheduler') as mock_scheduler_class:
            mock_scheduler = Mock()
            mock_scheduler_class.return_value = mock_scheduler
            
            cli = RecRadikoCLI(config_path=str(self.config_path))
            cli._initialize_components()
            
            # 初期状態ではスケジューラーがNone
            self.assertIsNone(cli.scheduler)
            
            # 遅延初期化を実行
            cli._ensure_scheduler_initialized()
            
            # スケジューラーが初期化されたことを確認
            self.assertIsNotNone(cli.scheduler)
            mock_scheduler_class.assert_called_once()
            
            # 2回目の呼び出しでは再初期化されないことを確認
            cli._ensure_scheduler_initialized()
            mock_scheduler_class.assert_called_once()  # 呼び出し回数は1回のまま
    
    def test_ensure_streaming_manager_initialized(self):
        """ストリーミング管理遅延初期化のテスト"""
        with patch('src.streaming.StreamingManager') as mock_streaming_class:
            mock_streaming = Mock()
            mock_streaming_class.return_value = mock_streaming
            
            cli = RecRadikoCLI(config_path=str(self.config_path))
            cli._initialize_components()
            
            # 初期状態ではストリーミング管理がNone
            self.assertIsNone(cli.streaming_manager)
            
            # 遅延初期化を実行
            cli._ensure_streaming_manager_initialized()
            
            # ストリーミング管理が初期化されたことを確認
            self.assertIsNotNone(cli.streaming_manager)
            mock_streaming_class.assert_called_once()
    
    def test_ensure_recording_manager_initialized(self):
        """録音管理遅延初期化のテスト"""
        with patch('src.recording.RecordingManager') as mock_recording_class, \
             patch('src.streaming.StreamingManager') as mock_streaming_class:
            mock_streaming = Mock()
            mock_recording = Mock()
            mock_streaming_class.return_value = mock_streaming
            mock_recording_class.return_value = mock_recording
            
            cli = RecRadikoCLI(config_path=str(self.config_path))
            cli._initialize_components()
            
            # 初期状態では録音管理がNone
            self.assertIsNone(cli.recording_manager)
            
            # 遅延初期化を実行
            cli._ensure_recording_manager_initialized()
            
            # 録音管理が初期化されたことを確認
            self.assertIsNotNone(cli.recording_manager)
            mock_recording_class.assert_called_once()
            
            # 依存するストリーミング管理も初期化されることを確認
            mock_streaming_class.assert_called_once()
    
    def test_schedule_command_triggers_lazy_initialization(self):
        """scheduleコマンドがスケジューラーの遅延初期化をトリガーすることをテスト"""
        with patch('src.scheduler.RecordingScheduler') as mock_scheduler_class:
            mock_scheduler = Mock()
            mock_scheduler.add_schedule.return_value = "test_schedule_id"
            mock_scheduler_class.return_value = mock_scheduler
            
            cli = RecRadikoCLI(config_path=str(self.config_path))
            cli._initialize_components()
            
            # 初期状態ではスケジューラーがNone
            self.assertIsNone(cli.scheduler)
            
            # scheduleコマンドの引数を作成
            class MockArgs:
                station_id = "TBS"
                program_title = "テスト番組"
                start_time = "2024-01-01T20:00"
                end_time = "2024-01-01T21:00"
                repeat = None
                repeat_end = None
                format = "aac"
                bitrate = 128
                notes = ""
            
            args = MockArgs()
            
            with redirect_stdout(io.StringIO()):
                result = cli._cmd_schedule(args)
            
            # スケジューラーが遅延初期化されたことを確認
            self.assertIsNotNone(cli.scheduler)
            mock_scheduler_class.assert_called_once()
            
            # スケジュール追加が呼ばれたことを確認
            mock_scheduler.add_schedule.assert_called_once()
            self.assertEqual(result, 0)
    
    def test_record_command_triggers_lazy_initialization(self):
        """recordコマンドが録音管理の遅延初期化をトリガーすることをテスト"""
        with patch('src.recording.RecordingManager') as mock_recording_class, \
             patch('src.streaming.StreamingManager') as mock_streaming_class:
            mock_streaming = Mock()
            mock_recording = Mock()
            # create_recording_jobはjob_idを返す
            mock_job_id = "test_job_123"
            mock_job = Mock()
            mock_job.status = RecordingStatus.PENDING
            mock_recording.create_recording_job.return_value = mock_job_id
            mock_recording.get_job_status.return_value = mock_job
            mock_recording.schedule_recording.return_value = True
            
            mock_streaming_class.return_value = mock_streaming
            mock_recording_class.return_value = mock_recording
            
            cli = RecRadikoCLI(config_path=str(self.config_path))
            cli._initialize_components()
            
            # テスト環境フラグを設定
            cli._all_components_injected = True
            
            # 初期状態では録音管理がNone
            self.assertIsNone(cli.recording_manager)
            
            # recordコマンドの引数を作成
            class MockArgs:
                station_id = "TBS"
                duration = 60
                format = "mp3"
                bitrate = 128
                output = None
            
            args = MockArgs()
            
            with redirect_stdout(io.StringIO()):
                result = cli._cmd_record(args)
            
            # 録音管理が遅延初期化されたことを確認
            self.assertIsNotNone(cli.recording_manager)
            mock_recording_class.assert_called_once()
            
            # 依存するストリーミング管理も初期化されることを確認
            mock_streaming_class.assert_called_once()
            
            self.assertEqual(result, 0)


class TestRecRadikoCLIProcessTermination(unittest.TestCase):
    """RecRadikoCLI プロセス終了のテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        test_config = {
            "area_id": "JP13",
            "output_dir": f"{self.temp_dir}/recordings"
        }
        
        self.config_path = Path(self.temp_dir) / "test_config.json"
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, ensure_ascii=False, indent=2)
    
    def test_cleanup_with_no_components(self):
        """コンポーネントが初期化されていない状態でのクリーンアップテスト"""
        cli = RecRadikoCLI(config_path=str(self.config_path))
        
        # コンポーネント初期化を実行（遅延初期化により一部コンポーネントはNone）
        cli._initialize_components()
        
        # クリーンアップが例外なく実行されることを確認
        try:
            cli._cleanup()
        except Exception as e:
            self.fail(f"クリーンアップで予期しない例外が発生: {e}")
    
    def test_cleanup_with_scheduler_error(self):
        """スケジューラークリーンアップでエラーが発生した場合のテスト"""
        cli = RecRadikoCLI(config_path=str(self.config_path))
        cli._initialize_components()
        
        # モックスケジューラーを設定（shutdownでエラーを発生）
        mock_scheduler = Mock()
        mock_scheduler.shutdown.side_effect = Exception("Scheduler shutdown error")
        cli.scheduler = mock_scheduler
        
        # クリーンアップが例外なく完了することを確認
        with redirect_stderr(io.StringIO()) as captured_stderr:
            try:
                cli._cleanup()
            except Exception as e:
                self.fail(f"クリーンアップで予期しない例外が発生: {e}")
    
    def test_cleanup_with_recording_manager_error(self):
        """録音管理クリーンアップでエラーが発生した場合のテスト"""
        cli = RecRadikoCLI(config_path=str(self.config_path))
        cli._initialize_components()
        
        # モック録音管理を設定（shutdownでエラーを発生）
        mock_recording = Mock()
        mock_recording.shutdown.side_effect = Exception("Recording manager shutdown error")
        cli.recording_manager = mock_recording
        
        # クリーンアップが例外なく完了することを確認
        try:
            cli._cleanup()
        except Exception as e:
            self.fail(f"クリーンアップで予期しない例外が発生: {e}")
    
    @patch('os._exit')
    @patch('threading.active_count')
    @patch('time.sleep')
    def test_forced_process_termination(self, mock_sleep, mock_active_count, mock_exit):
        """残留スレッドがある場合の強制終了テスト"""
        cli = RecRadikoCLI(config_path=str(self.config_path))
        cli._initialize_components()
        
        # 複数のアクティブスレッドがあることをシミュレート
        mock_active_count.return_value = 3  # メインスレッド + 2つの残留スレッド
        
        # クリーンアップを実行
        cli._cleanup()
        
        # 強制終了が呼ばれることを確認
        mock_exit.assert_called_once_with(0)
        mock_sleep.assert_called_once_with(0.1)
    
    @patch('os._exit')
    @patch('threading.active_count')
    def test_normal_process_termination(self, mock_active_count, mock_exit):
        """残留スレッドがない場合の正常終了テスト"""
        cli = RecRadikoCLI(config_path=str(self.config_path))
        cli._initialize_components()
        
        # メインスレッドのみがアクティブ
        mock_active_count.return_value = 1
        
        # クリーンアップを実行
        cli._cleanup()
        
        # 強制終了が呼ばれないことを確認
        mock_exit.assert_not_called()


if __name__ == '__main__':
    unittest.main()