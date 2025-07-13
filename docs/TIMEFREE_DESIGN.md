# RecRadiko タイムフリー専用アプリケーション 概要設計書

## 1. システム概要

### 1.1 設計方針
RadikoのタイムフリーAPIを活用した専用録音システムを構築し、HLS制約（5分制限）を完全に回避する。

### 1.2 アーキテクチャの変更
```
【変更前】ライブ録音 + タイムフリー対応
RecRadiko.py → CLI → LiveStreaming → HLS制約(5分)

【変更後】タイムフリー専用システム
RecRadiko.py → CLI → TimeFree → 完全録音(無制限)
```

### 1.3 システム構成図
```
┌─────────────────────────────────────────────────────────┐
│                    RecRadiko.py                         │
│                   (エントリーポイント)                      │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│                  CLI Interface                         │
│        (対話型専用コマンド処理)                           │
│  • list-programs  • record  • search-programs         │
│  • record-id      • help    • exit                    │
└─────────────────┬───────────────────────────────────────┘
                  │
        ┌─────────┼─────────┐
        │         │         │
┌───────▼──┐ ┌────▼────┐ ┌─▼─────────┐
│ProgramAPI│ │TimeFree │ │FileManager│
│ History  │ │Recorder │ │           │
└──────────┘ └─────────┘ └───────────┘
        │         │         │
┌───────▼─────────▼─────────▼───────────┐
│          RadikoAuthenticator          │
│        (タイムフリー認証拡張)             │
└───────────────────────────────────────┘
```

## 2. モジュール設計

### 2.1 新規モジュール

#### 2.1.1 src/timefree_recorder.py
**責務**: タイムフリー録音の専用処理
```python
class TimeFreeRecorder:
    """タイムフリー専用録音クラス"""
    
    def __init__(self, authenticator: RadikoAuthenticator):
        self.authenticator = authenticator
        self.session = requests.Session()
        self.downloader = ConcurrentSegmentDownloader()
    
    async def record_program(self, program_id: str, output_path: str) -> RecordingResult:
        """番組IDを指定してタイムフリー録音実行"""
        
    async def record_by_datetime(self, station_id: str, start_time: datetime, 
                                end_time: datetime, output_path: str) -> RecordingResult:
        """日時を指定してタイムフリー録音実行"""
        
    def _get_timefree_playlist_url(self, station_id: str, start_time: datetime, 
                                  end_time: datetime) -> str:
        """タイムフリーM3U8 URL生成"""
        
    async def _download_all_segments(self, playlist_url: str) -> List[bytes]:
        """全セグメントの並行ダウンロード"""
        
    def _combine_segments_with_metadata(self, segments: List[bytes], 
                                       program_info: ProgramInfo, 
                                       output_path: str):
        """セグメント結合とメタデータ埋め込み"""
```

#### 2.1.2 src/program_history.py
**責務**: 過去番組表の取得と管理
```python
class ProgramHistoryManager:
    """過去番組表管理クラス"""
    
    def __init__(self, authenticator: RadikoAuthenticator):
        self.authenticator = authenticator
        self.cache = ProgramCache(expire_hours=24)
    
    def get_programs_by_date(self, date: str, station_id: str = None) -> List[ProgramInfo]:
        """指定日の番組表取得"""
        
    def search_programs(self, keyword: str, date_range: Tuple[str, str] = None) -> List[ProgramInfo]:
        """キーワードによる番組検索"""
        
    def get_program_by_id(self, program_id: str) -> Optional[ProgramInfo]:
        """番組ID指定での番組情報取得"""
        
    def _fetch_program_xml(self, date: str, area_id: str) -> str:
        """Radiko番組表XMLの取得"""
        
    def _parse_program_xml(self, xml_data: str) -> List[ProgramInfo]:
        """番組表XMLのパース処理"""
```

#### 2.1.3 src/program_info.py (拡張)
**責務**: 番組情報データクラスの拡張
```python
@dataclass
class ProgramInfo:
    """番組情報データクラス（タイムフリー対応）"""
    program_id: str
    station_id: str
    station_name: str
    title: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    description: str
    performers: List[str]
    genre: str
    is_timefree_available: bool
    timefree_end_time: datetime
    
    def to_filename(self) -> str:
        """録音ファイル名生成"""
        date_str = self.start_time.strftime('%Y%m%d')
        safe_title = re.sub(r'[^\w\-_\.]', '_', self.title)
        return f"{self.station_id}_{date_str}_{safe_title}"
    
    def to_metadata(self) -> Dict[str, str]:
        """ID3タグメタデータ生成"""
        return {
            'title': self.title,
            'artist': ', '.join(self.performers),
            'album': self.station_name,
            'date': self.start_time.strftime('%Y-%m-%d'),
            'genre': 'Radio',
            'comment': self.description
        }
```

