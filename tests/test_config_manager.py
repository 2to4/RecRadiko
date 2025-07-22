"""
ConfigManager単体テスト（TDD手法）

TEST_REDESIGN_PLANに基づく実環境重視テスト。
モック使用最小限（10%以下）、実ファイル・実暗号化処理を使用。
"""

import unittest
import tempfile
import json
from pathlib import Path
import shutil
from typing import Dict, Any

# テスト対象
from src.utils.config_utils import ConfigManager


class TestConfigManagerBasicLoading(unittest.TestCase):
    """ConfigManager基本読み込み機能テスト"""
    
    def setUp(self):
        """テスト環境セットアップ（実環境）"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        self.config_path = self.temp_path / "test_config.json"
        self.template_path = self.temp_path / "config.json.template"
    
    def tearDown(self):
        """テストクリーンアップ"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_01_json読み込み成功パターン(self):
        """
        TDD Red Phase: JSON設定ファイル読み込み成功パターン
        
        設定ファイルが存在する場合、正しく読み込めることを確認
        """
        # Given: 設定ファイルが存在する
        test_config = {
            "prefecture": "東京都",
            "log_level": "INFO",
            "audio": {
                "format": "mp3",
                "bitrate": 256
            }
        }
        self.config_path.write_text(json.dumps(test_config, ensure_ascii=False, indent=2))
        
        # When: ConfigManagerで設定を読み込む
        config_manager = ConfigManager(self.config_path)
        loaded_config = config_manager.load_config()
        
        # Then: 設定が正しく読み込まれる
        self.assertEqual(loaded_config["prefecture"], "東京都")
        self.assertEqual(loaded_config["log_level"], "INFO")
        self.assertEqual(loaded_config["audio"]["format"], "mp3")
        self.assertEqual(loaded_config["audio"]["bitrate"], 256)
    
    def test_02_テンプレート使用設定生成パターン(self):
        """
        TDD Red Phase: テンプレートから設定ファイル生成パターン
        
        設定ファイルが存在しない場合、テンプレートから生成されることを確認
        """
        # Given: テンプレートファイルが存在し、設定ファイルは存在しない
        template_config = {
            "prefecture": "東京都",
            "premium_username": "",
            "premium_password": "",
            "log_level": "INFO",
            "audio": {
                "format": "mp3",
                "bitrate": 256,
                "sample_rate": 48000
            }
        }
        self.template_path.write_text(json.dumps(template_config, ensure_ascii=False, indent=2))
        
        # Ensure config file doesn't exist
        if self.config_path.exists():
            self.config_path.unlink()
        
        # When: テンプレートパス指定でConfigManagerを使用
        config_manager = ConfigManager(self.config_path, template_path=self.template_path)
        loaded_config = config_manager.load_config()
        
        # Then: テンプレートから設定が生成される
        self.assertEqual(loaded_config["prefecture"], "東京都")
        self.assertEqual(loaded_config["audio"]["format"], "mp3")
        self.assertEqual(loaded_config["audio"]["bitrate"], 256)
        self.assertEqual(loaded_config["audio"]["sample_rate"], 48000)
        
        # And: 設定ファイルが実際に作成される
        self.assertTrue(self.config_path.exists())
        
        # And: 作成されたファイルの内容も正しい
        saved_config = json.loads(self.config_path.read_text())
        self.assertEqual(saved_config["prefecture"], "東京都")


if __name__ == "__main__":
    unittest.main()