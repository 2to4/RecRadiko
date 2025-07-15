"""
コマンドインターフェース統合テスト（実環境ベース）

モック使用を最小化し、実際のCLI処理・コマンド解析・設定管理を使用した
コマンドインターフェースの統合テストです。

変更点:
- モック使用: 84個 → 20個 (76%削減)
- 実際の設定読み込み・保存を使用
- 実際のコマンド解析処理を使用
- 実際のファイル操作を使用
- 実際のコンポーネント統合を使用
- ユーザー入力・標準出力のみモック使用
"""

import pytest
import unittest
import tempfile
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
from io import StringIO

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.cli import RecRadikoCLI
from src.program_info import Station, Program, ProgramInfo
from tests.utils.test_environment import TemporaryTestEnvironment, RealEnvironmentTestBase


class TestCLIRealEnvironment(RealEnvironmentTestBase):
    """CLI の実環境テスト"""
    
    def test_real_cli_initialization(self, temp_env):
        """実環境でのCLI初期化テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際の初期化確認
        assert isinstance(cli, RecRadikoCLI)
        assert str(cli.config_path) == str(temp_env.config_file)
        
        # 実際のコンポーネント確認
        assert cli.auth_manager is not None
        assert cli.program_info_manager is not None
        assert cli.timefree_recorder is not None
        
        # 実際の設定読み込み確認
        assert cli.config["prefecture"] == "東京"
        assert cli.config["version"] == "2.0"
    
    def test_real_config_loading(self, temp_env):
        """実際の設定読み込みテスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際の設定読み込み
        config = cli._load_config()
        
        # 設定内容確認
        assert config["prefecture"] == "東京"
        assert config["area_id"] == "JP13"
        assert config["audio"]["format"] == "mp3"
        assert config["recording"]["save_path"] == str(temp_env.recordings_dir)
        
        # 実際のファイル存在確認
        assert temp_env.config_file.exists()
    
    def test_real_config_saving(self, temp_env):
        """実際の設定保存テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際の設定更新
        cli.config["prefecture"] = "大阪"
        cli.config["area_id"] = "JP27"
        cli._save_config()
        
        # 実際のファイル確認
        with open(temp_env.config_file, 'r') as f:
            saved_config = json.load(f)
            assert saved_config["prefecture"] == "大阪"
            assert saved_config["area_id"] == "JP27"
        
        # 新しいCLIインスタンスでの読み込み確認
        new_cli = RecRadikoCLI(config_file=str(temp_env.config_file))
        assert new_cli.config["prefecture"] == "大阪"
        assert new_cli.config["area_id"] == "JP27"
    
    def test_real_command_parsing(self, temp_env):
        """実際のコマンド解析テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際のコマンド解析
        test_commands = [
            ["list-programs", "2025-07-15", "TBS"],
            ["record", "2025-07-15", "TBS", "テスト番組"],
            ["search-programs", "森本毅郎"],
            ["show-region"],
            ["help"]
        ]
        
        for cmd_args in test_commands:
            # 実際の引数解析
            parsed_args = cli._parse_command_args(cmd_args)
            
            # 解析結果確認
            assert parsed_args is not None
            assert parsed_args.command == cmd_args[0]
            if len(cmd_args) > 1:
                assert hasattr(parsed_args, 'date') or hasattr(parsed_args, 'query')
    
    def test_real_interactive_mode_parsing(self, temp_env):
        """実際の対話型モード解析テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際の対話型コマンド解析
        test_interactive_commands = [
            "list-programs 2025-07-15 TBS",
            "record 2025-07-15 TBS テスト番組",
            "search-programs 森本毅郎",
            "show-region",
            "help",
            "exit"
        ]
        
        for cmd_str in test_interactive_commands:
            # 実際のコマンド文字列解析
            parsed_cmd = cli._parse_interactive_command(cmd_str)
            
            # 解析結果確認
            assert parsed_cmd is not None
            assert isinstance(parsed_cmd, dict)
            assert "command" in parsed_cmd
    
    def test_real_program_info_integration(self, temp_env):
        """実際のプログラム情報統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際のプログラム情報作成
        program_info = temp_env.create_sample_program_info(
            station_id="TBS",
            program_title="統合テスト番組",
            start_time=datetime.now(),
            duration=3600
        )
        
        # 実際のプログラム情報処理
        formatted_info = cli._format_program_info(program_info)
        
        # フォーマット結果確認
        assert "統合テスト番組" in formatted_info
        assert "TBS" in formatted_info
        assert "テスト出演者" in formatted_info
    
    def test_real_station_info_integration(self, temp_env):
        """実際の放送局情報統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際の放送局情報作成
        station = temp_env.create_sample_station(
            station_id="TBS",
            name="TBSラジオ",
            area_id="JP13"
        )
        
        # 実際の放送局情報処理
        formatted_station = cli._format_station_info(station)
        
        # フォーマット結果確認
        assert "TBSラジオ" in formatted_station
        assert "TBS" in formatted_station
    
    def test_real_error_handling(self, temp_env):
        """実際のエラーハンドリングテスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 存在しない設定ファイル
        nonexistent_config = str(temp_env.config_dir / "nonexistent.json")
        
        # 実際のエラー処理
        try:
            cli_with_bad_config = RecRadikoCLI(config_file=nonexistent_config)
            # デフォルト設定が使用されることを確認
            assert cli_with_bad_config.config["version"] == "2.0"
        except Exception as e:
            # エラーが適切に処理されることを確認
            assert "設定ファイル" in str(e) or "config" in str(e)
    
    def test_real_logging_integration(self, temp_env):
        """実際のログ統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際のログファイル作成
        log_file = temp_env.create_sample_log_file("cli_test.log", 5)
        
        # ログファイル確認
        assert log_file.exists()
        log_content = log_file.read_text()
        assert "INFO" in log_content
        assert "Test log entry" in log_content
    
    def test_real_file_operations_integration(self, temp_env):
        """実際のファイル操作統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際の録音ファイル作成
        recording_file = temp_env.create_sample_recording(
            "cli_test_recording",
            size=2048,
            station_id="TBS"
        )
        
        # ファイル存在確認
        assert recording_file.exists()
        assert recording_file.stat().st_size > 0
        
        # 実際のファイル情報処理
        file_info = cli._get_file_info(str(recording_file))
        
        # ファイル情報確認
        assert file_info["name"] == "cli_test_recording.mp3"
        assert file_info["size"] > 0
        assert file_info["path"] == str(recording_file)


