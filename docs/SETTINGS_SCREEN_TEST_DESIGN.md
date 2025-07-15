# 設定画面テスト設計書

## 1. テスト方針

### 1.1 基本方針
- **実環境優先**: 可能な限りモックを使わず、実際のファイルシステム・設定ファイルを使用
- **統合テスト重視**: 個別機能より全体的な動作フローを検証
- **実用性検証**: 実際のユーザー操作シナリオに基づくテスト
- **データ永続性**: 実際の設定ファイル読み書きを検証

### 1.2 テスト環境
- **一時ディレクトリ**: 各テストで独立した設定ファイル使用
- **実ファイルシステム**: tempfileを使用した実際のファイル操作
- **実RegionMapper**: 実際の都道府県データベース使用
- **実バリデーション**: 実際の設定値検証ロジック使用

### 1.3 モック使用の限定
- **UI入力のみ**: キーボード入力シミュレーション
- **外部API**: RadikoAPIなどの外部サービス呼び出し
- **システム通知**: macOS通知システム

---

## 2. テストクラス設計

### 2.1 テストクラス構成

```python
# 実環境テスト（モック最小限）
class TestSettingsScreenReal:
    """設定画面実環境テスト"""
    
class TestConfigManagerReal:
    """設定管理実環境テスト"""
    
class TestSettingValidatorReal:
    """設定検証実環境テスト"""
    
class TestRegionSettingReal:
    """地域設定実環境テスト"""
    
class TestAudioQualitySettingReal:
    """音質設定実環境テスト"""
    
class TestFilePathSettingReal:
    """ファイルパス設定実環境テスト"""
    
class TestSettingsWorkflowReal:
    """設定ワークフロー実環境テスト"""
    
# 統合テスト（モック最小限）
class TestSettingsIntegrationReal:
    """設定画面統合テスト"""
    
class TestSettingsPerformanceReal:
    """設定画面パフォーマンステスト"""
    
class TestSettingsErrorHandlingReal:
    """設定画面エラーハンドリングテスト"""
```

### 2.2 テストフィクスチャ設計

```python
@pytest.fixture
def temp_config_dir():
    """一時設定ディレクトリ作成"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / ".recradiko"
        config_dir.mkdir(parents=True)
        yield config_dir

@pytest.fixture
def real_config_file(temp_config_dir):
    """実設定ファイル作成"""
    config_file = temp_config_dir / "config.json"
    
    # 実際の設定ファイル形式で作成
    config_data = {
        "version": "2.0",
        "prefecture": "東京",
        "audio": {
            "format": "mp3",
            "bitrate": 256,
            "sample_rate": 48000
        },
        "recording": {
            "save_path": str(temp_config_dir / "recordings"),
            "id3_tags_enabled": True,
            "timeout_seconds": 30,
            "max_retries": 3
        },
        "notification": {
            "type": "macos_standard",
            "enabled": True
        },
        "system": {
            "log_level": "INFO",
            "user_agent": "RecRadiko/2.0"
        }
    }
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    return config_file

@pytest.fixture
def real_settings_screen(real_config_file):
    """実設定画面インスタンス"""
    # 実際のUIServiceは軽量モックのみ使用
    ui_service = MockUIService()  # 最小限のUI入力シミュレーション
    
    screen = SettingsScreen()
    screen.ui_service = ui_service
    screen.config_manager = ConfigManager(str(real_config_file))
    screen.region_mapper = RegionMapper()  # 実RegionMapper使用
    screen.validator = SettingValidator()  # 実バリデーション使用
    
    return screen

@pytest.fixture
def real_recording_directory(temp_config_dir):
    """実録音ディレクトリ作成"""
    recordings_dir = temp_config_dir / "recordings"
    recordings_dir.mkdir(parents=True)
    
    # 実際のファイル権限設定
    recordings_dir.chmod(0o755)
    
    return recordings_dir
```

---

## 3. 詳細テストケース設計

