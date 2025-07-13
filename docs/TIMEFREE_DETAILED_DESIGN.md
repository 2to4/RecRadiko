# RecRadiko タイムフリー専用アプリケーション 詳細設計書

## 1. モジュール詳細設計

### 1.1 TimeFreeRecorder クラス詳細設計

#### 1.1.1 クラス構造
```python
# src/timefree_recorder.py

import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import aiohttp
import aiofiles
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, COMM

class TimeFreeRecorder:
    """タイムフリー専用録音クラス"""
    
    def __init__(self, authenticator: 'RadikoAuthenticator'):
        self.authenticator = authenticator
        self.logger = get_logger(__name__)
        self.max_workers = 8
        self.segment_timeout = 30
        self.retry_attempts = 3
        self.chunk_size = 8192
        
    async def record_program(self, program_info: 'ProgramInfo', 
                           output_path: str) -> 'RecordingResult':
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
        
    async def record_by_datetime(self, station_id: str, start_time: datetime, 
                               end_time: datetime, output_path: str) -> 'RecordingResult':
        """日時指定でタイムフリー録音実行
        
        Args:
            station_id: 放送局ID
            start_time: 録音開始時刻
            end_time: 録音終了時刻
            output_path: 出力ファイルパス
            
        Returns:
            RecordingResult: 録音結果
        """
        
    def _generate_timefree_url(self, station_id: str, start_time: datetime, 
                             end_time: datetime) -> str:
        """タイムフリーM3U8 URL生成
        
        Args:
            station_id: 放送局ID
            start_time: 開始時刻
            end_time: 終了時刻
            
        Returns:
            str: タイムフリーM3U8 URL
            
        URL形式:
        https://radiko.jp/v2/api/ts/playlist.m3u8?station_id={STATION}&l=15&lsid={LSID}&ft={START}&to={END}
        """
        
    async def _fetch_playlist(self, playlist_url: str) -> List[str]:
        """M3U8プレイリストからセグメントURL一覧取得
        
        Args:
            playlist_url: M3U8プレイリストURL
            
        Returns:
            List[str]: セグメントURL一覧
            
        Raises:
            PlaylistFetchError: プレイリスト取得エラー
        """
        
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
        
    async def _download_single_segment(self, session: aiohttp.ClientSession, 
                                     url: str, index: int) -> Tuple[int, bytes]:
        """単一セグメントのダウンロード
        
        Args:
            session: HTTP セッション
            url: セグメントURL
            index: セグメントインデックス
            
        Returns:
            Tuple[int, bytes]: (インデックス, セグメントデータ)
            
        Raises:
            SegmentDownloadError: ダウンロード失敗
        """
        
    def _combine_ts_segments(self, segments: List[bytes], temp_file_path: str):
        """TSセグメントの結合
        
        Args:
            segments: セグメントデータ一覧
            temp_file_path: 一時ファイルパス
            
        Note:
            セグメントを順序通りに結合し、一時TSファイルを作成
        """
        
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
```

#### 1.1.2 エラーハンドリング
```python
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
```

### 1.2 ProgramHistoryManager クラス詳細設計

