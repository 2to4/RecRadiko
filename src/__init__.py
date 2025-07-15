"""
RecRadiko - Radikoの録音・録画を自動化するアプリケーション

このパッケージはRadikoのストリーミング録音機能を提供します。

主要コンポーネント:
- auth: Radiko認証機能
- program_info: 番組情報取得・管理
- streaming: HLS/M3U8ストリーミング処理
- timefree_recorder: タイムフリー専用録音機能
- error_handler: 統一エラー処理
- cli: コマンドライン操作
"""

__version__ = "1.0.0"
__author__ = "Claude (Anthropic)"
__license__ = "MIT"

# 主要クラスのインポート
from .auth import RadikoAuthenticator, AuthInfo, LocationInfo, AuthenticationError
from .program_info import ProgramInfoManager, Station, Program, ProgramInfoError
from .streaming import StreamingManager, StreamSegment, StreamInfo, StreamingError
from .timefree_recorder import TimeFreeRecorder, TimeFreeError, RecordingResult
from .error_handler import ErrorHandler, RecRadikoError, ErrorSeverity, ErrorCategory
from .cli import RecRadikoCLI

__all__ = [
    # 認証関連
    'RadikoAuthenticator',
    'AuthInfo',
    'LocationInfo',
    'AuthenticationError',
    
    # 番組情報関連
    'ProgramInfoManager',
    'Station',
    'Program',
    'ProgramInfoError',
    
    # ストリーミング関連
    'StreamingManager',
    'StreamSegment',
    'StreamInfo',
    'StreamingError',
    
    
    # タイムフリー録音関連
    'TimeFreeRecorder',
    'TimeFreeError',
    'RecordingResult',
    
    # エラーハンドリング関連
    'ErrorHandler',
    'RecRadikoError',
    'ErrorSeverity',
    'ErrorCategory',
    
    # インターフェース関連
    'RecRadikoCLI',
]