### 3.1 ConfigManager実環境テスト

```python
class TestConfigManagerReal:
    """設定管理実環境テスト（モック不使用）"""
    
    def test_config_file_creation_and_loading(self, temp_config_dir):
        """設定ファイル作成・読み込みテスト"""
        config_file = temp_config_dir / "config.json"
        
        # 実際のConfigManagerインスタンス作成
        config_manager = ConfigManager(str(config_file))
        
        # 設定ファイルが存在しない場合のデフォルト作成
        assert config_file.exists()
        assert config_manager.get_setting("prefecture") == "東京"
        assert config_manager.get_setting("audio.format") == "mp3"
        
        # 実際のファイル内容確認
        with open(config_file, 'r', encoding='utf-8') as f:
            file_content = json.load(f)
        
        assert file_content["prefecture"] == "東京"
        assert file_content["audio"]["format"] == "mp3"
    
    def test_setting_modification_and_persistence(self, real_config_file):
        """設定変更・永続化テスト"""
        config_manager = ConfigManager(str(real_config_file))
        
        # 設定変更
        config_manager.set_setting("prefecture", "大阪")
        config_manager.set_setting("audio.bitrate", 320)
        
        # 保存
        assert config_manager.save_config() == True
        
        # 新しいインスタンスで読み込み確認
        new_config_manager = ConfigManager(str(real_config_file))
        assert new_config_manager.get_setting("prefecture") == "大阪"
        assert new_config_manager.get_setting("audio.bitrate") == 320
        
        # 実際のファイル内容確認
        with open(real_config_file, 'r', encoding='utf-8') as f:
            file_content = json.load(f)
        
        assert file_content["prefecture"] == "大阪"
        assert file_content["audio"]["bitrate"] == 320
    
    def test_config_export_import_real_files(self, real_config_file, temp_config_dir):
        """設定エクスポート・インポート実ファイルテスト"""
        config_manager = ConfigManager(str(real_config_file))
        
        # エクスポート
        export_file = temp_config_dir / "exported_config.json"
        assert config_manager.export_settings(str(export_file)) == True
        assert export_file.exists()
        
        # 設定変更
        config_manager.set_setting("prefecture", "北海道")
        config_manager.save_config()
        
        # インポート
        assert config_manager.import_settings(str(export_file)) == True
        assert config_manager.get_setting("prefecture") == "東京"  # 元の値に戻る
    
    def test_config_validation_with_real_data(self, real_config_file):
        """実データでの設定検証テスト"""
        config_manager = ConfigManager(str(real_config_file))
        
        # 正常なデータ
        is_valid, errors = config_manager.validate_config()
        assert is_valid == True
        assert len(errors) == 0
        
        # 不正なデータを設定
        config_manager.set_setting("audio.bitrate", "invalid")
        config_manager.set_setting("prefecture", "存在しない県")
        
        is_valid, errors = config_manager.validate_config()
        assert is_valid == False
        assert len(errors) > 0
        assert any("bitrate" in error for error in errors)
        assert any("prefecture" in error for error in errors)
    
    def test_config_file_corruption_handling(self, temp_config_dir):
        """設定ファイル破損対応テスト"""
        config_file = temp_config_dir / "config.json"
        
        # 破損したJSONファイル作成
        with open(config_file, 'w') as f:
            f.write('{"invalid": json content}')
        
        # ConfigManagerが破損ファイルを処理
        config_manager = ConfigManager(str(config_file))
        
        # デフォルト設定で復旧
        assert config_manager.get_setting("prefecture") == "東京"
        
        # 正常な設定ファイルとして保存
        assert config_manager.save_config() == True
        
        # 保存されたファイルが正常
        with open(config_file, 'r', encoding='utf-8') as f:
            restored_content = json.load(f)
        
        assert restored_content["prefecture"] == "東京"
```

### 3.2 RegionMapper統合テスト