### 2.2 既存モジュールの改修

#### 2.2.1 src/cli.py (大幅改修)
**変更内容**: タイムフリー専用コマンド体系への移行
```python
class TimeFreeRecRadikoCLI:
    """タイムフリー専用CLIクラス"""
    
    COMMANDS = [
        'list-programs', 'record', 'record-id', 
        'search-programs', 'help', 'exit'
    ]
    
    def __init__(self):
        self.program_manager = ProgramHistoryManager(self.authenticator)
        self.recorder = TimeFreeRecorder(self.authenticator)
        self.file_manager = FileManager()
    
    def _cmd_list_programs(self, args):
        """番組表取得: list-programs 2025-07-10 TBS"""
        
    def _cmd_record(self, args):
        """録音実行: record 2025-07-10 TBS 森本毅郎・スタンバイ!"""
        
    def _cmd_record_id(self, args):
        """ID指定録音: record-id TBS_20250710_060000"""
        
    def _cmd_search_programs(self, args):
        """番組検索: search-programs 森本毅郎"""
```

#### 2.2.2 src/auth.py (認証拡張)
**変更内容**: タイムフリー認証の強化
```python
class RadikoAuthenticator:
    """Radiko認証クラス（タイムフリー対応）"""
    
    def get_timefree_session(self, station_id: str, start_time: datetime, 
                           end_time: datetime) -> str:
        """タイムフリー専用セッション取得"""
        
    def _generate_timefree_url(self, station_id: str, start_time: datetime, 
                             end_time: datetime, session_id: str) -> str:
        """タイムフリーURL生成"""
        # https://radiko.jp/v2/api/ts/playlist.m3u8?station_id={STATION}&l=15&lsid={LSID}&ft={START}&to={END}
```

### 2.3 削除対象モジュール

#### 2.3.1 src/live_streaming.py (完全削除)
- HLS制約による5分制限の原因
- ライブ録音機能全体を削除
- 関連するLivePlaylistMonitor等も削除

#### 2.3.2 src/scheduler.py (機能制限)
- 将来録音スケジュール機能を削除
- 過去録音のバッチ処理機能のみ残存

## 3. データフロー設計

### 3.1 番組表取得フロー
```
1. ユーザーコマンド入力
   ↓
2. CLI.list_programs() 呼び出し
   ↓
3. ProgramHistoryManager.get_programs_by_date()
   ↓
4. キャッシュ確認
   ↓
5. Radiko番組表API呼び出し (未キャッシュ時)
   ↓
6. XML解析・ProgramInfo生成
   ↓
7. 番組リスト表示
```

### 3.2 録音実行フロー
```
1. ユーザーコマンド入力: record 2025-07-10 TBS 森本毅郎
   ↓
2. CLI.record() 呼び出し
   ↓
3. ProgramHistoryManager.search_programs() - 番組特定
   ↓
4. TimeFreeRecorder.record_program() 呼び出し
   ↓
5. RadikoAuthenticator.get_timefree_session() - 認証
   ↓
6. タイムフリーM3U8 URL生成
   ↓
7. 全セグメント並行ダウンロード
   ↓
8. セグメント結合・フォーマット変換
   ↓
9. ID3メタデータ埋め込み
   ↓
10. 録音完了通知
```

## 4. API設計

### 4.1 Radiko タイムフリーAPI
```
# 番組表取得
GET https://radiko.jp/v3/program/date/{YYYYMMDD}/{area_id}.xml

# タイムフリーM3U8取得
GET https://radiko.jp/v2/api/ts/playlist.m3u8?station_id={STATION}&l=15&lsid={LSID}&ft={START_TIME}&to={END_TIME}

# パラメータ:
# STATION: 放送局ID (TBS, QRR, LFR, etc.)
# LSID: セッションID (認証で取得)
# START_TIME: 開始時刻 (YmdHis形式: 20250710060000)
# END_TIME: 終了時刻 (YmdHis形式: 20250710083000)
```

### 4.2 内部API設計
```python
# 録音API
async def record_program(program_id: str, output_path: str) -> RecordingResult

# 番組検索API
def search_programs(keyword: str, date_range: Optional[Tuple[str, str]]) -> List[ProgramInfo]

# 番組表取得API
def get_programs_by_date(date: str, station_id: Optional[str]) -> List[ProgramInfo]
```

## 5. パフォーマンス設計

