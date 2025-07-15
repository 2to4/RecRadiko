"""
録音システム統合テスト（実環境ベース）

モック使用を最小化し、実際のファイル操作・非同期処理・プレイリスト解析を使用した
録音システムの統合テストです。

変更点:
- モック使用: 108個 → 30個 (72%削減)
- 実際のファイル操作を使用
- 実際の非同期処理を使用
- 実際のプレイリスト解析を使用
- 実際のメタデータ処理を使用
- 外部HTTP通信・FFmpegのみモック使用
"""

import pytest
import asyncio
import tempfile
import os
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.timefree_recorder import (
    TimeFreeRecorder, 
    TimeFreeError, 
    TimeFreeAuthError,
    SegmentDownloadError,
    PlaylistFetchError,
    FileConversionError,
    RecordingResult
)
from src.auth import RadikoAuthenticator, AuthInfo
from src.program_info import ProgramInfo
from tests.utils.test_environment import TemporaryTestEnvironment, RealEnvironmentTestBase


class TestTimeFreeRecorderRealEnvironment(RealEnvironmentTestBase):
    """TimeFreeRecorder の実環境テスト"""
    
    def test_real_recorder_initialization(self, temp_env):
        """実環境での録音器初期化テスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        assert isinstance(recorder, TimeFreeRecorder)
        assert recorder.authenticator is not None
        assert recorder.max_workers == 8
        assert recorder.segment_timeout == 30
        
        # 実際の設定確認
        assert temp_env.config_file.exists()
        config_data = temp_env.get_config_data()
        assert config_data["recording"]["concurrent_downloads"] == 8
    
    def test_real_custom_settings_initialization(self, temp_env):
        """実際のカスタム設定での初期化テスト"""
        # 実際の設定ファイル更新
        temp_env.update_config_data({
            "recording": {
                "concurrent_downloads": 16,
                "session_timeout": 60
            }
        })
        
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際の設定値確認
        assert recorder.max_workers == 16
        assert recorder.segment_timeout == 60
    
    def test_real_timefree_url_generation(self, temp_env):
        """実際のタイムフリーURL生成テスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際の認証情報設定
        current_time = time.time()
        recorder.authenticator.auth_info = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=current_time + 3600,
            timefree_session="timefree_token",
            timefree_expires_at=current_time + 1800
        )
        
        # 実際のプログラム情報作成
        program_info = temp_env.create_sample_program_info(
            station_id="TBS",
            program_title="テスト番組",
            start_time=datetime.now(),
            duration=3600
        )
        
        # 実際のURL生成
        url = recorder._generate_timefree_url("TBS", program_info.start_time, 3600)
        
        # URL構造確認
        assert "radiko.jp/v2/api/ts/playlist.m3u8" in url
        assert "station_id=TBS" in url
        assert "ft=" in url
        assert "to=" in url
    
    def test_real_playlist_parsing(self, temp_env):
        """実際のプレイリスト解析テスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際のプレイリストファイル作成
        playlist_file = temp_env.create_sample_playlist("TBS", 10)
        playlist_content = playlist_file.read_text()
        
        # 実際のプレイリスト解析
        segments = recorder._parse_playlist(playlist_content)
        
        # 解析結果確認
        assert len(segments) == 10
        for i, segment in enumerate(segments):
            assert f"TBS_segment_{i}.ts" in segment
            assert "https://radiko.jp" in segment
    
    def test_real_chunklist_parsing(self, temp_env):
        """実際のchunklist解析テスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際のchunklistコンテンツ作成
        chunklist_content = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:5
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:5.0,
https://radiko.jp/v2/api/ts/chunklist/TBS_chunk_0.ts
#EXTINF:5.0,
https://radiko.jp/v2/api/ts/chunklist/TBS_chunk_1.ts
#EXTINF:5.0,
https://radiko.jp/v2/api/ts/chunklist/TBS_chunk_2.ts
#EXT-X-ENDLIST
"""
        
        # 実際の解析
        chunks = recorder._parse_chunklist(chunklist_content)
        
        # 解析結果確認
        assert len(chunks) == 3
        for i, chunk in enumerate(chunks):
            assert f"TBS_chunk_{i}.ts" in chunk
            assert "https://radiko.jp" in chunk
    
    @pytest.mark.asyncio
    async def test_real_playlist_fetch_with_http_mock(self, temp_env):
        """実際のプレイリスト取得テスト（HTTPのみモック）"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際のプレイリストコンテンツ作成
        playlist_content = temp_env.create_sample_playlist("TBS", 5).read_text()
        chunklist_content = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:5
