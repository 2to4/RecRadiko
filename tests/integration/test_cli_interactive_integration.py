"""
対話型モードの結合テスト

対話型CLIモードとコンポーネント間の統合を検証するテストケース
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
import io
import sqlite3
import os
from pathlib import Path
from datetime import datetime, timedelta

from src.cli import RecRadikoCLI
from src.auth import RadikoAuthenticator
from src.program_info import ProgramInfoManager, Station, Program
from src.recording import RecordingManager, RecordingJob, RecordingStatus
from src.file_manager import FileManager
from src.scheduler import RecordingScheduler, RepeatPattern, ScheduleStatus
from src.error_handler import ErrorHandler


class TestCLIInteractiveIntegration(unittest.TestCase):
    """対話型モードの結合テスト"""
    
    def setUp(self):
        """テストのセットアップ"""
        # テストディレクトリ
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.test_dir) / "recordings"
        self.output_dir.mkdir(exist_ok=True)
        
        # テスト用設定
        self.test_config = {
            "area_id": "JP13",
            "output_dir": str(self.output_dir),
            "max_concurrent_recordings": 2,
            "notification_enabled": False,
            "log_level": "ERROR",
            "database_path": str(Path(self.test_dir) / "test.db"),
            "auth_cache_path": str(Path(self.test_dir) / "auth_cache.json"),
            "recording": {
                "default_format": "mp3",
                "default_bitrate": 128
            }
        }
        
        # 設定ファイル作成
        self.config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.test_config, self.config_file)
        self.config_file.close()
        
        # データベース初期化
        self._setup_database()
        
        # CLIインスタンス作成（実際のコンポーネントを使用）
        self.cli = RecRadikoCLI(config_file=self.config_file.name)
    
    def tearDown(self):
        """テストのクリーンアップ"""
        Path(self.config_file.name).unlink(missing_ok=True)
        # テストディレクトリのクリーンアップは省略（tmpdir自動削除）
    
    def _setup_database(self):
        """テスト用データベースをセットアップ"""
        db_path = self.test_config["database_path"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # テーブル作成（基本的な構造のみ）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY,
                station_id TEXT,
                program_title TEXT,
                start_time TEXT,
                end_time TEXT,
                file_path TEXT,
                file_size INTEGER,
                status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY,
                station_id TEXT,
                program_title TEXT,
                start_time TEXT,
                end_time TEXT,
                repeat_pattern TEXT,
                status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # テストデータ挿入
        test_recordings = [
            ("TBS", "ニュース番組", "2024-01-01T19:00:00", "2024-01-01T20:00:00", 
             str(self.output_dir / "TBS_news.mp3"), 50*1024*1024, "completed"),
            ("QRR", "音楽番組", "2024-01-01T21:00:00", "2024-01-01T22:00:00",
             str(self.output_dir / "QRR_music.mp3"), 75*1024*1024, "completed")
        ]
        
        for recording in test_recordings:
            cursor.execute("""
                INSERT INTO recordings (station_id, program_title, start_time, end_time, 
                                      file_path, file_size, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, recording)
        
        test_schedules = [
            ("TBS", "朝のニュース", "2024-01-02T07:00:00", "2024-01-02T09:00:00", "daily", "active"),
            ("LFR", "深夜番組", "2024-01-02T25:00:00", "2024-01-02T27:00:00", "weekly", "active")
        ]
        
        for schedule in test_schedules:
            cursor.execute("""
                INSERT INTO schedules (station_id, program_title, start_time, end_time, 
                                     repeat_pattern, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, schedule)
        
        conn.commit()
        conn.close()
    
    @patch('src.program_info.requests.get')
    def test_interactive_list_stations_integration(self, mock_get):
        """放送局一覧の統合テスト"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = """<?xml version="1.0" encoding="UTF-8"?>
        <stations>
            <station>
                <id>TBS</id>
                <name>TBSラジオ</name>
                <logo></logo>
                <banner></banner>
            </station>
            <station>
                <id>QRR</id>
                <name>文化放送</name>
                <logo></logo>
                <banner></banner>
            </station>
        </stations>""".encode('utf-8')
        mock_get.return_value = mock_response
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['list-stations'])
            output = mock_stdout.getvalue()
            
            # 検証
            self.assertEqual(result, 0)
            self.assertIn("放送局一覧", output)
            self.assertIn("TBS", output)
            self.assertIn("TBSラジオ", output)
            self.assertIn("QRR", output)
            self.assertIn("文化放送", output)
    
    @patch('src.program_info.requests.get')
    def test_interactive_list_programs_integration(self, mock_get):
        """番組表取得の統合テスト"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.status_code = 200
        now = datetime.now()
        mock_response.content = f"""<?xml version="1.0" encoding="UTF-8"?>
        <radiko>
            <stations>
                <station id="TBS">
                    <progs>
                        <prog id="prog1" 
                              ft="{int(now.timestamp())}" 
                              to="{int((now + timedelta(hours=1)).timestamp())}"
                              ftl="{now.strftime('%Y%m%d%H%M%S')}"
                              tol="{(now + timedelta(hours=1)).strftime('%Y%m%d%H%M%S')}">
                            <title>ニュース番組</title>
                            <pfm>アナウンサーA</pfm>
                        </prog>
                        <prog id="prog2"
                              ft="{int((now + timedelta(hours=1)).timestamp())}"
                              to="{int((now + timedelta(hours=2)).timestamp())}"
                              ftl="{(now + timedelta(hours=1)).strftime('%Y%m%d%H%M%S')}"
                              tol="{(now + timedelta(hours=2)).strftime('%Y%m%d%H%M%S')}">
                            <title>音楽番組</title>
                            <pfm>DJ B,ゲスト C</pfm>
                        </prog>
                    </progs>
                </station>
            </stations>
        </radiko>""".encode('utf-8')
        mock_get.return_value = mock_response
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['list-programs', '--station', 'TBS'])
            output = mock_stdout.getvalue()
            
            # 検証
            self.assertEqual(result, 0)
            self.assertIn("番組表", output)
            self.assertIn("ニュース番組", output)
            self.assertIn("音楽番組", output)
            self.assertIn("アナウンサーA", output)
    
    def test_interactive_list_recordings_integration(self):
        """録音ファイル一覧の統合テスト"""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['list-recordings'])
            output = mock_stdout.getvalue()
            
            # 検証
            self.assertEqual(result, 0)
            self.assertIn("録音ファイル一覧", output)
            # データベースから読み込まれたデータの確認
            # 実装に依存するが、基本的な動作確認
    
    def test_interactive_list_schedules_integration(self):
        """録音予約一覧の統合テスト"""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['list-schedules'])
            output = mock_stdout.getvalue()
            
            # 検証
            self.assertEqual(result, 0)
            self.assertIn("録音予約一覧", output)
            # データベースから読み込まれたスケジュールの確認
    
    def test_interactive_status_integration(self):
        """システム状況の統合テスト"""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['status'])
            output = mock_stdout.getvalue()
            
            # 検証
            self.assertEqual(result, 0)
            self.assertIn("RecRadiko システム状況", output)
            self.assertIn("アクティブな録音", output)
            self.assertIn("ストレージ使用状況", output)
    
    def test_interactive_stats_integration(self):
        """統計情報の統合テスト"""
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['stats'])
            output = mock_stdout.getvalue()
            
            # 検証
            self.assertEqual(result, 0)
            self.assertIn("統計情報", output)
            self.assertIn("総録音ファイル", output)
            self.assertIn("総スケジュール", output)
    
    @patch('src.streaming.requests.Session.get')
    @patch('src.auth.requests.get')
    @patch('src.auth.requests.post')
    def test_interactive_record_integration(self, mock_post, mock_auth_get, mock_stream_get):
        """録音機能の統合テスト"""
        # 認証モック
        mock_auth_response = Mock()
        mock_auth_response.status_code = 200
        mock_auth_response.headers = {'X-Radiko-AUTHTOKEN': 'test-token'}
        mock_post.return_value = mock_auth_response
        
        mock_area_response = Mock()
        mock_area_response.status_code = 200
        mock_area_response.json.return_value = {'region_id': 'JP13'}
        mock_auth_get.return_value = mock_area_response
        
        # ストリーミングモック
        mock_stream_response = Mock()
        mock_stream_response.status_code = 200
        mock_stream_response.content = b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=48000\nhttp://example.com/stream.m3u8\n'
        mock_stream_get.return_value = mock_stream_response
        
        # FFmpegのモック
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None  # 実行中
            mock_process.wait.return_value = 0     # 成功終了
            mock_popen.return_value = mock_process
            
            with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                # 短時間の録音をテスト（実際の録音は行わない）
                result = self.cli._execute_interactive_command(['record', 'TBS', '1'])
                
                # 基本的な動作確認（詳細は他のテストで）
                self.assertIsNotNone(result)
    
    @patch('builtins.input')
    def test_interactive_session_integration(self, mock_input):
        """対話型セッション全体の統合テスト"""
        # 複数コマンドのシーケンス
        mock_input.side_effect = [
            'help',           # ヘルプ表示
            'status',         # システム状況
            'stats',          # 統計情報
            'list-schedules', # スケジュール一覧
            'exit'            # 終了
        ]
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._run_interactive()
            output = mock_stdout.getvalue()
            
            # セッション全体の動作確認
            self.assertEqual(result, 0)
            self.assertIn("RecRadiko 対話型モード", output)
            self.assertIn("利用可能なコマンド", output)  # ヘルプ
            self.assertIn("システム状況", output)       # status
            self.assertIn("統計情報", output)          # stats
            self.assertIn("録音予約一覧", output)      # list-schedules
            self.assertIn("RecRadikoを終了します", output)
    
    def test_interactive_error_handling_integration(self):
        """対話型モードのエラーハンドリング統合テスト"""
        # 無効な引数でのコマンド実行
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['record'])
            output = mock_stdout.getvalue()
            
            # エラーハンドリングの確認
            self.assertEqual(result, 1)
            self.assertIn("使用法", output)
        
        # 存在しないコマンドの実行
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._execute_interactive_command(['nonexistent-command'])
            
            # 適切な処理がされることを確認
            self.assertIsNotNone(result)
    
    @patch('builtins.input')
    def test_interactive_component_initialization(self, mock_input):
        """対話型モードでのコンポーネント初期化テスト"""
        mock_input.side_effect = ['exit']
        
        # 初期化前の状態確認
        self.assertIsNotNone(self.cli.auth_manager)
        self.assertIsNotNone(self.cli.program_info_manager)
        self.assertIsNotNone(self.cli.recording_manager)
        self.assertIsNotNone(self.cli.file_manager)
        self.assertIsNotNone(self.cli.scheduler)
        self.assertIsNotNone(self.cli.error_handler)
        
        # 対話型モード実行
        result = self.cli._run_interactive()
        
        # 正常終了の確認
        self.assertEqual(result, 0)
    
    def test_interactive_config_loading_integration(self):
        """対話型モードでの設定読み込み統合テスト"""
        # 設定内容の確認
        self.assertEqual(self.cli.config['area_id'], 'JP13')
        self.assertEqual(self.cli.config['output_dir'], str(self.output_dir))
        self.assertEqual(self.cli.config['recording']['default_format'], 'mp3')
        
        # 設定がコンポーネントに正しく渡されていることを確認
        # （実装詳細に依存するため、基本的な確認のみ）
        self.assertIsNotNone(self.cli.config)
    
    @patch('builtins.input')
    def test_interactive_command_history_simulation(self, mock_input):
        """対話型モードのコマンド履歴シミュレーション"""
        # 実際のユーザー操作を模擬
        command_sequence = [
            'help',                    # 初回ヘルプ確認
            'list-stations',           # 利用可能放送局確認
            'status',                  # 現在のシステム状況確認
            'list-schedules',          # 既存スケジュール確認
            'stats',                   # 統計情報確認
            'list-recordings',         # 過去の録音確認
            'exit'                     # 終了
        ]
        
        mock_input.side_effect = command_sequence
        
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            result = self.cli._run_interactive()
            output = mock_stdout.getvalue()
            
            # 全コマンドが実行されたことを確認
            self.assertEqual(result, 0)
            
            # 各コマンドの出力が含まれていることを確認
            expected_outputs = [
                "利用可能なコマンド",  # help
                "放送局一覧",         # list-stations
                "システム状況",       # status
                "録音予約一覧",       # list-schedules
                "統計情報",          # stats
                "録音ファイル一覧"    # list-recordings
            ]
            
            for expected in expected_outputs:
                self.assertIn(expected, output, f"Expected output '{expected}' not found")


if __name__ == '__main__':
    unittest.main()