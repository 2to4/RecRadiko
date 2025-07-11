# ライブストリーミング対応録音システム設計書

## 概要

RecRadikoのライブストリーミング録音機能を実現するための技術設計書です。現在の静的プレイリスト方式（約5分制限）から、継続的なライブストリーミング監視方式への移行により、任意の長時間録音を可能にします。

## 現状分析

### 現在の問題点
- **録音時間制限**: HLSプレイリストの静的セグメント（約60個=5分）に依存
- **ライブ特性の未対応**: プレイリストの動的更新に非対応
- **セグメント管理不備**: 新規セグメントの継続取得機能なし
- **API制限**: Radiko側の一回取得制限による録音時間の物理的制約

### 技術的制約
- Radiko HLS プレイリストは定期的に更新される
- 各プレイリストには限定的なセグメント数のみ含まれる
- セグメントURLには有効期限が存在する
- ライブストリームは継続的なポーリングが必要

## アーキテクチャ設計

### システム構成図

```
┌─────────────────────┐    ┌──────────────────────┐    ┌────────────────────┐
│  RecordingManager   │◄───│ LiveRecordingSession │◄───│ LivePlaylistMonitor│
└─────────────────────┘    └──────────────────────┘    └────────────────────┘
            │                         │                          │
            ▼                         ▼                          ▼
┌─────────────────────┐    ┌──────────────────────┐    ┌────────────────────┐
│ SegmentDownloader   │    │   SegmentTracker     │    │  PlaylistParser    │
└─────────────────────┘    └──────────────────────┘    └────────────────────┘
            │                         │                          │
            └─────────────────────────┴──────────────────────────┘
                                      │
                                      ▼
                            ┌────────────────────┐
                            │   Output Stream    │
                            └────────────────────┘
```

## コンポーネント設計

### 1. LivePlaylistMonitor クラス

**責務**: ライブプレイリストの継続監視と新規セグメント検出

```python
class LivePlaylistMonitor:
    """ライブプレイリストの継続監視システム"""
    
    def __init__(self, 
                 playlist_url: str, 
                 update_interval: int = 15,
                 timeout: int = 10):
        """
        Args:
            playlist_url: 監視対象のM3U8プレイリストURL
            update_interval: プレイリスト更新間隔（秒）
            timeout: HTTP要求タイムアウト（秒）
        """
        self.playlist_url = playlist_url
        self.update_interval = update_interval
        self.timeout = timeout
        self.is_monitoring = False
        self.last_sequence = 0
        
    async def start_monitoring(self) -> AsyncGenerator[PlaylistUpdate, None]:
        """プレイリスト監視開始"""
        
    async def stop_monitoring(self):
        """プレイリスト監視停止"""
        
    async def fetch_playlist(self) -> m3u8.M3U8:
        """プレイリスト取得"""
        
    def extract_new_segments(self, playlist: m3u8.M3U8) -> List[Segment]:
        """新規セグメント抽出"""
```

**主要機能**:
- 定期的なプレイリスト取得（15-30秒間隔）
- 新規セグメントの検出とフィルタリング
- ネットワークエラー時の自動リトライ
- タイムアウト管理

### 2. SegmentTracker クラス

**責務**: セグメントの重複回避と順序管理

```python
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
        
    def is_new_segment(self, segment: Segment) -> bool:
        """新規セグメント判定"""
        
    def register_segment(self, segment: Segment):
        """セグメント登録"""
        
    def get_missing_segments(self) -> List[int]:
        """欠落セグメント検出"""
        
    def cleanup_old_segments(self):
        """古いセグメント情報のクリーンアップ"""
```

**主要機能**:
- セグメント重複ダウンロードの防止
- セグメント順序の管理と欠落検出
- メモリ使用量の制御（LRUベースのクリーンアップ）
- セグメント統計情報の提供

### 3. LiveRecordingSession クラス

**責務**: ライブ録音セッションの統合管理

```python
class LiveRecordingSession:
    """ライブストリーミング録音セッション管理"""
    
    def __init__(self, 
                 job: RecordingJob,
                 streaming_manager: StreamingManager):
        """
        Args:
            job: 録音ジョブ情報
            streaming_manager: ストリーミング管理インスタンス
        """
        self.job = job
        self.streaming_manager = streaming_manager
        self.monitor: Optional[LivePlaylistMonitor] = None
        self.tracker = SegmentTracker()
        self.start_time = time.time()
        self.downloaded_bytes = 0
        self.segment_count = 0
        
    async def start_recording(self, output_path: str) -> RecordingResult:
        """ライブ録音開始"""
        
    async def stop_recording(self):
        """ライブ録音停止"""
        
    def get_progress(self) -> RecordingProgress:
        """録音進捗取得"""
        
    def should_continue_recording(self) -> bool:
        """録音継続判定"""
```

