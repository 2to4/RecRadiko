"""
RadikoAuthenticator単体テスト（TDD手法）

TEST_REDESIGN_PLANに基づく実環境重視テスト。
認証・暗号化・ファイル操作・エラーハンドリングを実環境でテスト。
"""

import unittest
import time
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# テスト対象
from src.auth import RadikoAuthenticator, AuthInfo, LocationInfo, AuthenticationError
from tests.utils.test_environment import TemporaryTestEnvironment, RealEnvironmentTestBase


class TestRadikoAuthenticatorBasicAuth(unittest.TestCase, RealEnvironmentTestBase):
    """RadikoAuthenticator基本認証機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    @patch('requests.Session.get')
    def test_01_基本認証成功パターン(self, mock_get):
        """
        TDD Test: 基本認証成功パターン
        
        正常な基本認証フローが完了することを確認
        """
        # Given: 正常な認証レスポンスを設定
        auth1_response = MagicMock()
        auth1_response.raise_for_status.return_value = None
        auth1_response.headers = {
            'X-Radiko-AuthToken': 'test_auth_token_12345',
            'X-Radiko-KeyLength': '16',
            'X-Radiko-KeyOffset': '0'
        }
        
        auth2_response = MagicMock()
        auth2_response.raise_for_status.return_value = None
        auth2_response.text = 'JP13,TBS,QRR,LFR,RN1,RN2'
        
        mock_get.side_effect = [auth1_response, auth2_response]
        
        # When: 認証器で基本認証を実行
        config_path = self.temp_env.config_dir / "auth_config.json"
        authenticator = RadikoAuthenticator(config_path=str(config_path))
        
        # 位置情報を事前設定（外部API呼び出し回避）
        authenticator.location_info = LocationInfo(
            ip_address="test_ip",
            area_id="JP13",
            region="Tokyo",
            country="Japan"
        )
        
        auth_info = authenticator.authenticate()
        
        # Then: 認証情報が正しく設定される
        self.assertIsInstance(auth_info, AuthInfo)
        self.assertEqual(auth_info.auth_token, 'test_auth_token_12345')
        self.assertEqual(auth_info.area_id, 'JP13')
        self.assertFalse(auth_info.premium_user)
        self.assertFalse(auth_info.is_expired())
        
        # And: セッションに認証トークンが設定される
        self.assertEqual(authenticator.session.headers['X-Radiko-AuthToken'], 'test_auth_token_12345')
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_02_プレミアム認証成功パターン(self, mock_get, mock_post):
        """
        TDD Test: プレミアム認証成功パターン
        
        基本認証後のプレミアム認証が正常完了することを確認
        """
        # Given: 基本認証とプレミアム認証の正常レスポンス
        auth1_response = MagicMock()
        auth1_response.raise_for_status.return_value = None
        auth1_response.headers = {
            'X-Radiko-AuthToken': 'test_auth_token_premium',
            'X-Radiko-KeyLength': '16',
            'X-Radiko-KeyOffset': '0'
        }
        
        auth2_response = MagicMock()
        auth2_response.raise_for_status.return_value = None
        auth2_response.text = 'JP13,TBS,QRR,LFR,RN1,RN2'
        
        premium_response = MagicMock()
        premium_response.raise_for_status.return_value = None
        premium_response.json.return_value = {'status': 200, 'message': 'success'}
        
        mock_get.side_effect = [auth1_response, auth2_response]
        mock_post.return_value = premium_response
        
        # When: プレミアム認証を実行
        config_path = self.temp_env.config_dir / "auth_config.json"
        authenticator = RadikoAuthenticator(config_path=str(config_path))
        
        # 位置情報を事前設定
        authenticator.location_info = LocationInfo(
            ip_address="test_ip",
            area_id="JP13", 
            region="Tokyo",
            country="Japan"
        )
        
        auth_info = authenticator.authenticate_premium("test@example.com", "testpass")
        
        # Then: プレミアム認証情報が正しく設定される
        self.assertIsInstance(auth_info, AuthInfo)
        self.assertEqual(auth_info.auth_token, 'test_auth_token_premium')
        self.assertEqual(auth_info.area_id, 'JP13')
        self.assertTrue(auth_info.premium_user)
        self.assertFalse(auth_info.is_expired())
        
        # And: 認証情報が暗号化保存される
        self.assertTrue(config_path.exists())
        with open(config_path, 'r') as f:
            saved_config = json.load(f)
        self.assertIn('username', saved_config)
        self.assertIn('password', saved_config)
        self.assertIn('saved_at', saved_config)
    
    @patch('requests.Session.get')
    def test_03_タイムフリー認証成功パターン(self, mock_get):
        """
        TDD Test: タイムフリー認証成功パターン
        
        基本認証後のタイムフリー認証が正常完了することを確認
        """
        # Given: 基本認証の正常レスポンス
        auth1_response = MagicMock()
        auth1_response.raise_for_status.return_value = None
        auth1_response.headers = {
            'X-Radiko-AuthToken': 'test_timefree_token',
            'X-Radiko-KeyLength': '16',
            'X-Radiko-KeyOffset': '0'
        }
        
        auth2_response = MagicMock()
        auth2_response.raise_for_status.return_value = None
        auth2_response.text = 'JP13,TBS,QRR,LFR'
        
        mock_get.side_effect = [auth1_response, auth2_response]
        
        # When: タイムフリー認証を実行
        config_path = self.temp_env.config_dir / "auth_config.json"
        authenticator = RadikoAuthenticator(config_path=str(config_path))
        
        # 位置情報を事前設定
        authenticator.location_info = LocationInfo(
            ip_address="test_ip",
            area_id="JP13",
            region="Tokyo", 
            country="Japan"
        )
        
        # 基本認証を先に実行
        authenticator.authenticate()
        
        # タイムフリー認証実行
        timefree_session = authenticator.authenticate_timefree()
        
        # Then: タイムフリーセッションが正しく設定される
        self.assertEqual(timefree_session, 'test_timefree_token')
        self.assertEqual(authenticator.auth_info.timefree_session, 'test_timefree_token')
        self.assertFalse(authenticator.auth_info.is_timefree_session_expired())
        
        # And: セッションヘッダーにトークンが設定される
        self.assertEqual(authenticator.session.headers['X-Radiko-AuthToken'], 'test_timefree_token')


class TestRadikoAuthenticatorSecurity(unittest.TestCase, RealEnvironmentTestBase):
    """RadikoAuthenticator暗号化・セキュリティ機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_04_認証情報暗号化復号化検証(self):
        """
        TDD Test: 認証情報暗号化・復号化検証
        
        認証情報の暗号化保存と復号化読み込みが正常動作することを確認
        """
        # Given: 認証器と暗号化対象データ
        config_path = self.temp_env.config_dir / "auth_config.json"
        authenticator = RadikoAuthenticator(config_path=str(config_path))
        
        test_username = "test_user@example.com"
        test_password = "secure_password_123"
        
        # When: データを暗号化
        encrypted_username = authenticator._encrypt_data(test_username)
        encrypted_password = authenticator._encrypt_data(test_password)
        
        # Then: 暗号化データが元データと異なる
        self.assertNotEqual(encrypted_username, test_username)
        self.assertNotEqual(encrypted_password, test_password)
        self.assertTrue(len(encrypted_username) > len(test_username))
        self.assertTrue(len(encrypted_password) > len(test_password))
        
        # When: データを復号化
        decrypted_username = authenticator._decrypt_data(encrypted_username)
        decrypted_password = authenticator._decrypt_data(encrypted_password)
        
        # Then: 復号化データが元データと一致
        self.assertEqual(decrypted_username, test_username)
        self.assertEqual(decrypted_password, test_password)
    
    def test_05_認証ファイル読み書き検証(self):
        """
        TDD Test: 認証ファイル読み書き検証
        
        認証情報のファイル保存と読み込みが正常動作することを確認
        """
        # Given: 認証器と保存データ
        config_path = self.temp_env.config_dir / "auth_config.json"
        authenticator = RadikoAuthenticator(config_path=str(config_path))
        
        test_username = "test_user@example.com"
        test_password = "secure_password_123"
        
        # When: 認証情報を保存
        authenticator._save_config(test_username, test_password)
        
        # Then: ファイルが作成される
        self.assertTrue(config_path.exists())
        
        # And: ファイル権限が制限される（Unix系のみ）
        if hasattr(config_path, 'stat'):
            file_stat = config_path.stat()
            # 0o600 = owner read/write only
            self.assertEqual(file_stat.st_mode & 0o777, 0o600)
        
        # When: 認証情報を読み込み
        loaded_config = authenticator._load_config()
        
        # Then: 正しい認証情報が復号化される
        self.assertIsNotNone(loaded_config)
        self.assertEqual(loaded_config['username'], test_username)
        self.assertEqual(loaded_config['password'], test_password)
        
        # And: 保存時のタイムスタンプが記録される
        with open(config_path, 'r') as f:
            raw_config = json.load(f)
        self.assertIn('saved_at', raw_config)
        self.assertIsInstance(raw_config['saved_at'], (int, float))
    
    def test_06_認証エラーハンドリング(self):
        """
        TDD Test: 認証エラーハンドリング
        
        各種認証エラーが適切に処理されることを確認
        """
        # Given: 認証器
        config_path = self.temp_env.config_dir / "auth_config.json"
        authenticator = RadikoAuthenticator(config_path=str(config_path))
        
        # Test Case 1: 暗号化エラー
        with patch('cryptography.fernet.Fernet.encrypt', side_effect=Exception("Encryption failed")):
            with self.assertRaises(AuthenticationError) as context:
                authenticator._encrypt_data("test_data")
            self.assertIn("データの暗号化に失敗しました", str(context.exception))
        
        # Test Case 2: 復号化エラー
        with patch('cryptography.fernet.Fernet.decrypt', side_effect=Exception("Decryption failed")):
            with self.assertRaises(AuthenticationError) as context:
                authenticator._decrypt_data("invalid_encrypted_data")
            self.assertIn("データの復号化に失敗しました", str(context.exception))
        
        # Test Case 3: ファイル保存エラー
        invalid_config_path = Path("/invalid/path/config.json")
        invalid_authenticator = RadikoAuthenticator(config_path=str(invalid_config_path))
        invalid_authenticator.encryption_key = authenticator.encryption_key
        
        with self.assertRaises(AuthenticationError) as context:
            invalid_authenticator._save_config("test_user", "test_pass")
        self.assertIn("認証情報の保存に失敗しました", str(context.exception))
        
        # Test Case 4: 破損ファイル読み込み
        corrupted_file = self.temp_env.config_dir / "corrupted_config.json"
        corrupted_file.write_text("invalid json content")
        
        corrupted_authenticator = RadikoAuthenticator(config_path=str(corrupted_file))
        loaded_config = corrupted_authenticator._load_config()
        self.assertIsNone(loaded_config)


