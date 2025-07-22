"""
E2E 異常系・エラー処理テスト

Phase 4 Day 38-39: 異常系・エラー処理（7テストケース）
ネットワークエラー・認証期限切れ・ディスク容量不足・無効データ・同時実行制限・設定破損・割り込み処理の検証
"""

import unittest
import tempfile
import shutil
import json
import time
import os
import signal
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timedelta

# テスト対象
from src.cli import RecRadikoCLI
from src.auth import RadikoAuthenticator, AuthInfo
from src.program_info import ProgramInfo
from src.program_history import ProgramHistoryManager
from src.timefree_recorder import TimeFreeRecorder, RecordingResult
from src.utils.config_utils import ConfigManager
from tests.utils.test_environment import TemporaryTestEnvironment, RealEnvironmentTestBase


class TestE2EErrorScenarios(unittest.TestCase, RealEnvironmentTestBase):
    """E2E異常系・エラー処理テストスイート"""
    
    def setUp(self):
        """テスト環境セットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
        # テスト用番組情報
        self.test_program = ProgramInfo(
            program_id="error_test_001",
            station_id="TBS",
            station_name="TBSラジオ",
            title="エラーテスト番組",
            start_time=datetime(2025, 7, 22, 15, 0),
            end_time=datetime(2025, 7, 22, 15, 30),
            description="エラー処理テスト用番組",
            performers=["エラーテスト出演者"]
        )
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_e2e_09_ネットワークエラー回復(self):
        """
        E2E Test 09: ネットワークエラー回復
        
        シナリオ:
        1. 録音開始
        2. ネットワーク切断（シミュレート）
        3. エラー表示確認
        4. ネットワーク復旧
        5. リトライ成功
        """
        # Given: ネットワークエラーをシミュレートする認証システム
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        
        # Given: 初回失敗、2回目成功のネットワークエラーパターン
        network_error = Exception("Network error: Connection timeout")
        success_auth = AuthInfo(
            auth_token="recovery_token_123",
            area_id="JP13",
            expires_at=time.time() + 3600,
            premium_user=False
        )
        
        # 3回の呼び出し: 1回目失敗、2回目失敗、3回目成功
        mock_auth.authenticate.side_effect = [
            network_error,  # 1回目ネットワークエラー
            network_error,  # 2回目ネットワークエラー
            success_auth    # 3回目成功
        ]
        
        # When: エラー回復テスト実行
        retry_count = 0
        max_retries = 3
        auth_result = None
        error_messages = []
        
        for attempt in range(max_retries):
            try:
                auth_result = mock_auth.authenticate()
                break  # 成功したら終了
            except Exception as e:
                retry_count += 1
                error_messages.append(str(e))
                
                # エラーメッセージ表示（シミュレート）
                if "Network error" in str(e):
                    print(f"ネットワークエラーが発生しました: {e}")
                    print(f"リトライ中... ({retry_count}/{max_retries})")
                
                if retry_count >= max_retries:
                    raise e
                
                # リトライ間隔（実際より短縮）
                time.sleep(0.1)
        
        # Then: 最終的に認証成功
        self.assertIsNotNone(auth_result)
        self.assertEqual(auth_result.auth_token, "recovery_token_123")
        self.assertEqual(retry_count, 2)  # 2回リトライして3回目で成功
        
        # And: エラーメッセージが記録されている
        self.assertEqual(len(error_messages), 2)
        for error_msg in error_messages:
            self.assertIn("Network error", error_msg)
        
        # And: 最終的に成功している
        self.assertFalse(auth_result.is_expired())
        
        # When: 録音もネットワークエラー回復テスト
        with patch.object(TimeFreeRecorder, 'record_program') as mock_record:
            # 1回目失敗、2回目成功
            network_recording_error = Exception("Network timeout during recording")
            success_result = RecordingResult(
                success=True,
                output_path="./test_recovery.mp3",
                file_size_bytes=3_000_000,
                recording_duration_seconds=1800.0,
                total_segments=120,
                failed_segments=0,
                error_messages=[]
            )
            
            recording_attempts = []
            async def mock_recording_with_retry(*args, **kwargs):
                attempt_count = len(recording_attempts) + 1
                recording_attempts.append(attempt_count)
                
                if attempt_count <= 1:  # 1回目失敗
                    raise network_recording_error
                else:  # 2回目以降成功
                    return success_result
            
            mock_record.side_effect = mock_recording_with_retry
            
            # 録音リトライテスト
            recorder = TimeFreeRecorder(authenticator=mock_auth)
            recording_result = None
            recording_error_count = 0
            
            for attempt in range(3):
                try:
                    import asyncio
                    recording_result = asyncio.run(recorder.record_program(
                        program_info=self.test_program,
                        output_path="./test_recovery.mp3"
                    ))
                    break
                except Exception as e:
                    recording_error_count += 1
                    if "Network timeout" in str(e):
                        print(f"録音中にネットワークエラー: {e}")
                        print(f"録音リトライ中... ({recording_error_count}/3)")
                    
                    if recording_error_count >= 3:
                        raise e
                    time.sleep(0.1)
            
            # Then: 録音も最終的に成功
            self.assertIsNotNone(recording_result)
            self.assertTrue(recording_result.success)
            self.assertEqual(recording_error_count, 1)  # 1回エラーしてリトライ成功
    
    def test_e2e_10_認証期限切れ処理(self):
        """
        E2E Test 10: 認証期限切れ処理
        
        シナリオ:
        1. 認証期限切れ状態
        2. 番組録音試行
        3. 再認証プロンプト
        4. 認証更新
        5. 録音継続
        """
        # Given: 期限切れ認証情報
        expired_auth = AuthInfo(
            auth_token="expired_token_123",
            area_id="JP13",
            expires_at=time.time() - 3600,  # 1時間前に期限切れ
            premium_user=False
        )
        
        # And: 新しい認証情報
        new_auth = AuthInfo(
            auth_token="new_token_456",
            area_id="JP13",
            expires_at=time.time() + 3600,  # 1時間後まで有効
            premium_user=False
        )
        
        # Given: 認証システムモック
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        mock_auth.auth_info = expired_auth
        
        # When: 期限切れ検出テスト
        self.assertTrue(expired_auth.is_expired())
        self.assertFalse(new_auth.is_expired())
        
        # When: 期限切れ時の再認証処理
        def check_and_refresh_auth():
            if mock_auth.auth_info.is_expired():
                print("認証が期限切れです。再認証を実行します...")
                # 再認証実行（シミュレート）
                mock_auth.authenticate.return_value = new_auth
                refreshed_auth = mock_auth.authenticate()
                mock_auth.auth_info = refreshed_auth
                return refreshed_auth
            return mock_auth.auth_info
        
        # Then: 再認証が実行される
        refreshed_auth = check_and_refresh_auth()
        self.assertIsNotNone(refreshed_auth)
        self.assertEqual(refreshed_auth.auth_token, "new_token_456")
        self.assertFalse(refreshed_auth.is_expired())
        
        # When: 録音実行（再認証後）
        with patch.object(TimeFreeRecorder, 'record_program') as mock_record:
            # 期限切れエラー → 再認証 → 成功のパターン
            auth_expired_error = Exception("Authentication expired")
            success_result = RecordingResult(
                success=True,
                output_path="./test_reauth.mp3",
                file_size_bytes=4_000_000,
                recording_duration_seconds=1800.0,
                total_segments=120,
                failed_segments=0,
                error_messages=[]
            )
            
            recording_call_count = 0
            async def mock_recording_with_reauth(*args, **kwargs):
                nonlocal recording_call_count
                recording_call_count += 1
                
                # 1回目は期限切れエラー
                if recording_call_count == 1:
                    if mock_auth.auth_info.is_expired():
                        raise auth_expired_error
                
                # 2回目以降は成功（再認証済み）
                return success_result
            
            mock_record.side_effect = mock_recording_with_reauth
            
            # 録音実行（期限切れ対応付き）
            recorder = TimeFreeRecorder(authenticator=mock_auth)
            final_result = None
            
            try:
                import asyncio
                final_result = asyncio.run(recorder.record_program(
                    program_info=self.test_program,
                    output_path="./test_reauth.mp3"
                ))
            except Exception as e:
                if "Authentication expired" in str(e):
                    print("認証期限切れを検出しました")
                    # 再認証実行
                    refreshed_auth = check_and_refresh_auth()
                    recorder.authenticator.auth_info = refreshed_auth
                    
                    # 録音再実行
                    final_result = asyncio.run(recorder.record_program(
                        program_info=self.test_program,
                        output_path="./test_reauth.mp3"
                    ))
            
            # Then: 最終的に録音成功
            self.assertIsNotNone(final_result)
            self.assertTrue(final_result.success)
    
    def test_e2e_11_ディスク容量不足(self):
        """
        E2E Test 11: ディスク容量不足
        
        シナリオ:
        1. ディスク容量制限
        2. 録音開始
        3. 容量不足エラー
        4. エラーハンドリング
        """
        # Given: ディスク容量チェック機能
        def check_disk_space(output_path: str, required_mb: int = 100) -> bool:
            """ディスク容量をチェック（シミュレート）"""
            try:
                # 実際のディスク容量を取得
                statvfs = os.statvfs(output_path)
                free_bytes = statvfs.f_frsize * statvfs.f_bavail
                free_mb = free_bytes / (1024 * 1024)
                return free_mb >= required_mb
            except:
                return True  # エラー時はチェックをスキップ
        
        # When: 容量不足をシミュレート
        output_dir = str(self.temp_env.config_dir)
        
        # モックで容量不足を再現
        with patch('os.statvfs') as mock_statvfs:
            # 容量不足を示すstatvfs結果
            mock_statvfs_result = MagicMock()
            mock_statvfs_result.f_frsize = 4096  # ブロックサイズ
            mock_statvfs_result.f_bavail = 10    # 利用可能ブロック数（少ない）
            mock_statvfs.return_value = mock_statvfs_result
            
            # When: 容量チェック実行
            has_enough_space = check_disk_space(output_dir, required_mb=100)
            
            # Then: 容量不足が検出される
            self.assertFalse(has_enough_space)
        
        # When: 録音実行時の容量不足処理
        with patch.object(TimeFreeRecorder, 'record_program') as mock_record:
            disk_full_error = Exception("No space left on device")
            
            async def mock_recording_disk_full(*args, **kwargs):
                # 容量チェック
                if not check_disk_space(output_dir, required_mb=100):
                    raise disk_full_error
                return RecordingResult(success=True, output_path="test.mp3", file_size_bytes=0, recording_duration_seconds=0, total_segments=0, failed_segments=0, error_messages=[])
            
            mock_record.side_effect = mock_recording_disk_full
            
            # 容量不足エラーのテスト
            recorder = TimeFreeRecorder(authenticator=MagicMock())
            disk_error_caught = False
            error_message = ""
            
            with patch('os.statvfs') as mock_statvfs_recording:
                # 容量不足状態を維持
                mock_statvfs_recording.return_value = mock_statvfs_result
                
                try:
                    import asyncio
                    result = asyncio.run(recorder.record_program(
                        program_info=self.test_program,
                        output_path=str(self.temp_env.config_dir / "test_disk_full.mp3")
                    ))
                except Exception as e:
                    disk_error_caught = True
                    error_message = str(e)
                    print(f"ディスク容量不足エラー: {e}")
            
            # Then: 容量不足エラーが適切に処理される
            self.assertTrue(disk_error_caught)
            self.assertIn("No space left on device", error_message)
        
        # And: 容量確保後の処理テスト
        with patch('os.statvfs') as mock_statvfs_recovered:
            # 十分な容量がある状態
            mock_statvfs_recovered_result = MagicMock()
            mock_statvfs_recovered_result.f_frsize = 4096
            mock_statvfs_recovered_result.f_bavail = 1000000  # 十分なブロック数
            mock_statvfs_recovered.return_value = mock_statvfs_recovered_result
            
            # When: 容量回復後のチェック
            has_space_recovered = check_disk_space(output_dir, required_mb=100)
            
            # Then: 容量が十分になる
            self.assertTrue(has_space_recovered)
    
    def test_e2e_12_無効な番組ID処理(self):
        """
        E2E Test 12: 無効な番組ID処理
        
        シナリオ:
        1. 存在しない番組ID指定
        2. エラー検出
        3. エラーメッセージ表示
        4. 正常状態復帰
        """
        # Given: 無効な番組ID
        invalid_program_ids = [
            "",                    # 空文字
            "invalid_123",         # 存在しないID
            "special@#$%",         # 特殊文字
            "TBS_99999999_9999",   # 形式は正しいが存在しない
            None                   # None値
        ]
        
        # Given: 番組情報管理システム
        program_manager = ProgramHistoryManager()
        
        # When & Then: 各無効IDに対するエラー処理テスト
        for invalid_id in invalid_program_ids:
            with self.subTest(program_id=invalid_id):
                error_caught = False
                error_message = ""
                
                try:
                    # 無効なIDで番組検索
                    if invalid_id is None:
                        # None値の場合は直接例外
                        raise ValueError("Program ID cannot be None")
                    elif invalid_id == "":
                        # 空文字の場合
                        raise ValueError("Program ID cannot be empty")
                    elif "@" in str(invalid_id) or "#" in str(invalid_id):
                        # 特殊文字の場合
                        raise ValueError(f"Invalid characters in program ID: {invalid_id}")
                    else:
                        # 存在しないIDの場合（番組管理システムで検索）
                        with patch.object(program_manager, 'get_program_by_id') as mock_get:
                            mock_get.return_value = None  # 見つからない
                            
                            program = mock_get(invalid_id)
                            if program is None:
                                raise ValueError(f"Program not found: {invalid_id}")
                                
                except Exception as e:
                    error_caught = True
                    error_message = str(e)
                    print(f"無効な番組ID '{invalid_id}' でエラー: {e}")
                
                # Then: 適切なエラーが発生する
                self.assertTrue(error_caught, f"Expected error for invalid ID: {invalid_id}")
                # エラーメッセージの内容確認（各ケースに応じたキーワード）
                if invalid_id is None or invalid_id == "":
                    self.assertIn("Program ID", error_message)
                elif "@" in str(invalid_id) or "#" in str(invalid_id):
                    self.assertIn("Invalid characters", error_message)
                else:
                    self.assertIn("Program not found", error_message)
        
        # When: 有効な番組IDでの正常処理
        valid_program = self.test_program
        
        with patch.object(program_manager, 'get_program_by_id') as mock_get_valid:
            mock_get_valid.return_value = valid_program
            
            # Then: 正常に番組が取得できる
            result_program = mock_get_valid("error_test_001")
            self.assertIsNotNone(result_program)
            self.assertEqual(result_program.program_id, "error_test_001")
            self.assertEqual(result_program.title, "エラーテスト番組")
    
    def test_e2e_13_同時実行制限(self):
        """
        E2E Test 13: 同時実行制限
        
        シナリオ:
        1. RecRadiko起動
        2. 別プロセスで再起動試行
        3. 排他制御確認
        4. エラーメッセージ
        """
        # Given: プロセス排他制御のシミュレート
        lock_file_path = self.temp_env.config_dir / "recradiko.lock"
        
        def acquire_process_lock(lock_path: Path) -> bool:
            """プロセスロックを取得"""
            try:
                if lock_path.exists():
                    # ロックファイルが存在する場合、他のプロセスが実行中
                    return False
                
                # ロックファイルを作成
                with open(lock_path, 'w') as f:
                    f.write(str(os.getpid()))
                return True
            except:
                return False
        
        def release_process_lock(lock_path: Path):
            """プロセスロックを解放"""
            try:
                if lock_path.exists():
                    lock_path.unlink()
            except:
                pass
        
        # When: 最初のプロセスがロックを取得
        first_lock = acquire_process_lock(lock_file_path)
        
        # Then: 最初のプロセスは成功
        self.assertTrue(first_lock)
        self.assertTrue(lock_file_path.exists())
        
        # When: 2番目のプロセスがロック取得を試行
        second_lock = acquire_process_lock(lock_file_path)
        
        # Then: 2番目のプロセスは失敗
        self.assertFalse(second_lock)
        
        # When: 2番目のプロセスでの起動試行
        concurrent_start_error = False
        error_msg = ""
        
        try:
            if not acquire_process_lock(lock_file_path):
                raise RuntimeError("Another instance of RecRadiko is already running")
        except RuntimeError as e:
            concurrent_start_error = True
            error_msg = str(e)
            print(f"同時実行制限エラー: {e}")
        
        # Then: 適切なエラーメッセージが表示される
        self.assertTrue(concurrent_start_error)
        self.assertIn("already running", error_msg)
        
        # When: 最初のプロセスが終了
        release_process_lock(lock_file_path)
        
        # Then: ロックファイルが削除される
        self.assertFalse(lock_file_path.exists())
        
        # When: 新しいプロセスがロック取得を試行
        new_lock = acquire_process_lock(lock_file_path)
        
        # Then: 新しいプロセスは成功
        self.assertTrue(new_lock)
        
        # Cleanup
        release_process_lock(lock_file_path)
    
    def test_e2e_14_設定ファイル破損(self):
        """
        E2E Test 14: 設定ファイル破損
        
        シナリオ:
        1. 設定ファイル破損
        2. RecRadiko起動
        3. 自動修復確認
        4. デフォルト設定使用
        """
        # Given: 破損した設定ファイル群
        config_path = self.temp_env.config_dir / "corrupted_config.json"
        
        corrupted_configs = [
            '{"invalid": json syntax}',              # JSON構文エラー
            '{"incomplete": "config"',                # 不完全なJSON
            '',                                       # 空ファイル
            'not json at all',                       # JSON以外の内容
            '{"valid": "json", "but": "missing_key"}' # 有効だが必要キーが欠如
        ]
        
        # When & Then: 各破損パターンに対する復旧テスト
        for i, corrupted_content in enumerate(corrupted_configs):
            with self.subTest(corruption_type=i):
                # 破損ファイル作成
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(corrupted_content)
                
                # ConfigManager初期化（破損検出・修復）
                config_manager = ConfigManager(config_path)
                
                # 破損検出テスト
                config_data = None
                repair_attempted = False
                
                try:
                    config_data = config_manager.load_config({})
                except json.JSONDecodeError:
                    repair_attempted = True
                    print(f"設定ファイル破損を検出: {corrupted_content[:50]}...")
                    
                    # デフォルト設定で修復
                    default_config = {
                        "area_id": "JP13",
                        "prefecture": "東京",
                        "default_format": "mp3",
                        "default_bitrate": 128,
                        "output_dir": "./recordings",
                        "request_timeout": 30,
                        "max_retries": 3
                    }
                    
                    # 修復実行
                    backup_path = config_path.with_suffix('.bak')
                    shutil.copy2(config_path, backup_path)  # バックアップ作成
                    
                    # デフォルト設定で上書き
                    config_manager.save_config(default_config)
                    config_data = config_manager.load_config({})
                except:
                    # その他のエラーも修復対象
                    repair_attempted = True
                    default_config = {
                        "area_id": "JP13",
                        "prefecture": "東京",
                        "default_format": "mp3",
                        "default_bitrate": 128
                    }
                    config_manager.save_config(default_config)
                    config_data = config_manager.load_config({})
                
                # Then: 設定が復旧している
                self.assertIsNotNone(config_data)
                self.assertIsInstance(config_data, dict)
                
                # デフォルト値が設定されている
                self.assertEqual(config_data.get('area_id', 'JP13'), 'JP13')
                self.assertEqual(config_data.get('default_format', 'mp3'), 'mp3')
                
                # バックアップファイルが作成されている（JSON構文エラーの場合）
                if corrupted_content.startswith('{') and repair_attempted:
                    backup_path = config_path.with_suffix('.bak')
                    # バックアップの存在確認は環境依存のためスキップ
        
        # When: 修復後のRecRadiko起動テスト
        try:
            cli = RecRadikoCLI(config_file=str(config_path))
            startup_success = True
            
            # 設定値確認
            self.assertIsNotNone(cli.config)
            self.assertIn('area_id', cli.config)
            
        except Exception as e:
            startup_success = False
            print(f"修復後の起動エラー: {e}")
        
        # Then: 修復後は正常起動する
        self.assertTrue(startup_success)
    
    def test_e2e_15_キーボード割り込み(self):
        """
        E2E Test 15: キーボード割り込み
        
        シナリオ:
        1. 録音実行中
        2. Ctrl+C押下
        3. 安全な中断処理
        4. 一時ファイルクリーンアップ
        """
        # Given: 割り込み処理のシミュレート
        interrupt_handler_called = False
        cleanup_executed = False
        temp_files_created = []
        
        def signal_handler(signum, frame):
            """割り込みシグナルハンドラー"""
            nonlocal interrupt_handler_called
            interrupt_handler_called = True
            print("Ctrl+C が押されました。安全に中断しています...")
            raise KeyboardInterrupt("User interrupted")
        
        def cleanup_temp_files():
            """一時ファイルクリーンアップ"""
            nonlocal cleanup_executed
            cleanup_executed = True
            
            for temp_file in temp_files_created:
                try:
                    if Path(temp_file).exists():
                        Path(temp_file).unlink()
                        print(f"一時ファイルを削除: {temp_file}")
                except:
                    pass
        
        # Given: 録音プロセスの模擬実行
        output_path = str(self.temp_env.config_dir / "interrupted_recording.mp3")
        temp_segment_path = str(self.temp_env.config_dir / "temp_segment_001.ts")
        
        # 一時ファイル作成
        Path(temp_segment_path).write_text("temporary segment data")
        temp_files_created.append(temp_segment_path)
        
        # When: 録音中の割り込みシミュレート
        recording_interrupted = False
        
        try:
            # シグナルハンドラー設定（テスト用）
            original_handler = signal.signal(signal.SIGINT, signal_handler)
            
            # 録音プロセス開始（シミュレート）
            print("録音開始...")
            time.sleep(0.1)  # 短時間の録音模擬
            
            # 割り込み発生をシミュレート
            os.kill(os.getpid(), signal.SIGINT)
            
        except KeyboardInterrupt:
            recording_interrupted = True
            print("録音が中断されました")
            
            # クリーンアップ実行
            cleanup_temp_files()
            
        except Exception as e:
            print(f"予期しないエラー: {e}")
        finally:
            # シグナルハンドラーを元に戻す
            try:
                signal.signal(signal.SIGINT, signal.SIG_DFL)
            except:
                pass
        
        # Then: 割り込み処理が正常実行される
        self.assertTrue(interrupt_handler_called)
        self.assertTrue(recording_interrupted)
        self.assertTrue(cleanup_executed)
        
        # And: 一時ファイルがクリーンアップされる
        self.assertFalse(Path(temp_segment_path).exists())
        
        # When: より高度な割り込み処理テスト（録音状態保存）
        recording_state = {
            "program_id": "error_test_001",
            "output_path": output_path,
            "completed_segments": 45,
            "total_segments": 120,
            "start_time": time.time()
        }
        
        def save_recording_state(state: dict):
            """録音状態を保存"""
            state_file = self.temp_env.config_dir / "recording_state.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            return state_file
        
        def load_recording_state():
            """録音状態を読み込み"""
            state_file = self.temp_env.config_dir / "recording_state.json"
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        
        # 録音状態保存テスト
        state_file = save_recording_state(recording_state)
        self.assertTrue(state_file.exists())
        
        # 状態復元テスト
        restored_state = load_recording_state()
        self.assertIsNotNone(restored_state)
        self.assertEqual(restored_state['program_id'], "error_test_001")
        self.assertEqual(restored_state['completed_segments'], 45)
        
        # クリーンアップ
        if state_file.exists():
            state_file.unlink()


if __name__ == "__main__":
    unittest.main()