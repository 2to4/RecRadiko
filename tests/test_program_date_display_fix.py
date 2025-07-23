"""
番組表日付表示問題修正のテスト

TBSラジオで発生していた日付表示問題の修正効果を検証
- 深夜番組判定ロジックの修正
- 番組表表示での実際の放送日使用
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


class TestProgramDateDisplayFix(unittest.TestCase, RealEnvironmentTestBase):
    """番組表日付表示修正テスト"""
    
    def setUp(self):
        """テスト環境セットアップ"""
        self.setup_real_environment()
    
    def tearDown(self):
        """テスト環境クリーンアップ"""
        self.cleanup_real_environment()
    
    def test_midnight_program_judgment_fix(self):
        """深夜番組判定ロジック修正テスト"""
        # Given: 各時間帯の番組
        test_programs = [
            # 深夜番組（0:00-4:59）
            Program(id="1", station_id="TBS", title="0時番組", 
                   start_time=datetime(2025, 7, 22, 0, 0), 
                   end_time=datetime(2025, 7, 22, 1, 0), duration=60),
            Program(id="2", station_id="TBS", title="1時番組", 
                   start_time=datetime(2025, 7, 22, 1, 0), 
                   end_time=datetime(2025, 7, 22, 2, 0), duration=60),
            Program(id="3", station_id="TBS", title="4時番組", 
                   start_time=datetime(2025, 7, 22, 4, 0), 
                   end_time=datetime(2025, 7, 22, 5, 0), duration=60),
            
            # 通常番組（5:00以降）
            Program(id="4", station_id="TBS", title="5時番組", 
                   start_time=datetime(2025, 7, 22, 5, 0), 
                   end_time=datetime(2025, 7, 22, 6, 0), duration=60),
            Program(id="5", station_id="TBS", title="6時番組", 
                   start_time=datetime(2025, 7, 22, 6, 0), 
                   end_time=datetime(2025, 7, 22, 7, 0), duration=60),
        ]
        
        # When & Then: 深夜番組判定
        self.assertTrue(test_programs[0].is_midnight_program, "0時番組は深夜番組")
        self.assertTrue(test_programs[1].is_midnight_program, "1時番組は深夜番組") 
        self.assertTrue(test_programs[2].is_midnight_program, "4時番組は深夜番組")
        
        # 修正効果: 5時以降は通常番組
        self.assertFalse(test_programs[3].is_midnight_program, "5時番組は通常番組（修正済み）")
        self.assertFalse(test_programs[4].is_midnight_program, "6時番組は通常番組")
        
        print("✅ 深夜番組判定修正: 0-4時は深夜番組、5時以降は通常番組")
    
    def test_program_display_date_fix(self):
        """番組表示日付修正テスト"""
        # Given: 深夜番組と通常番組
        midnight_program = Program(
            id="midnight", station_id="TBS", title="深夜番組",
            start_time=datetime(2025, 7, 22, 1, 0),
            end_time=datetime(2025, 7, 22, 2, 0), duration=60
        )
        
        regular_program = Program(
            id="regular", station_id="TBS", title="朝番組", 
            start_time=datetime(2025, 7, 22, 6, 0),
            end_time=datetime(2025, 7, 22, 7, 0), duration=60
        )
        
        # When: 番組表示での日付確認
        midnight_actual_date = midnight_program.start_time.date().strftime('%Y-%m-%d')
        regular_actual_date = regular_program.start_time.date().strftime('%Y-%m-%d')
        
        # Then: 実際の放送日で表示される（display_dateではない）
        self.assertEqual(midnight_actual_date, "2025-07-22", "深夜番組も実際の放送日で表示")
        self.assertEqual(regular_actual_date, "2025-07-22", "通常番組も実際の放送日で表示")
        
        # display_dateプロパティは録音ファイル名等で使用（番組表示では使用しない）
        self.assertEqual(midnight_program.display_date, "2025-07-21", "display_dateは前日（録音用）")
        self.assertEqual(regular_program.display_date, "2025-07-22", "display_dateは当日")
        
        print("✅ 番組表示日付修正: 実際の放送日で表示、display_dateは録音用途")
    
    def test_program_select_screen_date_display(self):
        """ProgramSelectScreen日付表示テスト"""
        # Given: ProgramSelectScreen初期化
        screen = ProgramSelectScreen()
        
        # テスト用番組データ（モック）
        from unittest.mock import Mock
        
        mock_midnight_prog = Mock()
        mock_midnight_prog.title = "深夜番組テスト"
        mock_midnight_prog.start_time = datetime(2025, 7, 22, 1, 0)
        mock_midnight_prog.end_time = datetime(2025, 7, 22, 2, 0)
        mock_midnight_prog.is_midnight_program = True
        mock_midnight_prog.display_start_time = "25:00"
        mock_midnight_prog.display_end_time = "26:00"
        mock_midnight_prog.program_id = "test1"
        mock_midnight_prog.station_id = "TBS"
        mock_midnight_prog.station_name = "TBSラジオ"
        
        mock_regular_prog = Mock()
        mock_regular_prog.title = "朝番組テスト"
        mock_regular_prog.start_time = datetime(2025, 7, 22, 6, 0)
        mock_regular_prog.end_time = datetime(2025, 7, 22, 7, 0)
        mock_regular_prog.is_midnight_program = False
        mock_regular_prog.display_start_time = "06:00"
        mock_regular_prog.display_end_time = "07:00"
        mock_regular_prog.program_id = "test2"
        mock_regular_prog.station_id = "TBS"
        mock_regular_prog.station_name = "TBSラジオ"
        
        # ProgramInfoManagerをモック
        screen.program_info_manager = Mock()
        screen.program_info_manager.fetch_program_guide.return_value = [
            mock_midnight_prog, mock_regular_prog
        ]
        
        # When: 番組取得実行
        programs = screen._fetch_programs_from_api("TBS", date(2025, 7, 22))
        
        # Then: 両方とも実際の放送日で表示
        self.assertEqual(len(programs), 2, "2番組取得")
        
        midnight_prog_dict = next(p for p in programs if p['title'] == "深夜番組テスト")
        regular_prog_dict = next(p for p in programs if p['title'] == "朝番組テスト")
        
        # 修正効果: 両方とも2025-07-22で表示
        self.assertEqual(midnight_prog_dict['display_date'], "2025-07-22", 
                        "深夜番組も実際の放送日で表示")
        self.assertEqual(regular_prog_dict['display_date'], "2025-07-22",
                        "通常番組も実際の放送日で表示")
        
        print("✅ ProgramSelectScreen修正: 全番組が実際の放送日で表示")
    
    def test_real_tbs_program_display_integration(self):
        """実環境TBSラジオ番組表示統合テスト"""
        # Given: 実環境ProgramSelectScreen
        screen = ProgramSelectScreen()
        tbs_station = {"id": "TBS", "name": "TBSラジオ"}
        today = date.today()
        
        # When: 今日の番組表取得
        screen.set_station_and_date(tbs_station, today)
        success = screen.load_programs()
        
        # Then: 番組取得成功
        self.assertTrue(success, "TBSラジオ番組表取得成功")
        self.assertGreater(len(screen.programs), 0, "番組が取得されること")
        
        # 日付表示確認
        today_str = today.strftime('%Y-%m-%d')
        
        for prog in screen.programs:
            # 修正効果: 全ての番組が今日の日付で表示
            self.assertEqual(prog['display_date'], today_str, 
                           f"番組'{prog['title']}'が今日の日付で表示されること")
            
            # 深夜番組は時刻表示が24時間制
            if prog.get('is_midnight', False):
                start_time = prog['display_start_time']
                self.assertRegex(start_time, r'^2[4-9]:', 
                               f"深夜番組'{prog['title']}'は24時間制表示")
        
        print(f"✅ 実環境統合テスト: TBSラジオ{len(screen.programs)}番組、全て{today_str}で正常表示")


if __name__ == "__main__":
    unittest.main(verbosity=2)