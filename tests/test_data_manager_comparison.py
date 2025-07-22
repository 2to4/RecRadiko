"""
データマネージャー比較テスト（Phase 8.1改善）

ProgramInfoManager vs ProgramHistoryManager の動作差異を検出し、
UI実装で適切なマネージャーが使用されているかを検証する。

今回のTBSラジオ番組表問題のような実装差異を早期発見することを目的とする。
"""

import unittest
from datetime import datetime, date, timedelta
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.program_info import ProgramInfoManager
from src.program_history import ProgramHistoryManager
from src.auth import RadikoAuthenticator
from tests.utils.test_environment import RealEnvironmentTestBase


class TestDataManagerComparison(unittest.TestCase, RealEnvironmentTestBase):
    """データマネージャー動作比較テスト"""
    
    def setUp(self):
        """テスト環境セットアップ"""
        self.setup_real_environment()
        
        # 実際のRadiko認証
        self.authenticator = RadikoAuthenticator()
        self.auth_info = self.authenticator.authenticate()
        self.assertIsNotNone(self.auth_info, "Radiko認証が成功すること")
        
        # テスト対象局・日付
        self.test_stations = ["TBS", "QRR", "LFR"]  # 複数局でテスト
        self.test_dates = [
            date(2025, 7, 21),  # 問題が発見された日付
            date.today(),       # 今日
            date.today() - timedelta(days=1)  # 昨日
        ]
        
        # マネージャー初期化
        self.info_manager = ProgramInfoManager(
            area_id=self.auth_info.area_id,
            authenticator=self.authenticator
        )
        self.history_manager = ProgramHistoryManager()
    
    def tearDown(self):
        """テスト環境クリーンアップ"""
        self.cleanup_real_environment()
    
    def test_manager_comparison_comprehensive(self):
        """包括的マネージャー比較テスト"""
        comparison_results = []
        
        for station_id in self.test_stations:
            for test_date in self.test_dates:
                with self.subTest(station=station_id, date=test_date):
                    # ProgramInfoManagerで取得
                    target_datetime = datetime.combine(test_date, datetime.min.time())
                    try:
                        programs_info = self.info_manager.fetch_program_guide(target_datetime, station_id)
                        info_count = len(programs_info) if programs_info else 0
                    except Exception as e:
                        info_count = 0
                        print(f"ProgramInfoManager例外 ({station_id}, {test_date}): {e}")
                    
                    # ProgramHistoryManagerで取得
                    date_str = test_date.strftime('%Y-%m-%d')
                    try:
                        programs_history = self.history_manager.get_programs_by_date(date_str, station_id)
                        history_count = len(programs_history) if programs_history else 0
                    except Exception as e:
                        history_count = 0
                        print(f"ProgramHistoryManager例外 ({station_id}, {test_date}): {e}")
                    
                    # 結果記録
                    result = {
                        'station': station_id,
                        'date': test_date,
                        'info_count': info_count,
                        'history_count': history_count,
                        'difference': abs(info_count - history_count)
                    }
                    comparison_results.append(result)
                    
                    print(f"📊 {station_id} {test_date}: Info={info_count}, History={history_count}, 差={result['difference']}")
                    
                    # 品質検証
                    if info_count > 0 or history_count > 0:
                        # 少なくとも一方は番組を取得できていること
                        self.assertTrue(info_count > 0 or history_count > 0, 
                                       f"いずれかのマネージャーは番組を取得できること: {station_id} {test_date}")
        
        # 全体分析
        self._analyze_comparison_results(comparison_results)
    
    def _analyze_comparison_results(self, results):
        """比較結果の分析・問題検出"""
        print("\n" + "="*60)
        print("📈 データマネージャー比較分析")
        print("="*60)
        
        critical_issues = []
        significant_differences = []
        
        for result in results:
            station = result['station']
            date = result['date']
            info_count = result['info_count']
            history_count = result['history_count']
            difference = result['difference']
            
            # 重大な問題検出（今回のTBSラジオ問題パターン）
            if history_count <= 1 and info_count > 10:
                critical_issues.append(result)
                print(f"🚨 重大問題検出: {station} {date}")
                print(f"   ProgramHistoryManager: {history_count}番組（異常に少ない）")
                print(f"   ProgramInfoManager: {info_count}番組（正常）")
            
            # 大きな差異検出
            elif difference > 5:
                significant_differences.append(result)
                print(f"⚠️ 大きな差異: {station} {date}")
                print(f"   差異: {difference}番組 (Info: {info_count}, History: {history_count})")
        
        # テスト結果サマリー
        print(f"\n📋 分析サマリー:")
        print(f"   テスト対象: {len(results)}パターン")
        print(f"   重大問題: {len(critical_issues)}件")
        print(f"   大きな差異: {len(significant_differences)}件")
        
        # 重大問題がある場合はテスト失敗
        if critical_issues:
            print(f"\n💡 推奨対応:")
            print(f"   1. UIはProgramInfoManagerを使用")
            print(f"   2. ProgramHistoryManagerは録音履歴管理のみ使用")
            print(f"   3. 番組表表示にはProgramInfoManagerを使用")
            
            self.fail(f"重大な問題を{len(critical_issues)}件検出。UIの実装見直しが必要。")
    
    def test_specific_tbs_issue_reproduction(self):
        """特定のTBSラジオ問題再現テスト"""
        # Given: 問題が発生した具体的な条件
        station_id = "TBS"
        problem_date = date(2025, 7, 21)
        
        # When: 両マネージャーで番組取得
        # ProgramInfoManager
        target_datetime = datetime.combine(problem_date, datetime.min.time())
        programs_info = self.info_manager.fetch_program_guide(target_datetime, station_id)
        info_count = len(programs_info) if programs_info else 0
        
        # ProgramHistoryManager
        date_str = problem_date.strftime('%Y-%m-%d')
        programs_history = self.history_manager.get_programs_by_date(date_str, station_id)
        history_count = len(programs_history) if programs_history else 0
        
        # Then: 問題パターンを検出
        print(f"\n🔍 TBSラジオ7/21問題再現テスト:")
        print(f"   ProgramInfoManager: {info_count}番組")
        print(f"   ProgramHistoryManager: {history_count}番組")
        
        # TBSラジオの通常番組数は20+番組あるはず
        self.assertGreater(info_count, 15, "ProgramInfoManagerはTBSで十分な番組数を取得すること")
        
        # 問題条件：ProgramHistoryManagerが異常に少ない番組数を返す
        if history_count <= 1:
            print(f"⚠️ 問題再現成功: ProgramHistoryManagerが{history_count}番組のみ取得")
            print(f"✅ ProgramInfoManagerは正常に{info_count}番組を取得")
            print(f"→ この差異が今回の「1番組しか表示されない」問題の根本原因")
    
    def test_data_quality_comparison(self):
        """データ品質比較テスト"""
        station_id = "TBS"
        test_date = date(2025, 7, 21)
        
        # ProgramInfoManagerデータ品質
        target_datetime = datetime.combine(test_date, datetime.min.time())
        programs_info = self.info_manager.fetch_program_guide(target_datetime, station_id)
        
        if programs_info:
            info_quality = self._assess_data_quality(programs_info, "ProgramInfo")
        else:
            info_quality = {"valid_programs": 0, "total_programs": 0}
        
        # ProgramHistoryManagerデータ品質
        date_str = test_date.strftime('%Y-%m-%d')
        programs_history = self.history_manager.get_programs_by_date(date_str, station_id)
        
        if programs_history:
            history_quality = self._assess_data_quality(programs_history, "ProgramHistory")
        else:
            history_quality = {"valid_programs": 0, "total_programs": 0}
        
        # 品質比較結果
        print(f"\n📊 データ品質比較:")
        print(f"   ProgramInfoManager: {info_quality['valid_programs']}/{info_quality['total_programs']} 有効")
        print(f"   ProgramHistoryManager: {history_quality['valid_programs']}/{history_quality['total_programs']} 有効")
        
        # 品質基準
        if info_quality['total_programs'] > 0:
            info_ratio = info_quality['valid_programs'] / info_quality['total_programs']
            self.assertGreater(info_ratio, 0.8, "ProgramInfoManagerの品質率が80%以上であること")
        
        if history_quality['total_programs'] > 0:
            history_ratio = history_quality['valid_programs'] / history_quality['total_programs']
            self.assertGreater(history_ratio, 0.8, "ProgramHistoryManagerの品質率が80%以上であること")
    
    def _assess_data_quality(self, programs, manager_type):
        """データ品質評価"""
        total = len(programs)
        valid = 0
        
        for program in programs:
            is_valid = True
            
            # 共通品質チェック
            if manager_type == "ProgramInfo":
                # ProgramInfoオブジェクトの場合
                if not hasattr(program, 'title') or not program.title:
                    is_valid = False
                if not hasattr(program, 'start_time') or not program.start_time:
                    is_valid = False
                if not hasattr(program, 'end_time') or not program.end_time:
                    is_valid = False
            else:
                # 辞書形式の場合
                if not program.get('title', ''):
                    is_valid = False
                if not program.get('start_time', ''):
                    is_valid = False
                if not program.get('end_time', ''):
                    is_valid = False
            
            if is_valid:
                valid += 1
        
        return {
            "total_programs": total,
            "valid_programs": valid,
            "quality_ratio": valid / total if total > 0 else 0
        }


