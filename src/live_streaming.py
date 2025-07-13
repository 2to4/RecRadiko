"""
ライブストリーミング録音モジュール

このモジュールはRadikoのライブストリーミング録音機能を提供します。
- ライブプレイリストの継続監視
- セグメントの重複回避とトラッキング
- 並行セグメントダウンロード
- ライブ録音セッション管理
"""

import asyncio
import aiohttp
import m3u8
import time
import os
import logging
import hashlib
from typing import List, Optional, Dict, Any, AsyncGenerator, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import urllib.parse

from .logging_config import get_logger


@dataclass
class Segment:
    """セグメント情報"""
    url: str
    sequence_number: int
    duration: float
    byte_range: Optional[Tuple[int, int]] = None
    key_info: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        # セグメントURLが相対パスの場合は絶対URLに変換
        if not self.url.startswith(('http://', 'https://')):
            # 基本URLは呼び出し元で設定される
            pass


@dataclass
class SegmentInfo:
    """セグメント管理情報"""
    segment: Segment
    download_time: datetime
    file_size: int
    download_duration: float
    retry_count: int = 0
    data: Optional[bytes] = None  # セグメントデータ


@dataclass
class PlaylistUpdate:
    """プレイリスト更新情報"""
    timestamp: datetime
    sequence_number: int
    new_segments: List[Segment]
    total_segments: int
    duration_seconds: float


class LiveStreamingError(Exception):
    """ライブストリーミングエラーの例外クラス"""
    pass