**主要機能**:
- プレイリスト監視とセグメントダウンロードの協調制御
- 録音時間制限の管理
- 進捗情報の生成と通知
- エラー状況での自動復旧

### 4. SegmentDownloader クラス

**責務**: セグメントの並行ダウンロード管理

```python
class SegmentDownloader:
    """セグメント並行ダウンロードシステム"""
    
    def __init__(self, 
                 max_concurrent: int = 3,
                 download_timeout: int = 10):
        """
        Args:
            max_concurrent: 最大並行ダウンロード数
            download_timeout: ダウンロードタイムアウト（秒）
        """
        self.max_concurrent = max_concurrent
        self.download_timeout = download_timeout
        self.download_queue = asyncio.Queue()
        self.active_downloads: Set[asyncio.Task] = set()
        
    async def download_segment(self, segment_url: str) -> bytes:
        """単一セグメントダウンロード"""
        
    async def download_segments_parallel(self, 
                                       segments: List[str]) -> AsyncGenerator[bytes, None]:
        """並行セグメントダウンロード"""
        
    async def start_download_workers(self):
        """ダウンロードワーカー開始"""
        
    async def stop_download_workers(self):
        """ダウンロードワーカー停止"""
```

**主要機能**:
- セグメントの並行ダウンロード（3-5並行）
- ダウンロードキューの管理
- 失敗セグメントのリトライ処理
- ダウンロード速度の監視

## RecordingManager 拡張設計

### 既存メソッドの変更

```python
class RecordingManager:
    # 既存実装に追加
    
    def _execute_recording(self, job: RecordingJob):
        """録音実行（ライブ/静的判定追加）"""
        try:
            # ... 既存の準備処理 ...
            
            # ライブ録音か静的録音かを判定
            now = datetime.now()
            is_live_recording = self._is_live_recording(job, now)
            
            if is_live_recording:
                self._record_stream_live(job, stream_info, tmp_path)
            else:
                self._record_stream_static(job, stream_info, tmp_path)
                
            # ... 既存の後処理 ...
            
        except Exception as e:
            self._handle_job_error(job, str(e))
    
    def _is_live_recording(self, job: RecordingJob, current_time: datetime) -> bool:
        """ライブ録音判定"""
        return (job.start_time <= current_time <= job.end_time)
    
    def _record_stream_live(self, job: RecordingJob, stream_info, output_path: str):
        """ライブストリーミング録音（新メソッド）"""
        
    def _record_stream_static(self, job: RecordingJob, stream_info, output_path: str):
        """静的プレイリスト録音（既存ロジック）"""
        # 既存の_record_streamロジックをリネーム
```

## データ構造定義

### PlaylistUpdate

```python
@dataclass
class PlaylistUpdate:
    """プレイリスト更新情報"""
    timestamp: datetime
    sequence_number: int
    new_segments: List[Segment]
    total_segments: int
    duration_seconds: float
```

### Segment

```python
@dataclass
class Segment:
    """セグメント情報"""
    url: str
    sequence_number: int
    duration: float
    byte_range: Optional[Tuple[int, int]] = None
    key_info: Optional[Dict[str, str]] = None
```

### SegmentInfo

```python
@dataclass
class SegmentInfo:
    """セグメント管理情報"""
    segment: Segment
    download_time: datetime
    file_size: int
    download_duration: float
    retry_count: int = 0
```

### RecordingResult

```python
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
```

## エラーハンドリング設計

### エラー分類と対応

| エラータイプ | 対応方針 | 実装方法 |
|-------------|----------|----------|
| ネットワーク一時エラー | 自動リトライ | 指数バックオフ（1, 2, 4秒） |
| プレイリスト取得失敗 | リトライ後フォールバック | 最大5回リトライ、失敗時は録音継続 |
| セグメント取得失敗 | セグメントスキップ | ログ出力のみ、録音継続 |
| 認証エラー | 再認証 | 認証トークン更新、録音再開 |
| ディスク容量不足 | 録音停止 | 緊急停止、エラー通知 |

### エラーハンドラー実装

```python
class LiveRecordingErrorHandler:
    """ライブ録音エラー処理"""
    
    @staticmethod
    async def handle_playlist_error(error: Exception, 
                                  retry_count: int) -> bool:
        """プレイリストエラー処理"""
        
    @staticmethod
    async def handle_segment_error(segment_url: str, 
                                 error: Exception) -> bool:
        """セグメントエラー処理"""
        
    @staticmethod
    async def handle_network_error(error: Exception,
                                 operation: str) -> int:
        """ネットワークエラー処理"""
```

