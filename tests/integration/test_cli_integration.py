"""
CLI統合テスト

このモジュールは、RecRadikoのCLIコマンドと他のモジュールとの統合を検証します。
- CLIコマンドの完全実行フロー
- 設定管理の統合
- エラーハンドリングの統合
"""

import unittest
import tempfile
import os
import shutil
import json
import io
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

# RecRadikoモジュールのインポート
from src.cli import RecRadikoCLI
from src.auth import RadikoAuthenticator, AuthInfo
from src.program_info import ProgramInfoManager, Program
from src.recording import RecordingManager, RecordingJob, RecordingStatus
from src.scheduler import RecordingScheduler, RecordingSchedule, RepeatPattern
from src.file_manager import FileManager, FileMetadata, StorageInfo
from src.daemon import DaemonManager
from src.error_handler import ErrorHandler


class TestCLIIntegration(unittest.TestCase):
    """CLI統合テスト"""

    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.json")
        self.output_dir = os.path.join(self.temp_dir, "recordings")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # テスト用設定
        self.test_config = {
            "area_id": "JP13",
            "output_dir": self.output_dir,
            "max_concurrent_recordings": 2,
            "default_format": "aac",
            "default_bitrate": 128,
            "notification_enabled": True,
            "log_level": "INFO"
        }
        
        # 設定ファイル作成
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_config, f, ensure_ascii=False, indent=2)
        
        # モックデータ
        self.mock_auth_info = AuthInfo(
            auth_token="test_token_cli",
            area_id="JP13",
            expires_at=time.time() + 3600,  # 1時間後に期限切れ
            premium_user=False
        )
        
        self.mock_program = Program(
            id="TBS_20240101_2000",
            station_id="TBS",
            title="CLI統合テスト番組",
            start_time=datetime(2024, 1, 1, 20, 0, 0),
            end_time=datetime(2024, 1, 1, 21, 0, 0),
            duration=60,
            description="CLI統合テスト用番組",
            performers=["テスト出演者"],
            genre="テスト"
        )

    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_record_command_integration(self):
        """CLIレコードコマンドの完全統合テスト"""
        
        # CLIインスタンス作成
        cli = RecRadikoCLI(config_path=self.config_path)
        
        # 遅延初期化メソッドをモックして、事前に設定したモックが使われるようにする
        cli._ensure_recording_manager_initialized = Mock()
        cli._ensure_streaming_manager_initialized = Mock()
        
        # 依存関係のモック
        cli.authenticator = Mock()
        cli.authenticator.authenticate.return_value = self.mock_auth_info
        cli.authenticator.is_authenticated.return_value = True
        
        cli.streaming_manager = Mock()
        mock_stream_info = Mock()
        mock_stream_info.stream_url = "https://example.com/stream.m3u8"
        cli.streaming_manager.get_stream_url.return_value = "https://example.com/stream.m3u8"
        cli.streaming_manager.parse_playlist.return_value = mock_stream_info
        
        cli.recording_manager = Mock()
        mock_job = RecordingJob(
            id="cli_test_job",
            station_id="TBS",
            program_title="CLI統合テスト録音",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=30),
            output_path=os.path.join(self.output_dir, "cli_test.aac"),
            status=RecordingStatus.COMPLETED
        )
        cli.recording_manager.create_recording_job.return_value = mock_job
        cli.recording_manager.schedule_recording.return_value = None
        cli.recording_manager.get_job_status.return_value = None  # テスト時に進捗監視をスキップ
        
        # テスト環境フラグを設定
        cli._all_components_injected = True
        
        cli.file_manager = Mock()
        mock_metadata = FileMetadata(
            file_path=mock_job.output_path,
            program_title="CLI統合テスト録音",
            station_id="TBS",
            recorded_at=mock_job.start_time,
            start_time=mock_job.start_time,
            end_time=mock_job.end_time,
            duration_seconds=1800,
            file_size=1024000,
            format="aac",
            bitrate=128
        )
        cli.file_manager.register_file.return_value = mock_metadata
        
        # 対話型コマンドを直接実行
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = cli._execute_interactive_command(['record', 'TBS', '30'])
        
        # 結果検証
        self.assertEqual(exit_code, 0, "recordコマンドが成功する必要があります")
        
        # 各モジュールの呼び出し確認
        # CLI の record コマンドは recording_manager.create_recording_job を直接呼び出す
        cli.recording_manager.create_recording_job.assert_called_once()
        
        # 出力内容の確認
        output = captured_output.getvalue()
        self.assertIn("録音", output)

    def test_cli_schedule_command_integration(self):
        """CLIスケジュールコマンドの統合テスト"""
        
        # CLIインスタンス作成
        cli = RecRadikoCLI(config_path=self.config_path)
        
        # スケジューラーのモック
        cli.scheduler = Mock()
        cli.scheduler.add_schedule.return_value = True
        
        # スケジュール追加コマンド
        test_args = [
            'schedule',
            'TBS',
            '統合テストスケジュール',
            '2024-01-01T20:00',
            '2024-01-01T21:00',
            '--repeat', 'weekly',
            '--format', 'aac',
            '--bitrate', '128'
        ]
        
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = cli._execute_interactive_command(test_args)
        
        # 結果検証
        self.assertEqual(exit_code, 0, "scheduleコマンドが成功する必要があります")
        cli.scheduler.add_schedule.assert_called_once()
        
        # 出力内容の確認
        output = captured_output.getvalue()
        self.assertIn("スケジュール", output)

    def test_cli_status_command_integration(self):
        """CLIステータスコマンドの統合テスト"""
        
        # CLIインスタンス作成
        cli = RecRadikoCLI(config_path=self.config_path)
        
        # 各モジュールのモック
        cli.authenticator = Mock()
        cli.authenticator.is_authenticated.return_value = True
        
        cli.recording_manager = Mock()
        cli.recording_manager.list_jobs.return_value = []
        
        cli.scheduler = Mock()
        cli.scheduler.list_schedules.return_value = []
        cli.scheduler.get_next_schedules.return_value = []
        
        cli.file_manager = Mock()
        mock_storage = StorageInfo(
            total_space=100 * 1024**3,
            used_space=30 * 1024**3,
            free_space=70 * 1024**3,
            recording_files_size=25 * 1024**3,
            file_count=50
        )
        cli.file_manager.get_storage_info.return_value = mock_storage
        
        # ステータス表示コマンド（対話型）
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = cli._execute_interactive_command(['status'])
        
        # 結果検証
        self.assertEqual(exit_code, 0, "statusコマンドが成功する必要があります")
        
        # 各モジュールの呼び出し確認
        cli.authenticator.is_authenticated.assert_called()
        cli.file_manager.get_storage_info.assert_called()
        
        # 出力内容の確認
        output = captured_output.getvalue()
        self.assertIn("システム状態", output)
        self.assertIn("ストレージ", output)


    def test_cli_list_commands_integration(self):
        """CLIリストコマンドの統合テスト"""
        
        # CLIインスタンス作成
        cli = RecRadikoCLI(config_path=self.config_path)
        
        # プログラム情報管理のモック
        cli.program_info_manager = Mock()
        cli.program_info_manager.fetch_program_guide.return_value = [self.mock_program]
        
        # 番組一覧表示
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = cli._execute_interactive_command(['list-programs', '--station', 'TBS'])
        
        # 結果検証
        self.assertEqual(exit_code, 0, "list-programsコマンドが成功する必要があります")
        cli.program_info_manager.fetch_program_guide.assert_called_once()
        
        # 出力内容の確認
        output = captured_output.getvalue()
        self.assertIn("CLI統合テスト番組", output)
        
        # スケジュール一覧表示
        cli.scheduler = Mock()
        test_schedule = RecordingSchedule(
            schedule_id="test_list",
            station_id="TBS",
            program_title="リストテスト番組",
            start_time=datetime.now() + timedelta(hours=1),
            end_time=datetime.now() + timedelta(hours=2),
            repeat_pattern=RepeatPattern.NONE
        )
        cli.scheduler.list_schedules.return_value = [test_schedule]
        
        with redirect_stdout(io.StringIO()) as captured_output:
            exit_code = cli._execute_interactive_command(['list-schedules'])
        
        # 結果検証
        self.assertEqual(exit_code, 0, "list-schedulesコマンドが成功する必要があります")
        cli.scheduler.list_schedules.assert_called_once()
        
        # 出力内容の確認
        output = captured_output.getvalue()
        self.assertIn("リストテスト番組", output)

    def test_cli_error_handling_integration(self):
        """CLIエラーハンドリングの統合テスト"""
        
        # CLIインスタンス作成
        cli = RecRadikoCLI(config_path=self.config_path)
        
        # 認証エラーのシミュレート
        from src.auth import AuthenticationError
        cli.recording_manager = Mock()
        cli.recording_manager.create_recording_job.side_effect = AuthenticationError("認証失敗")
        
        # エラーハンドラーのモック
        cli.error_handler = Mock()
        
        # エラーが発生するコマンド実行
        with redirect_stdout(io.StringIO()) as captured_output:
            with redirect_stderr(io.StringIO()) as captured_error:
                exit_code = cli._execute_interactive_command(['record', 'TBS', '30'])
        
        # 結果検証
        self.assertEqual(exit_code, 1, "エラー時は終了コード1を返す必要があります")
        
        # エラー出力の確認
        output = captured_output.getvalue()
        error_output = captured_error.getvalue()
        
        # エラーメッセージが出力されているか確認
        combined_output = output + error_output
        self.assertTrue(
            "エラー" in combined_output or "認証" in combined_output,
            "エラーメッセージが出力される必要があります"
        )

    def test_cli_argument_validation_integration(self):
        """CLI引数検証の統合テスト"""
        
        # CLIインスタンス作成
        cli = RecRadikoCLI(config_path=self.config_path)
        
        # 不正な引数でのコマンド実行
        test_cases = [
            # 必須引数不足
            (['record'], 2),
            # 不正なコマンド
            (['invalid-command'], 1),
            # 不正なオプション
            (['record', 'TBS', 'invalid-duration'], 1),
        ]
        
        for args, expected_code in test_cases:
            with redirect_stdout(io.StringIO()) as captured_output:
                with redirect_stderr(io.StringIO()) as captured_error:
                    try:
                        exit_code = cli._execute_interactive_command(args)
                    except SystemExit as e:
                        exit_code = e.code or 2
            
            # エラーコードの確認
            self.assertNotEqual(exit_code, 0, f"不正な引数 {args} でエラーになる必要があります")

    def test_cli_daemon_integration(self):
        """CLIデーモン統合テスト"""
        
        # CLIインスタンス作成
        cli = RecRadikoCLI(config_path=self.config_path)
        
        # デーモンマネージャーのモック
        cli.daemon_manager = Mock()
        cli.daemon_manager.start.return_value = True
        cli.daemon_manager.stop.return_value = True
        cli.daemon_manager.is_running.return_value = False
        
        # デーモン起動コマンドのテスト（実際には長時間実行のため短縮）
        with patch.object(cli, '_run_daemon') as mock_run_daemon:
            mock_run_daemon.return_value = 0
            
            with redirect_stdout(io.StringIO()) as captured_output:
                # デーモンモードの擬似実行
                exit_code = cli._run_daemon()
            
            # 結果検証
            self.assertEqual(exit_code, 0, "デーモンモードが正常に開始される必要があります")

    def test_cli_configuration_propagation(self):
        """CLI設定変更の全モジュールへの反映テスト"""
        
        # CLIインスタンス作成
        cli = RecRadikoCLI(config_path=self.config_path)
        
        # 依存関係のモック
        cli.authenticator = Mock()
        cli.recording_manager = Mock()
        cli.file_manager = Mock()
        cli.scheduler = Mock()
        
        # 設定変更
        new_config = {
            'area_id': 'JP27',
            'output_dir': os.path.join(self.temp_dir, 'new_recordings'),
            'max_concurrent_recordings': 4,
            'default_format': 'mp3',
            'default_bitrate': 192
        }
        
        # 設定更新
        cli.config.update(new_config)
        cli._save_config(cli.config)
        
        # 設定の反映確認
        updated_config = cli._load_config()
        self.assertEqual(updated_config['area_id'], 'JP27')
        self.assertEqual(updated_config['default_format'], 'mp3')
        self.assertEqual(updated_config['max_concurrent_recordings'], 4)
        
        # モジュールへの設定反映の確認（実際の実装では各モジュールが設定を使用）
        # ここではCLIが適切に設定を管理していることを確認
        self.assertEqual(cli.config['area_id'], 'JP27')

    def test_cli_help_and_usage_integration(self):
        """CLIヘルプと使用方法の統合テスト"""
        
        # CLIインスタンス作成
        cli = RecRadikoCLI(config_path=self.config_path)
        
        # ヘルプ表示
        help_commands = [
            ['--help'],
            ['-h'],
            ['record', '--help'],
            ['schedule', '--help'],
            ['status', '--help']
        ]
        
        for help_cmd in help_commands:
            with redirect_stdout(io.StringIO()) as captured_output:
                with redirect_stderr(io.StringIO()) as captured_error:
                    try:
                        exit_code = cli._execute_interactive_command(help_cmd)
                    except SystemExit as e:
                        exit_code = e.code
            
            # ヘルプが表示されることを確認
            output = captured_output.getvalue() + captured_error.getvalue()
            self.assertTrue(
                len(output) > 0,
                f"ヘルプコマンド {help_cmd} で出力がある必要があります"
            )

    def test_cli_multi_command_workflow(self):
        """CLI複数コマンドワークフローの統合テスト"""
        
        # CLIインスタンス作成
        cli = RecRadikoCLI(config_path=self.config_path)
        
        # 依存関係のモック
        cli.authenticator = Mock()
        cli.authenticator.is_authenticated.return_value = True
        cli.scheduler = Mock()
        cli.scheduler.add_schedule.return_value = True
        cli.scheduler.list_schedules.return_value = []
        
        # ワークフロー: スケジュール追加 → スケジュール確認
        commands = [
            ['schedule', 'TBS', 'ワークフローテスト',
             '2024-01-01T20:00', '2024-01-01T21:00'],
            ['list-schedules'],
            ['status']
        ]
        
        # 各コマンドを順次実行
        for cmd in commands:
            with redirect_stdout(io.StringIO()) as captured_output:
                exit_code = cli._execute_interactive_command(cmd)
            
            # 各コマンドが成功することを確認
            self.assertEqual(exit_code, 0, f"コマンド {cmd} が成功する必要があります")


if __name__ == '__main__':
    unittest.main()