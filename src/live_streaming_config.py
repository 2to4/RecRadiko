"""
ライブストリーミング設定モジュール

ライブストリーミング録音に関する設定パラメータを定義します。
"""

from typing import Dict, Any


# ライブストリーミング録音設定
LIVE_RECORDING_CONFIG: Dict[str, Any] = {
    # プレイリスト監視設定
    'playlist_update_interval': 15,      # プレイリスト更新間隔（秒）
    'playlist_fetch_timeout': 10,        # プレイリスト取得タイムアウト
    'playlist_retry_attempts': 5,        # プレイリスト取得リトライ回数
    'playlist_retry_delay': 2,           # リトライ間隔（秒）
    
    # セグメントダウンロード設定
    'max_concurrent_downloads': 3,       # 並行ダウンロード数
    'segment_download_timeout': 10,      # セグメントダウンロードタイムアウト
    'segment_retry_attempts': 3,         # セグメントリトライ回数
    'segment_buffer_size': 5,            # バッファセグメント数
    
    # メモリ管理設定
    'segment_history_size': 100,         # セグメント履歴保持数
    'memory_cleanup_interval': 300,      # メモリクリーンアップ間隔（秒）
    
    # パフォーマンス設定
    'async_timeout': 30,                 # 非同期処理タイムアウト
    'connection_pool_size': 10,          # HTTP接続プールサイズ
    
    # ログ設定
    'enable_debug_logging': False,       # デバッグログ有効化
    'log_segment_details': False,        # セグメント詳細ログ
    
    # ファイル書き込み設定
    'write_buffer_size': 1048576,        # 書き込みバッファサイズ（1MB）
    'sync_interval': 30,                 # ファイル同期間隔（秒）
}


def get_live_recording_config(custom_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    ライブストリーミング録音設定を取得
    
    Args:
        custom_config: カスタム設定（省略可能）
        
    Returns:
        Dict[str, Any]: 統合された設定辞書
    """
    config = LIVE_RECORDING_CONFIG.copy()
    
    if custom_config:
        config.update(custom_config)
    
    return config


def validate_live_recording_config(config: Dict[str, Any]) -> bool:
    """
    ライブストリーミング録音設定を検証
    
    Args:
        config: 検証する設定辞書
        
    Returns:
        bool: 設定が有効な場合True
    """
    required_keys = [
        'playlist_update_interval',
        'max_concurrent_downloads',
        'segment_download_timeout'
    ]
    
    # 必須キーの存在確認
    for key in required_keys:
        if key not in config:
            return False
    
    # 値の範囲確認
    if config['playlist_update_interval'] < 5 or config['playlist_update_interval'] > 60:
        return False
    
    if config['max_concurrent_downloads'] < 1 or config['max_concurrent_downloads'] > 10:
        return False
    
    if config['segment_download_timeout'] < 5 or config['segment_download_timeout'] > 60:
        return False
    
    return True


# 環境別設定
DEVELOPMENT_CONFIG = {
    'playlist_update_interval': 5,       # 開発時は短間隔
    'enable_debug_logging': True,
    'log_segment_details': True,
}

PRODUCTION_CONFIG = {
    'playlist_update_interval': 15,      # 本番は標準間隔
    'enable_debug_logging': False,
    'log_segment_details': False,
}

TEST_CONFIG = {
    'playlist_update_interval': 1,       # テスト時は最短間隔
    'max_concurrent_downloads': 2,       # テスト時は軽負荷
    'segment_download_timeout': 5,       # テスト時は短タイムアウト
    'enable_debug_logging': True,
}


def get_config_for_environment(environment: str = 'production') -> Dict[str, Any]:
    """
    環境に応じた設定を取得
    
    Args:
        environment: 環境名 ('development', 'production', 'test')
        
    Returns:
        Dict[str, Any]: 環境に応じた設定
    """
    base_config = LIVE_RECORDING_CONFIG.copy()
    
    if environment == 'development':
        base_config.update(DEVELOPMENT_CONFIG)
    elif environment == 'production':
        base_config.update(PRODUCTION_CONFIG)
    elif environment == 'test':
        base_config.update(TEST_CONFIG)
    
    return base_config