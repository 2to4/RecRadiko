"""
番組情報モジュールの単体テスト
"""

import unittest
import tempfile
import sqlite3
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pytz

from src.program_info import ProgramInfoManager, Station, Program, ProgramInfoError
from src.auth import RadikoAuthenticator


class TestStation(unittest.TestCase):
    """Station クラスのテスト"""
    
    def test_station_creation(self):
        """Station の作成テスト"""
        station = Station(
            id="TBS",
            name="TBSラジオ",
            ascii_name="TBS RADIO",
            area_id="JP13",
            logo_url="http://example.com/logo.png",
            banner_url="http://example.com/banner.png"
        )
        
        self.assertEqual(station.id, "TBS")
        self.assertEqual(station.name, "TBSラジオ")
        self.assertEqual(station.ascii_name, "TBS RADIO")
        self.assertEqual(station.area_id, "JP13")
    
    def test_station_to_dict(self):
        """Station の辞書変換テスト"""
        station = Station(
            id="TBS",
            name="TBSラジオ",
            ascii_name="TBS RADIO",
            area_id="JP13"
        )
        
        station_dict = station.to_dict()
        
        self.assertEqual(station_dict['id'], "TBS")
        self.assertEqual(station_dict['name'], "TBSラジオ")
        self.assertEqual(station_dict['area_id'], "JP13")
    
    def test_station_from_dict(self):
        """Station の辞書からの復元テスト"""
        station_dict = {
            'id': "TBS",
            'name': "TBSラジオ",
            'ascii_name': "TBS RADIO",
            'area_id': "JP13",
            'logo_url': "",
            'banner_url': ""
        }
        
        station = Station.from_dict(station_dict)
        
        self.assertEqual(station.id, "TBS")
        self.assertEqual(station.name, "TBSラジオ")