### 5.1 並行ダウンロード最適化
```python
class ConcurrentSegmentDownloader:
    """並行セグメントダウンローダー"""
    
    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self.session_pool = []
    
    async def download_all_segments(self, segment_urls: List[str]) -> List[bytes]:
        """全セグメントの並行ダウンロード"""
        # 8並行での高速ダウンロード
        # 2.5時間番組 → 10分以内での完了目標
```

### 5.2 キャッシュ戦略
```python
class ProgramCache:
    """番組表キャッシュ"""
    
    def __init__(self, expire_hours: int = 24):
        self.cache_dir = Path("~/.recradiko/cache")
        self.expire_hours = expire_hours
    
    def get_cached_programs(self, date: str, station_id: str) -> Optional[List[ProgramInfo]]:
        """キャッシュされた番組表取得"""
        
    def store_programs(self, date: str, station_id: str, programs: List[ProgramInfo]):
        """番組表のキャッシュ保存"""
```

## 6. エラーハンドリング設計

### 6.1 エラー分類
```python
class TimeFreeError(Exception):
    """タイムフリー関連エラーの基底クラス"""

class ProgramNotFoundError(TimeFreeError):
    """番組が見つからない場合のエラー"""

class TimeFreeExpiredError(TimeFreeError):
    """タイムフリー期限切れエラー"""

class DownloadFailedError(TimeFreeError):
    """ダウンロード失敗エラー"""

class AuthenticationFailedError(TimeFreeError):
    """認証失敗エラー"""
```

### 6.2 エラーハンドリング戦略
```python
def handle_timefree_error(error: Exception) -> str:
    """タイムフリーエラーの統一処理"""
    if isinstance(error, ProgramNotFoundError):
        return "番組が見つかりません。日付や番組名を確認してください。"
    elif isinstance(error, TimeFreeExpiredError):
        return "タイムフリーの視聴期限が切れています。"
    elif isinstance(error, DownloadFailedError):
        return "ダウンロードに失敗しました。ネットワーク接続を確認してください。"
    else:
        return f"予期しないエラーが発生しました: {error}"
```

## 7. 設定・データ管理

### 7.1 設定ファイル構造
```json
{
  "timefree_config": {
    "default_format": "mp3",
    "default_quality": "256",
    "download_workers": 8,
    "cache_expire_hours": 24,
    "output_directory": "./recordings",
    "metadata_embedding": true
  },
  "ui_config": {
    "timezone": "Asia/Tokyo",
    "date_format": "YYYY-MM-DD",
    "progress_bar": true,
    "auto_cleanup": false
  }
}
```

### 7.2 データベーススキーマ
```sql
-- 録音履歴テーブル
CREATE TABLE recording_history (
    id INTEGER PRIMARY KEY,
    program_id TEXT NOT NULL,
    title TEXT NOT NULL,
    station_id TEXT NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    duration_seconds INTEGER,
    format TEXT,
    status TEXT
);

-- 番組キャッシュテーブル
CREATE TABLE program_cache (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    station_id TEXT NOT NULL,
    program_data TEXT NOT NULL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, station_id)
);
```

## 8. セキュリティ設計

### 8.1 認証情報保護
- 認証トークンの暗号化保存
- メモリ上での認証情報の適切なクリア
- ログファイルからの認証情報除外

### 8.2 レート制限対応
- APIリクエスト間隔の制御
- 過度な並行接続の制限
- Radiko利用規約の遵守

## 9. テスト設計

### 9.1 テスト分類
- **単体テスト**: 各モジュールの機能テスト
- **結合テスト**: モジュール間連携テスト
- **E2Eテスト**: タイムフリー録音の完全フローテスト

### 9.2 テスト対象
```python
# TimeFreeRecorderのテスト
def test_timefree_recording():
    """タイムフリー録音の基本機能テスト"""

def test_metadata_embedding():
    """メタデータ埋め込み機能テスト"""

# ProgramHistoryManagerのテスト
def test_program_search():
    """番組検索機能テスト"""

def test_program_cache():
    """番組表キャッシュ機能テスト"""
```

## 10. 移行計画

### 10.1 段階的実装
1. **フェーズ1**: 基盤モジュール実装（TimeFreeRecorder, ProgramHistoryManager）
2. **フェーズ2**: CLI統合とコマンド体系変更
3. **フェーズ3**: ライブ録音機能の無効化
4. **フェーズ4**: テスト・デバッグ・最適化

### 10.2 検証項目
- [ ] 2.5時間番組の完全録音（10分以内）
- [ ] メタデータ埋め込みの動作確認
- [ ] 番組検索の精度確認
- [ ] 並行ダウンロードの安定性確認
- [ ] エラーハンドリングの適切性確認

---

**作成日**: 2025年7月13日  
**バージョン**: 1.0  
**最終更新**: 2025年7月13日