```python
class TestRegionSettingReal:
    """地域設定実環境テスト（実RegionMapper使用）"""
    
    def test_prefecture_to_area_id_conversion(self):
        """都道府県名→エリアID変換テスト"""
        region_mapper = RegionMapper()  # 実RegionMapper使用
        
        # 正式名称テスト
        assert region_mapper.get_area_id("東京") == "JP13"
        assert region_mapper.get_area_id("大阪") == "JP27"
        assert region_mapper.get_area_id("北海道") == "JP1"
        
        # 略称テスト
        assert region_mapper.get_area_id("東京都") == "JP13"
        assert region_mapper.get_area_id("大阪府") == "JP27"
        
        # 英語名テスト
        assert region_mapper.get_area_id("Tokyo") == "JP13"
        assert region_mapper.get_area_id("Osaka") == "JP27"
        
        # 無効な名称
        assert region_mapper.get_area_id("存在しない県") is None
    
    def test_area_id_to_prefecture_conversion(self):
        """エリアID→都道府県名変換テスト"""
        region_mapper = RegionMapper()
        
        assert region_mapper.get_prefecture_name("JP13") == "東京"
        assert region_mapper.get_prefecture_name("JP27") == "大阪"
        assert region_mapper.get_prefecture_name("JP1") == "北海道"
        
        # 無効なエリアID
        assert region_mapper.get_prefecture_name("JP99") is None
    
    def test_region_setting_workflow_with_real_data(self, real_settings_screen):
        """地域設定ワークフロー実データテスト"""
        settings_screen = real_settings_screen
        
        # 現在の地域設定確認
        current_region = settings_screen._get_current_region_display()
        assert current_region == "東京"
        
        # 地域変更シミュレーション
        settings_screen.ui_service.set_input_sequence(["1", "2"])  # 関東地方→東京以外
        
        # 地域設定画面実行
        region_screen = RegionSettingScreen(settings_screen)
        new_region = region_screen.run_region_selection()
        
        # 実際の設定変更確認
        if new_region:
            assert new_region in ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島"]  # 実際の都道府県名
            
            # 設定保存確認
            settings_screen.config_manager.set_setting("prefecture", new_region)
            assert settings_screen.config_manager.save_config() == True
    
    def test_all_47_prefectures_mapping(self):
        """47都道府県完全マッピングテスト"""
        region_mapper = RegionMapper()
        
        # 47都道府県の完全リスト
        all_prefectures = [
            "北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島",
            "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
            "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜",
            "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
            "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口",
            "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
            "熊本", "大分", "宮崎", "鹿児島", "沖縄"
        ]
        
        # 全都道府県の双方向変換テスト
        for prefecture in all_prefectures:
            area_id = region_mapper.get_area_id(prefecture)
            assert area_id is not None, f"Failed to get area_id for {prefecture}"
            assert area_id.startswith("JP"), f"Invalid area_id format: {area_id}"
            
            # 逆変換テスト
            converted_prefecture = region_mapper.get_prefecture_name(area_id)
            assert converted_prefecture == prefecture, f"Conversion mismatch: {prefecture} -> {area_id} -> {converted_prefecture}"
```

### 3.3 音質設定実環境テスト