#### 1.2.1 クラス構造
```python
# src/program_history.py

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import requests
from dataclasses import dataclass
import sqlite3
import json

class ProgramHistoryManager:
    """過去番組表管理クラス"""
    
    def __init__(self, authenticator: 'RadikoAuthenticator'):
        self.authenticator = authenticator
        self.logger = get_logger(__name__)
        self.cache = ProgramCache()
        self.session = requests.Session()
        self.session.timeout = 30
        
    def get_programs_by_date(self, date: str, station_id: str = None) -> List['ProgramInfo']:
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
        
    def search_programs(self, keyword: str, 
                       date_range: Optional[Tuple[str, str]] = None,
                       station_ids: Optional[List[str]] = None) -> List['ProgramInfo']:
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
        
    def get_program_by_id(self, program_id: str) -> Optional['ProgramInfo']:
        """番組ID指定での番組情報取得
        
        Args:
            program_id: 番組ID (例: TBS_20250710_060000)
            
        Returns:
            Optional[ProgramInfo]: 番組情報 (見つからない場合はNone)
        """
        
    def get_available_dates(self, station_id: str = None) -> List[str]:
        """利用可能な日付一覧取得
        
        Args:
            station_id: 放送局ID
            
        Returns:
            List[str]: 利用可能日付一覧 (YYYY-MM-DD形式)
            
        Note:
            現在日時から7日前までの日付を返す
        """
        
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
        
    def _parse_program_xml(self, xml_data: str, target_date: str) -> List['ProgramInfo']:
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
        
    def _is_timefree_available(self, start_time: datetime) -> bool:
        """タイムフリー利用可能性判定
        
        Args:
            start_time: 番組開始時刻
            
        Returns:
            bool: タイムフリー利用可能な場合True
            
        Logic:
            現在時刻から7日以内かつ放送終了済みの番組
        """
        
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
```

#### 1.2.2 キャッシュシステム設計
```python
class ProgramCache:
    """番組表キャッシュクラス"""
    
    def __init__(self, cache_dir: str = "~/.recradiko/cache", expire_hours: int = 24):
        self.cache_dir = Path(cache_dir).expanduser()
        self.expire_hours = expire_hours
        self.db_path = self.cache_dir / "program_cache.db"
        self._init_database()
        
    def _init_database(self):
        """キャッシュデータベース初期化"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS program_cache (
                    id INTEGER PRIMARY KEY,
                    cache_key TEXT UNIQUE NOT NULL,
                    program_data TEXT NOT NULL,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            
            # 期限切れキャッシュの削除
            conn.execute("DELETE FROM program_cache WHERE expires_at < datetime('now')")
            conn.commit()
            
    def get_cached_programs(self, date: str, station_id: str = None) -> Optional[List['ProgramInfo']]:
        """キャッシュされた番組表取得"""
        cache_key = self._generate_cache_key(date, station_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT program_data FROM program_cache WHERE cache_key = ? AND expires_at > datetime('now')",
                (cache_key,)
            )
            result = cursor.fetchone()
            
            if result:
                program_data = json.loads(result[0])
                return [ProgramInfo.from_dict(p) for p in program_data]
            
        return None
        
    def store_programs(self, date: str, station_id: str, programs: List['ProgramInfo']):
        """番組表のキャッシュ保存"""
        cache_key = self._generate_cache_key(date, station_id)
        expires_at = datetime.now() + timedelta(hours=self.expire_hours)
        program_data = json.dumps([p.to_dict() for p in programs], ensure_ascii=False)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO program_cache (cache_key, program_data, expires_at) VALUES (?, ?, ?)",
                (cache_key, program_data, expires_at)
            )
            conn.commit()
            
    def _generate_cache_key(self, date: str, station_id: str = None) -> str:
        """キャッシュキー生成"""
        if station_id:
            return f"{date}_{station_id}"
        else:
            return f"{date}_all"
            
    def clear_expired_cache(self):
        """期限切れキャッシュの削除"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM program_cache WHERE expires_at < datetime('now')")
            conn.commit()
```

### 1.3 ProgramInfo データクラス詳細設計

