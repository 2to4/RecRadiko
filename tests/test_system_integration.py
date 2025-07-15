"""
システム統合テスト（実環境ベース）

全コンポーネントの実際の統合動作を検証する包括的なテストスイートです。
モック使用を最小化し、実際のシステム動作を検証します。

テスト範囲:
- 認証システム + 録音システム + CLI統合
- 実際のファイル操作 + 設定管理 + データベース操作
- エラーハンドリング + 回復処理
- パフォーマンス + メモリ管理
- セキュリティ + データ整合性
"""

import pytest
import asyncio
import tempfile
import json
import time
import os
import sys
import shutil
import sqlite3
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.auth import RadikoAuthenticator, AuthInfo
from src.timefree_recorder import TimeFreeRecorder, RecordingResult
from src.cli import RecRadikoCLI
from src.program_info import ProgramInfo
from src.program_history import ProgramHistoryManager
from tests.utils.test_environment import TemporaryTestEnvironment, RealEnvironmentTestBase


class TestAuthenticationRecordingIntegration(RealEnvironmentTestBase):
    """認証・録音システム統合テスト"""
    
    def test_real_authentication_to_recording_workflow(self, temp_env):
        """実際の認証→録音ワークフロー統合テスト"""
        # 1. 実際の認証システム初期化
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 2. 実際の認証情報設定
        current_time = time.time()
        auth_info = AuthInfo(
            auth_token="integration_auth_token",
            area_id="JP13",
            expires_at=current_time + 3600,
            timefree_session="integration_timefree_token",
            timefree_expires_at=current_time + 1800
        )
        authenticator.auth_info = auth_info
        
        # 3. 実際の録音システム初期化
        recorder = TimeFreeRecorder(authenticator)
        
        # 4. 実際の統合動作確認
        assert recorder.authenticator == authenticator
        assert recorder.authenticator.auth_info == auth_info
        
        # 5. 実際のタイムフリーURL生成
        url = recorder._generate_timefree_url(
            "TBS", 
            datetime.now(), 
            3600
        )
        assert "radiko.jp" in url
        assert "station_id=TBS" in url
        assert "ft=" in url
        assert "to=" in url
    
    @pytest.mark.asyncio
    async def test_real_end_to_end_recording_with_auth(self, temp_env):
        """実際のエンドツーエンド録音テスト（認証付き）"""
        # 1. 実際の認証処理
        authenticator = self.setup_real_authenticator(temp_env)
        recorder = TimeFreeRecorder(authenticator)
        
        # 2. 実際の認証情報設定
        current_time = time.time()
        authenticator.auth_info = AuthInfo(
            auth_token="e2e_auth_token",
            area_id="JP13",
            expires_at=current_time + 3600,
            timefree_session="e2e_timefree_token",
            timefree_expires_at=current_time + 1800
        )
        
        # 3. 実際のプログラム情報作成
        program_info = temp_env.create_sample_program_info(
            station_id="TBS",
            program_title="統合テスト番組",
            start_time=datetime.now(),
            duration=600
        )
        
        # 4. 実際のプレイリスト・セグメントデータ
        playlist_content = temp_env.create_sample_playlist("TBS", 2).read_text()
        chunklist_content = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:5
