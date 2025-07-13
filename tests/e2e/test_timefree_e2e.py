"""
タイムフリー専用E2Eテスト

このテストモジュールはタイムフリー専用システムのエンドツーエンドテストを提供します。
- タイムフリー録音の完全ワークフロー
- CLI対話型モードでのタイムフリー操作
- エラーシナリオとリカバリー
- パフォーマンス・信頼性テスト
"""

import pytest
import asyncio
import tempfile
import subprocess
import time
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.cli import RecRadikoCLI
from src.auth import RadikoAuthenticator, AuthInfo
from src.timefree_recorder import TimeFreeRecorder, RecordingResult
from src.program_history import ProgramHistoryManager
from src.program_info import ProgramInfo


class TestTimeFreeE2EWorkflows:
    """タイムフリーE2Eワークフローテスト"""
    
    @pytest.fixture
    def temp_workspace(self):
        """一時作業スペース"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def mock_authenticator(self):
        """モック認証器"""
        auth = Mock(spec=RadikoAuthenticator)
        auth_info = AuthInfo(
            auth_token="e2e_test_token_789",
            key_length=16,
            key_offset=0,
            area_id="JP13",
            premium=False
        )
        auth.get_valid_auth_info.return_value = auth_info
        return auth
    
    @pytest.fixture
    def sample_programs(self):
        """サンプル番組データ"""
        base_time = datetime(2025, 7, 10, 6, 0, 0)
        return [
            ProgramInfo(
                program_id="TBS_20250710_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=base_time,
                end_time=base_time + timedelta(hours=2, minutes=30),
                description="朝の情報番組",
                performers=["森本毅郎", "寺島尚正"],
                genre="情報番組",
                is_timefree_available=True,
                timefree_end_time=base_time + timedelta(days=7)
            ),
            ProgramInfo(
                program_id="QRR_20250710_060000",
                station_id="QRR",
                station_name="文化放送",
                title="おはよう寺ちゃん",
                start_time=base_time,
                end_time=base_time + timedelta(hours=2, minutes=30),
                description="朝の情報番組",
                performers=["寺島尚正"],
                genre="情報番組",
                is_timefree_available=True,
                timefree_end_time=base_time + timedelta(days=7)
            )
        ]
    
    @pytest.mark.e2e
    def test_complete_timefree_recording_workflow(self, temp_workspace, mock_authenticator, sample_programs):
        """完全なタイムフリー録音ワークフロー"""
        # 設定ファイル作成
        config_file = Path(temp_workspace) / "config.json"
        config = {
            "area_id": "JP13",
            "output_dir": str(Path(temp_workspace) / "recordings"),
            "default_format": "mp3"
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        # CLI初期化
        cli = RecRadikoCLI(config_file=str(config_file))
        
        # モックコンポーネント設定
        mock_history = Mock(spec=ProgramHistoryManager)
        mock_recorder = Mock(spec=TimeFreeRecorder)
        
        # 番組検索結果をモック
        mock_history.search_programs.return_value = [sample_programs[0]]
        mock_history.get_program_by_id.return_value = sample_programs[0]
        
        # 録音結果をモック（成功）
        output_path = Path(temp_workspace) / "recordings" / "TBS_20250710_森本毅郎・スタンバイ!.mp3"
        recording_result = RecordingResult(
            success=True,
            output_path=str(output_path),
            file_size_bytes=2048000,  # 2MB
            recording_duration_seconds=180.0,
            total_segments=36,  # 3分×12セグメント/分
            failed_segments=0,
            error_messages=[]
        )
        
        with patch('asyncio.run', return_value=recording_result):
            cli.program_history_manager = mock_history
            cli.timefree_recorder = mock_recorder
            
            # Step 1: 番組表取得
            mock_history.get_programs_by_date.return_value = sample_programs
            
            import io
            from contextlib import redirect_stdout
            
            with redirect_stdout(io.StringIO()) as captured_output:
                result1 = cli._execute_interactive_command([
                    'list-programs', '2025-07-10', '--station', 'TBS'
                ])
            
            assert result1 == 0
            output1 = captured_output.getvalue()
            assert "森本毅郎・スタンバイ!" in output1
            assert "TBSラジオ" in output1
            
            # Step 2: 番組検索
            with redirect_stdout(io.StringIO()) as captured_output:
                result2 = cli._execute_interactive_command([
                    'search-programs', '森本毅郎'
                ])
            
            assert result2 == 0
            output2 = captured_output.getvalue()
            assert "森本毅郎・スタンバイ!" in output2
            
            # Step 3: 番組名指定録音
            with redirect_stdout(io.StringIO()) as captured_output:
                result3 = cli._execute_interactive_command([
                    'record', '2025-07-10', 'TBS', '森本毅郎・スタンバイ!'
                ])
            
            assert result3 == 0
            output3 = captured_output.getvalue()
            assert "録音開始" in output3
            assert "録音完了" in output3
            
            # Step 4: 番組ID指定録音
            with redirect_stdout(io.StringIO()) as captured_output:
                result4 = cli._execute_interactive_command([
                    'record-id', 'TBS_20250710_060000'
                ])
            
            assert result4 == 0
            output4 = captured_output.getvalue()
            assert "録音開始" in output4
            assert "録音完了" in output4
            
            # 全てのステップが成功し、期待されるメソッドが呼ばれたことを確認
            mock_history.get_programs_by_date.assert_called()
            mock_history.search_programs.assert_called()
            mock_history.get_program_by_id.assert_called()
    
    @pytest.mark.e2e
    def test_timefree_error_scenarios(self, temp_workspace, mock_authenticator):
        """タイムフリーエラーシナリオテスト"""
        # 設定ファイル作成
        config_file = Path(temp_workspace) / "config.json"
        config = {"area_id": "JP13", "output_dir": str(Path(temp_workspace) / "recordings")}
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        cli = RecRadikoCLI(config_file=str(config_file))
        
        # モックコンポーネント設定
        mock_history = Mock(spec=ProgramHistoryManager)
        mock_recorder = Mock(spec=TimeFreeRecorder)
        
        cli.program_history_manager = mock_history
        cli.timefree_recorder = mock_recorder
        
        import io
        from contextlib import redirect_stdout
        
        # エラーシナリオ1: 番組が見つからない
        mock_history.search_programs.return_value = []
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result1 = cli._execute_interactive_command([
                'record', '2025-07-10', 'TBS', '存在しない番組'
            ])
        
        assert result1 == 1
        output1 = captured_output.getvalue()
        assert "番組が見つかりません" in output1
        
        # エラーシナリオ2: 番組ID が無効
        mock_history.get_program_by_id.return_value = None
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result2 = cli._execute_interactive_command([
                'record-id', 'INVALID_ID'
            ])
        
        assert result2 == 1
        output2 = captured_output.getvalue()
        assert "番組が見つかりません" in output2
        
        # エラーシナリオ3: API呼び出し失敗
        mock_history.get_programs_by_date.side_effect = Exception("API エラー")
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result3 = cli._execute_interactive_command([
                'list-programs', '2025-07-10'
            ])
        
        assert result3 == 1
        output3 = captured_output.getvalue()
        assert "エラー" in output3
        
        # エラーシナリオ4: 検索エラー
        mock_history.search_programs.side_effect = Exception("検索エラー")
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result4 = cli._execute_interactive_command([
                'search-programs', 'キーワード'
            ])
        
        assert result4 == 1
        output4 = captured_output.getvalue()
        assert "エラー" in output4
    
    @pytest.mark.e2e
    def test_timefree_interactive_session(self, temp_workspace, mock_authenticator, sample_programs):
        """タイムフリー対話型セッションテスト"""
        # 設定ファイル作成
        config_file = Path(temp_workspace) / "config.json"
        config = {"area_id": "JP13", "output_dir": str(Path(temp_workspace) / "recordings")}
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        cli = RecRadikoCLI(config_file=str(config_file))
        
        # モックコンポーネント設定
        mock_history = Mock(spec=ProgramHistoryManager)
        mock_recorder = Mock(spec=TimeFreeRecorder)
        
        cli.program_history_manager = mock_history
        cli.timefree_recorder = mock_recorder
        
        import io
        from contextlib import redirect_stdout
        
        # 対話型コマンドの確認
        timefree_commands = [
            'list-programs', 'record', 'record-id', 'search-programs',
            'list-stations', 'show-region', 'list-prefectures',
            'status', 'help', 'exit', 'quit'
        ]
        
        for command in timefree_commands:
            assert command in cli.INTERACTIVE_COMMANDS
        
        # 削除されたコマンドが含まれていないことを確認
        removed_commands = ['schedule', 'list-schedules', 'list-recordings']
        for command in removed_commands:
            assert command not in cli.INTERACTIVE_COMMANDS
        
        # ヘルプコマンドテスト
        with redirect_stdout(io.StringIO()) as captured_output:
            result = cli._execute_interactive_command(['help'])
        
        assert result == 0
        help_output = captured_output.getvalue()
        
        # タイムフリー専用ヘルプ内容の確認
        assert "タイムフリー専用" in help_output
        assert "過去7日間" in help_output
        assert "list-programs" in help_output
        assert "record" in help_output
        assert "record-id" in help_output
        assert "search-programs" in help_output
        
        # 削除されたコマンドがヘルプに表示されないことを確認
        assert "schedule" not in help_output
        assert "list-schedules" not in help_output
    
    @pytest.mark.e2e
    def test_timefree_performance_characteristics(self, temp_workspace, mock_authenticator):
        """タイムフリーパフォーマンス特性テスト"""
        # 大量番組データでのパフォーマンステスト
        large_program_list = []
        base_time = datetime(2025, 7, 10, 0, 0, 0)
        
        # 1日分の番組データ（1時間ごと24番組）を生成
        for hour in range(24):
            program = ProgramInfo(
                program_id=f"TEST_{hour:02d}_20250710_{hour:02d}0000",
                station_id="TEST",
                station_name="テスト放送局",
                title=f"テスト番組 {hour:02d}時",
                start_time=base_time + timedelta(hours=hour),
                end_time=base_time + timedelta(hours=hour+1),
                description=f"{hour}時台の番組",
                performers=[f"出演者{hour}"],
                genre="テスト",
                is_timefree_available=True,
                timefree_end_time=base_time + timedelta(days=7)
            )
            large_program_list.append(program)
        
        # 設定ファイル作成
        config_file = Path(temp_workspace) / "config.json"
        config = {"area_id": "JP13", "output_dir": str(Path(temp_workspace) / "recordings")}
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        cli = RecRadikoCLI(config_file=str(config_file))
        
        # モックコンポーネント設定
        mock_history = Mock(spec=ProgramHistoryManager)
        mock_history.get_programs_by_date.return_value = large_program_list
        mock_history.search_programs.return_value = large_program_list[:5]  # 最初の5件
        
        cli.program_history_manager = mock_history
        
        import io
        from contextlib import redirect_stdout
        
        # パフォーマンステスト1: 大量番組表示
        start_time = time.time()
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result1 = cli._execute_interactive_command([
                'list-programs', '2025-07-10'
            ])
        
        list_duration = time.time() - start_time
        
        assert result1 == 0
        assert list_duration < 1.0  # 1秒以内に完了
        
        output1 = captured_output.getvalue()
        assert "テスト番組" in output1
        
        # パフォーマンステスト2: 検索処理
        start_time = time.time()
        
        with redirect_stdout(io.StringIO()) as captured_output:
            result2 = cli._execute_interactive_command([
                'search-programs', 'テスト'
            ])
        
        search_duration = time.time() - start_time
        
        assert result2 == 0
        assert search_duration < 1.0  # 1秒以内に完了
        
        output2 = captured_output.getvalue()
        assert "検索結果: 5件" in output2 or "テスト番組" in output2
    
    @pytest.mark.e2e
    def test_timefree_concurrent_operations(self, temp_workspace, mock_authenticator, sample_programs):
        """タイムフリー並行処理テスト"""
        # 設定ファイル作成
        config_file = Path(temp_workspace) / "config.json"
        config = {"area_id": "JP13", "output_dir": str(Path(temp_workspace) / "recordings")}
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        # 複数のCLIインスタンスを作成
        cli1 = RecRadikoCLI(config_file=str(config_file))
        cli2 = RecRadikoCLI(config_file=str(config_file))
        
        # モックコンポーネント設定
        for cli in [cli1, cli2]:
            mock_history = Mock(spec=ProgramHistoryManager)
            mock_recorder = Mock(spec=TimeFreeRecorder)
            
            mock_history.get_programs_by_date.return_value = sample_programs
            mock_history.search_programs.return_value = sample_programs
            
            cli.program_history_manager = mock_history
            cli.timefree_recorder = mock_recorder
        
        import io
        from contextlib import redirect_stdout
        import threading
        
        results = {}
        
        def execute_command(cli_instance, command_args, result_key):
            with redirect_stdout(io.StringIO()) as captured_output:
                result = cli_instance._execute_interactive_command(command_args)
                results[result_key] = (result, captured_output.getvalue())
        
        # 並行でコマンド実行
        threads = [
            threading.Thread(
                target=execute_command,
                args=(cli1, ['list-programs', '2025-07-10'], 'cli1_list')
            ),
            threading.Thread(
                target=execute_command,
                args=(cli2, ['search-programs', '森本毅郎'], 'cli2_search')
            )
        ]
        
        # スレッド開始・終了
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 結果確認
        assert len(results) == 2
        
        # CLI1 の結果確認
        cli1_result, cli1_output = results['cli1_list']
        assert cli1_result == 0
        assert "森本毅郎・スタンバイ!" in cli1_output
        
        # CLI2 の結果確認
        cli2_result, cli2_output = results['cli2_search']
        assert cli2_result == 0
        assert "森本毅郎・スタンバイ!" in cli2_output
    
    @pytest.mark.e2e 
    def test_timefree_data_consistency(self, temp_workspace, mock_authenticator, sample_programs):
        """タイムフリーデータ一貫性テスト"""
        # 設定ファイル作成
        config_file = Path(temp_workspace) / "config.json"
        config = {"area_id": "JP13", "output_dir": str(Path(temp_workspace) / "recordings")}
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f)
        
        cli = RecRadikoCLI(config_file=str(config_file))
        
        # モックコンポーネント設定
        mock_history = Mock(spec=ProgramHistoryManager)
        mock_recorder = Mock(spec=TimeFreeRecorder)
        
        # 一貫したデータを返すように設定
        mock_history.get_programs_by_date.return_value = sample_programs
        mock_history.search_programs.return_value = [sample_programs[0]]
        mock_history.get_program_by_id.return_value = sample_programs[0]
        
        cli.program_history_manager = mock_history
        cli.timefree_recorder = mock_recorder
        
        import io
        from contextlib import redirect_stdout
        
        # データ一貫性テスト1: 番組表と検索結果の一貫性
        with redirect_stdout(io.StringIO()) as captured_output1:
            result1 = cli._execute_interactive_command([
                'list-programs', '2025-07-10', '--station', 'TBS'
            ])
        
        with redirect_stdout(io.StringIO()) as captured_output2:
            result2 = cli._execute_interactive_command([
                'search-programs', '森本毅郎', '--station', 'TBS'
            ])
        
        assert result1 == 0
        assert result2 == 0
        
        output1 = captured_output1.getvalue()
        output2 = captured_output2.getvalue()
        
        # 両方の出力に同じ番組情報が含まれることを確認
        assert "森本毅郎・スタンバイ!" in output1
        assert "森本毅郎・スタンバイ!" in output2
        assert "TBSラジオ" in output1
        assert "TBSラジオ" in output2
        
        # データ一貫性テスト2: 番組IDと番組情報の一貫性
        with redirect_stdout(io.StringIO()) as captured_output3:
            result3 = cli._execute_interactive_command([
                'record-id', 'TBS_20250710_060000', '--format', 'mp3'
            ])
        
        # 録音処理のモック設定
        recording_result = RecordingResult(
            success=True,
            output_path=str(Path(temp_workspace) / "recordings" / "test.mp3"),
            file_size_bytes=1024000,
            recording_duration_seconds=120.0,
            total_segments=24,
            failed_segments=0,
            error_messages=[]
        )
        
        with patch('asyncio.run', return_value=recording_result):
            result3 = cli._execute_interactive_command([
                'record-id', 'TBS_20250710_060000'
            ])
        
        assert result3 == 0
        
        # 番組ID検索が正しく呼ばれることを確認
        mock_history.get_program_by_id.assert_called_with('TBS_20250710_060000')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])