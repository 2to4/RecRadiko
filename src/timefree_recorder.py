"""
タイムフリー専用録音モジュール

このモジュールはRadikoのタイムフリーAPIを使用した録音機能を提供します。
- タイムフリーM3U8プレイリストの取得
- セグメントの並行ダウンロード
- 音声フォーマット変換とメタデータ埋め込み
"""

import asyncio
import time
import os
import tempfile
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Any
import aiohttp
import sys
# import aiofiles  # 必要に応じて後で追加
from dataclasses import dataclass

from .auth import RadikoAuthenticator, AuthenticationError
from .utils.base import LoggerMixin


@dataclass
class RecordingResult:
    """録音結果データクラス"""
    success: bool
    output_path: str
    file_size_bytes: int
    recording_duration_seconds: float
    total_segments: int
    failed_segments: int
    error_messages: List[str]


class TimeFreeError(Exception):
    """タイムフリー関連エラーの基底クラス"""
    pass


class TimeFreeAuthError(TimeFreeError):
    """タイムフリー認証エラー"""
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message)


class SegmentDownloadError(TimeFreeError):
    """セグメントダウンロードエラー"""
    def __init__(self, message: str, failed_segments: List[int] = None):
        self.failed_segments = failed_segments or []
        super().__init__(message)


class PlaylistFetchError(TimeFreeError):
    """プレイリスト取得エラー"""
    pass


class FileConversionError(TimeFreeError):
    """ファイル変換エラー"""
    pass