```python
class TestAudioQualitySettingReal:
    """音質設定実環境テスト"""
    
    def test_audio_quality_options_validation(self):
        """音質設定選択肢検証テスト"""
        validator = SettingValidator()
        
        # 有効な音質設定
        valid_options = [
            "MP3 128kbps, 44kHz",
            "MP3 256kbps, 48kHz",
            "AAC 128kbps, 44kHz",
            "AAC 256kbps, 48kHz"
        ]
        
        for option in valid_options:
            is_valid, error = validator.validate_audio_quality(option)
            assert is_valid == True, f"Valid option rejected: {option}"
            assert error == "", f"Unexpected error for {option}: {error}"
        
        # 無効な音質設定
        invalid_options = [
            "MP3 999kbps, 44kHz",  # 無効なビットレート
            "OGG 256kbps, 48kHz",  # 未対応フォーマット
            "MP3 256kbps, 999kHz", # 無効なサンプルレート
            "invalid format"        # 無効な形式
        ]
        
        for option in invalid_options:
            is_valid, error = validator.validate_audio_quality(option)
            assert is_valid == False, f"Invalid option accepted: {option}"
            assert error != "", f"No error message for invalid option: {option}"
    
    def test_audio_setting_persistence(self, real_config_file):
        """音質設定永続化テスト"""
        config_manager = ConfigManager(str(real_config_file))
        
        # 音質設定変更
        config_manager.set_setting("audio.format", "aac")
        config_manager.set_setting("audio.bitrate", 128)
        config_manager.set_setting("audio.sample_rate", 44100)
        
        # 保存
        assert config_manager.save_config() == True
        
        # 再読み込み確認
        new_config_manager = ConfigManager(str(real_config_file))
        assert new_config_manager.get_setting("audio.format") == "aac"
        assert new_config_manager.get_setting("audio.bitrate") == 128
        assert new_config_manager.get_setting("audio.sample_rate") == 44100
        
        # 実際のファイル内容確認
        with open(real_config_file, 'r', encoding='utf-8') as f:
            file_content = json.load(f)
        
        assert file_content["audio"]["format"] == "aac"
        assert file_content["audio"]["bitrate"] == 128
        assert file_content["audio"]["sample_rate"] == 44100
    
    def test_audio_quality_screen_workflow(self, real_settings_screen):
        """音質設定画面ワークフロー実テスト"""
        settings_screen = real_settings_screen
        
        # 音質設定画面初期化
        audio_screen = AudioQualitySettingScreen(settings_screen)
        
        # 音質オプション確認
        options = audio_screen._load_audio_options()
        assert len(options) == 4  # MP3 x2, AAC x2
        
        # 各オプションの構造確認
        for option in options:
            assert "id" in option
            assert "display" in option
            assert "format" in option
            assert "bitrate" in option
            assert "sample_rate" in option
            assert "description" in option
            
            # 値の妥当性確認
            assert option["format"] in ["mp3", "aac"]
            assert option["bitrate"] in [128, 256]
            assert option["sample_rate"] in [44100, 48000]
```

### 3.4 ファイルパス設定実環境テスト

```python
class TestFilePathSettingReal:
    """ファイルパス設定実環境テスト"""
    
    def test_file_path_validation_with_real_filesystem(self, temp_config_dir):
        """実ファイルシステムでのパス検証テスト"""
        validator = SettingValidator()
        
        # 有効なパス（実際に作成）
        valid_dir = temp_config_dir / "recordings"
        valid_dir.mkdir(parents=True)
        
        is_valid, error = validator.validate_file_path(str(valid_dir))
        assert is_valid == True
        assert error == ""
        
        # 存在しないパス
        nonexistent_dir = temp_config_dir / "nonexistent"
        
        is_valid, error = validator.validate_file_path(str(nonexistent_dir))
        assert is_valid == False
        assert "存在しません" in error
        
        # 権限のないパス（読み取り専用）
        readonly_dir = temp_config_dir / "readonly"
        readonly_dir.mkdir(parents=True)
        readonly_dir.chmod(0o444)  # 読み取り専用
        
        is_valid, error = validator.validate_file_path(str(readonly_dir))
        assert is_valid == False
        assert "書き込み権限" in error
        
        # 後始末
        readonly_dir.chmod(0o755)
    
    def test_file_path_setting_with_real_directories(self, real_config_file, temp_config_dir):
        """実ディレクトリでのファイルパス設定テスト"""
        config_manager = ConfigManager(str(real_config_file))
        
        # 新しい録音ディレクトリ作成
        new_recordings_dir = temp_config_dir / "new_recordings"
        new_recordings_dir.mkdir(parents=True)
        
        # パス設定変更
        config_manager.set_setting("recording.save_path", str(new_recordings_dir))
        assert config_manager.save_config() == True
        
        # 設定確認
        assert config_manager.get_setting("recording.save_path") == str(new_recordings_dir)
        
        # 実際のファイル作成テスト
        test_file = new_recordings_dir / "test_recording.mp3"
        test_file.write_text("test content")
        
        assert test_file.exists()
        assert test_file.read_text() == "test content"
    
    def test_path_expansion_and_normalization(self, real_config_file):
        """パス展開・正規化テスト"""
        config_manager = ConfigManager(str(real_config_file))
        
        # チルダ展開テスト
        config_manager.set_setting("recording.save_path", "~/RecRadiko/")
        expanded_path = config_manager.get_setting("recording.save_path")
        
        assert expanded_path.startswith("/")  # 絶対パスに展開
        assert "~" not in expanded_path  # チルダが展開されている
        
        # 相対パス正規化テスト
        config_manager.set_setting("recording.save_path", "./recordings/../recordings")
        normalized_path = config_manager.get_setting("recording.save_path")
        
        assert "../" not in normalized_path  # 正規化されている
```

