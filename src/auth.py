"""
Radiko認証モジュール

このモジュールはRadikoサービスへの認証を管理します。
- 基本認証（エリア認証）
- プレミアム会員認証
- 認証トークンの管理
- 位置情報の取得
"""

import requests
import time
import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path
from cryptography.fernet import Fernet

from .logging_config import get_logger


@dataclass
class AuthInfo:
    """認証情報を保持するデータクラス"""
    auth_token: str
    area_id: str
    expires_at: float
    premium_user: bool = False
    
    def is_expired(self) -> bool:
        """認証トークンが期限切れかどうかをチェック"""
        return time.time() >= self.expires_at


@dataclass
class LocationInfo:
    """位置情報を保持するデータクラス"""
    ip_address: str
    area_id: str
    region: str
    country: str


class RadikoAuthenticator:
    """Radiko認証を管理するクラス"""
    
    # Radiko API エンドポイント
    AUTH1_URL = "https://radiko.jp/v2/api/auth1"
    AUTH2_URL = "https://radiko.jp/v2/api/auth2"
    PREMIUM_LOGIN_URL = "https://radiko.jp/ap/member/webapi/member/login"
    
    # Radiko認証キー（固定値）
    AUTH_KEY = "bcd151073c03b352e1ef2fd66c32209da9ca0afa"
    
    # 認証に必要なヘッダー
    DEFAULT_HEADERS = {
        'User-Agent': 'curl/7.56.1',
        'Accept': '*/*',
        'Accept-Language': 'ja,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    def __init__(self, config_path: str = "auth_config.json"):
        self.config_path = Path(config_path)
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        
        self.auth_info: Optional[AuthInfo] = None
        self.location_info: Optional[LocationInfo] = None
        self.encryption_key = self._get_or_create_key()
        
        self.logger = get_logger(__name__)
        
        # セッションの設定
        self.session.timeout = 30
    
    def _generate_partialkey(self, offset: int, length: int) -> str:
        """部分キーを生成"""
        import base64
        auth_key_bytes = self.AUTH_KEY.encode('utf-8')
        partial_key = auth_key_bytes[offset:offset + length]
        return base64.b64encode(partial_key).decode('utf-8')
    
    def _get_or_create_key(self) -> bytes:
        """暗号化キーを取得または作成"""
        key_file = Path("encryption.key")
        try:
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    return f.read()
            else:
                key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(key)
                # ファイル権限を制限
                key_file.chmod(0o600)
                return key
        except Exception as e:
            self.logger.error(f"暗号化キーの処理でエラー: {e}")
            # フォールバック：一時的なキーを生成
            return Fernet.generate_key()
    
    def _encrypt_data(self, data: str) -> str:
        """データを暗号化"""
        try:
            f = Fernet(self.encryption_key)
            return f.encrypt(data.encode()).decode()
        except Exception as e:
            self.logger.error(f"データ暗号化エラー: {e}")
            raise AuthenticationError(f"データの暗号化に失敗しました: {e}")
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """データを復号化"""
        try:
            f = Fernet(self.encryption_key)
            return f.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            self.logger.error(f"データ復号化エラー: {e}")
            raise AuthenticationError(f"データの復号化に失敗しました: {e}")
    
    def get_location_info(self) -> LocationInfo:
        """位置情報を取得（複数のサービスを試行）"""
        # 複数のIP位置情報サービスを試行
        services = [
            ("ipapi.co", self._get_location_ipapi),
            ("ip-api.com", self._get_location_ipapi_com),
        ]
        
        for service_name, service_func in services:
            try:
                self.logger.info(f"位置情報を取得中: {service_name}")
                location_info = service_func()
                if location_info:
                    self.location_info = location_info
                    self.logger.info(f"位置情報取得成功: {location_info.area_id}")
                    return location_info
            except Exception as e:
                self.logger.warning(f"{service_name} での位置情報取得に失敗: {e}")
                continue
        
        # 全てのサービスが失敗した場合はデフォルト値を使用
        self.logger.warning("位置情報の取得に失敗、デフォルト値を使用")
        self.location_info = LocationInfo(
            ip_address="unknown",
            area_id="JP13",  # 東京をデフォルト
            region="Tokyo",
            country="Japan"
        )
        return self.location_info
    
    def _get_location_ipapi(self) -> Optional[LocationInfo]:
        """ipapi.co から位置情報を取得"""
        try:
            response = self.session.get("https://ipapi.co/json/", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 日本の地域IDマッピング
            area_mapping = {
                "Tokyo": "JP13",
                "Osaka": "JP27", 
                "Aichi": "JP23",  # 名古屋
                "Fukuoka": "JP40",
                "Hokkaido": "JP1",
                "Miyagi": "JP4",  # 仙台
                "Hiroshima": "JP34",
                "Shizuoka": "JP22"
            }
            
            # 複数のフィールド名パターンに対応
            region = (data.get('region') or 
                     data.get('region_name') or 
                     data.get('regionName') or 
                     'Tokyo')
            
            country = (data.get('country_name') or 
                      data.get('country') or 
                      'Japan')
            
            area_id = area_mapping.get(region, "JP13")
            
            return LocationInfo(
                ip_address=data.get('ip', 'unknown'),
                area_id=area_id,
                region=region,
                country=country
            )
        except Exception as e:
            self.logger.error(f"ipapi.co エラー: {e}")
            return None
    
    def _get_location_ipapi_com(self) -> Optional[LocationInfo]:
        """ip-api.com から位置情報を取得"""
        try:
            response = self.session.get(
                "http://ip-api.com/json/?fields=status,country,regionName,query", 
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'success':
                return None
            
            # 複数のフィールド名パターンに対応
            region = (data.get('regionName') or 
                     data.get('region_name') or 
                     data.get('region') or 
                     'Tokyo')
            
            country = (data.get('country') or 
                      data.get('country_name') or 
                      'Japan')
            
            # 簡易的な地域マッピング
            area_mapping = {
                "Tokyo": "JP13",
                "Kanagawa": "JP14",
                "Osaka": "JP27", 
                "Aichi": "JP23",
                "Fukuoka": "JP40",
                "Hokkaido": "JP1",
                "Miyagi": "JP4",
                "Hiroshima": "JP34",
                "Shizuoka": "JP22"
            }
            area_id = area_mapping.get(region, "JP13")  # デフォルト
            
            return LocationInfo(
                ip_address=data.get('query', 'unknown'),
                area_id=area_id,
                region=region,
                country=country
            )
        except Exception as e:
            self.logger.error(f"ip-api.com エラー: {e}")
            return None
    
    def authenticate(self) -> AuthInfo:
        """基本認証（エリア認証）を実行"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Radiko基本認証を開始 (試行 {attempt + 1}/{max_retries})")
                
                # Step 1: 認証開始リクエスト
                auth1_headers = {
                    'X-Radiko-App': 'pc_html5',
                    'X-Radiko-App-Version': '0.0.1',
                    'X-Radiko-User': 'dummy_user',
                    'X-Radiko-Device': 'pc'
                }
                
                auth1_response = self.session.get(
                    self.AUTH1_URL,
                    headers=auth1_headers
                )
                auth1_response.raise_for_status()
                
                # 認証トークンとキー情報を取得
                auth_token = auth1_response.headers.get('X-Radiko-AuthToken')
                key_length = auth1_response.headers.get('X-Radiko-KeyLength')
                key_offset = auth1_response.headers.get('X-Radiko-KeyOffset')
                
                if not auth_token:
                    raise AuthenticationError("認証トークンが取得できませんでした")
                if not key_length or not key_offset:
                    raise AuthenticationError("認証キー情報が取得できませんでした")
                
                self.logger.info("認証トークンとキー情報取得成功")
                
                # 部分キーを生成
                partialkey = self._generate_partialkey(int(key_offset), int(key_length))
                
                # Step 2: 位置情報を取得
                if not self.location_info:
                    self.get_location_info()
                
                # Step 3: 認証を完了
                auth2_headers = {
                    'X-Radiko-AuthToken': auth_token,
                    'X-Radiko-Partialkey': partialkey,
                    'X-Radiko-User': 'dummy_user',
                    'X-Radiko-Device': 'pc'
                }
                
                auth2_response = self.session.get(
                    self.AUTH2_URL,
                    headers=auth2_headers
                )
                auth2_response.raise_for_status()
                
                # レスポンスから地域情報を取得（可能であれば）
                response_text = auth2_response.text
                area_id = "JP13"  # デフォルト値
                if response_text and ',' in response_text:
                    # レスポンス形式: "area_id,station_ids"
                    parts = response_text.split(',')
                    if parts[0]:
                        area_id = parts[0]
                        if self.location_info:
                            self.location_info.area_id = parts[0]
                
                # 認証情報を作成
                self.auth_info = AuthInfo(
                    auth_token=auth_token,
                    area_id=area_id,
                    expires_at=time.time() + 3600  # 1時間後に期限切れ
                )
            
                # セッションヘッダーに認証トークンを追加
                self.session.headers['X-Radiko-AuthToken'] = auth_token
                
                self.logger.info(f"基本認証完了: area_id={self.auth_info.area_id}")
                return self.auth_info
                
            except requests.RequestException as e:
                self.logger.warning(f"認証リクエストエラー (試行 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise AuthenticationError(f"認証リクエストに失敗しました: {e}")
                # 1秒待機してリトライ
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"認証処理エラー: {e}")
                raise AuthenticationError(f"認証処理に失敗しました: {e}")
    
    def authenticate_premium(self, username: str, password: str) -> AuthInfo:
        """プレミアム会員認証"""
        try:
            self.logger.info("プレミアム会員認証を開始")
            
            # まず基本認証を実行
            auth_info = self.authenticate()
            
            # プレミアム認証リクエスト
            login_data = {
                'mail': username,
                'pass': password
            }
            
            premium_headers = {
                'X-Radiko-AuthToken': auth_info.auth_token,
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            premium_response = self.session.post(
                self.PREMIUM_LOGIN_URL,
                data=login_data,
                headers=premium_headers
            )
            premium_response.raise_for_status()
            
            # レスポンスをチェック
            response_data = premium_response.json()
            if response_data.get('status') != 200:
                error_msg = response_data.get('message', 'プレミアム認証に失敗')
                raise AuthenticationError(f"プレミアム認証エラー: {error_msg}")
            
            # プレミアム認証成功
            auth_info.premium_user = True
            self.auth_info = auth_info
            
            # 認証情報を保存
            self._save_config(username, password)
            
            self.logger.info("プレミアム認証完了")
            return auth_info
            
        except requests.RequestException as e:
            self.logger.error(f"プレミアム認証リクエストエラー: {e}")
            raise AuthenticationError(f"プレミアム認証リクエストに失敗しました: {e}")
        except Exception as e:
            self.logger.error(f"プレミアム認証エラー: {e}")
            raise AuthenticationError(f"プレミアム認証に失敗しました: {e}")
    
    def _save_config(self, username: str, password: str):
        """認証情報を暗号化して保存"""
        try:
            config = {
                'username': self._encrypt_data(username),
                'password': self._encrypt_data(password),
                'saved_at': time.time()
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f)
            
            # ファイル権限を制限
            self.config_path.chmod(0o600)
            
            self.logger.info("認証情報を保存しました")
            
        except Exception as e:
            self.logger.error(f"認証情報保存エラー: {e}")
            raise AuthenticationError(f"認証情報の保存に失敗しました: {e}")
    
    def _load_config(self) -> Optional[Dict[str, str]]:
        """保存された認証情報を読み込み復号化"""
        try:
            if not self.config_path.exists():
                return None
            
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            return {
                'username': self._decrypt_data(config['username']),
                'password': self._decrypt_data(config['password'])
            }
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            self.logger.warning(f"認証情報読み込みエラー: {e}")
            return None
        except Exception as e:
            self.logger.error(f"認証情報復号化エラー: {e}")
            return None
    
    def get_valid_auth_info(self) -> AuthInfo:
        """有効な認証情報を取得（期限切れの場合は再認証）"""
        # 既存の認証情報が有効かチェック
        if self.auth_info and not self.auth_info.is_expired():
            return self.auth_info
        
        self.logger.info("認証情報が期限切れまたは未取得、再認証を実行")
        
        # 保存済みプレミアム認証情報があるかチェック
        config = self._load_config()
        if config:
            try:
                return self.authenticate_premium(config['username'], config['password'])
            except AuthenticationError as e:
                self.logger.warning(f"保存済み認証情報での認証に失敗: {e}")
                # プレミアム認証に失敗した場合は基本認証にフォールバック
        
        # 基本認証を実行
        return self.authenticate()
    
    def is_authenticated(self) -> bool:
        """認証済みかどうかをチェック"""
        return self.auth_info is not None and not self.auth_info.is_expired()
    
    def logout(self):
        """ログアウト（認証情報をクリア）"""
        self.auth_info = None
        self.location_info = None
        
        # セッションから認証ヘッダーを削除
        if 'X-Radiko-AuthToken' in self.session.headers:
            del self.session.headers['X-Radiko-AuthToken']
        
        self.logger.info("ログアウトしました")
    
    def get_session(self) -> requests.Session:
        """認証済みセッションを取得"""
        if not self.is_authenticated():
            self.get_valid_auth_info()
        
        return self.session


class AuthenticationError(Exception):
    """認証エラーの例外クラス"""
    pass


# テスト用の簡単な使用例
if __name__ == "__main__":
    import sys
    
    # ログ設定（テスト実行時のみ）
    import os
    if os.environ.get('RECRADIKO_TEST_MODE', '').lower() == 'true':
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    try:
        # 認証テスト
        authenticator = RadikoAuthenticator()
        
        print("基本認証をテスト中...")
        auth_info = authenticator.authenticate()
        print(f"認証成功: area_id={auth_info.area_id}")
        
        # プレミアム認証をテストする場合（コメントアウト）
        # print("プレミアム認証をテスト中...")
        # username = input("ユーザー名: ")
        # password = input("パスワード: ")
        # auth_info = authenticator.authenticate_premium(username, password)
        # print(f"プレミアム認証成功: premium={auth_info.premium_user}")
        
    except AuthenticationError as e:
        print(f"認証エラー: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"予期しないエラー: {e}")
        sys.exit(1)