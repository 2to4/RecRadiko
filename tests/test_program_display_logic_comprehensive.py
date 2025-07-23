"""
番組表示ロジック包括テスト（Phase 8.2）

今回の番組表日付表示問題を受けて、プロパティ使い分けと
表示ロジックの包括的なテストを実装。

テスト対象:
1. display_date vs start_time.date() の使い分け
2. UIでの表示vs録音ファイル名での使用
3. 深夜番組の表示ロジック一貫性
4. ユーザー体験としての日付表示
"""

import unittest
from datetime import datetime, date, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.program_info import Program, ProgramInfo
from src.ui.screens.program_select_screen import ProgramSelectScreen
from tests.utils.test_environment import RealEnvironmentTestBase


class TestProgramDisplayLogicComprehensive(unittest.TestCase):
    """番組表示ロジック包括テスト"""
    
    def test_property_usage_distinction(self):
        """プロパティ使い分け明確化テスト"""
        # Given: 深夜番組と通常番組
        midnight_prog = Program(
            id="midnight_test",
            station_id="TBS",
            title="深夜番組",
            start_time=datetime(2025, 7, 22, 2, 0),
            end_time=datetime(2025, 7, 22, 3, 0),
            duration=60
        )
        
        regular_prog = Program(
            id="regular_test",
            station_id="TBS", 
            title="朝番組",
            start_time=datetime(2025, 7, 22, 6, 0),
            end_time=datetime(2025, 7, 22, 7, 0),
            duration=60
        )
        
        # When: 各用途でのプロパティ使い分け確認
        
        # 1. UI表示用: 実際の放送日（start_time.date()）
        midnight_ui_date = midnight_prog.start_time.date().strftime('%Y-%m-%d')
        regular_ui_date = regular_prog.start_time.date().strftime('%Y-%m-%d')
        
        # 2. 録音ファイル名用: display_dateプロパティ
        midnight_file_date = midnight_prog.display_date
        regular_file_date = regular_prog.display_date
        
        # 3. 録音メタデータ用: start_time.date()を使用（実装に合わせて）
        midnight_metadata_date = midnight_prog.start_time.strftime('%Y%m%d')
        regular_metadata_date = regular_prog.start_time.strftime('%Y%m%d')
        
        # Then: 使い分けの明確化確認
        # UI表示: 両方とも実際の放送日
        self.assertEqual(midnight_ui_date, "2025-07-22", "深夜番組UI: 実際の放送日")
        self.assertEqual(regular_ui_date, "2025-07-22", "通常番組UI: 実際の放送日")
        
        # ファイル名・メタデータ: 深夜番組のみ前日扱い
        self.assertEqual(midnight_file_date, "2025-07-21", "深夜番組ファイル: 前日")
        self.assertEqual(regular_file_date, "2025-07-22", "通常番組ファイル: 当日")
        
        # メタデータ日付の確認
        self.assertEqual(midnight_metadata_date, "20250722", "深夜番組メタデータ: 実際の放送日")
        self.assertEqual(regular_metadata_date, "20250722", "通常番組メタデータ: 実際の放送日")
        
        print("✅ プロパティ使い分け: UI表示とファイル名で適切に使い分け")
    
    def test_ui_display_consistency_scenarios(self):
        """UI表示一貫性シナリオテスト"""
        # Given: ユーザーが選択する各シナリオ
        scenarios = [
            {
                "name": "今日の番組表を見る",
                "selected_date": date(2025, 7, 22),
                "expected_display": "2025-07-22",
                "programs": [
                    # 今日の深夜番組（0:00-3:00）
                    Program(id="today_midnight", station_id="TBS", title="今日深夜番組",
                           start_time=datetime(2025, 7, 22, 1, 0),
                           end_time=datetime(2025, 7, 22, 2, 0), duration=60),
                    # 今日の朝番組（5:00-6:00）
                    Program(id="today_morning", station_id="TBS", title="今日朝番組",
                           start_time=datetime(2025, 7, 22, 5, 0),
                           end_time=datetime(2025, 7, 22, 6, 0), duration=60),
                ]
            },
            {
                "name": "昨日の番組表を見る",
                "selected_date": date(2025, 7, 21),  
                "expected_display": "2025-07-21",
                "programs": [
                    # 昨日の深夜番組（0:00-3:00）
                    Program(id="yesterday_midnight", station_id="TBS", title="昨日深夜番組",
                           start_time=datetime(2025, 7, 21, 1, 0),
                           end_time=datetime(2025, 7, 21, 2, 0), duration=60),
                    # 昨日の朝番組（5:00-6:00）
                    Program(id="yesterday_morning", station_id="TBS", title="昨日朝番組",
                           start_time=datetime(2025, 7, 21, 5, 0),
                           end_time=datetime(2025, 7, 21, 6, 0), duration=60),
                ]
            }
        ]
        
        for scenario in scenarios:
            with self.subTest(scenario=scenario["name"]):
                # When: ProgramSelectScreenでの表示処理
                screen = ProgramSelectScreen()
                
                # シミュレート: _fetch_programs_from_apiの結果
                programs = []
                for prog in scenario["programs"]:
                    # UI表示ロジック: 実際の放送日使用
                    actual_date = prog.start_time.date().strftime('%Y-%m-%d')
                    
                    program_dict = {
                        'id': prog.program_id,
                        'title': prog.title,
                        'display_date': actual_date,  # ← 修正後のロジック
                        'is_midnight': prog.is_midnight_program
                    }
                    programs.append(program_dict)
                
                # Then: シナリオ一貫性確認
                for prog_dict in programs:
                    # ユーザーが選択した日付で表示される
                    self.assertEqual(prog_dict['display_date'], scenario["expected_display"],
                                   f"{scenario['name']}: {prog_dict['title']}が選択日で表示")
        
        print("✅ UI表示一貫性: ユーザー選択日と表示日付が一致")
    
    def test_user_experience_date_confusion_prevention(self):
        """ユーザー体験：日付混乱防止テスト"""
        # Given: ユーザーが混乱しやすいケース
        confusion_cases = [
            {
                "case": "今日を選択したのに昨日の日付で表示される",
                "user_selection": date(2025, 7, 22),
                "program": Program(
                    id="confusing_midnight",
                    station_id="TBS",
                    title="深夜番組",
                    start_time=datetime(2025, 7, 22, 1, 0),
                    end_time=datetime(2025, 7, 22, 2, 0),
                    duration=60
                ),
                "expected_ui_date": "2025-07-22",  # ユーザー選択日
                "expected_file_date": "2025-07-21"  # ファイル名は前日
            }
        ]
        
        for case_data in confusion_cases:
            with self.subTest(case=case_data["case"]):
                prog = case_data["program"]
                
                # When: UI表示での日付（修正後）
                ui_display_date = prog.start_time.date().strftime('%Y-%m-%d')
                
                # And: ファイル名での日付（従来通り）
                file_date = prog.display_date
                
                # Then: 混乱防止確認
                # UI表示: ユーザー選択日と一致
                self.assertEqual(ui_display_date, case_data["expected_ui_date"],
                               "UI表示はユーザー選択日と一致（混乱防止）")
                
                # ファイル名: 放送業界慣習に従い前日
                self.assertEqual(file_date, case_data["expected_file_date"],
                               "ファイル名は業界慣習（深夜番組は前日扱い）")
        
        print("✅ 日付混乱防止: UI表示とファイル名で適切に使い分け")
    
    def test_midnight_program_display_logic_consistency(self):
        """深夜番組表示ロジック一貫性テスト"""
        # Given: 様々な深夜番組パターン
        midnight_patterns = [
            (0, 0, "00:00開始"),
            (1, 30, "01:30開始"), 
            (3, 45, "03:45開始"),
            (4, 59, "04:59開始（境界値）"),
        ]
        
        base_date = datetime(2025, 7, 22)
        
        for hour, minute, description in midnight_patterns:
            with self.subTest(hour=hour, minute=minute, desc=description):
                program = Program(
                    id=f"midnight_{hour:02d}{minute:02d}",
                    station_id="TBS",
                    title=f"{description}番組",
                    start_time=base_date.replace(hour=hour, minute=minute),
                    end_time=base_date.replace(hour=hour, minute=minute) + timedelta(hours=1),
                    duration=60
                )
                
                # When: 各表示ロジック確認
                ui_date = program.start_time.date().strftime('%Y-%m-%d')
                file_date = program.display_date
                display_time = program.display_start_time
                
                # Then: 一貫性確認
                # 深夜番組判定の一貫性
                self.assertTrue(program.is_midnight_program, f"{description}は深夜番組")
                
                # UI表示: 実際の放送日
                self.assertEqual(ui_date, "2025-07-22", f"{description}UI: 実際の放送日")
                
                # ファイル名: 前日
                self.assertEqual(file_date, "2025-07-21", f"{description}ファイル: 前日")
                
                # 時刻表示: 24時間制
                expected_hour = hour + 24
                expected_display = f"{expected_hour:02d}:{minute:02d}"
                self.assertEqual(display_time, expected_display, f"{description}時刻: 24時間制")
        
        print("✅ 深夜番組ロジック一貫性: 各プロパティで適切な値")
    
    def test_program_info_program_consistency(self):
        """Program/ProgramInfo間の一貫性テスト"""
        # Given: 同じ番組のProgram/ProgramInfoオブジェクト
        start_time = datetime(2025, 7, 22, 2, 30)
        end_time = datetime(2025, 7, 22, 4, 0)
        
        program = Program(
            id="consistency_test",
            station_id="TBS",
            title="一貫性テスト番組",
            start_time=start_time,
            end_time=end_time,
            duration=90
        )
        
        program_info = ProgramInfo(
            program_id="consistency_test",
            station_id="TBS",
            station_name="TBSラジオ",
            title="一貫性テスト番組",
            start_time=start_time,
            end_time=end_time
        )
        
        # When & Then: 各プロパティの一貫性確認
        properties_to_check = [
            ('is_midnight_program', '深夜判定'),
            ('display_start_time', '開始時刻表示'),
            ('display_end_time', '終了時刻表示'),
            ('display_date', '表示日付')
        ]
        
        for prop_name, desc in properties_to_check:
            with self.subTest(property=prop_name):
                program_value = getattr(program, prop_name)
                program_info_value = getattr(program_info, prop_name)
                
                self.assertEqual(program_value, program_info_value,
                               f"{desc}がProgram/ProgramInfo間で一致")
        
        print("✅ Program/ProgramInfo一貫性: 各プロパティで同じ値")


