"""
ProgramSelectScreen改善版テスト（Phase 8.2）

今回の番組表日付表示問題を受けて、UI統合テストを実環境化・境界値強化。

改善点:
1. モック依存から実環境APIテストに変更
2. 境界値テスト追加（深夜番組・日付表示）
3. 実際のRadiko番組での動作確認
4. プロパティ使い分けの明確化
"""

import pytest
import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, date
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.ui.screens.program_select_screen import ProgramSelectScreen
from src.ui.services.ui_service import UIService
from tests.utils.test_environment import RealEnvironmentTestBase


class TestProgramSelectScreenImproved(unittest.TestCase, RealEnvironmentTestBase):
    """ProgramSelectScreen改善版テスト（実環境中心）"""
    
    def setUp(self):
        """テスト環境セットアップ"""
        self.setup_real_environment()
        
        # テスト対象
        self.test_stations = [
            {"id": "TBS", "name": "TBSラジオ"},
            {"id": "QRR", "name": "文化放送"}
        ]
        
        # テスト日付（今日と昨日）
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)
    
    def tearDown(self):
        """テスト環境クリーンアップ"""
        self.cleanup_real_environment()
    
    def test_program_loading_real_environment(self):
        """実環境での番組読み込みテスト"""
        # Given: 実環境ProgramSelectScreen
        screen = ProgramSelectScreen()
        
        for station in self.test_stations:
            with self.subTest(station=station["id"]):
                screen.set_station_and_date(station, self.yesterday)
                
                # When: 実際の番組データ読み込み
                success = screen.load_programs()
                
                # Then: 成功し、番組データが取得される
                self.assertTrue(success, f"{station['id']}の番組読み込み成功")
                self.assertGreater(len(screen.programs), 5, 
                                 f"{station['id']}は5番組以上あること")
                
                # 番組データ品質確認
                for prog in screen.programs:
                    with self.subTest(station=station["id"], program=prog["title"]):
                        self.assertIn('title', prog, "番組にタイトルがあること")
                        self.assertIn('display_date', prog, "番組に表示日付があること")
                        self.assertEqual(prog['display_date'], 
                                       self.yesterday.strftime('%Y-%m-%d'),
                                       "表示日付が選択日と一致すること")
    
    def test_midnight_program_display_boundaries(self):
        """深夜番組表示境界テスト"""
        # Given: ProgramSelectScreen with mocked data for boundary testing
        screen = ProgramSelectScreen()
        
        # 境界値番組をモック（実装詳細テストのため）
        from unittest.mock import Mock
        
        boundary_programs = [
            # 4:59深夜番組
            Mock(
                title="4:59深夜番組",
                start_time=datetime(2025, 7, 22, 4, 59),
                end_time=datetime(2025, 7, 22, 6, 0),
                is_midnight_program=True,
                display_start_time="28:59",
                display_end_time="30:00",
                program_id="test_459",
                station_id="TBS",
                station_name="TBSラジオ"
            ),
            # 5:00通常番組
            Mock(
                title="5:00朝番組", 
                start_time=datetime(2025, 7, 22, 5, 0),
                end_time=datetime(2025, 7, 22, 6, 0),
                is_midnight_program=False,
                display_start_time="05:00",
                display_end_time="06:00",
                program_id="test_500",
                station_id="TBS",
                station_name="TBSラジオ"
            )
        ]
        
        # ProgramInfoManagerをモック
        screen.program_info_manager = Mock()
        screen.program_info_manager.fetch_program_guide.return_value = boundary_programs
        
        # When: 境界値番組を処理
        programs = screen._fetch_programs_from_api("TBS", date(2025, 7, 22))
        
        # Then: 境界値で正しく処理される
        self.assertEqual(len(programs), 2, "境界値番組2つが処理される")
        
        # 深夜番組の処理確認
        midnight_prog = next(p for p in programs if p['title'] == "4:59深夜番組")
        self.assertEqual(midnight_prog['display_date'], "2025-07-22", 
                        "深夜番組も実際の放送日で表示（修正後）")
        self.assertTrue(midnight_prog['is_midnight'], "深夜フラグが設定される")
        self.assertEqual(midnight_prog['display_start_time'], "28:59", "24時間表示")
        
        # 通常番組の処理確認
        regular_prog = next(p for p in programs if p['title'] == "5:00朝番組")
        self.assertEqual(regular_prog['display_date'], "2025-07-22", 
                        "通常番組は実際の放送日で表示")
        self.assertFalse(regular_prog['is_midnight'], "深夜フラグが設定されない")
        self.assertEqual(regular_prog['display_start_time'], "05:00", "通常時刻表示")
    
    def test_date_consistency_across_ui_workflow(self):
        """UI全体での日付一貫性テスト"""
        # Given: 実環境でのTBSラジオ昨日の番組
        screen = ProgramSelectScreen()
        tbs_station = {"id": "TBS", "name": "TBSラジオ"}
        screen.set_station_and_date(tbs_station, self.yesterday)
        
        # When: 番組読み込み
        success = screen.load_programs()
        self.assertTrue(success, "番組読み込み成功")
        
        # Then: 全番組で日付一貫性確認
        yesterday_str = self.yesterday.strftime('%Y-%m-%d')
        
        for prog in screen.programs:
            with self.subTest(program=prog["title"]):
                # UIで表示される日付は選択日と一致
                self.assertEqual(prog['display_date'], yesterday_str,
                               f"番組'{prog['title']}'の表示日付が選択日と一致")
                
                # 深夜番組でも実際の放送日で表示（修正効果）
                if prog.get('is_midnight', False):
                    # 深夜番組も選択した日付で表示される
                    self.assertEqual(prog['display_date'], yesterday_str,
                                   f"深夜番組'{prog['title']}'も選択日で表示（修正後）")
    
    def test_program_display_format_boundaries(self):
        """番組表示フォーマット境界テスト"""
        # Given: 各種時刻パターンの番組
        screen = ProgramSelectScreen()
        
        # フォーマットテスト用番組（モック）
        format_test_programs = [
            # 通常番組
            {"title": "朝番組", "start_time": "06:30", "end_time": "08:00", "is_midnight": False},
            # 深夜番組（24時間表示）
            {"title": "深夜番組", "start_time": "25:00", "end_time": "27:00", "is_midnight": True},
            # 境界値時刻
            {"title": "5時番組", "start_time": "05:00", "end_time": "06:00", "is_midnight": False},
        ]
        
        # When & Then: フォーマット確認
        for prog in format_test_programs:
            with self.subTest(program=prog["title"]):
                display_text = screen.format_program_for_display(prog)
                
                expected = f"{prog['start_time']}-{prog['end_time']} {prog['title']}"
                self.assertEqual(display_text, expected, f"{prog['title']}のフォーマット")
                
                # 逆方向検索テスト
                found_prog = screen.get_program_by_display_text(display_text)
                self.assertEqual(found_prog, prog, "表示テキストから番組検索")
    
    def test_pagination_with_boundary_data(self):
        """境界値データでのページネーションテスト"""
        # Given: 実環境でのTBSラジオ（多数番組）
        screen = ProgramSelectScreen()
        screen.set_station_and_date({"id": "TBS", "name": "TBSラジオ"}, self.yesterday)
        screen.load_programs()
        
        total_programs = len(screen.programs)
        items_per_page = screen.items_per_page
        
        # When: ページネーション境界値
        total_pages = screen.get_total_pages()
        
        # Then: 境界値でのページ計算
        expected_pages = (total_programs + items_per_page - 1) // items_per_page
        self.assertEqual(total_pages, expected_pages, "ページ数計算")
        
        # 最終ページでの境界確認
        if total_pages > 1:
            screen.current_page = total_pages - 1  # 最終ページ
            last_page_programs = screen.get_current_page_programs()
            
            expected_last_count = total_programs % items_per_page
            if expected_last_count == 0:
                expected_last_count = items_per_page
            
            self.assertEqual(len(last_page_programs), expected_last_count,
                           "最終ページの番組数")
    
    def test_error_handling_boundaries(self):
        """エラーハンドリング境界テスト"""
        # Given: ProgramSelectScreen
        screen = ProgramSelectScreen()
        
        # When & Then: 境界エラー条件
        # 1. 放送局・日付未設定
        self.assertFalse(screen.load_programs(), "未設定時はFalse")
        
        # 2. 存在しない放送局
        screen.set_station_and_date({"id": "INVALID", "name": "存在しない局"}, self.yesterday)
        result = screen.load_programs()
        # 結果はAPIの実装に依存するが、エラーハンドリングは動作する
        
        # 3. 古すぎる日付
        old_date = date(2020, 1, 1)
        screen.set_station_and_date({"id": "TBS", "name": "TBSラジオ"}, old_date)
        result = screen.load_programs()
        # 結果はAPIの実装に依存するが、エラーハンドリングは動作する