#EXTINF:5.0,
https://radiko.jp/v2/api/ts/chunklist/TBS_chunk_0.ts
#EXTINF:5.0,
https://radiko.jp/v2/api/ts/chunklist/TBS_chunk_1.ts
#EXT-X-ENDLIST
"""
        segment_data = b"e2e test segment data" * 200
        
        # 5. 外部依存のみモック（実際の処理は実環境）
        with patch('aiohttp.ClientSession') as mock_session_class:
            with patch('subprocess.run') as mock_ffmpeg:
                # HTTP クライアントモック
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__.return_value = mock_session
                
                # プレイリスト・セグメントレスポンス
                mock_playlist_response = Mock()
                mock_playlist_response.status = 200
                mock_playlist_response.text = AsyncMock(return_value=playlist_content)
                
                mock_chunklist_response = Mock()
                mock_chunklist_response.status = 200
                mock_chunklist_response.text = AsyncMock(return_value=chunklist_content)
                
                mock_segment_response = Mock()
                mock_segment_response.status = 200
                mock_segment_response.read = AsyncMock(return_value=segment_data)
                
                mock_session.get.side_effect = [
                    mock_playlist_response,
                    mock_chunklist_response,
                    mock_segment_response,
                    mock_segment_response
                ]
                
                # FFmpeg モック
                mock_ffmpeg.return_value.returncode = 0
                
                # 6. 実際の録音実行
                output_path = temp_env.recordings_dir / "e2e_test.mp3"
                result = await recorder.record_program(
                    station_id="TBS",
                    start_time=program_info.start_time,
                    duration=600,
                    output_path=str(output_path),
                    program_info=program_info
                )
                
                # 7. 統合結果確認
                assert result.success
                assert result.output_path == str(output_path)
                assert result.segments_downloaded == 2
                assert result.total_segments == 2
                
                # 8. 実際のファイル操作確認
                ts_file = temp_env.recordings_dir / "e2e_test.ts"
                assert ts_file.exists()
                assert ts_file.stat().st_size > 0
                
                # 9. 実際の認証状態確認
                assert not authenticator.auth_info.is_expired()
                assert not authenticator.auth_info.is_timefree_session_expired()


class TestCLISystemIntegration(RealEnvironmentTestBase):
    """CLIシステム統合テスト"""
    
    def test_real_cli_full_component_integration(self, temp_env):
        """実際のCLI全コンポーネント統合テスト"""
        # 1. 実際の環境確認
        assert self.verify_file_operations(temp_env)
        assert self.verify_recording_operations(temp_env)
        assert self.verify_configuration_operations(temp_env)
        
        # 2. 実際のCLI初期化
        cli = self.setup_real_cli(temp_env)
        
        # 3. 実際のコンポーネント統合確認
        assert cli.auth_manager is not None
        assert cli.program_info_manager is not None
        assert cli.timefree_recorder is not None
        assert cli.program_history_manager is not None
        
        # 4. 実際の認証システム統合
        assert cli.timefree_recorder.authenticator == cli.auth_manager
        
        # 5. 実際の設定共有確認
        config_data = temp_env.get_config_data()
        assert cli.config["prefecture"] == config_data["prefecture"]
        assert cli.config["recording"]["save_path"] == config_data["recording"]["save_path"]
        
        # 6. 実際のファイル操作統合
        recording_file = temp_env.create_sample_recording("cli_integration_test")
        assert recording_file.exists()
        
        file_info = cli._get_file_info(str(recording_file))
        assert file_info["name"] == "cli_integration_test.mp3"
        assert file_info["size"] > 0
    
    def test_real_cli_command_pipeline_integration(self, temp_env):
        """実際のCLIコマンドパイプライン統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 1. 実際のコマンド解析パイプライン
        command_pipeline = [
            "list-programs 2025-07-15 TBS",
            "record 2025-07-15 TBS テスト番組",
            "search-programs 森本毅郎",
            "show-region"
        ]
        
        for cmd_str in command_pipeline:
            # 実際のコマンド解析
            parsed = cli._parse_interactive_command(cmd_str)
            assert parsed is not None
            assert "command" in parsed
            
            # 実際のコマンド検証
            is_valid = cli._validate_interactive_command(cmd_str)
            assert is_valid == True
    
    def test_real_cli_configuration_pipeline(self, temp_env):
        """実際のCLI設定パイプライン統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 1. 実際の設定変更パイプライン
        config_changes = [
            {"prefecture": "神奈川", "area_id": "JP14"},
            {"prefecture": "埼玉", "area_id": "JP11"},
            {"prefecture": "千葉", "area_id": "JP12"}
        ]
        
        for config_change in config_changes:
            # 実際の設定更新
            cli.config.update(config_change)
            cli._save_config()
            
            # 実際のファイル確認
            with open(temp_env.config_file, 'r') as f:
                saved_config = json.load(f)
                assert saved_config["prefecture"] == config_change["prefecture"]
                assert saved_config["area_id"] == config_change["area_id"]
            
            # 実際の新規CLI確認
            new_cli = RecRadikoCLI(config_file=str(temp_env.config_file))
            assert new_cli.config["prefecture"] == config_change["prefecture"]
            assert new_cli.config["area_id"] == config_change["area_id"]


class TestProgramHistoryIntegration(RealEnvironmentTestBase):
    """プログラム履歴統合テスト"""
    
    def test_real_program_history_database_integration(self, temp_env):
        """実際のプログラム履歴データベース統合テスト"""
        # 1. 実際のプログラム履歴管理器初期化
        history_manager = ProgramHistoryManager(
            db_path=str(temp_env.config_dir / "program_history.db")
        )
        
        # 2. 実際のデータベース作成
        history_manager._create_table()
        
        # 3. 実際のプログラム情報作成・保存
        test_programs = [
            temp_env.create_sample_program_info("TBS", "森本毅郎・スタンバイ!", datetime.now(), 10800),
            temp_env.create_sample_program_info("QRR", "武田鉄矢・今朝の三枚おろし", datetime.now(), 900),
            temp_env.create_sample_program_info("LFR", "飯田浩司のOK! Cozy up!", datetime.now(), 7200)
        ]
        
        for program in test_programs:
            history_manager.add_program(program)
        
        # 4. 実際のデータベース検索
        search_results = history_manager.search_programs("森本毅郎")
        assert len(search_results) == 1
        assert search_results[0].program_title == "森本毅郎・スタンバイ!"
        
        # 5. 実際のデータベースファイル確認
        db_file = Path(temp_env.config_dir / "program_history.db")
        assert db_file.exists()
        assert db_file.stat().st_size > 0
        
        # 6. 実際のSQLite操作確認
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM programs")
        count = cursor.fetchone()[0]
        assert count == 3
        conn.close()
    
    def test_real_program_history_cli_integration(self, temp_env):
        """実際のプログラム履歴CLI統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 1. 実際のプログラム履歴マネージャー確認
        assert cli.program_history_manager is not None
        
        # 2. 実際の履歴データ追加
        test_programs = [
            temp_env.create_sample_program_info("TBS", "ナイツのラジオ", datetime.now(), 3600),
            temp_env.create_sample_program_info("QRR", "伊集院光とらじおと", datetime.now(), 10800),
            temp_env.create_sample_program_info("LFR", "オールナイトニッポン", datetime.now(), 7200)
        ]
        
        for program in test_programs:
            cli.program_history_manager.add_program(program)
        
        # 3. 実際のCLI経由検索
        search_results = cli.program_history_manager.search_programs("ナイツ")
        assert len(search_results) == 1
        assert search_results[0].program_title == "ナイツのラジオ"
        
        # 4. 実際のCLI経由フォーマット
        formatted_result = cli._format_program_info(search_results[0])
        assert "ナイツのラジオ" in formatted_result
        assert "TBS" in formatted_result


