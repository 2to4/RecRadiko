"""
スケジューラーモジュールの単体テスト
"""

import unittest
import tempfile
import json
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.scheduler import (
    RecordingScheduler, RecordingSchedule, RepeatPattern, ScheduleConflict,
    SchedulerError, ScheduleStatus, DetectedConflict
)


class TestRepeatPattern(unittest.TestCase):
    """RepeatPattern Enum のテスト"""
    
    def test_repeat_pattern_values(self):
        """RepeatPattern の値テスト"""
        self.assertEqual(RepeatPattern.NONE.value, "none")
        self.assertEqual(RepeatPattern.DAILY.value, "daily")
        self.assertEqual(RepeatPattern.WEEKLY.value, "weekly")
        self.assertEqual(RepeatPattern.MONTHLY.value, "monthly")
        self.assertEqual(RepeatPattern.WEEKDAYS.value, "weekdays")
        self.assertEqual(RepeatPattern.CUSTOM.value, "custom")


class TestScheduleStatus(unittest.TestCase):
    """ScheduleStatus Enum のテスト"""
    
    def test_schedule_status_values(self):
        """ScheduleStatus の値テスト"""
        self.assertEqual(ScheduleStatus.SCHEDULED.value, "scheduled")
        self.assertEqual(ScheduleStatus.RUNNING.value, "running")
        self.assertEqual(ScheduleStatus.COMPLETED.value, "completed")
        self.assertEqual(ScheduleStatus.FAILED.value, "failed")
        self.assertEqual(ScheduleStatus.CANCELLED.value, "cancelled")
        self.assertEqual(ScheduleStatus.MISSED.value, "missed")


class TestScheduleConflict(unittest.TestCase):
    """ScheduleConflict クラスのテスト"""
    
    def test_schedule_conflict_creation(self):
        """ScheduleConflict の作成テスト"""
        conflict_time = datetime.now()
        schedule1 = RecordingSchedule(
            schedule_id="test1",
            station_id="TBS",
            program_title="番組1",
            start_time=conflict_time,
            end_time=conflict_time + timedelta(hours=1),
            repeat_pattern=RepeatPattern.NONE
        )
        schedule2 = RecordingSchedule(
            schedule_id="test2",
            station_id="QRR",
            program_title="番組2",
            start_time=conflict_time + timedelta(minutes=30),
            end_time=conflict_time + timedelta(hours=1, minutes=30),
            repeat_pattern=RepeatPattern.NONE
        )
        
        conflict = ScheduleConflict(
            schedule1_id=schedule1.schedule_id,
            schedule2_id=schedule2.schedule_id,
            overlap_start=conflict_time + timedelta(minutes=30),
            overlap_end=conflict_time + timedelta(hours=1),
            duration_minutes=30
        )
        
        self.assertEqual(conflict.schedule1_id, "test1")
        self.assertEqual(conflict.schedule2_id, "test2")
        self.assertEqual(conflict.overlap_start, conflict_time + timedelta(minutes=30))
        self.assertEqual(conflict.overlap_end, conflict_time + timedelta(hours=1))
        self.assertEqual(conflict.duration_minutes, 30)


