"""
ProgramSelectScreen 実環境テスト（Phase 8.1改善）

モック依存を最小化し、実際のRadiko APIとデータマネージャーを使用。
今回発見されたProgramHistoryManager vs ProgramInfoManager問題の検出を目的とする。
"""

import pytest
import unittest
from unittest.mock import patch, Mock
from datetime import datetime, date
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.ui.screens.program_select_screen import ProgramSelectScreen
from src.program_history import ProgramHistoryManager
from src.program_info import ProgramInfoManager
from src.auth import RadikoAuthenticator
from tests.utils.test_environment import RealEnvironmentTestBase


class TestProgramSelectScreenRealEnvironment(unittest.TestCase, RealEnvironmentTestBase):
    """ProgramSelectScreen実環境統合テスト"""
    
    def setUp(self):
        """テスト環境セットアップ"""
        self.setup_real_environment()
        
        # 実際のRadiko認証を使用
        self.authenticator = RadikoAuthenticator()
        
        # テスト対象駅・日付
        self.test_station = {"id": "TBS", "name": "TBSラジオ"}
        self.test_date = date(2025, 7, 21)  # 問題が発見された日付
    
    def tearDown(self):
        """テスト環境クリーンアップ"""
        self.cleanup_real_environment()
    
    def test_program_select_screen_real_initialization(self):
        """ProgramSelectScreen実環境初期化テスト"""
        # Given: 実環境でのProgramSelectScreen作成
        screen = ProgramSelectScreen()
        
        # Then: 正常に初期化される
        self.assertIsNotNone(screen)
        self.assertEqual(screen.title, "番組選択")
        
        # ProgramInfoManagerが正常に初期化される
        self.assertIsNotNone(screen.program_info_manager)
        self.assertIsNotNone(screen.authenticator)
    
    def test_program_select_screen_real_program_loading(self):
        """実環境での番組読み込みテスト（重要：実際の問題検出）"""
        # Given: 実環境ProgramSelectScreen
        screen = ProgramSelectScreen()
        screen.set_station_and_date(self.test_station, self.test_date)
        
        # When: 実際の番組データを読み込み
        success = screen.load_programs()
        
        # Then: 成功し、十分な数の番組が取得される
        self.assertTrue(success, "番組読み込みが成功すること")
        self.assertGreater(len(screen.programs), 10, 
                          f"TBSラジオ7/21は10番組以上あるはず。実際: {len(screen.programs)}個")
        
        # 番組データの品質確認
        for i, program in enumerate(screen.programs):
            with self.subTest(f"番組{i+1}"):
                self.assertIn('title', program, "番組にタイトルがあること")
                self.assertIn('start_time', program, "番組に開始時刻があること")
                self.assertIn('end_time', program, "番組に終了時刻があること")
                self.assertNotEqual(program['title'], '', "番組タイトルが空でないこと")
    
    def test_program_managers_comparison_in_ui(self):
        """UI内でのデータマネージャー比較テスト（問題検出）"""
        # Given: 認証情報取得
        auth_info = self.authenticator.authenticate()
        self.assertIsNotNone(auth_info, "認証が成功すること")
        
        # ProgramInfoManager（修正後UI使用）
        program_info_manager = ProgramInfoManager(
            area_id=auth_info.area_id,
            authenticator=self.authenticator
        )
        
        # ProgramHistoryManager（修正前UI使用）
        program_history_manager = ProgramHistoryManager()
        
        # When: 同じ日付・放送局で番組取得
        target_datetime = datetime.combine(self.test_date, datetime.min.time())
        
        # ProgramInfoManagerから取得
        programs_info = program_info_manager.fetch_program_guide(target_datetime, self.test_station["id"])
        info_count = len(programs_info) if programs_info else 0
        
        # ProgramHistoryManagerから取得
        date_str = self.test_date.strftime('%Y-%m-%d')
        programs_history = program_history_manager.get_programs_by_date(date_str, self.test_station["id"])
        history_count = len(programs_history) if programs_history else 0
        
        # Then: データマネージャー間の差異を検出
        print(f"ProgramInfoManager番組数: {info_count}")
        print(f"ProgramHistoryManager番組数: {history_count}")
        
        # 重要: この差異が今回の問題の根本原因
        self.assertGreater(info_count, 10, "ProgramInfoManagerは十分な番組数を取得すること")
        
        if history_count <= 1 and info_count > 10:
            print("⚠️ 問題検出: ProgramHistoryManagerは番組を正常に取得できない")
            print("✅ 修正: ProgramSelectScreenはProgramInfoManagerを使用すべき")
        
        # この条件が今回発見された問題
        self.assertNotEqual(info_count, history_count, 
                           "データマネージャー間で取得数が異なる問題を検出")
    
    def test_program_select_screen_real_display_content(self):
        """実環境での表示コンテンツテスト"""
        # Given: 実際の番組データが読み込まれたProgramSelectScreen
        screen = ProgramSelectScreen()
        screen.set_station_and_date(self.test_station, self.test_date)
        
        # 実際の番組データを読み込み
        success = screen.load_programs()
        self.assertTrue(success, "番組読み込みが成功すること")
        
        # UIServiceをモック（表示部分のみ）
        with patch.object(screen, 'ui_service') as mock_ui:
            # When: 表示コンテンツを生成
            screen.display_content()
            
            # Then: 実際の番組数に応じた表示が行われる
            mock_ui.set_menu_items.assert_called_once()
            call_args = mock_ui.set_menu_items.call_args[0][0]
            
            # 実際に取得された番組数と表示項目数が一致
            displayed_programs = [item for item in call_args if not item.startswith('═')]
            self.assertGreater(len(displayed_programs), 10, 
                              "表示される番組数が十分であること")
    
    def test_program_format_consistency(self):
        """番組フォーマット一貫性テスト"""
        # Given: 実環境で番組取得
        screen = ProgramSelectScreen()
        screen.set_station_and_date(self.test_station, self.test_date)
        screen.load_programs()
        
        # When: 各番組をフォーマット
        for i, program in enumerate(screen.programs):
            with self.subTest(f"番組{i+1}: {program.get('title', 'N/A')}"):
                # Then: フォーマットが正常
                display_text = screen.format_program_for_display(program)
                
                # フォーマット要件確認
                self.assertIsNotNone(display_text, "表示テキストが生成されること")
                self.assertNotEqual(display_text, "", "表示テキストが空でないこと")
                
                # 時刻-番組名形式確認
                self.assertIn('-', display_text, "時刻区切りがあること")
                
                # 逆方向検索テスト
                found_program = screen.get_program_by_display_text(display_text)
                self.assertEqual(found_program, program, "表示テキストから番組が検索できること")
    
    def test_pagination_with_real_data(self):
        """実データでのページネーション機能テスト"""
        # Given: 実環境で大量番組データ取得
        screen = ProgramSelectScreen()
        screen.set_station_and_date(self.test_station, self.test_date)
        screen.load_programs()
        
        total_programs = len(screen.programs)
        items_per_page = screen.items_per_page
        
        # When: ページネーション計算
        total_pages = screen.get_total_pages()
        
        # Then: 正確なページ数計算
        expected_pages = (total_programs + items_per_page - 1) // items_per_page
        self.assertEqual(total_pages, expected_pages, "ページ数が正確に計算されること")
        
        # 各ページの内容確認
        for page in range(total_pages):
            screen.current_page = page
            page_programs = screen.get_current_page_programs()
            
            with self.subTest(f"ページ{page + 1}"):
                if page < total_pages - 1:
                    # 最後以外のページは満杯
                    self.assertEqual(len(page_programs), items_per_page)
                else:
                    # 最後のページは残り番組数
                    expected_last = total_programs - (page * items_per_page)
                    self.assertEqual(len(page_programs), expected_last)