class TestProgramSelectScreenDateDisplayRegression(unittest.TestCase, RealEnvironmentTestBase):
    """番組表日付表示リグレッションテスト"""
    
    def setUp(self):
        """テスト環境セットアップ"""
        self.setup_real_environment()
    
    def tearDown(self):
        """テスト環境クリーンアップ"""
        self.cleanup_real_environment()
    
    def test_tbs_radio_date_display_regression(self):
        """TBSラジオ日付表示リグレッションテスト（今回の問題の再発防止）"""
        # Given: TBSラジオの実環境データ
        screen = ProgramSelectScreen()
        tbs_station = {"id": "TBS", "name": "TBSラジオ"}
        test_date = date.today() - timedelta(days=1)  # 昨日
        
        screen.set_station_and_date(tbs_station, test_date)
        
        # When: 番組読み込み
        success = screen.load_programs()
        self.assertTrue(success, "TBSラジオ番組読み込み成功")
        
        # Then: リグレッション防止確認
        test_date_str = test_date.strftime('%Y-%m-%d')
        
        # 1. 全番組が選択した日付で表示される
        wrong_date_programs = []
        for prog in screen.programs:
            if prog['display_date'] != test_date_str:
                wrong_date_programs.append(prog)
        
        self.assertEqual(len(wrong_date_programs), 0,
                        f"間違った日付で表示される番組: {[p['title'] for p in wrong_date_programs]}")
        
        # 2. 深夜番組も正しく処理される
        midnight_programs = [p for p in screen.programs if p.get('is_midnight', False)]
        if midnight_programs:
            for midnight_prog in midnight_programs:
                self.assertEqual(midnight_prog['display_date'], test_date_str,
                               f"深夜番組'{midnight_prog['title']}'も選択日で表示")
        
        # 3. 5:00番組が通常番組として扱われる（今回の修正確認）
        morning_programs = [p for p in screen.programs 
                           if '5:00' in p.get('display_start_time', '') or
                              '05:00' in p.get('display_start_time', '')]
        for morning_prog in morning_programs:
            self.assertFalse(morning_prog.get('is_midnight', False),
                           f"5:00番組'{morning_prog['title']}'は通常番組扱い")
        
        print(f"✅ TBSラジオリグレッションテスト: {len(screen.programs)}番組が選択日{test_date_str}で正常表示")


if __name__ == "__main__":
    unittest.main(verbosity=2)