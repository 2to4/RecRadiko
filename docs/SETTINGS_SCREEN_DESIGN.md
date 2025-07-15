# 設定画面詳細設計書

## 1. 概要

### 1.1 目的
RecRadikoアプリケーションの設定管理画面のキーボードナビゲーション対応実装における詳細設計を定義する。

### 1.2 対象範囲
- 設定画面UI実装（SettingsScreen）
- 設定データ管理（ConfigManager）
- 設定項目の変更処理
- バリデーション機能
- 地域設定の都道府県名対応

### 1.3 前提条件
- UI_SPECIFICATION.mdの設定画面仕様に準拠
- 既存ScreenBaseフレームワークを使用
- RegionMapperとの統合
- 既存設定システムとの互換性維持

---

## 2. アーキテクチャ設計

### 2.1 クラス構成

```
SettingsScreen
├── ConfigManager (設定データ管理)
├── RegionMapper (地域設定管理)
├── SettingValidator (設定値検証)
└── SettingItem (設定項目定義)
```

### 2.2 クラス関係図

```
ScreenBase
    ↑
SettingsScreen
    ├── ConfigManager
    ├── RegionMapper
    ├── SettingValidator
    └── List<SettingItem>
```

---

## 3. 詳細設計

### 3.1 SettingsScreen クラス

#### 3.1.1 基本構造

```python
class SettingsScreen(ScreenBase):
    """
    設定管理画面
    
    機能:
    - 設定項目の一覧表示
    - 設定値の変更処理
    - 設定の保存・読み込み
    - バリデーション
    """
    
    def __init__(self):
        super().__init__()
        self.set_title("設定管理")
        self.config_manager = ConfigManager()
        self.region_mapper = RegionMapper()
        self.validator = SettingValidator()
        self.setting_items: List[SettingItem] = []
        self.current_settings: Dict[str, Any] = {}
        
    def display_content(self) -> None:
        """設定画面コンテンツ表示"""
        
    def run_settings_workflow(self) -> bool:
        """設定管理ワークフロー実行"""
        
    def handle_setting_change(self, setting_id: str) -> bool:
        """設定項目変更処理"""
        
    def save_settings(self) -> bool:
        """設定保存"""
        
    def load_settings(self) -> bool:
        """設定読み込み"""
        
    def reset_to_defaults(self) -> bool:
        """デフォルト設定復元"""
        
    def export_settings(self) -> bool:
        """設定エクスポート"""
        
    def import_settings(self) -> bool:
        """設定インポート"""
```

#### 3.1.2 設定項目定義

```python
@dataclass
class SettingItem:
    """設定項目定義"""
    id: str                     # 設定ID
    title: str                  # 表示名
    description: str            # 説明文
    current_value: Any          # 現在値
    default_value: Any          # デフォルト値
    setting_type: SettingType   # 設定タイプ
    options: Optional[List[str]] = None  # 選択肢（選択タイプ時）
    validator: Optional[Callable] = None  # バリデーション関数
    
class SettingType(Enum):
    """設定タイプ"""
    REGION = "region"           # 地域設定
    AUDIO_QUALITY = "audio"     # 音質設定
    FILE_PATH = "path"          # ファイルパス
    BOOLEAN = "boolean"         # ON/OFF
    SELECTION = "selection"     # 選択肢
    ACTION = "action"           # アクション（リセット等）
```

#### 3.1.3 設定項目初期化