#### 1.3.1 データクラス構造
```python
# src/program_info.py (拡張)

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import re

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
    performers: List[str] = field(default_factory=list)
    genre: str = ""
    
    # タイムフリー関連
    is_timefree_available: bool = False
    timefree_end_time: Optional[datetime] = None
    
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
        """辞書からのインスタンス生成（キャッシュ用）"""
        return cls(
            program_id=data['program_id'],
            station_id=data['station_id'],
            station_name=data['station_name'],
            title=data['title'],
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']),
            description=data.get('description', ''),
            performers=data.get('performers', []),
            genre=data.get('genre', ''),
            is_timefree_available=data.get('is_timefree_available', False),
            timefree_end_time=datetime.fromisoformat(data['timefree_end_time']) if data.get('timefree_end_time') else None
        )
    
    def matches_keyword(self, keyword: str) -> bool:
        """キーワード検索マッチング判定
        
        Args:
            keyword: 検索キーワード
            
        Returns:
            bool: マッチする場合True
            
        Search Targets:
            - 番組タイトル
            - 番組説明
            - 出演者名
        """
        keyword_lower = keyword.lower()
        
        # タイトル検索
        if keyword_lower in self.title.lower():
            return True
            
        # 説明文検索
        if keyword_lower in self.description.lower():
            return True
            
        # 出演者検索
        for performer in self.performers:
            if keyword_lower in performer.lower():
                return True
                
        return False
    
    def is_in_date_range(self, start_date: str, end_date: str) -> bool:
        """日付範囲内判定
        
        Args:
            start_date: 開始日 (YYYY-MM-DD)
            end_date: 終了日 (YYYY-MM-DD)
            
        Returns:
            bool: 範囲内の場合True
        """
        program_date = self.start_time.date()
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        return start <= program_date <= end
```

### 1.4 CLI インターフェース詳細設計