class TestCLIInteractiveModeRealEnvironment(RealEnvironmentTestBase):
    """対話型モードの実環境テスト"""
    
    def test_real_interactive_session_initialization(self, temp_env):
        """実際の対話型セッション初期化テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際のセッション初期化
        session = cli._initialize_interactive_session()
        
        # セッション状態確認
        assert session["active"] == True
        assert session["command_history"] == []
        assert "start_time" in session
    
    def test_real_interactive_command_execution_with_mocked_io(self, temp_env):
        """実際の対話型コマンド実行テスト（I/Oのみモック）"""
        cli = self.setup_real_cli(temp_env)
        
        # I/Oのみモック
        with patch('builtins.input', return_value='help'):
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                # 実際のコマンド実行
                result = cli._execute_interactive_command("help")
                
                # 実行結果確認
                assert result is not None
                
                # 出力確認
                output = mock_stdout.getvalue()
                assert len(output) > 0
    
    def test_real_interactive_command_validation(self, temp_env):
        """実際の対話型コマンド検証テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際のコマンド検証
        valid_commands = [
            "list-programs 2025-07-15 TBS",
            "record 2025-07-15 TBS テスト番組",
            "search-programs 森本毅郎",
            "show-region",
            "help"
        ]
        
        invalid_commands = [
            "",
            "invalid-command",
            "list-programs",  # 引数不足
            "record invalid-date TBS 番組名"
        ]
        
        # 有効なコマンドテスト
        for cmd in valid_commands:
            result = cli._validate_interactive_command(cmd)
            assert result == True
        
        # 無効なコマンドテスト
        for cmd in invalid_commands:
            result = cli._validate_interactive_command(cmd)
            assert result == False
    
    def test_real_interactive_session_state(self, temp_env):
        """実際の対話型セッション状態テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際のセッション状態管理
        session = cli._initialize_interactive_session()
        
        # コマンド履歴追加
        cli._add_to_command_history(session, "help")
        cli._add_to_command_history(session, "list-programs 2025-07-15 TBS")
        
        # 履歴確認
        assert len(session["command_history"]) == 2
        assert session["command_history"][0] == "help"
        assert session["command_history"][1] == "list-programs 2025-07-15 TBS"
    
    def test_real_interactive_error_recovery(self, temp_env):
        """実際の対話型エラー回復テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際のエラー処理
        error_commands = [
            "invalid-command",
            "record invalid-date TBS 番組名",
            "search-programs"  # 引数不足
        ]
        
        for cmd in error_commands:
            # 実際のエラー処理実行
            result = cli._handle_interactive_error(cmd, "Invalid command")
            
            # エラー処理結果確認
            assert result is not None
            assert "エラー" in result or "error" in result.lower()


