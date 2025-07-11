"""
ファイル管理モジュールの単体テスト
"""

import unittest
import tempfile
import json
import os
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

from src.file_manager import FileManager, FileMetadata, StorageInfo, FileManagerError


class TestFileMetadata(unittest.TestCase):
    """FileMetadata クラスのテスト"""
    
    def test_file_metadata_creation(self):
        """FileMetadata の作成テスト"""
        recorded_at = datetime.now()
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        
        metadata = FileMetadata(
            file_path="/tmp/test.aac",
            station_id="TBS",
            program_title="テスト番組",
            recorded_at=recorded_at,
            start_time=start_time,
            end_time=end_time,
            file_size=1024000,
            duration_seconds=3600,
            format="aac",
            bitrate=128,
            performers=["出演者1", "出演者2"],
            genre="音楽",
            description="テスト番組の説明"
        )
        
        self.assertEqual(metadata.file_path, "/tmp/test.aac")
        self.assertEqual(metadata.station_id, "TBS")
        self.assertEqual(metadata.program_title, "テスト番組")
        self.assertEqual(metadata.file_size, 1024000)
        self.assertEqual(metadata.duration_seconds, 3600)
        self.assertEqual(metadata.format, "aac")
        self.assertEqual(len(metadata.performers), 2)
    
    def test_file_metadata_to_dict(self):
        """FileMetadata の辞書変換テスト"""
        recorded_at = datetime.now()
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        
        metadata = FileMetadata(
            file_path="/tmp/test.aac",
            station_id="TBS",
            program_title="テスト番組",
            recorded_at=recorded_at,
            start_time=start_time,
            end_time=end_time,
            file_size=1024000,
            duration_seconds=3600,
            format="aac",
            bitrate=128
        )
        
        metadata_dict = metadata.to_dict()
        
        self.assertEqual(metadata_dict['file_path'], "/tmp/test.aac")
        self.assertEqual(metadata_dict['station_id'], "TBS")
        self.assertIn('recorded_at', metadata_dict)
        self.assertIn('start_time', metadata_dict)
        self.assertIn('end_time', metadata_dict)
    
    def test_file_metadata_from_dict(self):
        """FileMetadata の辞書からの復元テスト"""
        recorded_at = datetime.now()
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        
        metadata_dict = {
            'file_path': "/tmp/test.aac",
            'station_id': "TBS",
            'program_title': "テスト番組",
            'recorded_at': recorded_at.isoformat(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'file_size': 1024000,
            'duration_seconds': 3600,
            'format': "aac",
            'bitrate': 128,
            'performers': ["出演者1"],
            'genre': "音楽",
            'description': "説明",
            'checksum': "abc123",
            'created_at': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat()
        }
        
        metadata = FileMetadata.from_dict(metadata_dict)
        
        self.assertEqual(metadata.file_path, "/tmp/test.aac")
        self.assertEqual(metadata.station_id, "TBS")
        self.assertEqual(metadata.program_title, "テスト番組")


class TestStorageInfo(unittest.TestCase):
    """StorageInfo クラスのテスト"""
    
    def test_storage_info_creation(self):
        """StorageInfo の作成テスト"""
        storage_info = StorageInfo(
            total_space=1000000000,  # 1GB
            used_space=400000000,    # 400MB
            free_space=600000000,    # 600MB
            recording_files_size=200000000,  # 200MB
            file_count=10
        )
        
        self.assertEqual(storage_info.total_space, 1000000000)
        self.assertEqual(storage_info.used_space, 400000000)
        self.assertEqual(storage_info.free_space, 600000000)
        self.assertEqual(storage_info.file_count, 10)
    
    def test_storage_info_usage_percent(self):
        """StorageInfo の使用率計算テスト"""
        storage_info = StorageInfo(
            total_space=1000000000,
            used_space=400000000,
            free_space=600000000,
            recording_files_size=200000000,
            file_count=10
        )
        
        self.assertEqual(storage_info.usage_percent, 40.0)  # 400MB / 1GB = 40%
    
    def test_storage_info_free_space_gb(self):
        """StorageInfo の空き容量GB計算テスト"""
        storage_info = StorageInfo(
            total_space=1000000000,
            used_space=400000000,
            free_space=600000000,
            recording_files_size=200000000,
            file_count=10
        )
        
        self.assertAlmostEqual(storage_info.free_space_gb, 0.558, places=2)


class TestFileManager(unittest.TestCase):
    """FileManager クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.metadata_file = f"{self.temp_dir}/metadata.json"
        
        self.file_manager = FileManager(
            base_dir=self.temp_dir,
            metadata_file="metadata.json",
            retention_days=30,
            min_free_space_gb=1.0,
            auto_cleanup_enabled=False  # テスト中は無効化
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.file_manager.shutdown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_file_manager_creation(self):
        """FileManager の作成テスト"""
        self.assertIsInstance(self.file_manager, FileManager)
        self.assertTrue(self.file_manager.base_dir.exists())
        self.assertEqual(self.file_manager.retention_days, 30)
        self.assertEqual(self.file_manager.min_free_space_gb, 1.0)
    
    def test_sanitize_filename(self):
        """ファイル名サニタイズのテスト"""
        # 危険な文字を含むファイル名
        unsafe_filename = "テスト<番組>:2024/01/01|危険*.txt"
        safe_filename = self.file_manager._sanitize_filename(unsafe_filename)
        
        # 危険な文字が置換されることを確認
        for char in '<>:"/\\|?*\0':
            self.assertNotIn(char, safe_filename)
        
        # 長すぎるファイル名の切り詰め
        long_filename = "a" * 150
        safe_long = self.file_manager._sanitize_filename(long_filename)
        self.assertLessEqual(len(safe_long), 100)
        
        # 空文字列の処理
        empty_safe = self.file_manager._sanitize_filename("")
        self.assertEqual(empty_safe, "untitled")
        
        # 正常なファイル名はそのまま
        normal_filename = "テスト番組_20240101"
        safe_normal = self.file_manager._sanitize_filename(normal_filename)
        self.assertEqual(safe_normal, normal_filename)
    
    def test_generate_file_path(self):
        """ファイルパス生成のテスト"""
        start_time = datetime(2024, 1, 1, 20, 0, 0)
        
        file_path = self.file_manager.generate_file_path(
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            format="aac"
        )
        
        self.assertIsInstance(file_path, str)
        self.assertTrue(file_path.endswith(".aac"))
        self.assertIn("TBS", file_path)
        self.assertIn("2024", file_path)
        self.assertIn("01", file_path)  # 月
        
        # ディレクトリが作成されることを確認
        file_path_obj = Path(file_path)
        self.assertTrue(file_path_obj.parent.exists())
    
    def test_generate_file_path_duplicate_handling(self):
        """重複ファイルパス処理のテスト"""
        start_time = datetime(2024, 1, 1, 20, 0, 0)
        
        # 最初のファイルパス
        file_path1 = self.file_manager.generate_file_path(
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            format="aac"
        )
        
        # ファイルを作成して重複をシミュレート
        Path(file_path1).touch()
        
        # 2番目のファイルパス（重複回避されるべき）
        file_path2 = self.file_manager.generate_file_path(
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            format="aac"
        )
        
        self.assertNotEqual(file_path1, file_path2)
        self.assertIn("_1.aac", file_path2)
    
    def test_calculate_checksum(self):
        """チェックサム計算のテスト"""
        # テストファイルを作成
        test_file = f"{self.temp_dir}/test_checksum.txt"
        test_content = b"test file content for checksum"
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        checksum = self.file_manager._calculate_checksum(test_file)
        
        self.assertIsInstance(checksum, str)
        self.assertEqual(len(checksum), 32)  # MD5は32文字
        
        # 同じ内容なら同じチェックサム
        checksum2 = self.file_manager._calculate_checksum(test_file)
        self.assertEqual(checksum, checksum2)
    
    def test_register_file(self):
        """ファイル登録のテスト"""
        # テストファイルを作成
        test_file = f"{self.temp_dir}/test_register.aac"
        test_content = b"test audio content"
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        
        result = self.file_manager.register_file(
            file_path=test_file,
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time,
            format="aac",
            bitrate=128,
            performers=["出演者1"],
            genre="音楽",
            description="テスト説明"
        )
        
        self.assertTrue(result)
        
        # メタデータキャッシュに登録されることを確認
        self.assertIn(test_file, self.file_manager.metadata_cache)
        
        metadata = self.file_manager.metadata_cache[test_file]
        self.assertEqual(metadata.station_id, "TBS")
        self.assertEqual(metadata.program_title, "テスト番組")
        self.assertEqual(metadata.format, "aac")
        self.assertEqual(len(metadata.performers), 1)
    
    def test_register_file_nonexistent(self):
        """存在しないファイル登録のテスト"""
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        
        result = self.file_manager.register_file(
            file_path="/nonexistent/file.aac",
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time,
            format="aac",
            bitrate=128
        )
        
        self.assertFalse(result)
    
    def test_get_file_metadata(self):
        """ファイルメタデータ取得のテスト"""
        # テストファイルを登録
        test_file = f"{self.temp_dir}/test_get_metadata.aac"
        Path(test_file).touch()
        
        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now()
        
        self.file_manager.register_file(
            file_path=test_file,
            station_id="TBS",
            program_title="テスト番組",
            start_time=start_time,
            end_time=end_time,
            format="aac",
            bitrate=128
        )
        
        # メタデータ取得
        metadata = self.file_manager.get_file_metadata(test_file)
        
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.station_id, "TBS")
        self.assertEqual(metadata.program_title, "テスト番組")
        
        # 存在しないファイル
        nonexistent_metadata = self.file_manager.get_file_metadata("/nonexistent.aac")
        self.assertIsNone(nonexistent_metadata)
    
    def test_list_files(self):
        """ファイル一覧取得のテスト"""
        # 複数のテストファイルを登録
        files_data = [
            ("TBS", "番組1", datetime(2024, 1, 1, 20, 0)),
            ("QRR", "番組2", datetime(2024, 1, 2, 21, 0)),
            ("TBS", "番組3", datetime(2024, 1, 3, 22, 0))
        ]
        
        for i, (station_id, title, start_time) in enumerate(files_data):
            test_file = f"{self.temp_dir}/test_list_{i}.aac"
            Path(test_file).touch()
            
            self.file_manager.register_file(
                file_path=test_file,
                station_id=station_id,
                program_title=title,
                start_time=start_time,
                end_time=start_time + timedelta(hours=1),
                format="aac",
                bitrate=128
            )
        
        # 全ファイル取得
        all_files = self.file_manager.list_files()
        self.assertEqual(len(all_files), 3)
        
        # 放送局でフィルター
        tbs_files = self.file_manager.list_files(station_id="TBS")
        self.assertEqual(len(tbs_files), 2)
        
        # 日付範囲でフィルター
        date_filtered = self.file_manager.list_files(
            start_date=datetime(2024, 1, 2),
            end_date=datetime(2024, 1, 3)
        )
        self.assertEqual(len(date_filtered), 1)
        
        # タイトルでフィルター
        title_filtered = self.file_manager.list_files(program_title_filter="番組1")
        self.assertEqual(len(title_filtered), 1)
    
    def test_search_files(self):
        """ファイル検索のテスト"""
        # テストファイルを登録
        test_file = f"{self.temp_dir}/test_search.aac"
        Path(test_file).touch()
        
        self.file_manager.register_file(
            file_path=test_file,
            station_id="TBS",
            program_title="音楽番組",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            format="aac",
            bitrate=128,
            performers=["歌手A", "歌手B"],
            genre="ポップス",
            description="人気の音楽番組"
        )
        
        # タイトルで検索
        title_results = self.file_manager.search_files("音楽")
        self.assertEqual(len(title_results), 1)
        
        # 出演者で検索
        performer_results = self.file_manager.search_files("歌手A")
        self.assertEqual(len(performer_results), 1)
        
        # 説明で検索
        desc_results = self.file_manager.search_files("人気")
        self.assertEqual(len(desc_results), 1)
        
        # 放送局で検索
        station_results = self.file_manager.search_files("TBS")
        self.assertEqual(len(station_results), 1)
        
        # ヒットしない検索
        no_results = self.file_manager.search_files("存在しない")
        self.assertEqual(len(no_results), 0)
    
    def test_delete_file(self):
        """ファイル削除のテスト"""
        # テストファイルを作成・登録
        test_file = f"{self.temp_dir}/test_delete.aac"
        Path(test_file).touch()
        
        self.file_manager.register_file(
            file_path=test_file,
            station_id="TBS",
            program_title="削除テスト",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            format="aac",
            bitrate=128
        )
        
        # ファイル削除
        result = self.file_manager.delete_file(test_file, remove_file=True)
        
        self.assertTrue(result)
        self.assertFalse(Path(test_file).exists())
        self.assertNotIn(test_file, self.file_manager.metadata_cache)
    
    def test_delete_file_metadata_only(self):
        """メタデータのみ削除のテスト"""
        # テストファイルを作成・登録
        test_file = f"{self.temp_dir}/test_delete_meta.aac"
        Path(test_file).touch()
        
        self.file_manager.register_file(
            file_path=test_file,
            station_id="TBS",
            program_title="メタデータ削除テスト",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            format="aac",
            bitrate=128
        )
        
        # メタデータのみ削除
        result = self.file_manager.delete_file(test_file, remove_file=False)
        
        self.assertTrue(result)
        self.assertTrue(Path(test_file).exists())  # ファイルは残る
        self.assertNotIn(test_file, self.file_manager.metadata_cache)  # メタデータは削除
    
    @patch('shutil.disk_usage')
    def test_get_storage_info(self, mock_disk_usage):
        """ストレージ情報取得のテスト"""
        # ディスク使用量をモック
        mock_disk_usage.return_value = (
            1000000000,  # total
            400000000,   # used 
            600000000    # free
        )
        
        # テストファイルを登録
        test_file = f"{self.temp_dir}/test_storage.aac"
        test_content = b"a" * 1024  # 1KB
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        self.file_manager.register_file(
            file_path=test_file,
            station_id="TBS",
            program_title="ストレージテスト",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            format="aac",
            bitrate=128
        )
        
        storage_info = self.file_manager.get_storage_info()
        
        self.assertIsInstance(storage_info, StorageInfo)
        self.assertEqual(storage_info.total_space, 1000000000)
        self.assertEqual(storage_info.free_space, 600000000)
        self.assertEqual(storage_info.file_count, 1)
        self.assertEqual(storage_info.recording_files_size, 1024)
    
    def test_cleanup_old_files(self):
        """古いファイルクリーンアップのテスト"""
        # 古いテストファイルを作成（サイズあり）
        old_file = f"{self.temp_dir}/old_test.aac"
        with open(old_file, 'wb') as f:
            f.write(b'\x00' * 1024)  # 1KBのテストファイル
        
        old_time = datetime.now() - timedelta(days=60)
        
        self.file_manager.register_file(
            file_path=old_file,
            station_id="TBS",
            program_title="古い番組",
            start_time=old_time,
            end_time=old_time + timedelta(hours=1),
            format="aac",
            bitrate=128
        )
        
        # 録音日時を古い日付に変更
        metadata = self.file_manager.metadata_cache[old_file]
        metadata.recorded_at = old_time
        
        # クリーンアップ実行
        deleted_count, freed_space = self.file_manager.cleanup_old_files(30)
        
        self.assertEqual(deleted_count, 1)
        self.assertGreater(freed_space, 0)
        self.assertNotIn(old_file, self.file_manager.metadata_cache)
    
    @patch('shutil.disk_usage')
    def test_cleanup_by_disk_space(self, mock_disk_usage):
        """ディスク容量不足時のクリーンアップのテスト"""
        # 容量不足をシミュレート
        mock_disk_usage.return_value = (
            1000000000,  # total (1GB)
            500000000,   # used 
            500000000    # free (500MB) - 不足
        )
        
        # テストファイルを作成
        test_file = f"{self.temp_dir}/space_test.aac"
        test_content = b"a" * (10 * 1024 * 1024)  # 10MB
        
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        old_time = datetime.now() - timedelta(days=1)
        
        self.file_manager.register_file(
            file_path=test_file,
            station_id="TBS",
            program_title="容量テスト",
            start_time=old_time,
            end_time=old_time + timedelta(hours=1),
            format="aac",
            bitrate=128
        )
        
        # アクセス日時を古くして削除対象にする
        metadata = self.file_manager.metadata_cache[test_file]
        metadata.last_accessed = old_time
        
        # クリーンアップ実行（1GB = 1.0GB必要）
        deleted_count, freed_space = self.file_manager.cleanup_by_disk_space(1.0)
        
        self.assertEqual(deleted_count, 1)
        self.assertGreater(freed_space, 0)
    
    def test_verify_files(self):
        """ファイル整合性チェックのテスト"""
        # 存在するファイル
        existing_file = f"{self.temp_dir}/existing.aac"
        Path(existing_file).touch()
        
        self.file_manager.register_file(
            file_path=existing_file,
            station_id="TBS",
            program_title="存在ファイル",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            format="aac",
            bitrate=128
        )
        
        # 一時的に存在するファイルを作成して登録後に削除
        temp_file = f"{self.temp_dir}/temp_will_be_deleted.aac"
        Path(temp_file).touch()
        
        self.file_manager.register_file(
            file_path=temp_file,
            station_id="QRR",
            program_title="削除予定ファイル",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            format="aac",
            bitrate=128
        )
        
        # 登録後にファイルを削除（存在しないファイルをシミュレート）
        Path(temp_file).unlink()
        
        # 登録前の状態を確認
        self.assertEqual(len(self.file_manager.metadata_cache), 2)
        
        # 整合性チェック実行
        corrupted_files = self.file_manager.verify_files()
        
        # 存在しないファイルが検出される
        self.assertEqual(len(corrupted_files), 1)
        self.assertEqual(corrupted_files[0], temp_file)
        
        # 存在しないファイルのメタデータが削除される
        self.assertNotIn(temp_file, self.file_manager.metadata_cache)
        self.assertIn(existing_file, self.file_manager.metadata_cache)
    
    def test_get_statistics(self):
        """統計情報取得のテスト"""
        # 複数のテストファイルを登録
        files_data = [
            ("TBS", "番組1", "aac", 1024),
            ("TBS", "番組2", "mp3", 2048),
            ("QRR", "番組3", "aac", 1536)
        ]
        
        for i, (station_id, title, format, size) in enumerate(files_data):
            test_file = f"{self.temp_dir}/stats_test_{i}.{format}"
            test_content = b"a" * size
            
            with open(test_file, 'wb') as f:
                f.write(test_content)
            
            start_time = datetime.now() - timedelta(hours=1)
            
            self.file_manager.register_file(
                file_path=test_file,
                station_id=station_id,
                program_title=title,
                start_time=start_time,
                end_time=start_time + timedelta(hours=1),
                format=format,
                bitrate=128
            )
        
        stats = self.file_manager.get_statistics()
        
        self.assertEqual(stats['total_files'], 3)
        self.assertGreater(stats['total_duration_hours'], 0)
        self.assertGreater(stats['total_size_gb'], 0)
        
        # 放送局別統計
        self.assertEqual(stats['stations']['TBS']['count'], 2)
        self.assertEqual(stats['stations']['QRR']['count'], 1)
        
        # 形式別統計
        self.assertEqual(stats['formats']['aac']['count'], 2)
        self.assertEqual(stats['formats']['mp3']['count'], 1)
    
    def test_export_metadata_json(self):
        """メタデータJSONエクスポートのテスト"""
        # テストファイルを登録
        test_file = f"{self.temp_dir}/export_test.aac"
        Path(test_file).touch()
        
        self.file_manager.register_file(
            file_path=test_file,
            station_id="TBS",
            program_title="エクスポートテスト",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            format="aac",
            bitrate=128
        )
        
        export_path = f"{self.temp_dir}/exported_metadata.json"
        self.file_manager.export_metadata(export_path, "json")
        
        # エクスポートファイルの確認
        self.assertTrue(Path(export_path).exists())
        
        with open(export_path, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
        
        self.assertEqual(len(exported_data), 1)
        self.assertEqual(exported_data[0]['program_title'], "エクスポートテスト")
    
    def test_export_metadata_csv(self):
        """メタデータCSVエクスポートのテスト"""
        # テストファイルを登録
        test_file = f"{self.temp_dir}/csv_export_test.aac"
        Path(test_file).touch()
        
        self.file_manager.register_file(
            file_path=test_file,
            station_id="TBS",
            program_title="CSVエクスポートテスト",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            format="aac",
            bitrate=128
        )
        
        export_path = f"{self.temp_dir}/exported_metadata.csv"
        self.file_manager.export_metadata(export_path, "csv")
        
        # エクスポートファイルの確認
        self.assertTrue(Path(export_path).exists())
        
        with open(export_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("CSVエクスポートテスト", content)
            self.assertIn("TBS", content)
    
    def test_metadata_save_and_load(self):
        """メタデータ保存・読み込みのテスト"""
        # テストファイルを登録
        test_file = f"{self.temp_dir}/save_load_test.aac"
        Path(test_file).touch()
        
        self.file_manager.register_file(
            file_path=test_file,
            station_id="TBS",
            program_title="保存読み込みテスト",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            format="aac",
            bitrate=128
        )
        
        # メタデータを保存
        self.file_manager._save_metadata()
        
        # 新しいファイルマネージャーで読み込み
        new_manager = FileManager(
            base_dir=self.temp_dir,
            metadata_file="metadata.json",
            auto_cleanup_enabled=False
        )
        
        # メタデータが復元されることを確認
        self.assertIn(test_file, new_manager.metadata_cache)
        metadata = new_manager.get_file_metadata(test_file)
        self.assertEqual(metadata.program_title, "保存読み込みテスト")
        
        new_manager.shutdown()


if __name__ == '__main__':
    unittest.main()