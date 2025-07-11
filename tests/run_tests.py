#!/usr/bin/env python3
"""
RecRadiko テスト実行スクリプト

このスクリプトはRecRadikoの全モジュールのテストを実行します。

使用例:
    # 全テストを実行
    python tests/run_tests.py
    
    # 特定のモジュールのテストを実行
    python tests/run_tests.py --module auth
    
    # カバレッジレポート付きで実行
    python tests/run_tests.py --coverage
    
    # 詳細出力付きで実行
    python tests/run_tests.py --verbose
"""

import sys
import os
import unittest
import argparse
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """テスト実行管理クラス"""
    
    def __init__(self):
        self.test_modules = {
            'auth': 'test_auth',
            'program_info': 'test_program_info', 
            'streaming': 'test_streaming',
            'recording': 'test_recording',
            'error_handler': 'test_error_handler',
            'file_manager': 'test_file_manager',
            'scheduler': 'test_scheduler',
            'cli': 'test_cli',
            'daemon': 'test_daemon'
        }
    
    def discover_tests(self, module_name=None):
        """テストを検出"""
        if module_name and module_name in self.test_modules:
            # 特定のモジュールのテストのみ
            test_module = self.test_modules[module_name]
            return unittest.TestLoader().loadTestsFromName(f'tests.{test_module}')
        else:
            # 全テストを検出
            test_dir = Path(__file__).parent
            return unittest.TestLoader().discover(
                start_dir=str(test_dir),
                pattern='test_*.py',
                top_level_dir=str(project_root)
            )
    
    def run_tests(self, module_name=None, verbose=False, coverage=False):
        """テストを実行"""
        # カバレッジが要求された場合
        if coverage:
            try:
                import coverage
                cov = coverage.Coverage()
                cov.start()
            except ImportError:
                print("Warning: coverage パッケージがインストールされていません")
                print("pip install coverage でインストールしてください")
                coverage = False
        
        # テストスイートを作成
        test_suite = self.discover_tests(module_name)
        
        # テストランナーを設定
        verbosity = 2 if verbose else 1
        runner = unittest.TextTestRunner(
            verbosity=verbosity,
            stream=sys.stdout,
            buffer=True
        )
        
        print("=" * 70)
        if module_name:
            print(f"RecRadiko {module_name} モジュール テスト実行中...")
        else:
            print("RecRadiko 全モジュール テスト実行中...")
        print("=" * 70)
        
        # テスト実行
        result = runner.run(test_suite)
        
        # カバレッジレポート
        if coverage and 'cov' in locals():
            cov.stop()
            cov.save()
            
            print("\\n" + "=" * 70)
            print("カバレッジレポート:")
            print("=" * 70)
            
            cov.report(include="src/*")
            
            # HTMLレポート生成
            html_dir = project_root / "htmlcov"
            cov.html_report(directory=str(html_dir), include="src/*")
            print(f"\\nHTML カバレッジレポートが生成されました: {html_dir}/index.html")
        
        # 結果サマリー
        print("\\n" + "=" * 70)
        print("テスト結果サマリー:")
        print("=" * 70)
        print(f"実行テスト数: {result.testsRun}")
        print(f"失敗: {len(result.failures)}")
        print(f"エラー: {len(result.errors)}")
        print(f"スキップ: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
        
        if result.failures:
            print("\\n失敗したテスト:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("\\nエラーが発生したテスト:")
            for test, traceback in result.errors:
                print(f"  - {test}")
        
        # 成功判定
        success = len(result.failures) == 0 and len(result.errors) == 0
        
        if success:
            print("\\n✅ 全てのテストが成功しました！")
        else:
            print("\\n❌ テストに失敗したものがあります。")
        
        return success
    
    def list_modules(self):
        """利用可能なテストモジュール一覧を表示"""
        print("利用可能なテストモジュール:")
        for module_name in sorted(self.test_modules.keys()):
            print(f"  - {module_name}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="RecRadiko テスト実行スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 全テストを実行
  python tests/run_tests.py
  
  # 特定のモジュールのテストを実行
  python tests/run_tests.py --module auth
  
  # カバレッジレポート付きで実行
  python tests/run_tests.py --coverage
  
  # 詳細出力付きで実行
  python tests/run_tests.py --verbose
        """
    )
    
    parser.add_argument(
        '--module', '-m',
        help='特定のモジュールのテストのみ実行'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細な出力を表示'
    )
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='カバレッジレポートを生成'
    )
    parser.add_argument(
        '--list-modules', '-l',
        action='store_true',
        help='利用可能なテストモジュール一覧を表示'
    )
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.list_modules:
        runner.list_modules()
        return
    
    # モジュール名検証
    if args.module and args.module not in runner.test_modules:
        print(f"エラー: モジュール '{args.module}' が見つかりません")
        print("利用可能なモジュール:")
        runner.list_modules()
        sys.exit(1)
    
    try:
        success = runner.run_tests(
            module_name=args.module,
            verbose=args.verbose,
            coverage=args.coverage
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\\nテストが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"テスト実行中にエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()