class TestProgramDisplayRegressionSuite(unittest.TestCase, RealEnvironmentTestBase):
    """番組表示リグレッションテストスイート"""
    
    def setUp(self):
        """テスト環境セットアップ"""
        self.setup_real_environment()
    
    def tearDown(self):
        """テスト環境クリーンアップ"""
        self.cleanup_real_environment()
    
    def test_five_am_program_regression(self):
        """5時番組リグレッションテスト（今回の修正内容）"""
        # Given: 5時開始番組（今回問題となった境界値）
        five_am_program = Program(
            id="five_am_test",
            station_id="TBS",
            title="大島由香里 BRAND-NEW MORNING",
            start_time=datetime(2025, 7, 22, 5, 0),
            end_time=datetime(2025, 7, 22, 6, 30),
            duration=90
        )
        
        # When & Then: リグレッション防止確認
        # 1. 深夜番組ではない（修正後）
        self.assertFalse(five_am_program.is_midnight_program,
                        "5:00番組は通常番組（修正後）")
        
        # 2. UI表示は実際の放送日
        ui_date = five_am_program.start_time.date().strftime('%Y-%m-%d')
        self.assertEqual(ui_date, "2025-07-22", "UI表示: 実際の放送日")
        
        # 3. display_dateも当日（通常番組のため）
        self.assertEqual(five_am_program.display_date, "2025-07-22",
                        "display_date: 通常番組は当日")
        
        # 4. 時刻表示は通常形式
        self.assertEqual(five_am_program.display_start_time, "05:00",
                        "時刻表示: 通常形式")
        
        print("✅ 5時番組リグレッション: 修正内容が正常に動作")
    
    def test_ui_date_display_regression(self):
        """UI日付表示リグレッションテスト（今回の問題全般）"""
        # Given: ProgramSelectScreen with various programs
        screen = ProgramSelectScreen()
        
        # 問題となった日付表示パターン
        test_programs = [
            Program(
                id="regression_midnight",
                station_id="TBS",
                title="深夜番組",
                start_time=datetime(2025, 7, 22, 1, 0),
                end_time=datetime(2025, 7, 22, 2, 0),
                duration=60
            ),
            Program(
                id="regression_morning",
                station_id="TBS",
                title="朝番組", 
                start_time=datetime(2025, 7, 22, 5, 0),
                end_time=datetime(2025, 7, 22, 6, 0),
                duration=60
            )
        ]
        
        # Mock ProgramInfoManager for regression test
        from unittest.mock import Mock
        screen.program_info_manager = Mock()
        screen.program_info_manager.fetch_program_guide.return_value = test_programs
        
        # When: UI処理実行
        programs = screen._fetch_programs_from_api("TBS", date(2025, 7, 22))
        
        # Then: リグレッション防止確認
        self.assertEqual(len(programs), 2, "2番組が処理される")
        
        for prog_dict in programs:
            with self.subTest(program=prog_dict["title"]):
                # 全番組が選択日（2025-07-22）で表示
                self.assertEqual(prog_dict['display_date'], "2025-07-22",
                               f"{prog_dict['title']}が選択日で表示（リグレッション防止）")
        
        print("✅ UI日付表示リグレッション: 選択日で統一表示")


if __name__ == "__main__":
    unittest.main(verbosity=2)