class TestRecordingSchedule(unittest.TestCase):
    """RecordingSchedule クラスのテスト"""
    
    def test_recording_schedule_creation(self):
        """RecordingSchedule の作成テスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        schedule = RecordingSchedule(
            schedule_id="test_schedule",
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.WEEKLY,
            status=ScheduleStatus.SCHEDULED
        )
        
        self.assertEqual(schedule.schedule_id, "test_schedule")
        self.assertEqual(schedule.station_id, "TBS")
        self.assertEqual(schedule.program_title, "テスト番組")
        self.assertEqual(schedule.start_time, start_time)
        self.assertEqual(schedule.end_time, end_time)
        self.assertEqual(schedule.repeat_pattern, RepeatPattern.WEEKLY)
        self.assertEqual(schedule.status, ScheduleStatus.SCHEDULED)
    
    def test_recording_schedule_duration(self):
        """RecordingSchedule の録音時間計算テスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2, minutes=30)
        
        schedule = RecordingSchedule(
            schedule_id="test_duration",
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.NONE
        )
        
        self.assertEqual(schedule.duration_seconds, 9000)  # 2.5時間 = 9000秒
    
    def test_recording_schedule_is_active(self):
        """RecordingSchedule のアクティブ判定テスト"""
        now = datetime.now()
        
        # 現在時刻を挟むスケジュール
        active_schedule = RecordingSchedule(
            schedule_id="active",
            station_id="TBS",
            program_title="アクティブ番組",
            start_time=now - timedelta(minutes=30),
            end_time=now + timedelta(minutes=30),
            repeat_pattern=RepeatPattern.NONE
        )
        
        # 過去のスケジュール
        past_schedule = RecordingSchedule(
            schedule_id="past",
            station_id="TBS",
            program_title="過去番組",
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
            repeat_pattern=RepeatPattern.NONE
        )
        
        # 未来のスケジュール
        future_schedule = RecordingSchedule(
            schedule_id="future",
            station_id="TBS",
            program_title="未来番組",
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            repeat_pattern=RepeatPattern.NONE
        )
        
        self.assertTrue(active_schedule.is_active())
        self.assertFalse(past_schedule.is_active())
        self.assertFalse(future_schedule.is_active())
    
    def test_recording_schedule_next_execution(self):
        """RecordingSchedule の次回実行時刻計算テスト"""
        base_time = datetime(2024, 1, 1, 20, 0, 0)  # 月曜日 20:00
        
        # 毎日繰り返し
        daily_schedule = RecordingSchedule(
            schedule_id="daily",
            station_id="TBS",
            program_title="毎日番組",
            start_time=base_time,
            end_time=base_time + timedelta(hours=1),
            repeat_pattern=RepeatPattern.DAILY
        )
        
        # 基準時刻を指定して次回実行時刻を取得
        next_daily = daily_schedule.get_next_execution_time(after=base_time)
        self.assertEqual(next_daily, base_time + timedelta(days=1))
        
        # 毎週繰り返し
        weekly_schedule = RecordingSchedule(
            schedule_id="weekly",
            station_id="TBS",
            program_title="毎週番組",
            start_time=base_time,
            end_time=base_time + timedelta(hours=1),
            repeat_pattern=RepeatPattern.WEEKLY
        )
        
        next_weekly = weekly_schedule.get_next_execution_time(after=base_time)
        self.assertEqual(next_weekly, base_time + timedelta(weeks=1))
        
        # 繰り返しなし
        no_repeat_schedule = RecordingSchedule(
            schedule_id="no_repeat",
            station_id="TBS",
            program_title="単発番組",
            start_time=base_time,
            end_time=base_time + timedelta(hours=1),
            repeat_pattern=RepeatPattern.NONE
        )
        
        # 繰り返しなしの場合、過去の時刻なのでNoneになる
        next_no_repeat = no_repeat_schedule.get_next_execution_time(after=base_time)
        self.assertIsNone(next_no_repeat)
    
    def test_recording_schedule_to_dict(self):
        """RecordingSchedule の辞書変換テスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        schedule = RecordingSchedule(
            schedule_id="test_dict",
            station_id="TBS",
            program_title="辞書テスト",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.WEEKLY,
            tags=["テスト"]
        )
        
        schedule_dict = schedule.to_dict()
        
        self.assertEqual(schedule_dict['schedule_id'], "test_dict")
        self.assertEqual(schedule_dict['station_id'], "TBS")
        self.assertEqual(schedule_dict['program_title'], "辞書テスト")
        self.assertEqual(schedule_dict['repeat_pattern'], "weekly")
        self.assertIn('start_time', schedule_dict)
        self.assertIn('end_time', schedule_dict)
        self.assertIn('tags', schedule_dict)
    
    def test_recording_schedule_from_dict(self):
        """RecordingSchedule の辞書からの復元テスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        schedule_dict = {
            'schedule_id': "test_restore",
            'station_id': "TBS",
            'program_title': "復元テスト",
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'repeat_pattern': "weekly",
            'description': "復元テスト用",
            'tags': ["復元", "テスト"],
            'priority': 3,
            'auto_delete_days': 60,
            'status': "scheduled",
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'last_run': None,
            'next_run': None,
            'run_count': 0,
            'max_runs': None,
            'enabled': True,
            'custom_repeat_config': None
        }
        
        schedule = RecordingSchedule.from_dict(schedule_dict)
        
        self.assertEqual(schedule.schedule_id, "test_restore")
        self.assertEqual(schedule.station_id, "TBS")
        self.assertEqual(schedule.program_title, "復元テスト")
        self.assertEqual(schedule.repeat_pattern, RepeatPattern.WEEKLY)
        self.assertEqual(schedule.status, ScheduleStatus.SCHEDULED)