class LivePlaylistMonitor:
    """ライブプレイリストの継続監視システム"""
    
    def __init__(self, 
                 playlist_url: str, 
                 auth_headers: Optional[Dict[str, str]] = None,
                 update_interval: int = 15,
                 timeout: int = 10,
                 max_retries: int = 5):
        """
        Args:
            playlist_url: 監視対象のM3U8プレイリストURL
            auth_headers: 認証ヘッダー（Radiko認証用）
            update_interval: プレイリスト更新間隔（秒）
            timeout: HTTP要求タイムアウト（秒）
            max_retries: 最大リトライ回数
        """
        self.playlist_url = playlist_url
        self.auth_headers = auth_headers or {}
        self.update_interval = update_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self.is_monitoring = False
        self.last_sequence = 0
        self.base_url = self._extract_base_url(playlist_url)
        
        # セグメント追跡（URL変化ベース検出用）
        self.seen_segment_urls = set()
        self.last_playlist_hash = None
        
        # ログ設定
        self.logger = get_logger(__name__)
        
        # HTTP セッション
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 監視状態
        self._stop_event = asyncio.Event()
        
    def _extract_base_url(self, playlist_url: str) -> str:
        """プレイリストURLから基本URLを抽出"""
        parsed = urllib.parse.urlparse(playlist_url)
        base_path = '/'.join(parsed.path.split('/')[:-1])
        return f"{parsed.scheme}://{parsed.netloc}{base_path}/"
    
    async def start_monitoring(self) -> AsyncGenerator[PlaylistUpdate, None]:
        """プレイリスト監視開始"""
        self.is_monitoring = True
        self._stop_event.clear()
        
        # HTTPセッション作成（認証ヘッダー付き）
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.auth_headers
        )
        
        self.logger.info(f"ライブプレイリスト監視開始: {self.playlist_url}")
        
        try:
            loop_count = 0
            while self.is_monitoring and not self._stop_event.is_set():
                loop_count += 1
                try:
                    # プレイリスト取得
                    self.logger.info(f"プレイリスト監視ループ {loop_count}: {self.playlist_url}")
                    playlist = await self.fetch_playlist()
                    
                    if playlist:
                        # プレイリスト詳細ログ（診断用）
                        media_seq = getattr(playlist, 'media_sequence', 0)
                        segment_urls = [seg.uri for seg in playlist.segments[:3]] if playlist.segments else []
                        self.logger.info(f"プレイリスト詳細: media_sequence={media_seq}, segments={len(playlist.segments)}, URLs={segment_urls}")
                        
                        # 新規セグメント抽出
                        new_segments = self.extract_new_segments(playlist)
                        
                        if new_segments:
                            # プレイリスト更新情報を生成
                            update = PlaylistUpdate(
                                timestamp=datetime.now(),
                                sequence_number=self.last_sequence,
                                new_segments=new_segments,
                                total_segments=len(playlist.segments),
                                duration_seconds=sum(seg.duration for seg in new_segments)
                            )
                            
                            # 新規セグメント検出ログは extract_new_segments 内で出力される
                            yield update
                    else:
                        self.logger.warning(f"プレイリスト取得失敗: {self.playlist_url}")
                    
                    # 更新間隔待機
                    try:
                        await asyncio.wait_for(
                            self._stop_event.wait(),
                            timeout=self.update_interval
                        )
                        # stop_eventがセットされた場合はループ終了
                        break
                    except asyncio.TimeoutError:
                        # タイムアウトは正常（更新間隔経過）
                        continue
                        
                except Exception as e:
                    self.logger.warning(f"プレイリスト監視エラー: {e}")
                    # エラー時は短時間待機後に継続
                    await asyncio.sleep(5)
                    
        finally:
            await self.stop_monitoring()
    
    async def stop_monitoring(self):
        """プレイリスト監視停止"""
        self.is_monitoring = False
        self._stop_event.set()
        
        if self.session:
            await self.session.close()
            self.session = None
        
        self.logger.info("ライブプレイリスト監視停止")
    
    async def fetch_playlist(self) -> Optional[m3u8.M3U8]:
        """プレイリスト取得（2段階：マスター→チャンクリスト）"""
        if not self.session:
            return None
            
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # 1段階目：マスタープレイリスト取得
                async with self.session.get(self.playlist_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # M3U8パース
                        master_playlist = m3u8.loads(content, uri=self.playlist_url)
                        
                        # マスタープレイリストかチェック（playlists属性があるかで判定）
                        if hasattr(master_playlist, 'playlists') and master_playlist.playlists:
                            # マスタープレイリストの場合：最初のチャンクリストURLを取得
                            chunk_playlist = master_playlist.playlists[0]  # 最初のストリーム（通常1つだけ）
                            chunk_url = chunk_playlist.absolute_uri
                            
                            self.logger.debug(f"チャンクリストURL: {chunk_url}")
                            
                            # 2段階目：チャンクリスト取得
                            async with self.session.get(chunk_url) as chunk_response:
                                if chunk_response.status == 200:
                                    chunk_content = await chunk_response.text()
                                    
                                    # チャンクリストパース
                                    chunk_playlist_obj = m3u8.loads(chunk_content, uri=chunk_url)
                                    
                                    # ライブストリームかチェック
                                    if not chunk_playlist_obj.is_endlist:
                                        self.logger.debug(f"ライブチャンクリスト取得成功: {len(chunk_playlist_obj.segments)}セグメント")
                                        return chunk_playlist_obj
                                    else:
                                        self.logger.warning("静的チャンクリスト検出（ライブではない）")
                                        return chunk_playlist_obj
                                else:
                                    self.logger.warning(f"チャンクリスト取得失敗: HTTP {chunk_response.status}")
                        else:
                            # 直接セグメントリストの場合（既にチャンクリスト）
                            if not master_playlist.is_endlist:
                                self.logger.debug(f"直接セグメントリスト取得: {len(master_playlist.segments)}セグメント")
                                return master_playlist
                            else:
                                self.logger.warning("静的プレイリスト検出（ライブではない）")
                                return master_playlist
                    else:
                        self.logger.warning(f"プレイリスト取得失敗: HTTP {response.status}")
                        
            except Exception as e:
                retry_count += 1
                self.logger.warning(f"プレイリスト取得エラー (試行 {retry_count}/{self.max_retries}): {e}")
                
                if retry_count < self.max_retries:
                    # 指数バックオフ
                    await asyncio.sleep(2 ** retry_count)
                else:
                    raise LiveStreamingError(f"プレイリスト取得に連続失敗: {e}")
        
        return None
    
    def extract_new_segments(self, playlist: m3u8.M3U8) -> List[Segment]:
        """新規セグメント抽出（スライディングウィンドウ対応）"""
        new_segments = []
        
        # プレイリストにセグメントが存在しない場合
        if not playlist.segments:
            return new_segments
        
        # 現在のセグメントURL一覧
        current_urls = [seg.uri for seg in playlist.segments]
        media_sequence = getattr(playlist, 'media_sequence', 1)
        
        if self.last_sequence == 0:
            # 初回監視：最新の1セグメントのみを対象（過度なダウンロードを避ける）
            if playlist.segments:
                # すべてのセグメントURLを既知として登録（重複ダウンロードを防ぐ）
                for segment in playlist.segments:
                    self.seen_segment_urls.add(segment.uri)
                
                # 最新の1セグメントのみを新規として取得
                last_segment = playlist.segments[-1]
                sequence_number = media_sequence + len(playlist.segments) - 1
                
                # 相対URLを絶対URLに変換
                segment_url = last_segment.uri
                if not segment_url.startswith(('http://', 'https://')):
                    segment_url = urllib.parse.urljoin(self.base_url, segment_url)
                
                new_segment = Segment(
                    url=segment_url,
                    sequence_number=sequence_number,
                    duration=last_segment.duration or 5.0,
                    byte_range=getattr(last_segment, 'byterange', None),
                    key_info=getattr(last_segment, 'key', None)
                )
                
                new_segments.append(new_segment)
                self.last_sequence = sequence_number
                
                self.logger.info(f"初回監視: 最新セグメント取得 seq={sequence_number}, 既知URL登録={len(playlist.segments)}個")
        
        else:
            # 継続監視：URL差分ベースの新規セグメント検出
            new_urls = []
            for url in current_urls:
                if url not in self.seen_segment_urls:
                    new_urls.append(url)
            
            if new_urls:
                # 新規URLに対応するセグメントを抽出
                for i, segment in enumerate(playlist.segments):
                    if segment.uri in new_urls:
                        sequence_number = media_sequence + i
                        
                        # 相対URLを絶対URLに変換
                        segment_url = segment.uri
                        if not segment_url.startswith(('http://', 'https://')):
                            segment_url = urllib.parse.urljoin(self.base_url, segment_url)
                        
                        new_segment = Segment(
                            url=segment_url,
                            sequence_number=sequence_number,
                            duration=segment.duration or 5.0,
                            byte_range=getattr(segment, 'byterange', None),
                            key_info=getattr(segment, 'key', None)
                        )
                        
                        new_segments.append(new_segment)
                        self.last_sequence = max(self.last_sequence, sequence_number)
                        self.seen_segment_urls.add(segment.uri)
                
                self.logger.info(f"新規セグメント検出: {len(new_segments)}個 (新規URL: {len(new_urls)})")
                
                # デバッグ情報
                for segment in new_segments:
                    self.logger.debug(f"新規セグメント: seq={segment.sequence_number}, url={segment.url[-30:]}")
            else:
                self.logger.debug(f"新規セグメントなし (見たURL: {len(self.seen_segment_urls)}, 現在URL: {len(current_urls)})")
        
        # 古いURLクリーンアップ（メモリ効率化）
        # スライディングウィンドウのため、プレイリスト外のURLは削除
        current_url_set = set(current_urls)
        old_urls = self.seen_segment_urls - current_url_set
        
        if old_urls:
            self.seen_segment_urls = self.seen_segment_urls - old_urls
            self.logger.debug(f"古いURL削除: {len(old_urls)}個")
        
        return new_segments


class SegmentTracker:
    """セグメント管理とトラッキングシステム"""
    
    def __init__(self, buffer_size: int = 100):
        """
        Args:
            buffer_size: 追跡するセグメント履歴のサイズ
        """
        self.downloaded_segments: Dict[int, SegmentInfo] = {}
        self.current_sequence = 0
        self.buffer_size = buffer_size
        self.total_downloaded_bytes = 0
        self.total_downloaded_count = 0
        
        # ログ設定
        self.logger = get_logger(__name__)
    
    def is_new_segment(self, segment: Segment) -> bool:
        """新規セグメント判定"""
        return segment.sequence_number not in self.downloaded_segments
    
    def register_segment(self, segment: Segment, file_size: int, download_duration: float, data: Optional[bytes] = None):
        """セグメント登録"""
        segment_info = SegmentInfo(
            segment=segment,
            download_time=datetime.now(),
            file_size=file_size,
            download_duration=download_duration,
            retry_count=0,
            data=data
        )
        
        self.downloaded_segments[segment.sequence_number] = segment_info
        self.current_sequence = max(self.current_sequence, segment.sequence_number)
        
        # 統計更新
        self.total_downloaded_bytes += file_size
        self.total_downloaded_count += 1
        
        # バッファサイズを超えた場合は古いセグメントを削除
        self.cleanup_old_segments()
        
        self.logger.debug(f"セグメント登録: {segment.sequence_number} ({file_size} bytes)")
    
    def get_missing_segments(self, start_sequence: int = None, end_sequence: int = None) -> List[int]:
        """欠落セグメント検出"""
        if start_sequence is None:
            start_sequence = min(self.downloaded_segments.keys()) if self.downloaded_segments else 1
        if end_sequence is None:
            end_sequence = self.current_sequence
        
        missing = []
        for seq in range(start_sequence, end_sequence + 1):
            if seq not in self.downloaded_segments:
                missing.append(seq)
        
        return missing
    
    def cleanup_old_segments(self):
        """古いセグメント情報のクリーンアップ"""
        if len(self.downloaded_segments) <= self.buffer_size:
            return
        
        # 古いセグメントを削除（LRU方式）
        sequences_to_remove = sorted(self.downloaded_segments.keys())[:-self.buffer_size]
        
        for seq in sequences_to_remove:
            del self.downloaded_segments[seq]
        
        if sequences_to_remove:
            self.logger.debug(f"古いセグメント {len(sequences_to_remove)} 個を削除")
    
    def get_statistics(self) -> Dict[str, Any]:
        """ダウンロード統計取得"""
        if not self.downloaded_segments:
            return {
                'total_segments': 0,
                'total_bytes': 0,
                'average_segment_size': 0,
                'average_download_time': 0,
                'download_rate_mbps': 0
            }
        
        segment_infos = list(self.downloaded_segments.values())
        total_download_time = sum(info.download_duration for info in segment_infos)
        
        avg_download_time = total_download_time / len(segment_infos) if segment_infos else 0
        avg_segment_size = self.total_downloaded_bytes / self.total_downloaded_count if self.total_downloaded_count > 0 else 0
        
        # ダウンロード速度計算（Mbps）
        download_rate_mbps = 0
        if total_download_time > 0:
            download_rate_mbps = (self.total_downloaded_bytes * 8) / (total_download_time * 1024 * 1024)
        
        return {
            'total_segments': self.total_downloaded_count,
            'total_bytes': self.total_downloaded_bytes,
            'average_segment_size': avg_segment_size,
            'average_download_time': avg_download_time,
            'download_rate_mbps': download_rate_mbps,
            'missing_segments': len(self.get_missing_segments()),
            'buffer_usage': len(self.downloaded_segments)
        }


class SegmentDownloader:
    """セグメント並行ダウンロードシステム"""
    
    def __init__(self, 
                 max_concurrent: int = 3,
                 download_timeout: int = 10,
                 retry_attempts: int = 3,
                 auth_headers: Optional[Dict[str, str]] = None):
        """
        Args:
            max_concurrent: 最大並行ダウンロード数
            download_timeout: ダウンロードタイムアウト（秒）
            retry_attempts: セグメントリトライ回数
            auth_headers: 認証ヘッダー（Radiko認証用）
        """
        self.max_concurrent = max_concurrent
        self.download_timeout = download_timeout
        self.retry_attempts = retry_attempts
        self.auth_headers = auth_headers or {}
        
        # ダウンロードキューと制御
        self.download_queue = asyncio.Queue()
        self.result_queue = asyncio.Queue()
        self.active_downloads: Set[asyncio.Task] = set()
        self.download_semaphore = asyncio.Semaphore(max_concurrent)
        
        # HTTP セッション
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 停止制御
        self._stop_event = asyncio.Event()
        self._worker_tasks: List[asyncio.Task] = []
        
        # ログ設定
        self.logger = get_logger(__name__)
        
        # 統計情報
        self.total_downloaded = 0
        self.total_failed = 0
        self.total_bytes = 0
    
    async def start_download_workers(self):
        """ダウンロードワーカー開始"""
        # HTTPセッション作成（認証ヘッダー付き）
        connector = aiohttp.TCPConnector(limit=20, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=self.download_timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.auth_headers
        )
        
        # ワーカータスク開始
        for i in range(self.max_concurrent):
            task = asyncio.create_task(self._download_worker(f"worker-{i}"))
            self._worker_tasks.append(task)
        
        self.logger.info(f"セグメントダウンロードワーカー {self.max_concurrent} 個を開始")
    
    async def stop_download_workers(self):
        """ダウンロードワーカー停止"""
        self._stop_event.set()
        
        # ワーカータスクの停止を待機
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
            self._worker_tasks.clear()
        
        # HTTPセッション閉じる
        if self.session:
            await self.session.close()
            self.session = None
        
        self.logger.info("セグメントダウンロードワーカー停止完了")
    
    async def _download_worker(self, worker_name: str):
        """ダウンロードワーカーのメインループ"""
        self.logger.debug(f"ダウンロードワーカー開始: {worker_name}")
        
        while not self._stop_event.is_set():
            try:
                # キューからセグメントを取得（タイムアウト付き）
                try:
                    segment = await asyncio.wait_for(
                        self.download_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # セグメントダウンロード実行
                try:
                    segment_data = await self.download_segment(segment)
                    
                    # 結果をキューに送信
                    await self.result_queue.put((segment, segment_data, None))
                    self.total_downloaded += 1
                    self.total_bytes += len(segment_data)
                    
                    self.logger.debug(f"セグメントダウンロード完了: {segment.sequence_number}")
                    
                except Exception as e:
                    # ダウンロード失敗
                    await self.result_queue.put((segment, None, e))
                    self.total_failed += 1
                    
                    self.logger.warning(f"セグメントダウンロード失敗: {segment.sequence_number} - {e}")
                
                # タスク完了通知
                self.download_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"ダウンロードワーカーエラー ({worker_name}): {e}")
                await asyncio.sleep(1)
        
        self.logger.debug(f"ダウンロードワーカー終了: {worker_name}")
    
    async def download_segment(self, segment: Segment) -> bytes:
        """単一セグメントダウンロード"""
        if not self.session:
            raise LiveStreamingError("HTTPセッションが初期化されていません")
        
        retry_count = 0
        last_error = None
        
        while retry_count < self.retry_attempts:
            try:
                async with self.session.get(segment.url) as response:
                    if response.status == 200:
                        data = await response.read()
                        
                        # データ検証
                        if len(data) == 0:
                            raise LiveStreamingError("空のセグメントデータ")
                        
                        return data
                    else:
                        raise LiveStreamingError(f"HTTP {response.status}: {segment.url}")
                        
            except Exception as e:
                retry_count += 1
                last_error = e
                
                if retry_count < self.retry_attempts:
                    # 指数バックオフ
                    await asyncio.sleep(2 ** retry_count)
                    self.logger.debug(f"セグメントダウンロードリトライ {retry_count}/{self.retry_attempts}: {segment.sequence_number}")
        
        # 全てのリトライが失敗
        raise LiveStreamingError(f"セグメントダウンロードに連続失敗: {last_error}")
    
    async def queue_segment(self, segment: Segment):
        """セグメントをダウンロードキューに追加"""
        await self.download_queue.put(segment)
    
    async def get_download_result(self) -> Tuple[Segment, Optional[bytes], Optional[Exception]]:
        """ダウンロード結果を取得"""
        return await self.result_queue.get()
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """ダウンロード統計取得"""
        total_attempts = self.total_downloaded + self.total_failed
        success_rate = (self.total_downloaded / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            'total_downloaded': self.total_downloaded,
            'total_failed': self.total_failed,
            'total_bytes': self.total_bytes,
            'success_rate': success_rate,
            'queue_size': self.download_queue.qsize(),
            'active_downloads': len(self.active_downloads)
        }


@dataclass
class RecordingResult:
    """録音結果情報"""
    success: bool
    total_segments: int
    downloaded_segments: int
    failed_segments: int
    total_bytes: int
    recording_duration: float
    error_messages: List[str]


class LiveRecordingSession:
    """ライブストリーミング録音セッション管理"""
    
    def __init__(self, 
                 job,  # RecordingJob (循環インポート回避のため型注釈なし)
                 streaming_manager):  # StreamingManager
        """
        Args:
            job: 録音ジョブ情報
            streaming_manager: ストリーミング管理インスタンス
        """
        self.job = job
        self.streaming_manager = streaming_manager
        self.start_time = time.time()
        
        # デバッグ: ジョブ情報をログ出力
        from .logging_config import get_logger
        logger = get_logger(__name__)
        logger.info(f"LiveRecordingSession作成: job.duration_seconds={job.duration_seconds} ({job.duration_seconds//60}分)")
        
        # コンポーネント
        self.monitor: Optional[LivePlaylistMonitor] = None
        self.tracker = SegmentTracker()
        self.downloader = SegmentDownloader()  # 認証ヘッダーは後で設定
        
        # 録音状態
        self.is_recording = False
        self.downloaded_bytes = 0
        self.segment_count = 0
        self.error_messages: List[str] = []
        
        # 停止制御
        self._stop_event = asyncio.Event()
        
        # ログ設定
        self.logger = get_logger(__name__)
    
    async def start_recording(self, output_path: str) -> RecordingResult:
        """ライブ録音開始"""
        self.logger.info(f"ライブ録音セッション開始: {self.job.id}")
        
        try:
            # 初期プレイリスト取得
            stream_url = await self._get_initial_stream_url()
            
            # 認証ヘッダー取得
            auth_info = self.streaming_manager.authenticator.get_valid_auth_info()
            auth_headers = {
                'X-Radiko-AuthToken': auth_info.auth_token,
                'X-Radiko-AreaId': auth_info.area_id,
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            # プレイリスト監視開始（認証ヘッダー付き、HLSに最適化された更新間隔）
            self.monitor = LivePlaylistMonitor(
                stream_url, 
                auth_headers=auth_headers,
                update_interval=5,  # HLSセグメント更新に最適化（15秒→5秒）
                timeout=10
            )
            
            # 認証ヘッダー付きダウンローダーを作成
            self.downloader = SegmentDownloader(auth_headers=auth_headers)
            
            # ダウンロードワーカー開始
            await self.downloader.start_download_workers()
            
            # 録音実行
            result = await self._execute_live_recording(output_path)
            
            return result
            
        except Exception as e:
            error_msg = f"ライブ録音セッションエラー: {e}"
            self.logger.error(error_msg)
            self.error_messages.append(error_msg)
            
            return RecordingResult(
                success=False,
                total_segments=0,
                downloaded_segments=0,
                failed_segments=0,
                total_bytes=0,
                recording_duration=time.time() - self.start_time,
                error_messages=self.error_messages
            )
        
        finally:
            await self.stop_recording()
    
    async def _get_initial_stream_url(self) -> str:
        """初期ストリームURL取得"""
        # StreamingManagerからライブストリームURLを取得
        # 現在時刻でのライブストリーミング
        stream_url = self.streaming_manager.get_stream_url(self.job.station_id)
        return stream_url
    
    async def _execute_live_recording(self, output_path: str) -> RecordingResult:
        """ライブ録音実行（段階的停止対応）"""
        self.is_recording = True
        recording_start = time.time()
        
        # 並行タスク実行
        tasks = [
            asyncio.create_task(self._monitor_playlist_task(), name="playlist_monitor"),
            asyncio.create_task(self._download_segments_task(), name="segment_downloader"),
            asyncio.create_task(self._write_segments_task(output_path), name="segment_writer"),
            asyncio.create_task(self._monitor_recording_duration(), name="duration_monitor")
        ]
        
        try:
            # すべてのタスクが完了するまで待機（グレースフル停止対応）
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # タスク結果をログ出力
            for i, (task, result) in enumerate(zip(tasks, results)):
                task_name = task.get_name()
                if isinstance(result, Exception):
                    self.logger.error(f"タスク {task_name} がエラーで終了: {result}")
                    self.error_messages.append(f"{task_name}: {result}")
                else:
                    self.logger.info(f"タスク {task_name} が正常終了")
            
        except Exception as e:
            self.logger.error(f"ライブ録音実行エラー: {e}")
            self.error_messages.append(f"録音実行エラー: {e}")
        
        recording_duration = time.time() - recording_start
        
        # グレースフル停止処理
        await self._graceful_shutdown()
        
        # 最終的なファイル確認
        final_file_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0
        
        # 結果生成
        downloader_stats = self.downloader.get_download_statistics()
        
        result = RecordingResult(
            success=len(self.error_messages) == 0 and final_file_exists,
            total_segments=downloader_stats['total_downloaded'] + downloader_stats['total_failed'],
            downloaded_segments=downloader_stats['total_downloaded'],
            failed_segments=downloader_stats['total_failed'],
            total_bytes=downloader_stats['total_bytes'],
            recording_duration=recording_duration,
            error_messages=self.error_messages
        )
        
        if final_file_exists:
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            self.logger.info(f"最終録音ファイル確認: {output_path} ({file_size_mb:.2f}MB)")
        else:
            self.logger.warning(f"最終録音ファイルが見つからない: {output_path}")
            result.error_messages.append("最終録音ファイルが作成されませんでした")
            result.success = False
        
        return result
    
    async def _graceful_shutdown(self):
        """段階的かつ協調的なシャットダウン処理"""
        self.logger.info("ライブ録音セッション停止中...")
        
        try:
            # フェーズ1: 停止シグナル（既に設定済み）
            self._stop_event.set()
            
            # フェーズ2: ダウンローダー停止（短時間）
            if self.downloader:
                await asyncio.wait_for(self.downloader.stop_download_workers(), timeout=3.0)
            
            # フェーズ3: プレイリスト監視停止
            if self.monitor:
                await asyncio.wait_for(self.monitor.stop_monitoring(), timeout=2.0)
            
            self.logger.info("ライブ録音セッション停止完了")
            
        except asyncio.TimeoutError:
            self.logger.warning("一部コンポーネントの停止がタイムアウトしました")
        except Exception as e:
            self.logger.error(f"停止処理エラー: {e}")
    
    async def _monitor_playlist_task(self):
        """プレイリスト監視タスク"""
        if not self.monitor:
            return
            
        try:
            async for update in self.monitor.start_monitoring():
                if self._stop_event.is_set():
                    break
                
                # 新規セグメントをダウンロードキューに追加
                for segment in update.new_segments:
                    if self.tracker.is_new_segment(segment):
                        await self.downloader.queue_segment(segment)
                        
        except Exception as e:
            self.logger.error(f"プレイリスト監視エラー: {e}")
            self.error_messages.append(f"プレイリスト監視エラー: {e}")
    
    async def _download_segments_task(self):
        """セグメントダウンロードタスク"""
        # ダウンロードワーカーは既に開始済み
        # このタスクは結果処理のみ
        while not self._stop_event.is_set():
            try:
                # ダウンロード結果を取得（タイムアウト付き）
                try:
                    segment, data, error = await asyncio.wait_for(
                        self.downloader.get_download_result(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                if data and not error:
                    # ダウンロード成功
                    download_duration = 0.5  # 仮の値
                    self.tracker.register_segment(segment, len(data), download_duration, data)
                    self.downloaded_bytes += len(data)
                    self.segment_count += 1
                else:
                    # ダウンロード失敗
                    if error:
                        self.logger.warning(f"セグメントダウンロード失敗: {segment.sequence_number} - {error}")
                
            except Exception as e:
                self.logger.error(f"セグメントダウンロード処理エラー: {e}")
    
    async def _write_segments_task(self, output_path: str):
        """セグメント書き込みタスク（グレースフル停止対応）"""
        self.logger.info(f"セグメント書き込み開始: {output_path}")
        
        # 一時ファイルでセグメントを結合
        # 一時TSファイルパス生成（拡張子に関係なく動作）
        base_path = os.path.splitext(output_path)[0]
        temp_ts_file = f"{base_path}_temp.ts"
        written_segments = set()
        last_written_seq = -1
        
        try:
            # ディレクトリ作成
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(temp_ts_file, 'wb') as ts_file:
                self.logger.info(f"一時TSファイル作成: {temp_ts_file}")
                
                # フェーズ1: アクティブ書き込み（停止イベントまで）
                while not self._stop_event.is_set():
                    written_count = self._write_available_segments(ts_file, written_segments, last_written_seq)
                    if written_count > 0:
                        last_written_seq = max(written_segments) if written_segments else last_written_seq
                        self.logger.debug(f"アクティブフェーズ: {written_count}セグメント書き込み (合計: {len(written_segments)})")
                    
                    await asyncio.sleep(0.1)  # 高頻度チェック
                
                self.logger.info("停止イベント検出 - 残りセグメント処理開始")
                
                # フェーズ2: 時間制限チェック後の限定的な猶予期間
                # 録音時間制限到達が理由の場合は追加書き込みを制限
                elapsed = time.time() - self.start_time
                target_duration = self.job.duration_seconds
                if target_duration <= 0:
                    if hasattr(self.job, 'start_time') and hasattr(self.job, 'end_time') and self.job.start_time and self.job.end_time:
                        target_duration = int((self.job.end_time - self.job.start_time).total_seconds())
                    else:
                        target_duration = 300
                
                self.logger.info(f"停止後処理: elapsed={elapsed:.1f}秒, target_duration={target_duration}秒, written_segments={len(written_segments)}")
                
                # 時間制限到達による停止の場合は適切な数のセグメントのみ書き込み
                if elapsed >= target_duration:
                    # 必要なセグメント数を計算（各セグメント約5秒と仮定）
                    max_segments_for_duration = int(target_duration / 5) + 1  # 少し余裕を持たせる
                    current_segments = len(written_segments)
                    
                    self.logger.info(f"時間制限調整判定: max_segments_for_duration={max_segments_for_duration}, current_segments={current_segments}")
                    
                    if current_segments < max_segments_for_duration:
                        # 不足分のセグメントを書き込み
                        needed_segments = max_segments_for_duration - current_segments
                        self.logger.info(f"不足セグメント書き込み開始: needed_segments={needed_segments}")
                        final_count = self._write_available_segments(ts_file, written_segments, last_written_seq, needed_segments)
                        if final_count > 0:
                            self.logger.info(f"時間制限調整: {final_count}セグメント追加書き込み (合計: {len(written_segments)})")
                        else:
                            self.logger.info(f"時間制限調整: 利用可能な追加セグメントなし")
                    else:
                        self.logger.info(f"時間制限到達による停止のため、追加セグメント書き込みをスキップ (既存: {current_segments})")
                else:
                    # 通常の停止（エラー等）の場合は猶予期間を設ける
                    grace_period = 2.0  # 2秒の短縮された猶予期間
                    grace_start = time.time()
                    
                    while time.time() - grace_start < grace_period:
                        written_count = self._write_available_segments(ts_file, written_segments, last_written_seq)
                        if written_count > 0:
                            last_written_seq = max(written_segments) if written_segments else last_written_seq
                            self.logger.debug(f"グレースフェーズ: {written_count}セグメント書き込み")
                        
                        await asyncio.sleep(0.1)
                    
                    # フェーズ3: 最終フラッシュ（通常停止の場合のみ）
                    final_count = self._write_available_segments(ts_file, written_segments, last_written_seq)
                    if final_count > 0:
                        self.logger.info(f"最終フラッシュ: {final_count}セグメント書き込み")
                
                # ファイル同期
                ts_file.flush()
                os.fsync(ts_file.fileno())
                
                self.logger.info(f"TSファイル書き込み完了: {len(written_segments)}セグメント")
            
            # フェーズ4: ファイル存在確認
            if not os.path.exists(temp_ts_file) or os.path.getsize(temp_ts_file) == 0:
                raise Exception(f"一時TSファイルが空またはが存在しません: {temp_ts_file}")
            
            file_size_mb = os.path.getsize(temp_ts_file) / (1024 * 1024)
            self.logger.info(f"一時TSファイルサイズ: {file_size_mb:.2f}MB")
            
            # フェーズ5: FFmpeg変換
            await self._convert_ts_to_target_format(temp_ts_file, output_path)
            
        except Exception as e:
            self.logger.error(f"セグメント書き込みエラー: {e}")
            import traceback
            traceback.print_exc()
            
            # エラー時も一時ファイルを残す（デバッグ用）
            if os.path.exists(temp_ts_file):
                self.logger.info(f"エラー時一時ファイル保持: {temp_ts_file}")
    
    def _write_available_segments(self, ts_file, written_segments: set, last_written_seq: int, max_additional: int = None) -> int:
        """利用可能なセグメントを順序通りに書き込み"""
        written_count = 0
        
        # セグメント番号順にソート
        available_segments = sorted(self.tracker.downloaded_segments.keys())
        
        for seq_num in available_segments:
            if seq_num in written_segments:
                continue
            
            # 最大追加数チェック
            if max_additional is not None and written_count >= max_additional:
                self.logger.debug(f"追加セグメント数制限到達: {written_count}/{max_additional}")
                break
                
            segment_info = self.tracker.downloaded_segments[seq_num]
            segment_data = getattr(segment_info, 'data', None)
            
            if segment_data and len(segment_data) > 0:
                try:
                    ts_file.write(segment_data)
                    written_segments.add(seq_num)
                    self.downloaded_bytes += len(segment_data)
                    written_count += 1
                    
                    self.logger.debug(f"セグメント書き込み完了: {seq_num} ({len(segment_data)} bytes)")
                    
                except Exception as e:
                    self.logger.error(f"セグメント{seq_num}書き込みエラー: {e}")
                    break
        
        return written_count
    
    async def _convert_ts_to_target_format(self, temp_ts_file: str, output_path: str):
        """TSファイルをターゲット形式に変換"""
        self.logger.info(f"音声変換開始: {temp_ts_file} -> {output_path}")
        
        try:
            # FFmpegコマンド構築（出力フォーマットに応じたコーデック選択）
            output_ext = os.path.splitext(output_path)[1].lower()
            if output_ext == '.mp3':
                audio_codec = 'libmp3lame'
            elif output_ext == '.aac':
                audio_codec = 'aac'
            else:
                audio_codec = 'aac'  # デフォルト
            
            ffmpeg_cmd = [
                'ffmpeg', 
                '-i', temp_ts_file,
                '-c:a', audio_codec, 
                '-b:a', '128k',
                '-avoid_negative_ts', 'make_zero',  # タイムスタンプ問題対策
                '-y', output_path
            ]
            
            # 非同期でサブプロセス実行
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    output_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    self.logger.info(f"音声変換完了: {output_path} ({output_size_mb:.2f}MB)")
                    
                    # 一時ファイル削除
                    try:
                        os.unlink(temp_ts_file)
                        self.logger.debug(f"一時ファイル削除完了: {temp_ts_file}")
                    except Exception as e:
                        self.logger.warning(f"一時ファイル削除失敗: {e}")
                else:
                    raise Exception(f"変換後ファイルが空または存在しません: {output_path}")
            else:
                error_msg = stderr.decode('utf-8') if stderr else "不明なエラー"
                raise Exception(f"FFmpeg変換失敗 (exit code: {process.returncode}): {error_msg}")
                
        except Exception as e:
            self.logger.error(f"音声変換エラー: {e}")
            raise
    
    async def _monitor_recording_duration(self):
        """録音時間監視タスク"""
        target_duration = self.job.duration_seconds
        self.logger.info(f"録音時間監視開始: job.duration_seconds={self.job.duration_seconds}")
        if target_duration <= 0:
            # より詳細なエラー情報を表示
            self.logger.error(f"ライブ録音時間が無効: duration_seconds={self.job.duration_seconds}, start_time={self.job.start_time}, end_time={self.job.end_time}")
            if hasattr(self.job, 'start_time') and hasattr(self.job, 'end_time') and self.job.start_time and self.job.end_time:
                calculated_duration = int((self.job.end_time - self.job.start_time).total_seconds())
                self.logger.info(f"start_time/end_timeから再計算: {calculated_duration}秒")
                target_duration = calculated_duration if calculated_duration > 0 else 300
            else:
                target_duration = 300  # 最後の手段
            self.logger.warning(f"使用する録音時間: {target_duration}秒 ({target_duration//60}分)")
        else:
            self.logger.info(f"録音時間制限設定: {target_duration}秒 ({target_duration//60}分)")
        
        while not self._stop_event.is_set():
            elapsed = time.time() - self.start_time
            
            if elapsed >= target_duration:
                self.logger.info(f"録音時間制限到達: {target_duration}秒")
                await self.stop_recording()
                break
            
            await asyncio.sleep(5)  # 5秒間隔でチェック
    
    async def stop_recording(self):
        """ライブ録音停止"""
        if not self.is_recording:
            return
            
        self.logger.info("ライブ録音セッション停止中...")
        
        self.is_recording = False
        self._stop_event.set()
        
        # 各コンポーネントの停止
        if self.monitor:
            await self.monitor.stop_monitoring()
        
        await self.downloader.stop_download_workers()
        
        self.logger.info("ライブ録音セッション停止完了")
    
    def should_continue_recording(self) -> bool:
        """録音継続判定"""
        if self._stop_event.is_set():
            return False
        
        # 録音時間制限チェック
        elapsed = time.time() - self.start_time
        target_duration = self.job.duration_seconds
        if target_duration <= 0:
            # start_time/end_timeから再計算を試行
            if hasattr(self.job, 'start_time') and hasattr(self.job, 'end_time') and self.job.start_time and self.job.end_time:
                calculated_duration = int((self.job.end_time - self.job.start_time).total_seconds())
                target_duration = calculated_duration if calculated_duration > 0 else 300
                self.logger.debug(f"時間制限チェック: 再計算された時間 {target_duration}秒を使用")
            else:
                target_duration = 300  # フォールバック
                self.logger.debug(f"時間制限チェック: 無効な値（{self.job.duration_seconds}秒）、300秒使用")
        else:
            self.logger.debug(f"時間制限チェック: {target_duration}秒, 経過時間: {elapsed:.1f}秒")
        
        return elapsed < target_duration
    
    def get_progress(self):
        """録音進捗取得"""
        elapsed = time.time() - self.start_time
        target_duration = self.job.duration_seconds
        if target_duration <= 0:
            # start_time/end_timeから再計算を試行
            if hasattr(self.job, 'start_time') and hasattr(self.job, 'end_time') and self.job.start_time and self.job.end_time:
                calculated_duration = int((self.job.end_time - self.job.start_time).total_seconds())
                target_duration = calculated_duration if calculated_duration > 0 else 300
                self.logger.debug(f"進捗計算: 再計算された時間 {target_duration}秒を使用")
            else:
                target_duration = 300  # フォールバック
                self.logger.debug(f"進捗計算: 無効な値（{self.job.duration_seconds}秒）、300秒使用")
        else:
            self.logger.debug(f"進捗計算: {target_duration}秒, 経過時間: {elapsed:.1f}秒")
        
        progress_percent = min(100.0, (elapsed / target_duration) * 100)
        
        # RecordingProgress の代わりに辞書で返す（循環インポート回避）
        return {
            'job_id': self.job.id,
            'progress_percent': progress_percent,
            'bytes_written': self.downloaded_bytes,
            'elapsed_seconds': int(elapsed),
            'estimated_remaining_seconds': max(0, int(target_duration - elapsed)),
            'segments_downloaded': self.segment_count
        }


# テスト用の簡単な使用例
if __name__ == "__main__":
    import sys
    
    # ログ設定（テスト実行時のみ）
    import os
    if os.environ.get('RECRADIKO_TEST_MODE', '').lower() == 'true':
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    async def test_playlist_monitor():
        """プレイリスト監視のテスト"""
        # テスト用のプレイリストURL（実際のURLに置き換え）
        test_url = "https://example.com/test.m3u8"
        
        monitor = LivePlaylistMonitor(
            playlist_url=test_url,
            update_interval=10
        )
        
        tracker = SegmentTracker()
        
        try:
            async for update in monitor.start_monitoring():
                print(f"プレイリスト更新: {len(update.new_segments)} 新規セグメント")
                
                for segment in update.new_segments:
                    if tracker.is_new_segment(segment):
                        print(f"新規セグメント: {segment.sequence_number} - {segment.url}")
                        # 実際のダウンロードはここで実行
                        # tracker.register_segment(segment, file_size, download_duration)
                
                # テスト用に10回更新で停止
                if update.sequence_number > 10:
                    break
                    
        except Exception as e:
            print(f"監視エラー: {e}")
        finally:
            await monitor.stop_monitoring()
    
    try:
        # 非同期テスト実行
        asyncio.run(test_playlist_monitor())
    except Exception as e:
        print(f"テストエラー: {e}")
        sys.exit(1)