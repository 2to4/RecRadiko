"""
録音機能モジュールの単体テスト
"""

import unittest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import threading
import time
import queue

from src.recording import (
    RecordingManager, RecordingJob, RecordingStatus, RecordingProgress, RecordingError
)
from src.auth import RadikoAuthenticator
from src.program_info import ProgramInfoManager
from src.streaming import StreamingManager


class TestRecordingJob(unittest.TestCase):
    """RecordingJob クラスのテスト"""
    
    def test_recording_job_creation(self):
        """RecordingJob の作成テスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        job = RecordingJob(
            id="test_job_123",
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time,
            output_path="/tmp/test.aac",
            format="aac",
            bitrate=128
        )
        
        self.assertEqual(job.id, "test_job_123")
        self.assertEqual(job.station_id, "TBS")
        self.assertEqual(job.program_title, "テスト番組")
        self.assertEqual(job.status, RecordingStatus.PENDING)
        self.assertEqual(job.format, "aac")
        self.assertEqual(job.bitrate, 128)
    
    def test_recording_job_duration_calculation(self):
        """RecordingJob の継続時間自動計算テスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=90)
        
        job = RecordingJob(
            id="test_job_123",
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time,
            output_path="/tmp/test.aac",
            duration_seconds=0  # 自動計算される
        )
        
        self.assertEqual(job.duration_seconds, 5400)  # 90分 = 5400秒
        self.assertEqual(job.duration_minutes, 90)
    
    def test_recording_job_to_dict(self):
        """RecordingJob の辞書変換テスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        job = RecordingJob(
            id="test_job_123",
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time,
            output_path="/tmp/test.aac"
        )
        
        job_dict = job.to_dict()
        
        self.assertEqual(job_dict['id'], "test_job_123")
        self.assertEqual(job_dict['station_id'], "TBS")
        self.assertEqual(job_dict['status'], RecordingStatus.PENDING.value)
        self.assertIn('start_time', job_dict)
        self.assertIn('end_time', job_dict)
    
    def test_recording_job_from_dict(self):
        """RecordingJob の辞書からの復元テスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        job_dict = {
            'id': "test_job_123",
            'station_id': "TBS",
            'program_title': "テスト番組",
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'output_path': "/tmp/test.aac",
            'status': RecordingStatus.PENDING.value,
            'format': "aac",
            'bitrate': 128,
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'file_size': 0,
            'duration_seconds': 3600,
            'error_message': "",
            'retry_count': 0,
            'priority': 0
        }
        
        job = RecordingJob.from_dict(job_dict)
        
        self.assertEqual(job.id, "test_job_123")
        self.assertEqual(job.station_id, "TBS")
        self.assertEqual(job.status, RecordingStatus.PENDING)


class TestRecordingProgress(unittest.TestCase):
    """RecordingProgress クラスのテスト"""
    
    def test_recording_progress_creation(self):
        """RecordingProgress の作成テスト"""
        progress = RecordingProgress(
            job_id="test_job_123",
            status=RecordingStatus.RECORDING,
            progress_percent=50.5,
            bytes_written=1024000,
            elapsed_seconds=300,
            estimated_remaining_seconds=300
        )
        
        self.assertEqual(progress.job_id, "test_job_123")
        self.assertEqual(progress.status, RecordingStatus.RECORDING)
        self.assertEqual(progress.progress_percent, 50.5)
        self.assertEqual(progress.bytes_written, 1024000)
    
    def test_recording_progress_percent_bounds(self):
        """RecordingProgress の進捗率境界値テスト"""
        # 100%を超える場合
        progress_over = RecordingProgress(
            job_id="test_job",
            status=RecordingStatus.RECORDING,
            progress_percent=150.0,
            bytes_written=0,
            elapsed_seconds=0,
            estimated_remaining_seconds=0
        )
        self.assertEqual(progress_over.progress_percent, 100.0)
        
        # 0%未満の場合
        progress_under = RecordingProgress(
            job_id="test_job",
            status=RecordingStatus.RECORDING,
            progress_percent=-10.0,
            bytes_written=0,
            elapsed_seconds=0,
            estimated_remaining_seconds=0
        )
        self.assertEqual(progress_under.progress_percent, 0.0)


