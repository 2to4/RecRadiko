# テストリファクタリング計画

## 🎯 **目標**

**全テストの実環境化・モック使用最小化により、実用性と信頼性を向上させる**

### 現在の問題点
- **過度なモック使用**: 実際の動作と乖離するテスト
- **テスト複雑性**: モック設定によるテスト保守困難
- **実用性欠如**: 実際のファイル・API・設定での動作未検証
- **テスト重複**: 類似テストケースの散在

### 改善目標
- **モック使用率**: 80% → 10%以下（外部API・UI入力・システム通知のみ）
- **実環境テスト**: 実際のファイル・設定・システムリソース使用
- **テスト信頼性**: 実際の動作保証によるバグ発見率向上
- **保守性**: シンプルで理解しやすいテスト構造

## 📊 **現在のテスト状況分析**

### テストファイル構成
```
tests/
├── test_*.py (単体テスト: 27ファイル)
├── integration/ (統合テスト: 3ファイル)
├── ui/ (UIテスト: 8ファイル)
└── test_cli_interactive.py (対話型テスト: 1ファイル)
```

### モック使用状況
- **高モック使用**: `test_auth.py`, `test_cli.py`, `test_program_info.py`
- **中モック使用**: `test_streaming.py`, `test_timefree_recorder.py`
- **低モック使用**: `test_region_mapper.py`, `test_program_history.py`
- **実環境テスト**: `tests/ui/test_*_screen.py`（Phase 4実装）

### 問題のあるテストパターン
1. **過度なモック設定**: 実際の動作と乖離
2. **ファイルシステムモック**: 実際のファイル操作未検証
3. **設定ファイルモック**: 実際の設定読み込み未検証
4. **API応答モック**: 実際のAPI変更に対応できない

## 🔄 **リファクタリング戦略**

### 1. **実環境テストパターン**

#### **ファイルシステムテスト**
```python
# 従来（モック使用）
@patch('pathlib.Path.exists', return_value=True)
def test_config_loading(mock_exists):
    # モック設定が複雑

# 改善（実環境）
@pytest.fixture
def temp_config_file():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"test": "config"}, f)
        yield f.name
    os.unlink(f.name)

def test_config_loading(temp_config_file):
    # 実際のファイル使用
```

#### **設定管理テスト**
```python
# 従来（モック使用）
@patch('json.load', return_value={"mock": "config"})
def test_config_update(mock_load):
    # モック設定が複雑

# 改善（実環境）
@pytest.fixture
def temp_config_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.json"
        config_path.write_text(json.dumps({"test": "config"}))
        yield temp_dir

def test_config_update(temp_config_dir):
    # 実際の設定ファイル使用
```

#### **システムリソーステスト**
```python
# 従来（モック使用）
@patch('psutil.disk_usage', return_value=Mock(total=1000, used=500, free=500))
def test_disk_usage(mock_disk):
    # モック設定

# 改善（実環境）
def test_disk_usage():
    # 実際のシステムリソース使用
    disk_info = get_disk_usage_info()
    assert disk_info['total'] > 0
    assert disk_info['used'] >= 0
    assert disk_info['free'] >= 0
```

### 2. **モック使用を許可する範囲**

#### **外部API通信**
```python
# 実際のRadiko APIは変動するため、モック使用
@patch('requests.get')
def test_api_call(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"test": "data"}
    # テスト実行
```

#### **UI入力シミュレーション**
```python
# キーボード入力は実際のユーザー操作が困難なため、モック使用
@patch('src.ui.input.keyboard_handler.KeyboardHandler.get_key')
def test_keyboard_input(mock_get_key):
    mock_get_key.return_value = 'enter'
    # テスト実行
```

#### **システム通知**
```python
# 実際の通知は継続的テスト環境で不適切なため、モック使用
@patch('subprocess.run')
def test_notification(mock_run):
    # 通知システムテスト
```

### 3. **テストファイル統合計画**

