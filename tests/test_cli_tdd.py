"""
RecRadikoCLI単体テスト（TDD手法）

TEST_REDESIGN_PLANに基づく実環境重視テスト。
コンポーネント依存性注入・設定管理・地域設定・引数解析・エラーハンドリングを実環境でテスト。
"""

import unittest
import tempfile
import shutil
import json
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock

# テスト対象
from src.cli import RecRadikoCLI
from src.auth import RadikoAuthenticator
from src.program_info import ProgramInfoManager
from src.streaming import StreamingManager
from src.error_handler import ErrorHandler
from tests.utils.test_environment import TemporaryTestEnvironment, RealEnvironmentTestBase


class TestRecRadikoCLIComponentInjection(unittest.TestCase, RealEnvironmentTestBase):
    """RecRadikoCLI コンポーネント依存性注入テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_01_コンポーネント依存性注入(self):
        """
        TDD Test: コンポーネント依存性注入
        
        外部コンポーネントが正しく注入され、初期化されることを確認
        """
        # Given: モックコンポーネント
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        mock_program_info = MagicMock(spec=ProgramInfoManager)
        mock_streaming = MagicMock(spec=StreamingManager)
        mock_error_handler = MagicMock(spec=ErrorHandler)
        
        config_file = self.temp_env.config_dir / "test_config.json"
        config_file.write_text('{"area_id": "JP13"}')
        
        # When: 依存性注入でCLI初期化
        cli = RecRadikoCLI(
            config_file=str(config_file),
            auth_manager=mock_auth,
            program_info_manager=mock_program_info,
            streaming_manager=mock_streaming,
            error_handler=mock_error_handler
        )
        
        # Then: 注入されたコンポーネントが設定される
        self.assertEqual(cli.auth_manager, mock_auth)
        self.assertEqual(cli.program_info_manager, mock_program_info)
        self.assertEqual(cli.streaming_manager, mock_streaming)
        self.assertEqual(cli.error_handler, mock_error_handler)
        
        # And: 後方互換性が保たれる
        self.assertEqual(cli.authenticator, mock_auth)
        self.assertEqual(cli.program_manager, mock_program_info)
        
        # And: 全コンポーネント注入フラグが設定される
        self.assertTrue(cli._all_components_injected)
    
    def test_02_デフォルトコンポーネント初期化(self):
        """
        TDD Test: デフォルトコンポーネント初期化
        
        依存性注入されない場合のデフォルト初期化が正常動作することを確認
        """
        # Given: 設定ファイル
        config_file = self.temp_env.config_dir / "test_config.json"
        config_file.write_text('{"area_id": "JP13"}')
        
        # _initialize_default_componentsをモック
        with patch.object(RecRadikoCLI, '_initialize_default_components') as mock_init:
            # When: デフォルト初期化でCLI初期化
            cli = RecRadikoCLI(config_file=str(config_file))
            
            # Then: デフォルト初期化メソッドが呼び出される
            mock_init.assert_called_once()
            
            # And: コンポーネントが空の状態
            self.assertIsNone(cli.auth_manager)
            self.assertIsNone(cli.program_info_manager)
            self.assertIsNone(cli.streaming_manager)
            self.assertIsNone(cli.error_handler)
            
            # And: 全コンポーネント注入フラグが無効
            self.assertFalse(cli._all_components_injected)


class TestRecRadikoCLIConfiguration(unittest.TestCase, RealEnvironmentTestBase):
    """RecRadikoCLI 設定管理テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_03_設定ファイル読み込み機能(self):
        """
        TDD Test: 設定ファイル読み込み機能
        
        設定ファイルの読み込みとデフォルト値適用が正常動作することを確認
        """
        # Given: カスタム設定ファイル
        config_file = self.temp_env.config_dir / "custom_config.json"
        custom_config = {
            "area_id": "JP27", 
            "premium_username": "test@example.com",
            "output_dir": "/custom/recordings",
            "default_format": "aac",
            "log_level": "DEBUG"
        }
        config_file.write_text(json.dumps(custom_config, ensure_ascii=False))
        
        # テンプレートファイルを作成
        template_file = self.temp_env.config_dir / "config.json.template"
        template_config = {
            "area_id": "JP13",
            "premium_username": "",
            "premium_password": "",
            "output_dir": "./recordings"
        }
        template_file.write_text(json.dumps(template_config, ensure_ascii=False))
        
        # When: CLIを初期化
        cli = RecRadikoCLI(config_file=str(config_file))
        
        # Then: カスタム設定が読み込まれる
        self.assertEqual(cli.config["area_id"], "JP27")
        self.assertEqual(cli.config["premium_username"], "test@example.com")
        self.assertEqual(cli.config["output_dir"], "/custom/recordings")
        self.assertEqual(cli.config["default_format"], "aac")
        self.assertEqual(cli.config["log_level"], "DEBUG")
        
        # And: デフォルト値が適用される（設定されていない項目）
        self.assertEqual(cli.config["default_bitrate"], 128)
        self.assertEqual(cli.config["max_concurrent_recordings"], 4)
        self.assertTrue(cli.config["auto_cleanup_enabled"])
    
    def test_04_テンプレート使用設定生成(self):
        """
        TDD Test: テンプレート使用設定生成
        
        設定ファイルが存在しない場合のテンプレート使用生成が正常動作することを確認
        """
        # Given: 存在しない設定ファイルパス
        config_file = self.temp_env.config_dir / "nonexistent_config.json"
        
        # テンプレートファイルを作成
        template_file = self.temp_env.config_dir / "config.json.template"
        template_config = {
            "area_id": "JP13",
            "prefecture": "東京",
            "premium_username": "",
            "premium_password": "",
            "output_dir": "./recordings"
        }
        template_file.write_text(json.dumps(template_config, ensure_ascii=False))
        
        # When: CLIを初期化
        cli = RecRadikoCLI(config_file=str(config_file))
        
        # Then: 設定ファイルが生成される
        self.assertTrue(config_file.exists())
        
        # And: テンプレートの内容が適用される
        self.assertEqual(cli.config["area_id"], "JP13")
        self.assertEqual(cli.config["prefecture"], "東京")
        self.assertEqual(cli.config["output_dir"], "./recordings")