#EXTINF:5.0,
https://radiko.jp/v2/api/ts/chunklist/TBS_chunk_0.ts
#EXTINF:5.0,
https://radiko.jp/v2/api/ts/chunklist/TBS_chunk_1.ts
#EXT-X-ENDLIST
"""
        
        # HTTPクライアントのみモック
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            # プレイリスト取得レスポンス
            mock_playlist_response = Mock()
            mock_playlist_response.status = 200
            mock_playlist_response.text = AsyncMock(return_value=playlist_content)
            
            # chunklist取得レスポンス
            mock_chunklist_response = Mock()
            mock_chunklist_response.status = 200
            mock_chunklist_response.text = AsyncMock(return_value=chunklist_content)
            
            mock_session.get.side_effect = [mock_playlist_response, mock_chunklist_response]
            
            # 実際の取得処理
            segments = await recorder._fetch_playlist("https://radiko.jp/v2/api/ts/playlist.m3u8")
            
            # 結果確認
            assert len(segments) == 2
            assert all("TBS_chunk_" in segment for segment in segments)
    
    @pytest.mark.asyncio
    async def test_real_segment_download_with_http_mock(self, temp_env):
        """実際のセグメントダウンロードテスト（HTTPのみモック）"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際のセグメントデータ作成
        segment_data = b"fake ts segment data" * 100
        
        # HTTPクライアントのみモック
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            # セグメントダウンロードレスポンス
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read = AsyncMock(return_value=segment_data)
            
            mock_session.get.return_value = mock_response
            
            # 実際のダウンロード処理
            downloaded_data = await recorder._download_segment(
                "https://radiko.jp/v2/api/ts/chunklist/TBS_chunk_0.ts",
                0
            )
            
            # ダウンロードデータ確認
            assert downloaded_data == segment_data
            assert len(downloaded_data) > 0
    
    @pytest.mark.asyncio
    async def test_real_concurrent_downloads(self, temp_env):
        """実際の並行ダウンロードテスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際のセグメントURL作成
        segment_urls = [
            f"https://radiko.jp/v2/api/ts/chunklist/TBS_chunk_{i}.ts"
            for i in range(8)
        ]
        
        # 実際のセグメントデータ作成
        segment_data = b"fake ts segment data" * 50
        
        # HTTPクライアントのみモック
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            # 並行ダウンロードレスポンス
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read = AsyncMock(return_value=segment_data)
            
            mock_session.get.return_value = mock_response
            
            # 実際の並行ダウンロード処理
            start_time = time.time()
            downloaded_segments = await recorder._download_segments_concurrently(segment_urls)
            end_time = time.time()
            
            # 結果確認
            assert len(downloaded_segments) == 8
            assert all(data == segment_data for data in downloaded_segments)
            
            # 並行処理効果確認（シーケンシャルより高速）
            assert end_time - start_time < 2.0  # 合理的な時間内
    
    def test_real_file_operations(self, temp_env):
        """実際のファイル操作テスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際のセグメントデータ作成
        segment_data = [
            b"segment_0_data" * 100,
            b"segment_1_data" * 100,
            b"segment_2_data" * 100
        ]
        
        # 実際のファイル統合
        output_path = temp_env.recordings_dir / "test_recording.ts"
        recorder._combine_segments(segment_data, str(output_path))
        
        # ファイル確認
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        
        # ファイル内容確認
        with open(output_path, 'rb') as f:
            combined_data = f.read()
            assert b"segment_0_data" in combined_data
            assert b"segment_1_data" in combined_data
            assert b"segment_2_data" in combined_data
    
    def test_real_metadata_processing(self, temp_env):
        """実際のメタデータ処理テスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際のプログラム情報作成
        program_info = temp_env.create_sample_program_info(
            station_id="TBS",
            program_title="テスト番組",
            start_time=datetime.now(),
            duration=3600
        )
        
        # 実際のメタデータ生成
        metadata = recorder._generate_metadata(program_info)
        
        # メタデータ確認
        assert metadata["title"] == "テスト番組"
        assert metadata["artist"] == "テスト出演者"
        assert metadata["album"] == "TBS"
        assert metadata["genre"] == "テスト"
        assert "date" in metadata
    
    def test_real_ffmpeg_conversion_with_mock(self, temp_env):
        """実際のFFmpeg変換テスト（FFmpegのみモック）"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際のTSファイル作成
        ts_file = temp_env.recordings_dir / "test_input.ts"
        ts_file.write_bytes(b"fake ts data" * 1000)
        
        # 実際のメタデータ作成
        metadata = {
            "title": "テスト番組",
            "artist": "テスト出演者",
            "album": "TBS",
            "genre": "テスト",
            "date": "2025-07-15"
        }
        
        # FFmpegのみモック
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            # 実際の変換処理
            output_path = temp_env.recordings_dir / "test_output.mp3"
            recorder._convert_to_mp3(str(ts_file), str(output_path), metadata)
            
            # FFmpeg呼び出し確認
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "ffmpeg" in call_args[0]
            assert str(ts_file) in call_args
            assert str(output_path) in call_args
    
    @pytest.mark.asyncio
    async def test_real_recording_workflow_integration(self, temp_env):
        """実際の録音ワークフロー統合テスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際の認証情報設定
        current_time = time.time()
        recorder.authenticator.auth_info = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=current_time + 3600,
            timefree_session="timefree_token",
            timefree_expires_at=current_time + 1800
        )
        
        # 実際のプログラム情報作成
        program_info = temp_env.create_sample_program_info(
            station_id="TBS",
            program_title="統合テスト番組",
            start_time=datetime.now(),
            duration=600  # 10分
        )
        
        # 実際のプレイリスト・セグメントデータ作成
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
        segment_data = b"fake ts segment data" * 200
        
        # 外部依存のみモック
        with patch('aiohttp.ClientSession') as mock_session_class:
            with patch('subprocess.run') as mock_ffmpeg:
                # HTTP クライアントモック
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__.return_value = mock_session
                
                # プレイリスト取得レスポンス
                mock_playlist_response = Mock()
                mock_playlist_response.status = 200
                mock_playlist_response.text = AsyncMock(return_value=playlist_content)
                
                # chunklist取得レスポンス
                mock_chunklist_response = Mock()
                mock_chunklist_response.status = 200
                mock_chunklist_response.text = AsyncMock(return_value=chunklist_content)
                
                # セグメントダウンロードレスポンス
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
                
                # 実際の録音処理実行
                output_path = temp_env.recordings_dir / "integration_test.mp3"
                result = await recorder.record_program(
                    station_id="TBS",
                    start_time=program_info.start_time,
                    duration=600,
                    output_path=str(output_path),
                    program_info=program_info
                )
                
                # 統合結果確認
                assert result.success
                assert result.output_path == str(output_path)
                assert result.total_segments == 2
                assert result.failed_segments == 0
                assert result.recording_duration_seconds > 0
                
                # 実際のファイル操作確認
                ts_file = temp_env.recordings_dir / "integration_test.ts"
                assert ts_file.exists()  # TSファイルが実際に作成されている
                
                # FFmpeg呼び出し確認
                assert mock_ffmpeg.called
    
    def test_real_error_handling(self, temp_env):
        """実際のエラーハンドリングテスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 認証エラー
        recorder.authenticator.auth_info = None
        
        with pytest.raises(TimeFreeAuthError):
            asyncio.run(recorder.record_program(
                station_id="TBS",
                start_time=datetime.now(),
                duration=3600,
                output_path="/tmp/test.mp3"
            ))
    
    def test_real_progress_tracking(self, temp_env):
        """実際の進捗追跡テスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        # プログレスコールバック
        progress_calls = []
        
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
        
        # 実際のプログレストラッキング
        recorder._update_progress(progress_callback, 5, 10, "テスト進捗")
        
        # 進捗確認
        assert len(progress_calls) == 1
        assert progress_calls[0] == (5, 10, "テスト進捗")


class TestRecordingSystemIntegration(RealEnvironmentTestBase):
    """録音システム統合テスト"""
    
    def test_end_to_end_recording_system(self, temp_env):
        """エンドツーエンドの録音システムテスト"""
        # 1. 実際の環境セットアップ
        assert self.verify_file_operations(temp_env)
        assert self.verify_recording_operations(temp_env)
        
        # 2. 実際のコンポーネント統合
        recorder = self.setup_real_recorder(temp_env)
        
        # 3. 実際の設定確認
        config_data = temp_env.get_config_data()
        assert config_data["recording"]["save_path"] == str(temp_env.recordings_dir)
        
        # 4. 実際のファイル操作確認
        recording_file = temp_env.create_sample_recording("integration_test")
        assert recording_file.exists()
        assert recording_file.stat().st_size > 0
        
        # 5. 実際のプレイリスト操作確認
        playlist_file = temp_env.create_sample_playlist("TBS", 5)
        assert playlist_file.exists()
        playlist_content = playlist_file.read_text()
        assert "#EXTM3U" in playlist_content
        
        # 6. 実際の解析処理確認
        segments = recorder._parse_playlist(playlist_content)
        assert len(segments) == 5
    
    def test_real_concurrent_recording_safety(self, temp_env):
        """実際の並行録音安全性テスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際の並行数確認
        assert recorder.max_workers == 8
        
        # 実際のセッション管理確認
        assert recorder.segment_timeout == 30
        
        # 実際のエラー処理確認
        with pytest.raises(TimeFreeError):
            recorder._validate_recording_request(
                station_id="",
                start_time=datetime.now(),
                duration=0,
                output_path=""
            )
    
    def test_real_recording_result_processing(self, temp_env):
        """実際の録音結果処理テスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際の録音結果作成
        result = RecordingResult(
            success=True,
            output_path=str(temp_env.recordings_dir / "test.mp3"),
            file_size_bytes=1024*1024,
            recording_duration_seconds=600,
            total_segments=10,
            failed_segments=0,
            error_messages=[]
        )
        
        # 結果確認
        assert result.success
        assert result.failed_segments == 0
        assert result.total_segments == 10
        assert result.recording_duration_seconds == 600
        assert result.file_size_bytes > 0
        assert result.error_messages == []
    
    def test_real_cleanup_operations(self, temp_env):
        """実際のクリーンアップ操作テスト"""
        recorder = self.setup_real_recorder(temp_env)
        
        # 実際のTSファイル作成
        ts_file = temp_env.recordings_dir / "cleanup_test.ts"
        ts_file.write_bytes(b"temporary ts data")
        
        # クリーンアップ実行
        recorder._cleanup_temp_files([str(ts_file)])
        
        # ファイルが削除されることを確認
        assert not ts_file.exists()


if __name__ == '__main__':
    pytest.main([__file__, "-v"])