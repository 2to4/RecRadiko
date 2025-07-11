"""
ファイル管理モジュール

このモジュールはRecRadikoの録音ファイル管理を行います。
- ファイルの自動整理・命名
- メタデータ管理
- 古いファイルの自動削除
- ディスク容量監視
"""

import os
import shutil
import json
import logging
import threading
import time
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, COMM
from mutagen.mp4 import MP4
from mutagen.flac import FLAC

from .logging_config import get_logger


@dataclass
class FileMetadata:
    """ファイルメタデータ情報"""
    file_path: str
    station_id: str
    program_title: str
    recorded_at: datetime
    start_time: datetime
    end_time: datetime
    file_size: int
    duration_seconds: int
    format: str
    bitrate: int
    performers: List[str] = field(default_factory=list)
    genre: str = ""
    description: str = ""
    checksum: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['recorded_at'] = self.recorded_at.isoformat()
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        data['created_at'] = self.created_at.isoformat()
        data['last_accessed'] = self.last_accessed.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileMetadata':
        """辞書から復元"""
        data = data.copy()
        data['recorded_at'] = datetime.fromisoformat(data['recorded_at'])
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        data['end_time'] = datetime.fromisoformat(data['end_time'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        return cls(**data)


@dataclass
class StorageInfo:
    """ストレージ情報"""
    total_space: int
    used_space: int
    free_space: int
    recording_files_size: int
    file_count: int
    
    @property
    def usage_percent(self) -> float:
        """使用率を返す"""
        if self.total_space == 0:
            return 0.0
        return (self.used_space / self.total_space) * 100
    
    @property
    def free_space_gb(self) -> float:
        """空き容量をGBで返す"""
        return self.free_space / (1024 ** 3)


class FileManager:
    """ファイル管理クラス"""
    
    def __init__(self, 
                 base_dir: str = "./recordings",
                 metadata_file: str = "metadata.json",
                 retention_days: int = 30,
                 min_free_space_gb: float = 10.0,
                 auto_cleanup_enabled: bool = True):
        
        self.base_dir = Path(base_dir)
        self.metadata_file = self.base_dir / metadata_file
        self.retention_days = retention_days
        self.min_free_space_gb = min_free_space_gb
        self.auto_cleanup_enabled = auto_cleanup_enabled
        
        # ディレクトリを作成
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # ログ設定
        self.logger = get_logger(__name__)
        
        # メタデータキャッシュ
        self.metadata_cache: Dict[str, FileMetadata] = {}
        self.cache_lock = threading.RLock()
        
        # 自動クリーンアップタイマー
        self.cleanup_timer: Optional[threading.Timer] = None
        
        # メタデータを読み込み
        self._load_metadata()
        
        # 自動クリーンアップを開始
        if self.auto_cleanup_enabled:
            self._start_auto_cleanup()
    
    def _load_metadata(self):
        """メタデータファイルを読み込み"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                with self.cache_lock:
                    for item in data.get('files', []):
                        metadata = FileMetadata.from_dict(item)
                        self.metadata_cache[metadata.file_path] = metadata
                
                self.logger.info(f"メタデータ読み込み完了: {len(self.metadata_cache)} 件")
            else:
                self.logger.info("メタデータファイルが存在しません。新規作成します。")
                self._save_metadata()
                
        except Exception as e:
            self.logger.error(f"メタデータ読み込みエラー: {e}")
    
    def _save_metadata(self):
        """メタデータをファイルに保存"""
        try:
            with self.cache_lock:
                data = {
                    'version': '1.0',
                    'updated_at': datetime.now().isoformat(),
                    'files': [metadata.to_dict() for metadata in self.metadata_cache.values()]
                }
            
            # 一時ファイルに書き込み後、原子的に置換
            temp_file = self.metadata_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            temp_file.replace(self.metadata_file)
            
        except Exception as e:
            self.logger.error(f"メタデータ保存エラー: {e}")
    
    def generate_file_path(self, 
                          station_id: str,
                          program_title: str,
                          start_time: datetime,
                          format: str = "aac") -> str:
        """ファイルパスを生成"""
        
        # 日付ベースのディレクトリ構造
        date_dir = start_time.strftime('%Y/%m/%d')
        station_dir = station_id
        
        # ファイル名を生成
        safe_title = self._sanitize_filename(program_title)
        timestamp = start_time.strftime('%Y%m%d_%H%M')
        
        # 重複を避けるためのサフィックス
        base_filename = f"{station_id}_{safe_title}_{timestamp}"
        filename = f"{base_filename}.{format}"
        
        # 完全パスを構築
        full_dir = self.base_dir / date_dir / station_dir
        full_path = full_dir / filename
        
        # 重複チェック
        counter = 1
        while full_path.exists():
            filename = f"{base_filename}_{counter}.{format}"
            full_path = full_dir / filename
            counter += 1
        
        # ディレクトリを作成
        full_dir.mkdir(parents=True, exist_ok=True)
        
        return str(full_path)
    
    def _sanitize_filename(self, filename: str) -> str:
        """ファイル名を安全な文字に変換"""
        # 不正な文字を置換
        unsafe_chars = '<>:"/\\|?*\0'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        
        # 連続するアンダースコアを単一に変換
        while '__' in filename:
            filename = filename.replace('__', '_')
        
        # 前後の空白とピリオドを削除
        filename = filename.strip(' .')
        
        # 長すぎる場合は切り詰め
        if len(filename) > 100:
            filename = filename[:100].rstrip('_')
        
        # 空文字列の場合はデフォルト名
        if not filename:
            filename = "untitled"
        
        return filename
    
    def register_file(self, 
                     file_path: str,
                     station_id: str,
                     program_title: str,
                     start_time: datetime,
                     end_time: datetime,
                     format: str,
                     bitrate: int,
                     performers: List[str] = None,
                     genre: str = "",
                     description: str = "") -> bool:
        """ファイルをメタデータに登録"""
        
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                self.logger.error(f"ファイルが存在しません: {file_path}")
                return False
            
            # ファイル情報を取得
            stat_info = file_path_obj.stat()
            file_size = stat_info.st_size
            
            # チェックサムを計算
            checksum = self._calculate_checksum(file_path)
            
            # 継続時間を計算
            duration_seconds = int((end_time - start_time).total_seconds())
            
            # メタデータを作成
            metadata = FileMetadata(
                file_path=file_path,
                station_id=station_id,
                program_title=program_title,
                recorded_at=datetime.now(),
                start_time=start_time,
                end_time=end_time,
                file_size=file_size,
                duration_seconds=duration_seconds,
                format=format,
                bitrate=bitrate,
                performers=performers or [],
                genre=genre,
                description=description,
                checksum=checksum
            )
            
            # キャッシュに追加
            with self.cache_lock:
                self.metadata_cache[file_path] = metadata
            
            # ファイルにメタデータタグを追加
            self._add_file_metadata_tags(metadata)
            
            # メタデータファイルを保存
            self._save_metadata()
            
            self.logger.info(f"ファイル登録完了: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル登録エラー: {e}")
            return False
    
    def _calculate_checksum(self, file_path: str) -> str:
        """ファイルのMD5チェックサムを計算"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.warning(f"チェックサム計算エラー: {e}")
            return ""
    
    def _add_file_metadata_tags(self, metadata: FileMetadata):
        """ファイルにメタデータタグを追加"""
        try:
            file_path = metadata.file_path
            format_lower = metadata.format.lower()
            
            if format_lower == 'mp3':
                self._add_mp3_tags(metadata)
            elif format_lower in ['mp4', 'aac', 'm4a']:
                self._add_mp4_tags(metadata)
            elif format_lower == 'flac':
                self._add_flac_tags(metadata)
            else:
                self.logger.debug(f"メタデータタグ未対応形式: {metadata.format}")
                
        except Exception as e:
            self.logger.warning(f"メタデータタグ追加エラー: {e}")
    
    def _add_mp3_tags(self, metadata: FileMetadata):
        """MP3ファイルにID3タグを追加"""
        try:
            audio = ID3(metadata.file_path)
            
            audio.add(TIT2(encoding=3, text=metadata.program_title))
            if metadata.performers:
                audio.add(TPE1(encoding=3, text=metadata.performers))
            
            album_name = f"{metadata.station_id}_{metadata.start_time.strftime('%Y%m%d')}"
            audio.add(TALB(encoding=3, text=album_name))
            audio.add(TDRC(encoding=3, text=metadata.start_time.strftime('%Y')))
            
            comment = f"Recorded from Radiko - {metadata.station_id}"
            audio.add(COMM(encoding=3, lang='jpn', desc='comment', text=comment))
            
            audio.save()
            
        except Exception as e:
            self.logger.warning(f"MP3タグ追加エラー: {e}")
    
    def _add_mp4_tags(self, metadata: FileMetadata):
        """MP4/AACファイルにタグを追加"""
        try:
            audio = MP4(metadata.file_path)
            
            audio['©nam'] = metadata.program_title
            if metadata.performers:
                audio['©ART'] = metadata.performers
            
            album_name = f"{metadata.station_id}_{metadata.start_time.strftime('%Y%m%d')}"
            audio['©alb'] = album_name
            audio['©day'] = metadata.start_time.strftime('%Y')
            
            comment = f"Recorded from Radiko - {metadata.station_id}"
            audio['©cmt'] = comment
            
            audio.save()
            
        except Exception as e:
            self.logger.warning(f"MP4タグ追加エラー: {e}")
    
    def _add_flac_tags(self, metadata: FileMetadata):
        """FLACファイルにタグを追加"""
        try:
            audio = FLAC(metadata.file_path)
            
            audio['TITLE'] = metadata.program_title
            if metadata.performers:
                audio['ARTIST'] = metadata.performers
            
            album_name = f"{metadata.station_id}_{metadata.start_time.strftime('%Y%m%d')}"
            audio['ALBUM'] = album_name
            audio['DATE'] = metadata.start_time.strftime('%Y')
            
            comment = f"Recorded from Radiko - {metadata.station_id}"
            audio['COMMENT'] = comment
            
            audio.save()
            
        except Exception as e:
            self.logger.warning(f"FLACタグ追加エラー: {e}")
    
    def get_file_metadata(self, file_path: str) -> Optional[FileMetadata]:
        """ファイルのメタデータを取得"""
        with self.cache_lock:
            metadata = self.metadata_cache.get(file_path)
            if metadata:
                # アクセス時刻を更新
                metadata.last_accessed = datetime.now()
                self._save_metadata()
            return metadata
    
    def list_files(self, 
                  station_id: Optional[str] = None,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None,
                  program_title_filter: Optional[str] = None) -> List[FileMetadata]:
        """ファイル一覧を取得"""
        
        with self.cache_lock:
            files = list(self.metadata_cache.values())
        
        # フィルタリング
        if station_id:
            files = [f for f in files if f.station_id == station_id]
        
        if start_date:
            files = [f for f in files if f.start_time >= start_date]
        
        if end_date:
            files = [f for f in files if f.end_time <= end_date]
        
        if program_title_filter:
            filter_lower = program_title_filter.lower()
            files = [f for f in files if filter_lower in f.program_title.lower()]
        
        # 録音日時の降順でソート
        files.sort(key=lambda x: x.start_time, reverse=True)
        
        return files
    
    def search_files(self, query: str) -> List[FileMetadata]:
        """ファイルを検索"""
        query_lower = query.lower()
        
        with self.cache_lock:
            results = []
            for metadata in self.metadata_cache.values():
                # タイトル、出演者、説明で検索
                if (query_lower in metadata.program_title.lower() or
                    any(query_lower in performer.lower() for performer in metadata.performers) or
                    query_lower in metadata.description.lower() or
                    query_lower in metadata.station_id.lower()):
                    results.append(metadata)
        
        # 関連度でソート（簡易実装）
        def relevance_score(metadata: FileMetadata) -> int:
            score = 0
            if query_lower in metadata.program_title.lower():
                score += 10
            if any(query_lower in performer.lower() for performer in metadata.performers):
                score += 5
            if query_lower in metadata.station_id.lower():
                score += 3
            if query_lower in metadata.description.lower():
                score += 1
            return score
        
        results.sort(key=relevance_score, reverse=True)
        return results
    
    def delete_file(self, file_path: str, remove_file: bool = True) -> bool:
        """ファイルを削除"""
        try:
            # メタデータから削除
            with self.cache_lock:
                if file_path in self.metadata_cache:
                    del self.metadata_cache[file_path]
            
            # 実際のファイルを削除
            if remove_file:
                file_path_obj = Path(file_path)
                if file_path_obj.exists():
                    file_path_obj.unlink()
                    self.logger.info(f"ファイル削除: {file_path}")
                
                # 空のディレクトリを削除
                self._cleanup_empty_directories(file_path_obj.parent)
            
            # メタデータファイルを保存
            self._save_metadata()
            
            return True
            
        except Exception as e:
            self.logger.error(f"ファイル削除エラー: {e}")
            return False
    
    def _cleanup_empty_directories(self, directory: Path):
        """空のディレクトリを削除"""
        try:
            # ベースディレクトリより上は削除しない
            if not str(directory).startswith(str(self.base_dir)):
                return
            
            # ディレクトリが空の場合は削除
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()
                self.logger.debug(f"空ディレクトリ削除: {directory}")
                
                # 親ディレクトリも再帰的にチェック
                self._cleanup_empty_directories(directory.parent)
                
        except Exception as e:
            self.logger.debug(f"ディレクトリ削除エラー: {e}")
    
    def get_storage_info(self) -> StorageInfo:
        """ストレージ情報を取得"""
        try:
            # ディスク使用量を取得
            stat = shutil.disk_usage(self.base_dir)
            total_space = stat[0]  # total
            free_space = stat[2]   # free
            used_space = stat[0] - stat[2]  # total - free
            
            # 録音ファイルのサイズと件数を計算
            recording_files_size = 0
            file_count = 0
            
            with self.cache_lock:
                for metadata in self.metadata_cache.values():
                    if Path(metadata.file_path).exists():
                        recording_files_size += metadata.file_size
                        file_count += 1
            
            return StorageInfo(
                total_space=total_space,
                used_space=used_space,
                free_space=free_space,
                recording_files_size=recording_files_size,
                file_count=file_count
            )
            
        except Exception as e:
            self.logger.error(f"ストレージ情報取得エラー: {e}")
            return StorageInfo(0, 0, 0, 0, 0)
    
    def cleanup_old_files(self, retention_days: Optional[int] = None) -> Tuple[int, int]:
        """古いファイルを削除"""
        if retention_days is None:
            retention_days = self.retention_days
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        deleted_count = 0
        freed_space = 0
        
        with self.cache_lock:
            files_to_delete = []
            for file_path, metadata in self.metadata_cache.items():
                if metadata.recorded_at < cutoff_date:
                    files_to_delete.append((file_path, metadata))
        
        # ファイルを削除
        for file_path, metadata in files_to_delete:
            # ファイルサイズを取得（削除前に）
            try:
                file_size = Path(file_path).stat().st_size
            except (OSError, FileNotFoundError):
                file_size = metadata.file_size or 0
            
            if self.delete_file(file_path):
                deleted_count += 1
                freed_space += file_size
        
        self.logger.info(f"古いファイル削除: {deleted_count} 件, {freed_space / (1024**2):.1f} MB")
        return deleted_count, freed_space
    
    def cleanup_by_disk_space(self, target_free_gb: Optional[float] = None) -> Tuple[int, int]:
        """ディスク容量不足時のクリーンアップ"""
        if target_free_gb is None:
            target_free_gb = self.min_free_space_gb
        
        storage_info = self.get_storage_info()
        current_free_gb = storage_info.free_space_gb
        
        if current_free_gb >= target_free_gb:
            return 0, 0  # クリーンアップ不要
        
        need_to_free = int((target_free_gb - current_free_gb) * (1024**3))
        
        # 古いファイルから順に削除
        with self.cache_lock:
            files_by_date = sorted(
                self.metadata_cache.items(),
                key=lambda x: x[1].last_accessed
            )
        
        deleted_count = 0
        freed_space = 0
        
        for file_path, metadata in files_by_date:
            if freed_space >= need_to_free:
                break
            
            if self.delete_file(file_path):
                deleted_count += 1
                freed_space += metadata.file_size
        
        self.logger.info(f"容量不足解消: {deleted_count} 件削除, {freed_space / (1024**2):.1f} MB解放")
        return deleted_count, freed_space
    
    def verify_files(self) -> List[str]:
        """ファイルの整合性をチェック"""
        corrupted_files = []
        missing_files = []
        
        with self.cache_lock:
            for file_path, metadata in list(self.metadata_cache.items()):
                file_path_obj = Path(file_path)
                
                # ファイルの存在チェック
                if not file_path_obj.exists():
                    missing_files.append(file_path)
                    self.logger.error(f"ファイルが存在しません: {file_path}")
                    # メタデータから削除
                    del self.metadata_cache[file_path]
                    continue
                
                # チェックサムチェック（有効な場合のみ）
                if metadata.checksum:
                    current_checksum = self._calculate_checksum(file_path)
                    if current_checksum != metadata.checksum:
                        corrupted_files.append(file_path)
        
        # メタデータを保存（削除されたエントリを反映）
        if missing_files:
            self._save_metadata()
        
        if missing_files:
            self.logger.warning(f"見つからないファイル: {len(missing_files)} 件")
        
        if corrupted_files:
            self.logger.warning(f"破損ファイル: {len(corrupted_files)} 件")
        
        # 破損ファイルと見つからないファイルの両方を返す
        return missing_files + corrupted_files
    
    def _start_auto_cleanup(self):
        """自動クリーンアップを開始"""
        def cleanup_task():
            try:
                # 古いファイルのクリーンアップ
                self.cleanup_old_files()
                
                # ディスク容量チェック
                storage_info = self.get_storage_info()
                if storage_info.free_space_gb < self.min_free_space_gb:
                    self.cleanup_by_disk_space()
                
                # ファイル整合性チェック
                self.verify_files()
                
            except Exception as e:
                self.logger.error(f"自動クリーンアップエラー: {e}")
            finally:
                # 次回の実行をスケジュール（24時間後）
                if self.auto_cleanup_enabled:
                    self.cleanup_timer = threading.Timer(86400, cleanup_task)  # 24時間
                    self.cleanup_timer.start()
        
        # 初回実行をスケジュール（1時間後）
        self.cleanup_timer = threading.Timer(3600, cleanup_task)  # 1時間後
        self.cleanup_timer.start()
        
        self.logger.info("自動クリーンアップを開始しました")
    
    def stop_auto_cleanup(self):
        """自動クリーンアップを停止"""
        if self.cleanup_timer:
            self.cleanup_timer.cancel()
            self.cleanup_timer = None
        
        self.logger.info("自動クリーンアップを停止しました")
    
    def export_metadata(self, export_path: str, format: str = "json"):
        """メタデータをエクスポート"""
        try:
            with self.cache_lock:
                data = [metadata.to_dict() for metadata in self.metadata_cache.values()]
            
            export_path_obj = Path(export_path)
            
            if format.lower() == "json":
                with open(export_path_obj, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            elif format.lower() == "csv":
                import csv
                
                if data:
                    with open(export_path_obj, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
            
            else:
                raise ValueError(f"未対応の形式: {format}")
            
            self.logger.info(f"メタデータエクスポート完了: {export_path}")
            
        except Exception as e:
            self.logger.error(f"メタデータエクスポートエラー: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        with self.cache_lock:
            files = list(self.metadata_cache.values())
        
        if not files:
            return {}
        
        # 基本統計
        total_files = len(files)
        total_duration = sum(f.duration_seconds for f in files)
        total_size = sum(f.file_size for f in files)
        
        # 放送局別統計
        station_stats = {}
        format_stats = {}
        
        for file_metadata in files:
            station = file_metadata.station_id
            format_name = file_metadata.format
            
            # 放送局別
            if station not in station_stats:
                station_stats[station] = {'count': 0, 'duration': 0, 'size': 0}
            station_stats[station]['count'] += 1
            station_stats[station]['duration'] += file_metadata.duration_seconds
            station_stats[station]['size'] += file_metadata.file_size
            
            # 形式別
            if format_name not in format_stats:
                format_stats[format_name] = {'count': 0, 'duration': 0, 'size': 0}
            format_stats[format_name]['count'] += 1
            format_stats[format_name]['duration'] += file_metadata.duration_seconds
            format_stats[format_name]['size'] += file_metadata.file_size
        
        # 日付範囲
        dates = [f.recorded_at for f in files]
        oldest_date = min(dates) if dates else None
        newest_date = max(dates) if dates else None
        
        return {
            'total_files': total_files,
            'total_duration_hours': total_duration / 3600,
            'total_size_gb': total_size / (1024**3),
            'average_file_size_mb': (total_size / total_files) / (1024**2) if total_files > 0 else 0,
            'oldest_recording': oldest_date.isoformat() if oldest_date else None,
            'newest_recording': newest_date.isoformat() if newest_date else None,
            'stations': station_stats,
            'formats': format_stats
        }
    
    def shutdown(self):
        """ファイルマネージャーを終了"""
        self.logger.info("ファイルマネージャーを終了中...")
        
        # 自動クリーンアップを停止
        self.stop_auto_cleanup()
        
        # メタデータを保存
        self._save_metadata()
        
        self.logger.info("ファイルマネージャーを終了しました")


class FileManagerError(Exception):
    """ファイル管理エラーの例外クラス"""
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
        # ファイルマネージャーのテスト
        file_manager = FileManager(base_dir="./test_recordings")
        
        # ストレージ情報を表示
        storage_info = file_manager.get_storage_info()
        print(f"ストレージ情報:")
        print(f"  総容量: {storage_info.total_space / (1024**3):.1f} GB")
        print(f"  使用済み: {storage_info.used_space / (1024**3):.1f} GB")
        print(f"  空き容量: {storage_info.free_space_gb:.1f} GB")
        print(f"  録音ファイル: {storage_info.file_count} 件, {storage_info.recording_files_size / (1024**2):.1f} MB")
        
        # ファイル一覧を表示
        files = file_manager.list_files()
        print(f"\\n録音ファイル: {len(files)} 件")
        
        for file_metadata in files[:5]:  # 最初の5件
            print(f"  {file_metadata.program_title} ({file_metadata.station_id}) - {file_metadata.start_time.strftime('%Y-%m-%d %H:%M')}")
        
        # 統計情報を表示
        stats = file_manager.get_statistics()
        if stats:
            print(f"\\n統計情報:")
            print(f"  総ファイル数: {stats['total_files']}")
            print(f"  総録音時間: {stats['total_duration_hours']:.1f} 時間")
            print(f"  総ファイルサイズ: {stats['total_size_gb']:.2f} GB")
        
        # 終了処理
        file_manager.shutdown()
        
    except Exception as e:
        print(f"ファイルマネージャーテストエラー: {e}")
        sys.exit(1)