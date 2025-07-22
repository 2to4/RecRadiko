"""
認証統合テスト（TDD手法）

Phase 3: UI・統合テスト
認証フローの統合動作を実環境でテスト。モジュール間連携・エラーハンドリング・リカバリー処理を検証。
"""

import unittest
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# テスト対象
from src.auth import RadikoAuthenticator, AuthInfo, AuthenticationError
from src.region_mapper import RegionMapper
from src.utils.config_utils import ConfigManager
from tests.utils.test_environment import TemporaryTestEnvironment, RealEnvironmentTestBase


class TestAuthenticationIntegrationFlow(unittest.TestCase, RealEnvironmentTestBase):
    """認証統合フローテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
        # 設定管理初期化
        config_file = self.temp_env.config_dir / "auth_config.json"
        test_config = {
            "area_id": "JP13",
            "premium_username": "test@example.com",
            "premium_password": "test_password"
        }
        config_file.write_text(json.dumps(test_config, ensure_ascii=False))
        
        self.config_manager = ConfigManager(config_file)
        self.config = self.config_manager.load_config({})
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_01_基本認証フロー統合(self):
        """
        TDD Test: 基本認証フロー統合（シンプル版）
        
        認証の最小統合フロー: auth1→location→auth2を確認
        """
        # Given: 認証システム初期化
        auth_config_file = self.temp_env.config_dir / "auth_config.json"
        authenticator = RadikoAuthenticator(
            config_path=str(auth_config_file)
        )
        
        # モック設定: 基本認証のみに集中
        with patch('requests.Session.get') as mock_get, \
             patch.object(authenticator, 'get_location_info') as mock_location:
            
            # 基本認証レスポンス設定
            auth1_response = MagicMock()
            auth1_response.raise_for_status.return_value = None
            auth1_response.headers = {
                'X-Radiko-AuthToken': 'test_auth_token_12345',
                'X-Radiko-KeyLength': '16',
                'X-Radiko-KeyOffset': '0'
            }
            
            # 認証確認レスポンス設定  
            auth2_response = MagicMock()
            auth2_response.raise_for_status.return_value = None
            auth2_response.text = 'JP13,JP14'  # シンプルなレスポンス
            
            # モック設定
            mock_get.side_effect = [auth1_response, auth2_response]
            mock_location.return_value = None  # 位置情報は後回し
            
            # When: 基本認証実行
            auth_info = authenticator.authenticate()
            
            # Then: 認証成功
            self.assertIsNotNone(auth_info)
            self.assertEqual(auth_info.auth_token, 'test_auth_token_12345')
            self.assertEqual(auth_info.area_id, 'JP13')  # レスポンスの最初の地域ID
            
            # And: 呼び出し確認
            self.assertEqual(mock_get.call_count, 2)  # auth1 + auth2
            mock_location.assert_called_once()  # 位置情報取得呼び出し
    
    def test_02_プレミアム認証統合(self):
        """
        TDD Test: プレミアム認証統合（シンプル版）
        
        基本認証→プレミアム認証の統合フローを確認
        """
        # Given: 認証システム初期化
        auth_config_file = self.temp_env.config_dir / "auth_config.json"
        authenticator = RadikoAuthenticator(
            config_path=str(auth_config_file)
        )
        
        # モック設定: 基本認証＋プレミアム認証
        with patch('requests.Session.get') as mock_get, \
             patch('requests.Session.post') as mock_post, \
             patch.object(authenticator, 'get_location_info') as mock_location:
            
            # 基本認証レスポンス（プレミアム認証内で呼ばれる）
            auth1_response = MagicMock()
            auth1_response.raise_for_status.return_value = None
            auth1_response.headers = {
                'X-Radiko-AuthToken': 'basic_auth_token_11111',
                'X-Radiko-KeyLength': '16',
                'X-Radiko-KeyOffset': '0'
            }
            
            auth2_response = MagicMock()
            auth2_response.raise_for_status.return_value = None
            auth2_response.text = 'JP13'
            
            # プレミアム認証レスポンス
            premium_response = MagicMock()
            premium_response.raise_for_status.return_value = None
            premium_response.text = "OK"
            premium_response.json.return_value = {"status": 200, "message": "success"}
            
            # モック設定
            mock_get.side_effect = [auth1_response, auth2_response]
            mock_post.return_value = premium_response
            mock_location.return_value = None
            
            # When: プレミアム認証実行
            premium_info = authenticator.authenticate_premium(
                username="test@example.com",
                password="test_password"
            )
            
            # Then: プレミアム認証成功
            self.assertIsNotNone(premium_info)
            self.assertEqual(premium_info.auth_token, 'basic_auth_token_11111')  # 基本認証のトークンが使用される
            self.assertTrue(premium_info.premium_user)  # premium_userフラグが設定される
            
            # And: 呼び出し確認
            self.assertEqual(mock_get.call_count, 2)  # 基本認証
            self.assertEqual(mock_post.call_count, 1)  # プレミアム認証
            
            # And: プレミアム認証リクエスト内容確認
            call_args = mock_post.call_args
            self.assertIn("mail", call_args[1]["data"])
            self.assertIn("pass", call_args[1]["data"])
            self.assertEqual(call_args[1]["data"]["mail"], "test@example.com")
    
    def test_03_認証エラー回復統合(self):
        """
        TDD Test: 認証エラー回復統合（シンプル版）
        
        認証エラー→リトライ→成功の統合フローを確認
        """
        # Given: 認証システム
        auth_config_file = self.temp_env.config_dir / "auth_config.json"
        authenticator = RadikoAuthenticator(
            config_path=str(auth_config_file)
        )
        
        # 認証エラー→リトライ→成功をシミュレート
        with patch('requests.Session.get') as mock_get, \
             patch.object(authenticator, 'get_location_info') as mock_location:
            
            # 1回目: エラーレスポンス（最初のauth1で失敗）
            import requests
            error_response = MagicMock()
            error_response.raise_for_status.side_effect = requests.RequestException("認証サーバーエラー")
            
            # 2回目: リトライでauth1成功
            auth1_success = MagicMock()
            auth1_success.raise_for_status.return_value = None
            auth1_success.headers = {
                'X-Radiko-AuthToken': 'retry_auth_token_11111',
                'X-Radiko-KeyLength': '16',
                'X-Radiko-KeyOffset': '0'
            }
            
            # 3回目: auth2成功
            auth2_success = MagicMock()
            auth2_success.raise_for_status.return_value = None
            auth2_success.text = 'JP13'
            
            # モック設定: エラー→成功→成功
            mock_get.side_effect = [error_response, auth1_success, auth2_success]
            mock_location.return_value = None
            
            # When: 認証実行（内部でリトライされる）
            auth_info = authenticator.authenticate()
            
            # Then: 最終的に成功
            self.assertIsNotNone(auth_info)
            self.assertEqual(auth_info.auth_token, 'retry_auth_token_11111')
            self.assertEqual(auth_info.area_id, 'JP13')
            
            # And: リトライ動作確認
            self.assertEqual(mock_get.call_count, 3)  # エラー1回 + 成功2回（auth1+auth2）


class TestAuthenticationCacheIntegration(unittest.TestCase, RealEnvironmentTestBase):
    """認証キャッシュ統合テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_04_認証情報統合管理(self):
        """
        TDD Test: 認証情報統合管理（シンプル版）
        
        認証システムの基本統合フロー（認証→保存→再利用）を確認
        """
        # Given: 認証システムと設定
        auth_config_file = self.temp_env.config_dir / "auth_integration_config.json"
        authenticator = RadikoAuthenticator(config_path=str(auth_config_file))
        
        # 認証をモック（実環境でのAuthInfo統合をテスト）
        with patch('requests.Session.get') as mock_get, \
             patch.object(authenticator, 'get_location_info') as mock_location:
            
            # 認証レスポンス設定
            auth1_response = MagicMock()
            auth1_response.raise_for_status.return_value = None
            auth1_response.headers = {
                'X-Radiko-AuthToken': 'integration_token_99999',
                'X-Radiko-KeyLength': '16',
                'X-Radiko-KeyOffset': '0'
            }
            
            auth2_response = MagicMock()
            auth2_response.raise_for_status.return_value = None
            auth2_response.text = 'JP13'
            
            mock_get.side_effect = [auth1_response, auth2_response]
            mock_location.return_value = None
            
            # When: 認証実行
            auth_info = authenticator.authenticate()
            
            # Then: AuthInfoが正しく生成・保存される
            self.assertIsNotNone(auth_info)
            self.assertEqual(auth_info.auth_token, 'integration_token_99999')
            self.assertEqual(auth_info.area_id, 'JP13')
            self.assertFalse(auth_info.premium_user)
            
            # And: 認証システム内部に保存される
            self.assertEqual(authenticator.auth_info, auth_info)
            self.assertIsNotNone(authenticator.session.headers.get('X-Radiko-AuthToken'))
            
            # And: 有効期限管理
            self.assertFalse(auth_info.is_expired())
            self.assertIsInstance(auth_info.expires_at, float)
            
            # When: 同じインスタンスで再認証チェック
            # 既に認証済みの場合の動作確認
            cached_info = authenticator.auth_info
            
            # Then: 既存の認証情報が保持される
            self.assertEqual(cached_info.auth_token, 'integration_token_99999')
    
    def test_05_地域設定統合ワークフロー(self):
        """
        TDD Test: 地域設定統合ワークフロー（シンプル版）
        
        RegionMapperと認証システムの統合確認
        """
        # Given: 認証システム
        auth_config_file = self.temp_env.config_dir / "region_auth_config.json"
        authenticator = RadikoAuthenticator(config_path=str(auth_config_file))
        
        # RegionMapper統合テスト
        region_mapper = RegionMapper()
        
        # Test Case 1: 地域情報取得統合
        tokyo_info = region_mapper.get_region_info("JP13")
        self.assertIsNotNone(tokyo_info)
        self.assertEqual(tokyo_info.prefecture_ja, "東京都")
        self.assertEqual(tokyo_info.prefecture_en, "Tokyo")
        self.assertEqual(tokyo_info.region_name, "関東")
        
        osaka_info = region_mapper.get_region_info("JP27")
        self.assertIsNotNone(osaka_info)
        self.assertEqual(osaka_info.prefecture_ja, "大阪府")
        self.assertEqual(osaka_info.prefecture_en, "Osaka")
        self.assertEqual(osaka_info.region_name, "近畿")
        
        # Test Case 2: 都道府県名→地域ID変換統合
        tokyo_area_id = region_mapper.get_area_id("東京")
        self.assertEqual(tokyo_area_id, "JP13")
        
        osaka_area_id = region_mapper.get_area_id("大阪")
        self.assertEqual(osaka_area_id, "JP27")
        
        kanagawa_area_id = region_mapper.get_area_id("Kanagawa")  # 英語名
        self.assertEqual(kanagawa_area_id, "JP14")
        
        # Test Case 3: 認証と地域設定の統合
        with patch('requests.Session.get') as mock_get, \
             patch.object(authenticator, 'get_location_info') as mock_location:
            
            # 東京での認証レスポンス
            auth1_response = MagicMock()
            auth1_response.raise_for_status.return_value = None
            auth1_response.headers = {
                'X-Radiko-AuthToken': 'region_test_token_13',
                'X-Radiko-KeyLength': '16',
                'X-Radiko-KeyOffset': '0'
            }
            
            auth2_response = MagicMock()
            auth2_response.raise_for_status.return_value = None
            auth2_response.text = 'JP13'  # 東京地域
            
            mock_get.side_effect = [auth1_response, auth2_response]
            mock_location.return_value = None
            
            # When: 認証実行
            auth_info = authenticator.authenticate()
            
            # Then: 認証情報に地域IDが設定される
            self.assertIsNotNone(auth_info)
            self.assertEqual(auth_info.area_id, 'JP13')
            
            # And: 地域情報との整合性確認
            region_info = region_mapper.get_region_info(auth_info.area_id)
            self.assertEqual(region_info.prefecture_ja, "東京都")
            
        # Test Case 4: エラーケース処理
        invalid_area_id = region_mapper.get_area_id("存在しない県")
        self.assertIsNone(invalid_area_id)
        
        invalid_info = region_mapper.get_region_info("JP99")
        self.assertIsNone(invalid_info)


if __name__ == "__main__":
    unittest.main()