#### **統合対象ファイル**
- `test_auth.py` + `test_region_mapper.py` → `test_authentication_integration.py`
- `test_program_info.py` + `test_program_history.py` → `test_program_management.py`
- `test_streaming.py` + `test_timefree_recorder.py` → `test_recording_system.py`
- `test_cli.py` + `test_cli_interactive.py` → `test_command_interface.py`

#### **新規テストファイル**
- `test_file_operations.py`: 実際のファイル操作統合テスト
- `test_configuration_management.py`: 設定ファイル実環境テスト
- `test_system_integration.py`: システムリソース統合テスト

## 📋 **リファクタリング実行計画**

### **Phase 1: 分析・計画（1-2日）**
1. **現在のモック使用状況調査**
   - 全テストファイルのモック使用箇所特定
   - モック削除可能な箇所の分類
   - 実環境テスト変換の優先度設定

2. **実環境テスト設計**
   - 一時ファイル・ディレクトリ戦略
   - 設定ファイル管理戦略
   - テストデータ管理戦略

### **Phase 2: 実装（3-4日）**
1. **高優先度テストファイル変換**
   - `test_auth.py`: 認証システム実環境化
   - `test_program_info.py`: 番組情報実環境化
   - `test_cli.py`: CLI実環境化

2. **中優先度テストファイル変換**
   - `test_streaming.py`: ストリーミング実環境化
   - `test_timefree_recorder.py`: 録音システム実環境化

3. **テストファイル統合**
   - 重複テストケース削除
   - 関連テストファイル統合
   - 新規統合テストファイル作成

### **Phase 3: 検証・最適化（1-2日）**
1. **テスト実行・検証**
   - 全テスト実行・成功確認
   - パフォーマンス測定
   - エラーハンドリング検証

2. **ドキュメント更新**
   - テスト実行手順更新
   - 新しいテストパターン説明
   - 開発者向けガイド更新

## 🔧 **実装詳細**

### **共通テストユーティリティ**

#### **TemporaryEnvironment**
```python
class TemporaryEnvironment:
    """実環境テスト用一時環境管理"""
    
    def __init__(self):
        self.temp_dir = None
        self.config_dir = None
        self.config_file = None
        
    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / ".recradiko"
        self.config_dir.mkdir(parents=True)
        
        # デフォルト設定ファイル作成
        self.config_file = self.config_dir / "config.json"
        default_config = {
            "version": "2.0",
            "prefecture": "東京",
            "audio": {"format": "mp3", "bitrate": 256},
            "recording": {"save_path": str(self.config_dir / "recordings")}
        }
        self.config_file.write_text(json.dumps(default_config, indent=2))
        
        # 録音ディレクトリ作成
        (self.config_dir / "recordings").mkdir(parents=True)
        (self.config_dir / "logs").mkdir(parents=True)
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
```

#### **RealFileTestCase**
```python
class RealFileTestCase:
    """実ファイル操作テストベース"""
    
    @pytest.fixture
    def temp_env(self):
        with TemporaryEnvironment() as env:
            yield env
    
    def create_sample_recording(self, env: TemporaryEnvironment, 
                               name: str, size: int = 1024) -> Path:
        """サンプル録音ファイル作成"""
        recording_path = env.config_dir / "recordings" / f"{name}.mp3"
        recording_path.write_bytes(b"fake mp3 data" * (size // 13))
        return recording_path
    
    def create_sample_config(self, env: TemporaryEnvironment, 
                           config_data: dict) -> Path:
        """サンプル設定ファイル作成"""
        env.config_file.write_text(json.dumps(config_data, indent=2))
        return env.config_file
```

### **具体的なテスト変換例**