#### 1.4.1 タイムフリー専用CLIクラス
```python
# src/cli.py (大幅改修)

import shlex
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import readline
from tqdm import tqdm

class TimeFreeRecRadikoCLI:
    """タイムフリー専用CLIクラス"""
    
    COMMANDS = [
        'list-programs', 'record', 'record-id', 
        'search-programs', 'help', 'exit', 'quit'
    ]
    
    def __init__(self):
        self.authenticator = RadikoAuthenticator()
        self.program_manager = ProgramHistoryManager(self.authenticator)
        self.recorder = TimeFreeRecorder(self.authenticator)
        self.file_manager = FileManager()
        self.config = self._load_config()
        self.logger = get_logger(__name__)
        
        # タブ補完設定
        self._setup_tab_completion()
        
    def run(self) -> int:
        """対話型モード実行"""
        print("RecRadiko タイムフリー録音システム")
        print("利用可能なコマンド: " + ", ".join(self.COMMANDS))
        print("例: record 2025-07-10 TBS 森本毅郎・スタンバイ!")
        print("💡 タブキーでコマンド補完、↑↓キーで履歴操作が利用できます")
        print("終了するには 'exit' または Ctrl+C を入力してください")
        print("-" * 60)
        
        try:
            while True:
                try:
                    command_line = input("RecRadiko> ").strip()
                    
                    if not command_line:
                        continue
                        
                    if command_line.lower() in ('exit', 'quit'):
                        print("RecRadikoを終了します")
                        break
                        
                    result = self._execute_command(command_line)
                    if result != 0:
                        print(f"コマンドエラー (終了コード: {result})")
                        
                except KeyboardInterrupt:
                    print("\nCtrl+C が押されました")
                    break
                except EOFError:
                    print("\nEOF が検出されました")
                    break
                    
        except Exception as e:
            self.logger.error(f"予期しないエラー: {e}")
            return 1
            
        return 0
    
    def _execute_command(self, command_line: str) -> int:
        """コマンド実行
        
        Args:
            command_line: 入力されたコマンドライン
            
        Returns:
            int: 終了コード (0: 成功, 1: エラー)
        """
        try:
            parts = shlex.split(command_line)
            if not parts:
                return 0
                
            command = parts[0].lower()
            args = parts[1:]
            
            if command == 'list-programs':
                return self._cmd_list_programs(args)
            elif command == 'record':
                return self._cmd_record(args)
            elif command == 'record-id':
                return self._cmd_record_id(args)
            elif command == 'search-programs':
                return self._cmd_search_programs(args)
            elif command == 'help':
                return self._cmd_help(args)
            else:
                print(f"不明なコマンド: {command}")
                print("'help' コマンドで利用可能なコマンドを確認してください")
                return 1
                
        except Exception as e:
            print(f"コマンド実行エラー: {e}")
            self.logger.error(f"コマンド実行エラー: {e}")
            return 1
    
    def _cmd_list_programs(self, args: List[str]) -> int:
        """番組表取得コマンド
        
        Usage:
            list-programs <日付> [放送局ID]
            list-programs 2025-07-10
            list-programs 2025-07-10 TBS
            
        Args:
            args: コマンド引数
            
        Returns:
            int: 終了コード
        """
        if len(args) < 1:
            print("使用法: list-programs <日付> [放送局ID]")
            print("例: list-programs 2025-07-10 TBS")
            return 1
            
        date = args[0]
        station_id = args[1] if len(args) > 1 else None
        
        try:
            # 日付形式チェック
            datetime.strptime(date, '%Y-%m-%d')
            
            print(f"番組表取得中: {date}" + (f" ({station_id})" if station_id else " (全局)"))
            
            programs = self.program_manager.get_programs_by_date(date, station_id)
            
            if not programs:
                print("番組が見つかりませんでした")
                return 1
                
            self._display_programs(programs)
            return 0
            
        except ValueError:
            print("日付形式が正しくありません (YYYY-MM-DD形式で入力してください)")
            return 1
        except Exception as e:
            print(f"番組表取得エラー: {e}")
            return 1
    
    def _cmd_record(self, args: List[str]) -> int:
        """録音実行コマンド
        
        Usage:
            record <日付> <放送局ID> <番組名>
            record 2025-07-10 TBS 森本毅郎・スタンバイ!
            
        Args:
            args: コマンド引数
            
        Returns:
            int: 終了コード
        """
        if len(args) < 3:
            print("使用法: record <日付> <放送局ID> <番組名>")
            print("例: record 2025-07-10 TBS 森本毅郎・スタンバイ!")
            return 1
            
        date = args[0]
        station_id = args[1]
        program_title = ' '.join(args[2:])
        
        try:
            # 番組検索
            programs = self.program_manager.get_programs_by_date(date, station_id)
            matching_programs = [p for p in programs if program_title.lower() in p.title.lower()]
            
            if not matching_programs:
                print(f"番組が見つかりませんでした: {program_title}")
                print("候補番組:")
                for p in programs[:5]:  # 上位5件表示
                    print(f"  - {p.title} ({p.start_time.strftime('%H:%M')}-{p.end_time.strftime('%H:%M')})")
                return 1
                
            if len(matching_programs) > 1:
                print("複数の番組が見つかりました:")
                for i, p in enumerate(matching_programs):
                    print(f"  {i+1}. {p.title} ({p.start_time.strftime('%H:%M')}-{p.end_time.strftime('%H:%M')})")
                
                try:
                    choice = int(input("番号を選択してください: ")) - 1
                    if 0 <= choice < len(matching_programs):
                        program = matching_programs[choice]
                    else:
                        print("無効な選択です")
                        return 1
                except (ValueError, KeyboardInterrupt):
                    print("選択がキャンセルされました")
                    return 1
            else:
                program = matching_programs[0]
            
            # タイムフリー利用可能性チェック
            if not program.is_timefree_available:
                print(f"この番組はタイムフリーで利用できません: {program.title}")
                return 1
            
            # 録音実行
            output_path = self._generate_output_path(program)
            print(f"録音開始: {program.title} ({program.start_time.strftime('%Y-%m-%d %H:%M')}-{program.end_time.strftime('%H:%M')})")
            print(f"出力先: {output_path}")
            
            # 非同期録音実行
            import asyncio
            result = asyncio.run(self.recorder.record_program(program, output_path))
            
            if result.success:
                print(f"録音完了: {output_path}")
                print(f"ファイルサイズ: {result.file_size / (1024*1024):.1f}MB")
                print(f"録音時間: {result.duration_seconds // 60}分{result.duration_seconds % 60}秒")
            else:
                print(f"録音失敗: {', '.join(result.error_messages)}")
                return 1
            
            return 0
            
        except Exception as e:
            print(f"録音エラー: {e}")
            self.logger.error(f"録音エラー: {e}")
            return 1
    
    def _cmd_record_id(self, args: List[str]) -> int:
        """番組ID指定録音コマンド
        
        Usage:
            record-id <番組ID>
            record-id TBS_20250710_060000
            
        Args:
            args: コマンド引数
            
        Returns:
            int: 終了コード
        """
        if len(args) < 1:
            print("使用法: record-id <番組ID>")
            print("例: record-id TBS_20250710_060000")
            return 1
            
        program_id = args[0]
        
        try:
            program = self.program_manager.get_program_by_id(program_id)
            
            if not program:
                print(f"番組が見つかりませんでした: {program_id}")
                return 1
            
            if not program.is_timefree_available:
                print(f"この番組はタイムフリーで利用できません: {program.title}")
                return 1
            
            # 録音実行
            output_path = self._generate_output_path(program)
            print(f"録音開始: {program.title}")
            
            import asyncio
            result = asyncio.run(self.recorder.record_program(program, output_path))
            
            if result.success:
                print(f"録音完了: {output_path}")
            else:
                print(f"録音失敗: {', '.join(result.error_messages)}")
                return 1
            
            return 0
            
        except Exception as e:
            print(f"録音エラー: {e}")
            return 1
    
    def _cmd_search_programs(self, args: List[str]) -> int:
        """番組検索コマンド
        
        Usage:
            search-programs <キーワード> [開始日] [終了日]
            search-programs 森本毅郎
            search-programs ニュース 2025-07-08 2025-07-10
            
        Args:
            args: コマンド引数
            
        Returns:
            int: 終了コード
        """
        if len(args) < 1:
            print("使用法: search-programs <キーワード> [開始日] [終了日]")
            print("例: search-programs 森本毅郎")
            return 1
            
        keyword = args[0]
        date_range = None
        
        if len(args) >= 3:
            try:
                start_date = args[1]
                end_date = args[2]
                # 日付形式チェック
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
                date_range = (start_date, end_date)
            except ValueError:
                print("日付形式が正しくありません (YYYY-MM-DD形式で入力してください)")
                return 1
        
        try:
            print(f"番組検索中: {keyword}")
            
            programs = self.program_manager.search_programs(keyword, date_range)
            
            if not programs:
                print("番組が見つかりませんでした")
                return 1
                
            self._display_programs(programs)
            return 0
            
        except Exception as e:
            print(f"検索エラー: {e}")
            return 1
    
    def _cmd_help(self, args: List[str]) -> int:
        """ヘルプ表示コマンド"""
        print("\n=== RecRadiko タイムフリー録音システム ヘルプ ===")
        print()
        print("利用可能なコマンド:")
        print()
        print("📺 list-programs <日付> [放送局ID]")
        print("    指定日の番組表を表示")
        print("    例: list-programs 2025-07-10 TBS")
        print()
        print("🎵 record <日付> <放送局ID> <番組名>")
        print("    番組を録音")
        print("    例: record 2025-07-10 TBS 森本毅郎・スタンバイ!")
        print()
        print("🆔 record-id <番組ID>")
        print("    番組IDを指定して録音")
        print("    例: record-id TBS_20250710_060000")
        print()
        print("🔍 search-programs <キーワード> [開始日] [終了日]")
        print("    番組を検索")
        print("    例: search-programs 森本毅郎")
        print("    例: search-programs ニュース 2025-07-08 2025-07-10")
        print()
        print("❓ help")
        print("    このヘルプを表示")
        print()
        print("🚪 exit / quit")
        print("    アプリケーションを終了")
        print()
        print("💡 Tips:")
        print("  - タブキーでコマンド補完が利用できます")
        print("  - ↑↓キーでコマンド履歴を辿れます")
        print("  - 録音ファイルは ./recordings/ に保存されます")
        print()
        
        return 0
    
    def _display_programs(self, programs: List['ProgramInfo']):
        """番組一覧表示"""
        if not programs:
            return
            
        print(f"\n見つかった番組数: {len(programs)}")
        print("-" * 80)
        
        for program in programs:
            timefree_status = "✅" if program.is_timefree_available else "❌"
            print(f"{timefree_status} [{program.station_id}] {program.title}")
            print(f"    時間: {program.start_time.strftime('%Y-%m-%d %H:%M')} - {program.end_time.strftime('%H:%M')} ({program.duration_minutes}分)")
            
            if program.performers:
                print(f"    出演: {', '.join(program.performers)}")
            
            if program.description:
                desc = program.description[:100] + "..." if len(program.description) > 100 else program.description
                print(f"    内容: {desc}")
            
            print(f"    ID: {program.program_id}")
            print()
        
        print("✅: タイムフリー利用可能, ❌: 利用不可")
    
    def _generate_output_path(self, program: 'ProgramInfo') -> str:
        """出力パス生成"""
        output_dir = Path(self.config.get('output_directory', './recordings'))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        format = self.config.get('default_format', 'mp3')
        filename = program.to_filename(format)
        
        return str(output_dir / filename)
    
    def _setup_tab_completion(self):
        """タブ補完設定"""
        try:
            import readline
            
            def complete(text, state):
                options = [cmd for cmd in self.COMMANDS if cmd.startswith(text)]
                return options[state] if state < len(options) else None
            
            readline.set_completer(complete)
            readline.parse_and_bind("tab: complete")
            
        except ImportError:
            pass  # readlineが利用できない環境では無視
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイル読み込み"""
        config_path = Path("~/.recradiko/config.json").expanduser()
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"設定ファイル読み込みエラー: {e}")
        
        # デフォルト設定
        return {
            'default_format': 'mp3',
            'default_quality': '256',
            'output_directory': './recordings',
            'download_workers': 8,
            'cache_expire_hours': 24
        }
```

