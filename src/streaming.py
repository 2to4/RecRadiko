"""
ストリーミング処理モジュール

このモジュールはRadikoのHLS/M3U8ストリーミングを処理します。
- ストリーミングURLの取得
- M3U8プレイリストの解析
- TSセグメントのダウンロード
- 暗号化セグメントの復号
"""

import m3u8
import requests
import threading
import queue
import time
import logging
import hashlib
from typing import List, Optional, Dict, Any, Generator, Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import tempfile

from .auth import RadikoAuthenticator, AuthenticationError
from .utils.base import LoggerMixin
from .utils.network_utils import create_streaming_session


@dataclass
class StreamSegment:
    """ストリームセグメント情報"""
    url: str
    duration: float
    sequence: int
    timestamp: datetime
    encryption_key: Optional[str] = None
    encryption_iv: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now()


@dataclass
class StreamInfo:
    """ストリーム情報"""
    stream_url: str
    station_id: str
    quality: str
    bitrate: int
    codec: str
    segments: List[StreamSegment]
    is_live: bool = True
    total_duration: float = 0.0
    
    def __post_init__(self):
        if not self.total_duration and self.segments:
            self.total_duration = sum(seg.duration for seg in self.segments)


class StreamingManager(LoggerMixin):
    """ストリーミング管理クラス"""
    
    # Radiko ストリーミング API
    STREAM_URL_API = "https://radiko.jp/v2/api/ts/playlist.m3u8"
    TIMEFREE_URL_API = "https://radiko.jp/v2/api/ts/playlist.m3u8"
    
    def __init__(self, authenticator: RadikoAuthenticator, max_workers: int = 4):
        super().__init__()  # LoggerMixin初期化
        
        self.authenticator = authenticator
        self.max_workers = max_workers
        
        # セッション設定
        self.session = create_streaming_session()
        
        # セグメントダウンロード用の設定
        self.segment_timeout = 30
        self.retry_count = 3
        self.buffer_size = 8192
        self.max_segment_cache = 100
        
        
        # セグメントキャッシュ
        self.segment_cache: Dict[str, bytes] = {}
        self.cache_lock = threading.RLock()
    
    def get_stream_url(self, station_id: str, start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None) -> str:
        """ストリーミングURLを取得"""
        try:
            self.logger.info(f"ストリーミングURL取得: {station_id}")
            
            # 認証情報を取得
            auth_info = self.authenticator.get_valid_auth_info()
            
            # タイムシフト再生の場合
            if start_time:
                # タイムフリー認証を実行
                try:
                    timefree_session = self.authenticator.authenticate_timefree()
                    self.logger.info(f"タイムフリー認証成功: {timefree_session[:10]}...")
                except Exception as e:
                    self.logger.warning(f"タイムフリー認証失敗: {e}")
                
                # タイムフリー用パラメータ
                params = {
                    'station_id': station_id,
                    'l': '15',  # 15分間のセグメント
                    'ft': start_time.strftime('%Y%m%d%H%M%S'),
                    'to': (end_time or (start_time + timedelta(minutes=15))).strftime('%Y%m%d%H%M%S')
                }
                url = self.TIMEFREE_URL_API
            else:
                # タイムフリー専用システム（ライブストリーミング機能削除済み）
                raise StreamingError("ライブストリーミング機能は削除されました。タイムフリー録音を使用してください。")
            
            # ヘッダーを設定
            headers = {
                'X-Radiko-AuthToken': auth_info.auth_token,
                'X-Radiko-AreaId': auth_info.area_id,
                'User-Agent': self.session.headers.get('User-Agent', ''),
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            response = self.session.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            # Content-Typeの検証
            content_type = str(response.headers.get('content-type', '')).lower()
            if 'text/html' in content_type:
                self.logger.error(f"HTMLページが返されました: {response.url}")
                raise StreamingError("HTMLページが返されました（エラーページの可能性）")
            
            # レスポンスからM3U8 URLを取得
            # レスポンスがリダイレクトの場合はそのURLを使用
            stream_url = response.url
            
            # URLの妥当性検証
            if not stream_url.endswith('.m3u8'):
                self.logger.warning(f"想定外のURL形式: {stream_url}")
                # M3U8形式でない場合でも処理を続行（一部の配信形式に対応）
            
            # URLの基本的な妥当性チェック
            parsed_url = urlparse(stream_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise StreamingError(f"不正なURL形式: {stream_url}")
            
            self.logger.info(f"ストリーミングURL取得成功: {stream_url}")
            return stream_url
            
        except requests.RequestException as e:
            self.logger.error(f"ストリーミングURL取得エラー: {e}")
            raise StreamingError(f"ストリーミングURLの取得に失敗しました: {e}")
        except AuthenticationError as e:
            self.logger.error(f"認証エラー: {e}")
            raise StreamingError(f"認証に失敗しました: {e}")
        except Exception as e:
            self.logger.error(f"予期しないエラー: {e}")
            raise StreamingError(f"ストリーミングURL取得で予期しないエラー: {e}")
    
    def parse_playlist(self, playlist_url: str) -> StreamInfo:
        """M3U8プレイリストを解析"""
        try:
            self.logger.info(f"プレイリスト解析開始: {playlist_url}")
            
            # M3U8プレイリストを取得（認証ヘッダー付き）
            auth_info = self.authenticator.get_valid_auth_info()
            headers = {
                'X-Radiko-AuthToken': auth_info.auth_token,
                'X-Radiko-AreaId': auth_info.area_id,
                'User-Agent': self.session.headers.get('User-Agent', ''),
                'Accept': '*/*'
            }
            response = self.session.get(playlist_url, headers=headers)
            response.raise_for_status()
            
            # m3u8ライブラリでプレイリストを解析
            playlist = m3u8.loads(response.text, uri=playlist_url)
            
            if not playlist.segments:
                # マスタープレイリストの場合、適切な品質を選択
                if playlist.playlists:
                    # 最高品質のプレイリストを選択
                    best_playlist = max(playlist.playlists, 
                                      key=lambda p: p.stream_info.bandwidth if p.stream_info else 0)
                    playlist_url = urljoin(playlist_url, best_playlist.uri)
                    
                    # 再帰的に解析
                    return self.parse_playlist(playlist_url)
                else:
                    raise StreamingError("有効なセグメントが見つかりません")
            
            # セグメント情報を抽出
            segments = []
            for i, segment in enumerate(playlist.segments):
                segment_url = urljoin(playlist_url, segment.uri)
                
                # 暗号化情報を取得
                encryption_key = None
                encryption_iv = None
                if segment.key and segment.key.uri:
                    encryption_key = urljoin(playlist_url, segment.key.uri)
                    encryption_iv = segment.key.iv
                
                stream_segment = StreamSegment(
                    url=segment_url,
                    duration=segment.duration,
                    sequence=i,
                    timestamp=datetime.now(),
                    encryption_key=encryption_key,
                    encryption_iv=encryption_iv
                )
                segments.append(stream_segment)
            
            # ストリーム情報を作成
            stream_info = StreamInfo(
                stream_url=playlist_url,
                station_id=self._extract_station_id(playlist_url),
                quality="standard",
                bitrate=playlist.target_duration * 1000 if playlist.target_duration else 48000,
                codec="aac",
                segments=segments,
                is_live=not playlist.is_endlist
            )
            
            self.logger.info(f"プレイリスト解析完了: {len(segments)}セグメント")
            return stream_info
            
        except requests.RequestException as e:
            self.logger.error(f"プレイリスト取得エラー: {e}")
            raise StreamingError(f"プレイリストの取得に失敗しました: {e}")
        except Exception as e:
            self.logger.error(f"プレイリスト解析エラー: {e}")
            raise StreamingError(f"プレイリストの解析に失敗しました: {e}")
    
    def _extract_station_id(self, url: str) -> str:
        """URLから放送局IDを抽出"""
        try:
            # URLパラメータから放送局IDを抽出
            parsed = urlparse(url)
            # パスまたはクエリパラメータから放送局IDを推測
            # 実際の実装では、URLの構造に基づいて調整が必要
            path_parts = parsed.path.split('/')
            for part in path_parts:
                if part and len(part) <= 10:  # 放送局IDの形式を仮定
                    return part
            return "unknown"
        except Exception:
            return "unknown"
    
    def download_segments(self, stream_info: StreamInfo, output_path: str,
                         progress_callback: Optional[Callable[[int, int], None]] = None,
                         stop_flag: Optional[threading.Event] = None) -> Generator[bytes, None, None]:
        """セグメントをダウンロードしてデータを返す"""
        try:
            total_segments = len(stream_info.segments)
            downloaded_segments = 0
            
            self.logger.info(f"セグメントダウンロード開始: {total_segments}セグメント")
            
            # セグメントを順次ダウンロード
            for segment in stream_info.segments:
                if stop_flag and stop_flag.is_set():
                    self.logger.info("ダウンロード停止要求を受信")
                    break
                
                try:
                    # セグメントデータを取得
                    segment_data = self._download_single_segment(segment)
                    yield segment_data
                    
                    downloaded_segments += 1
                    
                    # 進捗コールバックを呼び出し
                    if progress_callback:
                        progress_callback(downloaded_segments, total_segments)
                    
                    self.logger.debug(f"セグメント {downloaded_segments}/{total_segments} 完了")
                    
                except Exception as e:
                    self.logger.error(f"セグメント {segment.sequence} ダウンロードエラー: {e}")
                    # 個別のセグメントエラーは継続
                    continue
            
            self.logger.info(f"セグメントダウンロード完了: {downloaded_segments}/{total_segments}")
            
        except Exception as e:
            self.logger.error(f"セグメントダウンロードエラー: {e}")
            raise StreamingError(f"セグメントのダウンロードに失敗しました: {e}")
    
    def download_segments_parallel(self, stream_info: StreamInfo, output_path: str,
                                  progress_callback: Optional[Callable[[int, int], None]] = None,
                                  stop_flag: Optional[threading.Event] = None) -> Generator[bytes, None, None]:
        """セグメントを並列ダウンロード（順序保証あり）"""
        try:
            total_segments = len(stream_info.segments)
            downloaded_segments = 0
            
            self.logger.info(f"並列セグメントダウンロード開始: {total_segments}セグメント")
            
            # 並列ダウンロードとバッファリング
            segment_buffer = {}
            next_sequence = 0
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 最初のバッチをサブミット
                future_to_segment = {
                    executor.submit(self._download_single_segment, segment): segment
                    for segment in stream_info.segments[:self.max_workers]
                }
                
                submitted_count = min(self.max_workers, total_segments)
                
                while future_to_segment:
                    if stop_flag and stop_flag.is_set():
                        self.logger.info("並列ダウンロード停止要求を受信")
                        # 実行中のタスクをキャンセル
                        for future in future_to_segment.keys():
                            future.cancel()
                        break
                    
                    # 完了したタスクを処理
                    for future in as_completed(future_to_segment, timeout=1.0):
                        segment = future_to_segment.pop(future)
                        
                        try:
                            segment_data = future.result()
                            segment_buffer[segment.sequence] = segment_data
                            
                            # 順序通りにバッファから出力
                            while next_sequence in segment_buffer:
                                yield segment_buffer.pop(next_sequence)
                                downloaded_segments += 1
                                next_sequence += 1
                                
                                # 進捗コールバック
                                if progress_callback:
                                    progress_callback(downloaded_segments, total_segments)
                            
                            # 次のセグメントをサブミット
                            if submitted_count < total_segments:
                                next_segment = stream_info.segments[submitted_count]
                                new_future = executor.submit(self._download_single_segment, next_segment)
                                future_to_segment[new_future] = next_segment
                                submitted_count += 1
                                
                        except Exception as e:
                            self.logger.error(f"セグメント {segment.sequence} 処理エラー: {e}")
                            continue
            
            # 残りのバッファを出力
            while next_sequence in segment_buffer:
                yield segment_buffer.pop(next_sequence)
                downloaded_segments += 1
                next_sequence += 1
                
                if progress_callback:
                    progress_callback(downloaded_segments, total_segments)
            
            self.logger.info(f"並列セグメントダウンロード完了: {downloaded_segments}/{total_segments}")
            
        except Exception as e:
            self.logger.error(f"並列セグメントダウンロードエラー: {e}")
            raise StreamingError(f"並列セグメントダウンロードに失敗しました: {e}")
    
    def _download_single_segment(self, segment: StreamSegment) -> bytes:
        """単一セグメントをダウンロード"""
        # キャッシュをチェック
        cache_key = hashlib.md5(segment.url.encode()).hexdigest()
        
        with self.cache_lock:
            if cache_key in self.segment_cache:
                self.logger.debug(f"セグメントキャッシュヒット: {segment.sequence}")
                return self.segment_cache[cache_key]
        
        # ダウンロードを試行
        for attempt in range(self.retry_count):
            try:
                # 認証ヘッダーを追加
                auth_info = self.authenticator.get_valid_auth_info()
                headers = {
                    'X-Radiko-AuthToken': auth_info.auth_token,
                    'X-Radiko-AreaId': auth_info.area_id,
                    'User-Agent': self.session.headers.get('User-Agent', ''),
                    'Accept': '*/*'
                }
                
                response = self.session.get(
                    segment.url,
                    headers=headers,
                    timeout=self.segment_timeout,
                    stream=True
                )
                response.raise_for_status()
                
                # データを読み取り
                data = b''
                for chunk in response.iter_content(chunk_size=self.buffer_size):
                    data += chunk
                
                # 暗号化されている場合は復号化
                if segment.encryption_key:
                    data = self._decrypt_segment(data, segment.encryption_key, segment.encryption_iv)
                
                # キャッシュに保存（サイズ制限あり）
                with self.cache_lock:
                    if len(self.segment_cache) < self.max_segment_cache:
                        self.segment_cache[cache_key] = data
                    elif cache_key not in self.segment_cache:
                        # 古いエントリを削除して新しいものを追加
                        oldest_key = next(iter(self.segment_cache))
                        del self.segment_cache[oldest_key]
                        self.segment_cache[cache_key] = data
                
                return data
                
            except Exception as e:
                if attempt == self.retry_count - 1:
                    raise StreamingError(f"セグメント {segment.sequence} のダウンロードに失敗: {e}")
                
                self.logger.warning(
                    f"セグメント {segment.sequence} ダウンロード再試行 "
                    f"({attempt + 1}/{self.retry_count}): {e}"
                )
                time.sleep(1)  # リトライ前に待機
    
    def _decrypt_segment(self, data: bytes, key_uri: str, iv: Optional[str]) -> bytes:
        """セグメントを復号化"""
        try:
            # 暗号化キーを取得
            key_response = self.session.get(key_uri, timeout=10)
            key_response.raise_for_status()
            key = key_response.content
            
            # AES復号化
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            
            # IVを処理
            if iv:
                if iv.startswith('0x'):
                    iv_bytes = bytes.fromhex(iv[2:])
                else:
                    iv_bytes = bytes.fromhex(iv)
            else:
                # デフォルトIV（シーケンス番号ベース）
                iv_bytes = b'\x00' * 16
            
            # 復号化
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv_bytes),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            decrypted_data = decryptor.update(data) + decryptor.finalize()
            
            # PKCS7パディングを除去
            if decrypted_data:
                padding_length = decrypted_data[-1]
                if padding_length <= 16:  # 有効なパディング長
                    decrypted_data = decrypted_data[:-padding_length]
            
            return decrypted_data
            
        except Exception as e:
            self.logger.error(f"セグメント復号化エラー: {e}")
            # 復号化に失敗した場合は元のデータを返す
            return data
    
    
    
    
    
    def clear_cache(self):
        """セグメントキャッシュをクリア"""
        with self.cache_lock:
            self.segment_cache.clear()
        self.logger.info("セグメントキャッシュをクリアしました")


class StreamingError(Exception):
    """ストリーミングエラーの例外クラス"""
    pass


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
    
    try:
        from .auth import RadikoAuthenticator
        
        # ストリーミングテスト
        authenticator = RadikoAuthenticator()
        streaming_manager = StreamingManager(authenticator)
        
        station_id = "TBS"  # テスト用放送局
        
        print(f"ストリーミングURLを取得中: {station_id}")
        stream_url = streaming_manager.get_stream_url(station_id)
        print(f"ストリーミングURL: {stream_url}")
        
        print("プレイリストを解析中...")
        stream_info = streaming_manager.parse_playlist(stream_url)
        print(f"セグメント数: {len(stream_info.segments)}")
        print(f"総再生時間: {stream_info.total_duration:.1f}秒")
        
        # 実際のダウンロードはコメントアウト（テスト時のみ有効化）
        # print("セグメントダウンロードテスト...")
        # with tempfile.NamedTemporaryFile(suffix='.ts', delete=False) as tmp_file:
        #     count = 0
        #     for segment_data in streaming_manager.download_segments(stream_info, tmp_file.name):
        #         count += 1
        #         if count >= 5:  # 最初の5セグメントのみテスト
        #             break
        #     print(f"テストダウンロード完了: {count}セグメント")
        
    except Exception as e:
        print(f"ストリーミングテストエラー: {e}")
        sys.exit(1)