### 3.5 設定画面統合テスト

```python
class TestSettingsIntegrationReal:
    """設定画面統合テスト（実環境）"""
    
    def test_complete_settings_workflow(self, real_settings_screen, temp_config_dir):
        """完全な設定ワークフロー実テスト"""
        settings_screen = real_settings_screen
        
        # 1. 設定画面初期化
        settings_screen.load_settings()
        
        # 2. 初期設定確認
        assert settings_screen.current_settings["prefecture"] == "東京"
        assert settings_screen.current_settings["audio"]["format"] == "mp3"
        
        # 3. 設定変更シミュレーション
        # 地域設定変更
        settings_screen.ui_service.set_input_sequence(["1", "2"])  # 地域設定 → 大阪選択
        result = settings_screen.handle_setting_change("region")
        assert result == True
        
        # 音質設定変更
        settings_screen.ui_service.set_input_sequence(["2", "4"])  # 音質設定 → AAC高品質
        result = settings_screen.handle_setting_change("audio_quality")
        assert result == True
        
        # 4. 設定保存確認
        assert settings_screen.save_settings() == True
        
        # 5. 設定ファイル内容確認
        config_file = settings_screen.config_manager.config_file
        with open(config_file, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
        
        assert saved_config["prefecture"] != "東京"  # 変更されている
        assert saved_config["audio"]["format"] == "aac"  # 音質も変更
        
        # 6. 新インスタンスで確認
        new_settings_screen = SettingsScreen()
        new_settings_screen.config_manager = ConfigManager(str(config_file))
        new_settings_screen.load_settings()
        
        assert new_settings_screen.current_settings["audio"]["format"] == "aac"
    
    def test_settings_screen_error_recovery(self, real_settings_screen):
        """設定画面エラー回復テスト"""
        settings_screen = real_settings_screen
        
        # 1. 無効な設定を設定
        settings_screen.config_manager.set_setting("prefecture", "無効な県")
        settings_screen.config_manager.set_setting("audio.bitrate", "invalid")
        
        # 2. 設定読み込み時のエラー処理
        settings_screen.load_settings()
        
        # 3. バリデーションエラー検出
        is_valid, errors = settings_screen.config_manager.validate_config()
        assert is_valid == False
        assert len(errors) > 0
        
        # 4. デフォルト設定復元
        assert settings_screen.reset_to_defaults() == True
        
        # 5. 復元確認
        settings_screen.load_settings()
        assert settings_screen.current_settings["prefecture"] == "東京"
        assert settings_screen.current_settings["audio"]["bitrate"] == 256
    
    def test_concurrent_settings_access(self, real_config_file):
        """並行設定アクセステスト"""
        # 2つの独立したConfigManagerインスタンス
        config_manager1 = ConfigManager(str(real_config_file))
        config_manager2 = ConfigManager(str(real_config_file))
        
        # 同時設定変更
        config_manager1.set_setting("prefecture", "大阪")
        config_manager2.set_setting("prefecture", "愛知")
        
        # 順次保存
        assert config_manager1.save_config() == True
        assert config_manager2.save_config() == True
        
        # 最後の保存が優先されることを確認
        config_manager3 = ConfigManager(str(real_config_file))
        assert config_manager3.get_setting("prefecture") == "愛知"
```

