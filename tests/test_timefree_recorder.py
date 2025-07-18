"""
TimeFreeRecorderクラスの単体テスト

このテストモジュールはタイムフリー録音機能の品質を保証します。
- タイムフリーURL生成
- プレイリスト取得・解析
- セグメントダウンロード
- 音声変換とメタデータ埋め込み
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
# import aiofiles  # 必要に応じて後で追加

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


@pytest.fixture
def mock_authenticator():
    """モック認証器"""
    auth = Mock(spec=RadikoAuthenticator)
    auth_info = AuthInfo(
        auth_token="test_token_123",
        area_id="JP13",
        expires_at=1234567890.0,
        premium_user=False,
        timefree_session="timefree_token_123",
        timefree_expires_at=1234567890.0
    )
    auth.get_valid_auth_info.return_value = auth_info
    auth.get_timefree_playlist_url.return_value = "https://radiko.jp/v2/api/ts/playlist.m3u8?station_id=TBS&start_at=20250713120000&ft=20250713120000&to=20250713123600&type=b"
    auth.get_timefree_session.return_value = Mock()
    return auth


@pytest.fixture
def timefree_recorder(mock_authenticator):
    """TimeFreeRecorderインスタンス"""
    return TimeFreeRecorder(mock_authenticator)


@pytest.fixture
def sample_program_info():
    """サンプル番組情報"""
    start_time = datetime(2025, 7, 10, 6, 0, 0)
    end_time = datetime(2025, 7, 10, 8, 30, 0)
    
    return ProgramInfo(
        program_id="TBS_20250710_060000",
        station_id="TBS",
        station_name="TBSラジオ",
        title="森本毅郎・スタンバイ!",
        start_time=start_time,
        end_time=end_time,
        description="朝の情報番組",
        performers=["森本毅郎", "寺島尚正"],
        genre="情報番組",
        is_timefree_available=True,
        timefree_end_time=start_time + timedelta(days=7)
    )


class TestTimeFreeRecorderInit:
    """TimeFreeRecorder初期化テスト"""
    
    def test_init_with_authenticator(self, mock_authenticator):
        """認証器を指定した初期化"""
        recorder = TimeFreeRecorder(mock_authenticator)
        
        assert recorder.authenticator == mock_authenticator
        assert recorder.max_workers == 8
        assert recorder.segment_timeout == 30
        assert recorder.retry_attempts == 3
        assert recorder.chunk_size == 8192
    
    def test_init_with_custom_settings(self, mock_authenticator):
        """カスタム設定での初期化"""
        recorder = TimeFreeRecorder(mock_authenticator)
        recorder.max_workers = 16
        recorder.segment_timeout = 60
        
        assert recorder.max_workers == 16
        assert recorder.segment_timeout == 60


class TestTimeFreeUrlGeneration:
    """タイムフリーURL生成テスト"""
    
    def test_generate_timefree_url_success(self, timefree_recorder, mock_authenticator):
        """正常なURL生成（2025年仕様：直接URL生成）"""
        start_time = datetime(2025, 7, 10, 6, 0, 0)
        end_time = datetime(2025, 7, 10, 8, 30, 0)
        
        # 2025年仕様：直接URL生成のため、期待されるURL形式
        expected_url = "https://radiko.jp/v2/api/ts/playlist.m3u8?station_id=TBS&ft=20250710060000&to=20250710083000"
        
        url = timefree_recorder._generate_timefree_url("TBS", start_time, end_time)
        
        # URL形式の確認
        assert url == expected_url
        
        # 2025年仕様：認証システムメソッドは呼ばれない（直接URL生成）
        # 代わりに、URL構造の詳細検証
        assert "station_id=TBS" in url
        assert "ft=20250710060000" in url
        assert "to=20250710083000" in url
        assert "radiko.jp/v2/api/ts/playlist.m3u8" in url
    
    def test_generate_timefree_url_various_stations(self, timefree_recorder, mock_authenticator):
        """様々な放送局でのURL生成（2025年仕様：直接URL生成）"""
        start_time = datetime(2025, 7, 10, 6, 0, 0)
        end_time = datetime(2025, 7, 10, 8, 30, 0)
        
        # 複数の放送局でテスト
        stations = ["TBS", "LFR", "QRR", "RN1"]
        
        for station_id in stations:
            url = timefree_recorder._generate_timefree_url(station_id, start_time, end_time)
            
            # 各放送局のURL構造を確認
            assert f"station_id={station_id}" in url
            assert "ft=20250710060000" in url
            assert "to=20250710083000" in url
            assert "radiko.jp/v2/api/ts/playlist.m3u8" in url


class TestPlaylistFetching:
    """プレイリスト取得テスト"""
    
    @pytest.mark.asyncio
    async def test_fetch_playlist_success(self, timefree_recorder):
        """正常なプレイリスト取得（2025年Radiko 2段階プレイリスト対応）"""
        # 1段目: playlist.m3u8 (ストリーム情報) 
        mock_playlist_content = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=128000,CODECS="mp4a.40.2"
https://radiko.jp/v2/api/ts/chunklist.m3u8?station_id=TBS
"""
        
        # 2段目: chunklist.m3u8 (実際のセグメント)
        mock_chunklist_content = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:5
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:5.0,
https://radiko.jp/v2/api/ts/segment_0.aac
#EXTINF:5.0,
https://radiko.jp/v2/api/ts/segment_1.aac
#EXTINF:5.0,
https://radiko.jp/v2/api/ts/segment_2.aac
#EXT-X-ENDLIST
"""
        
        # Radiko 2段階プレイリスト対応の非同期Mock
        with patch('aiohttp.ClientSession') as mock_session_class:
            # 1段目レスポンス (playlist.m3u8)
            mock_playlist_response = Mock()
            mock_playlist_response.status = 200
            mock_playlist_response.text = AsyncMock(return_value=mock_playlist_content)
            
            # 2段目レスポンス (chunklist.m3u8)
            mock_chunklist_response = Mock()
            mock_chunklist_response.status = 200
            mock_chunklist_response.text = AsyncMock(return_value=mock_chunklist_content)
            
            # セッションとコンテキストマネージャー設定
            mock_session = Mock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            # get メソッドの戻り値を順番に設定
            mock_get_calls = [
                Mock(__aenter__=AsyncMock(return_value=mock_playlist_response), __aexit__=AsyncMock(return_value=None)),
                Mock(__aenter__=AsyncMock(return_value=mock_chunklist_response), __aexit__=AsyncMock(return_value=None))
            ]
            mock_session.get = Mock(side_effect=mock_get_calls)
            
            mock_session_class.return_value = mock_session
            
            playlist_url = "https://radiko.jp/v2/api/ts/playlist.m3u8"
            segment_urls = await timefree_recorder._fetch_playlist(playlist_url)
            
            assert len(segment_urls) == 3
            assert all(".aac" in url for url in segment_urls)
            assert all("radiko.jp" in url for url in segment_urls)
    
    @pytest.mark.asyncio
    async def test_fetch_playlist_http_error(self, timefree_recorder):
        """HTTP エラー時のプレイリスト取得"""
        with patch('aiohttp.ClientSession') as mock_session_class:
            # 404エラーレスポンス（非同期text()メソッド対応）
            mock_response = Mock()
            mock_response.status = 404
            mock_response.text = AsyncMock(return_value="404 Not Found")
            
            # コンテキストマネージャーを正しく設定
            mock_session = Mock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            mock_get = Mock()
            mock_get.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get.__aexit__ = AsyncMock(return_value=None)
            mock_session.get = Mock(return_value=mock_get)
            
            mock_session_class.return_value = mock_session
            
            playlist_url = "https://example.com/playlist.m3u8"
            
            with pytest.raises(PlaylistFetchError, match="プレイリスト取得失敗: HTTP 404"):
                await timefree_recorder._fetch_playlist(playlist_url)
    
    @pytest.mark.asyncio
    async def test_fetch_playlist_network_error(self, timefree_recorder):
        """ネットワークエラー時のプレイリスト取得"""
        with patch('aiohttp.ClientSession') as mock_session_class:
            # ネットワークエラーを発生させる
            mock_session = Mock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.get.side_effect = aiohttp.ClientError("Network error")
            
            mock_session_class.return_value = mock_session
            
            playlist_url = "https://example.com/playlist.m3u8"
            
            with pytest.raises(PlaylistFetchError, match="プレイリスト取得エラー"):
                await timefree_recorder._fetch_playlist(playlist_url)


class TestSegmentDownload:
    """セグメントダウンロードテスト"""
    
    @pytest.mark.asyncio
    async def test_download_segments_concurrent_success(self, timefree_recorder):
        """並行ダウンロード成功（適切な非同期Mock）"""
        segment_urls = [
            "https://example.com/segment_0.ts",
            "https://example.com/segment_1.ts",
            "https://example.com/segment_2.ts"
        ]
        
        segment_data = [b"data0", b"data1", b"data2"]
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            # レスポンスモック作成
            mock_responses = []
            for data in segment_data:
                mock_response = Mock()
                mock_response.status = 200
                mock_response.read = AsyncMock(return_value=data)
                mock_responses.append(mock_response)
            
            # セッションコンテキストマネージャー設定
            mock_session = Mock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            # レスポンスコンテキストマネージャー設定
            mock_get_results = []
            for resp in mock_responses:
                mock_get = Mock()
                mock_get.__aenter__ = AsyncMock(return_value=resp)
                mock_get.__aexit__ = AsyncMock(return_value=None)
                mock_get_results.append(mock_get)
            
            mock_session.get.side_effect = mock_get_results
            mock_session_class.return_value = mock_session
            
            # プログレスバーをモック
            with patch('tqdm.asyncio.tqdm') as mock_tqdm:
                mock_progress = Mock()
                mock_tqdm.return_value = mock_progress
                
                downloaded_data = await timefree_recorder._download_segments_concurrent(segment_urls)
                
                assert len(downloaded_data) == 3
                assert downloaded_data == segment_data
                assert mock_progress.update.call_count == 3
    
    @pytest.mark.asyncio
    async def test_download_segments_with_failures(self, timefree_recorder):
        """一部セグメントの失敗を含むダウンロード（適切な非同期Mock）"""
        segment_urls = [
            "https://example.com/segment_0.ts",
            "https://example.com/segment_1.ts"  # このセグメントは失敗
        ]
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            # 最初のレスポンスは成功、2番目は失敗
            mock_response_success = Mock()
            mock_response_success.status = 200
            mock_response_success.read = AsyncMock(return_value=b"data0")
            
            mock_response_fail = Mock()
            mock_response_fail.status = 404
            
            # セッションコンテキストマネージャー設定
            mock_session = Mock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            # レスポンスコンテキストマネージャー設定
            mock_get_success = Mock()
            mock_get_success.__aenter__ = AsyncMock(return_value=mock_response_success)
            mock_get_success.__aexit__ = AsyncMock(return_value=None)
            
            mock_get_fail = Mock()
            mock_get_fail.__aenter__ = AsyncMock(return_value=mock_response_fail)
            mock_get_fail.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.get.side_effect = [mock_get_success, mock_get_fail]
            mock_session_class.return_value = mock_session
            
            with patch('tqdm.asyncio.tqdm'):
                with pytest.raises(SegmentDownloadError, match="1個のセグメントダウンロードに失敗"):
                    await timefree_recorder._download_segments_concurrent(segment_urls)
    
    @pytest.mark.asyncio
    async def test_download_segments_retry_mechanism(self, timefree_recorder):
        """リトライ機構のテスト（適切な非同期Mock）"""
        # リトライ回数を2に設定してテストを高速化（1回失敗→1回成功）
        timefree_recorder.retry_attempts = 2
        
        segment_urls = ["https://example.com/segment_0.ts"]
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            # 1回目は失敗、2回目は成功
            mock_response_fail = Mock()
            mock_response_fail.status = 500
            
            mock_response_success = Mock()
            mock_response_success.status = 200
            mock_response_success.read = AsyncMock(return_value=b"data0")
            
            # セッションコンテキストマネージャー設定
            mock_session = Mock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            # レスポンスコンテキストマネージャー設定
            mock_get_fail = Mock()
            mock_get_fail.__aenter__ = AsyncMock(return_value=mock_response_fail)
            mock_get_fail.__aexit__ = AsyncMock(return_value=None)
            
            mock_get_success = Mock()
            mock_get_success.__aenter__ = AsyncMock(return_value=mock_response_success)
            mock_get_success.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.get.side_effect = [mock_get_fail, mock_get_success]
            mock_session_class.return_value = mock_session
            
            with patch('tqdm.asyncio.tqdm'):
                with patch('asyncio.sleep'):  # スリープをモック化
                    downloaded_data = await timefree_recorder._download_segments_concurrent(segment_urls)
                    
                    assert len(downloaded_data) == 1
                    assert downloaded_data[0] == b"data0"


class TestFileConversion:
    """ファイル変換テスト"""
    
    def test_combine_ts_segments_success(self, timefree_recorder):
        """TSセグメント結合成功"""
        segments = [b"segment1", b"segment2", b"segment3"]
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            timefree_recorder._combine_ts_segments(segments, temp_path)
            
            # ファイル内容確認
            with open(temp_path, 'rb') as f:
                content = f.read()
            
            assert content == b"segment1segment2segment3"
            assert os.path.getsize(temp_path) == len(b"segment1segment2segment3")
            
        finally:
            os.unlink(temp_path)
    
    def test_combine_ts_segments_empty_list(self, timefree_recorder):
        """空のセグメントリストでの結合"""
        segments = []
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            timefree_recorder._combine_ts_segments(segments, temp_path)
            
            # 空ファイルが作成されることを確認
            assert os.path.getsize(temp_path) == 0
            
        finally:
            os.unlink(temp_path)
    
    def test_combine_ts_segments_with_none_data(self, timefree_recorder):
        """Noneデータを含むセグメントでの結合"""
        segments = [b"segment1", None, b"segment3"]
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            timefree_recorder._combine_ts_segments(segments, temp_path)
            
            # Noneは無視されることを確認
            with open(temp_path, 'rb') as f:
                content = f.read()
            
            assert content == b"segment1segment3"
            
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_convert_to_target_format_mp3(self, timefree_recorder, sample_program_info):
        """MP3形式への変換テスト"""
        with tempfile.NamedTemporaryFile(suffix='.ts', delete=False) as temp_ts:
            temp_ts_path = temp_ts.name
            temp_ts.write(b"fake_ts_data")
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as output_file:
            output_path = output_file.name
        
        try:
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"", b"")
                mock_subprocess.return_value = mock_process
                
                await timefree_recorder._convert_to_target_format(
                    temp_ts_path, output_path, sample_program_info
                )
                
                # FFmpegが正しい引数で呼ばれることを確認
                mock_subprocess.assert_called_once()
                args = mock_subprocess.call_args[0]
                expected_cmd = ['ffmpeg', '-i', temp_ts_path, '-c:a', 'libmp3lame', '-b:a', '256k', '-y', output_path]
                assert args == tuple(expected_cmd)
                
        finally:
            if os.path.exists(temp_ts_path):
                os.unlink(temp_ts_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    @pytest.mark.asyncio
    async def test_convert_to_target_format_aac(self, timefree_recorder, sample_program_info):
        """AAC形式への変換テスト"""
        with tempfile.NamedTemporaryFile(suffix='.ts', delete=False) as temp_ts:
            temp_ts_path = temp_ts.name
            temp_ts.write(b"fake_ts_data")
        
        with tempfile.NamedTemporaryFile(suffix='.aac', delete=False) as output_file:
            output_path = output_file.name
        
        try:
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"", b"")
                mock_subprocess.return_value = mock_process
                
                await timefree_recorder._convert_to_target_format(
                    temp_ts_path, output_path, sample_program_info
                )
                
                # FFmpegが正しい引数で呼ばれることを確認
                args = mock_subprocess.call_args[0]
                assert '-c:a' in args
                assert 'aac' in args
                
        finally:
            if os.path.exists(temp_ts_path):
                os.unlink(temp_ts_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    @pytest.mark.asyncio
    async def test_convert_to_target_format_ffmpeg_error(self, timefree_recorder, sample_program_info):
        """FFmpegエラー時の変換テスト"""
        with tempfile.NamedTemporaryFile(suffix='.ts', delete=False) as temp_ts:
            temp_ts_path = temp_ts.name
            temp_ts.write(b"fake_ts_data")
        
        output_path = "/tmp/test_output.mp3"
        
        try:
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 1  # エラー
                mock_process.communicate.return_value = (b"", b"FFmpeg error message")
                mock_subprocess.return_value = mock_process
                
                with pytest.raises(FileConversionError, match="FFmpeg変換エラー"):
                    await timefree_recorder._convert_to_target_format(
                        temp_ts_path, output_path, sample_program_info
                    )
                
        finally:
            if os.path.exists(temp_ts_path):
                os.unlink(temp_ts_path)
    
    @pytest.mark.asyncio
    async def test_convert_to_target_format_ffmpeg_not_found(self, timefree_recorder, sample_program_info):
        """FFmpeg未インストール時の変換テスト"""
        with tempfile.NamedTemporaryFile(suffix='.ts', delete=False) as temp_ts:
            temp_ts_path = temp_ts.name
            temp_ts.write(b"fake_ts_data")
        
        output_path = "/tmp/test_output.mp3"
        
        try:
            with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError()):
                with pytest.raises(FileConversionError, match="FFmpegが見つかりません"):
                    await timefree_recorder._convert_to_target_format(
                        temp_ts_path, output_path, sample_program_info
                    )
                
        finally:
            if os.path.exists(temp_ts_path):
                os.unlink(temp_ts_path)


class TestMetadataEmbedding:
    """メタデータ埋め込みテスト"""
    
    def test_embed_metadata_mp3_success(self, timefree_recorder, sample_program_info):
        """MP3ファイルへのメタデータ埋め込み成功"""
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            file_path = temp_file.name
            temp_file.write(b"fake_mp3_data")
        
        try:
            with patch('mutagen.mp3.MP3') as mock_mp3:
                mock_audio = Mock()
                mock_audio.tags = Mock()
                mock_mp3.return_value = mock_audio
                
                with patch('mutagen.id3.TIT2') as mock_tit2, \
                     patch('mutagen.id3.TPE1') as mock_tpe1, \
                     patch('mutagen.id3.TALB') as mock_talb, \
                     patch('mutagen.id3.TDRC') as mock_tdrc, \
                     patch('mutagen.id3.TCON') as mock_tcon, \
                     patch('mutagen.id3.COMM') as mock_comm:
                    
                    timefree_recorder._embed_metadata(file_path, sample_program_info)
                    
                    # 各メタデータタグが追加されることを確認
                    mock_audio.tags.add.assert_any_call(mock_tit2.return_value)
                    mock_audio.tags.add.assert_any_call(mock_tpe1.return_value)
                    mock_audio.tags.add.assert_any_call(mock_talb.return_value)
                    mock_audio.tags.add.assert_any_call(mock_tdrc.return_value)
                    mock_audio.tags.add.assert_any_call(mock_tcon.return_value)
                    mock_audio.tags.add.assert_any_call(mock_comm.return_value)
                    
                    # ファイル保存が呼ばれることを確認
                    mock_audio.save.assert_called_once()
        
        finally:
            os.unlink(file_path)
    
    def test_embed_metadata_non_mp3_file(self, timefree_recorder, sample_program_info):
        """MP3以外のファイルでのメタデータ埋め込み"""
        with tempfile.NamedTemporaryFile(suffix='.aac', delete=False) as temp_file:
            file_path = temp_file.name
            temp_file.write(b"fake_aac_data")
        
        try:
            # MP3以外の場合はスキップされることを確認
            with patch('mutagen.mp3.MP3') as mock_mp3:
                timefree_recorder._embed_metadata(file_path, sample_program_info)
                
                # MP3コンストラクタが呼ばれないことを確認
                mock_mp3.assert_not_called()
        
        finally:
            os.unlink(file_path)
    
    def test_embed_metadata_mutagen_not_available(self, timefree_recorder, sample_program_info):
        """mutagenライブラリが利用できない場合"""
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            file_path = temp_file.name
            temp_file.write(b"fake_mp3_data")
        
        try:
            with patch('mutagen.mp3.MP3', side_effect=ImportError()):
                # ImportErrorが発生してもエラーにならないことを確認
                timefree_recorder._embed_metadata(file_path, sample_program_info)
        
        finally:
            os.unlink(file_path)


class TestRecordProgram:
    """番組録音統合テスト（適切な非同期Mock）"""
    
    @pytest.mark.asyncio
    async def test_record_program_success(self, timefree_recorder, sample_program_info):
        """番組録音の完全成功シナリオ（簡略化された統合テスト）"""
        output_path = "/tmp/test_recording.mp3"
        
        # URL生成をモック
        with patch.object(timefree_recorder, '_generate_timefree_url') as mock_url_gen:
            mock_url_gen.return_value = "https://example.com/playlist.m3u8"
            
            # プレイリスト取得をモック
            with patch.object(timefree_recorder, '_fetch_playlist') as mock_fetch:
                mock_fetch.return_value = ["https://example.com/seg1.ts", "https://example.com/seg2.ts"]
                
                # セグメントダウンロードをモック
                with patch.object(timefree_recorder, '_download_segments_concurrent') as mock_download:
                    mock_download.return_value = [b"segment1", b"segment2"]
                    
                    # ファイル結合をモック
                    with patch.object(timefree_recorder, '_combine_ts_segments') as mock_combine:
                        
                        # 音声変換をモック
                        with patch.object(timefree_recorder, '_convert_to_target_format') as mock_convert:
                            
                            # メタデータ埋め込みをモック
                            with patch.object(timefree_recorder, '_embed_metadata') as mock_metadata:
                                
                                # 一時ファイル作成をモック
                                with patch('tempfile.NamedTemporaryFile') as mock_temp:
                                    mock_temp_file = Mock()
                                    mock_temp_file.name = "/tmp/temp_file.ts"
                                    mock_temp.return_value.__enter__.return_value = mock_temp_file
                                    
                                    # os.path.getsize をモック（正しいモジュールパス）
                                    with patch('src.timefree_recorder.os.path.getsize', return_value=1024000):  # 1MB
                                        with patch('src.timefree_recorder.os.path.exists', return_value=True):
                                            with patch('src.timefree_recorder.os.unlink'):
                                                
                                                result = await timefree_recorder.record_program(
                                                    sample_program_info, output_path
                                                )
                                                
                                                assert result.success == True
                                                assert result.output_path == output_path
                                                assert result.file_size_bytes == 1024000
                                                assert result.total_segments == 2
                                                assert result.failed_segments == 0
                                                assert len(result.error_messages) == 0
                                                
                                                # 各メソッドが呼ばれることを確認
                                                mock_url_gen.assert_called_once()
                                                mock_fetch.assert_called_once()
                                                mock_download.assert_called_once()
                                                mock_combine.assert_called_once()
                                                mock_convert.assert_called_once()
                                                mock_metadata.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_program_timefree_not_available(self, timefree_recorder, sample_program_info):
        """タイムフリー利用不可の番組録音"""
        # タイムフリー利用不可に設定
        sample_program_info.is_timefree_available = False
        
        output_path = "/tmp/test_recording.mp3"
        
        result = await timefree_recorder.record_program(sample_program_info, output_path)
        
        assert result.success == False
        assert len(result.error_messages) == 1
        assert "この番組はタイムフリーで利用できません" in result.error_messages[0]
    
    @pytest.mark.asyncio
    async def test_record_program_playlist_fetch_error(self, timefree_recorder, sample_program_info):
        """プレイリスト取得エラー時の録音"""
        output_path = "/tmp/test_recording.mp3"
        
        with patch.object(timefree_recorder, '_generate_timefree_url') as mock_url_gen:
            mock_url_gen.return_value = "https://example.com/playlist.m3u8"
            
            with patch.object(timefree_recorder, '_fetch_playlist') as mock_fetch:
                mock_fetch.side_effect = PlaylistFetchError("プレイリスト取得失敗")
                
                result = await timefree_recorder.record_program(sample_program_info, output_path)
                
                assert result.success == False
                assert len(result.error_messages) == 1
                assert "プレイリスト取得失敗" in result.error_messages[0]
    
    @pytest.mark.asyncio
    async def test_record_program_segment_download_error(self, timefree_recorder, sample_program_info):
        """セグメントダウンロードエラー時の録音"""
        output_path = "/tmp/test_recording.mp3"
        
        with patch.object(timefree_recorder, '_generate_timefree_url') as mock_url_gen:
            mock_url_gen.return_value = "https://example.com/playlist.m3u8"
            
            with patch.object(timefree_recorder, '_fetch_playlist') as mock_fetch:
                mock_fetch.return_value = ["https://example.com/seg1.ts"]
                
                with patch.object(timefree_recorder, '_download_segments_concurrent') as mock_download:
                    mock_download.side_effect = SegmentDownloadError("ダウンロード失敗", [0])
                    
                    result = await timefree_recorder.record_program(sample_program_info, output_path)
                    
                    assert result.success == False
                    assert len(result.error_messages) == 1
                    assert "ダウンロード失敗" in result.error_messages[0]


class TestRecordByDatetime:
    """日時指定録音テスト"""
    
    @pytest.mark.asyncio
    async def test_record_by_datetime_success(self, timefree_recorder):
        """日時指定録音の成功"""
        start_time = datetime(2025, 7, 10, 6, 0, 0)
        end_time = datetime(2025, 7, 10, 8, 30, 0)
        output_path = "/tmp/test_recording.mp3"
        
        with patch.object(timefree_recorder, 'record_program') as mock_record:
            mock_result = RecordingResult(
                success=True,
                output_path=output_path,
                file_size_bytes=1024000,
                recording_duration_seconds=120.0,
                total_segments=10,
                failed_segments=0,
                error_messages=[]
            )
            mock_record.return_value = mock_result
            
            result = await timefree_recorder.record_by_datetime(
                "TBS", start_time, end_time, output_path
            )
            
            assert result.success == True
            assert result.output_path == output_path
            
            # record_program が適切な引数で呼ばれることを確認
            mock_record.assert_called_once()
            call_args = mock_record.call_args[0]
            program_info = call_args[0]
            
            assert program_info.station_id == "TBS"
            assert program_info.start_time == start_time
            assert program_info.end_time == end_time
            assert program_info.is_timefree_available == True


class TestErrorHandling:
    """エラーハンドリングテスト"""
    
    def test_timefree_error_hierarchy(self):
        """エラークラス階層のテスト"""
        # 基底クラス
        base_error = TimeFreeError("基底エラー")
        assert isinstance(base_error, Exception)
        
        # 認証エラー
        auth_error = TimeFreeAuthError("認証エラー", 401)
        assert isinstance(auth_error, TimeFreeError)
        assert auth_error.status_code == 401
        
        # セグメントダウンロードエラー
        segment_error = SegmentDownloadError("ダウンロードエラー", [1, 2])
        assert isinstance(segment_error, TimeFreeError)
        assert segment_error.failed_segments == [1, 2]
        
        # プレイリスト取得エラー
        playlist_error = PlaylistFetchError("プレイリストエラー")
        assert isinstance(playlist_error, TimeFreeError)
        
        # ファイル変換エラー
        conversion_error = FileConversionError("変換エラー")
        assert isinstance(conversion_error, TimeFreeError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])