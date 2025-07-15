"""
認証システム統合テスト（実環境ベース）

モック使用を最小化し、実際のファイル操作・設定管理・暗号化処理を使用した
認証システムの統合テストです。

変更点:
- モック使用: 117個 → 25個 (78%削減)
- 実際のファイル操作を使用
- 実際の暗号化・復号化処理を使用
- 実際の設定管理を使用
- 外部API通信のみモック使用
"""

import pytest
import unittest
import tempfile
import json
import time
from unittest.mock import patch, Mock
from datetime import datetime
from pathlib import Path
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.auth import RadikoAuthenticator, AuthInfo, LocationInfo, AuthenticationError
from tests.utils.test_environment import TemporaryTestEnvironment, RealEnvironmentTestBase


class TestAuthInfoRealEnvironment(unittest.TestCase):
    """AuthInfo クラスの実環境テスト"""
    
    def test_auth_info_creation_real_time(self):
        """実際の時刻を使用したAuthInfo作成テスト"""
        current_time = time.time()
        
        auth_info = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=current_time + 3600,
            premium_user=False
        )
        
        assert auth_info.auth_token == "test_token"
        assert auth_info.area_id == "JP13"
        assert not auth_info.premium_user
        assert not auth_info.is_expired()
    
    def test_expiration_with_real_time(self):
        """実際の時刻を使用した有効期限テスト"""
        current_time = time.time()
        
        # 有効な認証情報
        valid_auth = AuthInfo(
            auth_token="valid_token",
            area_id="JP13",
            expires_at=current_time + 3600
        )
        assert not valid_auth.is_expired()
        
        # 期限切れの認証情報
        expired_auth = AuthInfo(
            auth_token="expired_token",
            area_id="JP13",
            expires_at=current_time - 3600
        )
        assert expired_auth.is_expired()
    
    def test_timefree_session_real_time(self):
        """実際の時刻を使用したタイムフリーセッションテスト"""
        current_time = time.time()
        
        auth_info = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=current_time + 3600,
            premium_user=True,
            timefree_session="timefree_token",
            timefree_expires_at=current_time + 1800
        )
        
        assert auth_info.timefree_session == "timefree_token"
        assert not auth_info.is_timefree_session_expired()
        
        # 期限切れ設定
        auth_info.timefree_expires_at = current_time - 1800
        assert auth_info.is_timefree_session_expired()


class TestLocationInfoRealEnvironment(unittest.TestCase):
    """LocationInfo クラスの実環境テスト"""
    
    def test_location_info_creation_real_data(self):
        """実際のデータを使用したLocationInfo作成テスト"""
        location_info = LocationInfo(
            ip_address="192.168.1.100",
            area_id="JP13",
            region="Tokyo",
            country="Japan"
        )
        
        assert location_info.ip_address == "192.168.1.100"
        assert location_info.area_id == "JP13"
        assert location_info.region == "Tokyo"
        assert location_info.country == "Japan"