## 2. 認証システム拡張設計

### 2.1 タイムフリー認証拡張
```python
# src/auth.py (拡張)

class RadikoAuthenticator:
    """Radiko認証クラス（タイムフリー対応）"""
    
    def __init__(self):
        # 既存の初期化処理
        self.timefree_session_cache = {}
        self.session_expire_time = None
        
    async def get_timefree_session(self, station_id: str, start_time: datetime, 
                                 end_time: datetime) -> str:
        """タイムフリー専用セッション取得
        
        Args:
            station_id: 放送局ID
            start_time: 開始時刻
            end_time: 終了時刻
            
        Returns:
            str: セッションID
            
        Raises:
            TimeFreeAuthError: 認証失敗
        """
        # セッションキャッシュ確認
        cache_key = f"{station_id}_{start_time}_{end_time}"
        if cache_key in self.timefree_session_cache:
            session_data = self.timefree_session_cache[cache_key]
            if datetime.now() < session_data['expires_at']:
                return session_data['session_id']
        
        # 新規セッション取得
        try:
            # 基本認証実行
            await self.authenticate()
            
            # タイムフリー専用認証
            session_id = await self._get_timefree_session_id(station_id, start_time, end_time)
            
            # セッションキャッシュ
            self.timefree_session_cache[cache_key] = {
                'session_id': session_id,
                'expires_at': datetime.now() + timedelta(hours=1)
            }
            
            return session_id
            
        except Exception as e:
            raise TimeFreeAuthError(f"タイムフリー認証失敗: {e}")
    
    async def _get_timefree_session_id(self, station_id: str, start_time: datetime, 
                                     end_time: datetime) -> str:
        """タイムフリーセッションID取得"""
        # RadikoのタイムフリーAPI認証ロジック
        # 実装詳細は既存認証システムを拡張
        pass
    
    def generate_timefree_url(self, station_id: str, start_time: datetime, 
                            end_time: datetime, session_id: str) -> str:
        """タイムフリーM3U8 URL生成
        
        Args:
            station_id: 放送局ID
            start_time: 開始時刻
            end_time: 終了時刻
            session_id: セッションID
            
        Returns:
            str: タイムフリーM3U8 URL
        """
        ft = start_time.strftime('%Y%m%d%H%M%S')
        to = end_time.strftime('%Y%m%d%H%M%S')
        
        url = (
            f"https://radiko.jp/v2/api/ts/playlist.m3u8"
            f"?station_id={station_id}"
            f"&l=15"
            f"&lsid={session_id}"
            f"&ft={ft}"
            f"&to={to}"
        )
        
        return url
```

