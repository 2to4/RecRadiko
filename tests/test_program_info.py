"""
ProgramInfoManager単体テスト（TDD手法）

TEST_REDESIGN_PLANに基づく実環境重視テスト。
番組情報管理・SQLite操作・放送局管理・データクラス機能を実環境でテスト。
"""

import unittest
import sqlite3
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET

# テスト対象
from src.program_info import (
    ProgramInfoManager, ProgramInfo, Station, Program, ProgramInfoError
)
from src.auth import RadikoAuthenticator
from tests.utils.test_environment import TemporaryTestEnvironment, RealEnvironmentTestBase


class TestProgramInfoDataClasses(unittest.TestCase, RealEnvironmentTestBase):
    """ProgramInfo データクラス機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_01_ProgramInfoデータクラス機能(self):
        """
        TDD Test: ProgramInfoデータクラス機能
        
        ProgramInfoの各種プロパティとメソッドが正常動作することを確認
        """
        # Given: 番組情報データ
        start_time = datetime(2025, 7, 21, 14, 0, 0)
        end_time = datetime(2025, 7, 21, 16, 30, 0)
        
        program_info = ProgramInfo(
            program_id="TBS_20250721_140000",
            station_id="TBS",
            station_name="TBSラジオ",
            title="アフタヌーンプログラム",
            start_time=start_time,
            end_time=end_time,
            description="午後の音楽番組です",
            performers=["山田太郎", "田中花子"],
            genre="音楽"
        )
        
        # Then: 基本プロパティが正しく設定される
        self.assertEqual(program_info.program_id, "TBS_20250721_140000")
        self.assertEqual(program_info.station_id, "TBS")
        self.assertEqual(program_info.title, "アフタヌーンプログラム")
        self.assertEqual(len(program_info.performers), 2)
        
        # And: 時間計算プロパティが正しく動作する
        self.assertEqual(program_info.duration_minutes, 150)  # 2.5時間
        self.assertEqual(program_info.duration_seconds, 9000)  # 150分
        
        # And: 深夜番組判定が正しく動作する
        self.assertFalse(program_info.is_midnight_program)  # 14時開始は深夜番組ではない
        
        # And: 表示用時刻が正しく取得される
        self.assertEqual(program_info.display_start_time, "14:00")
        self.assertEqual(program_info.display_end_time, "16:30")
        self.assertEqual(program_info.display_date, "2025-07-21")
    
    def test_02_深夜番組処理機能(self):
        """
        TDD Test: 深夜番組処理機能
        
        深夜番組の特殊処理（24時間表示、日付跨ぎ）が正常動作することを確認
        """
        # Given: 深夜番組データ（翌日1:00開始）
        start_time = datetime(2025, 7, 22, 1, 0, 0)  # 深夜1:00
        end_time = datetime(2025, 7, 22, 3, 0, 0)    # 深夜3:00
        
        midnight_program = ProgramInfo(
            program_id="TBS_20250722_010000", 
            station_id="TBS",
            station_name="TBSラジオ",
            title="深夜の音楽番組",
            start_time=start_time,
            end_time=end_time,
            description="深夜のリラックス音楽",
            performers=["深夜DJ"],
            genre="音楽"
        )
        
        # Then: 深夜番組として正しく認識される
        self.assertTrue(midnight_program.is_midnight_program)
        
        # And: 24時間表示で時刻が表示される
        self.assertEqual(midnight_program.display_start_time, "25:00")  # 1:00 → 25:00
        self.assertEqual(midnight_program.display_end_time, "27:00")   # 3:00 → 27:00
        
        # And: 表示日付が前日扱いになる
        self.assertEqual(midnight_program.display_date, "2025-07-21")  # 前日扱い
        
        # And: 時間計算は正常に動作する
        self.assertEqual(midnight_program.duration_minutes, 120)  # 2時間
    
    def test_03_メタデータ・ファイル名生成機能(self):
        """
        TDD Test: メタデータ・ファイル名生成機能
        
        ID3タグメタデータとファイル名の生成が正常動作することを確認
        """
        # Given: 番組情報データ
        program_info = ProgramInfo(
            program_id="QRR_20250721_070000",
            station_id="QRR",
            station_name="文化放送",
            title="おはよう！文化放送",
            start_time=datetime(2025, 7, 21, 7, 0, 0),
            end_time=datetime(2025, 7, 21, 9, 0, 0),
            description="朝の情報番組です",
            performers=["朝の司会者A", "朝の司会者B"],
            genre="情報・ワイドショー"
        )
        
        # When: メタデータを生成
        metadata = program_info.to_metadata()
        
        # Then: 正しいID3タグ情報が生成される
        self.assertEqual(metadata['title'], "おはよう！文化放送")
        self.assertEqual(metadata['artist'], "朝の司会者A, 朝の司会者B")
        self.assertEqual(metadata['album'], "文化放送")
        self.assertEqual(metadata['date'], "2025-07-21")
        self.assertEqual(metadata['genre'], "Radio")
        self.assertEqual(metadata['comment'], "朝の情報番組です")
        
        # When: ファイル名を生成
        filename = program_info.to_filename()
        
        # Then: 正しいファイル名が生成される
        expected_filename = "QRR_20250721_おはよう_文化放送.mp3"
        self.assertEqual(filename, expected_filename)
        
        # And: 特殊文字が適切にエスケープされる
        special_program = ProgramInfo(
            program_id="TBS_20250721_120000",
            station_id="TBS", 
            station_name="TBSラジオ",
            title="特殊文字テスト！？＆番組",
            start_time=datetime(2025, 7, 21, 12, 0, 0),
            end_time=datetime(2025, 7, 21, 13, 0, 0)
        )
        
        special_filename = special_program.to_filename()
        # 特殊文字がアンダースコアに変換される
        self.assertIn("特殊文字テスト_番組", special_filename)
        self.assertTrue(special_filename.endswith(".mp3"))


class TestProgramInfoManagerDatabase(unittest.TestCase, RealEnvironmentTestBase):
    """ProgramInfoManager データベース機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_04_SQLiteデータベース初期化(self):
        """
        TDD Test: SQLiteデータベース初期化
        
        データベースとテーブルが正しく初期化されることを確認
        """
        # Given: データベースファイルパス
        db_path = self.temp_env.config_dir / "test_program_info.db"
        
        # When: ProgramInfoManagerを初期化
        manager = ProgramInfoManager(
            db_path=str(db_path),
            area_id="JP13"
        )
        
        # Then: データベースファイルが作成される
        self.assertTrue(db_path.exists())
        
        # And: 正しいテーブルが作成される
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            self.assertIn('stations', tables)
            self.assertIn('programs', tables)
        
        # And: 放送局テーブルの構造が正しい
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(stations)")
            columns = [col[1] for col in cursor.fetchall()]
            
            expected_columns = ['id', 'name', 'ascii_name', 'area_id', 'logo_url', 'banner_url', 'updated_at']
            for col in expected_columns:
                self.assertIn(col, columns)
        
        # And: 番組テーブルの構造が正しい
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(programs)")
            columns = [col[1] for col in cursor.fetchall()]
            
            expected_columns = ['id', 'station_id', 'title', 'start_time', 'end_time', 'duration', 
                              'description', 'performers', 'genre', 'sub_genre', 'updated_at']
            for col in expected_columns:
                self.assertIn(col, columns)
    
    def test_05_放送局情報管理機能(self):
        """
        TDD Test: 放送局情報管理機能
        
        放送局情報の保存・読み込み・キャッシュが正常動作することを確認
        """
        # Given: ProgramInfoManagerとサンプル放送局データ
        db_path = self.temp_env.config_dir / "test_stations.db"
        manager = ProgramInfoManager(db_path=str(db_path), area_id="JP13")
        
        sample_stations = [
            Station(
                id="TBS",
                name="TBSラジオ",
                ascii_name="TBS RADIO",
                area_id="JP13",
                logo_url="https://example.com/tbs_logo.png",
                banner_url="https://example.com/tbs_banner.png"
            ),
            Station(
                id="QRR",
                name="文化放送",
                ascii_name="Joqr",
                area_id="JP13",
                logo_url="https://example.com/qrr_logo.png",
                banner_url="https://example.com/qrr_banner.png"
            )
        ]
        
        # When: 放送局情報を保存
        manager._save_stations(sample_stations)
        
        # Then: データベースに正しく保存される
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM stations")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 2)
        
        # When: 放送局情報をキャッシュから読み込み
        cached_stations = manager._get_cached_stations()
        
        # Then: 正しい放送局情報が取得される
        self.assertEqual(len(cached_stations), 2)
        
        tbs_station = next(s for s in cached_stations if s.id == "TBS")
        self.assertEqual(tbs_station.name, "TBSラジオ")
        self.assertEqual(tbs_station.ascii_name, "TBS RADIO")
        self.assertEqual(tbs_station.area_id, "JP13")
        
        qrr_station = next(s for s in cached_stations if s.id == "QRR")
        self.assertEqual(qrr_station.name, "文化放送")
        self.assertEqual(qrr_station.ascii_name, "Joqr")
        
        # When: 特定の放送局IDで検索
        tbs_by_id = manager.get_station_by_id("TBS")
        
        # Then: 正しい放送局が取得される
        self.assertIsNotNone(tbs_by_id)
        self.assertEqual(tbs_by_id.name, "TBSラジオ")
        
        # When: 存在しない放送局IDで検索
        nonexistent = manager.get_station_by_id("NONEXISTENT")
        
        # Then: Noneが返される
        self.assertIsNone(nonexistent)
    
    def test_06_番組情報管理機能(self):
        """
        TDD Test: 番組情報管理機能
        
        番組情報の保存・読み込み・検索が正常動作することを確認
        """
        # Given: ProgramInfoManagerとサンプル番組データ
        db_path = self.temp_env.config_dir / "test_programs.db"
        manager = ProgramInfoManager(db_path=str(db_path), area_id="JP13")
        
        sample_programs = [
            Program(
                id="TBS_20250721_060000",
                station_id="TBS",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 21, 6, 0, 0),
                end_time=datetime(2025, 7, 21, 8, 30, 0),
                duration=150,
                description="朝の情報番組",
                performers=["森本毅郎", "小島慶子"],
                genre="情報・ワイドショー"
            ),
            Program(
                id="QRR_20250721_070000",
                station_id="QRR",
                title="おはよう寺ちゃん",
                start_time=datetime(2025, 7, 21, 7, 0, 0),
                end_time=datetime(2025, 7, 21, 10, 0, 0),
                duration=180,
                description="朝の番組",
                performers=["寺島尚正"],
                genre="情報"
            )
        ]
        
        # When: 番組情報を保存
        manager._save_programs(sample_programs)
        
        # Then: データベースに正しく保存される
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM programs")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 2)
        
        # When: 特定日の番組をキャッシュから読み込み
        target_date = datetime(2025, 7, 21)
        cached_programs = manager._get_cached_programs(target_date)
        
        # Then: 正しい番組情報が取得される
        self.assertEqual(len(cached_programs), 2)
        
        tbs_program = next(p for p in cached_programs if p.station_id == "TBS")
        self.assertEqual(tbs_program.title, "森本毅郎・スタンバイ!")
        self.assertEqual(len(tbs_program.performers), 2)
        self.assertEqual(tbs_program.duration, 150)
        
        # When: 特定放送局の番組のみ取得
        tbs_only_programs = manager._get_cached_programs(target_date, "TBS")
        
        # Then: TBSの番組のみが取得される
        self.assertEqual(len(tbs_only_programs), 1)
        self.assertEqual(tbs_only_programs[0].station_id, "TBS")