## 設定とパフォーマンス

### 設定パラメータ

```python
LIVE_RECORDING_CONFIG = {
    # プレイリスト監視設定
    'playlist_update_interval': 15,      # プレイリスト更新間隔（秒）
    'playlist_fetch_timeout': 10,        # プレイリスト取得タイムアウト
    'playlist_retry_attempts': 5,        # プレイリスト取得リトライ回数
    'playlist_retry_delay': 2,           # リトライ間隔（秒）
    
    # セグメントダウンロード設定
    'max_concurrent_downloads': 3,       # 並行ダウンロード数
    'segment_download_timeout': 10,      # セグメントダウンロードタイムアウト
    'segment_retry_attempts': 3,         # セグメントリトライ回数
    'segment_buffer_size': 5,            # バッファセグメント数
    
    # メモリ管理設定
    'segment_history_size': 100,         # セグメント履歴保持数
    'memory_cleanup_interval': 300,      # メモリクリーンアップ間隔（秒）
    
    # パフォーマンス設定
    'async_timeout': 30,                 # 非同期処理タイムアウト
    'connection_pool_size': 10,          # HTTP接続プールサイズ
}
```

### パフォーマンス最適化

1. **非同期処理**: asyncio による並行ダウンロード
2. **接続プール**: HTTP接続の再利用
3. **メモリ管理**: LRUベースのセグメント履歴管理
4. **バッファリング**: 先読みセグメントバッファ
5. **レート制限**: API呼び出し頻度の制御

## 実装スケジュール

### Phase 1: 基盤実装（1週間）
- [ ] `LivePlaylistMonitor` クラス実装
- [ ] `SegmentTracker` クラス実装
- [ ] 基本的な非同期処理フレームワーク
- [ ] 単体テスト作成

### Phase 2: 統合実装（1週間）
- [ ] `LiveRecordingSession` クラス実装
- [ ] `SegmentDownloader` クラス実装
- [ ] `RecordingManager` 拡張
- [ ] 結合テスト作成

### Phase 3: エラーハンドリング（3日）
- [ ] `LiveRecordingErrorHandler` 実装
- [ ] 各種エラーシナリオ対応
- [ ] エラー処理テスト作成

### Phase 4: 最適化とテスト（4日）
- [ ] パフォーマンス最適化
- [ ] E2Eテスト実装
- [ ] 長時間録音テスト（1時間+）
- [ ] メモリリーク検証

### Phase 5: 統合とドキュメント（2日）
- [ ] 既存コードベースとの統合
- [ ] ユーザーマニュアル更新
- [ ] 設定ファイル対応
- [ ] 最終テスト実行

## テスト戦略

### 単体テスト
- 各クラスの基本機能テスト
- エラーケースのテスト
- モック使用によるネットワーク処理テスト

### 結合テスト
- コンポーネント間の連携テスト
- プレイリスト更新シナリオテスト
- セグメント取得フローテスト

### E2Eテスト
- 実際のRadiko APIを使用した長時間録音テスト
- ネットワーク障害シミュレーション
- メモリ使用量・CPU使用率の監視

### パフォーマンステスト
- 10分、30分、1時間の継続録音テスト
- 並行録音（複数局同時）テスト
- リソース使用量の測定

## リスク分析

### 技術的リスク
- **API変更**: Radiko側のHLS仕様変更
- **レート制限**: API呼び出し頻度制限
- **メモリリーク**: 長時間録音でのメモリ増加
- **CPU負荷**: 並行ダウンロードによる負荷増加

### 対応策
- **API監視**: 定期的なAPI動作確認
- **設定調整**: 呼び出し間隔の動的調整
- **メモリ管理**: 定期的なガベージコレクション
- **負荷制御**: CPU使用率ベースの並行数制御

## 期待効果

### 機能面
- **任意長録音**: 時間制限のない録音が可能
- **高品質録音**: セグメント欠落の最小化
- **安定性向上**: エラー耐性の強化

### ユーザー体験
- **利便性向上**: 長時間番組の完全録音
- **信頼性向上**: 録音失敗の大幅削減
- **監視機能**: リアルタイム進捗表示

### システム品質
- **拡張性**: 将来の機能追加への対応
- **保守性**: モジュラー設計による保守容易性
- **テスト性**: 包括的なテストカバレッジ

## 結論

このライブストリーミング対応設計により、RecRadikoは技術的制約を克服し、真の意味での「任意時間録音」を実現できます。段階的な実装アプローチにより、既存機能を維持しながら安全に新機能を導入できる設計となっています。