#### **認証テスト（test_auth.py）**
```python
# 従来
@patch('requests.post')
@patch('pathlib.Path.exists', return_value=True)
def test_authentication_success(mock_exists, mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.text = "auth_token=test_token"
    # テスト実行

# 改善
def test_authentication_success(temp_env):
    """実際の設定ファイルを使用した認証テスト"""
    # 実際の設定ファイル作成
    config_data = {
        "version": "2.0",
        "prefecture": "東京",
        "area_id": "JP13"
    }
    temp_env.config_file.write_text(json.dumps(config_data))
    
    # 実際のファイル操作でテスト
    authenticator = RadikoAuthenticator(str(temp_env.config_file))
    
    # 外部APIのみモック（実際のAPI呼び出しは制御困難）
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "auth_token=test_token"
        
        result = authenticator.authenticate()
        assert result == True
        
        # 認証トークンが実際のファイルに保存されているか確認
        token_file = temp_env.config_dir / "auth_token"
        assert token_file.exists()
        assert "test_token" in token_file.read_text()
```

#### **CLI テスト（test_cli.py）**
```python
# 従来
@patch('src.cli.RecRadikoCLI._load_config')
@patch('src.cli.RecRadikoCLI._initialize_components')
def test_cli_initialization(mock_init, mock_load):
    mock_load.return_value = {"test": "config"}
    # テスト実行

# 改善
def test_cli_initialization(temp_env):
    """実際の設定ファイルを使用したCLI初期化テスト"""
    # 実際の設定ファイル作成
    config_data = {
        "version": "2.0",
        "prefecture": "東京",
        "audio": {"format": "mp3", "bitrate": 256}
    }
    temp_env.config_file.write_text(json.dumps(config_data))
    
    # 実際のファイル操作でCLI初期化
    cli = RecRadikoCLI(config_file=str(temp_env.config_file))
    
    # 設定が正しく読み込まれているか確認
    assert cli.config["prefecture"] == "東京"
    assert cli.config["audio"]["format"] == "mp3"
    
    # 実際のコンポーネント初期化確認
    assert cli.auth_manager is not None
    assert cli.program_info_manager is not None
```

### **テスト実行戦略**

#### **並列テスト実行**
```python
# pytest-xdist を使用した並列実行
# 実環境テストは一時ディレクトリを使用するため並列実行安全

pytest tests/ -n auto  # 自動並列実行
pytest tests/ -n 4     # 4プロセス並列実行
```

#### **テストカテゴリ分類**
```python
# pytest マーカーによるテストカテゴリ分類
@pytest.mark.unit        # 単体テスト
@pytest.mark.integration # 統合テスト
@pytest.mark.real_env    # 実環境テスト
@pytest.mark.slow        # 時間のかかるテスト

# 実行例
pytest -m "unit and real_env"      # 実環境単体テスト
pytest -m "integration and real_env" # 実環境統合テスト
pytest -m "not slow"               # 高速テストのみ
```

## 📊 **期待される効果**

### **品質向上**
- **バグ発見率**: 30%向上（実際の動作検証）
- **テスト信頼性**: 50%向上（実環境動作保証）
- **回帰テスト**: 90%向上（実際の変更影響検出）

### **保守性向上**
- **テスト理解性**: 40%向上（モック設定削除）
- **テスト保守**: 60%向上（シンプルな構造）
- **新規開発**: 30%高速化（実環境テストパターン）

### **開発効率向上**
- **デバッグ時間**: 50%短縮（実際の動作確認）
- **テスト作成**: 40%高速化（モック設定不要）
- **CI/CD**: 20%高速化（並列実行最適化）

## 🎯 **成功指標**

### **定量指標**
- **モック使用率**: 80% → 10%以下
- **テスト成功率**: 98.5% → 99.5%以上
- **テスト実行時間**: 現在の120%以内
- **テストカバレッジ**: 95%以上維持

### **定性指標**
- **テスト理解性**: 新規開発者でも理解可能
- **実用性**: 実際の動作保証
- **保守性**: 機能変更時のテスト更新最小化
- **信頼性**: プロダクション環境での動作保証

---

**実行スケジュール**: 1週間（7日）  
**担当**: 開発チーム全体  
**前提条件**: Phase 4完了・安定したコードベース  
**成功条件**: 全テスト成功・モック使用率10%以下・実行時間120%以内