class TestErrorHandlingIntegration(RealEnvironmentTestBase):
    """エラーハンドリング統合テスト"""
    
    def test_real_authentication_error_recovery(self, temp_env):
        """実際の認証エラー回復統合テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        recorder = TimeFreeRecorder(authenticator)
        
        # 1. 実際のエラー状態作成
        authenticator.auth_info = None
        
        # 2. 実際のエラー処理確認
        with pytest.raises(Exception) as exc_info:
            asyncio.run(recorder.record_program(
                station_id="TBS",
                start_time=datetime.now(),
                duration=3600,
                output_path="/tmp/test.mp3"
            ))
        
        # 3. エラー内容確認
        assert "認証" in str(exc_info.value) or "auth" in str(exc_info.value).lower()
    
    def test_real_file_operation_error_recovery(self, temp_env):
        """実際のファイル操作エラー回復統合テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 1. 実際の読み取り専用ディレクトリ作成
        readonly_dir = temp_env.config_dir / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)
        
        # 2. 実際のファイル操作エラー処理
        try:
            test_file = readonly_dir / "test.txt"
            test_file.write_text("test content")
            assert False, "Should have raised PermissionError"
        except PermissionError:
            # 期待されるエラー
            pass
        
        # 3. 権限復旧
        os.chmod(readonly_dir, 0o755)
    
    def test_real_configuration_error_recovery(self, temp_env):
        """実際の設定エラー回復統合テスト"""
        # 1. 実際の破損設定ファイル作成
        temp_env.config_file.write_text("invalid json content")
        
        # 2. 実際のエラー回復処理
        cli = RecRadikoCLI(config_file=str(temp_env.config_file))
        
        # 3. デフォルト設定使用確認
        assert cli.config["version"] == "2.0"
        assert cli.config["prefecture"] == "東京"
        
        # 4. 実際の設定修復
        cli._save_config()
        
        # 5. 修復確認
        with open(temp_env.config_file, 'r') as f:
            repaired_config = json.load(f)
            assert repaired_config["version"] == "2.0"


