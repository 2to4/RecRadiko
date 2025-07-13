"""
番組情報取得モジュール

このモジュールはRadikoの番組情報を取得・管理します。
- 放送局一覧の取得
- 番組表の取得
- 番組情報のキャッシュ
- 番組検索機能
"""

import sqlite3
import xml.etree.ElementTree as ET
import requests
import logging
import threading
import pytz
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from .auth import RadikoAuthenticator, AuthenticationError
from .logging_config import get_logger


@dataclass
class Station:
    """放送局情報"""
    id: str
    name: str
    ascii_name: str
    area_id: str
    logo_url: str = ""
    banner_url: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Station':
        return cls(**data)


@dataclass
class Program:
    """番組情報"""
    id: str
    station_id: str
    title: str
    start_time: datetime
    end_time: datetime
    duration: int  # 分単位
    description: str = ""
    performers: List[str] = None
    genre: str = ""
    sub_genre: str = ""
    
    def __post_init__(self):
        if self.performers is None:
            self.performers = []
        if not self.duration:
            self.duration = int((self.end_time - self.start_time).total_seconds() / 60)
    
    @property
    def duration_minutes(self) -> int:
        return self.duration
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['start_time'] = self.start_time.isoformat()
        data['end_time'] = self.end_time.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Program':
        data = data.copy()
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        data['end_time'] = datetime.fromisoformat(data['end_time'])
        return cls(**data)