class TestProgramInfoManagerAPI(unittest.TestCase, RealEnvironmentTestBase):
    """ProgramInfoManager API連携機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    @patch('requests.Session.get')
    def test_07_放送局一覧取得機能(self, mock_get):
        """
        TDD Test: 放送局一覧取得機能
        
        Radiko APIからの放送局一覧取得が正常動作することを確認
        """
        # Given: 正常な放送局一覧XMLレスポンス
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <stations>
            <station>
                <id>TBS</id>
                <name>TBSラジオ</name>
                <ascii_name>TBS RADIO</ascii_name>
            </station>
            <station>
                <id>QRR</id>
                <name>文化放送</name>
                <ascii_name>Joqr</ascii_name>
            </station>
        </stations>"""
        
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = sample_xml.encode('utf-8')
        mock_get.return_value = mock_response
        
        # When: 放送局一覧を取得
        db_path = self.temp_env.config_dir / "test_api.db"
        manager = ProgramInfoManager(db_path=str(db_path), area_id="JP13")
        
        stations = manager.get_station_list(force_update=True)
        
        # Then: 正しい放送局リストが取得される
        self.assertEqual(len(stations), 2)
        
        tbs_station = next(s for s in stations if s.id == "TBS")
        self.assertEqual(tbs_station.name, "TBSラジオ")
        self.assertEqual(tbs_station.ascii_name, "TBS RADIO")
        self.assertEqual(tbs_station.area_id, "JP13")
        
        # And: API URLが正しく呼び出される
        expected_url = f"https://radiko.jp/v3/station/list/JP13.xml"
        mock_get.assert_called_with(expected_url)
        
        # And: データベースに保存される
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM stations")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 2)
    
    def test_08_番組検索機能(self):
        """
        TDD Test: 番組検索機能
        
        タイトル・出演者・説明文での検索が正常動作することを確認
        """
        # Given: ProgramInfoManagerと検索対象番組データ
        db_path = self.temp_env.config_dir / "test_search.db"
        manager = ProgramInfoManager(db_path=str(db_path), area_id="JP13")
        
        search_programs = [
            Program(
                id="TBS_20250721_060000",
                station_id="TBS",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 21, 6, 0, 0),
                end_time=datetime(2025, 7, 21, 8, 30, 0),
                duration=150,
                description="朝の情報番組。政治・経済ニュースをお届け",
                performers=["森本毅郎", "小島慶子"],
                genre="情報・ワイドショー"
            ),
            Program(
                id="QRR_20250721_140000",
                station_id="QRR",
                title="アフタヌーンパラダイス",
                start_time=datetime(2025, 7, 21, 14, 0, 0),
                end_time=datetime(2025, 7, 21, 16, 0, 0),
                duration=120,
                description="午後の音楽番組",
                performers=["山田太郎", "森山直太朗"],
                genre="音楽"
            )
        ]
        
        # データベースに保存
        manager._save_programs(search_programs)
        
        # Test Case 1: タイトル検索
        title_results = manager.search_programs("森本", limit=10)
        self.assertEqual(len(title_results), 1)
        self.assertEqual(title_results[0].title, "森本毅郎・スタンバイ!")
        
        # Test Case 2: 出演者検索
        performer_results = manager.search_programs("森山", limit=10)
        self.assertEqual(len(performer_results), 1)
        self.assertEqual(performer_results[0].title, "アフタヌーンパラダイス")
        
        # Test Case 3: 説明文検索
        description_results = manager.search_programs("政治", limit=10)
        self.assertEqual(len(description_results), 1)
        self.assertEqual(description_results[0].title, "森本毅郎・スタンバイ!")
        
        # Test Case 4: 放送局フィルタリング
        station_results = manager.search_programs("", station_id="QRR", limit=10)
        self.assertEqual(len(station_results), 1)
        self.assertEqual(station_results[0].station_id, "QRR")
        
        # Test Case 5: 日付範囲検索
        start_date = datetime(2025, 7, 21, 0, 0, 0)
        end_date = datetime(2025, 7, 21, 23, 59, 59)
        date_results = manager.search_programs("", start_date=start_date, end_date=end_date, limit=10)
        self.assertEqual(len(date_results), 2)


if __name__ == "__main__":
    unittest.main()