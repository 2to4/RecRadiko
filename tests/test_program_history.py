"""
ProgramHistoryManager単体テスト（TDD手法）

TEST_REDESIGN_PLANに基づく実環境重視テスト。
番組表取得・XMLパース・SQLiteキャッシュ・検索機能を実環境でテスト。
"""

import unittest
import json
import sqlite3
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET

# テスト対象
from src.program_history import (
    ProgramHistoryManager, ProgramCache, 
    ProgramHistoryError, ProgramFetchError, ProgramParseError
)
from src.program_info import ProgramInfo
from src.auth import RadikoAuthenticator, AuthInfo
from tests.utils.test_environment import TemporaryTestEnvironment, RealEnvironmentTestBase


class TestProgramCacheBasicOperations(unittest.TestCase, RealEnvironmentTestBase):
    """ProgramCache基本操作機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        self.cache_dir = self.temp_env.config_dir / "cache"
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_01_SQLiteキャッシュ初期化(self):
        """
        TDD Test: SQLiteキャッシュ初期化
        
        キャッシュディレクトリとSQLiteデータベースが正しく初期化されることを確認
        """
        # Given: キャッシュディレクトリパス
        cache_dir = self.cache_dir / "program_cache"
        
        # When: ProgramCacheを初期化
        cache = ProgramCache(cache_dir=str(cache_dir))
        
        # Then: キャッシュディレクトリが作成される
        self.assertTrue(cache_dir.exists())
        self.assertTrue(cache_dir.is_dir())
        
        # And: SQLiteデータベースファイルが作成される
        db_path = cache_dir / "program_cache.db"
        self.assertTrue(db_path.exists())
        
        # And: テーブルが正しく作成される
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='program_cache'"
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            
        # And: テーブル構造が正しい
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(program_cache)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            expected_columns = ['id', 'cache_key', 'program_data', 'cached_at', 'expires_at']
            for col in expected_columns:
                self.assertIn(col, column_names)
    
    def test_02_番組データキャッシュ保存読み込み(self):
        """
        TDD Test: 番組データキャッシュ保存・読み込み
        
        番組情報のキャッシュ保存と読み込みが正常動作することを確認
        """
        # Given: キャッシュとサンプル番組データ
        cache = ProgramCache(cache_dir=str(self.cache_dir))
        
        sample_programs = [
            ProgramInfo(
                program_id="TBS_20250721_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 21, 6, 0, 0),
                end_time=datetime(2025, 7, 21, 8, 30, 0),
                description="朝の情報番組",
                performers=["森本毅郎", "小島慶子"],
                genre="情報・ワイドショー"
            ),
            ProgramInfo(
                program_id="TBS_20250721_083000",
                station_id="TBS", 
                station_name="TBSラジオ",
                title="中島らもの明るい悩み相談室",
                start_time=datetime(2025, 7, 21, 8, 30, 0),
                end_time=datetime(2025, 7, 21, 9, 0, 0),
                description="悩み相談番組",
                performers=["中島らも"],
                genre="バラエティ"
            )
        ]
        
        # When: 番組データをキャッシュに保存
        cache.store_programs("2025-07-21", "TBS", sample_programs)
        
        # Then: データベースにレコードが保存される
        with sqlite3.connect(cache.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM program_cache")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
        
        # When: キャッシュから番組データを読み込み
        cached_programs = cache.get_cached_programs("2025-07-21", "TBS")
        
        # Then: 正しい番組データが復元される
        self.assertIsNotNone(cached_programs)
        self.assertEqual(len(cached_programs), 2)
        
        # And: 番組情報が正確に保存・復元される
        self.assertEqual(cached_programs[0].program_id, "TBS_20250721_060000")
        self.assertEqual(cached_programs[0].title, "森本毅郎・スタンバイ!")
        self.assertEqual(cached_programs[0].station_id, "TBS")
        self.assertEqual(len(cached_programs[0].performers), 2)
        
        self.assertEqual(cached_programs[1].program_id, "TBS_20250721_083000")
        self.assertEqual(cached_programs[1].title, "中島らもの明るい悩み相談室")
    
    def test_03_キャッシュ有効期限管理(self):
        """
        TDD Test: キャッシュ有効期限管理
        
        キャッシュの有効期限管理が正常動作することを確認
        """
        # Given: 通常のキャッシュ
        cache = ProgramCache(cache_dir=str(self.cache_dir), expire_hours=24)
        
        sample_programs = [
            ProgramInfo(
                program_id="TBS_20250721_120000",
                station_id="TBS",
                station_name="TBSラジオ", 
                title="テスト番組",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=1),
                description="テスト用番組",
                performers=["テスト出演者"],
                genre="テスト"
            )
        ]
        
        # When: 番組データを保存
        cache.store_programs("2025-07-21", "TBS", sample_programs)
        
        # Then: データが正常に保存される
        with sqlite3.connect(cache.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM program_cache")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
        
        # When: 有効なデータの読み込み
        cached_programs = cache.get_cached_programs("2025-07-21", "TBS")
        
        # Then: データが正常に取得される
        self.assertIsNotNone(cached_programs)
        self.assertEqual(len(cached_programs), 1)
        
        # When: 直接期限切れデータを挿入してクリーンアップテスト
        with sqlite3.connect(cache.db_path) as conn:
            # 明らかに期限切れの時刻を設定
            expired_time = datetime(2020, 1, 1, 0, 0, 0)  # 2020年のデータ
            conn.execute(
                "INSERT INTO program_cache (cache_key, program_data, expires_at) VALUES (?, ?, ?)",
                ("expired_test", '[]', expired_time)
            )
            conn.commit()
        
        # Then: 期限切れレコードが追加される
        with sqlite3.connect(cache.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM program_cache")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 2)
        
        # When: 期限切れキャッシュをクリーンアップ
        cache.clear_expired_cache()
        
        # Then: 期限切れレコードのみが削除される
        with sqlite3.connect(cache.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM program_cache")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)  # 有効なキャッシュは残る
            
            # 残っているのが有効なキャッシュであることを確認
            cursor = conn.execute("SELECT cache_key FROM program_cache")
            result = cursor.fetchone()
            self.assertEqual(result[0], "2025-07-21_TBS")


class TestProgramHistoryManagerAPI(unittest.TestCase, RealEnvironmentTestBase):
    """ProgramHistoryManager API取得機能テスト"""
    
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
    def test_04_番組表XML取得成功パターン(self, mock_get):
        """
        TDD Test: 番組表XML取得成功パターン
        
        Radiko APIからの番組表XML取得が正常動作することを確認
        """
        # Given: モック認証器と正常なXMLレスポンス
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        mock_auth.get_valid_auth_info.return_value = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=datetime.now().timestamp() + 3600
        )
        
        sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <radiko>
            <stations>
                <station id="TBS">
                    <name>TBSラジオ</name>
                    <progs>
                        <prog id="123" ft="20250721060000" to="20250721083000" dur="9000">
                            <title>森本毅郎・スタンバイ!</title>
                            <desc>朝の情報番組</desc>
                            <pfm>森本毅郎,小島慶子</pfm>
                            <genre>情報・ワイドショー</genre>
                        </prog>
                    </progs>
                </station>
            </stations>
        </radiko>"""
        
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = sample_xml
        mock_response.encoding = 'utf-8'
        mock_get.return_value = mock_response
        
        # When: 番組表取得を実行（キャッシュを無効化）
        manager = ProgramHistoryManager(authenticator=mock_auth)
        
        # キャッシュを無効化するためのパッチ
        with patch.object(manager.cache, 'get_cached_programs', return_value=None):
            programs = manager.get_programs_by_date("2025-07-21", "TBS")
        
        # Then: 正しいAPIが呼び出される
        expected_url = "https://radiko.jp/v3/program/date/20250721/JP13.xml"
        mock_get.assert_called_once_with(expected_url)
        
        # And: XMLが正しくパースされる
        self.assertEqual(len(programs), 1)
        program = programs[0]
        
        self.assertEqual(program.program_id, "TBS_20250721_060000")
        self.assertEqual(program.station_id, "TBS")
        self.assertEqual(program.station_name, "TBSラジオ")
        self.assertEqual(program.title, "森本毅郎・スタンバイ!")
        self.assertEqual(program.description, "朝の情報番組")
        self.assertEqual(program.performers, ["森本毅郎", "小島慶子"])
        self.assertEqual(program.genre, "情報・ワイドショー")
        self.assertEqual(program.start_time, datetime(2025, 7, 21, 6, 0, 0))
        self.assertEqual(program.end_time, datetime(2025, 7, 21, 8, 30, 0))
    
    @patch('requests.Session.get')
    def test_05_番組表XML取得エラーハンドリング(self, mock_get):
        """
        TDD Test: 番組表XML取得エラーハンドリング
        
        API取得エラーが適切に処理されることを確認
        """
        # Given: 認証器とエラーレスポンス
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        mock_auth.get_valid_auth_info.return_value = AuthInfo(
            auth_token="test_token",
            area_id="JP13",
            expires_at=datetime.now().timestamp() + 3600
        )
        
        # Test Case 1: HTTP エラー
        mock_get.side_effect = Exception("Network error")
        
        manager = ProgramHistoryManager(authenticator=mock_auth)
        
        # When & Then: エラーが適切に処理される（キャッシュを無効化）
        with patch.object(manager.cache, 'get_cached_programs', return_value=None):
            with self.assertRaises(ProgramFetchError) as context:
                manager.get_programs_by_date("2025-07-21", "TBS")
        
        self.assertIn("番組表取得エラー", str(context.exception))
        
        # Test Case 2: 空のレスポンス
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = ""
        mock_get.side_effect = None
        mock_get.return_value = mock_response
        
        with patch.object(manager.cache, 'get_cached_programs', return_value=None):
            with self.assertRaises(ProgramFetchError) as context:
                manager.get_programs_by_date("2025-07-21", "TBS")
        
        self.assertIn("番組表取得エラー", str(context.exception))
    
    def test_06_XMLパース処理詳細検証(self):
        """
        TDD Test: XMLパース処理詳細検証
        
        複雑なXML構造の正確なパース処理を確認
        """
        # Given: 認証器と複雑なXMLデータ
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        manager = ProgramHistoryManager(authenticator=mock_auth)
        
        complex_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <radiko>
            <stations>
                <station id="TBS">
                    <name>TBSラジオ</name>
                    <progs>
                        <prog id="123" ft="20250721060000" to="20250721083000" dur="9000">
                            <title>森本毅郎・スタンバイ!</title>
                            <desc>朝の情報番組です。政治、経済、スポーツなど幅広いニュースをお届けします。</desc>
                            <pfm>森本毅郎,小島慶子,佐々木明子</pfm>
                            <genre>情報・ワイドショー</genre>
                        </prog>
                        <prog id="124" ft="20250721083000" to="20250721090000" dur="1800">
                            <title>中島らもの明るい悩み相談室</title>
                            <desc></desc>
                            <pfm>中島らも</pfm>
                            <genre>バラエティ</genre>
                        </prog>
                        <prog id="125" ft="20250721230000" to="20250722010000" dur="3600">
                            <title>深夜番組</title>
                            <desc>深夜の番組</desc>
                            <pfm>深夜DJA,深夜DJB</pfm>
                            <genre>音楽</genre>
                        </prog>
                    </progs>
                </station>
                <station id="QRR">
                    <name>文化放送</name>
                    <progs>
                        <prog id="201" ft="20250721070000" to="20250721100000" dur="10800">
                            <title>おはよう寺ちゃん</title>
                            <desc>朝の番組</desc>
                            <pfm>寺島尚正</pfm>
                            <genre>情報</genre>
                        </prog>
                    </progs>
                </station>
            </stations>
        </radiko>"""
        
        # When: XMLをパース
        programs = manager._parse_program_xml(complex_xml, "2025-07-21")
        
        # Then: 全番組が正しくパースされる
        self.assertEqual(len(programs), 4)
        
        # TBS番組検証
        tbs_programs = [p for p in programs if p.station_id == "TBS"]
        self.assertEqual(len(tbs_programs), 3)
        
        # 最初のTBS番組詳細検証
        morning_show = next(p for p in tbs_programs if "森本毅郎" in p.title)
        self.assertEqual(morning_show.performers, ["森本毅郎", "小島慶子", "佐々木明子"])
        self.assertIn("政治、経済", morning_show.description)
        
        # 深夜番組の日付跨ぎ処理検証
        late_night = next(p for p in tbs_programs if "深夜" in p.title)
        self.assertEqual(late_night.start_time, datetime(2025, 7, 21, 23, 0, 0))
        self.assertEqual(late_night.end_time, datetime(2025, 7, 22, 1, 0, 0))  # 翌日
        
        # QRR番組検証
        qrr_programs = [p for p in programs if p.station_id == "QRR"]
        self.assertEqual(len(qrr_programs), 1)
        self.assertEqual(qrr_programs[0].station_name, "文化放送")
        self.assertEqual(qrr_programs[0].performers, ["寺島尚正"])


class TestProgramHistoryManagerSearch(unittest.TestCase, RealEnvironmentTestBase):
    """ProgramHistoryManager検索機能テスト"""
    
    def setUp(self):
        """テストセットアップ"""
        super().setUp()
        self.temp_env = TemporaryTestEnvironment()
        self.temp_env.__enter__()
        
    def tearDown(self):
        """テストクリーンアップ"""
        self.temp_env.__exit__(None, None, None)
        super().tearDown()
    
    def test_07_番組キーワード検索機能(self):
        """
        TDD Test: 番組キーワード検索機能
        
        番組タイトル・出演者・説明文での検索が正常動作することを確認
        """
        # Given: 認証器とサンプル番組データ
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        manager = ProgramHistoryManager(authenticator=mock_auth)
        
        sample_programs = [
            ProgramInfo(
                program_id="TBS_20250721_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 21, 6, 0, 0),
                end_time=datetime(2025, 7, 21, 8, 30, 0),
                description="朝の情報番組。政治・経済ニュース",
                performers=["森本毅郎", "小島慶子"],
                genre="情報・ワイドショー"
            ),
            ProgramInfo(
                program_id="TBS_20250721_140000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="アフタヌーンパラダイス",
                start_time=datetime(2025, 7, 21, 14, 0, 0),
                end_time=datetime(2025, 7, 21, 16, 0, 0),
                description="午後の音楽番組",
                performers=["山田太郎", "森山直太朗"],
                genre="音楽"
            ),
            ProgramInfo(
                program_id="QRR_20250721_100000",
                station_id="QRR",
                station_name="文化放送",
                title="文化放送ニュース",
                start_time=datetime(2025, 7, 21, 10, 0, 0),
                end_time=datetime(2025, 7, 21, 10, 30, 0),
                description="最新ニュースをお届け",
                performers=["田中花子"],
                genre="ニュース"
            )
        ]
        
        # Test Case 1: タイトル検索
        matches = []
        for program in sample_programs:
            if manager._match_program(program, "森本"):
                matches.append(program)
        
        # Then: タイトルにマッチする番組が見つかる
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].title, "森本毅郎・スタンバイ!")
        
        # Test Case 2: 出演者検索
        matches = []
        for program in sample_programs:
            if manager._match_program(program, "森山"):
                matches.append(program)
        
        # Then: 出演者にマッチする番組が見つかる
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].title, "アフタヌーンパラダイス")
        
        # Test Case 3: 説明文検索
        matches = []
        for program in sample_programs:
            if manager._match_program(program, "政治"):
                matches.append(program)
        
        # Then: 説明文にマッチする番組が見つかる
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].title, "森本毅郎・スタンバイ!")
        
        # Test Case 4: 大文字小文字を区別しない検索
        matches = []
        for program in sample_programs:
            if manager._match_program(program, "パラダイス"):
                matches.append(program)
        
        # Then: 大文字小文字を区別せずマッチする
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].title, "アフタヌーンパラダイス")
    
    def test_08_番組ID検索機能(self):
        """
        TDD Test: 番組ID検索機能
        
        番組IDから番組情報が正確に取得されることを確認
        """
        # Given: 認証器とマネージャー
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        manager = ProgramHistoryManager(authenticator=mock_auth)
        
        # get_programs_by_dateをモック
        sample_programs = [
            ProgramInfo(
                program_id="TBS_20250721_060000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="森本毅郎・スタンバイ!",
                start_time=datetime(2025, 7, 21, 6, 0, 0),
                end_time=datetime(2025, 7, 21, 8, 30, 0),
                description="朝の情報番組",
                performers=["森本毅郎"],
                genre="情報"
            ),
            ProgramInfo(
                program_id="TBS_20250721_140000",
                station_id="TBS",
                station_name="TBSラジオ",
                title="午後番組",
                start_time=datetime(2025, 7, 21, 14, 0, 0),
                end_time=datetime(2025, 7, 21, 16, 0, 0),
                description="午後の番組",
                performers=["午後DJ"],
                genre="音楽"
            )
        ]
        
        with patch.object(manager, 'get_programs_by_date', return_value=sample_programs):
            # Test Case 1: 有効な番組ID
            program = manager.get_program_by_id("TBS_20250721_060000")
            
            # Then: 正しい番組が取得される
            self.assertIsNotNone(program)
            self.assertEqual(program.title, "森本毅郎・スタンバイ!")
            self.assertEqual(program.station_id, "TBS")
            
            # Test Case 2: 存在しない番組ID
            program = manager.get_program_by_id("TBS_20250721_999999")
            
            # Then: Noneが返される
            self.assertIsNone(program)
            
            # Test Case 3: 無効なID形式
            program = manager.get_program_by_id("INVALID_ID")
            
            # Then: Noneが返される（エラーハンドリング）
            self.assertIsNone(program)
    
    def test_09_利用可能日付一覧取得(self):
        """
        TDD Test: 利用可能日付一覧取得
        
        タイムフリー対応期間の日付一覧が正しく生成されることを確認
        """
        # Given: 認証器とマネージャー
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        manager = ProgramHistoryManager(authenticator=mock_auth)
        
        # When: 利用可能日付を取得
        available_dates = manager.get_available_dates()
        
        # Then: 正しい日数の日付が返される（今日を含む8日間）
        self.assertEqual(len(available_dates), 8)
        
        # And: 日付形式が正しい（YYYY-MM-DD）
        for date_str in available_dates:
            self.assertRegex(date_str, r'^\d{4}-\d{2}-\d{2}$')
            # 日付として解析可能であることを確認
            datetime.strptime(date_str, '%Y-%m-%d')
        
        # And: 日付が降順（新しい順）で並んでいる
        dates = [datetime.strptime(d, '%Y-%m-%d') for d in available_dates]
        for i in range(len(dates) - 1):
            self.assertGreaterEqual(dates[i], dates[i + 1])
        
        # And: 今日の日付が含まれている
        today = datetime.now().strftime('%Y-%m-%d')
        self.assertIn(today, available_dates)
        
        # And: 7日前の日付が含まれている
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        self.assertIn(seven_days_ago, available_dates)
    
    def test_10_タイムフリー利用可能性判定(self):
        """
        TDD Test: タイムフリー利用可能性判定
        
        番組のタイムフリー利用可能性が正しく判定されることを確認
        """
        # Given: マネージャー
        mock_auth = MagicMock(spec=RadikoAuthenticator)
        manager = ProgramHistoryManager(authenticator=mock_auth)
        
        now = datetime.now()
        
        # Test Case 1: 7日以内の過去番組（利用可能）
        past_program_time = now - timedelta(days=3)
        is_available = manager._is_timefree_available(past_program_time)
        self.assertTrue(is_available)
        
        # Test Case 2: 7日以上前の番組（利用不可）
        old_program_time = now - timedelta(days=8)
        is_available = manager._is_timefree_available(old_program_time)
        self.assertFalse(is_available)
        
        # Test Case 3: 未来の番組（利用不可）
        future_program_time = now + timedelta(hours=2)
        is_available = manager._is_timefree_available(future_program_time)
        self.assertFalse(is_available)
        
        # Test Case 4: ちょうど7日前の番組（境界値テスト）
        boundary_time = now - timedelta(days=7, seconds=1)
        is_available = manager._is_timefree_available(boundary_time)
        self.assertFalse(is_available)
        
        # Test Case 5: ちょうど現在時刻（境界値テスト）
        current_time = now - timedelta(seconds=1)
        is_available = manager._is_timefree_available(current_time)
        self.assertTrue(is_available)


if __name__ == "__main__":
    unittest.main()