class TestRecordingScheduler(unittest.TestCase):
    """RecordingScheduler クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.schedule_file = f"{self.temp_dir}/test_schedules.json"
        
        # モックの作成
        self.mock_recorder = Mock()
        self.mock_error_handler = Mock()
        self.mock_notification_handler = Mock()
        
        self.scheduler = RecordingScheduler(
            recorder=self.mock_recorder,
            error_handler=self.mock_error_handler,
            notification_handler=self.mock_notification_handler,
            schedule_file=self.schedule_file,
            max_concurrent_recordings=2
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.scheduler.shutdown()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_scheduler_creation(self):
        """RecordingScheduler の作成テスト"""
        self.assertIsInstance(self.scheduler, RecordingScheduler)
        self.assertEqual(self.scheduler.max_concurrent_recordings, 2)
        self.assertEqual(len(self.scheduler.schedules), 0)
        # 遅延初期化により、最初は起動していない
        self.assertFalse(self.scheduler.is_running)
    
    def test_add_schedule(self):
        """スケジュール追加のテスト"""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        schedule = RecordingSchedule(
            schedule_id="test_add",
            station_id="TBS",
            program_title="追加テスト",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.NONE
        )
        
        result = self.scheduler.add_schedule(schedule)
        
        self.assertTrue(result)
        self.assertIn("test_add", self.scheduler.schedules)
        self.assertEqual(len(self.scheduler.schedules), 1)
    
    def test_add_schedule_duplicate(self):
        """重複スケジュール追加のテスト"""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        schedule1 = RecordingSchedule(
            schedule_id="test_duplicate",
            station_id="TBS",
            program_title="重複テスト1",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.NONE
        )
        
        schedule2 = RecordingSchedule(
            schedule_id="test_duplicate",
            station_id="QRR",
            program_title="重複テスト2",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.NONE
        )
        
        # 最初のスケジュール追加は成功
        result1 = self.scheduler.add_schedule(schedule1)
        self.assertTrue(result1)
        
        # 同じIDのスケジュール追加は失敗
        result2 = self.scheduler.add_schedule(schedule2)
        self.assertFalse(result2)
        
        # 元のスケジュールが残っている
        self.assertEqual(self.scheduler.schedules["test_duplicate"].program_title, "重複テスト1")
    
    def test_update_schedule(self):
        """スケジュール更新のテスト"""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        original_schedule = RecordingSchedule(
            schedule_id="test_update",
            station_id="TBS",
            program_title="更新前",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.NONE
        )
        
        updated_schedule = RecordingSchedule(
            schedule_id="test_update",
            station_id="TBS",
            program_title="更新後",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.WEEKLY
        )
        
        # 元のスケジュールを追加
        self.scheduler.add_schedule(original_schedule)
        
        # スケジュールを更新
        result = self.scheduler.update_schedule(updated_schedule)
        
        self.assertTrue(result)
        self.assertEqual(self.scheduler.schedules["test_update"].program_title, "更新後")
        self.assertEqual(self.scheduler.schedules["test_update"].repeat_pattern, RepeatPattern.WEEKLY)
    
    def test_update_schedule_nonexistent(self):
        """存在しないスケジュール更新のテスト"""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        schedule = RecordingSchedule(
            schedule_id="nonexistent",
            station_id="TBS",
            program_title="存在しない",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.NONE
        )
        
        result = self.scheduler.update_schedule(schedule)
        
        self.assertFalse(result)
        self.assertNotIn("nonexistent", self.scheduler.schedules)
    
    def test_remove_schedule(self):
        """スケジュール削除のテスト"""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        schedule = RecordingSchedule(
            schedule_id="test_remove",
            station_id="TBS",
            program_title="削除テスト",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.NONE
        )
        
        # スケジュールを追加
        self.scheduler.add_schedule(schedule)
        self.assertIn("test_remove", self.scheduler.schedules)
        
        # スケジュールを削除
        result = self.scheduler.remove_schedule("test_remove")
        
        self.assertTrue(result)
        self.assertNotIn("test_remove", self.scheduler.schedules)
    
    def test_remove_schedule_nonexistent(self):
        """存在しないスケジュール削除のテスト"""
        result = self.scheduler.remove_schedule("nonexistent")
        
        self.assertFalse(result)
    
    def test_get_schedule(self):
        """スケジュール取得のテスト"""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        schedule = RecordingSchedule(
            schedule_id="test_get",
            station_id="TBS",
            program_title="取得テスト",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.NONE
        )
        
        # スケジュールを追加
        self.scheduler.add_schedule(schedule)
        
        # スケジュールを取得
        retrieved = self.scheduler.get_schedule("test_get")
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.schedule_id, "test_get")
        self.assertEqual(retrieved.program_title, "取得テスト")
        
        # 存在しないスケジュール
        nonexistent = self.scheduler.get_schedule("nonexistent")
        self.assertIsNone(nonexistent)
    
    def test_list_schedules(self):
        """スケジュール一覧取得のテスト"""
        now = datetime.now()
        
        schedules_data = [
            ("TBS", "番組1", now + timedelta(hours=1), RepeatPattern.NONE),
            ("QRR", "番組2", now + timedelta(hours=2), RepeatPattern.DAILY),
            ("TBS", "番組3", now + timedelta(hours=3), RepeatPattern.WEEKLY)
        ]
        
        for i, (station_id, title, start_time, repeat) in enumerate(schedules_data):
            schedule = RecordingSchedule(
                schedule_id=f"test_list_{i}",
                station_id=station_id,
                program_title=title,
                start_time=start_time,
                end_time=start_time + timedelta(hours=1),
                repeat_pattern=repeat
            )
            self.scheduler.add_schedule(schedule)
        
        # 全スケジュール取得
        all_schedules = self.scheduler.list_schedules()
        self.assertEqual(len(all_schedules), 3)
        
        # 放送局でフィルター
        tbs_schedules = self.scheduler.list_schedules(station_id="TBS")
        self.assertEqual(len(tbs_schedules), 2)
        
        # 繰り返しパターンでフィルター
        repeat_schedules = self.scheduler.list_schedules(repeat_pattern=RepeatPattern.NONE)
        self.assertEqual(len(repeat_schedules), 1)
        
        # 日付範囲でフィルター
        date_filtered = self.scheduler.list_schedules(
            start_date=now + timedelta(hours=1, minutes=30),
            end_date=now + timedelta(hours=2, minutes=30)
        )
        self.assertEqual(len(date_filtered), 1)
    
    def test_detect_conflicts(self):
        """スケジュール競合検出のテスト"""
        base_time = datetime.now() + timedelta(hours=1)
        
        # 重複するスケジュール
        schedule1 = RecordingSchedule(
            schedule_id="conflict1",
            station_id="TBS",
            program_title="競合番組1",
            start_time=base_time,
            end_time=base_time + timedelta(hours=1),
            repeat_pattern=RepeatPattern.NONE
        )
        
        schedule2 = RecordingSchedule(
            schedule_id="conflict2",
            station_id="QRR",
            program_title="競合番組2",
            start_time=base_time + timedelta(minutes=30),
            end_time=base_time + timedelta(hours=1, minutes=30),
            repeat_pattern=RepeatPattern.NONE
        )
        
        # 競合しないスケジュール
        schedule3 = RecordingSchedule(
            schedule_id="no_conflict",
            station_id="LFR",
            program_title="非競合番組",
            start_time=base_time + timedelta(hours=2),
            end_time=base_time + timedelta(hours=3),
            repeat_pattern=RepeatPattern.NONE
        )
        
        self.scheduler.add_schedule(schedule1)
        self.scheduler.add_schedule(schedule2)
        self.scheduler.add_schedule(schedule3)
        
        conflicts = self.scheduler.detect_conflicts()
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].schedule1.schedule_id, "conflict1")
        self.assertEqual(conflicts[0].schedule2.schedule_id, "conflict2")
    
    def test_get_next_schedules(self):
        """次回実行スケジュール取得のテスト"""
        now = datetime.now()
        
        schedules_data = [
            ("near", now + timedelta(minutes=10)),
            ("far", now + timedelta(hours=2)),
            ("very_far", now + timedelta(days=1))
        ]
        
        for schedule_id, start_time in schedules_data:
            schedule = RecordingSchedule(
                schedule_id=schedule_id,
                station_id="TBS",
                program_title=f"番組_{schedule_id}",
                start_time=start_time,
                end_time=start_time + timedelta(hours=1),
                repeat_pattern=RepeatPattern.NONE
            )
            self.scheduler.add_schedule(schedule)
        
        # 次の1時間以内のスケジュール
        next_schedules = self.scheduler.get_next_schedules(hours=1)
        self.assertEqual(len(next_schedules), 1)
        self.assertEqual(next_schedules[0].schedule_id, "near")
        
        # 次の3時間以内のスケジュール
        next_schedules_3h = self.scheduler.get_next_schedules(hours=3)
        self.assertEqual(len(next_schedules_3h), 2)
    
    def test_enable_disable_schedule(self):
        """スケジュール有効/無効化のテスト"""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        schedule = RecordingSchedule(
            schedule_id="test_enable",
            station_id="TBS",
            program_title="有効化テスト",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.NONE
        )
        
        self.scheduler.add_schedule(schedule)
        
        # 初期状態は有効
        self.assertTrue(self.scheduler.schedules["test_enable"].enabled)
        
        # 無効化
        result_disable = self.scheduler.disable_schedule("test_enable")
        self.assertTrue(result_disable)
        self.assertFalse(self.scheduler.schedules["test_enable"].enabled)
        
        # 有効化
        result_enable = self.scheduler.enable_schedule("test_enable")
        self.assertTrue(result_enable)
        self.assertTrue(self.scheduler.schedules["test_enable"].enabled)
    
    @patch('src.scheduler.RecordingScheduler._execute_recording')
    def test_schedule_execution(self, mock_execute):
        """スケジュール実行のテスト"""
        # 近い将来のスケジュール
        start_time = datetime.now() + timedelta(seconds=1)
        end_time = start_time + timedelta(minutes=30)
        
        schedule = RecordingSchedule(
            schedule_id="test_execution",
            station_id="TBS",
            program_title="実行テスト",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.NONE
        )
        
        self.scheduler.add_schedule(schedule)
        
        # 少し待ってスケジュールが実行されるのを確認
        time.sleep(2)
        
        # モックが呼ばれたことを確認
        mock_execute.assert_called_once()
        called_schedule_id = mock_execute.call_args[0][0]
        self.assertEqual(called_schedule_id, "test_execution")
    
    def test_schedule_statistics(self):
        """スケジュール統計のテスト"""
        now = datetime.now()
        
        schedules_data = [
            ("TBS", RepeatPattern.NONE, ScheduleStatus.SCHEDULED),
            ("QRR", RepeatPattern.DAILY, ScheduleStatus.COMPLETED),
            ("TBS", RepeatPattern.WEEKLY, ScheduleStatus.FAILED),
            ("LFR", RepeatPattern.NONE, ScheduleStatus.SCHEDULED)
        ]
        
        for i, (station_id, repeat, status) in enumerate(schedules_data):
            schedule = RecordingSchedule(
                schedule_id=f"stats_{i}",
                station_id=station_id,
                program_title=f"統計テスト{i}",
                start_time=now + timedelta(hours=i),
                end_time=now + timedelta(hours=i+1),
                repeat_pattern=repeat,
                status=status
            )
            self.scheduler.add_schedule(schedule)
        
        stats = self.scheduler.get_statistics()
        
        self.assertEqual(stats['total_schedules'], 4)
        self.assertEqual(stats['active_schedules'], 2)  # SCHEDULED のみ
        self.assertEqual(stats['stations']['TBS']['count'], 2)
        self.assertEqual(stats['stations']['QRR']['count'], 1)
        self.assertEqual(stats['repeat_patterns']['none'], 2)
        self.assertEqual(stats['repeat_patterns']['daily'], 1)
        self.assertEqual(stats['status_breakdown']['scheduled'], 2)
        self.assertEqual(stats['status_breakdown']['completed'], 1)
        self.assertEqual(stats['status_breakdown']['failed'], 1)
    
    def test_save_and_load_schedules(self):
        """スケジュール保存・読み込みのテスト"""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        schedule = RecordingSchedule(
            schedule_id="test_save_load",
            station_id="TBS",
            program_title="保存読み込みテスト",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.WEEKLY,
            tags=["テスト", "保存"]
        )
        
        self.scheduler.add_schedule(schedule)
        
        # 保存
        self.scheduler._save_schedules()
        
        # 新しいスケジューラーで読み込み
        new_scheduler = RecordingScheduler(
            recorder=self.mock_recorder,
            error_handler=self.mock_error_handler,
            notification_handler=self.mock_notification_handler,
            schedule_file=self.schedule_file
        )
        
        # スケジュールが復元されることを確認
        self.assertIn("test_save_load", new_scheduler.schedules)
        restored_schedule = new_scheduler.get_schedule("test_save_load")
        self.assertEqual(restored_schedule.program_title, "保存読み込みテスト")
        self.assertEqual(restored_schedule.repeat_pattern, RepeatPattern.WEEKLY)
        self.assertEqual(len(restored_schedule.tags), 2)
        
        new_scheduler.shutdown()
    
    def test_export_schedules(self):
        """スケジュール一覧エクスポートのテスト"""
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        schedule = RecordingSchedule(
            schedule_id="test_export",
            station_id="TBS",
            program_title="エクスポートテスト",
            start_time=start_time,
            end_time=end_time,
            repeat_pattern=RepeatPattern.NONE
        )
        
        self.scheduler.add_schedule(schedule)
        
        export_path = f"{self.temp_dir}/exported_schedules.json"
        self.scheduler.export_schedules(export_path)
        
        # エクスポートファイルの確認
        import os
        self.assertTrue(os.path.exists(export_path))
        
        with open(export_path, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
        
        self.assertEqual(len(exported_data), 1)
        self.assertEqual(exported_data[0]['program_title'], "エクスポートテスト")


class TestRecordingSchedulerLazyInitialization(unittest.TestCase):
    """RecordingScheduler 遅延初期化とプロセス終了のテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = f"{self.temp_dir}/test_scheduler.db"
    
    @patch('src.scheduler.BackgroundScheduler')
    def test_scheduler_not_started_on_init(self, mock_bg_scheduler_class):
        """初期化時にスケジューラーが自動起動されないことをテスト"""
        mock_scheduler = Mock()
        mock_bg_scheduler_class.return_value = mock_scheduler
        
        # RecordingSchedulerを作成
        scheduler = RecordingScheduler(db_path=self.db_path)
        
        # BackgroundSchedulerが作成されるが、startは呼ばれない
        mock_bg_scheduler_class.assert_called_once()
        mock_scheduler.start.assert_not_called()
        
        # is_runningがFalseであることを確認
        self.assertFalse(scheduler.is_running)
    
    @patch('src.scheduler.BackgroundScheduler')
    def test_ensure_scheduler_running(self, mock_bg_scheduler_class):
        """_ensure_scheduler_runningメソッドのテスト"""
        mock_scheduler = Mock()
        mock_bg_scheduler_class.return_value = mock_scheduler
        
        scheduler = RecordingScheduler(db_path=self.db_path)
        
        # 初期状態では起動していない
        self.assertFalse(scheduler.is_running)
        
        # _ensure_scheduler_runningを呼び出し
        scheduler._ensure_scheduler_running()
        
        # スケジューラーが起動されることを確認
        mock_scheduler.start.assert_called_once()
        self.assertTrue(scheduler.is_running)
        
        # 2回目の呼び出しでは再起動されないことを確認
        scheduler._ensure_scheduler_running()
        mock_scheduler.start.assert_called_once()  # 呼び出し回数は1回のまま
    
    @patch('src.scheduler.BackgroundScheduler')
    def test_add_schedule_triggers_scheduler_start(self, mock_bg_scheduler_class):
        """add_scheduleがスケジューラーの起動をトリガーすることをテスト"""
        mock_scheduler = Mock()
        mock_bg_scheduler_class.return_value = mock_scheduler
        
        scheduler = RecordingScheduler(db_path=self.db_path)
        
        # 初期状態では起動していない
        self.assertFalse(scheduler.is_running)
        
        # スケジュールを追加
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)
        
        schedule_id = scheduler.add_schedule(
            "TBS",  # 第1引数として station_id を渡す
            program_title="遅延初期化テスト",
            start_time=start_time,
            end_time=end_time
        )
        
        # スケジューラーが起動されることを確認
        mock_scheduler.start.assert_called_once()
        self.assertTrue(scheduler.is_running)
        
        # スケジュールが追加されることを確認
        self.assertIsNotNone(schedule_id)
    
    @patch('src.scheduler.BackgroundScheduler')
    def test_shutdown_with_not_running_scheduler(self, mock_bg_scheduler_class):
        """起動していないスケジューラーのshutdownテスト"""
        mock_scheduler = Mock()
        mock_scheduler.running = False
        mock_scheduler.state = 0  # STATE_STOPPED
        mock_bg_scheduler_class.return_value = mock_scheduler
        
        scheduler = RecordingScheduler(db_path=self.db_path)
        
        # shutdownを呼び出し（例外が発生しないことを確認）
        try:
            scheduler.shutdown()
        except Exception as e:
            self.fail(f"shutdown時に予期しない例外が発生: {e}")
        
        # スケジューラーのshutdownが呼ばれないことを確認
        mock_scheduler.shutdown.assert_not_called()
    
    @patch('src.scheduler.BackgroundScheduler')
    def test_shutdown_with_running_scheduler(self, mock_bg_scheduler_class):
        """起動中のスケジューラーのshutdownテスト"""
        mock_scheduler = Mock()
        mock_scheduler.running = True
        mock_scheduler.state = 1  # STATE_RUNNING
        mock_bg_scheduler_class.return_value = mock_scheduler
        
        scheduler = RecordingScheduler(db_path=self.db_path)
        
        # スケジューラーを起動状態にする
        scheduler._ensure_scheduler_running()
        
        # shutdownを呼び出し
        scheduler.shutdown()
        
        # スケジューラーのshutdownが呼ばれることを確認
        mock_scheduler.shutdown.assert_called_once()
        self.assertFalse(scheduler.is_running)
    
    @patch('src.scheduler.BackgroundScheduler')
    def test_shutdown_with_scheduler_error(self, mock_bg_scheduler_class):
        """スケジューラーshutdown時のエラーハンドリングテスト"""
        mock_scheduler = Mock()
        mock_scheduler.running = True
        mock_scheduler.state = 1  # STATE_RUNNING
        mock_scheduler.shutdown.side_effect = Exception("Scheduler shutdown error")
        mock_bg_scheduler_class.return_value = mock_scheduler
        
        scheduler = RecordingScheduler(db_path=self.db_path)
        
        # スケジューラーを起動状態にする
        scheduler._ensure_scheduler_running()
        
        # shutdownでエラーが発生しても例外が伝播しないことを確認
        try:
            scheduler.shutdown()
        except Exception as e:
            self.fail(f"shutdown時に予期しない例外が発生: {e}")
        
        # is_runningがFalseに設定されることを確認
        self.assertFalse(scheduler.is_running)
    
    def test_scheduler_without_apscheduler(self):
        """APSchedulerがない環境でのテスト"""
        with patch('src.scheduler.BackgroundScheduler', None):
            scheduler = RecordingScheduler(db_path=self.db_path)
            
            # schedulerがNoneに設定されることを確認
            self.assertIsNone(scheduler.scheduler)
            
            # shutdownが例外なく実行されることを確認
            try:
                scheduler.shutdown()
            except Exception as e:
                self.fail(f"shutdown時に予期しない例外が発生: {e}")


if __name__ == '__main__':
    unittest.main()