class TimeFreeRecorder(LoggerMixin):
    """タイムフリー専用録音クラス"""
    
    # Radiko タイムフリーAPI
    TIMEFREE_URL_API = "https://radiko.jp/v2/api/ts/playlist.m3u8"
    
    def __init__(self, authenticator: RadikoAuthenticator):
        super().__init__()  # LoggerMixin初期化
        self.authenticator = authenticator
        self.max_workers = 8
        self.segment_timeout = 30
        self.retry_attempts = 3
        self.chunk_size = 8192
    
    async def record_program(self, program_info: 'ProgramInfo', 
                           output_path: str) -> RecordingResult:
        """番組情報を指定してタイムフリー録音実行
        
        Args:
            program_info: 録音対象番組情報
            output_path: 出力ファイルパス
            
        Returns:
            RecordingResult: 録音結果
            
        Raises:
            TimeFreeAuthError: 認証エラー
            SegmentDownloadError: セグメントダウンロードエラー
            FileConversionError: ファイル変換エラー
        """
        try:
            self.logger.info(f"タイムフリー録音開始: {program_info.title} ({program_info.station_id})")
            recording_start = time.time()
            
            # タイムフリー利用可能性確認
            if not program_info.is_timefree_available:
                raise TimeFreeError("この番組はタイムフリーで利用できません")
            
            # プレイリストURL生成
            playlist_url = self._generate_timefree_url(
                program_info.station_id,
                program_info.start_time,
                program_info.end_time
            )
            
            # セグメントURL一覧取得
            segment_urls = await self._fetch_playlist(playlist_url)
            
            if not segment_urls:
                raise PlaylistFetchError("セグメントURLが取得できませんでした")
            
            self.logger.info(f"セグメント数: {len(segment_urls)}")
            
            # セグメントを並行ダウンロード
            segments_data = await self._download_segments_concurrent(segment_urls)
            
            # 一時TSファイルに結合
            temp_ts_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.ts', delete=False) as temp_file:
                    temp_ts_path = temp_file.name
                    self._combine_ts_segments(segments_data, temp_ts_path)
                
                # 音声フォーマット変換とメタデータ埋め込み
                await self._convert_to_target_format(temp_ts_path, output_path, program_info)
                
                # メタデータ埋め込み
                self._embed_metadata(output_path, program_info)
                
            finally:
                # 一時ファイルクリーンアップ
                if temp_ts_path and os.path.exists(temp_ts_path):
                    os.unlink(temp_ts_path)
            
            # 録音結果生成
            recording_duration = time.time() - recording_start
            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            
            self.logger.info(f"タイムフリー録音完了: {output_path} ({file_size / 1024 / 1024:.1f}MB)")
            
            return RecordingResult(
                success=True,
                output_path=output_path,
                file_size_bytes=file_size,
                recording_duration_seconds=recording_duration,
                total_segments=len(segment_urls),
                failed_segments=0,
                error_messages=[]
            )
            
        except Exception as e:
            error_msg = f"タイムフリー録音エラー: {e}"
            self.logger.error(error_msg)
            
            return RecordingResult(
                success=False,
                output_path=output_path,
                file_size_bytes=0,
                recording_duration_seconds=time.time() - recording_start if 'recording_start' in locals() else 0,
                total_segments=len(segment_urls) if 'segment_urls' in locals() else 0,
                failed_segments=len(segment_urls) if 'segment_urls' in locals() else 0,
                error_messages=[error_msg]
            )
    
    async def record_by_datetime(self, station_id: str, start_time: datetime, 
                               end_time: datetime, output_path: str) -> RecordingResult:
        """日時指定でタイムフリー録音実行
        
        Args:
            station_id: 放送局ID
            start_time: 録音開始時刻
            end_time: 録音終了時刻
            output_path: 出力ファイルパス
            
        Returns:
            RecordingResult: 録音結果
        """
        # 番組情報を生成（簡易版）
        from .program_info import ProgramInfo
        
        program_info = ProgramInfo(
            program_id=f"{station_id}_{start_time.strftime('%Y%m%d_%H%M%S')}",
            station_id=station_id,
            station_name=station_id,  # 簡易設定
            title=f"タイムフリー録音_{start_time.strftime('%Y-%m-%d_%H:%M')}",
            start_time=start_time,
            end_time=end_time,
            is_timefree_available=True
        )
        
        return await self.record_program(program_info, output_path)
    
    def _generate_timefree_url(self, station_id: str, start_time: datetime, 
                             end_time: datetime) -> str:
        """タイムフリーM3U8 URL生成
        
        Args:
            station_id: 放送局ID
            start_time: 開始時刻
            end_time: 終了時刻
            
        Returns:
            str: タイムフリーM3U8 URL
        """
        try:
            # タイムフリー専用URL生成（直接形式）
            ft = start_time.strftime('%Y%m%d%H%M%S')
            to = end_time.strftime('%Y%m%d%H%M%S')
            
            playlist_url = f"https://radiko.jp/v2/api/ts/playlist.m3u8?station_id={station_id}&ft={ft}&to={to}"
            
            self.logger.debug(f"タイムフリーURL生成: {playlist_url}")
            return playlist_url
            
        except AuthenticationError as e:
            raise TimeFreeAuthError(f"認証に失敗しました: {e}")
        except Exception as e:
            raise TimeFreeError(f"URL生成エラー: {e}")
    
    async def _fetch_playlist(self, playlist_url: str) -> List[str]:
        """M3U8プレイリストからセグメントURL一覧取得
        
        Args:
            playlist_url: M3U8プレイリストURL
            
        Returns:
            List[str]: セグメントURL一覧
            
        Raises:
            PlaylistFetchError: プレイリスト取得エラー
        """
        try:
            # タイムフリー認証トークン取得
            timefree_token = self.authenticator.authenticate_timefree()
            if not timefree_token:
                raise PlaylistFetchError("タイムフリー認証に失敗しました")
            
            # 2025年Radiko仕様に合わせたヘッダー設定
            headers = {
                'User-Agent': 'curl/7.56.1',
                'Accept': '*/*',
                'Accept-Language': 'ja,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'X-Radiko-App': 'pc_html5',
                'X-Radiko-App-Version': '0.0.1',
                'X-Radiko-User': 'dummy_user',
                'X-Radiko-Device': 'pc',
                'X-Radiko-AuthToken': timefree_token
            }
            
            async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get(playlist_url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"プレイリスト取得エラー詳細: URL={playlist_url}")
                        self.logger.error(f"ステータス: {response.status}, レスポンス: {error_text}")
                        self.logger.error(f"リクエストヘッダー: {headers}")
                        raise PlaylistFetchError(f"プレイリスト取得失敗: HTTP {response.status}")
                    
                    playlist_content = await response.text()
                    self.logger.debug(f"プレイリスト内容: {playlist_content[:500]}...")
                    
                    # Radikoの2段階プレイリスト対応
                    # 1段目: playlist.m3u8 (ストリーム情報)
                    # 2段目: chunklist.m3u8 (実際のセグメント)
                    
                    # chunklistのURLを抽出
                    chunklist_url = None
                    for line in playlist_content.strip().split('\n'):
                        if line.startswith('https://') and 'chunklist' in line:
                            chunklist_url = line.strip()
                            break
                    
                    if not chunklist_url:
                        raise PlaylistFetchError("chunklistURLが見つかりません")
                    
                    self.logger.debug(f"chunklist URL: {chunklist_url}")
                    
                    # chunklistを取得
                    async with session.get(chunklist_url) as chunklist_response:
                        if chunklist_response.status != 200:
                            error_text = await chunklist_response.text()
                            raise PlaylistFetchError(f"chunklist取得失敗: HTTP {chunklist_response.status}")
                        
                        chunklist_content = await chunklist_response.text()
                        self.logger.debug(f"chunklist内容: {chunklist_content[:500]}...")
                        
                        # セグメントURL抽出
                        segment_urls = []
                        for line in chunklist_content.strip().split('\n'):
                            if line.startswith('https://') and '.aac' in line:
                                segment_urls.append(line.strip())
                        
                        self.logger.info(f"プレイリスト解析完了: {len(segment_urls)}セグメント")
                        return segment_urls
                    
        except Exception as e:
            raise PlaylistFetchError(f"プレイリスト取得エラー: {e}")
    
    async def _download_segments_concurrent(self, segment_urls: List[str]) -> List[bytes]:
        """セグメントの並行ダウンロード
        
        Args:
            segment_urls: セグメントURL一覧
            
        Returns:
            List[bytes]: ダウンロードされたセグメントデータ
            
        Performance:
            - 8並行ダウンロード
            - セグメント毎のリトライ処理
            - プログレスバー表示
        """
        try:
            segment_data = [None] * len(segment_urls)
            failed_segments = []
            
            # タイムフリー認証ヘッダー準備
            timefree_token = self.authenticator.authenticate_timefree()
            if not timefree_token:
                raise SegmentDownloadError("タイムフリー認証に失敗しました")
            
            headers = {
                'User-Agent': 'curl/7.56.1',
                'Accept': '*/*',
                'Accept-Language': 'ja,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'X-Radiko-App': 'pc_html5',
                'X-Radiko-App-Version': '0.0.1',
                'X-Radiko-User': 'dummy_user',
                'X-Radiko-Device': 'pc',
                'X-Radiko-AuthToken': timefree_token
            }
            
            # プログレスバー表示用
            try:
                from tqdm.asyncio import tqdm
                progress_bar = tqdm(total=len(segment_urls), desc="セグメントダウンロード", unit="seg")
            except ImportError:
                progress_bar = None
            
            async with aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.segment_timeout),
                connector=aiohttp.TCPConnector(limit=self.max_workers)
            ) as session:
                
                # セマフォで並行数制御
                semaphore = asyncio.Semaphore(self.max_workers)
                
                async def download_single_segment(index: int, url: str) -> Tuple[int, Optional[bytes]]:
                    """単一セグメントのダウンロード"""
                    async with semaphore:
                        for attempt in range(self.retry_attempts):
                            try:
                                async with session.get(url) as response:
                                    if response.status == 200:
                                        data = await response.read()
                                        if progress_bar:
                                            progress_bar.update(1)
                                        return index, data
                                    else:
                                        self.logger.warning(f"セグメント {index} HTTP {response.status}")
                                        
                            except Exception as e:
                                if attempt == self.retry_attempts - 1:
                                    self.logger.error(f"セグメント {index} ダウンロード失敗: {e}")
                                    failed_segments.append(index)
                                    if progress_bar:
                                        progress_bar.update(1)
                                    return index, None
                                else:
                                    await asyncio.sleep(1)  # リトライ前の待機
                    
                    return index, None
                
                # 並行ダウンロード実行
                tasks = [download_single_segment(i, url) for i, url in enumerate(segment_urls)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 結果を整理
                for result in results:
                    if isinstance(result, tuple):
                        index, data = result
                        segment_data[index] = data
                
                if progress_bar:
                    progress_bar.close()
            
            # 失敗セグメントがある場合はエラー
            if failed_segments:
                raise SegmentDownloadError(
                    f"{len(failed_segments)}個のセグメントダウンロードに失敗",
                    failed_segments
                )
            
            # Noneを除去して有効なデータのみ返す
            valid_segments = [data for data in segment_data if data is not None]
            
            self.logger.info(f"セグメントダウンロード完了: {len(valid_segments)}/{len(segment_urls)}")
            return valid_segments
            
        except Exception as e:
            raise SegmentDownloadError(f"並行ダウンロードエラー: {e}")
    
    def _combine_ts_segments(self, segments: List[bytes], temp_file_path: str):
        """TSセグメントの結合
        
        Args:
            segments: セグメントデータ一覧
            temp_file_path: 一時ファイルパス
            
        Note:
            セグメントを順序通りに結合し、一時TSファイルを作成
        """
        try:
            with open(temp_file_path, 'wb') as temp_file:
                for segment_data in segments:
                    if segment_data:
                        temp_file.write(segment_data)
            
            file_size_mb = os.path.getsize(temp_file_path) / (1024 * 1024)
            self.logger.info(f"TSセグメント結合完了: {temp_file_path} ({file_size_mb:.1f}MB)")
            
        except Exception as e:
            raise FileConversionError(f"TSセグメント結合エラー: {e}")
    
    async def _convert_to_target_format(self, temp_ts_path: str, 
                                      output_path: str, 
                                      program_info: 'ProgramInfo'):
        """音声フォーマット変換とメタデータ埋め込み
        
        Args:
            temp_ts_path: 一時TSファイルパス
            output_path: 最終出力パス
            program_info: 番組情報（メタデータ用）
            
        Supported Formats:
            - MP3: libmp3lame コーデック
            - AAC: aac コーデック  
            - WAV: pcm_s16le コーデック
        """
        try:
            # 出力形式を拡張子から判定
            output_ext = Path(output_path).suffix.lower()
            
            # FFmpegコマンド構築
            if output_ext == '.mp3':
                codec = 'libmp3lame'
                extra_args = ['-b:a', '256k']
            elif output_ext == '.aac':
                codec = 'aac'
                extra_args = ['-b:a', '256k']
            elif output_ext == '.wav':
                codec = 'pcm_s16le'
                extra_args = []
            else:
                # デフォルトはMP3
                codec = 'libmp3lame'
                extra_args = ['-b:a', '256k']
            
            # プログレス情報を取得するためのパイプを作成
            import tempfile
            progress_fd, progress_path = tempfile.mkstemp(suffix='.txt')
            os.close(progress_fd)
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', temp_ts_path,
                '-c:a', codec,
                *extra_args,
                '-progress', progress_path,  # プログレス情報出力
                '-y',  # 上書き許可
                output_path
            ]
            
            self.logger.info(f"音声変換開始: {codec} -> {output_path}")
            print("\n音声変換中...")
            
            # FFmpeg実行
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # プログレスバーを表示しながら処理を待機
            await self._show_ffmpeg_progress(process, progress_path, temp_ts_path)
            
            stdout, stderr = await process.communicate()
            
            # プログレスファイルを削除
            try:
                os.unlink(progress_path)
            except:
                pass
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else 'Unknown FFmpeg error'
                raise FileConversionError(f"FFmpeg変換エラー: {error_msg}")
            
            print("\n音声変換完了!")
            self.logger.info(f"音声変換完了: {output_path}")
            
        except FileNotFoundError:
            raise FileConversionError("FFmpegが見つかりません。FFmpegをインストールしてください。")
        except Exception as e:
            raise FileConversionError(f"音声変換エラー: {e}")
    
    async def _show_ffmpeg_progress(self, process: asyncio.subprocess.Process, progress_path: str, input_file: str):
        """FFmpegの進捗を表示する
        
        Args:
            process: FFmpegプロセス
            progress_path: プログレス情報ファイルパス
            input_file: 入力ファイルパス（時間取得用）
        """
        try:
            # 入力ファイルの総時間を取得
            duration = await self._get_media_duration(input_file)
            
            # プログレスバーを表示
            last_time = 0
            while process.returncode is None:
                try:
                    # プログレスファイルを読み込む
                    if os.path.exists(progress_path):
                        with open(progress_path, 'r') as f:
                            content = f.read()
                            current_time = self._parse_ffmpeg_progress(content)
                            
                            if current_time > last_time:
                                last_time = current_time
                                if duration > 0:
                                    progress = min(current_time / duration, 1.0)
                                    self._display_progress_bar(progress, current_time, duration)
                except Exception:
                    pass
                
                await asyncio.sleep(0.1)
                
            # 最終的に100%を表示
            if duration > 0:
                self._display_progress_bar(1.0, duration, duration)
                
        except Exception as e:
            self.logger.debug(f"Progress display error: {e}")
    
    async def _get_media_duration(self, file_path: str) -> float:
        """メディアファイルの時間を取得
        
        Args:
            file_path: ファイルパス
            
        Returns:
            時間（秒）
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                return float(stdout.decode().strip())
            else:
                return 0.0
                
        except Exception:
            return 0.0
    
    def _parse_ffmpeg_progress(self, content: str) -> float:
        """FFmpegプログレス情報から現在時刻を解析
        
        Args:
            content: プログレスファイルの内容
            
        Returns:
            現在時刻（秒）
        """
        try:
            # out_time_msフィールドを検索
            for line in content.split('\n'):
                if line.startswith('out_time_ms='):
                    time_ms = int(line.split('=')[1])
                    return time_ms / 1000000.0  # マイクロ秒を秒に変換
            return 0.0
        except Exception:
            return 0.0
    
    def _display_progress_bar(self, progress: float, current_time: float, total_time: float):
        """プログレスバーを表示
        
        Args:
            progress: 進捗率（0.0-1.0）
            current_time: 現在時刻（秒）
            total_time: 総時間（秒）
        """
        try:
            bar_length = 30
            filled_length = int(bar_length * progress)
            
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            
            # 時刻を mm:ss 形式に変換
            current_min, current_sec = divmod(int(current_time), 60)
            total_min, total_sec = divmod(int(total_time), 60)
            
            percent = progress * 100
            
            # カーソルを行の先頭に戻して上書き
            sys.stdout.write(f'\\r変換進捗: |{bar}| {percent:.1f}% ({current_min:02d}:{current_sec:02d}/{total_min:02d}:{total_sec:02d})')
            sys.stdout.flush()
            
        except Exception:
            pass
    
    def _embed_metadata(self, file_path: str, program_info: 'ProgramInfo'):
        """ID3メタデータの埋め込み
        
        Args:
            file_path: 音声ファイルパス
            program_info: 番組情報
            
        Metadata Fields:
            - TIT2: 番組タイトル
            - TPE1: 出演者
            - TALB: 放送局名
            - TDRC: 放送日
            - TCON: ジャンル (Radio)
            - COMM: 番組説明
        """
        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, COMM
            
            # ファイル形式確認
            if not file_path.lower().endswith('.mp3'):
                self.logger.info("MP3以外のファイル形式のため、メタデータ埋め込みをスキップ")
                return
            
            # ID3タグを追加/更新
            try:
                audio = MP3(file_path, ID3=ID3)
            except Exception:
                # ID3タグが存在しない場合は作成
                audio = MP3(file_path)
                audio.add_tags()
            
            # メタデータを設定
            metadata = program_info.to_metadata()
            
            audio.tags.add(TIT2(encoding=3, text=metadata['title']))
            audio.tags.add(TPE1(encoding=3, text=metadata['artist']))
            audio.tags.add(TALB(encoding=3, text=metadata['album']))
            audio.tags.add(TDRC(encoding=3, text=metadata['date']))
            audio.tags.add(TCON(encoding=3, text=metadata['genre']))
            audio.tags.add(COMM(encoding=3, lang='jpn', desc='Description', text=metadata['comment']))
            
            # ファイルに保存
            audio.save()
            
            self.logger.info(f"メタデータ埋め込み完了: {file_path}")
            
        except ImportError:
            self.logger.warning("mutagenライブラリが見つかりません。メタデータ埋め込みをスキップします。")
        except Exception as e:
            self.logger.warning(f"メタデータ埋め込みエラー: {e}")


# テスト用の簡単な使用例
if __name__ == "__main__":
    import sys
    from datetime import datetime, timedelta
    
    async def test_timefree_recording():
        """タイムフリー録音のテスト"""
        try:
            from .auth import RadikoAuthenticator
            
            # 認証器を初期化
            authenticator = RadikoAuthenticator()
            recorder = TimeFreeRecorder(authenticator)
            
            # テスト用の録音（1時間前の15分間）
            now = datetime.now()
            start_time = now - timedelta(hours=1)
            end_time = start_time + timedelta(minutes=15)
            
            output_path = f"test_timefree_{start_time.strftime('%Y%m%d_%H%M')}.mp3"
            
            print(f"タイムフリー録音テスト開始: {start_time} - {end_time}")
            
            result = await recorder.record_by_datetime(
                "TBS",  # TBSラジオ
                start_time,
                end_time,
                output_path
            )
            
            if result.success:
                print(f"録音成功: {result.output_path} ({result.file_size_bytes / 1024 / 1024:.1f}MB)")
            else:
                print(f"録音失敗: {result.error_messages}")
                
        except Exception as e:
            print(f"テストエラー: {e}")
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test_timefree_recording())
    else:
        print("タイムフリー録音モジュール - RecRadiko")
        print("使用方法: python -m src.timefree_recorder test")