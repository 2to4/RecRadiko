"""
ネットワーク処理ユーティリティ

HTTP セッション作成などのネットワーク関連処理の統一機能
4クラスで重複していたセッション初期化・設定コードを統一
"""

import requests
from typing import Dict, Any, Optional


def create_radiko_session(
    timeout: int = 30,
    additional_headers: Optional[Dict[str, str]] = None
) -> requests.Session:
    """Radiko API用の標準セッションを作成
    
    Radiko APIアクセス用に最適化された requests.Session を作成する。
    タイムアウト設定、標準ヘッダー、認証設定などを統一する。
    
    Args:
        timeout: リクエストタイムアウト秒数（デフォルト: 30秒）
        additional_headers: 追加ヘッダー辞書
        
    Returns:
        requests.Session: 設定済みセッション
        
    Example:
        # 基本的な使用
        session = create_radiko_session()
        response = session.get("https://radiko.jp/v2/api/auth1")
        
        # カスタムヘッダー付き
        session = create_radiko_session(
            timeout=60,
            additional_headers={'X-Custom': 'value'}
        )
    
    Note:
        これまで4クラスで重複していた以下のパターンを置換:
        self.session = requests.Session()
        self.session.timeout = 30
        self.session.headers.update({'User-Agent': 'RecRadiko/1.0'})
    """
    session = requests.Session()
    session.timeout = timeout
    
    # Radiko API標準ヘッダー
    standard_headers = {
        'User-Agent': 'RecRadiko/1.0',
        'Accept': '*/*',
        'Accept-Language': 'ja,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    # 追加ヘッダーがある場合は統合
    if additional_headers:
        standard_headers.update(additional_headers)
    
    session.headers.update(standard_headers)
    return session


def create_streaming_session(
    timeout: int = 60,
    stream_timeout: int = 120
) -> requests.Session:
    """ストリーミング用の専用セッションを作成
    
    HLS ストリーミングやファイルダウンロード用に最適化された
    requests.Session を作成する。
    
    Args:
        timeout: 通常のリクエストタイムアウト秒数
        stream_timeout: ストリーミングタイムアウト秒数
        
    Returns:
        requests.Session: ストリーミング用設定済みセッション
    """
    session = requests.Session()
    session.timeout = timeout
    
    # ストリーミング用ヘッダー
    session.headers.update({
        'User-Agent': 'RecRadiko/1.0 (Streaming)',
        'Accept': '*/*',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache'
    })
    
    # ストリーミング用の追加設定
    session.stream = True
    
    return session