```python
def _initialize_setting_items(self) -> List[SettingItem]:
    """設定項目初期化"""
    return [
        SettingItem(
            id="region",
            title="地域設定",
            description="録音可能な地域を設定",
            current_value=self._get_current_region_display(),
            default_value="東京都",
            setting_type=SettingType.REGION
        ),
        SettingItem(
            id="audio_quality",
            title="音質設定",
            description="録音音質を設定",
            current_value=self._get_current_audio_quality(),
            default_value="MP3 256kbps, 48kHz",
            setting_type=SettingType.AUDIO_QUALITY,
            options=["MP3 128kbps, 44kHz", "MP3 256kbps, 48kHz", "AAC 128kbps, 44kHz", "AAC 256kbps, 48kHz"]
        ),
        SettingItem(
            id="save_path",
            title="保存先",
            description="録音ファイルの保存先",
            current_value=self._get_current_save_path(),
            default_value="~/Downloads/RecRadiko/",
            setting_type=SettingType.FILE_PATH
        ),
        SettingItem(
            id="id3_tags",
            title="録音後処理",
            description="ID3タグの自動付与",
            current_value=self._get_current_id3_setting(),
            default_value=True,
            setting_type=SettingType.BOOLEAN
        ),
        SettingItem(
            id="notifications",
            title="通知設定",
            description="完了通知の設定",
            current_value=self._get_current_notification_setting(),
            default_value="macOS標準通知",
            setting_type=SettingType.SELECTION,
            options=["無効", "macOS標準通知", "音声通知", "メール通知"]
        ),
        SettingItem(
            id="reset_defaults",
            title="設定をデフォルトに戻す",
            description="全設定を初期値に戻す",
            current_value=None,
            default_value=None,
            setting_type=SettingType.ACTION
        ),
        SettingItem(
            id="export_settings",
            title="設定ファイルエクスポート",
            description="設定をファイルに保存",
            current_value=None,
            default_value=None,
            setting_type=SettingType.ACTION
        ),
        SettingItem(
            id="import_settings",
            title="設定ファイルインポート",
            description="設定をファイルから読み込み",
            current_value=None,
            default_value=None,
            setting_type=SettingType.ACTION
        )
    ]
```

### 3.2 ConfigManager クラス

#### 3.2.1 基本構造

```python
class ConfigManager:
    """設定データ管理"""
    
    def __init__(self, config_file: str = "~/.recradiko/config.json"):
        self.config_file = Path(config_file).expanduser()
        self.config_data: Dict[str, Any] = {}
        self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """設定読み込み"""
        
    def save_config(self) -> bool:
        """設定保存"""
        
    def get_setting(self, key: str, default: Any = None) -> Any:
        """設定値取得"""
        
    def set_setting(self, key: str, value: Any) -> None:
        """設定値設定"""
        
    def reset_to_defaults(self) -> bool:
        """デフォルト設定復元"""
        
    def export_settings(self, export_path: str) -> bool:
        """設定エクスポート"""
        
    def import_settings(self, import_path: str) -> bool:
        """設定インポート"""
        
    def validate_config(self) -> Tuple[bool, List[str]]:
        """設定検証"""
```

#### 3.2.2 デフォルト設定

```python
DEFAULT_CONFIG = {
    "prefecture": "東京",
    "audio_format": "mp3",
    "audio_bitrate": 256,
    "audio_sample_rate": 48000,
    "save_path": "~/Downloads/RecRadiko/",
    "id3_tags_enabled": True,
    "notification_type": "macos_standard",
    "notification_enabled": True,
    "log_level": "INFO",
    "timeout_seconds": 30,
    "max_retries": 3,
    "user_agent": "RecRadiko/2.0"
}
```

### 3.3 SettingValidator クラス

#### 3.3.1 バリデーション機能

```python
class SettingValidator:
    """設定値検証"""
    
    def validate_region(self, prefecture: str) -> Tuple[bool, str]:
        """地域設定検証"""
        
    def validate_audio_quality(self, format_str: str) -> Tuple[bool, str]:
        """音質設定検証"""
        
    def validate_file_path(self, path: str) -> Tuple[bool, str]:
        """ファイルパス検証"""
        
    def validate_notification_setting(self, setting: str) -> Tuple[bool, str]:
        """通知設定検証"""
        
    def validate_boolean_setting(self, value: Any) -> Tuple[bool, str]:
        """Boolean設定検証"""
```

### 3.4 地域設定処理

#### 3.4.1 地域設定画面

```python
class RegionSettingScreen(ScreenBase):
    """地域設定画面"""
    
    def __init__(self, parent_screen: SettingsScreen):
        super().__init__()
        self.set_title("地域設定変更")
        self.parent_screen = parent_screen
        self.region_mapper = RegionMapper()
        self.regions = self._load_regions()
        
    def display_content(self) -> None:
        """地域設定コンテンツ表示"""
        
    def run_region_selection(self) -> Optional[str]:
        """地域選択ワークフロー"""
        
    def _load_regions(self) -> List[Dict[str, str]]:
        """地域一覧読み込み"""
        return [
            {"id": "hokkaido_tohoku", "name": "北海道・東北地方"},
            {"id": "kanto", "name": "関東地方"},
            {"id": "chubu", "name": "中部地方"},
            {"id": "kansai", "name": "近畿地方"},
            {"id": "chugoku_shikoku", "name": "中国・四国地方"},
            {"id": "kyushu_okinawa", "name": "九州・沖縄地方"}
        ]
```