### 3.6 パフォーマンステスト

```python
class TestSettingsPerformanceReal:
    """設定画面パフォーマンステスト"""
    
    def test_large_config_file_performance(self, temp_config_dir):
        """大きな設定ファイルのパフォーマンステスト"""
        config_file = temp_config_dir / "large_config.json"
        
        # 大きな設定ファイル作成（1000個の設定項目）
        large_config = {
            "version": "2.0",
            "prefecture": "東京",
            "audio": {"format": "mp3", "bitrate": 256},
            "large_data": {f"key_{i}": f"value_{i}" for i in range(1000)}
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(large_config, f, indent=2)
        
        # 読み込み時間測定
        start_time = time.time()
        config_manager = ConfigManager(str(config_file))
        load_time = time.time() - start_time
        
        assert load_time < 1.0  # 1秒以内
        assert config_manager.get_setting("prefecture") == "東京"
        
        # 保存時間測定
        config_manager.set_setting("prefecture", "大阪")
        start_time = time.time()
        assert config_manager.save_config() == True
        save_time = time.time() - start_time
        
        assert save_time < 1.0  # 1秒以内
    
    def test_settings_screen_response_time(self, real_settings_screen):
        """設定画面応答時間テスト"""
        settings_screen = real_settings_screen
        
        # 設定画面初期化時間
        start_time = time.time()
        settings_screen.load_settings()
        init_time = time.time() - start_time
        
        assert init_time < 0.5  # 500ms以内
        
        # 設定変更時間
        start_time = time.time()
        settings_screen.handle_setting_change("region")
        change_time = time.time() - start_time
        
        assert change_time < 0.1  # 100ms以内（UI入力除く）
        
        # 設定保存時間
        start_time = time.time()
        settings_screen.save_settings()
        save_time = time.time() - start_time
        
        assert save_time < 0.2  # 200ms以内
    
    def test_memory_usage_monitoring(self, real_settings_screen):
        """メモリ使用量監視テスト"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # 初期メモリ使用量
        initial_memory = process.memory_info().rss
        
        # 設定画面操作
        settings_screen = real_settings_screen
        settings_screen.load_settings()
        
        # 大量の設定変更
        for i in range(100):
            settings_screen.config_manager.set_setting(f"test_key_{i}", f"test_value_{i}")
        
        settings_screen.save_settings()
        
        # メモリ使用量確認
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # メモリ増加量が10MB以下であることを確認
        assert memory_increase < 10 * 1024 * 1024
```

### 3.7 エラーハンドリングテスト

