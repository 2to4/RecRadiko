"""
CLIモジュールの単体テスト（最新実装対応版）
2025年7月12日更新: ライブストリーミング対応・対話型モード専用CLI対応
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
    """RecRadikoCLI クラスのテスト（最新実装対応版）"""
    
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
            "log_file": f"{self.temp_dir}/test.log",
            "live_streaming_enabled": True,
            "playlist_update_interval": 5,
            "max_concurrent_downloads": 3
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
    
    def test_parser_invalid_command(self):
        """無効なコマンドのテスト"""
        parser = self.cli.create_parser()
        
        with self.assertRaises(SystemExit):
            parser.parse_args(['invalid-command'])
    
    def test_run_with_invalid_args(self):
        """無効な引数でのテスト"""
        with redirect_stderr(io.StringIO()) as captured_error:
            try:
                exit_code = self.cli.run(['invalid-command'])
                self.assertEqual(exit_code, 2)  # argparse error code
            except SystemExit as e:
                self.assertEqual(e.code, 2)  # argparse error code
    
    def test_run_with_exception(self):
        """例外発生時のテスト"""
        with patch.object(self.cli, '_run_interactive', side_effect=Exception("Test exception")):
            exit_code = self.cli.run([])
            self.assertEqual(exit_code, 1)
    
    def test_daemon_mode_option(self):
        """デーモンモードオプションのテスト"""
        parser = self.cli.create_parser()
        args = parser.parse_args(['--daemon'])
        
        self.assertTrue(args.daemon)
    
    def test_verbose_option(self):
        """詳細モードオプションのテスト"""
        parser = self.cli.create_parser()
        args = parser.parse_args(['--verbose'])
        
        self.assertTrue(args.verbose)
    
    def test_config_option(self):
        """設定ファイルオプションのテスト"""
        parser = self.cli.create_parser()
        custom_config = '/path/to/custom/config.json'
        args = parser.parse_args(['--config', custom_config])
        
        self.assertEqual(args.config, custom_config)


class TestCLIInteractiveCommands(unittest.TestCase):
    """CLI対話型コマンドのテスト"""
    
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
        
        # 設定ファイル
        test_config = {
            "area_id": "JP13",
            "output_dir": f"{self.temp_dir}/recordings",
            "live_streaming_enabled": True
        }
        
        config_file = f"{self.temp_dir}/test_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f)
        
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
    
    def test_interactive_record_command(self):
        """対話型recordコマンドのテスト"""
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
        
        exit_code = self.cli._execute_interactive_command(['record', 'TBS', '60'])
        
        self.assertEqual(exit_code, 0)
        self.mock_recording.create_recording_job.assert_called_once()
    
    def test_interactive_schedule_command(self):
        """対話型scheduleコマンドのテスト"""
        # スケジュール追加成功をモック
        self.mock_scheduler.add_schedule.return_value = True
        
        exit_code = self.cli._execute_interactive_command([
            'schedule', 'TBS', '番組名', 
            '2024-01-01T20:00', '2024-01-01T21:00'
        ])
        
        self.assertEqual(exit_code, 0)
        self.mock_scheduler.add_schedule.assert_called_once()
    
    def test_interactive_list_stations_command(self):
        """対話型list-stationsコマンドのテスト"""
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
        
        self.mock_program_info.get_station_list.return_value = mock_stations
        
        exit_code = self.cli._execute_interactive_command(['list-stations'])
        
        self.assertEqual(exit_code, 0)
        self.mock_program_info.get_station_list.assert_called_once()
    
    def test_interactive_status_command(self):
        """対話型statusコマンドのテスト"""
        # 各種ステータス情報をモック
        self.mock_recording.get_active_jobs.return_value = []
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
        
        exit_code = self.cli._execute_interactive_command(['status'])
        
        self.assertEqual(exit_code, 0)
    
    def test_interactive_help_command(self):
        """対話型helpコマンドのテスト"""
        exit_code = self.cli._execute_interactive_command(['help'])
        
        self.assertEqual(exit_code, 0)
    
    def test_interactive_exit_command(self):
        """対話型exitコマンドのテスト"""
        exit_code = self.cli._execute_interactive_command(['exit'])
        
        self.assertEqual(exit_code, 0)
    
    def test_interactive_invalid_command(self):
        """対話型無効コマンドのテスト"""
        exit_code = self.cli._execute_interactive_command(['invalid-command'])
        
        self.assertEqual(exit_code, 1)


class TestCLILiveStreamingIntegration(unittest.TestCase):
    """CLIライブストリーミング統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        # ライブストリーミング対応設定
        test_config = {
            "area_id": "JP13",
            "output_dir": f"{self.temp_dir}/recordings",
            "live_streaming_enabled": True,
            "playlist_update_interval": 5,
            "max_concurrent_downloads": 3
        }
        
        config_file = f"{self.temp_dir}/test_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(test_config, f)
        
        self.cli = RecRadikoCLI(config_file=config_file)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_live_streaming_config_loaded(self):
        """ライブストリーミング設定読み込みテスト"""
        self.assertTrue(self.cli.config.get('live_streaming_enabled', False))
        self.assertEqual(self.cli.config.get('playlist_update_interval'), 5)
        self.assertEqual(self.cli.config.get('max_concurrent_downloads'), 3)
    
    @patch('src.live_streaming.LiveRecordingSession')
    def test_live_recording_integration(self, mock_live_session):
        """ライブ録音統合テスト"""
        # ライブ録音セッションのモック
        mock_session_instance = Mock()
        mock_live_session.return_value = mock_session_instance
        
        # RecordingManagerのモック
        with patch.object(self.cli, 'recording_manager') as mock_recording:
            mock_job = RecordingJob(
                id="live_test_job",
                station_id="TBS",
                program_title="ライブテスト",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(minutes=30),
                output_path=f"{self.temp_dir}/live_test.mp3"
            )
            mock_recording.create_recording_job.return_value = mock_job
            
            # ライブ録音コマンド実行
            exit_code = self.cli._execute_interactive_command(['record', 'TBS', '30'])
            
            self.assertEqual(exit_code, 0)
            mock_recording.create_recording_job.assert_called_once()


if __name__ == '__main__':
    unittest.main()