#### 3.4.2 都道府県直接指定

```python
def handle_direct_prefecture_input(self) -> Optional[str]:
    """都道府県直接指定処理"""
    try:
        # 都道府県名入力
        prefecture_input = self.ui_service.get_text_input(
            prompt="都道府県名を入力してください: ",
            allow_empty=False
        )
        
        if not prefecture_input:
            return None
            
        # RegionMapperで検証・変換
        area_id = self.region_mapper.get_area_id(prefecture_input)
        if not area_id:
            self.ui_service.display_error("無効な都道府県名です")
            return None
            
        # 正規化された都道府県名を取得
        prefecture_name = self.region_mapper.get_prefecture_name(area_id)
        
        # 確認
        if self.ui_service.confirm(f"「{prefecture_name}」に設定しますか？"):
            return prefecture_name
            
        return None
        
    except Exception as e:
        self.logger.error(f"Prefecture input error: {e}")
        self.ui_service.display_error("都道府県名の処理中にエラーが発生しました")
        return None
```

### 3.5 音質設定処理

#### 3.5.1 音質設定画面

```python
class AudioQualitySettingScreen(ScreenBase):
    """音質設定画面"""
    
    def __init__(self, parent_screen: SettingsScreen):
        super().__init__()
        self.set_title("音質設定変更")
        self.parent_screen = parent_screen
        self.audio_options = self._load_audio_options()
        
    def _load_audio_options(self) -> List[Dict[str, Any]]:
        """音質オプション読み込み"""
        return [
            {
                "id": "mp3_128_44",
                "display": "MP3 128kbps, 44kHz",
                "format": "mp3",
                "bitrate": 128,
                "sample_rate": 44100,
                "description": "標準品質（ファイルサイズ小）"
            },
            {
                "id": "mp3_256_48",
                "display": "MP3 256kbps, 48kHz",
                "format": "mp3",
                "bitrate": 256,
                "sample_rate": 48000,
                "description": "高品質（推奨）"
            },
            {
                "id": "aac_128_44",
                "display": "AAC 128kbps, 44kHz",
                "format": "aac",
                "bitrate": 128,
                "sample_rate": 44100,
                "description": "標準品質（効率的圧縮）"
            },
            {
                "id": "aac_256_48",
                "display": "AAC 256kbps, 48kHz",
                "format": "aac",
                "bitrate": 256,
                "sample_rate": 48000,
                "description": "高品質（最高音質）"
            }
        ]
```

---

## 4. 画面フロー設計

### 4.1 基本フロー

```
MainMenu → SettingsScreen → [設定項目選択] → [設定変更] → SettingsScreen
```

### 4.2 詳細フロー

```
1. 設定画面表示
   ├── 現在設定値読み込み
   ├── 設定項目一覧表示
   └── ユーザー入力待機

2. 設定項目選択
   ├── 地域設定 → RegionSettingScreen
   ├── 音質設定 → AudioQualitySettingScreen
   ├── 保存先設定 → FilePathSettingScreen
   ├── Boolean設定 → BooleanSettingScreen
   ├── 通知設定 → NotificationSettingScreen
   └── アクション → ActionHandler

3. 設定変更処理
   ├── 入力値検証
   ├── 設定値更新
   ├── 設定保存
   └── 結果表示

4. 終了処理
   ├── 設定画面に戻る
   ├── メインメニューに戻る
   └── アプリケーション終了
```

---

## 5. データ構造設計

### 5.1 設定ファイル構造

```json
{
    "version": "2.0",
    "prefecture": "東京",
    "audio": {
        "format": "mp3",
        "bitrate": 256,
        "sample_rate": 48000
    },
    "recording": {
        "save_path": "~/Downloads/RecRadiko/",
        "id3_tags_enabled": true,
        "timeout_seconds": 30,
        "max_retries": 3
    },
    "notification": {
        "type": "macos_standard",
        "enabled": true
    },
    "system": {
        "log_level": "INFO",
        "user_agent": "RecRadiko/2.0"
    },
    "created_at": "2025-07-15T19:00:00Z",
    "updated_at": "2025-07-15T19:00:00Z"
}
```

