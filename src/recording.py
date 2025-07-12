"""
録音機能モジュール

このモジュールはRadikoの録音機能を管理します。
- 録音ジョブの管理
- FFmpegとの連携
- 音声形式の変換
- 進捗監視とキューイング
"""

import ffmpeg
import subprocess
import threading
import queue
import time
import logging
import tempfile
import shutil
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import hashlib
import json

from .auth import RadikoAuthenticator
from .program_info import ProgramInfoManager, Program
from .streaming import StreamingManager, StreamingError
from .logging_config import get_logger


class RecordingStatus(Enum):
    """録音ステータス"""
    PENDING = "pending"
    PREPARING = "preparing"
    RECORDING = "recording"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RecordingJob:
    """録音ジョブ情報"""
    id: str
    station_id: str
    program_title: str
    start_time: datetime
    end_time: datetime
    output_path: str
    status: RecordingStatus = RecordingStatus.PENDING
    format: str = "aac"
    bitrate: int = 128
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    file_size: int = 0
    duration_seconds: int = 0
    error_message: str = ""
    retry_count: int = 0
    priority: int = 0
    
    def __post_init__(self):
        if not self.duration_seconds:
            self.duration_seconds = int((self.end_time - self.start_time).total_seconds())
    
    @property
    def duration_minutes(self) -> int:
        return self.duration_seconds // 60
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'id': self.id,
            'station_id': self.station_id,
            'program_title': self.program_title,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'output_path': self.output_path,
            'status': self.status.value,
            'format': self.format,
            'bitrate': self.bitrate,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'file_size': self.file_size,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'priority': self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecordingJob':
        """辞書から復元"""
        data = data.copy()
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        data['end_time'] = datetime.fromisoformat(data['end_time'])
        data['status'] = RecordingStatus(data['status'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data['started_at']:
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data['completed_at']:
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


@dataclass
class RecordingProgress:
    """録音進捗情報"""
    job_id: str
    status: RecordingStatus
    progress_percent: float
    bytes_written: int
    elapsed_seconds: int
    estimated_remaining_seconds: int
    
    def __post_init__(self):
        self.progress_percent = min(100.0, max(0.0, self.progress_percent))


class RecordingManager:
    """録音管理クラス"""
    
    def __init__(self, 
                 authenticator: RadikoAuthenticator,
                 program_manager: ProgramInfoManager,
                 streaming_manager: StreamingManager,
                 output_dir: str = "./recordings",
                 max_concurrent_jobs: int = 4,
                 max_retries: int = 3):
        
        self.authenticator = authenticator
        self.program_manager = program_manager
        self.streaming_manager = streaming_manager
        self.output_dir = Path(output_dir)
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_retries = max_retries
        
        # 出力ディレクトリを作成
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # ログ設定
        self.logger = get_logger(__name__)
        
        # ジョブ管理
        self.jobs: Dict[str, RecordingJob] = {}
        self.job_queue = queue.PriorityQueue()
        self.active_jobs: Dict[str, threading.Thread] = {}
        self.job_progress: Dict[str, RecordingProgress] = {}
        
        # スレッド管理
        self.worker_threads: List[threading.Thread] = []
        self.stop_event = threading.Event()
        self.lock = threading.RLock()
        
        # FFmpeg設定
        self.ffmpeg_path = self._find_ffmpeg()
        
        # 進捗コールバック
        self.progress_callbacks: List[Callable[[RecordingProgress], None]] = []
        
        # ワーカースレッドを開始
        self._start_workers()
    
    def _find_ffmpeg(self) -> str:
        """FFmpegの実行パスを探す"""
        try:
            # システムPATHからffmpegを探す
            result = subprocess.run(['which', 'ffmpeg'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception):
            pass
        
        # 一般的なパスを試す
        common_paths = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            '/opt/homebrew/bin/ffmpeg',
            'ffmpeg'  # PATH環境変数に依存
        ]
        
        for path in common_paths:
            try:
                result = subprocess.run([path, '-version'], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    return path
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, Exception):
                continue
        
        raise RecordingError("FFmpegが見つかりません。インストールしてください。")
    
    def _start_workers(self):
        """ワーカースレッドを開始"""
        for i in range(self.max_concurrent_jobs):
            worker = threading.Thread(
                target=self._worker_thread, 
                name=f"RecordingWorker-{i}",
                daemon=True
            )
            worker.start()
            self.worker_threads.append(worker)
        
        self.logger.info(f"録音ワーカー {len(self.worker_threads)} スレッドを開始")
    
    def _worker_thread(self):
        """ワーカースレッドのメインループ"""
        while not self.stop_event.is_set():
            try:
                # キューからジョブを取得（タイムアウト付き）
                _, job_id = self.job_queue.get(timeout=1.0)
                
                if job_id not in self.jobs:
                    continue
                
                job = self.jobs[job_id]
                
                # アクティブジョブに追加
                with self.lock:
                    self.active_jobs[job_id] = threading.current_thread()
                
                try:
                    self._execute_recording(job)
                except Exception as e:
                    self.logger.error(f"録音実行エラー {job_id}: {e}")
                    self._handle_job_error(job, str(e))
                finally:
                    # アクティブジョブから削除
                    with self.lock:
                        if job_id in self.active_jobs:
                            del self.active_jobs[job_id]
                        if job_id in self.job_progress:
                            del self.job_progress[job_id]
                
                self.job_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"ワーカースレッドエラー: {e}")
                time.sleep(1)
    
    def create_recording_job(self, 
                           station_id: str,
                           program_title: str,
                           start_time: datetime,
                           end_time: datetime,
                           output_path: Optional[str] = None,
                           format: str = "aac",
                           bitrate: int = 128,
                           priority: int = 0) -> str:
        """録音ジョブを作成"""
        
        # ジョブIDを生成
        job_id = self._generate_job_id(station_id, start_time)
        
        # 出力パスを決定
        if not output_path:
            output_path = self._generate_output_path(
                station_id, program_title, start_time, format
            )
        
        # 録音時間を計算
        duration_seconds = int((end_time - start_time).total_seconds())
        
        # ジョブを作成
        job = RecordingJob(
            id=job_id,
            station_id=station_id,
            program_title=program_title,
            start_time=start_time,
            end_time=end_time,
            output_path=output_path,
            format=format,
            bitrate=bitrate,
            priority=priority,
            duration_seconds=duration_seconds
        )
        
        with self.lock:
            self.jobs[job_id] = job
        
        self.logger.info(f"録音ジョブ作成: {job_id}")
        return job_id
    
    def _generate_job_id(self, station_id: str, start_time: datetime) -> str:
        """ジョブIDを生成"""
        timestamp = int(start_time.timestamp())
        hash_input = f"{station_id}_{timestamp}".encode()
        hash_short = hashlib.md5(hash_input).hexdigest()[:8]
        return f"{station_id}_{timestamp}_{hash_short}"
    
    def _generate_output_path(self, 
                            station_id: str,
                            program_title: str,
                            start_time: datetime,
                            format: str) -> str:
        """出力ファイルパスを生成"""
        
        # 日付ベースのディレクトリ構造
        date_dir = start_time.strftime('%Y/%m/%d')
        station_dir = station_id
        
        # ファイル名を生成（安全な文字のみ）
        safe_title = self._sanitize_filename(program_title)
        timestamp = start_time.strftime('%Y%m%d_%H%M')
        filename = f"{station_id}_{safe_title}_{timestamp}.{format}"
        
        # 完全パスを構築
        full_path = self.output_dir / date_dir / station_dir / filename
        
        # ディレクトリを作成
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        return str(full_path)
    
    def _sanitize_filename(self, filename: str) -> str:
        """ファイル名を安全な文字に変換"""
        # 空文字列の場合はデフォルト名を返す
        if not filename or not filename.strip():
            return "untitled"
        
        # 不正な文字を置換
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        
        # 長すぎる場合は切り詰め
        if len(filename) > 100:
            filename = filename[:100]
        
        result = filename.strip()
        return result if result else "untitled"
    
    def schedule_recording(self, job_id: str) -> bool:
        """録音をスケジュール"""
        if job_id not in self.jobs:
            self.logger.error(f"ジョブが見つかりません: {job_id}")
            return False
        
        job = self.jobs[job_id]
        
        # 即座に実行するか開始時刻を待つか判定
        now = datetime.now()
        if job.start_time <= now:
            # 即座に実行
            self._queue_job(job)
        else:
            # 開始時刻まで待機するタイマーを設定
            delay = (job.start_time - now).total_seconds()
            timer = threading.Timer(delay, self._queue_job, args=[job])
            timer.start()
            self.logger.info(f"録音予約: {job_id} - {job.start_time}")
        
        return True
    
    def _queue_job(self, job: RecordingJob):
        """ジョブをキューに追加"""
        # 優先度付きキューに追加（負の値で高優先度）
        priority_score = (-job.priority, job.start_time.timestamp())
        self.job_queue.put((priority_score, job.id))
        
        job.status = RecordingStatus.PENDING
        self.logger.info(f"録音ジョブをキューに追加: {job.id}")
    
    def _execute_recording(self, job: RecordingJob):
        """録音を実行"""
        try:
            job.status = RecordingStatus.PREPARING
            job.started_at = datetime.now()
            
            self.logger.info(f"録音開始: {job.id}")
            
            # 進捗情報を初期化
            progress = RecordingProgress(
                job_id=job.id,
                status=RecordingStatus.PREPARING,
                progress_percent=0.0,
                bytes_written=0,
                elapsed_seconds=0,
                estimated_remaining_seconds=job.duration_seconds
            )
            self.job_progress[job.id] = progress
            
            # ストリーミングURLを取得
            # ライブ録音の場合は現在時刻から録音開始
            now = datetime.now()
            is_live_recording = self._is_live_recording(job, now)
            
            if not is_live_recording:
                # 従来の静的録音（タイムフリー）
                stream_url = self.streaming_manager.get_stream_url(
                    job.station_id, job.start_time, job.end_time
                )
                stream_info = self.streaming_manager.parse_playlist(stream_url)
                
                # 一時ファイルで録音
                with tempfile.NamedTemporaryFile(suffix='.ts', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                try:
                    # 静的録音実行
                    self._record_stream_static(job, stream_info, tmp_path)
                    
                    # 音声形式を変換
                    if job.format != 'ts':
                        self._convert_audio(job, tmp_path, job.output_path)
                    else:
                        # TSファイルはそのまま移動
                        shutil.move(tmp_path, job.output_path)
                    
                    # メタデータを追加
                    self._add_metadata(job)
                    
                    # 完了処理
                    job.status = RecordingStatus.COMPLETED
                    job.completed_at = datetime.now()
                    job.file_size = Path(job.output_path).stat().st_size
                    
                    self.logger.info(f"録音完了: {job.id} -> {job.output_path}")
                    
                finally:
                    # 一時ファイルを削除
                    try:
                        Path(tmp_path).unlink(missing_ok=True)
                    except Exception as e:
                        self.logger.warning(f"一時ファイル削除エラー: {e}")
            else:
                # ライブストリーミング録音
                self.logger.info(f"ライブストリーミング録音を開始: {job.id}")
                self._record_stream_live(job)
            
        except Exception as e:
            self.logger.error(f"録音エラー {job.id}: {e}")
            self._handle_job_error(job, str(e))
    
    def _is_live_recording(self, job: RecordingJob, current_time: datetime) -> bool:
        """ライブ録音判定"""
        # 現在時刻が録音開始時刻と終了時刻の間にある場合はライブ録音
        return (job.start_time <= current_time <= job.end_time)
    
    def _record_stream_live(self, job: RecordingJob):
        """ライブストリーミング録音（新メソッド）"""
        try:
            # live_streaming モジュールをここでインポート（循環インポート回避）
            from .live_streaming import LiveRecordingSession
            
            # ライブ録音セッション作成
            live_session = LiveRecordingSession(job, self.streaming_manager)
            
            # 非同期録音をイベントループで実行
            import asyncio
            
            # 新しいイベントループを作成（スレッド内での実行のため）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # ライブ録音実行
                result = loop.run_until_complete(
                    live_session.start_recording(job.output_path)
                )
                
                # 結果を反映
                if result.success:
                    job.status = RecordingStatus.COMPLETED
                    job.file_size = result.total_bytes
                    self.logger.info(f"ライブ録音完了: {job.id} - {result.downloaded_segments}セグメント")
                else:
                    job.status = RecordingStatus.FAILED
                    job.error_message = "; ".join(result.error_messages)
                    self.logger.error(f"ライブ録音失敗: {job.id} - {job.error_message}")
                
                job.completed_at = datetime.now()
                
            finally:
                loop.close()
                
        except Exception as e:
            self.logger.error(f"ライブ録音セッションエラー {job.id}: {e}")
            job.status = RecordingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
    
    def _record_stream_static(self, job: RecordingJob, stream_info, output_path: str):
        """静的プレイリスト録音（既存ロジック）"""
        # 既存の_record_streamロジックをリネームして使用
        job.status = RecordingStatus.RECORDING
        
        start_time = time.time()
        bytes_written = 0
        
        # 進捗更新のコールバック
        def update_progress(current_seg: int, total_seg: int):
            nonlocal bytes_written
            
            elapsed = time.time() - start_time
            progress_percent = (current_seg / total_seg) * 100
            
            # 推定残り時間を計算
            if progress_percent > 0:
                estimated_total = elapsed / (progress_percent / 100)
                estimated_remaining = max(0, estimated_total - elapsed)
            else:
                estimated_remaining = job.duration_seconds
            
            # 進捗情報を更新
            progress = RecordingProgress(
                job_id=job.id,
                status=RecordingStatus.RECORDING,
                progress_percent=progress_percent,
                bytes_written=bytes_written,
                elapsed_seconds=int(elapsed),
                estimated_remaining_seconds=int(estimated_remaining)
            )
            
            self.job_progress[job.id] = progress
            
            # コールバックを呼び出し
            for callback in self.progress_callbacks:
                try:
                    callback(progress)
                except Exception as e:
                    self.logger.warning(f"進捗コールバックエラー: {e}")
        
        # 録音時間制限（秒）
        max_recording_time = job.duration_seconds
        if max_recording_time <= 0:
            max_recording_time = 300  # 無効な値の場合のフォールバック
            self.logger.warning(f"録音時間が無効（{job.duration_seconds}秒）、デフォルト5分を使用")
        
        self.logger.info(f"静的録音時間制限: {max_recording_time}秒 ({max_recording_time//60}分)")
        self.logger.debug(f"ジョブの詳細: start_time={job.start_time}, end_time={job.end_time}, duration_seconds={job.duration_seconds}")
        recording_start_time = time.time()
        
        # セグメントをダウンロードして保存
        with open(output_path, 'wb') as output_file:
            for segment_data in self.streaming_manager.download_segments(
                stream_info, output_path, update_progress
            ):
                # 録音時間制限チェック
                if time.time() - recording_start_time >= max_recording_time:
                    self.logger.info(f"静的録音時間制限に到達: {max_recording_time}秒")
                    break
                
                output_file.write(segment_data)
                bytes_written += len(segment_data)
    
    
    def _convert_audio(self, job: RecordingJob, input_path: str, output_path: str):
        """音声形式を変換"""
        job.status = RecordingStatus.PROCESSING
        
        self.logger.info(f"音声変換開始: {job.format} (bitrate: {job.bitrate})")
        
        try:
            # FFmpegを使用して変換
            input_stream = ffmpeg.input(input_path)
            
            # 出力設定
            output_kwargs = {
                'acodec': self._get_audio_codec(job.format),
                'ab': f'{job.bitrate}k',
                'ar': '44100',  # サンプリングレート
                'ac': '2',      # ステレオ
            }
            
            output_stream = ffmpeg.output(input_stream, output_path, **output_kwargs)
            
            # 実行
            ffmpeg.run(output_stream, overwrite_output=True, quiet=True)
            
            self.logger.info(f"音声変換完了: {output_path}")
            
        except ffmpeg.Error as e:
            error_msg = f"FFmpegエラー: {e}"
            self.logger.error(error_msg)
            raise RecordingError(error_msg)
    
    def _get_audio_codec(self, format: str) -> str:
        """音声形式に対応するコーデックを取得"""
        codec_map = {
            'aac': 'aac',
            'mp3': 'libmp3lame',
            'wav': 'pcm_s16le',
            'flac': 'flac',
            'ogg': 'libvorbis'
        }
        
        return codec_map.get(format.lower(), 'aac')
    
    def _add_metadata(self, job: RecordingJob):
        """録音ファイルにメタデータを追加"""
        try:
            # 番組情報を取得
            program = self.program_manager.get_current_program(job.station_id)
            
            # ffmpeg-pythonを使用してメタデータを追加
            metadata = {
                'title': job.program_title,
                'album': f"{job.station_id}_{job.start_time.strftime('%Y%m%d')}",
                'date': job.start_time.strftime('%Y-%m-%d'),
                'comment': f"Recorded from Radiko - {job.station_id}"
            }
            
            if program and program.performers:
                metadata['artist'] = ', '.join(program.performers)
            
            # 一時ファイルに出力
            temp_path = job.output_path + '.tmp'
            
            input_stream = ffmpeg.input(job.output_path)
            output_stream = ffmpeg.output(
                input_stream, temp_path,
                **{'metadata': f"{k}={v}" for k, v in metadata.items()},
                acodec='copy'
            )
            
            ffmpeg.run(output_stream, overwrite_output=True, quiet=True)
            
            # 元ファイルを置き換え
            shutil.move(temp_path, job.output_path)
            
            self.logger.info(f"メタデータ追加完了: {job.id}")
            
        except Exception as e:
            self.logger.warning(f"メタデータ追加エラー: {e}")
            # メタデータ追加に失敗しても録音は成功とする
    
    def _handle_job_error(self, job: RecordingJob, error_message: str):
        """ジョブエラーを処理"""
        job.error_message = error_message
        job.retry_count += 1
        
        if job.retry_count <= self.max_retries:
            job.status = RecordingStatus.PENDING
            self.logger.info(f"録音リトライ {job.id} ({job.retry_count}/{self.max_retries})")
            
            # 短時間待機後に再キューイング
            threading.Timer(10, self._queue_job, args=[job]).start()
        else:
            job.status = RecordingStatus.FAILED
            job.completed_at = datetime.now()
            self.logger.error(f"録音失敗 {job.id}: {error_message}")
    
    def get_job_status(self, job_id: str) -> Optional[RecordingJob]:
        """ジョブステータスを取得"""
        return self.jobs.get(job_id)
    
    def get_job_progress(self, job_id: str) -> Optional[RecordingProgress]:
        """ジョブ進捗を取得"""
        return self.job_progress.get(job_id)
    
    def get_active_jobs(self) -> List[RecordingJob]:
        """アクティブなジョブ一覧を取得"""
        with self.lock:
            return [job for job in self.jobs.values() 
                   if job.status in [RecordingStatus.PREPARING, RecordingStatus.RECORDING, RecordingStatus.PROCESSING]]
    
    def get_all_jobs(self) -> List[RecordingJob]:
        """全ジョブ一覧を取得"""
        return list(self.jobs.values())
    
    def cancel_job(self, job_id: str) -> bool:
        """ジョブをキャンセル"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        if job.status in [RecordingStatus.COMPLETED, RecordingStatus.FAILED, RecordingStatus.CANCELLED]:
            return False
        
        # アクティブなジョブの場合はスレッドを中断
        with self.lock:
            if job_id in self.active_jobs:
                # 実際の中断処理は複雑なので、ここでは状態変更のみ
                job.status = RecordingStatus.CANCELLED
                job.completed_at = datetime.now()
                self.logger.info(f"録音キャンセル: {job_id}")
                return True
        
        # 未実行のジョブはステータスを変更
        job.status = RecordingStatus.CANCELLED
        job.completed_at = datetime.now()
        self.logger.info(f"録音キャンセル: {job_id}")
        return True
    
    def add_progress_callback(self, callback: Callable[[RecordingProgress], None]):
        """進捗コールバックを追加"""
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[RecordingProgress], None]):
        """進捗コールバックを削除"""
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def save_jobs_to_file(self, file_path: str):
        """ジョブ情報をファイルに保存"""
        try:
            jobs_data = [job.to_dict() for job in self.jobs.values()]
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(jobs_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"ジョブ情報を保存: {file_path}")
        except Exception as e:
            self.logger.error(f"ジョブ保存エラー: {e}")
    
    def load_jobs_from_file(self, file_path: str):
        """ファイルからジョブ情報を読み込み"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                jobs_data = json.load(f)
            
            for job_data in jobs_data:
                job = RecordingJob.from_dict(job_data)
                self.jobs[job.id] = job
            
            self.logger.info(f"ジョブ情報を読み込み: {file_path} ({len(jobs_data)} 件)")
        except Exception as e:
            self.logger.error(f"ジョブ読み込みエラー: {e}")
    
    def cleanup_old_jobs(self, retention_days: int = 30):
        """古いジョブ情報を削除"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        with self.lock:
            jobs_to_remove = [
                job_id for job_id, job in self.jobs.items()
                if job.completed_at and job.completed_at < cutoff_date
                and job.status in [RecordingStatus.COMPLETED, RecordingStatus.FAILED, RecordingStatus.CANCELLED]
            ]
            
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
        
        self.logger.info(f"古いジョブ {len(jobs_to_remove)} 件を削除")
    
    def shutdown(self):
        """録音マネージャーを終了"""
        self.logger.info("録音マネージャーを終了中...")
        
        # 停止フラグを設定
        self.stop_event.set()
        
        # キューに残っているタスクを完了
        while not self.job_queue.empty():
            try:
                self.job_queue.get_nowait()
                self.job_queue.task_done()
            except queue.Empty:
                break
        
        # ワーカースレッドの終了を待機
        for worker in self.worker_threads:
            worker.join(timeout=5)
        
        self.logger.info("録音マネージャーを終了しました")


class RecordingError(Exception):
    """録音エラーの例外クラス"""
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
        from .program_info import ProgramInfoManager
        from .streaming import StreamingManager
        
        # 録音マネージャーのテスト
        authenticator = RadikoAuthenticator()
        program_manager = ProgramInfoManager()
        streaming_manager = StreamingManager(authenticator)
        
        recording_manager = RecordingManager(
            authenticator, program_manager, streaming_manager
        )
        
        # 進捗コールバックを設定
        def progress_callback(progress: RecordingProgress):
            print(f"進捗: {progress.progress_percent:.1f}% - {progress.status.value}")
        
        recording_manager.add_progress_callback(progress_callback)
        
        # テスト録音ジョブを作成
        now = datetime.now()
        job_id = recording_manager.create_recording_job(
            station_id="TBS",
            program_title="テスト番組",
            start_time=now,
            end_time=now + timedelta(minutes=1),
            format="aac",
            bitrate=128
        )
        
        print(f"録音ジョブ作成: {job_id}")
        
        # 録音をスケジュール
        recording_manager.schedule_recording(job_id)
        
        # 進捗監視
        while True:
            job = recording_manager.get_job_status(job_id)
            if job.status in [RecordingStatus.COMPLETED, RecordingStatus.FAILED, RecordingStatus.CANCELLED]:
                break
            
            progress = recording_manager.get_job_progress(job_id)
            if progress:
                print(f"ステータス: {progress.status.value}, 進捗: {progress.progress_percent:.1f}%")
            
            time.sleep(5)
        
        print(f"録音終了: {job.status.value}")
        
        # 終了処理
        recording_manager.shutdown()
        
    except Exception as e:
        print(f"録音テストエラー: {e}")
        sys.exit(1)