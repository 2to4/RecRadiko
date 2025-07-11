"""
認証モジュールの単体テスト
"""

import unittest
import tempfile
import json
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import time

from src.auth import RadikoAuthenticator, AuthInfo, LocationInfo, AuthenticationError


class TestAuthInfo(unittest.TestCase):
    """AuthInfo クラスのテスト"""
    
    def test_auth_info_creation(self):
        """AuthInfo の作成テスト"""
        auth_info = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=time.time() + 3600,
            premium_user=False
        )
        
        self.assertEqual(auth_info.auth_token, "test_token")
        self.assertEqual(auth_info.area_id, "JP13")
        self.assertFalse(auth_info.premium_user)
    
    def test_is_expired(self):
        """有効期限チェックのテスト"""
        # 期限切れでない場合
        auth_info = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=time.time() + 3600
        )
        self.assertFalse(auth_info.is_expired())
        
        # 期限切れの場合
        auth_info_expired = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=time.time() - 3600
        )
        self.assertTrue(auth_info_expired.is_expired())


class TestLocationInfo(unittest.TestCase):
    """LocationInfo クラスのテスト"""
    
    def test_location_info_creation(self):
        """LocationInfo の作成テスト"""
        location_info = LocationInfo(
            ip_address="192.168.1.1",
            area_id="JP13",
            region="Tokyo",
            country="Japan"
        )
        
        self.assertEqual(location_info.ip_address, "192.168.1.1")
        self.assertEqual(location_info.area_id, "JP13")
        self.assertEqual(location_info.region, "Tokyo")
        self.assertEqual(location_info.country, "Japan")


