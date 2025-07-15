# テストリファクタリング詳細分析

## 📊 **現在のモック使用状況（詳細分析）**

### 高優先度変換対象ファイル

#### 1. **test_auth.py** (モック使用: 117個)
**主なモックパターン:**
- `@patch('requests.Session.get')` - 外部API呼び出し
- `@patch('requests.Session.post')` - 認証リクエスト
- `@patch('pathlib.Path.exists')` - ファイル存在確認
- `@patch('time.sleep')` - 時間待機
- `@patch.object(RadikoAuthenticator, 'get_location_info')` - 位置情報取得

**実環境化可能な箇所:**
- ✅ **ファイル操作**: tempfile使用で実際のファイル操作
- ✅ **設定管理**: 実際のJSON設定ファイル
- ✅ **暗号化処理**: 実際の暗号化・復号化
- ✅ **認証情報保存**: 実際のファイル保存・読み込み
- ❌ **外部API**: requests mockingは必要（実際のRadiko API変動）
- ❌ **時間待機**: テスト実行時間短縮のためmock必要

#### 2. **test_timefree_recorder.py** (モック使用: 108個)
**主なモックパターン:**
- `@patch('aiohttp.ClientSession')` - 非同期HTTP通信
- `Mock(spec=RadikoAuthenticator)` - 認証器
- `AsyncMock(return_value=content)` - 非同期レスポンス
- `@patch('subprocess.run')` - FFmpeg実行
- `@patch('pathlib.Path.exists')` - ファイル存在確認

**実環境化可能な箇所:**
- ✅ **ファイル操作**: 実際のファイル作成・削除
- ✅ **並行処理**: 実際の非同期処理
- ✅ **プレイリスト解析**: 実際のM3U8パース
- ✅ **メタデータ処理**: 実際のID3タグ処理
- ❌ **HTTP通信**: aiohttp mockingは必要（外部API）
- ❌ **FFmpeg実行**: subprocess mockingは必要（システム依存）

#### 3. **test_cli_interactive.py** (モック使用: 84個)
**主なモックパターン:**
- `@patch('sys.stdout', new_callable=io.StringIO)` - 標準出力
- `@patch('builtins.input')` - ユーザー入力
- `Mock()` - 削除されたクラス代替
- `@patch.object(RecRadikoCLI, 'method')` - CLIメソッド

**実環境化可能な箇所:**
- ✅ **設定読み込み**: 実際の設定ファイル
- ✅ **コマンド解析**: 実際のargparse処理
- ✅ **ファイル操作**: 実際のファイル管理
- ❌ **ユーザー入力**: 自動テスト実行のためmock必要
- ❌ **標準出力**: テスト検証のためmock必要

### 中優先度変換対象ファイル

#### 4. **test_streaming.py** (モック使用: 76個)
**主なモックパターン:**
- `@patch('requests.get')` - HTTP GET
- `@patch('m3u8.load')` - M3U8ライブラリ
- `@patch('pathlib.Path.write_bytes')` - ファイル書き込み

**実環境化可能な箇所:**
- ✅ **M3U8処理**: 実際のm3u8ライブラリ使用
- ✅ **ファイル処理**: 実際のファイル操作
- ❌ **HTTP通信**: 外部API通信のためmock必要

#### 5. **test_program_info.py** (モック使用: 69個)
**主なモックパターン:**
- `@patch('requests.get')` - XMLデータ取得
- `@patch('xml.etree.ElementTree.parse')` - XML解析
- `@patch('pathlib.Path.exists')` - ファイル存在確認

**実環境化可能な箇所:**
- ✅ **XML処理**: 実際のXML解析
- ✅ **データ構造**: 実際のデータクラス
- ✅ **ファイル操作**: 実際のファイル処理
- ❌ **HTTP通信**: 外部API通信のためmock必要

## 🔄 **実環境テスト変換戦略**

### Phase 1: 共通テストユーティリティ実装

#### **TemporaryTestEnvironment**
```python
class TemporaryTestEnvironment:
    """統合テスト用実環境管理"""
    
    def __init__(self):
        self.temp_dir = None
        self.config_dir = None
        self.recordings_dir = None
        self.logs_dir = None
        self.auth_file = None
        self.config_file = None
        
    def __enter__(self):
        # 一時ディレクトリ構築
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / ".recradiko"
        self.recordings_dir = self.config_dir / "recordings"
        self.logs_dir = self.config_dir / "logs"
        
        # ディレクトリ作成
        self.config_dir.mkdir(parents=True)
        self.recordings_dir.mkdir(parents=True)
        self.logs_dir.mkdir(parents=True)
        
        # デフォルト設定ファイル作成
        self.config_file = self.config_dir / "config.json"
        default_config = {
            "version": "2.0",
            "prefecture": "東京",
            "area_id": "JP13",
            "audio": {"format": "mp3", "bitrate": 256},
            "recording": {"save_path": str(self.recordings_dir)}
        }
        self.config_file.write_text(json.dumps(default_config))
        
        # 認証ファイル作成
        self.auth_file = self.config_dir / "auth_token"
        self.auth_file.write_text("test_auth_token")
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
    
    def create_sample_recording(self, name: str, size: int = 1024) -> Path:
        """サンプル録音ファイル作成"""
        file_path = self.recordings_dir / f"{name}.mp3"
        file_path.write_bytes(b"fake mp3 data" * (size // 13))
        return file_path
    
    def create_sample_playlist(self, station_id: str, segments: int = 5) -> Path:
        """サンプルプレイリストファイル作成"""
        playlist_content = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:5\n"
        for i in range(segments):
            playlist_content += f"#EXTINF:5.0,\n{station_id}_segment_{i}.ts\n"
        playlist_content += "#EXT-X-ENDLIST\n"
        
        playlist_file = self.config_dir / f"{station_id}_playlist.m3u8"
        playlist_file.write_text(playlist_content)
        return playlist_file
```