## 3. データベース設計

### 3.1 録音履歴テーブル
```sql
-- recordings/history.db

CREATE TABLE recording_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id TEXT NOT NULL,
    station_id TEXT NOT NULL,
    title TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    duration_seconds INTEGER,
    format TEXT DEFAULT 'mp3',
    quality TEXT DEFAULT '256',
    status TEXT DEFAULT 'completed',
    error_message TEXT,
    metadata_json TEXT,
    UNIQUE(program_id)
);

CREATE INDEX idx_recording_station_date ON recording_history(station_id, start_time);
CREATE INDEX idx_recording_recorded_at ON recording_history(recorded_at);
```

### 3.2 番組キャッシュテーブル
```sql
-- cache/program_cache.db

CREATE TABLE program_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    program_data TEXT NOT NULL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_cache_key ON program_cache(cache_key);
CREATE INDEX idx_cache_expires ON program_cache(expires_at);
```

## 4. パフォーマンス最適化設計

### 4.1 並行ダウンロード最適化
```python
class OptimizedSegmentDownloader:
    """最適化されたセグメントダウンローダー"""
    
    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
        self.session_pool = []
        self.retry_delays = [1, 2, 4]  # エクスポネンシャルバックオフ
        
    async def download_segments_optimized(self, segment_urls: List[str]) -> List[bytes]:
        """最適化されたセグメント並行ダウンロード
        
        Optimizations:
            - Connection pooling
            - Adaptive retry with exponential backoff
            - Memory-efficient streaming
            - Progress tracking
        """
        
        connector = aiohttp.TCPConnector(
            limit=self.max_workers * 2,
            limit_per_host=self.max_workers,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'RecRadiko/1.0'}
        ) as session:
            
            tasks = []
            for i, url in enumerate(segment_urls):
                task = asyncio.create_task(
                    self._download_segment_with_retry(session, url, i)
                )
                tasks.append(task)
            
            # Progress tracking
            segments = [None] * len(segment_urls)
            completed = 0
            
            with tqdm(total=len(segment_urls), desc="Downloading segments") as pbar:
                for task in asyncio.as_completed(tasks):
                    try:
                        index, data = await task
                        segments[index] = data
                        completed += 1
                        pbar.update(1)
                    except Exception as e:
                        self.logger.error(f"Segment download failed: {e}")
                        
            return [s for s in segments if s is not None]
    
    async def _download_segment_with_retry(self, session: aiohttp.ClientSession, 
                                         url: str, index: int) -> Tuple[int, bytes]:
        """リトライ付きセグメントダウンロード"""
        
        async with self.semaphore:
            for attempt in range(len(self.retry_delays) + 1):
                try:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        data = await response.read()
                        return index, data
                        
                except Exception as e:
                    if attempt < len(self.retry_delays):
                        delay = self.retry_delays[attempt]
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise SegmentDownloadError(f"Failed after {attempt + 1} attempts: {e}")
```

