#!/usr/bin/env python3
"""
RecRadiko - Radikoの録音・録画を自動化するアプリケーション

このファイルはRecRadikoのメインエントリーポイントです。
コマンドライン引数に基づいて適切なモジュールを呼び出します。

使用例:
    # 即座に録音
    python RecRadiko.py record TBS 60
    
    # 録音予約
    python RecRadiko.py schedule TBS "番組名" 2024-01-01T20:00 2024-01-01T21:00
    
    # デーモンモード
    python RecRadiko.py --daemon
    
    # 設定確認
    python RecRadiko.py show-config

作成者: Claude (Anthropic)
バージョン: 1.0.0
ライセンス: MIT License
"""

import sys
import os
from pathlib import Path

# プロジェクトルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # 必要なモジュールをインポート
    from src.cli import RecRadikoCLI
    from src.daemon import DaemonManager
    from src.error_handler import setup_error_handler, handle_error
    
except ImportError as e:
    print(f"モジュールインポートエラー: {e}")
    print("必要な依存関係がインストールされていない可能性があります。")
    print("pip install -r requirements.txt を実行してください。")
    sys.exit(1)


def main():
    """メインエントリーポイント"""
    try:
        # エラーハンドラーを初期化
        setup_error_handler(
            log_file="error.log",
            notification_enabled=True
        )
        
        # コマンドライン引数をチェック
        if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
            # デーモンモードで実行
            print("RecRadiko デーモンモードで開始...")
            
            daemon = DaemonManager()
            daemon.run()
        else:
            # CLIモードで実行
            cli = RecRadikoCLI()
            cli.run()
    
    except KeyboardInterrupt:
        print("\n操作がキャンセルされました")
        sys.exit(0)
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        
        # エラーハンドラーでエラーを記録
        try:
            handle_error(e, {'argv': sys.argv})
        except:
            pass  # エラーハンドラー自体がエラーの場合は無視
        
        sys.exit(1)


if __name__ == "__main__":
    main()