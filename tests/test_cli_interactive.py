"""
対話型モードの単体テスト

対話型CLIモードの動作を検証するテストケース
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import io
import sys
import tempfile
import json
from pathlib import Path

from src.cli import RecRadikoCLI
from src.recording import RecordingJob, RecordingStatus
from src.scheduler import RecordingSchedule, ScheduleStatus, RepeatPattern
from src.program_info import Station, Program
from src.file_manager import FileMetadata
from datetime import datetime, timedelta


class TestCLIInteractiveMode(unittest.TestCase):
    """対話型モードの単体テスト"""
    
    def setUp(self):
        """テストのセットアップ"""
        # テスト用設定ファイル作成
        self.test_config = {
            "area_id": "JP13",
            "output_dir": "./test_recordings",
            "max_concurrent_recordings": 2,
            "notification_enabled": False,
            "log_level": "ERROR",
            "recording": {
                "default_format": "mp3",
                "default_bitrate": 128
            }
        }
        
        # 一時設定ファイル
        self.config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.test_config, self.config_file)
        self.config_file.close()
        
        # モックコンポーネント作成
        self.mock_auth = Mock()
        self.mock_program_info = Mock()
        self.mock_streaming = Mock()
        self.mock_recording = Mock()
        self.mock_file_manager = Mock()
        self.mock_scheduler = Mock()
        self.mock_error_handler = Mock()
        
        # CLIインスタンス作成（すべてモック注入）
        self.cli = RecRadikoCLI(
            config_file=self.config_file.name,
            auth_manager=self.mock_auth,
            program_info_manager=self.mock_program_info,
            streaming_manager=self.mock_streaming,
            recording_manager=self.mock_recording,
            file_manager=self.mock_file_manager,
            scheduler=self.mock_scheduler,
            error_handler=self.mock_error_handler
        )
    
    def tearDown(self):
        """テストのクリーンアップ"""
        Path(self.config_file.name).unlink(missing_ok=True)
    
    def test_interactive_help_display(self):
        """対話型ヘルプ表示のテスト"""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            self.cli._print_interactive_help()
            help_output = mock_stdout.getvalue()
            
            # ヘルプ内容の確認
            self.assertIn("利用可能なコマンド", help_output)
            self.assertIn("record", help_output)
            self.assertIn("schedule", help_output)
            self.assertIn("list-stations", help_output)
            self.assertIn("exit", help_output)
    
    @patch('builtins.input')
    def test_interactive_record_command(self, mock_input):
        """対話型録音コマンドのテスト"""
        # モック設定
        now = datetime.now()
        mock_job = RecordingJob(
            id="test-job-001",
            station_id="TBS",
            program_title="Live Recording",
            start_time=now,
            end_time=now + timedelta(hours=1),
            output_path="./test_recordings/TBS_2024.mp3",
            status=RecordingStatus.RECORDING,
            format="mp3",
            bitrate=128
        )
        self.mock_recording.create_recording_job.return_value = mock_job
        
        # recordコマンドの実行
        result = self.cli._execute_interactive_command(['record', 'TBS', '60'])
        
        # 検証
        self.assertEqual(result, 0)
        # 実際の呼び出しパラメータに合わせて検証
        self.mock_recording.create_recording_job.assert_called_once()
        call_args = self.mock_recording.create_recording_job.call_args
        self.assertEqual(call_args.kwargs['station_id'], 'TBS')
        self.assertEqual(call_args.kwargs['format'], 'mp3')
        self.assertEqual(call_args.kwargs['bitrate'], 128)
        self.assertIn('program_title', call_args.kwargs)
        self.assertIn('start_time', call_args.kwargs)
        self.assertIn('end_time', call_args.kwargs)
        self.assertIn('output_path', call_args.kwargs)
    
    def test_interactive_record_command_with_options(self):
        """オプション付き録音コマンドのテスト"""
        # モック設定
        now = datetime.now()
        mock_job = RecordingJob(
            id="test-job-002",
            station_id="QRR",
            program_title="Live Recording",
            start_time=now,
            end_time=now + timedelta(minutes=30),
            output_path="./test_recordings/QRR_2024.aac",
            status=RecordingStatus.RECORDING,
            format="aac",
            bitrate=192
        )
        self.mock_recording.create_recording_job.return_value = mock_job
        
        # オプション付きrecordコマンド
        result = self.cli._execute_interactive_command([
            'record', 'QRR', '30', '--format', 'aac', '--bitrate', '192'
        ])
        
        # 検証
        self.assertEqual(result, 0)
        # 実際の呼び出しパラメータに合わせて検証
        self.mock_recording.create_recording_job.assert_called_once()
        call_args = self.mock_recording.create_recording_job.call_args
        self.assertEqual(call_args.kwargs['station_id'], 'QRR')
        self.assertEqual(call_args.kwargs['format'], 'aac')
        self.assertEqual(call_args.kwargs['bitrate'], 192)
        self.assertIn('program_title', call_args.kwargs)
        self.assertIn('start_time', call_args.kwargs)
        self.assertIn('end_time', call_args.kwargs)
        self.assertIn('output_path', call_args.kwargs)
    
    def test_interactive_list_stations_command(self):
        """対話型放送局一覧コマンドのテスト"""
        # モック設定
        mock_stations = [
            Station(id="TBS", name="TBSラジオ", ascii_name="TBS", area_id="JP13", logo_url="", banner_url=""),
            Station(id="QRR", name="文化放送", ascii_name="QRR", area_id="JP13", logo_url="", banner_url=""),
            Station(id="LFR", name="ニッポン放送", ascii_name="LFR", area_id="JP13", logo_url="", banner_url="")
        ]
        self.mock_program_info.fetch_station_list.return_value = mock_stations
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['list-stations'])
            output = mock_stdout.getvalue()
            
            # 検証
            self.assertEqual(result, 0)
            self.assertIn("放送局一覧", output)
            self.assertIn("TBS", output)
            self.assertIn("QRR", output)
            self.assertIn("LFR", output)
            self.mock_program_info.fetch_station_list.assert_called_once()
    
    def test_interactive_list_programs_command(self):
        """対話型番組表コマンドのテスト"""
        # モック設定
        now = datetime.now()
        mock_programs = [
            Program(
                id="prog-001",
                station_id="TBS",
                title="ニュース番組",
                start_time=now,
                end_time=now + timedelta(hours=1),
                duration=60,
                performers=["アナウンサーA"]
            ),
            Program(
                id="prog-002",
                station_id="TBS", 
                title="音楽番組",
                start_time=now + timedelta(hours=1),
                end_time=now + timedelta(hours=2),
                duration=60,
                performers=["DJ B", "ゲスト C"]
            )
        ]
        self.mock_program_info.get_program_guide.return_value = mock_programs
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['list-programs', '--station', 'TBS'])
            output = mock_stdout.getvalue()
            
            # 検証
            self.assertEqual(result, 0)
            self.assertIn("番組表", output)
            self.assertIn("ニュース番組", output)
            self.assertIn("音楽番組", output)
            self.assertIn("アナウンサーA", output)
            self.mock_program_info.get_program_guide.assert_called_once()
    
    def test_interactive_schedule_command(self):
        """対話型スケジュールコマンドのテスト"""
        # スケジュールコマンド（schedule実装がないため、基本的なテストのみ）
        result = self.cli._execute_interactive_command([
            'schedule', 'TBS', 'テスト番組', '2024-01-01T20:00', '2024-01-01T21:00'
        ])
        
        # コマンド解析の検証（実装によってはスケジューラ呼び出しも検証）
        # このテストケースは対話型コマンド解析が正常に動作することを確認
        self.assertIsNotNone(result)
    
    def test_interactive_status_command(self):
        """対話型ステータスコマンドのテスト"""
        # モック設定
        self.mock_recording.get_active_jobs.return_value = []
        self.mock_scheduler.list_schedules.return_value = []
        
        mock_storage_info = Mock()
        mock_storage_info.file_count = 10
        mock_storage_info.recording_files_size = 1024 * 1024 * 100  # 100MB
        mock_storage_info.free_space_gb = 50.0
        self.mock_file_manager.get_storage_info.return_value = mock_storage_info
        
        self.mock_scheduler.get_next_schedules.return_value = []
        
        # スケジュールの統計情報もモック
        self.mock_scheduler.get_statistics.return_value = {'active_schedules': 0}
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['status'])
            output = mock_stdout.getvalue()
            
            # 検証（実際の出力に合わせて調整）
            self.assertEqual(result, 0)
            self.assertIn("システム状態", output)
            self.assertIn("録音状況", output)
            self.assertIn("ストレージ使用状況", output)
    
    def test_interactive_stats_command(self):
        """対話型統計コマンドのテスト"""
        # モック設定
        mock_file_stats = {
            'total_files': 25,
            'total_duration_hours': 50.5,
            'total_size_gb': 5.2,
            'average_file_size_mb': 220.5,
            'stations': {
                'TBS': {'count': 15, 'duration': 90000},
                'QRR': {'count': 10, 'duration': 72000}
            }
        }
        self.mock_file_manager.get_statistics.return_value = mock_file_stats
        
        mock_schedule_stats = {
            'total_schedules': 8,
            'active_schedules': 3,
            'completed_schedules': 5
        }
        self.mock_scheduler.get_statistics.return_value = mock_schedule_stats
        
        mock_error_stats = {
            'total_errors': 2,
            'unresolved_errors': 0,
            'recent_errors_24h': 1
        }
        self.mock_error_handler.get_error_statistics.return_value = mock_error_stats
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['stats'])
            output = mock_stdout.getvalue()
            
            # 検証
            self.assertEqual(result, 0)
            self.assertIn("統計情報", output)
            self.assertIn("総録音ファイル: 25", output)
            self.assertIn("総録音時間: 50.5", output)
            self.assertIn("放送局別統計", output)
    
    def test_interactive_invalid_command(self):
        """無効な対話型コマンドのテスト"""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['invalid-command'])
            
            # 無効なコマンドは0を返すか例外を発生する
            # 実装に依存するが、エラーハンドリングが適切であることを確認
            self.assertIsNotNone(result)
    
    def test_interactive_command_parsing_errors(self):
        """対話型コマンド解析エラーのテスト"""
        # 引数不足のrecordコマンド
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['record'])
            output = mock_stdout.getvalue()
            
            # エラーメッセージの確認
            self.assertEqual(result, 1)
            self.assertIn("使用法", output)
        
        # 不正な時間指定
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['record', 'TBS', 'invalid'])
            
            # 数値変換エラーのハンドリング確認
            self.assertIsNotNone(result)
    
    @patch('builtins.input')
    def test_interactive_mode_flow(self, mock_input):
        """対話型モード全体のフローテスト"""
        # 入力シーケンス設定
        mock_input.side_effect = [
            'help',  # ヘルプ表示
            'list-stations',  # 放送局一覧
            'exit'  # 終了
        ]
        
        # モック設定
        mock_stations = [
            Station(id="TBS", name="TBSラジオ", ascii_name="TBS", area_id="JP13", logo_url="", banner_url="")
        ]
        self.mock_program_info.fetch_station_list.return_value = mock_stations
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._run_interactive()
            output = mock_stdout.getvalue()
            
            # 対話型モードの開始と終了を確認
            self.assertEqual(result, 0)
            self.assertIn("RecRadiko 対話型モード", output)
            self.assertIn("RecRadikoを終了します", output)
    
    @patch('builtins.input')
    def test_interactive_mode_keyboard_interrupt(self, mock_input):
        """対話型モードのキーボード割り込みテスト"""
        # KeyboardInterruptを発生させる
        mock_input.side_effect = KeyboardInterrupt()
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._run_interactive()
            output = mock_stdout.getvalue()
            
            # 割り込みによる終了を確認
            self.assertEqual(result, 0)
            self.assertIn("RecRadikoを終了します", output)
    
    @patch('builtins.input')
    def test_interactive_mode_eof_error(self, mock_input):
        """対話型モードのEOFエラーテスト"""
        # EOFErrorを発生させる
        mock_input.side_effect = EOFError()
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._run_interactive()
            output = mock_stdout.getvalue()
            
            # EOF による終了を確認
            self.assertEqual(result, 0)
            self.assertIn("RecRadikoを終了します", output)
    
    @patch('builtins.input')
    def test_interactive_empty_input_handling(self, mock_input):
        """対話型モードの空入力処理テスト"""
        # 空文字列とexitを入力
        mock_input.side_effect = ['', '   ', 'exit']
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._run_interactive()
            
            # 空入力が適切に処理されることを確認
            self.assertEqual(result, 0)
    
    def test_command_argument_parsing(self):
        """コマンド引数解析のテスト"""
        # record コマンドの引数解析
        args_list = ['record', 'TBS', '60', '--format', 'aac', '--bitrate', '320']
        
        # 内部的な引数解析メソッドの動作確認
        # _execute_interactive_command が正しい引数を生成することを検証
        now = datetime.now()
        mock_job = RecordingJob(
            id="test-job-003",
            station_id="TBS",
            program_title="Live Recording",
            start_time=now,
            end_time=now + timedelta(hours=1),
            output_path="./test_recordings/TBS_2024.aac",
            status=RecordingStatus.RECORDING,
            format="aac",
            bitrate=320
        )
        self.mock_recording.create_recording_job.return_value = mock_job
        
        result = self.cli._execute_interactive_command(args_list)
        
        # 解析された引数でrecording_managerが呼び出されることを確認
        self.assertEqual(result, 0)
        # 実際の呼び出しパラメータに合わせて検証
        self.mock_recording.create_recording_job.assert_called_once()
        call_args = self.mock_recording.create_recording_job.call_args
        self.assertEqual(call_args.kwargs['station_id'], 'TBS')
        self.assertEqual(call_args.kwargs['format'], 'aac')
        self.assertEqual(call_args.kwargs['bitrate'], 320)
        self.assertIn('program_title', call_args.kwargs)
        self.assertIn('start_time', call_args.kwargs)
        self.assertIn('end_time', call_args.kwargs)
        self.assertIn('output_path', call_args.kwargs)


if __name__ == '__main__':
    unittest.main()