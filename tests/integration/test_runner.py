"""
タイムフリー専用結合テスト実行用テストランナー

このモジュールは、RecRadikoのタイムフリー専用結合テストを効率的に実行するためのテストランナーです。
- タイムフリー統合テストの実行順序制御
- テスト環境のセットアップ・クリーンアップ
- 結果レポートの生成
"""

import unittest
import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

# タイムフリー専用テストモジュールのインポート
from . import test_timefree_integration


class IntegrationTestRunner:
    """結合テストランナー"""
    
    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_all_tests(self, verbosity: int = 2) -> Dict[str, Any]:
        """全結合テストの実行"""
        print("🚀 RecRadiko 結合テスト実行開始")
        print("=" * 60)
        
        self.start_time = datetime.now()
        
        # タイムフリー専用テストスイートの定義
        test_suites = [
            ("タイムフリー統合テスト", test_timefree_integration),
        ]
        
        total_tests = 0
        total_failures = 0
        total_errors = 0
        suite_results = []
        
        for suite_name, test_module in test_suites:
            print(f"\n📋 {suite_name} 実行中...")
            print("-" * 40)
            
            # テストスイートの作成
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(test_module)
            
            # テスト実行
            runner = unittest.TextTestRunner(
                verbosity=verbosity,
                stream=sys.stdout,
                buffer=True
            )
            
            result = runner.run(suite)
            
            # 結果の集計
            suite_result = {
                'name': suite_name,
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100 if result.testsRun > 0 else 0,
                'duration': 0,  # 実際の実装では時間測定
                'failure_details': [str(failure[1]) for failure in result.failures],
                'error_details': [str(error[1]) for error in result.errors]
            }
            
            suite_results.append(suite_result)
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            
            # スイート結果の表示
            if result.wasSuccessful():
                print(f"✅ {suite_name}: 全 {result.testsRun} テスト成功")
            else:
                print(f"❌ {suite_name}: {result.testsRun} テスト中 {len(result.failures)} 失敗, {len(result.errors)} エラー")
        
        self.end_time = datetime.now()
        
        # 全体結果の集計
        overall_result = {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': (self.end_time - self.start_time).total_seconds(),
            'total_tests': total_tests,
            'total_failures': total_failures,
            'total_errors': total_errors,
            'success_rate': (total_tests - total_failures - total_errors) / total_tests * 100 if total_tests > 0 else 0,
            'suite_results': suite_results
        }
        
        self.results = overall_result
        
        # 結果の表示
        self._print_summary()
        
        # レポート生成
        self._generate_report()
        
        return overall_result
    
    def run_specific_suite(self, suite_name: str, verbosity: int = 2) -> Dict[str, Any]:
        """特定の結合テストスイートの実行"""
        print(f"🎯 {suite_name} 実行開始")
        print("=" * 40)
        
        # スイート名からモジュールをマッピング
        suite_mapping = {
            'e2e': test_e2e_recording,
            'scheduling': test_scheduling_integration,
            'cli': test_cli_integration,
        }
        
        if suite_name not in suite_mapping:
            raise ValueError(f"不明なテストスイート: {suite_name}")
        
        test_module = suite_mapping[suite_name]
        
        # テストスイートの作成と実行
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_module)
        
        runner = unittest.TextTestRunner(
            verbosity=verbosity,
            stream=sys.stdout,
            buffer=True
        )
        
        result = runner.run(suite)
        
        # 結果の集計
        suite_result = {
            'name': suite_name,
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success_rate': (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100 if result.testsRun > 0 else 0,
            'failure_details': [str(failure[1]) for failure in result.failures],
            'error_details': [str(error[1]) for error in result.errors]
        }
        
        return suite_result
    
    def _print_summary(self):
        """結果サマリーの表示"""
        print("\n" + "=" * 60)
        print("📊 結合テスト実行結果サマリー")
        print("=" * 60)
        
        print(f"実行時間: {self.results['duration_seconds']:.2f}秒")
        print(f"総テスト数: {self.results['total_tests']}")
        print(f"成功率: {self.results['success_rate']:.1f}%")
        print(f"失敗: {self.results['total_failures']}")
        print(f"エラー: {self.results['total_errors']}")
        
        print("\n📋 スイート別結果:")
        print("-" * 40)
        
        for suite in self.results['suite_results']:
            status = "✅" if suite['failures'] == 0 and suite['errors'] == 0 else "❌"
            print(f"{status} {suite['name']}: {suite['success_rate']:.1f}% ({suite['tests_run']} テスト)")
        
        # 失敗・エラーの詳細表示
        if self.results['total_failures'] > 0 or self.results['total_errors'] > 0:
            print("\n🔍 失敗・エラー詳細:")
            print("-" * 40)
            
            for suite in self.results['suite_results']:
                if suite['failures'] > 0 or suite['errors'] > 0:
                    print(f"\n{suite['name']}:")
                    
                    for failure in suite['failure_details']:
                        print(f"  ❌ 失敗: {failure[:100]}...")
                    
                    for error in suite['error_details']:
                        print(f"  💥 エラー: {error[:100]}...")
    
    def _generate_report(self):
        """結果レポートの生成"""
        # JSON形式のレポート
        report_file = self.output_dir / f"integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 レポート生成: {report_file}")
        
        # HTML形式のレポート（簡易版）
        html_report = self._generate_html_report()
        html_file = self.output_dir / f"integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        print(f"📄 HTMLレポート生成: {html_file}")
    
    def _generate_html_report(self) -> str:
        """HTMLレポートの生成"""
        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RecRadiko 結合テストレポート</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .suite {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        .success {{ background-color: #d4edda; }}
        .failure {{ background-color: #f8d7da; }}
        .details {{ margin-top: 10px; font-size: 0.9em; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 RecRadiko 結合テストレポート</h1>
        <p>実行日時: {self.results['start_time']}</p>
        <p>実行時間: {self.results['duration_seconds']:.2f}秒</p>
    </div>
    
    <div class="summary">
        <h2>📊 実行結果サマリー</h2>
        <ul>
            <li>総テスト数: {self.results['total_tests']}</li>
            <li>成功率: {self.results['success_rate']:.1f}%</li>
            <li>失敗: {self.results['total_failures']}</li>
            <li>エラー: {self.results['total_errors']}</li>
        </ul>
    </div>
    
    <div class="suites">
        <h2>📋 スイート別結果</h2>
"""
        
        for suite in self.results['suite_results']:
            status_class = "success" if suite['failures'] == 0 and suite['errors'] == 0 else "failure"
            status_icon = "✅" if suite['failures'] == 0 and suite['errors'] == 0 else "❌"
            
            html += f"""
        <div class="suite {status_class}">
            <h3>{status_icon} {suite['name']}</h3>
            <p>テスト数: {suite['tests_run']}, 成功率: {suite['success_rate']:.1f}%</p>
            <p>失敗: {suite['failures']}, エラー: {suite['errors']}</p>
"""
            
            if suite['failure_details'] or suite['error_details']:
                html += '<div class="details">'
                
                for failure in suite['failure_details']:
                    html += f'<p>❌ 失敗: {failure[:200]}...</p>'
                
                for error in suite['error_details']:
                    html += f'<p>💥 エラー: {error[:200]}...</p>'
                
                html += '</div>'
            
            html += '</div>'
        
        html += """
    </div>
</body>
</html>
"""
        
        return html


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RecRadiko 結合テスト実行')
    parser.add_argument('--suite', choices=['e2e', 'scheduling', 'cli'], 
                       help='実行する特定のテストスイート')
    parser.add_argument('--verbosity', type=int, default=2, choices=[0, 1, 2],
                       help='出力レベル (0: 最小, 1: 通常, 2: 詳細)')
    parser.add_argument('--output-dir', default='test_reports',
                       help='レポート出力ディレクトリ')
    
    args = parser.parse_args()
    
    # テストランナーの作成
    runner = IntegrationTestRunner(output_dir=args.output_dir)
    
    try:
        if args.suite:
            # 特定スイートの実行
            result = runner.run_specific_suite(args.suite, args.verbosity)
            success = result['failures'] == 0 and result['errors'] == 0
        else:
            # 全テストの実行
            result = runner.run_all_tests(args.verbosity)
            success = result['total_failures'] == 0 and result['total_errors'] == 0
        
        # 終了コード
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        sys.exit(2)


if __name__ == '__main__':
    main()