class TestRecRadikoCLIPrefectureMapping(unittest.TestCase, RealEnvironmentTestBase):
    """RecRadikoCLI 都道府県名変換テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_05_都道府県名から地域ID変換(self):
        """
        TDD Test: 都道府県名から地域ID変換
        
        設定ファイルの都道府県名から地域IDへの自動変換が正常動作することを確認
        """
        # Given: 都道府県名設定
        config_file = self.temp_env.config_dir / "prefecture_config.json"
        prefecture_config = {
            "prefecture": "大阪",
            "area_id": "JP13"  # 変換前の設定
        }
        config_file.write_text(json.dumps(prefecture_config, ensure_ascii=False))
        
        # When: CLIを初期化
        cli = RecRadikoCLI(config_file=str(config_file))
        
        # Then: 都道府県名から正しい地域IDに変換される
        self.assertEqual(cli.config["area_id"], "JP27")  # 大阪 -> JP27
        self.assertEqual(cli.config["prefecture"], "大阪")
        
        # Test Case 2: 英語都道府県名
        config_file2 = self.temp_env.config_dir / "prefecture_en_config.json"
        prefecture_en_config = {
            "prefecture": "Kanagawa"
        }
        config_file2.write_text(json.dumps(prefecture_en_config, ensure_ascii=False))
        
        cli2 = RecRadikoCLI(config_file=str(config_file2))
        
        # Then: 英語名も正しく変換される
        self.assertEqual(cli2.config["area_id"], "JP14")  # Kanagawa -> JP14
        
        # Test Case 3: 不正な都道府県名
        config_file3 = self.temp_env.config_dir / "invalid_prefecture_config.json"
        invalid_config = {
            "prefecture": "存在しない県"
        }
        config_file3.write_text(json.dumps(invalid_config, ensure_ascii=False))
        
        cli3 = RecRadikoCLI(config_file=str(config_file3))
        
        # Then: デフォルト地域IDが使用される
        self.assertEqual(cli3.config["area_id"], "JP13")  # デフォルト東京
    
    def test_06_現在地域設定情報取得(self):
        """
        TDD Test: 現在地域設定情報取得
        
        設定された地域IDから地域情報が正しく取得されることを確認
        """
        # Given: 地域ID設定
        config_file = self.temp_env.config_dir / "region_config.json"
        region_config = {
            "area_id": "JP27"  # 大阪
        }
        config_file.write_text(json.dumps(region_config, ensure_ascii=False))
        
        # When: CLIを初期化し地域情報を取得
        cli = RecRadikoCLI(config_file=str(config_file))
        region_info = cli.get_current_prefecture_info()
        
        # Then: 正しい地域情報が取得される
        self.assertEqual(region_info["area_id"], "JP27")
        self.assertEqual(region_info["prefecture_ja"], "大阪府")
        self.assertEqual(region_info["prefecture_en"], "Osaka")
        self.assertEqual(region_info["region_name"], "近畿")


class TestRecRadikoCLILoggingAndValidation(unittest.TestCase, RealEnvironmentTestBase):
    """RecRadikoCLI ログ設定・検証機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_07_ログ設定管理(self):
        """
        TDD Test: ログ設定管理
        
        ログレベル・ファイル出力設定が正常動作することを確認
        """
        # Given: ログ設定
        config_file = self.temp_env.config_dir / "log_config.json"
        log_config = {
            "area_id": "JP13",
            "log_level": "DEBUG",
            "log_file": "test_recradiko.log",
            "max_log_size_mb": 50
        }
        config_file.write_text(json.dumps(log_config, ensure_ascii=False))
        
        # When: CLIを初期化
        cli = RecRadikoCLI(config_file=str(config_file))
        
        # Then: ログ設定が正しく読み込まれる
        self.assertEqual(cli.config["log_level"], "DEBUG")
        self.assertEqual(cli.config["log_file"], "test_recradiko.log")
        self.assertEqual(cli.config["max_log_size_mb"], 50)
        
        # And: ロガーが初期化される
        self.assertIsNotNone(cli.logger)
    
    def test_08_設定検証とデフォルト値適用(self):
        """
        TDD Test: 設定検証とデフォルト値適用
        
        設定値の検証とデフォルト値適用が正常動作することを確認
        """
        # Given: 不完全な設定ファイル
        config_file = self.temp_env.config_dir / "partial_config.json"
        partial_config = {
            "area_id": "JP27",
            "premium_username": "test@example.com"
            # その他の設定項目は未設定
        }
        config_file.write_text(json.dumps(partial_config, ensure_ascii=False))
        
        # When: CLIを初期化
        cli = RecRadikoCLI(config_file=str(config_file))
        
        # Then: 設定値が正しく設定される
        self.assertEqual(cli.config["area_id"], "JP27")
        self.assertEqual(cli.config["premium_username"], "test@example.com")
        
        # And: デフォルト値が適用される
        self.assertEqual(cli.config["output_dir"], "./recordings")
        self.assertEqual(cli.config["default_format"], "mp3")
        self.assertEqual(cli.config["default_bitrate"], 128)
        self.assertEqual(cli.config["max_concurrent_recordings"], 4)
        self.assertEqual(cli.config["request_timeout"], 30)
        self.assertEqual(cli.config["max_retries"], 3)
        
        # And: ブール値・数値のデフォルト値
        self.assertTrue(cli.config["auto_cleanup_enabled"])
        self.assertTrue(cli.config["notification_enabled"])
        self.assertEqual(cli.config["retention_days"], 30)
        self.assertEqual(cli.config["min_free_space_gb"], 10.0)


if __name__ == "__main__":
    unittest.main()