#### **RealAuthenticatorTest**
```python
class RealAuthenticatorTest:
    """実環境認証テスト"""
    
    def setup_real_authenticator(self, temp_env: TemporaryTestEnvironment):
        """実環境認証器セットアップ"""
        return RadikoAuthenticator(config_path=str(temp_env.config_file))
    
    def test_real_config_operations(self, temp_env: TemporaryTestEnvironment):
        """実際の設定操作テスト"""
        auth = self.setup_real_authenticator(temp_env)
        
        # 実際の設定保存
        auth._save_config("test_user", "test_password")
        
        # 実際の設定読み込み
        config = auth._load_config()
        assert config["username"] == "test_user"
        assert config["password"] == "test_password"
        
        # 実際のファイル存在確認
        assert temp_env.config_file.exists()
```

### Phase 2: 高優先度ファイル変換

#### **test_auth.py → test_authentication_integration.py**
```python
class TestAuthenticationIntegration:
    """認証システム統合テスト"""
    
    def test_real_authentication_flow(self, temp_env):
        """実際の認証フローテスト"""
        auth = RadikoAuthenticator(config_path=str(temp_env.config_file))
        
        # 実際のファイル操作
        auth._save_config("test_user", "test_password")
        config = auth._load_config()
        
        # 実際の暗号化処理
        encrypted = auth._encrypt_data("test_data")
        decrypted = auth._decrypt_data(encrypted)
        assert decrypted == "test_data"
        
        # 外部APIのみモック
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.headers = {"X-Radiko-AuthToken": "token"}
            
            # 実際の認証処理
            auth_info = auth.authenticate()
            assert auth_info.auth_token == "token"
```

#### **test_timefree_recorder.py → test_recording_system.py**
```python
class TestRecordingSystem:
    """録音システム統合テスト"""
    
    def test_real_recording_workflow(self, temp_env):
        """実際の録音ワークフローテスト"""
        # 実際のファイル操作
        authenticator = RadikoAuthenticator(str(temp_env.config_file))
        recorder = TimeFreeRecorder(authenticator)
        
        # 実際のプレイリスト解析
        playlist_file = temp_env.create_sample_playlist("TBS", 5)
        
        # 実際の非同期処理
        async def test_async_operations():
            # 外部HTTPのみモック
            with patch('aiohttp.ClientSession') as mock_session:
                mock_session.return_value.__aenter__.return_value.get.return_value.status = 200
                mock_session.return_value.__aenter__.return_value.get.return_value.text.return_value = playlist_file.read_text()
                
                # 実際の処理実行
                result = await recorder.record_program(
                    station_id="TBS",
                    start_time=datetime.now(),
                    duration=3600,
                    output_path=str(temp_env.recordings_dir / "test.mp3")
                )
                
                assert result.success
                assert Path(result.output_path).exists()
        
        asyncio.run(test_async_operations())
```

### Phase 3: 統合テストファイル

#### **test_system_integration.py**
```python
class TestSystemIntegration:
    """システム統合テスト"""
    
    def test_end_to_end_workflow(self, temp_env):
        """エンドツーエンドワークフローテスト"""
        # 実際のCLI初期化
        cli = RecRadikoCLI(config_file=str(temp_env.config_file))
        
        # 実際のコンポーネント統合
        assert cli.auth_manager is not None
        assert cli.program_info_manager is not None
        
        # 実際の設定読み込み
        config = cli._load_config()
        assert config["prefecture"] == "東京"
        
        # 実際のファイル操作
        recording_file = temp_env.create_sample_recording("test_recording")
        assert recording_file.exists()
        assert recording_file.stat().st_size > 0
```

## 📈 **期待される効果**

### **モック削減効果**
- **test_auth.py**: 117個 → 25個 (78%削減)
- **test_timefree_recorder.py**: 108個 → 30個 (72%削減)
- **test_cli_interactive.py**: 84個 → 20個 (76%削減)
- **全体**: 1,738個 → 174個 (90%削減)

### **品質向上効果**
- **実際の動作検証**: ファイル操作、設定管理、暗号化処理
- **統合テスト強化**: コンポーネント間の実際の連携
- **回帰テスト向上**: 実際の変更影響検出
- **保守性向上**: シンプルなテスト構造

### **開発効率向上**
- **テスト作成**: 40%高速化（モック設定不要）
- **デバッグ時間**: 50%短縮（実際の動作確認）
- **新機能開発**: 30%高速化（実環境テストパターン）

## 🎯 **次のステップ**

1. **共通テストユーティリティ実装** (1日)
2. **test_auth.py変換** (1日)
3. **test_timefree_recorder.py変換** (1日)
4. **test_cli_interactive.py変換** (1日)
5. **統合テストファイル作成** (1日)
6. **全体テスト実行・検証** (1日)
7. **ドキュメント更新** (1日)

**合計期間**: 7日間
**成功条件**: 全テスト成功・モック使用率10%以下・実行時間120%以内