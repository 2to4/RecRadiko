"""
番組履歴管理モジュール

このモジュールはRadikoの過去番組表を管理する機能を提供します。
- 番組表XMLの取得・パース
- 番組検索機能（部分一致、日付範囲）
- キャッシュシステム（24時間有効）
- 番組ID生成ロジック
"""

import re
import xml.etree.ElementTree as ET
import sqlite3
import json
import requests
from datetime import datetime, timedelta

# Python 3.12+ SQLite datetime adapter 警告回避
def adapt_datetime(dt):
    return dt.isoformat()

def convert_datetime(val):
    return datetime.fromisoformat(val.decode())

sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("datetime", convert_datetime)
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Any
from dataclasses import dataclass

from .auth import RadikoAuthenticator
from .program_info import ProgramInfo
from .utils.base import LoggerMixin
from .utils.network_utils import create_radiko_session
from .utils.path_utils import ensure_directory_path_exists


class ProgramHistoryError(Exception):
    """番組履歴管理関連エラーの基底クラス"""
    pass


class ProgramFetchError(ProgramHistoryError):
    """番組表取得エラー"""
    pass


class ProgramParseError(ProgramHistoryError):
    """番組表パースエラー"""
    pass


class ProgramCache(LoggerMixin):
    """番組表キャッシュクラス"""
    
    def __init__(self, cache_dir: str = "~/.recradiko/cache", expire_hours: int = 24):
        super().__init__()  # LoggerMixin初期化
        self.cache_dir = Path(cache_dir).expanduser()
        self.expire_hours = expire_hours
        self.db_path = self.cache_dir / "program_cache.db"
        self._init_database()
    
    def _init_database(self):
        """キャッシュデータベース初期化"""
        try:
            ensure_directory_path_exists(self.cache_dir)
            
            with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS program_cache (
                        id INTEGER PRIMARY KEY,
                        cache_key TEXT UNIQUE NOT NULL,
                        program_data TEXT NOT NULL,
                        cached_at datetime DEFAULT CURRENT_TIMESTAMP,
                        expires_at datetime NOT NULL
                    )
                """)
                
                # 期限切れキャッシュの削除
                conn.execute("DELETE FROM program_cache WHERE expires_at < datetime('now')")
                conn.commit()
                
                self.logger.debug(f"キャッシュデータベース初期化完了: {self.db_path}")
                
        except Exception as e:
            self.logger.error(f"キャッシュデータベース初期化エラー: {e}")
            raise ProgramHistoryError(f"キャッシュシステム初期化失敗: {e}")
    
    def get_cached_programs(self, date: str, station_id: str = None) -> Optional[List[ProgramInfo]]:
        """キャッシュされた番組表取得
        
        Args:
            date: 対象日付 (YYYY-MM-DD形式)
            station_id: 放送局ID (未指定時は全局)
            
        Returns:
            Optional[List[ProgramInfo]]: キャッシュされた番組情報 (期限切れの場合はNone)
        """
        try:
            cache_key = self._generate_cache_key(date, station_id)
            
            with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES) as conn:
                cursor = conn.execute(
                    "SELECT program_data FROM program_cache WHERE cache_key = ? AND expires_at > datetime('now')",
                    (cache_key,)
                )
                result = cursor.fetchone()
                
                if result:
                    program_data = json.loads(result[0])
                    programs = [ProgramInfo.from_dict(p) for p in program_data]
                    self.logger.debug(f"キャッシュから番組表取得: {cache_key} ({len(programs)}番組)")
                    return programs
                
            return None
            
        except Exception as e:
            self.logger.warning(f"キャッシュ取得エラー: {e}")
            return None
    
    def store_programs(self, date: str, station_id: str, programs: List[ProgramInfo]):
        """番組表のキャッシュ保存
        
        Args:
            date: 対象日付
            station_id: 放送局ID (Noneの場合は全局)
            programs: 番組情報一覧
        """
        try:
            cache_key = self._generate_cache_key(date, station_id)
            expires_at = datetime.now() + timedelta(hours=self.expire_hours)
            program_data = json.dumps([p.to_dict() for p in programs], ensure_ascii=False)
            
            with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO program_cache (cache_key, program_data, expires_at) VALUES (?, ?, ?)",
                    (cache_key, program_data, expires_at)
                )
                conn.commit()
                
                self.logger.debug(f"キャッシュに番組表保存: {cache_key} ({len(programs)}番組)")
                
        except Exception as e:
            self.logger.warning(f"キャッシュ保存エラー: {e}")
    
    def _generate_cache_key(self, date: str, station_id: str = None) -> str:
        """キャッシュキー生成
        
        Args:
            date: 日付
            station_id: 放送局ID
            
        Returns:
            str: キャッシュキー
        """
        if station_id:
            return f"{date}_{station_id}"
        else:
            return f"{date}_all"
    
    def clear_expired_cache(self):
        """期限切れキャッシュの削除"""
        try:
            with sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES) as conn:
                cursor = conn.execute("DELETE FROM program_cache WHERE expires_at < datetime('now')")
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    self.logger.info(f"期限切れキャッシュ削除: {deleted_count}件")
                    
        except Exception as e:
            self.logger.warning(f"キャッシュクリーンアップエラー: {e}")


class ProgramHistoryManager(LoggerMixin):
    """過去番組表管理クラス"""
    
    # Radiko 番組表API
    PROGRAM_API_BASE = "https://radiko.jp/v3/program/date"
    
    def __init__(self, authenticator: RadikoAuthenticator = None):
        super().__init__()  # LoggerMixin初期化
        self.authenticator = authenticator or RadikoAuthenticator()
        self.cache = ProgramCache()
        self.session = create_radiko_session()
    
    def get_programs_by_date(self, date: str, station_id: str = None) -> List[ProgramInfo]:
        """指定日の番組表取得
        
        Args:
            date: 対象日付 (YYYY-MM-DD形式)
            station_id: 放送局ID (未指定時は全局)
            
        Returns:
            List[ProgramInfo]: 番組情報一覧
            
        Cache Strategy:
            1. キャッシュ確認
            2. 未キャッシュ時はAPI呼び出し
            3. 結果をキャッシュに保存
        """
        try:
            self.logger.info(f"番組表取得開始: {date} {station_id or '全局'}")
            
            # キャッシュから確認
            cached_programs = self.cache.get_cached_programs(date, station_id)
            if cached_programs is not None:
                self.logger.info(f"キャッシュから番組表取得: {len(cached_programs)}番組")
                return cached_programs
            
            # 認証情報取得
            auth_info = self.authenticator.get_valid_auth_info()
            
            # 番組表XML取得
            xml_data = self._fetch_program_xml(date, auth_info.area_id)
            
            # XML解析
            programs = self._parse_program_xml(xml_data, date)
            
            # 放送局フィルタリング
            if station_id:
                programs = [p for p in programs if p.station_id == station_id]
            
            # キャッシュに保存
            self.cache.store_programs(date, station_id, programs)
            
            self.logger.info(f"番組表取得完了: {len(programs)}番組")
            return programs
            
        except Exception as e:
            error_msg = f"番組表取得エラー: {e}"
            self.logger.error(error_msg)
            raise ProgramFetchError(error_msg)
    
    def search_programs(self, keyword: str, 
                       date_range: Optional[Tuple[str, str]] = None,
                       station_ids: Optional[List[str]] = None) -> List[ProgramInfo]:
        """番組検索
        
        Args:
            keyword: 検索キーワード
            date_range: 検索日付範囲 (開始日, 終了日)
            station_ids: 対象放送局ID一覧
            
        Returns:
            List[ProgramInfo]: 検索結果
            
        Search Logic:
            - 番組タイトルでの部分一致
            - 出演者名での部分一致
            - 番組説明での部分一致
            - 大文字小文字の区別なし
        """
        try:
            self.logger.info(f"番組検索開始: キーワード='{keyword}'")
            
            # 検索対象日付範囲設定
            if date_range is None:
                # デフォルトは過去7日間
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                date_range = (
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
            
            start_date_str, end_date_str = date_range
            
            # 検索結果収集
            all_results = []
            current_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                
                try:
                    # 指定日の番組表取得
                    day_programs = self.get_programs_by_date(date_str)
                    
                    # 放送局フィルタリング
                    if station_ids:
                        day_programs = [p for p in day_programs if p.station_id in station_ids]
                    
                    # キーワード検索
                    keyword_lower = keyword.lower()
                    for program in day_programs:
                        if self._match_program(program, keyword_lower):
                            all_results.append(program)
                    
                except Exception as e:
                    self.logger.warning(f"日付 {date_str} の番組検索でエラー: {e}")
                
                current_date += timedelta(days=1)
            
            self.logger.info(f"番組検索完了: {len(all_results)}件ヒット")
            return all_results
            
        except Exception as e:
            error_msg = f"番組検索エラー: {e}"
            self.logger.error(error_msg)
            raise ProgramHistoryError(error_msg)
    
    def get_program_by_id(self, program_id: str) -> Optional[ProgramInfo]:
        """番組ID指定での番組情報取得
        
        Args:
            program_id: 番組ID (例: TBS_20250710_060000)
            
        Returns:
            Optional[ProgramInfo]: 番組情報 (見つからない場合はNone)
        """
        try:
            # 番組IDから日付と放送局を抽出
            parts = program_id.split('_')
            if len(parts) < 3:
                raise ValueError(f"無効な番組ID形式: {program_id}")
            
            station_id = parts[0]
            date_part = parts[1]
            
            # 日付形式を変換 (YYYYMMDD -> YYYY-MM-DD)
            if len(date_part) == 8:
                date_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
            else:
                raise ValueError(f"無効な日付形式: {date_part}")
            
            # 指定日・放送局の番組表取得
            programs = self.get_programs_by_date(date_str, station_id)
            
            # 番組ID一致検索
            for program in programs:
                if program.program_id == program_id:
                    self.logger.info(f"番組ID検索成功: {program_id}")
                    return program
            
            self.logger.warning(f"番組ID該当なし: {program_id}")
            return None
            
        except Exception as e:
            self.logger.error(f"番組ID検索エラー: {e}")
            return None
    
    def get_available_dates(self, station_id: str = None) -> List[str]:
        """利用可能な日付一覧取得
        
        Args:
            station_id: 放送局ID
            
        Returns:
            List[str]: 利用可能日付一覧 (YYYY-MM-DD形式)
            
        Note:
            現在日時から7日前までの日付を返す
        """
        try:
            available_dates = []
            current_date = datetime.now()
            
            # 過去7日間の日付を生成
            for i in range(8):  # 今日を含む8日間
                date = current_date - timedelta(days=i)
                available_dates.append(date.strftime('%Y-%m-%d'))
            
            self.logger.debug(f"利用可能日付: {len(available_dates)}日間")
            return available_dates
            
        except Exception as e:
            self.logger.error(f"利用可能日付取得エラー: {e}")
            return []
    
    def _fetch_program_xml(self, date: str, area_id: str) -> str:
        """Radiko番組表XMLの取得
        
        Args:
            date: 対象日付 (YYYY-MM-DD形式)
            area_id: エリアID
            
        Returns:
            str: 番組表XML文字列
            
        API Endpoint:
            GET https://radiko.jp/v3/program/date/{YYYYMMDD}/{area_id}.xml
        """
        try:
            # 日付形式変換 (YYYY-MM-DD -> YYYYMMDD)
            date_formatted = date.replace('-', '')
            
            # API URL構築
            api_url = f"{self.PROGRAM_API_BASE}/{date_formatted}/{area_id}.xml"
            
            self.logger.debug(f"番組表API呼び出し: {api_url}")
            
            # HTTP リクエスト実行
            response = self.session.get(api_url)
            response.raise_for_status()
            
            # エンコーディング設定
            response.encoding = 'utf-8'
            xml_data = response.text
            
            self.logger.debug(f"番組表XML取得成功: {len(xml_data)}文字")
            return xml_data
            
        except requests.exceptions.RequestException as e:
            raise ProgramFetchError(f"番組表API呼び出し失敗: {e}")
        except Exception as e:
            raise ProgramFetchError(f"番組表取得エラー: {e}")
    
    def _parse_program_xml(self, xml_data: str, target_date: str) -> List[ProgramInfo]:
        """番組表XMLのパース処理
        
        Args:
            xml_data: 番組表XML文字列
            target_date: 対象日付
            
        Returns:
            List[ProgramInfo]: パースされた番組情報一覧
            
        XML Structure:
            <radiko>
              <stations>
                <station id="TBS">
                  <name>TBSラジオ</name>
                  <progs>
                    <prog id="..." ft="..." to="..." dur="...">
                      <title>番組名</title>
                      <desc>番組説明</desc>
                      <pfm>出演者</pfm>
                      <genre>...</genre>
                    </prog>
                  </progs>
                </station>
              </stations>
            </radiko>
        """
        try:
            programs = []
            
            # XML解析
            root = ET.fromstring(xml_data)
            
            # 各放送局の処理
            stations = root.find('stations')
            if stations is None:
                raise ProgramParseError("stations要素が見つかりません")
            
            for station in stations.findall('station'):
                station_id = station.get('id')
                station_name_elem = station.find('name')
                station_name = station_name_elem.text if station_name_elem is not None else station_id
                
                # 番組リスト処理
                progs = station.find('progs')
                if progs is None:
                    continue
                
                for prog in progs.findall('prog'):
                    try:
                        program_info = self._parse_single_program(prog, station_id, station_name, target_date)
                        if program_info:
                            programs.append(program_info)
                    except Exception as e:
                        self.logger.warning(f"番組パースエラー (スキップ): {e}")
                        continue
            
            self.logger.info(f"番組表解析完了: {len(programs)}番組")
            return programs
            
        except ET.ParseError as e:
            raise ProgramParseError(f"XML解析エラー: {e}")
        except Exception as e:
            raise ProgramParseError(f"番組表解析エラー: {e}")
    
    def _parse_single_program(self, prog_elem: ET.Element, station_id: str, 
                            station_name: str, target_date: str) -> Optional[ProgramInfo]:
        """単一番組の解析
        
        Args:
            prog_elem: 番組XML要素
            station_id: 放送局ID
            station_name: 放送局名
            target_date: 対象日付
            
        Returns:
            Optional[ProgramInfo]: 番組情報 (解析失敗時はNone)
        """
        try:
            # 必須属性取得
            prog_id = prog_elem.get('id', '')
            ft_str = prog_elem.get('ft', '')  # 開始時刻 (YYYYMMDDHHMMSS)
            to_str = prog_elem.get('to', '')  # 終了時刻 (YYYYMMDDHHMMSS)
            
            if not all([ft_str, to_str]):
                return None
            
            # 時刻解析
            start_time = self._parse_time_string(ft_str)
            end_time = self._parse_time_string(to_str)
            
            if not start_time or not end_time:
                return None
            
            # 終了時刻が開始時刻よりも前の場合、翌日として処理
            if end_time <= start_time:
                end_time = end_time + timedelta(days=1)
                self.logger.debug(f"終了時刻を翌日に修正: {end_time}")
            
            # 番組詳細取得
            title_elem = prog_elem.find('title')
            title = title_elem.text if title_elem is not None and title_elem.text else '番組名不明'
            
            desc_elem = prog_elem.find('desc')
            description = desc_elem.text if desc_elem is not None and desc_elem.text else ''
            
            pfm_elem = prog_elem.find('pfm')
            performers_text = pfm_elem.text if pfm_elem is not None and pfm_elem.text else ''
            performers = [p.strip() for p in performers_text.split(',') if p.strip()] if performers_text else []
            
            genre_elem = prog_elem.find('genre')
            genre = genre_elem.text if genre_elem is not None and genre_elem.text else ''
            
            # 番組ID生成
            program_id = self._generate_program_id(station_id, start_time)
            
            # タイムフリー利用可能性判定
            is_timefree_available = self._is_timefree_available(start_time)
            timefree_end_time = start_time + timedelta(days=7) if is_timefree_available else None
            
            # ProgramInfoオブジェクト生成
            return ProgramInfo(
                program_id=program_id,
                station_id=station_id,
                station_name=station_name,
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=description,
                performers=performers,
                genre=genre,
                is_timefree_available=is_timefree_available,
                timefree_end_time=timefree_end_time
            )
            
        except Exception as e:
            self.logger.warning(f"単一番組解析エラー: {e}")
            return None
    
    def _parse_time_string(self, time_str: str) -> Optional[datetime]:
        """時刻文字列の解析
        
        Args:
            time_str: 時刻文字列 (YYYYMMDDHHMMSS形式)
            
        Returns:
            Optional[datetime]: 解析された日時 (失敗時はNone)
        """
        try:
            if len(time_str) != 14:
                return None
            
            year = int(time_str[:4])
            month = int(time_str[4:6])
            day = int(time_str[6:8])
            hour = int(time_str[8:10])
            minute = int(time_str[10:12])
            second = int(time_str[12:14])
            
            return datetime(year, month, day, hour, minute, second)
            
        except (ValueError, IndexError):
            return None
    
    def _is_timefree_available(self, start_time: datetime) -> bool:
        """タイムフリー利用可能性判定
        
        Args:
            start_time: 番組開始時刻
            
        Returns:
            bool: タイムフリー利用可能な場合True
            
        Logic:
            現在時刻から7日以内かつ放送終了済みの番組
        """
        try:
            now = datetime.now()
            
            # 7日以内かつ過去の番組
            return (
                start_time < now and  # 放送開始済み
                start_time > now - timedelta(days=7)  # 7日以内
            )
            
        except Exception:
            return False
    
    def _generate_program_id(self, station_id: str, start_time: datetime) -> str:
        """番組ID生成
        
        Args:
            station_id: 放送局ID
            start_time: 番組開始時刻
            
        Returns:
            str: 番組ID
            
        Format:
            {STATION_ID}_{YYYYMMDD}_{HHMMSS}
            例: TBS_20250710_060000
        """
        return f"{station_id}_{start_time.strftime('%Y%m%d_%H%M%S')}"
    
    def _match_program(self, program: ProgramInfo, keyword_lower: str) -> bool:
        """番組のキーワードマッチング判定
        
        Args:
            program: 番組情報
            keyword_lower: 検索キーワード（小文字）
            
        Returns:
            bool: マッチした場合True
        """
        try:
            # タイトル検索
            if keyword_lower in program.title.lower():
                return True
            
            # 出演者検索
            for performer in program.performers:
                if keyword_lower in performer.lower():
                    return True
            
            # 説明文検索
            if keyword_lower in program.description.lower():
                return True
            
            return False
            
        except Exception:
            return False


# テスト用の使用例
if __name__ == "__main__":
    import sys
    from .auth import RadikoAuthenticator
    
    def test_program_history():
        """番組履歴管理のテスト"""
        try:
            # 認証器を初期化
            authenticator = RadikoAuthenticator()
            history_manager = ProgramHistoryManager(authenticator)
            
            # 今日の番組表取得テスト
            today = datetime.now().strftime('%Y-%m-%d')
            print(f"番組表取得テスト: {today}")
            
            programs = history_manager.get_programs_by_date(today, "TBS")
            print(f"取得番組数: {len(programs)}")
            
            # 最初の5番組を表示
            for i, program in enumerate(programs[:5]):
                print(f"{i+1}. {program.title} ({program.start_time.strftime('%H:%M')}-{program.end_time.strftime('%H:%M')})")
            
            # 番組検索テスト
            print("\n番組検索テスト: '森本毅郎'")
            search_results = history_manager.search_programs("森本毅郎", station_ids=["TBS"])
            print(f"検索結果: {len(search_results)}件")
            
            for program in search_results[:3]:
                print(f"- {program.title} ({program.start_time.strftime('%Y-%m-%d %H:%M')})")
                
        except Exception as e:
            print(f"テストエラー: {e}")
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_program_history()
    else:
        print("番組履歴管理モジュール - RecRadiko")
        print("使用方法: python -m src.program_history test")