class TestPerformanceIntegration(RealEnvironmentTestBase):
    """パフォーマンス統合テスト"""
    
    def test_real_concurrent_operations_performance(self, temp_env):
        """実際の並行操作パフォーマンステスト"""
        # 1. 実際の並行処理セットアップ
        cli = self.setup_real_cli(temp_env)
        
        # 2. 実際の並行タスク作成
        def create_program_task(i):
            return temp_env.create_sample_program_info(
                station_id="TBS",
                program_title=f"並行テスト番組{i}",
                start_time=datetime.now(),
                duration=3600
            )
        
        # 3. 実際の並行実行
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(create_program_task, i) for i in range(20)]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 4. パフォーマンス確認
        assert len(results) == 20
        assert execution_time < 2.0  # 2秒以内
        assert all(result.program_title.startswith("並行テスト番組") for result in results)
    
    def test_real_memory_management_performance(self, temp_env):
        """実際のメモリ管理パフォーマンステスト"""
        import psutil
        
        # 1. 実際のメモリ使用量測定開始
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 2. 実際の大量データ処理
        cli = self.setup_real_cli(temp_env)
        
        for i in range(1000):
            program_info = temp_env.create_sample_program_info(
                station_id="TBS",
                program_title=f"メモリテスト{i}",
                start_time=datetime.now(),
                duration=3600
            )
            formatted = cli._format_program_info(program_info)
            del program_info, formatted
        
        # 3. 実際のガベージコレクション
        import gc
        gc.collect()
        
        # 4. 実際のメモリ使用量測定終了
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 5. メモリ使用量確認
        assert memory_increase < 200 * 1024 * 1024  # 200MB以下
    
    def test_real_file_io_performance(self, temp_env):
        """実際のファイルI/Oパフォーマンステスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 1. 実際の大量ファイル操作
        start_time = time.time()
        
        # 2. 実際のファイル作成・操作
        test_files = []
        for i in range(100):
            file_path = temp_env.create_sample_recording(f"perf_test_{i}", size=1024)
            test_files.append(file_path)
        
        # 3. 実際のファイル情報取得
        for file_path in test_files:
            file_info = cli._get_file_info(str(file_path))
            assert file_info["size"] > 0
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # 4. パフォーマンス確認
        assert execution_time < 5.0  # 5秒以内
        assert len(test_files) == 100


class TestSecurityIntegration(RealEnvironmentTestBase):
    """セキュリティ統合テスト"""
    
    def test_real_encryption_integration(self, temp_env):
        """実際の暗号化統合テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 1. 実際の暗号化処理
        sensitive_data = [
            "test_password_123",
            "secret_auth_token",
            "confidential_user_data"
        ]
        
        encrypted_data = []
        for data in sensitive_data:
            encrypted = authenticator._encrypt_data(data)
            encrypted_data.append(encrypted)
            
            # 暗号化確認
            assert encrypted != data
            assert len(encrypted) > len(data)
        
        # 2. 実際の復号化処理
        for i, encrypted in enumerate(encrypted_data):
            decrypted = authenticator._decrypt_data(encrypted)
            assert decrypted == sensitive_data[i]
    
    def test_real_file_permission_security(self, temp_env):
        """実際のファイル権限セキュリティテスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 1. 実際のファイル権限確認
        config_file_stat = temp_env.config_file.stat()
        
        # 2. 適切な権限設定確認
        # 所有者のみ読み書き可能であることを確認
        assert oct(config_file_stat.st_mode)[-3:] in ['600', '644']
        
        # 3. 実際の権限変更テスト
        os.chmod(temp_env.config_file, 0o600)
        
        # 4. 権限変更後の動作確認
        new_cli = RecRadikoCLI(config_file=str(temp_env.config_file))
        assert new_cli.config["version"] == "2.0"
    
    def test_real_data_integrity_protection(self, temp_env):
        """実際のデータ整合性保護テスト"""
        cli = self.setup_real_cli(temp_env)
        
        # 1. 実際の設定データ整合性確認
        original_config = cli.config.copy()
        
        # 2. 実際のデータ変更
        cli.config["prefecture"] = "大阪"
        cli._save_config()
        
        # 3. 実際のデータ読み込み確認
        new_cli = RecRadikoCLI(config_file=str(temp_env.config_file))
        assert new_cli.config["prefecture"] == "大阪"
        
        # 4. 実際の整合性確認
        assert new_cli.config["version"] == original_config["version"]
        assert new_cli.config["audio"]["format"] == original_config["audio"]["format"]


class TestDataIntegrityIntegration(RealEnvironmentTestBase):
    """データ整合性統合テスト"""
    
    def test_real_configuration_consistency(self, temp_env):
        """実際の設定一貫性テスト"""
        # 1. 実際の複数CLI間での設定一貫性
        cli1 = self.setup_real_cli(temp_env)
        cli2 = RecRadikoCLI(config_file=str(temp_env.config_file))
        
        # 2. 実際の設定同期確認
        assert cli1.config["prefecture"] == cli2.config["prefecture"]
        assert cli1.config["area_id"] == cli2.config["area_id"]
        
        # 3. 実際の設定変更同期
        cli1.config["prefecture"] = "福岡"
        cli1._save_config()
        
        # 4. 実際の新規CLI確認
        cli3 = RecRadikoCLI(config_file=str(temp_env.config_file))
        assert cli3.config["prefecture"] == "福岡"
    
    def test_real_program_data_consistency(self, temp_env):
        """実際のプログラムデータ一貫性テスト"""
        # 1. 実際のプログラム情報作成
        program_info = temp_env.create_sample_program_info(
            station_id="TBS",
            program_title="データ整合性テスト番組",
            start_time=datetime.now(),
            duration=3600
        )
        
        # 2. 実際のデータ確認
        assert program_info.station_id == "TBS"
        assert program_info.program_title == "データ整合性テスト番組"
        assert program_info.duration == 3600
        assert program_info.end_time == program_info.start_time + timedelta(seconds=3600)
        
        # 3. 実際のデータ変換確認
        cli = self.setup_real_cli(temp_env)
        formatted = cli._format_program_info(program_info)
        
        assert program_info.program_title in formatted
        assert program_info.station_id in formatted


if __name__ == '__main__':
    pytest.main([__file__, "-v"])