@dataclass
class ProgramInfo:
    """番組情報データクラス（タイムフリー対応）"""
    
    # 基本情報
    program_id: str
    station_id: str
    station_name: str
    title: str
    start_time: datetime
    end_time: datetime
    
    # 詳細情報
    description: str = ""
    performers: List[str] = None
    genre: str = ""
    
    # タイムフリー関連
    is_timefree_available: bool = False
    timefree_end_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.performers is None:
            self.performers = []
    
    @property
    def duration_minutes(self) -> int:
        """番組時間（分）"""
        return int((self.end_time - self.start_time).total_seconds() / 60)
    
    @property
    def duration_seconds(self) -> int:
        """番組時間（秒）"""
        return int((self.end_time - self.start_time).total_seconds())
    
    def to_filename(self, format: str = "mp3") -> str:
        """録音ファイル名生成
        
        Args:
            format: ファイル形式
            
        Returns:
            str: ファイル名
            
        Format:
            {STATION_ID}_{YYYYMMDD}_{safe_title}.{format}
        """
        import re
        date_str = self.start_time.strftime('%Y%m%d')
        safe_title = re.sub(r'[^\w\-_\.]', '_', self.title)
        safe_title = re.sub(r'_+', '_', safe_title).strip('_')
        return f"{self.station_id}_{date_str}_{safe_title}.{format}"
    
    def to_metadata(self) -> Dict[str, str]:
        """ID3タグメタデータ生成
        
        Returns:
            Dict[str, str]: メタデータ辞書
        """
        return {
            'title': self.title,
            'artist': ', '.join(self.performers) if self.performers else self.station_name,
            'album': self.station_name,
            'date': self.start_time.strftime('%Y-%m-%d'),
            'genre': 'Radio',
            'comment': self.description
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式への変換（キャッシュ用）"""
        return {
            'program_id': self.program_id,
            'station_id': self.station_id,
            'station_name': self.station_name,
            'title': self.title,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'description': self.description,
            'performers': self.performers,
            'genre': self.genre,
            'is_timefree_available': self.is_timefree_available,
            'timefree_end_time': self.timefree_end_time.isoformat() if self.timefree_end_time else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgramInfo':
        """辞書からの復元（キャッシュ用）"""
        data = data.copy()
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        data['end_time'] = datetime.fromisoformat(data['end_time'])
        if data.get('timefree_end_time'):
            data['timefree_end_time'] = datetime.fromisoformat(data['timefree_end_time'])
        return cls(**data)


class ProgramInfoManager:
    """番組情報管理クラス"""
    
    # Radiko API エンドポイント
    STATION_LIST_URL = "https://radiko.jp/v3/station/list/{area_id}.xml"
    PROGRAM_URL = "https://radiko.jp/v3/program/date/{date}/{area_id}.xml"
    PROGRAM_DETAIL_URL = "https://radiko.jp/v3/program/station/weekly/{station_id}.xml"
    
    def __init__(self, db_path: str = "radiko.db", area_id: str = "JP13", 
                 authenticator: Optional[RadikoAuthenticator] = None):
        self.db_path = Path(db_path)
        self.area_id = area_id
        self.authenticator = authenticator or RadikoAuthenticator()
        
        # セッション設定
        self.session = requests.Session()
        self.session.timeout = 30
        
        # 日本時間のタイムゾーン設定
        self.jst = pytz.timezone('Asia/Tokyo')
        
        # ログ設定
        self.logger = get_logger(__name__)
        
        # データベースロック
        self.db_lock = threading.RLock()
        
        # キャッシュ設定
        self.cache_duration_hours = 24
        self.last_station_update = None
        self.cached_stations = []
        
        # データベースを初期化
        self.init_database()
    
    def init_database(self):
        """データベースの初期化"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(str(self.db_path)) as conn:
                # 放送局テーブル
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS stations (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        ascii_name TEXT,
                        area_id TEXT NOT NULL,
                        logo_url TEXT,
                        banner_url TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 番組テーブル
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS programs (
                        id TEXT PRIMARY KEY,
                        station_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP NOT NULL,
                        duration INTEGER,
                        description TEXT,
                        performers TEXT,
                        genre TEXT,
                        sub_genre TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (station_id) REFERENCES stations(id)
                    )
                ''')
                
                # インデックス作成
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_programs_station_time 
                    ON programs(station_id, start_time)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_programs_time 
                    ON programs(start_time, end_time)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_programs_title 
                    ON programs(title)
                ''')
                
                conn.commit()
                
            self.logger.info("データベース初期化完了")
            
        except Exception as e:
            self.logger.error(f"データベース初期化エラー: {e}")
            raise ProgramInfoError(f"データベースの初期化に失敗しました: {e}")
    
    def fetch_station_list(self, force_update: bool = False) -> List[Station]:
        """放送局リストを取得"""
        try:
            # キャッシュをチェック
            if not force_update and self._is_station_cache_valid():
                self.logger.info("キャッシュから放送局リストを取得")
                return self.cached_stations
            
            self.logger.info(f"放送局リストを取得中: area_id={self.area_id}")
            
            url = self.STATION_LIST_URL.format(area_id=self.area_id)
            response = self.session.get(url)
            response.raise_for_status()
            
            # XMLをパース
            root = ET.fromstring(response.content)
            stations = []
            
            for station_elem in root.findall('.//station'):
                station = Station(
                    id=self._get_element_text(station_elem, 'id'),
                    name=self._get_element_text(station_elem, 'name'),
                    ascii_name=self._get_element_text(station_elem, 'ascii_name'),
                    area_id=self.area_id,
                    logo_url=self._get_element_text(station_elem, 'logo'),
                    banner_url=self._get_element_text(station_elem, 'banner')
                )
                
                if station.id and station.name:  # 必須フィールドをチェック
                    stations.append(station)
            
            if not stations:
                raise ProgramInfoError("放送局リストが空です")
            
            # データベースに保存
            self._save_stations(stations)
            
            # キャッシュを更新
            self.cached_stations = stations
            self.last_station_update = datetime.now()
            
            self.logger.info(f"放送局リスト取得完了: {len(stations)}局")
            return stations
            
        except requests.RequestException as e:
            self.logger.error(f"放送局リスト取得エラー: {e}")
            # キャッシュから取得を試行
            cached_stations = self._get_cached_stations()
            if cached_stations:
                self.logger.info("キャッシュから放送局リストを取得（フォールバック）")
                return cached_stations
            raise ProgramInfoError(f"放送局リストの取得に失敗しました: {e}")
        except ET.ParseError as e:
            self.logger.error(f"XML解析エラー: {e}")
            raise ProgramInfoError(f"放送局リストの解析に失敗しました: {e}")
        except Exception as e:
            self.logger.error(f"放送局リスト処理エラー: {e}")
            raise ProgramInfoError(f"放送局リストの処理に失敗しました: {e}")
    
    def fetch_program_guide(self, date: datetime, station_id: Optional[str] = None, 
                           force_update: bool = False) -> List[Program]:
        """番組表を取得"""
        try:
            date_str = date.strftime('%Y%m%d')
            
            # キャッシュをチェック
            if not force_update:
                cached_programs = self._get_cached_programs(date, station_id)
                if cached_programs:
                    self.logger.info(f"キャッシュから番組表を取得: {date_str}")
                    return cached_programs
            
            self.logger.info(f"番組表を取得中: {date_str}, area_id={self.area_id}")
            
            url = self.PROGRAM_URL.format(date=date_str, area_id=self.area_id)
            response = self.session.get(url)
            response.raise_for_status()
            
            # XMLをパース
            root = ET.fromstring(response.content)
            programs = []
            
            for station_elem in root.findall('.//station'):
                current_station_id = station_elem.get('id', '')
                
                # 特定の放送局のみを取得する場合
                if station_id and current_station_id != station_id:
                    continue
                
                for prog_elem in station_elem.findall('.//prog'):
                    try:
                        program = self._parse_program_element(prog_elem, current_station_id)
                        if program:
                            programs.append(program)
                    except Exception as e:
                        self.logger.warning(f"番組解析エラー (station={current_station_id}): {e}")
                        continue
            
            if not programs and not station_id:
                self.logger.warning(f"番組データが空です: {date_str}")
            
            # データベースに保存
            if programs:
                self._save_programs(programs)
            
            self.logger.info(f"番組表取得完了: {len(programs)}番組")
            return programs
            
        except requests.RequestException as e:
            self.logger.error(f"番組表取得エラー: {e}")
            # キャッシュから取得を試行
            cached_programs = self._get_cached_programs(date, station_id)
            if cached_programs:
                self.logger.info("キャッシュから番組表を取得（フォールバック）")
                return cached_programs
            raise ProgramInfoError(f"番組表の取得に失敗しました: {e}")
        except ET.ParseError as e:
            self.logger.error(f"XML解析エラー: {e}")
            raise ProgramInfoError(f"番組表の解析に失敗しました: {e}")
        except Exception as e:
            self.logger.error(f"番組表処理エラー: {e}")
            raise ProgramInfoError(f"番組表の処理に失敗しました: {e}")
    
    def _parse_program_element(self, prog_elem, station_id: str) -> Optional[Program]:
        """番組要素をパース"""
        try:
            # 必須フィールドを取得
            start_time_str = prog_elem.get('ft', '')
            end_time_str = prog_elem.get('to', '')
            title = self._get_element_text(prog_elem, 'title')
            
            if not all([start_time_str, end_time_str, title]):
                return None
            
            # 時刻をJSTで解析
            start_time = self._parse_radiko_time(start_time_str)
            end_time = self._parse_radiko_time(end_time_str)
            
            # 出演者情報を解析
            performers = []
            pfm_elem = prog_elem.find('pfm')
            if pfm_elem is not None and pfm_elem.text:
                performers = [p.strip() for p in pfm_elem.text.split(',') if p.strip()]
            
            # 番組IDを生成
            program_id = f"{station_id}_{start_time_str}"
            
            program = Program(
                id=program_id,
                station_id=station_id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                duration=int((end_time - start_time).total_seconds() / 60),
                description=self._get_element_text(prog_elem, 'desc'),
                performers=performers,
                genre=self._get_element_text(prog_elem, 'genre'),
                sub_genre=self._get_element_text(prog_elem, 'sub_genre')
            )
            
            return program
            
        except Exception as e:
            self.logger.error(f"番組要素解析エラー: {e}")
            return None
    
    def _parse_radiko_time(self, time_str: str) -> datetime:
        """Radikoの時刻文字列をdatetimeに変換（複数形式対応）"""
        # 複数の時刻形式に対応
        time_formats = [
            '%Y%m%d%H%M%S',      # 20240101050000
            '%Y-%m-%dT%H:%M:%S', # 2024-01-01T05:00:00
            '%Y-%m-%d %H:%M:%S', # 2024-01-01 05:00:00
            '%Y%m%d%H%M',        # 202401010500
            '%Y%m%d',            # 20240101 (日付のみ)
        ]
        
        for fmt in time_formats:
            try:
                dt = datetime.strptime(time_str, fmt)
                return self.jst.localize(dt)
            except ValueError:
                continue
        
        # 全ての形式で失敗した場合
        raise ValueError(f"時刻の解析に失敗しました: {time_str}")
    
    def _get_element_text(self, parent, tag_name: str) -> str:
        """XML要素からテキストを安全に取得（堅牢化版）"""
        if parent is None:
            return ""
        
        try:
            elem = parent.find(tag_name)
            if elem is None or elem.text is None:
                return ""
            
            return str(elem.text).strip()
        except (AttributeError, TypeError):
            return ""
    
    def _is_station_cache_valid(self) -> bool:
        """放送局キャッシュが有効かどうかをチェック"""
        if not self.last_station_update or not self.cached_stations:
            return False
        
        cache_age = datetime.now() - self.last_station_update
        return cache_age.total_seconds() < (self.cache_duration_hours * 3600)
    
    def _save_stations(self, stations: List[Station]):
        """放送局情報をデータベースに保存"""
        try:
            with self.db_lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    for station in stations:
                        conn.execute('''
                            INSERT OR REPLACE INTO stations 
                            (id, name, ascii_name, area_id, logo_url, banner_url, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ''', (
                            station.id, station.name, station.ascii_name,
                            station.area_id, station.logo_url, station.banner_url
                        ))
                    conn.commit()
        except Exception as e:
            self.logger.error(f"放送局保存エラー: {e}")
            raise ProgramInfoError(f"放送局の保存に失敗しました: {e}")
    
    def _save_programs(self, programs: List[Program]):
        """番組情報をデータベースに保存"""
        try:
            with self.db_lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    for program in programs:
                        conn.execute('''
                            INSERT OR REPLACE INTO programs 
                            (id, station_id, title, start_time, end_time, duration, 
                             description, performers, genre, sub_genre, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ''', (
                            program.id, program.station_id, program.title,
                            program.start_time.isoformat(), program.end_time.isoformat(),
                            program.duration, program.description, ','.join(program.performers),
                            program.genre, program.sub_genre
                        ))
                    conn.commit()
        except Exception as e:
            self.logger.error(f"番組保存エラー: {e}")
            raise ProgramInfoError(f"番組の保存に失敗しました: {e}")
    
    def _get_cached_stations(self) -> List[Station]:
        """キャッシュから放送局リストを取得"""
        try:
            with self.db_lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.execute('''
                        SELECT id, name, ascii_name, area_id, logo_url, banner_url
                        FROM stations 
                        WHERE area_id = ?
                        ORDER BY name
                    ''', (self.area_id,))
                    
                    stations = []
                    for row in cursor.fetchall():
                        station = Station(*row)
                        stations.append(station)
                    
                    return stations
        except Exception as e:
            self.logger.error(f"キャッシュ放送局取得エラー: {e}")
            return []
    
    def _get_cached_programs(self, date: datetime, station_id: Optional[str] = None) -> List[Program]:
        """キャッシュから番組情報を取得"""
        try:
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            with self.db_lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    if station_id:
                        cursor = conn.execute('''
                            SELECT id, station_id, title, start_time, end_time, duration,
                                   description, performers, genre, sub_genre
                            FROM programs 
                            WHERE station_id = ? AND start_time >= ? AND start_time < ?
                            ORDER BY start_time
                        ''', (station_id, start_of_day.isoformat(), end_of_day.isoformat()))
                    else:
                        cursor = conn.execute('''
                            SELECT id, station_id, title, start_time, end_time, duration,
                                   description, performers, genre, sub_genre
                            FROM programs 
                            WHERE start_time >= ? AND start_time < ?
                            ORDER BY station_id, start_time
                        ''', (start_of_day.isoformat(), end_of_day.isoformat()))
                    
                    programs = []
                    for row in cursor.fetchall():
                        program = Program(
                            id=row[0],
                            station_id=row[1],
                            title=row[2],
                            start_time=datetime.fromisoformat(row[3]),
                            end_time=datetime.fromisoformat(row[4]),
                            duration=row[5],
                            description=row[6] or "",
                            performers=row[7].split(',') if row[7] else [],
                            genre=row[8] or "",
                            sub_genre=row[9] or ""
                        )
                        programs.append(program)
                    
                    return programs
        except Exception as e:
            self.logger.error(f"キャッシュ番組取得エラー: {e}")
            return []
    
    def get_current_program(self, station_id: str) -> Optional[Program]:
        """現在放送中の番組を取得"""
        try:
            now = datetime.now(self.jst)
            
            with self.db_lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.execute('''
                        SELECT id, station_id, title, start_time, end_time, duration,
                               description, performers, genre, sub_genre
                        FROM programs 
                        WHERE station_id = ? AND start_time <= ? AND end_time > ?
                        ORDER BY start_time DESC
                        LIMIT 1
                    ''', (station_id, now.isoformat(), now.isoformat()))
                    
                    row = cursor.fetchone()
                    if row:
                        return Program(
                            id=row[0],
                            station_id=row[1],
                            title=row[2],
                            start_time=datetime.fromisoformat(row[3]),
                            end_time=datetime.fromisoformat(row[4]),
                            duration=row[5],
                            description=row[6] or "",
                            performers=row[7].split(',') if row[7] else [],
                            genre=row[8] or "",
                            sub_genre=row[9] or ""
                        )
                    return None
        except Exception as e:
            self.logger.error(f"現在番組取得エラー: {e}")
            return None
    
    def search_programs(self, query: str, genre: Optional[str] = None,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       station_id: Optional[str] = None,
                       limit: int = 100) -> List[Program]:
        """番組を検索"""
        try:
            with self.db_lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    where_clauses = []
                    params = []
                    
                    # タイトル・説明・出演者で検索
                    if query:
                        where_clauses.append(
                            "(title LIKE ? OR description LIKE ? OR performers LIKE ?)"
                        )
                        search_term = f"%{query}%"
                        params.extend([search_term, search_term, search_term])
                    
                    # 放送局で絞り込み
                    if station_id:
                        where_clauses.append("station_id = ?")
                        params.append(station_id)
                    
                    # ジャンルで絞り込み
                    if genre:
                        where_clauses.append("genre = ?")
                        params.append(genre)
                    
                    # 日付範囲で絞り込み
                    if start_date:
                        where_clauses.append("start_time >= ?")
                        params.append(start_date.isoformat())
                    
                    if end_date:
                        where_clauses.append("end_time <= ?")
                        params.append(end_date.isoformat())
                    
                    where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                    
                    cursor = conn.execute(f'''
                        SELECT id, station_id, title, start_time, end_time, duration,
                               description, performers, genre, sub_genre
                        FROM programs 
                        WHERE {where_clause}
                        ORDER BY start_time DESC
                        LIMIT ?
                    ''', params + [limit])
                    
                    programs = []
                    for row in cursor.fetchall():
                        program = Program(
                            id=row[0],
                            station_id=row[1],
                            title=row[2],
                            start_time=datetime.fromisoformat(row[3]),
                            end_time=datetime.fromisoformat(row[4]),
                            duration=row[5],
                            description=row[6] or "",
                            performers=row[7].split(',') if row[7] else [],
                            genre=row[8] or "",
                            sub_genre=row[9] or ""
                        )
                        programs.append(program)
                    
                    return programs
        except Exception as e:
            self.logger.error(f"番組検索エラー: {e}")
            return []
    
    def cleanup_old_programs(self, retention_days: int = 30):
        """古い番組情報を削除"""
        try:
            cutoff_date = datetime.now(self.jst) - timedelta(days=retention_days)
            
            with self.db_lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.execute('''
                        DELETE FROM programs WHERE end_time < ?
                    ''', (cutoff_date.isoformat(),))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    self.logger.info(f"古い番組情報 {deleted_count} 件を削除しました")
        except Exception as e:
            self.logger.error(f"番組クリーンアップエラー: {e}")
    
    def get_station_by_id(self, station_id: str) -> Optional[Station]:
        """IDで放送局を取得"""
        try:
            with self.db_lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.execute('''
                        SELECT id, name, ascii_name, area_id, logo_url, banner_url
                        FROM stations WHERE id = ?
                    ''', (station_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        return Station(*row)
                    return None
        except Exception as e:
            self.logger.error(f"放送局取得エラー: {e}")
            return None


class ProgramInfoError(Exception):
    """番組情報エラーの例外クラス"""
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
        # 番組情報管理のテスト
        manager = ProgramInfoManager(area_id="JP13")
        
        print("放送局リストを取得中...")
        stations = manager.fetch_station_list()
        print(f"放送局数: {len(stations)}")
        for station in stations[:5]:  # 最初の5局を表示
            print(f"  {station.id}: {station.name}")
        
        print("\n今日の番組表を取得中...")
        today = datetime.now()
        programs = manager.fetch_program_guide(today, stations[0].id if stations else None)
        print(f"番組数: {len(programs)}")
        for program in programs[:5]:  # 最初の5番組を表示
            print(f"  {program.start_time.strftime('%H:%M')}-{program.end_time.strftime('%H:%M')}: {program.title}")
        
        if stations:
            print(f"\n{stations[0].name}の現在の番組:")
            current = manager.get_current_program(stations[0].id)
            if current:
                print(f"  {current.title} ({current.start_time.strftime('%H:%M')}-{current.end_time.strftime('%H:%M')})")
            else:
                print("  現在の番組情報なし")
        
    except ProgramInfoError as e:
        print(f"番組情報エラー: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"予期しないエラー: {e}")
        sys.exit(1)