class TestRadikoAuthenticatorLocationServices(unittest.TestCase, RealEnvironmentTestBase):
    """RadikoAuthenticator地域判定・キャッシュ機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    @patch('requests.Session.get')
    def test_07_地域ID自動判定機能(self, mock_get):
        """
        TDD Test: 地域ID自動判定機能
        
        IP位置情報から地域IDが自動判定されることを確認
        """
        # Given: 位置情報APIの正常レスポンス
        location_response = MagicMock()
        location_response.raise_for_status.return_value = None
        location_response.headers = {'content-type': 'application/json'}
        location_response.text = '{"ip":"192.168.1.1","region":"Tokyo","country":"Japan"}'
        location_response.json.return_value = {
            "ip": "192.168.1.1",
            "region": "Tokyo", 
            "country": "Japan"
        }
        
        mock_get.return_value = location_response
        
        # When: 地域情報を取得
        config_path = self.temp_env.config_dir / "auth_config.json"
        authenticator = RadikoAuthenticator(config_path=str(config_path))
        location_info = authenticator.get_location_info()
        
        # Then: 正しい地域情報が設定される
        self.assertIsInstance(location_info, LocationInfo)
        self.assertEqual(location_info.ip_address, "192.168.1.1")
        self.assertEqual(location_info.region, "Tokyo")
        self.assertEqual(location_info.country, "Japan")
        self.assertEqual(location_info.area_id, "JP13")  # Tokyoに対応
        
        # And: 認証器の地域情報が更新される
        self.assertEqual(authenticator.location_info, location_info)
    
    def test_08_認証情報キャッシュ機能(self):
        """
        TDD Test: 認証情報キャッシュ機能
        
        有効な認証情報がキャッシュされ再利用されることを確認
        """
        # Given: 認証器と有効な認証情報
        config_path = self.temp_env.config_dir / "auth_config.json"
        authenticator = RadikoAuthenticator(config_path=str(config_path))
        
        # 有効な認証情報を設定（期限内）
        valid_auth_info = AuthInfo(
            auth_token="cached_token_123",
            area_id="JP13",
            expires_at=time.time() + 1800,  # 30分後
            premium_user=False,
            timefree_session="cached_timefree_123",
            timefree_expires_at=time.time() + 900  # 15分後
        )
        authenticator.auth_info = valid_auth_info
        
        # When: 有効な認証情報を取得
        cached_auth_info = authenticator.get_valid_auth_info()
        
        # Then: キャッシュされた認証情報が返される
        self.assertEqual(cached_auth_info, valid_auth_info)
        self.assertEqual(cached_auth_info.auth_token, "cached_token_123")
        self.assertFalse(cached_auth_info.is_expired())
        
        # When: 認証状態を確認
        is_authenticated = authenticator.is_authenticated()
        
        # Then: 認証済み状態が確認される
        self.assertTrue(is_authenticated)
        
        # When: ログアウト
        authenticator.logout()
        
        # Then: 認証情報がクリアされる
        self.assertIsNone(authenticator.auth_info)
        self.assertIsNone(authenticator.location_info)
        self.assertFalse(authenticator.is_authenticated())


if __name__ == "__main__":
    unittest.main()