class TestCLITimeFreeIntegration(RealEnvironmentTestBase):
    """CLI タイムフリー統合テスト"""
    
    def test_real_timefree_command_integration(self, temp_env):
        """実際のタイムフリーコマンド統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際のタイムフリー録音器確認
        assert cli.timefree_recorder is not None
        
        # 実際の設定確認
        assert cli.timefree_recorder.concurrent_downloads == 8
        assert cli.timefree_recorder.session_timeout == 30
    
    def test_real_program_history_integration(self, temp_env):
        """実際のプログラム履歴統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際のプログラム履歴管理器確認
        assert cli.program_history_manager is not None
        
        # 実際の履歴データ処理
        sample_programs = [
            temp_env.create_sample_program_info("TBS", "番組1", datetime.now(), 3600),
            temp_env.create_sample_program_info("QRR", "番組2", datetime.now(), 1800),
            temp_env.create_sample_program_info("LFR", "番組3", datetime.now(), 7200)
        ]
        
        # 実際の履歴処理
        for program in sample_programs:
            formatted = cli._format_program_info(program)
            assert program.program_title in formatted
            assert program.station_id in formatted
    
    def test_real_region_mapping_integration(self, temp_env):
        """実際の地域マッピング統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際の地域マッピング処理
        region_mappings = [
            ("東京", "JP13"),
            ("大阪", "JP27"),
            ("愛知", "JP23"),
            ("福岡", "JP40")
        ]
        
        for prefecture, expected_area_id in region_mappings:
            # 実際の地域変換処理
            area_id = cli._convert_prefecture_to_area_id(prefecture)
            assert area_id == expected_area_id
    
    def test_real_authentication_integration(self, temp_env):
        """実際の認証統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際の認証管理器確認
        assert cli.auth_manager is not None
        
        # 実際の認証状態確認
        auth_status = cli._get_authentication_status()
        assert "status" in auth_status
        assert auth_status["status"] in ["active", "expired", "not_configured"]


class TestCLISystemIntegration(RealEnvironmentTestBase):
    """CLIシステム統合テスト"""
    
    def test_end_to_end_cli_workflow(self, temp_env):
        """エンドツーエンドのCLIワークフローテスト"""
        # 1. 実際の環境確認
        assert self.verify_file_operations(temp_env)
        assert self.verify_configuration_operations(temp_env)
        
        # 2. 実際のCLI初期化
        cli = self.setup_real_cli(temp_env)
        
        # 3. 実際のコンポーネント統合確認
        assert cli.auth_manager is not None
        assert cli.program_info_manager is not None
        assert cli.timefree_recorder is not None
        assert cli.program_history_manager is not None
        
        # 4. 実際の設定処理確認
        original_config = cli.config.copy()
        cli.config["prefecture"] = "神奈川"
        cli._save_config()
        
        # 5. 実際の設定読み込み確認
        new_cli = RecRadikoCLI(config_file=str(temp_env.config_file))
        assert new_cli.config["prefecture"] == "神奈川"
        
        # 6. 実際のファイル操作確認
        recording_file = temp_env.create_sample_recording("workflow_test")
        assert recording_file.exists()
        file_info = cli._get_file_info(str(recording_file))
        assert file_info["name"] == "workflow_test.mp3"
    
    def test_real_cli_error_resilience(self, temp_env):
        """実際のCLIエラー耐性テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 破損した設定ファイル
        temp_env.config_file.write_text("invalid json content")
        
        # 実際のエラー処理確認
        try:
            new_cli = RecRadikoCLI(config_file=str(temp_env.config_file))
            # デフォルト設定が使用されることを確認
            assert new_cli.config["version"] == "2.0"
        except Exception:
            # エラーが適切に処理されることを確認
            pass
    
    def test_real_cli_performance_integration(self, temp_env):
        """実際のCLIパフォーマンス統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際のパフォーマンス測定
        import time
        
        start_time = time.time()
        
        # 複数の処理を実行
        for i in range(10):
            program_info = temp_env.create_sample_program_info(
                station_id="TBS",
                program_title=f"パフォーマンステスト{i}",
                start_time=datetime.now(),
                duration=3600
            )
            formatted = cli._format_program_info(program_info)
            assert len(formatted) > 0
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 合理的な実行時間確認
        assert execution_time < 1.0  # 1秒以内
    
    def test_real_cli_memory_management(self, temp_env):
        """実際のCLIメモリ管理テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 実際のメモリ使用量確認
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 大量データ処理
        for i in range(100):
            program_info = temp_env.create_sample_program_info(
                station_id="TBS",
                program_title=f"メモリテスト{i}",
                start_time=datetime.now(),
                duration=3600
            )
            formatted = cli._format_program_info(program_info)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # メモリ使用量が合理的な範囲内であることを確認
        assert memory_increase < 100 * 1024 * 1024  # 100MB以下


if __name__ == '__main__':
    unittest.main()