class TestRadikoAuthenticator(unittest.TestCase):
    """RadikoAuthenticator クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = f"{self.temp_dir}/auth_config.json"
        self.authenticator = RadikoAuthenticator(config_path=self.config_path)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_authenticator_creation(self):
        """認証器の作成テスト"""
        self.assertIsInstance(self.authenticator, RadikoAuthenticator)
        self.assertIsNone(self.authenticator.auth_info)
        self.assertIsNone(self.authenticator.location_info)
    
    def test_encrypt_decrypt_data(self):
        """データの暗号化・復号化テスト"""
        test_data = "test_password_123"
        
        encrypted = self.authenticator._encrypt_data(test_data)
        self.assertNotEqual(encrypted, test_data)
        
        decrypted = self.authenticator._decrypt_data(encrypted)
        self.assertEqual(decrypted, test_data)
    
    @patch('requests.Session.get')
    def test_get_location_info_success(self, mock_get):
        """位置情報取得成功のテスト"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'ip': '192.168.1.1',
            'region': 'Tokyo',
            'country_name': 'Japan'
        }
        mock_get.return_value = mock_response
        
        location_info = self.authenticator.get_location_info()
        
        self.assertIsInstance(location_info, LocationInfo)
        self.assertEqual(location_info.area_id, "JP13")  # Tokyo のマッピング
        self.assertEqual(location_info.region, "Tokyo")
        self.assertEqual(location_info.country, "Japan")
    
    @patch('requests.Session.get')
    def test_get_location_info_failure(self, mock_get):
        """位置情報取得失敗のテスト"""
        # API 呼び出しが失敗する場合
        mock_get.side_effect = Exception("Network error")
        
        location_info = self.authenticator.get_location_info()
        
        # デフォルト値が設定されることを確認
        self.assertEqual(location_info.area_id, "JP13")
        self.assertEqual(location_info.region, "Tokyo")
        self.assertEqual(location_info.country, "Japan")
        self.assertEqual(location_info.ip_address, "unknown")
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    @patch.object(RadikoAuthenticator, 'get_location_info')
    def test_authenticate_success(self, mock_location, mock_get, mock_post):
        """基本認証成功のテスト"""
        # 位置情報のモック
        mock_location.return_value = LocationInfo(
            ip_address="192.168.1.1",
            area_id="JP13",
            region="Tokyo",
            country="Japan"
        )
        
        # 認証レスポンスのモック
        mock_auth1_response = Mock()
        mock_auth1_response.raise_for_status.return_value = None
        mock_auth1_response.headers = {
            'X-Radiko-AuthToken': 'test_token_123',
            'X-Radiko-KeyLength': '16',
            'X-Radiko-KeyOffset': '0'
        }
        
        mock_auth2_response = Mock()
        mock_auth2_response.raise_for_status.return_value = None
        mock_auth2_response.text = "JP13,TBS,QRR"
        
        mock_get.side_effect = [mock_auth1_response, mock_auth2_response]
        
        auth_info = self.authenticator.authenticate()
        
        self.assertIsInstance(auth_info, AuthInfo)
        self.assertEqual(auth_info.auth_token, "test_token_123")
        self.assertEqual(auth_info.area_id, "JP13")
        self.assertFalse(auth_info.premium_user)
        self.assertFalse(auth_info.is_expired())
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_authenticate_failure_no_token(self, mock_get, mock_post):
        """認証失敗（トークンなし）のテスト"""
        # トークンなしのレスポンス
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {}
        mock_get.return_value = mock_response
        
        with self.assertRaises(AuthenticationError):
            self.authenticator.authenticate()
    
    @patch('requests.Session.post')
    @patch('requests.Session.get')
    def test_authenticate_failure_network_error(self, mock_get, mock_post):
        """認証失敗（ネットワークエラー）のテスト"""
        mock_get.side_effect = Exception("Network error")
        
        with self.assertRaises(AuthenticationError):
            self.authenticator.authenticate()
    
    @patch.object(RadikoAuthenticator, 'authenticate')
    @patch('requests.Session.post')
    def test_authenticate_premium_success(self, mock_post, mock_auth):
        """プレミアム認証成功のテスト"""
        # 基本認証の結果をモック
        basic_auth = AuthInfo(
            auth_token="basic_token",
            area_id="JP13",
            expires_at=time.time() + 3600
        )
        mock_auth.return_value = basic_auth
        
        # プレミアム認証レスポンスのモック
        mock_premium_response = Mock()
        mock_premium_response.raise_for_status.return_value = None
        mock_premium_response.json.return_value = {'status': 200}
        mock_post.return_value = mock_premium_response
        
        auth_info = self.authenticator.authenticate_premium("test_user", "test_pass")
        
        self.assertTrue(auth_info.premium_user)
        self.assertEqual(auth_info.auth_token, "basic_token")
    
    @patch.object(RadikoAuthenticator, 'authenticate')
    @patch('requests.Session.post')
    def test_authenticate_premium_failure(self, mock_post, mock_auth):
        """プレミアム認証失敗のテスト"""
        # 基本認証の結果をモック
        basic_auth = AuthInfo(
            auth_token="basic_token",
            area_id="JP13",
            expires_at=time.time() + 3600
        )
        mock_auth.return_value = basic_auth
        
        # プレミアム認証失敗レスポンス
        mock_premium_response = Mock()
        mock_premium_response.raise_for_status.return_value = None
        mock_premium_response.json.return_value = {
            'status': 400,
            'message': 'Invalid credentials'
        }
        mock_post.return_value = mock_premium_response
        
        with self.assertRaises(AuthenticationError):
            self.authenticator.authenticate_premium("bad_user", "bad_pass")
    
    def test_save_load_config(self):
        """設定保存・読み込みのテスト"""
        username = "test_user"
        password = "test_password"
        
        # 設定保存
        self.authenticator._save_config(username, password)
        
        # 設定読み込み
        config = self.authenticator._load_config()
        
        self.assertIsNotNone(config)
        self.assertEqual(config['username'], username)
        self.assertEqual(config['password'], password)
    
    def test_load_config_nonexistent(self):
        """存在しない設定ファイルの読み込みテスト"""
        # 存在しないファイルパスで認証器を作成
        auth = RadikoAuthenticator(config_path="/nonexistent/path.json")
        config = auth._load_config()
        
        self.assertIsNone(config)
    
    def test_is_authenticated(self):
        """認証状態チェックのテスト"""
        # 未認証状態
        self.assertFalse(self.authenticator.is_authenticated())
        
        # 有効な認証情報を設定
        self.authenticator.auth_info = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=time.time() + 3600
        )
        self.assertTrue(self.authenticator.is_authenticated())
        
        # 期限切れの認証情報を設定
        self.authenticator.auth_info = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=time.time() - 3600
        )
        self.assertFalse(self.authenticator.is_authenticated())
    
    def test_logout(self):
        """ログアウトのテスト"""
        # 認証情報を設定
        self.authenticator.auth_info = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=time.time() + 3600
        )
        self.authenticator.location_info = LocationInfo(
            ip_address="192.168.1.1",
            area_id="JP13",
            region="Tokyo",
            country="Japan"
        )
        
        # ログアウト実行
        self.authenticator.logout()
        
        # 認証情報がクリアされることを確認
        self.assertIsNone(self.authenticator.auth_info)
        self.assertIsNone(self.authenticator.location_info)
    
    @patch('src.auth.requests.Session.get')
    @patch('time.sleep')
    def test_authentication_retry_mechanism(self, mock_sleep, mock_get):
        """認証リトライ機能のテスト"""
        # 最初の2回は失敗、3回目は成功
        mock_response1 = Mock()
        mock_response1.raise_for_status.side_effect = requests.RequestException("Network error")
        
        mock_response2 = Mock()
        mock_response2.raise_for_status.side_effect = requests.RequestException("Network error")
        
        mock_response3 = Mock()
        mock_response3.raise_for_status.return_value = None
        mock_response3.headers = {
            'X-Radiko-AuthToken': 'test_token_123',
            'X-Radiko-KeyLength': '16',
            'X-Radiko-KeyOffset': '0'
        }
        
        # auth2レスポンス
        mock_response4 = Mock()
        mock_response4.raise_for_status.return_value = None
        mock_response4.text = "JP13,TBS,QRR,LFR"
        
        mock_get.side_effect = [mock_response1, mock_response2, mock_response3, mock_response4]
        
        # 位置情報取得をモック
        with patch.object(self.authenticator, 'get_location_info') as mock_location:
            mock_location.return_value = LocationInfo(
                ip_address="192.168.1.1",
                area_id="JP13",
                region="Tokyo",
                country="Japan"
            )
            
            # 認証実行
            auth_info = self.authenticator.authenticate()
            
            # 認証成功を確認
            self.assertIsNotNone(auth_info)
            self.assertEqual(auth_info.auth_token, "test_token_123")
            self.assertEqual(auth_info.area_id, "JP13")
            
            # 3回試行されたことを確認（auth1で3回 + auth2で1回）
            self.assertEqual(mock_get.call_count, 4)
            
            # sleepが2回呼ばれたことを確認（失敗間のリトライ待機）
            self.assertEqual(mock_sleep.call_count, 2)
    
    @patch('src.auth.requests.Session.get')
    @patch('time.sleep')
    def test_authentication_max_retries_exceeded(self, mock_sleep, mock_get):
        """認証リトライ上限超過のテスト"""
        # 全ての試行で失敗
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.RequestException("Persistent network error")
        mock_get.return_value = mock_response
        
        # 認証実行（例外が発生することを期待）
        with self.assertRaises(AuthenticationError) as context:
            self.authenticator.authenticate()
        
        # エラーメッセージの確認
        self.assertIn("認証リクエストに失敗しました", str(context.exception))
        
        # 3回試行されたことを確認
        self.assertEqual(mock_get.call_count, 3)
        
        # sleepが2回呼ばれたことを確認（失敗間のリトライ待機）
        self.assertEqual(mock_sleep.call_count, 2)
    
    @patch('src.auth.requests.Session.get')
    def test_authentication_immediate_success(self, mock_get):
        """認証即座成功のテスト（リトライなし）"""
        # 最初の試行で成功
        mock_response1 = Mock()
        mock_response1.raise_for_status.return_value = None
        mock_response1.headers = {
            'X-Radiko-AuthToken': 'test_token_success',
            'X-Radiko-KeyLength': '16',
            'X-Radiko-KeyOffset': '0'
        }
        
        mock_response2 = Mock()
        mock_response2.raise_for_status.return_value = None
        mock_response2.text = "JP13,TBS,QRR,LFR"
        
        mock_get.side_effect = [mock_response1, mock_response2]
        
        # 位置情報取得をモック
        with patch.object(self.authenticator, 'get_location_info') as mock_location:
            mock_location.return_value = LocationInfo(
                ip_address="192.168.1.1",
                area_id="JP13",
                region="Tokyo",
                country="Japan"
            )
            
            # 認証実行
            auth_info = self.authenticator.authenticate()
            
            # 認証成功を確認
            self.assertIsNotNone(auth_info)
            self.assertEqual(auth_info.auth_token, "test_token_success")
            
            # 2回のみ呼ばれたことを確認（auth1で1回 + auth2で1回）
            self.assertEqual(mock_get.call_count, 2)
    
    @patch('src.auth.requests.Session.get')
    @patch('time.sleep')
    def test_authentication_partial_retry(self, mock_sleep, mock_get):
        """認証部分リトライのテスト（2回目で成功）"""
        # 最初の1回は失敗、2回目は成功
        mock_response1 = Mock()
        mock_response1.raise_for_status.side_effect = requests.RequestException("Temporary error")
        
        mock_response2 = Mock()
        mock_response2.raise_for_status.return_value = None
        mock_response2.headers = {
            'X-Radiko-AuthToken': 'test_token_retry',
            'X-Radiko-KeyLength': '16',
            'X-Radiko-KeyOffset': '0'
        }
        
        mock_response3 = Mock()
        mock_response3.raise_for_status.return_value = None
        mock_response3.text = "JP13,TBS,QRR,LFR"
        
        mock_get.side_effect = [mock_response1, mock_response2, mock_response3]
        
        # 位置情報取得をモック
        with patch.object(self.authenticator, 'get_location_info') as mock_location:
            mock_location.return_value = LocationInfo(
                ip_address="192.168.1.1",
                area_id="JP13",
                region="Tokyo",
                country="Japan"
            )
            
            # 認証実行
            auth_info = self.authenticator.authenticate()
            
            # 認証成功を確認
            self.assertIsNotNone(auth_info)
            self.assertEqual(auth_info.auth_token, "test_token_retry")
            
            # 3回呼ばれたことを確認（auth1で2回 + auth2で1回）
            self.assertEqual(mock_get.call_count, 3)
            
            # sleepが1回呼ばれたことを確認（1回の失敗後のリトライ待機）
            self.assertEqual(mock_sleep.call_count, 1)


if __name__ == '__main__':
    unittest.main()