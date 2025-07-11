#!/usr/bin/env python3
"""
RecRadiko - Radikoの録音・録画を自動化するアプリケーション

このファイルはRecRadikoのメインエントリーポイントです。
対話型モード専用アーキテクチャにより、すべての操作は対話型CLIで実行されます。

使用例:
    # 対話型モードで起動
    python RecRadiko.py
    
    # 設定ファイルを指定
    python RecRadiko.py --config custom_config.json
    
    # 詳細ログ出力
    python RecRadiko.py --verbose
    
    # デーモンモード（バックグラウンド実行）
    python RecRadiko.py --daemon

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
        
        # 対話型モード専用実行
        cli = RecRadikoCLI()
        exit_code = cli.run()
        sys.exit(exit_code)
    
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