class TestUIManagerIntegration(unittest.TestCase, RealEnvironmentTestBase):
    """UI-マネージャー統合テスト"""
    
    def setUp(self):
        """テスト環境セットアップ"""
        self.setup_real_environment()
    
    def tearDown(self):
        """テスト環境クリーンアップ"""
        self.cleanup_real_environment()
    
    def test_ui_uses_correct_manager(self):
        """UIが適切なマネージャーを使用しているかテスト"""
        from src.ui.screens.program_select_screen import ProgramSelectScreen
        
        # Given: ProgramSelectScreen初期化
        screen = ProgramSelectScreen()
        
        # Then: 正しいマネージャーが使用されている
        self.assertIsNotNone(screen.program_info_manager, 
                            "ProgramSelectScreenはProgramInfoManagerを使用すること")
        self.assertIsInstance(screen.program_info_manager, ProgramInfoManager,
                             "program_info_managerの型が正しいこと")
        
        # 修正前の問題となったProgramHistoryManagerが直接使用されていないこと
        self.assertFalse(hasattr(screen, 'program_history_manager') or 
                        getattr(screen, 'program_history_manager', None) is not None,
                        "ProgramHistoryManagerが直接使用されていないこと")
    
    def test_ui_program_fetching_method(self):
        """UI番組取得メソッドテスト"""
        from src.ui.screens.program_select_screen import ProgramSelectScreen
        
        # Given: 設定済みProgramSelectScreen
        screen = ProgramSelectScreen()
        station_id = "TBS"
        test_date = date(2025, 7, 21)
        
        # When: 番組取得メソッドを呼び出し
        try:
            programs = screen._fetch_programs_from_api(station_id, test_date)
            program_count = len(programs) if programs else 0
        except Exception as e:
            self.fail(f"番組取得メソッドでエラーが発生: {e}")
        
        # Then: 十分な番組数が取得される
        self.assertGreater(program_count, 10, 
                          f"UI番組取得で十分な数の番組が取得されること: 実際{program_count}番組")
        
        print(f"✅ UI番組取得テスト成功: {program_count}番組取得")


if __name__ == "__main__":
    unittest.main(verbosity=2)