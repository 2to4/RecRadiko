"""
境界値テスト包括強化（Phase 8.2）

今回の番組表日付表示問題を受けて、時刻境界での深夜判定・日付処理の
境界値テストを包括的に実装。

境界値テストパターン:
1. 深夜番組境界: 4:59 vs 5:00
2. 日付変更境界: 23:59 vs 0:00  
3. UIプロパティ使い分け境界
4. 実際の放送局時間パターン
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


class TestBoundaryValueComprehensive(unittest.TestCase):
    """包括的境界値テスト"""
    
    def test_midnight_program_hour_boundaries(self):
        """深夜番組時間境界テスト"""
        # Given: 各時間の境界値番組
        base_date = datetime(2025, 7, 22)
        boundary_programs = []
        
        # 深夜番組の境界値: 0:00, 4:59, 5:00
        test_hours = [
            (0, 0, True, "0:00は深夜番組"),
            (1, 30, True, "1:30は深夜番組"),
            (3, 45, True, "3:45は深夜番組"),
            (4, 59, True, "4:59は深夜番組"),
            (5, 0, False, "5:00は通常番組（境界値）"),
            (5, 1, False, "5:01は通常番組"),
            (6, 0, False, "6:00は通常番組"),
            (12, 0, False, "12:00は通常番組"),
            (23, 59, False, "23:59は通常番組")
        ]
        
        for hour, minute, expected_midnight, description in test_hours:
            with self.subTest(hour=hour, minute=minute, desc=description):
                program = Program(
                    id=f"test_{hour:02d}{minute:02d}",
                    station_id="TBS",
                    title=f"{hour:02d}:{minute:02d}番組",
                    start_time=base_date.replace(hour=hour, minute=minute),
                    end_time=base_date.replace(hour=hour, minute=minute) + timedelta(hours=1),
                    duration=60
                )
                
                # Then: 境界値での深夜判定
                self.assertEqual(program.is_midnight_program, expected_midnight, description)
                
                # 表示時刻の境界値確認
                if expected_midnight:
                    expected_display_hour = hour + 24
                    self.assertEqual(program.display_start_time, f"{expected_display_hour:02d}:{minute:02d}",
                                   f"{description} - 24時間表示")
                else:
                    self.assertEqual(program.display_start_time, f"{hour:02d}:{minute:02d}",
                                   f"{description} - 通常時刻表示")
        
        print("✅ 深夜番組境界値テスト: 4:59/5:00境界を含む全時間帯で正常判定")
    
    def test_date_change_boundaries(self):
        """日付変更境界テスト"""
        # Given: 日付変更をまたぐ番組
        programs = [
            # 23:30-25:30 (翌日1:30まで)
            Program(
                id="cross_midnight",
                station_id="TBS",
                title="日付変更番組",
                start_time=datetime(2025, 7, 22, 23, 30),
                end_time=datetime(2025, 7, 23, 1, 30),
                duration=120
            ),
            # 23:59-0:01 (1分で日付変更)
            Program(
                id="minute_cross",
                station_id="TBS", 
                title="分境界番組",
                start_time=datetime(2025, 7, 22, 23, 59),
                end_time=datetime(2025, 7, 23, 0, 1),
                duration=2
            ),
            # 4:59-5:01 (深夜境界を跨ぐ)
            Program(
                id="midnight_boundary_cross",
                station_id="TBS",
                title="深夜境界番組", 
                start_time=datetime(2025, 7, 22, 4, 59),
                end_time=datetime(2025, 7, 22, 5, 1),
                duration=2
            )
        ]
        
        # When & Then: 各境界での動作確認
        for prog in programs:
            with self.subTest(program=prog.title):
                # 日付表示の境界値確認
                actual_date = prog.start_time.date().strftime('%Y-%m-%d')
                display_date = prog.display_date
                
                if prog.is_midnight_program:
                    # 深夜番組は前日表示
                    expected_display = (prog.start_time.date() - timedelta(days=1)).strftime('%Y-%m-%d')
                    self.assertEqual(display_date, expected_display, f"{prog.title}: 深夜番組は前日表示")
                else:
                    # 通常番組は当日表示
                    self.assertEqual(display_date, actual_date, f"{prog.title}: 通常番組は当日表示")
                
                # 時刻表示の境界値確認
                if prog.title == "深夜境界番組":
                    # 4:59開始は深夜判定
                    self.assertTrue(prog.is_midnight_program, "4:59開始は深夜番組")
                    self.assertEqual(prog.display_start_time, "28:59", "4:59は28:59表示")
        
        print("✅ 日付変更境界テスト: 23:59/0:00境界、4:59/5:00境界で正常動作")
    
    def test_ui_property_usage_boundaries(self):
        """UIプロパティ使い分け境界テスト"""
        # Given: 深夜番組と通常番組
        midnight_prog = Program(
            id="ui_midnight",
            station_id="TBS", 
            title="深夜番組",
            start_time=datetime(2025, 7, 22, 2, 0),
            end_time=datetime(2025, 7, 22, 3, 0),
            duration=60
        )
        
        regular_prog = Program(
            id="ui_regular",
            station_id="TBS",
            title="朝番組",
            start_time=datetime(2025, 7, 22, 5, 0),
            end_time=datetime(2025, 7, 22, 6, 0), 
            duration=60
        )
        
        # When: UIで使用するプロパティ確認
        # UI表示用: 実際の放送日
        midnight_ui_date = midnight_prog.start_time.date().strftime('%Y-%m-%d')
        regular_ui_date = regular_prog.start_time.date().strftime('%Y-%m-%d')
        
        # 録音・ファイル名用: display_dateプロパティ
        midnight_file_date = midnight_prog.display_date
        regular_file_date = regular_prog.display_date
        
        # Then: 使い分けの境界値確認
        # UI表示: 両方とも実際の放送日
        self.assertEqual(midnight_ui_date, "2025-07-22", "深夜番組UI表示: 実際の放送日")
        self.assertEqual(regular_ui_date, "2025-07-22", "通常番組UI表示: 実際の放送日")
        
        # ファイル名: 深夜番組は前日、通常番組は当日
        self.assertEqual(midnight_file_date, "2025-07-21", "深夜番組ファイル名: 前日")
        self.assertEqual(regular_file_date, "2025-07-22", "通常番組ファイル名: 当日")
        
        print("✅ UIプロパティ使い分け境界: UI表示とファイル名で適切に使い分け")
    
    def test_real_radio_station_time_patterns(self):
        """実際のラジオ局時間パターン境界テスト"""
        # Given: 実際のラジオ局で使われる時間パターン
        real_patterns = [
            # TBSラジオの実際の番組時間
            ("大島由香里 BRAND-NEW MORNING", 5, 0, False),
            ("森本毅郎・スタンバイ！", 6, 30, False),
            ("空気階段の踊り場", 0, 0, True),
            ("JUNK 伊集院光 深夜の馬鹿力", 1, 0, True),
            ("CITY CHILL CLUB", 3, 0, True),
            
            # 他局の境界ケース
            ("早朝ニュース", 4, 30, True),   # 4:30は深夜扱い
            ("早朝ラジオ体操", 6, 0, False), # 6:00は通常扱い
            ("オールナイト終了", 4, 59, True),  # 4:59は深夜扱い
            ("朝の挨拶", 5, 0, False),       # 5:00は通常扱い
        ]
        
        base_date = datetime(2025, 7, 22)
        
        for title, hour, minute, expected_midnight in real_patterns:
            with self.subTest(title=title, hour=hour, minute=minute):
                program = Program(
                    id=f"real_{title}",
                    station_id="TEST",
                    title=title,
                    start_time=base_date.replace(hour=hour, minute=minute),
                    end_time=base_date.replace(hour=hour, minute=minute) + timedelta(hours=1),
                    duration=60
                )
                
                # Then: 実際のパターンでの境界値確認
                self.assertEqual(program.is_midnight_program, expected_midnight,
                               f"{title}({hour}:{minute:02d})の深夜判定")
                
                # 5:00が境界値の確認
                if hour == 5 and minute == 0:
                    self.assertFalse(program.is_midnight_program, "5:00開始番組は通常番組（修正確認）")
                elif hour == 4 and minute == 59:
                    self.assertTrue(program.is_midnight_program, "4:59開始番組は深夜番組")
        
        print("✅ 実ラジオ局パターン境界: 実際の番組時間で正常判定、5:00境界修正確認")


class TestProgramInfoBoundaryValues(unittest.TestCase):
    """ProgramInfo境界値テスト"""
    
    def test_program_info_midnight_boundaries(self):
        """ProgramInfo深夜番組境界値テスト"""
        # Given: ProgramInfoクラスでの境界値
        base_time = datetime(2025, 7, 22, 0, 0)
        
        test_cases = [
            (4, 58, True, "4:58開始"),
            (4, 59, True, "4:59開始"),
            (5, 0, False, "5:00開始（境界値）"),
            (5, 1, False, "5:01開始"),
        ]
        
        for hour, minute, expected_midnight, description in test_cases:
            with self.subTest(hour=hour, minute=minute):
                program_info = ProgramInfo(
                    program_id=f"info_{hour:02d}{minute:02d}",
                    station_id="TBS",
                    station_name="TBSラジオ",
                    title=f"境界値テスト{hour}:{minute:02d}",
                    start_time=base_time.replace(hour=hour, minute=minute),
                    end_time=base_time.replace(hour=hour, minute=minute) + timedelta(hours=1)
                )
                
                # Then: ProgramInfoでも同様の境界値判定
                self.assertEqual(program_info.is_midnight_program, expected_midnight,
                               f"ProgramInfo {description}")
                
                # 表示プロパティの境界値確認
                if expected_midnight:
                    expected_display_hour = hour + 24
                    self.assertEqual(program_info.display_start_time, f"{expected_display_hour:02d}:{minute:02d}")
                else:
                    self.assertEqual(program_info.display_start_time, f"{hour:02d}:{minute:02d}")
        
        print("✅ ProgramInfo境界値: Program/ProgramInfo間で一貫した境界値判定")


class TestEdgeCasePrograms(unittest.TestCase):
    """エッジケース番組テスト"""
    
    def test_very_short_programs(self):
        """極短時間番組の境界値テスト"""
        # Given: 極短時間番組（ニュース、天気予報等）
        base_time = datetime(2025, 7, 22, 4, 59)
        
        short_programs = [
            (1, "1分ニュース"),    # 4:59-5:00 (境界跨ぎ)
            (2, "2分天気"),       # 4:59-5:01
            (30, "30秒CM")        # 4:59-4:59:30
        ]
        
        for duration_minutes, title in short_programs:
            with self.subTest(duration=duration_minutes, title=title):
                program = Program(
                    id=f"short_{duration_minutes}",
                    station_id="TBS",
                    title=title,
                    start_time=base_time,
                    end_time=base_time + timedelta(minutes=duration_minutes),
                    duration=duration_minutes
                )
                
                # Then: 開始時刻による判定（4:59開始は深夜）
                self.assertTrue(program.is_midnight_program, f"{title}: 4:59開始は深夜番組")
                
                # 極短時間でも正常な時刻表示
                self.assertEqual(program.display_start_time, "28:59", f"{title}: 深夜時刻表示")
        
        print("✅ 極短時間番組境界: 境界跨ぎでも開始時刻で正常判定")
    
    def test_cross_week_programs(self):
        """週跨ぎ番組の境界値テスト"""
        # Given: 日曜深夜→月曜早朝の番組
        sunday_night = datetime(2025, 7, 27, 23, 0)  # 日曜23:00
        monday_morning = datetime(2025, 7, 28, 2, 0)  # 月曜2:00
        
        cross_week_program = Program(
            id="cross_week",
            station_id="TBS",
            title="日曜→月曜番組",
            start_time=sunday_night,
            end_time=monday_morning,
            duration=180  # 3時間
        )
        
        # When & Then: 週跨ぎでの境界値確認
        # 開始時刻は日曜23:00（通常番組）
        self.assertFalse(cross_week_program.is_midnight_program, "23:00開始は通常番組")
        
        # 実際の放送日は日曜
        actual_date = cross_week_program.start_time.date().strftime('%Y-%m-%d')
        self.assertEqual(actual_date, "2025-07-27", "実際の放送日は日曜")
        
        # display_dateも日曜（通常番組のため）
        self.assertEqual(cross_week_program.display_date, "2025-07-27", "display_dateは日曜")
        
        print("✅ 週跨ぎ番組境界: 開始時刻基準で日付境界を正常処理")


if __name__ == "__main__":
    unittest.main(verbosity=2)