### 4.2 メモリ最適化
```python
class MemoryEfficientSegmentProcessor:
    """メモリ効率的なセグメント処理"""
    
    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size
        
    async def stream_combine_segments(self, segment_urls: List[str], 
                                    output_path: str):
        """ストリーミング方式でのセグメント結合
        
        Memory Optimization:
            - Segments are processed one by one
            - No full content in memory
            - Direct file writing
        """
        
        with open(output_path, 'wb') as output_file:
            for i, url in enumerate(segment_urls):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        
                        async for chunk in response.content.iter_chunked(self.chunk_size):
                            output_file.write(chunk)
                            
                # Progress update
                if i % 10 == 0:
                    progress = (i + 1) / len(segment_urls) * 100
                    print(f"Processing: {progress:.1f}%")
```

## 5. エラーハンドリング詳細設計

### 5.1 エラー階層
```python
class TimeFreeError(Exception):
    """タイムフリー関連エラーの基底クラス"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

class TimeFreeAuthError(TimeFreeError):
    """タイムフリー認証エラー"""
    pass

class ProgramNotFoundError(TimeFreeError):
    """番組未発見エラー"""
    
    def __init__(self, keyword: str, suggestions: List[str] = None):
        self.keyword = keyword
        self.suggestions = suggestions or []
        super().__init__(f"番組が見つかりません: {keyword}")

class TimeFreeExpiredError(TimeFreeError):
    """タイムフリー期限切れエラー"""
    
    def __init__(self, program_title: str, expired_at: datetime):
        self.program_title = program_title
        self.expired_at = expired_at
        super().__init__(f"タイムフリー期限切れ: {program_title} (期限: {expired_at})")

class SegmentDownloadError(TimeFreeError):
    """セグメントダウンロードエラー"""
    
    def __init__(self, failed_segments: List[int], total_segments: int):
        self.failed_segments = failed_segments
        self.total_segments = total_segments
        self.success_rate = (total_segments - len(failed_segments)) / total_segments
        super().__init__(f"セグメントダウンロード失敗: {len(failed_segments)}/{total_segments}")

class FileConversionError(TimeFreeError):
    """ファイル変換エラー"""
    pass
```