### 5.2 設定変更履歴

```json
{
    "settings_history": [
        {
            "timestamp": "2025-07-15T19:00:00Z",
            "key": "prefecture",
            "old_value": "神奈川",
            "new_value": "東京",
            "user_action": "manual_change"
        }
    ]
}
```

---

## 6. エラーハンドリング設計

### 6.1 エラーカテゴリ

| エラー種別 | 対応処理 | ユーザー通知 |
|------------|----------|--------------|
| 設定ファイル読み込みエラー | デフォルト設定で続行 | "設定ファイルが見つかりません。デフォルト設定を使用します。" |
| 設定値検証エラー | 入力再要求 | "無効な値です。再入力してください。" |
| 設定保存エラー | 再試行・ログ出力 | "設定の保存に失敗しました。再試行してください。" |
| ファイルパス権限エラー | 代替パス提案 | "指定されたパスにアクセスできません。" |
| 地域設定エラー | 既存設定維持 | "地域設定の変更に失敗しました。" |

### 6.2 バリデーション設計

```python
class ValidationResult:
    """バリデーション結果"""
    def __init__(self, is_valid: bool, error_message: str = "", 
                 suggestions: List[str] = None):
        self.is_valid = is_valid
        self.error_message = error_message
        self.suggestions = suggestions or []
```

---

## 7. パフォーマンス設計

### 7.1 最適化項目

- **設定読み込み**: 起動時1回のみ、キャッシュ使用
- **ファイルアクセス**: 最小限のI/O操作
- **バリデーション**: 入力時のリアルタイム検証
- **UI更新**: 変更時のみ再描画

### 7.2 メモリ使用量

- **設定データ**: 最大1KB（JSON形式）
- **キャッシュ**: 最大10KB（一時データ）
- **UI状態**: 最大5KB（画面状態）

---

## 8. テスト設計

### 8.1 単体テスト

```python
class TestSettingsScreen:
    """設定画面単体テスト"""
    
    def test_settings_screen_initialization(self):
        """設定画面初期化テスト"""
        
    def test_setting_item_display(self):
        """設定項目表示テスト"""
        
    def test_region_setting_change(self):
        """地域設定変更テスト"""
        
    def test_audio_quality_setting(self):
        """音質設定テスト"""
        
    def test_file_path_setting(self):
        """ファイルパス設定テスト"""
        
    def test_settings_save_load(self):
        """設定保存・読み込みテスト"""
        
    def test_validation_errors(self):
        """バリデーションエラーテスト"""
        
    def test_default_reset(self):
        """デフォルト復元テスト"""
```

### 8.2 統合テスト

```python
class TestSettingsIntegration:
    """設定画面統合テスト"""
    
    def test_settings_workflow(self):
        """設定変更ワークフローテスト"""
        
    def test_region_mapper_integration(self):
        """RegionMapper統合テスト"""
        
    def test_config_manager_integration(self):
        """ConfigManager統合テスト"""
```

---

## 9. 実装計画

### 9.1 実装順序

1. **Phase 1**: 基本クラス実装
   - SettingsScreen基本構造
   - ConfigManager実装
   - SettingItem定義

2. **Phase 2**: 設定項目実装
   - 地域設定機能
   - 音質設定機能
   - ファイルパス設定機能

3. **Phase 3**: 高度な機能
   - 設定エクスポート/インポート
   - バリデーション強化
   - エラーハンドリング

4. **Phase 4**: 統合・テスト
   - 既存システムとの統合
   - 包括的テスト実装
   - パフォーマンス最適化

### 9.2 実装時間見積もり

- **Phase 1**: 2日
- **Phase 2**: 3日
- **Phase 3**: 2日
- **Phase 4**: 2日
- **合計**: 9日

---

## 10. 品質基準

### 10.1 機能品質

- **設定項目**: 100%実装
- **バリデーション**: 全項目対応
- **エラーハンドリング**: 包括的対応
- **レスポンス時間**: 設定変更<100ms

### 10.2 テスト品質

- **単体テスト**: 95%以上カバレッジ
- **統合テスト**: 全ワークフロー検証
- **エラーテスト**: 全エラーパターン検証

---

**文書バージョン**: 1.0  
**作成日**: 2025-07-15  
**作成者**: システム設計チーム  
**承認**: 開発チーム