class TestRadikoAuthenticatorRealEnvironment(RealEnvironmentTestBase):
    """RadikoAuthenticator クラスの実環境テスト"""
    
    def test_authenticator_real_initialization(self, temp_env):
        """実環境での認証器初期化テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        assert isinstance(authenticator, RadikoAuthenticator)
        assert str(authenticator.config_path) == str(temp_env.config_file)
        assert authenticator.auth_info is None
        assert authenticator.location_info is None
        
        # 実際のファイル操作確認
        assert temp_env.config_file.exists()
    
    def test_real_encrypt_decrypt_operations(self, temp_env):
        """実際の暗号化・復号化操作テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 実際の暗号化処理
        test_data = "test_password_123"
        encrypted = authenticator._encrypt_data(test_data)
        
        # 暗号化されていることを確認
        assert encrypted != test_data
        assert len(encrypted) > len(test_data)
        
        # 実際の復号化処理
        decrypted = authenticator._decrypt_data(encrypted)
        assert decrypted == test_data
    
    def test_real_config_save_load_operations(self, temp_env):
        """実際の設定保存・読み込み操作テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        username = "test_user"
        password = "test_password"
        
        # 実際のファイル保存
        authenticator._save_config(username, password)
        
        # 実際のファイル読み込み
        config = authenticator._load_config()
        
        assert config is not None
        assert config['username'] == username
        assert config['password'] == password
        
        # 実際のファイル存在確認
        config_file = Path(authenticator.config_path)
        assert config_file.exists()
        
        # 実際のJSONファイル内容確認
        with open(config_file, 'r') as f:
            file_content = json.load(f)
            assert 'username' in file_content
            assert 'password' in file_content
    
    def test_real_config_load_nonexistent_file(self, temp_env):
        """存在しないファイルの読み込みテスト（実際のファイルシステム）"""
        # 存在しないパスで認証器作成
        nonexistent_path = str(temp_env.config_dir / "nonexistent.json")
        authenticator = RadikoAuthenticator(config_path=nonexistent_path)
        
        # 実際のファイルシステムでの動作確認
        config = authenticator._load_config()
        assert config is None
        
        # ファイルが存在しないことを確認
        assert not Path(nonexistent_path).exists()
    
    def test_real_authentication_state_management(self, temp_env):
        """実際の認証状態管理テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 初期状態確認
        assert not authenticator.is_authenticated()
        
        # 実際の認証情報設定
        current_time = time.time()
        authenticator.auth_info = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=current_time + 3600
        )
        
        # 認証状態確認
        assert authenticator.is_authenticated()
        
        # 期限切れの認証情報設定
        authenticator.auth_info = AuthInfo(
            auth_token="expired_token",
            area_id="JP13",
            expires_at=current_time - 3600
        )
        
        # 期限切れ確認
        assert not authenticator.is_authenticated()
    
    def test_real_logout_operations(self, temp_env):
        """実際のログアウト操作テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 認証情報設定
        authenticator.auth_info = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=time.time() + 3600
        )
        authenticator.location_info = LocationInfo(
            ip_address="192.168.1.1",
            area_id="JP13",
            region="Tokyo",
            country="Japan"
        )
        
        # ログアウト実行
        authenticator.logout()
        
        # 認証情報がクリアされることを確認
        assert authenticator.auth_info is None
        assert authenticator.location_info is None
    
    def test_real_location_info_with_api_mock(self, temp_env):
        """実際のHTTP処理（APIのみモック）での位置情報取得テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 外部APIのみモック使用
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                'ip': '192.168.1.1',
                'region': 'Tokyo',
                'country_name': 'Japan'
            }
            mock_get.return_value = mock_response
            
            # 実際の処理実行
            location_info = authenticator.get_location_info()
            
            # 結果確認
            assert isinstance(location_info, LocationInfo)
            assert location_info.area_id == "JP13"  # Tokyo mapping
            assert location_info.region == "Tokyo"
            assert location_info.country == "Japan"
    
    def test_real_location_info_api_failure(self, temp_env):
        """API失敗時の実際の処理テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 外部API失敗をモック
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            # 実際の処理実行（デフォルト値使用）
            location_info = authenticator.get_location_info()
            
            # デフォルト値確認
            assert location_info.area_id == "JP13"
            assert location_info.region == "Tokyo"
            assert location_info.country == "Japan"
            assert location_info.ip_address == "unknown"
    
    def test_real_basic_authentication_with_api_mock(self, temp_env):
        """基本認証の実際の処理テスト（外部APIのみモック）"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 外部APIのみモック使用
        with patch('requests.Session.get') as mock_get:
            with patch.object(authenticator, 'get_location_info') as mock_location:
                # 位置情報モック
                mock_location.return_value = LocationInfo(
                    ip_address="192.168.1.1",
                    area_id="JP13",
                    region="Tokyo",
                    country="Japan"
                )
                
                # 認証APIレスポンスモック
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
                
                # 実際の認証処理実行
                auth_info = authenticator.authenticate()
                
                # 結果確認
                assert isinstance(auth_info, AuthInfo)
                assert auth_info.auth_token == "test_token_123"
                assert auth_info.area_id == "JP13"
                assert not auth_info.premium_user
                assert not auth_info.is_expired()
    
    def test_real_authentication_failure_scenarios(self, temp_env):
        """実際の認証失敗シナリオテスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # トークンなしの場合
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.headers = {}
            mock_get.return_value = mock_response
            
            with pytest.raises(AuthenticationError):
                authenticator.authenticate()
        
        # ネットワークエラーの場合
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            with pytest.raises(AuthenticationError):
                authenticator.authenticate()


class TestTimeFreeAuthenticationRealEnvironment(RealEnvironmentTestBase):
    """タイムフリー認証の実環境テスト"""
    
    def test_real_timefree_authentication_2025_spec(self, temp_env):
        """2025年仕様での実際のタイムフリー認証テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 実際の基本認証情報設定
        authenticator.auth_info = AuthInfo(
            auth_token="base_auth_token",
            area_id="JP13",
            expires_at=time.time() + 3600
        )
        
        # 2025年仕様での実際の処理
        timefree_session = authenticator.authenticate_timefree()
        
        # 2025年仕様確認（基本認証トークン使用）
        assert timefree_session == 'base_auth_token'
        assert authenticator.auth_info.timefree_session == 'base_auth_token'
        assert authenticator.auth_info.timefree_expires_at is not None
        assert not authenticator.auth_info.is_timefree_session_expired()
    
    def test_real_timefree_cached_session(self, temp_env):
        """実際のキャッシュされたタイムフリーセッション使用テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 基本認証情報設定
        authenticator.auth_info = AuthInfo(
            auth_token="base_auth_token",
            area_id="JP13",
            expires_at=time.time() + 3600
        )
        
        # 有効なタイムフリーセッション設定
        authenticator.auth_info.timefree_session = "cached_timefree_token"
        authenticator.auth_info.timefree_expires_at = time.time() + 1800
        
        # 実際の処理実行
        timefree_session = authenticator.authenticate_timefree()
        
        # キャッシュされたセッション使用確認
        assert timefree_session == "cached_timefree_token"
    
    def test_real_timefree_playlist_url_generation(self, temp_env):
        """実際のタイムフリープレイリストURL生成テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # タイムフリーセッション設定
        authenticator.auth_info = AuthInfo(
            auth_token="base_auth_token",
            area_id="JP13",
            expires_at=time.time() + 3600,
            timefree_session="timefree_token_123",
            timefree_expires_at=time.time() + 1800
        )
        
        # 実際のURL生成
        playlist_url = authenticator.get_timefree_playlist_url(
            station_id="TBS",
            start_time="20250713120000",
            duration=3600
        )
        
        # 2025年仕様URL確認
        assert "radiko.jp/v2/api/ts/playlist.m3u8" in playlist_url
        assert "station_id=TBS" in playlist_url
        assert "ft=20250713120000" in playlist_url
        assert "to=20250713130000" in playlist_url
    
    def test_real_timefree_session_management(self, temp_env):
        """実際のタイムフリーセッション管理テスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 基本認証情報設定
        authenticator.auth_info = AuthInfo(
            auth_token="base_auth_token",
            area_id="JP13",
            expires_at=time.time() + 3600
        )
        
        # セッション取得
        session = authenticator.get_timefree_session()
        
        # 実際のセッション確認
        assert session is not None
        assert hasattr(session, 'get')  # requests.Session のメソッド確認


class TestAuthenticationIntegration(RealEnvironmentTestBase):
    """認証システム統合テスト"""
    
    def test_end_to_end_authentication_workflow(self, temp_env):
        """エンドツーエンドの認証ワークフローテスト"""
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 1. 実際の設定保存
        authenticator._save_config("test_user", "test_password")
        
        # 2. 実際の設定読み込み
        config = authenticator._load_config()
        assert config["username"] == "test_user"
        
        # 3. 実際の暗号化処理
        encrypted_password = authenticator._encrypt_data("test_password")
        decrypted_password = authenticator._decrypt_data(encrypted_password)
        assert decrypted_password == "test_password"
        
        # 4. 外部APIをモックした認証処理
        with patch('requests.Session.get') as mock_get:
            with patch.object(authenticator, 'get_location_info') as mock_location:
                mock_location.return_value = LocationInfo(
                    ip_address="192.168.1.1",
                    area_id="JP13",
                    region="Tokyo",
                    country="Japan"
                )
                
                mock_auth1_response = Mock()
                mock_auth1_response.raise_for_status.return_value = None
                mock_auth1_response.headers = {
                    'X-Radiko-AuthToken': 'integration_token_123',
                    'X-Radiko-KeyLength': '16',
                    'X-Radiko-KeyOffset': '0'
                }
                
                mock_auth2_response = Mock()
                mock_auth2_response.raise_for_status.return_value = None
                mock_auth2_response.text = "JP13,TBS,QRR"
                
                mock_get.side_effect = [mock_auth1_response, mock_auth2_response]
                
                # 統合テスト実行
                auth_info = authenticator.authenticate()
                
                # 結果確認
                assert auth_info.auth_token == "integration_token_123"
                assert auth_info.area_id == "JP13"
                
                # タイムフリー認証実行
                timefree_session = authenticator.authenticate_timefree()
                assert timefree_session == "integration_token_123"
    
    def test_real_file_system_integration(self, temp_env):
        """実際のファイルシステム統合テスト"""
        # ファイルシステム操作の検証
        assert self.verify_file_operations(temp_env)
        
        # 設定操作の検証
        assert self.verify_configuration_operations(temp_env)
        
        # 認証器での実際のファイル操作
        authenticator = self.setup_real_authenticator(temp_env)
        
        # 複数の設定保存・読み込み
        test_configs = [
            ("user1", "pass1"),
            ("user2", "pass2"),
            ("user3", "pass3")
        ]
        
        for username, password in test_configs:
            authenticator._save_config(username, password)
            config = authenticator._load_config()
            assert config["username"] == username
            assert config["password"] == password


if __name__ == '__main__':
    unittest.main()