### 5.2 エラーリカバリー戦略
```python
class ErrorRecoveryManager:
    """エラーリカバリー管理"""
    
    def __init__(self):
        self.recovery_strategies = {
            TimeFreeAuthError: self._recover_auth_error,
            SegmentDownloadError: self._recover_download_error,
            FileConversionError: self._recover_conversion_error
        }
    
    async def handle_error(self, error: Exception, context: Dict) -> bool:
        """エラーハンドリングとリカバリー
        
        Args:
            error: 発生したエラー
            context: エラーコンテキスト
            
        Returns:
            bool: リカバリー成功の場合True
        """
        error_type = type(error)
        
        if error_type in self.recovery_strategies:
            try:
                return await self.recovery_strategies[error_type](error, context)
            except Exception as e:
                self.logger.error(f"リカバリー処理失敗: {e}")
                return False
        
        return False
    
    async def _recover_auth_error(self, error: TimeFreeAuthError, context: Dict) -> bool:
        """認証エラーのリカバリー"""
        # 認証情報のクリアと再認証
        authenticator = context.get('authenticator')
        if authenticator:
            authenticator.clear_session()
            return await authenticator.authenticate()
        return False
    
    async def _recover_download_error(self, error: SegmentDownloadError, context: Dict) -> bool:
        """ダウンロードエラーのリカバリー"""
        # 失敗セグメントの再ダウンロード
        if error.success_rate > 0.8:  # 80%以上成功していれば継続
            return True
        return False
    
    async def _recover_conversion_error(self, error: FileConversionError, context: Dict) -> bool:
        """変換エラーのリカバリー"""
        # 別の変換方式での再試行
        return False
```

---

**作成日**: 2025年7月13日  
**バージョン**: 1.0  
**最終更新**: 2025年7月13日