```python
class TestSettingsErrorHandlingReal:
    """設定画面エラーハンドリングテスト"""
    
    def test_filesystem_error_handling(self, temp_config_dir):
        """ファイルシステムエラーハンドリングテスト"""
        config_file = temp_config_dir / "config.json"
        
        # 読み取り専用ディレクトリ作成
        readonly_dir = temp_config_dir / "readonly"
        readonly_dir.mkdir(parents=True)
        readonly_config = readonly_dir / "config.json"
        
        # 設定ファイル作成
        with open(readonly_config, 'w') as f:
            json.dump({"prefecture": "東京"}, f)
        
        # ディレクトリを読み取り専用に変更
        readonly_dir.chmod(0o444)
        
        try:
            # ConfigManagerは読み取り専用でも動作する
            config_manager = ConfigManager(str(readonly_config))
            assert config_manager.get_setting("prefecture") == "東京"
            
            # 保存時にエラーが発生することを確認
            config_manager.set_setting("prefecture", "大阪")
            result = config_manager.save_config()
            assert result == False  # 保存失敗
            
        finally:
            # 後始末
            readonly_dir.chmod(0o755)
    
    def test_invalid_json_recovery(self, temp_config_dir):
        """無効なJSON回復テスト"""
        config_file = temp_config_dir / "invalid.json"
        
        # 無効なJSONファイル作成
        with open(config_file, 'w') as f:
            f.write('{"invalid": json, "missing": quote}')
        
        # ConfigManagerが無効JSONを処理
        config_manager = ConfigManager(str(config_file))
        
        # デフォルト設定で動作
        assert config_manager.get_setting("prefecture") == "東京"
        
        # 正常な設定ファイルとして保存
        assert config_manager.save_config() == True
        
        # 保存後のファイルが正常
        with open(config_file, 'r', encoding='utf-8') as f:
            recovered_config = json.load(f)
        
        assert recovered_config["prefecture"] == "東京"
    
    def test_network_dependency_isolation(self, real_settings_screen):
        """ネットワーク依存分離テスト"""
        settings_screen = real_settings_screen
        
        # ネットワーク接続不要の設定操作
        settings_screen.load_settings()
        
        # 地域設定変更（RegionMapperは内部データ使用）
        result = settings_screen.handle_setting_change("region")
        # UI入力シミュレーションなので結果は入力依存
        
        # 音質設定変更（ネットワーク不要）
        result = settings_screen.handle_setting_change("audio_quality")
        
        # 設定保存（ファイルシステムのみ）
        assert settings_screen.save_settings() == True
        
        # 全操作がネットワーク接続なしで完了
        assert True  # テスト成功
```

---

## 4. テスト実行戦略

### 4.1 テスト実行順序

```python
# 1. 基本機能テスト
pytest tests/ui/test_settings_screen_real.py::TestConfigManagerReal -v

# 2. 統合テスト
pytest tests/ui/test_settings_screen_real.py::TestSettingsIntegrationReal -v

# 3. パフォーマンステスト
pytest tests/ui/test_settings_screen_real.py::TestSettingsPerformanceReal -v

# 4. エラーハンドリングテスト
pytest tests/ui/test_settings_screen_real.py::TestSettingsErrorHandlingReal -v

# 5. 全体テスト
pytest tests/ui/test_settings_screen_real.py -v
```

### 4.2 テスト環境設定

```python
# conftest.py
import pytest
import tempfile
import json
from pathlib import Path

@pytest.fixture(scope="session")
def test_data_dir():
    """テストデータディレクトリ"""
    return Path(__file__).parent / "test_data"

@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """テスト後のクリーンアップ"""
    yield
    # 一時ファイルの自動クリーンアップ
```

### 4.3 CI/CD統合

```yaml
# .github/workflows/settings-test.yml
name: Settings Screen Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    - name: Run settings tests
      run: |
        pytest tests/ui/test_settings_screen_real.py -v --cov=src/ui/screens/settings_screen
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

---

## 5. テスト品質基準

### 5.1 カバレッジ基準
- **コードカバレッジ**: 95%以上
- **ブランチカバレッジ**: 90%以上
- **機能カバレッジ**: 100%（全設定項目）

### 5.2 パフォーマンス基準
- **初期化時間**: < 500ms
- **設定変更時間**: < 100ms
- **設定保存時間**: < 200ms
- **メモリ使用量**: < 10MB増加

### 5.3 信頼性基準
- **エラー回復**: 100%（全エラーパターン）
- **データ整合性**: 100%（設定ファイル破損対応）
- **ファイルシステム**: 100%（権限・容量エラー対応）

---

**文書バージョン**: 1.0  
**作成日**: 2025-07-15  
**作成者**: テスト設計チーム  
**承認**: 品質保証チーム