class TestProgram(unittest.TestCase):
    """Program クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.jst = pytz.timezone('Asia/Tokyo')
        self.start_time = self.jst.localize(datetime(2024, 1, 1, 20, 0, 0))
        self.end_time = self.jst.localize(datetime(2024, 1, 1, 21, 0, 0))
    
    def test_program_creation(self):
        """Program の作成テスト"""
        program = Program(
            id="TBS_20240101200000",
            station_id="TBS",
            title="テスト番組",
            start_time=self.start_time,
            end_time=self.end_time,
            duration=60,
            description="テスト番組の説明",
            performers=["出演者1", "出演者2"],
            genre="音楽",
            sub_genre="ポップス"
        )
        
        self.assertEqual(program.id, "TBS_20240101200000")
        self.assertEqual(program.station_id, "TBS")
        self.assertEqual(program.title, "テスト番組")
        self.assertEqual(program.duration, 60)
        self.assertEqual(len(program.performers), 2)
    
    def test_program_duration_calculation(self):
        """Program の継続時間自動計算テスト"""
        program = Program(
            id="TBS_20240101200000",
            station_id="TBS",
            title="テスト番組",
            start_time=self.start_time,
            end_time=self.end_time,
            duration=0  # 自動計算されるべき
        )
        
        self.assertEqual(program.duration, 60)  # 1時間 = 60分
    
    def test_program_duration_minutes_property(self):
        """Program の duration_minutes プロパティテスト"""
        program = Program(
            id="TBS_20240101200000",
            station_id="TBS",
            title="テスト番組",
            start_time=self.start_time,
            end_time=self.end_time,
            duration=90
        )
        
        self.assertEqual(program.duration_minutes, 90)
    
    def test_program_to_dict(self):
        """Program の辞書変換テスト"""
        program = Program(
            id="TBS_20240101200000",
            station_id="TBS",
            title="テスト番組",
            start_time=self.start_time,
            end_time=self.end_time,
            duration=60
        )
        
        program_dict = program.to_dict()
        
        self.assertEqual(program_dict['id'], "TBS_20240101200000")
        self.assertEqual(program_dict['title'], "テスト番組")
        self.assertIn('start_time', program_dict)
        self.assertIn('end_time', program_dict)
    
    def test_program_from_dict(self):
        """Program の辞書からの復元テスト"""
        program_dict = {
            'id': "TBS_20240101200000",
            'station_id': "TBS",
            'title': "テスト番組",
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration': 60,
            'description': "",
            'performers': [],
            'genre': "",
            'sub_genre': ""
        }
        
        program = Program.from_dict(program_dict)
        
        self.assertEqual(program.id, "TBS_20240101200000")
        self.assertEqual(program.title, "テスト番組")
        self.assertEqual(program.duration, 60)


class TestProgramInfoManager(unittest.TestCase):
    """ProgramInfoManager クラスのテスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = f"{self.temp_dir}/test_radiko.db"
        self.authenticator = Mock(spec=RadikoAuthenticator)
        self.manager = ProgramInfoManager(
            db_path=self.db_path,
            area_id="JP13",
            authenticator=self.authenticator
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_manager_creation(self):
        """マネージャーの作成テスト"""
        self.assertIsInstance(self.manager, ProgramInfoManager)
        self.assertEqual(self.manager.area_id, "JP13")
        
        # データベースファイルが作成されることを確認
        import os
        self.assertTrue(os.path.exists(self.db_path))
    
    def test_database_initialization(self):
        """データベース初期化のテスト"""
        # データベースに期待するテーブルが作成されることを確認
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
        
        self.assertIn('stations', tables)
        self.assertIn('programs', tables)
    
    @patch('requests.Session.get')
    def test_fetch_station_list_success(self, mock_get):
        """放送局リスト取得成功のテスト"""
        # モックXMLレスポンス（実際のRadiko API構造に合わせて修正）
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <stations>
            <station>
                <id>TBS</id>
                <name>TBSラジオ</name>
                <ascii_name>TBS RADIO</ascii_name>
                <logo>http://example.com/tbs_logo.png</logo>
                <banner>http://example.com/tbs_banner.png</banner>
            </station>
            <station>
                <id>QRR</id>
                <name>文化放送</name>
                <ascii_name>BUNKA HOSO</ascii_name>
                <logo>http://example.com/qrr_logo.png</logo>
                <banner>http://example.com/qrr_banner.png</banner>
            </station>
        </stations>'''
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = xml_content.encode('utf-8')
        mock_get.return_value = mock_response
        
        stations = self.manager.fetch_station_list()
        
        self.assertEqual(len(stations), 2)
        self.assertEqual(stations[0].id, "TBS")
        self.assertEqual(stations[0].name, "TBSラジオ")
        self.assertEqual(stations[1].id, "QRR")
        self.assertEqual(stations[1].name, "文化放送")
    
    @patch('requests.Session.get')
    def test_fetch_station_list_network_error(self, mock_get):
        """放送局リスト取得ネットワークエラーのテスト"""
        mock_get.side_effect = Exception("Network error")
        
        with self.assertRaises(ProgramInfoError):
            self.manager.fetch_station_list()
    
    @patch('requests.Session.get')
    def test_fetch_program_guide_success(self, mock_get):
        """番組表取得成功のテスト"""
        # モックXMLレスポンス
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <programs>
            <station id="TBS">
                <prog ft="20240101200000" to="20240101210000">
                    <title>テスト番組1</title>
                    <desc>番組の説明</desc>
                    <pfm>出演者1,出演者2</pfm>
                    <genre>音楽</genre>
                    <sub_genre>ポップス</sub_genre>
                </prog>
                <prog ft="20240101210000" to="20240101220000">
                    <title>テスト番組2</title>
                    <desc>番組の説明2</desc>
                    <genre>トーク</genre>
                </prog>
            </station>
        </programs>'''
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = xml_content.encode('utf-8')
        mock_get.return_value = mock_response
        
        date = datetime(2024, 1, 1)
        programs = self.manager.fetch_program_guide(date)
        
        self.assertEqual(len(programs), 2)
        self.assertEqual(programs[0].title, "テスト番組1")
        self.assertEqual(programs[0].station_id, "TBS")
        self.assertEqual(len(programs[0].performers), 2)
        self.assertEqual(programs[1].title, "テスト番組2")
    
    def test_parse_radiko_time(self):
        """Radiko時刻解析のテスト"""
        time_str = "20240101200000"
        parsed_time = self.manager._parse_radiko_time(time_str)
        
        self.assertEqual(parsed_time.year, 2024)
        self.assertEqual(parsed_time.month, 1)
        self.assertEqual(parsed_time.day, 1)
        self.assertEqual(parsed_time.hour, 20)
        self.assertEqual(parsed_time.minute, 0)
        self.assertEqual(parsed_time.second, 0)
    
    def test_get_element_text(self):
        """XML要素テキスト取得のテスト"""
        xml_str = '<root><title>テスト番組</title><empty></empty></root>'
        root = ET.fromstring(xml_str)
        
        # 存在する要素
        title = self.manager._get_element_text(root, 'title')
        self.assertEqual(title, "テスト番組")
        
        # 空の要素
        empty = self.manager._get_element_text(root, 'empty')
        self.assertEqual(empty, "")
        
        # 存在しない要素
        nonexistent = self.manager._get_element_text(root, 'nonexistent')
        self.assertEqual(nonexistent, "")
    
    def test_save_and_get_stations(self):
        """放送局保存・取得のテスト"""
        stations = [
            Station(
                id="TBS",
                name="TBSラジオ",
                ascii_name="TBS RADIO",
                area_id="JP13"
            ),
            Station(
                id="QRR",
                name="文化放送",
                ascii_name="BUNKA HOSO",
                area_id="JP13"
            )
        ]
        
        # 保存
        self.manager._save_stations(stations)
        
        # 取得
        cached_stations = self.manager._get_cached_stations()
        
        self.assertEqual(len(cached_stations), 2)
        self.assertEqual(cached_stations[0].id, "TBS")  # 名前順でソート (TBSラジオ)
        self.assertEqual(cached_stations[1].id, "QRR")  # 文化放送
    
    def test_save_and_get_programs(self):
        """番組保存・取得のテスト"""
        jst = pytz.timezone('Asia/Tokyo')
        programs = [
            Program(
                id="TBS_20240101200000",
                station_id="TBS",
                title="テスト番組1",
                start_time=jst.localize(datetime(2024, 1, 1, 20, 0, 0)),
                end_time=jst.localize(datetime(2024, 1, 1, 21, 0, 0)),
                duration=60
            ),
            Program(
                id="TBS_20240101210000",
                station_id="TBS",
                title="テスト番組2",
                start_time=jst.localize(datetime(2024, 1, 1, 21, 0, 0)),
                end_time=jst.localize(datetime(2024, 1, 1, 22, 0, 0)),
                duration=60
            )
        ]
        
        # 保存
        self.manager._save_programs(programs)
        
        # 取得
        date = datetime(2024, 1, 1)
        cached_programs = self.manager._get_cached_programs(date)
        
        self.assertEqual(len(cached_programs), 2)
        self.assertEqual(cached_programs[0].title, "テスト番組1")
        self.assertEqual(cached_programs[1].title, "テスト番組2")
    
    def test_get_current_program(self):
        """現在放送中番組取得のテスト"""
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        
        # 現在時刻を含む番組を作成
        program = Program(
            id="TBS_test",
            station_id="TBS",
            title="現在の番組",
            start_time=now - timedelta(minutes=30),
            end_time=now + timedelta(minutes=30),
            duration=60
        )
        
        # データベースに保存
        self.manager._save_programs([program])
        
        # 現在の番組を取得
        current = self.manager.get_current_program("TBS")
        
        self.assertIsNotNone(current)
        self.assertEqual(current.title, "現在の番組")
    
    def test_search_programs(self):
        """番組検索のテスト"""
        jst = pytz.timezone('Asia/Tokyo')
        programs = [
            Program(
                id="TBS_1",
                station_id="TBS",
                title="音楽番組",
                start_time=jst.localize(datetime(2024, 1, 1, 20, 0, 0)),
                end_time=jst.localize(datetime(2024, 1, 1, 21, 0, 0)),
                duration=60,
                description="クラシック音楽の番組"
            ),
            Program(
                id="TBS_2",
                station_id="TBS",
                title="ニュース番組",
                start_time=jst.localize(datetime(2024, 1, 1, 21, 0, 0)),
                end_time=jst.localize(datetime(2024, 1, 1, 22, 0, 0)),
                duration=60,
                description="今日のニュース"
            )
        ]
        
        # データベースに保存
        self.manager._save_programs(programs)
        
        # タイトルで検索
        results = self.manager.search_programs("音楽")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "音楽番組")
        
        # 説明で検索
        results = self.manager.search_programs("ニュース")
        self.assertEqual(len(results), 1)  # ニュース番組が1件ヒット
    
    def test_cleanup_old_programs(self):
        """古い番組削除のテスト"""
        jst = pytz.timezone('Asia/Tokyo')
        old_time = datetime.now(jst) - timedelta(days=60)
        
        old_program = Program(
            id="TBS_old",
            station_id="TBS",
            title="古い番組",
            start_time=old_time,
            end_time=old_time + timedelta(hours=1),
            duration=60
        )
        
        # データベースに保存
        self.manager._save_programs([old_program])
        
        # クリーンアップ実行（30日より古いものを削除）
        self.manager.cleanup_old_programs(30)
        
        # 古い番組が削除されていることを確認
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM programs')
            count = cursor.fetchone()[0]
            self.assertEqual(count, 0)
    
    def test_get_station_by_id(self):
        """ID による放送局取得のテスト"""
        station = Station(
            id="TBS",
            name="TBSラジオ",
            ascii_name="TBS RADIO",
            area_id="JP13"
        )
        
        # 保存
        self.manager._save_stations([station])
        
        # ID で取得
        retrieved = self.manager.get_station_by_id("TBS")
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, "TBS")
        self.assertEqual(retrieved.name, "TBSラジオ")
        
        # 存在しない ID
        nonexistent = self.manager.get_station_by_id("NONEXISTENT")
        self.assertIsNone(nonexistent)


if __name__ == '__main__':
    unittest.main()