class TestDataManagerIntegration(unittest.TestCase, RealEnvironmentTestBase):
    """データマネージャー統合動作テスト"""
    
    def setUp(self):
        """テスト環境セットアップ"""
        self.setup_real_environment()
        self.authenticator = RadikoAuthenticator()
    
    def tearDown(self):
        """テスト環境クリーンアップ"""
        self.cleanup_real_environment()
    
    def test_program_info_manager_vs_history_manager_direct_comparison(self):
        """直接比較: ProgramInfoManager vs ProgramHistoryManager"""
        # Given: 認証情報
        auth_info = self.authenticator.authenticate()
        self.assertIsNotNone(auth_info)
        
        # 比較対象
        station_id = "TBS"
        test_date = date(2025, 7, 21)
        
        # When: ProgramInfoManagerで番組取得
        info_manager = ProgramInfoManager(
            area_id=auth_info.area_id,
            authenticator=self.authenticator
        )
        target_datetime = datetime.combine(test_date, datetime.min.time())
        programs_info = info_manager.fetch_program_guide(target_datetime, station_id)
        
        # When: ProgramHistoryManagerで番組取得
        history_manager = ProgramHistoryManager()
        date_str = test_date.strftime('%Y-%m-%d')
        programs_history = history_manager.get_programs_by_date(date_str, station_id)
        
        # Then: 結果記録・比較
        info_count = len(programs_info) if programs_info else 0
        history_count = len(programs_history) if programs_history else 0
        
        print(f"\n📊 データマネージャー比較結果:")
        print(f"  ProgramInfoManager: {info_count}番組")
        print(f"  ProgramHistoryManager: {history_count}番組")
        print(f"  差異: {abs(info_count - history_count)}番組")
        
        # 品質基準
        self.assertGreater(info_count, 0, "ProgramInfoManagerは番組を取得できること")
        
        # 問題検出条件
        if history_count <= 1 and info_count > 10:
            print("⚠️ 重大な問題を検出:")
            print(f"  - ProgramHistoryManager: {history_count}番組（異常に少ない）")
            print(f"  - ProgramInfoManager: {info_count}番組（正常）")
            print("  → UIはProgramInfoManagerを使用すべき")
            
            # この問題が今回のバグの根本原因
            self.fail(f"データマネージャー間で大きな差異を検出: {info_count} vs {history_count}")
        
        # 一定の差異は許容（実装差異）
        if abs(info_count - history_count) > 0:
            print(f"ℹ️ データマネージャー間の実装差異を記録: {info_count} vs {history_count}")


if __name__ == "__main__":
    unittest.main(verbosity=2)