class TestRecordingManager(unittest.TestCase):
    """RecordingManager クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        
        # モックコンポーネント
        self.authenticator = Mock(spec=RadikoAuthenticator)
        self.program_manager = Mock(spec=ProgramInfoManager)
        self.streaming_manager = Mock(spec=StreamingManager)
        
        # RecordingManager を作成
        self.recording_manager = RecordingManager(
            authenticator=self.authenticator,
            program_manager=self.program_manager,
            streaming_manager=self.streaming_manager,
            output_dir=self.temp_dir,
            max_concurrent_jobs=2,
            max_retries=2
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # 録音マネージャーを停止
        self.recording_manager.shutdown()
        
        # 一時ディレクトリを削除
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_recording_manager_creation(self):
        """RecordingManager の作成テスト"""
        self.assertIsInstance(self.recording_manager, RecordingManager)
        self.assertEqual(self.recording_manager.max_concurrent_jobs, 2)
        self.assertEqual(self.recording_manager.max_retries, 2)
        self.assertTrue(self.recording_manager.output_dir.exists())
    
    @patch('subprocess.run')
    def test_find_ffmpeg_success(self, mock_run):
        """FFmpeg検出成功のテスト"""
        # 'which ffmpeg' の成功レスポンス
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "/usr/local/bin/ffmpeg\n"
        mock_run.return_value = mock_result
        
        ffmpeg_path = self.recording_manager._find_ffmpeg()
        
        self.assertEqual(ffmpeg_path, "/usr/local/bin/ffmpeg")
    
    @patch('subprocess.run')
    def test_find_ffmpeg_failure(self, mock_run):
        """FFmpeg検出失敗のテスト"""
        mock_run.side_effect = Exception("Command not found")
        
        with self.assertRaises(RecordingError):
            self.recording_manager._find_ffmpeg()
    
    def test_generate_job_id(self):
        """ジョブID生成のテスト"""
        station_id = "TBS"
        start_time = datetime(2024, 1, 1, 20, 0, 0)
        
        job_id = self.recording_manager._generate_job_id(station_id, start_time)
        
        self.assertIsInstance(job_id, str)
        self.assertTrue(job_id.startswith("TBS_"))
        self.assertIn("1704106800", job_id)  # timestamp部分
    
    def test_generate_output_path(self):
        """出力パス生成のテスト"""
        station_id = "TBS"
        program_title = "テスト番組"
        start_time = datetime(2024, 1, 1, 20, 0, 0)
        format = "aac"
        
        output_path = self.recording_manager._generate_output_path(
            station_id, program_title, start_time, format
        )
        
        self.assertIsInstance(output_path, str)
        self.assertTrue(output_path.endswith(".aac"))
        self.assertIn("TBS", output_path)
        self.assertIn("2024", output_path)
    
    def test_sanitize_filename(self):
        """ファイル名サニタイズのテスト"""
        # 危険な文字を含むファイル名
        unsafe_filename = "テスト<番組>:2024/01/01"
        safe_filename = self.recording_manager._sanitize_filename(unsafe_filename)
        
        self.assertNotIn("<", safe_filename)
        self.assertNotIn(">", safe_filename)
        self.assertNotIn(":", safe_filename)
        self.assertNotIn("/", safe_filename)
        
        # 長すぎるファイル名
        long_filename = "a" * 150
        safe_long = self.recording_manager._sanitize_filename(long_filename)
        self.assertLessEqual(len(safe_long), 100)
        
        # 空文字列
        empty_safe = self.recording_manager._sanitize_filename("")
        self.assertEqual(empty_safe, "untitled")
    
    def test_create_recording_job(self):
        """録音ジョブ作成のテスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        job_id = self.recording_manager.create_recording_job(
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time,
            format="aac",
            bitrate=192
        )
        
        self.assertIsInstance(job_id, str)
        self.assertIn(job_id, self.recording_manager.jobs)
        
        job = self.recording_manager.jobs[job_id]
        self.assertEqual(job.station_id, "TBS")
        self.assertEqual(job.program_title, "テスト番組")
        self.assertEqual(job.format, "aac")
        self.assertEqual(job.bitrate, 192)
    
    def test_get_job_status(self):
        """ジョブステータス取得のテスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        job_id = self.recording_manager.create_recording_job(
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time
        )
        
        job = self.recording_manager.get_job_status(job_id)
        
        self.assertIsNotNone(job)
        self.assertEqual(job.id, job_id)
        self.assertEqual(job.status, RecordingStatus.PENDING)
        
        # 存在しないジョブ
        nonexistent_job = self.recording_manager.get_job_status("nonexistent")
        self.assertIsNone(nonexistent_job)
    
    def test_get_job_progress(self):
        """ジョブ進捗取得のテスト"""
        job_id = "test_job_123"
        
        # 進捗が存在しない場合
        progress = self.recording_manager.get_job_progress(job_id)
        self.assertIsNone(progress)
        
        # 進捗を手動で設定
        test_progress = RecordingProgress(
            job_id=job_id,
            status=RecordingStatus.RECORDING,
            progress_percent=50.0,
            bytes_written=1024,
            elapsed_seconds=300,
            estimated_remaining_seconds=300
        )
        self.recording_manager.job_progress[job_id] = test_progress
        
        # 進捗取得
        progress = self.recording_manager.get_job_progress(job_id)
        self.assertIsNotNone(progress)
        self.assertEqual(progress.job_id, job_id)
        self.assertEqual(progress.progress_percent, 50.0)
    
    def test_get_active_jobs(self):
        """アクティブジョブ一覧取得のテスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        # ジョブを作成
        job_id1 = self.recording_manager.create_recording_job(
            station_id="TBS",
            program_title="番組1",
            start_time=start_time,
            end_time=end_time
        )
        
        job_id2 = self.recording_manager.create_recording_job(
            station_id="QRR",
            program_title="番組2",
            start_time=start_time,
            end_time=end_time
        )
        
        # 1つのジョブを録音中に設定
        self.recording_manager.jobs[job_id1].status = RecordingStatus.RECORDING
        
        # アクティブジョブ取得
        active_jobs = self.recording_manager.get_active_jobs()
        
        self.assertEqual(len(active_jobs), 1)
        self.assertEqual(active_jobs[0].id, job_id1)
    
    def test_get_all_jobs(self):
        """全ジョブ一覧取得のテスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        # 複数のジョブを作成
        job_id1 = self.recording_manager.create_recording_job(
            station_id="TBS",
            program_title="番組1",
            start_time=start_time,
            end_time=end_time
        )
        
        job_id2 = self.recording_manager.create_recording_job(
            station_id="QRR",
            program_title="番組2",
            start_time=start_time,
            end_time=end_time
        )
        
        all_jobs = self.recording_manager.get_all_jobs()
        
        self.assertEqual(len(all_jobs), 2)
        job_ids = [job.id for job in all_jobs]
        self.assertIn(job_id1, job_ids)
        self.assertIn(job_id2, job_ids)
    
    def test_cancel_job(self):
        """ジョブキャンセルのテスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        job_id = self.recording_manager.create_recording_job(
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time
        )
        
        # ジョブをキャンセル
        result = self.recording_manager.cancel_job(job_id)
        
        self.assertTrue(result)
        
        job = self.recording_manager.get_job_status(job_id)
        self.assertEqual(job.status, RecordingStatus.CANCELLED)
        self.assertIsNotNone(job.completed_at)
        
        # 存在しないジョブのキャンセル
        result_nonexistent = self.recording_manager.cancel_job("nonexistent")
        self.assertFalse(result_nonexistent)
    
    def test_cancel_completed_job(self):
        """完了済みジョブキャンセルのテスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        job_id = self.recording_manager.create_recording_job(
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time
        )
        
        # ジョブを完了状態に設定
        self.recording_manager.jobs[job_id].status = RecordingStatus.COMPLETED
        
        # 完了済みジョブのキャンセルは失敗するべき
        result = self.recording_manager.cancel_job(job_id)
        self.assertFalse(result)
    
    def test_progress_callback(self):
        """進捗コールバックのテスト"""
        callback_called = []
        
        def test_callback(progress):
            callback_called.append(progress)
        
        # コールバック追加
        self.recording_manager.add_progress_callback(test_callback)
        
        # 手動で進捗コールバックを呼び出し
        test_progress = RecordingProgress(
            job_id="test_job",
            status=RecordingStatus.RECORDING,
            progress_percent=50.0,
            bytes_written=1024,
            elapsed_seconds=300,
            estimated_remaining_seconds=300
        )
        
        for callback in self.recording_manager.progress_callbacks:
            callback(test_progress)
        
        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0].job_id, "test_job")
        
        # コールバック削除
        self.recording_manager.remove_progress_callback(test_callback)
        self.assertEqual(len(self.recording_manager.progress_callbacks), 0)
    
    def test_save_and_load_jobs(self):
        """ジョブ保存・読み込みのテスト"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        # ジョブを作成
        job_id = self.recording_manager.create_recording_job(
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time
        )
        
        # ファイルに保存
        save_path = f"{self.temp_dir}/jobs.json"
        self.recording_manager.save_jobs_to_file(save_path)
        
        # 既存のジョブをクリア
        self.recording_manager.jobs.clear()
        
        # ファイルから読み込み
        self.recording_manager.load_jobs_from_file(save_path)
        
        # ジョブが復元されることを確認
        self.assertIn(job_id, self.recording_manager.jobs)
        restored_job = self.recording_manager.jobs[job_id]
        self.assertEqual(restored_job.station_id, "TBS")
        self.assertEqual(restored_job.program_title, "テスト番組")
    
    def test_cleanup_old_jobs(self):
        """古いジョブクリーンアップのテスト"""
        start_time = datetime.now() - timedelta(days=60)
        end_time = start_time + timedelta(hours=1)
        
        # 古いジョブを作成
        job_id = self.recording_manager.create_recording_job(
            station_id="TBS",
            program_title="古い番組",
            start_time=start_time,
            end_time=end_time
        )
        
        # ジョブを完了状態に設定し、完了日時を過去に設定
        job = self.recording_manager.jobs[job_id]
        job.status = RecordingStatus.COMPLETED
        job.completed_at = datetime.now() - timedelta(days=60)
        
        # クリーンアップ実行（30日より古いものを削除）
        self.recording_manager.cleanup_old_jobs(30)
        
        # 古いジョブが削除されることを確認
        self.assertNotIn(job_id, self.recording_manager.jobs)
    
    def test_get_audio_codec(self):
        """音声コーデック取得のテスト"""
        # 各形式のコーデックマッピングをテスト
        self.assertEqual(self.recording_manager._get_audio_codec("aac"), "aac")
        self.assertEqual(self.recording_manager._get_audio_codec("mp3"), "libmp3lame")
        self.assertEqual(self.recording_manager._get_audio_codec("wav"), "pcm_s16le")
        self.assertEqual(self.recording_manager._get_audio_codec("flac"), "flac")
        self.assertEqual(self.recording_manager._get_audio_codec("ogg"), "libvorbis")
        
        # 不明な形式はデフォルトでaac
        self.assertEqual(self.recording_manager._get_audio_codec("unknown"), "aac")


if __name__ == '__main__':
    unittest.main()