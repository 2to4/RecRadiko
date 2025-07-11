"""
RecRadiko テストパッケージ

このパッケージはRecRadikoの全モジュールに対する単体テストを提供します。

テスト構造:
- test_auth.py: 認証モジュールのテスト
- test_program_info.py: 番組情報モジュールのテスト
- test_streaming.py: ストリーミングモジュールのテスト
- test_recording.py: 録音機能モジュールのテスト
- test_file_manager.py: ファイル管理モジュールのテスト
- test_scheduler.py: スケジューリングモジュールのテスト
- test_error_handler.py: エラーハンドリングモジュールのテスト
- test_cli.py: CLIインターフェースのテスト
- test_daemon.py: デーモンモードのテスト
"""

import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

__version__ = "1.0.0"