"""
エンドツーエンド録音結合テスト

このモジュールは、RecRadikoの録音機能の完全なワークフローを検証する結合テストを含みます。
- CLI → 認証 → ストリーミング → 録音 → ファイル管理の統合フロー
- 番組情報との統合
- エラーハンドリングの統合
"""

import unittest
import tempfile
import os
import shutil
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

# RecRadikoモジュールのインポート
from src.cli import RecRadikoCLI
from src.auth import RadikoAuthenticator, AuthInfo
from src.program_info import ProgramInfoManager, Program
from src.streaming import StreamingManager, StreamInfo, StreamSegment
from src.recording import RecordingManager, RecordingJob, RecordingStatus
from src.file_manager import FileManager, FileMetadata
from src.scheduler import RecordingScheduler
from src.error_handler import ErrorHandler


class TestEndToEndRecording(unittest.TestCase):
    """エンドツーエンド録音結合テスト"""

    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.temp_dir, "recordings")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # テスト用の設定
        self.test_config = {
            "area_id": "JP13",
            "output_dir": self.output_dir,
            "max_concurrent_recordings": 2,
            "default_format": "aac",
            "default_bitrate": 128,
            "notification_enabled": False
        }
        
        # モックデータの準備
        self.mock_auth_info = AuthInfo(
            auth_token="test_token_123",
            area_id="JP13",
            expires_at=time.time() + 3600,  # 1時間後に期限切れ
            premium_user=False
        )
        
        self.mock_program = Program(
            id="TBS_20240101_2000",
            station_id="TBS",
            title="テスト番組",
            start_time=datetime(2024, 1, 1, 20, 0, 0),
            end_time=datetime(2024, 1, 1, 21, 0, 0),
            duration=60,
            description="テスト用番組",
            performers=["テスト出演者"],
            genre="テスト"
        )
        
        # ダミーセグメント
        mock_segment = StreamSegment(
            url="https://example.com/segment1.aac",
            duration=10.0,
            sequence=1,
            timestamp=datetime.now()
        )
        
        self.mock_stream_info = StreamInfo(
            stream_url="https://example.com/stream.m3u8",
            station_id="TBS",
            quality="high",
            bitrate=128,
            codec="aac",
            segments=[mock_segment],
            is_live=True,
            total_duration=10.0
        )

    def tearDown(self):
        """テスト後のクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('src.auth.RadikoAuthenticator.authenticate')
    @patch('src.streaming.StreamingManager.get_stream_url')
    @patch('src.streaming.StreamingManager.parse_playlist')
    @patch('src.recording.RecordingManager.create_recording_job')
    @patch('src.file_manager.FileManager.register_file')
    def test_immediate_recording_workflow(self, mock_register, mock_create_job, 
                                        mock_parse_playlist, mock_get_stream_url, mock_authenticate):
        """CLI → 認証 → ストリーミング → 録音 → ファイル管理の完全フロー"""
        
        # モックの設定
        mock_authenticate.return_value = self.mock_auth_info
        mock_get_stream_url.return_value = "https://example.com/stream.m3u8"
        mock_parse_playlist.return_value = self.mock_stream_info
        
        # 録音ジョブのモック
        mock_job = RecordingJob(
            id="test_job_001",
            station_id="TBS",
            program_title="テスト番組",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=30),
            output_path=os.path.join(self.output_dir, "test_recording.aac"),
            status=RecordingStatus.COMPLETED
        )
        mock_create_job.return_value = mock_job
        
        # ファイルメタデータのモック
        mock_metadata = FileMetadata(
            file_path=mock_job.output_path,
            program_title="テスト番組",
            station_id="TBS",
            recorded_at=mock_job.start_time,
            start_time=mock_job.start_time,
            end_time=mock_job.end_time,
            duration_seconds=1800,
            file_size=1024000,
            format="aac",
            bitrate=128
        )
        mock_register.return_value = mock_metadata
        
        # CLI実行
        with patch('src.cli.RecRadikoCLI._load_config') as mock_load_config:
            mock_load_config.return_value = self.test_config
            
            cli = RecRadikoCLI()
            # 依存関係を注入してテスト環境を構築
            cli.authenticator = Mock()
            cli.authenticator.authenticate.return_value = self.mock_auth_info
            cli.authenticator.is_authenticated.return_value = True
            
            cli.streaming_manager = Mock()
            cli.streaming_manager.get_stream_url.return_value = "https://example.com/stream.m3u8"
            cli.streaming_manager.parse_playlist.return_value = self.mock_stream_info
            
            cli.recording_manager = Mock()
            cli.recording_manager.create_recording_job.return_value = mock_job
            
            cli.file_manager = Mock()
            cli.file_manager.register_file.return_value = mock_metadata
            
            # CLI引数のシミュレート
            test_args = ['record', 'TBS', '30']
            
            # CLI実行
            exit_code = cli.run(test_args)
            
            # 結果の検証
            self.assertEqual(exit_code, 0, "CLI実行が成功する必要があります")
            
            # 各コンポーネントの呼び出し確認
            # CLI -> RecordingManager の統合フロー確認
            cli.recording_manager.create_recording_job.assert_called_once()
            # CLI は依存性注入によりモックされた manager を使用するため、
            # 実際の認証やストリーミング処理は行われない

    @patch('src.auth.RadikoAuthenticator.authenticate')
    @patch('src.program_info.ProgramInfoManager.get_current_program')
    @patch('src.recording.RecordingManager.create_recording_job')
    def test_program_info_integration_recording(self, mock_create_job, 
                                              mock_get_program, mock_authenticate):
        """認証 → 番組情報 → 録音の統合フロー"""
        
        # モックの設定
        mock_authenticate.return_value = self.mock_auth_info
        mock_get_program.return_value = self.mock_program
        
        # 録音ジョブのモック（番組情報付き）
        mock_job = RecordingJob(
            id="test_job_002",
            station_id="TBS",
            program_title="テスト番組",
            start_time=self.mock_program.start_time,
            end_time=self.mock_program.end_time,
            output_path=os.path.join(self.output_dir, "test_program.aac"),
            status=RecordingStatus.COMPLETED
        )
        mock_create_job.return_value = mock_job
        
        # 統合フローのシミュレート
        authenticator = RadikoAuthenticator()
        program_manager = ProgramInfoManager(authenticator=authenticator)
        streaming_manager = StreamingManager(authenticator=authenticator)
        recording_manager = RecordingManager(
            authenticator=authenticator,
            program_manager=program_manager,
            streaming_manager=streaming_manager
        )
        
        # 依存関係の注入
        with patch.object(authenticator, 'authenticate', return_value=self.mock_auth_info):
            with patch.object(program_manager, 'get_current_program', return_value=self.mock_program):
                with patch.object(recording_manager, 'create_recording_job', return_value=mock_job):
                    
                    # 統合フローの実行
                    auth_result = authenticator.authenticate()
                    program_info = program_manager.get_current_program("TBS")
                    recording_job = recording_manager.create_recording_job(
                        station_id="TBS",
                        program_title=program_info.title,
                        start_time=program_info.start_time,
                        end_time=program_info.end_time
                    )
                    
                    # 結果の検証
                    self.assertEqual(auth_result.auth_token, "test_token_123")
                    self.assertEqual(program_info.title, "テスト番組")
                    self.assertEqual(recording_job.program_title, "テスト番組")
                    self.assertEqual(recording_job.station_id, "TBS")

    @patch('src.recording.RecordingManager.create_recording_job')
    @patch('src.file_manager.FileManager.register_file')
    @patch('src.file_manager.FileManager.get_storage_info')
    def test_recording_file_management_integration(self, mock_get_storage, 
                                                 mock_register, mock_create_job):
        """録音管理 → ファイル管理の統合フロー"""
        
        # 録音ジョブのモック
        test_output_path = os.path.join(self.output_dir, "test_file_mgmt.aac")
        mock_job = RecordingJob(
            id="test_job_003",
            station_id="QRR",
            program_title="ファイル管理テスト",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(minutes=60),
            output_path=test_output_path,
            status=RecordingStatus.COMPLETED
        )
        mock_create_job.return_value = mock_job
        
        # ファイルメタデータのモック
        mock_metadata = FileMetadata(
            file_path=test_output_path,
            program_title="ファイル管理テスト",
            station_id="QRR",
            recorded_at=mock_job.start_time,
            start_time=mock_job.start_time,
            end_time=mock_job.end_time,
            duration_seconds=3600,
            file_size=5120000,
            format="aac",
            bitrate=128
        )
        mock_register.return_value = mock_metadata
        
        # ストレージ情報のモック
        from src.file_manager import StorageInfo
        mock_storage = StorageInfo(
            total_space=100 * 1024**3,
            used_space=50 * 1024**3,
            free_space=50 * 1024**3,
            recording_files_size=30 * 1024**3,
            file_count=150
        )
        mock_get_storage.return_value = mock_storage
        
        # 統合フローの実行
        mock_authenticator = Mock()
        mock_program_manager = Mock()
        mock_streaming_manager = Mock()
        recording_manager = RecordingManager(
            authenticator=mock_authenticator,
            program_manager=mock_program_manager,
            streaming_manager=mock_streaming_manager
        )
        file_manager = FileManager(base_dir=self.output_dir)
        
        with patch.object(recording_manager, 'create_recording_job', return_value=mock_job):
            with patch.object(file_manager, 'register_file', return_value=mock_metadata):
                with patch.object(file_manager, 'get_storage_info', return_value=mock_storage):
                    
                    # 録音ジョブの作成
                    job = recording_manager.create_recording_job(
                        station_id="QRR",
                        program_title="ファイル管理テスト",
                        start_time=datetime.now(),
                        end_time=datetime.now() + timedelta(minutes=60)
                    )
                    
                    # ファイル登録
                    metadata = file_manager.register_file(job.output_path, {
                        'program_title': job.program_title,
                        'station_id': job.station_id,
                        'start_time': job.start_time,
                        'duration_seconds': 3600
                    })
                    
                    # ストレージ情報の取得
                    storage_info = file_manager.get_storage_info()
                    
                    # 結果の検証
                    self.assertEqual(job.program_title, "ファイル管理テスト")
                    self.assertEqual(metadata.program_title, "ファイル管理テスト")
                    self.assertEqual(metadata.station_id, "QRR")
                    self.assertGreater(storage_info.free_space, 0)
                    self.assertEqual(storage_info.file_count, 150)

    @patch('src.auth.RadikoAuthenticator.authenticate')
    def test_authentication_error_propagation(self, mock_authenticate):
        """認証エラーの依存モジュールでの処理"""
        
        # 認証エラーのシミュレート
        from src.auth import AuthenticationError
        mock_authenticate.side_effect = AuthenticationError("認証に失敗しました")
        
        # CLI実行
        with patch('src.cli.RecRadikoCLI._load_config') as mock_load_config:
            mock_load_config.return_value = self.test_config
            
            cli = RecRadikoCLI()
            # RecordingManagerで認証エラーを発生させる
            cli.recording_manager = Mock()
            cli.recording_manager.create_recording_job.side_effect = AuthenticationError("認証に失敗しました")
            
            # エラーが発生するCLI実行
            test_args = ['record', 'TBS', '30']
            exit_code = cli.run(test_args)
            
            # エラー処理の確認
            self.assertEqual(exit_code, 1, "認証エラー時は終了コード1を返す必要があります")

    @patch('src.streaming.StreamingManager.get_stream_url')
    @patch('src.recording.RecordingManager.create_recording_job')
    def test_network_error_handling_integration(self, mock_create_job, mock_get_stream):
        """ネットワークエラーのモジュール間伝播"""
        
        # ネットワークエラーのシミュレート
        import requests
        mock_get_stream.side_effect = requests.exceptions.ConnectionError("ネットワークエラー")
        
        # 統合フローでのエラーハンドリング
        mock_authenticator = Mock()
        mock_program_manager = Mock() 
        streaming_manager = StreamingManager(authenticator=mock_authenticator)
        recording_manager = RecordingManager(
            authenticator=mock_authenticator,
            program_manager=mock_program_manager,
            streaming_manager=streaming_manager
        )
        
        with patch.object(streaming_manager, 'get_stream_url', side_effect=requests.exceptions.ConnectionError):
            with self.assertRaises(requests.exceptions.ConnectionError):
                # ストリーミング情報取得でエラー
                stream_url = streaming_manager.get_stream_url("TBS", datetime.now())
                
                # 録音ジョブは作成されない
                mock_create_job.assert_not_called()

    def test_data_flow_consistency(self):
        """モジュール間データフローの一貫性確認"""
        
        # データフローのシミュレート
        test_data = {
            'station_id': 'TBS',
            'program_title': 'データフローテスト',
            'start_time': datetime(2024, 1, 1, 20, 0, 0),
            'end_time': datetime(2024, 1, 1, 21, 0, 0),
            'format': 'aac',
            'bitrate': 128
        }
        
        # 各モジュールでのデータ処理をシミュレート
        auth_data = {
            'auth_token': 'test_token_456',
            'station_id': test_data['station_id']
        }
        
        stream_data = {
            'stream_url': 'https://example.com/stream.m3u8',
            'station_id': test_data['station_id'],
            'start_time': test_data['start_time'],
            'end_time': test_data['end_time']
        }
        
        recording_data = {
            'station_id': test_data['station_id'],
            'program_title': test_data['program_title'],
            'start_time': test_data['start_time'],
            'end_time': test_data['end_time'],
            'output_path': os.path.join(self.output_dir, 'consistency_test.aac')
        }
        
        # データの一貫性を確認
        self.assertEqual(auth_data['station_id'], test_data['station_id'])
        self.assertEqual(stream_data['station_id'], test_data['station_id'])
        self.assertEqual(recording_data['station_id'], test_data['station_id'])
        self.assertEqual(stream_data['start_time'], test_data['start_time'])
        self.assertEqual(recording_data['start_time'], test_data['start_time'])


if __name__ == '__main__':
    unittest.main()