"""
対話型モードのエンドツーエンドテスト

実際のユーザーシナリオに基づく対話型CLIモードの包括的テスト
"""
import unittest
import tempfile
import json
import subprocess
import os
import time
import signal
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import threading
import queue


class TestInteractiveE2E(unittest.TestCase):
    """対話型モードのE2Eテスト"""
    
    def setUp(self):
        """テストのセットアップ"""
        # テスト環境構築
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.test_dir) / "recordings"
        self.output_dir.mkdir(exist_ok=True)
        
        # テスト設定
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
                "default_bitrate": 128,
                "max_concurrent_jobs": 2
            },
            "daemon": {
                "health_check_interval": 10,
                "monitoring_enabled": False
            }
        }
        
        # 設定ファイル作成
        self.config_file = Path(self.test_dir) / "config.json"
        with open(self.config_file, 'w') as f:
            json.dump(self.test_config, f)
        
        # プロジェクトルート
        self.project_root = Path(__file__).parent.parent.parent
        self.recradiko_script = self.project_root / "RecRadiko.py"
        
        # テスト用データベース初期化
        self._setup_test_database()
        
        # 実行中プロセス追跡
        self.processes = []
    
    def tearDown(self):
        """テストのクリーンアップ"""
        # プロセス終了
        for process in self.processes:
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        # テストディレクトリクリーンアップ
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _setup_test_database(self):
        """テスト用データベースセットアップ"""
        db_path = self.test_config["database_path"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # テーブル作成
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
        
        # サンプルデータ挿入
        sample_recordings = [
            ("TBS", "朝のニュース", "2024-01-01T07:00:00", "2024-01-01T09:00:00",
             str(self.output_dir / "TBS_morning_news.mp3"), 120*1024*1024, "completed"),
            ("QRR", "音楽番組", "2024-01-01T20:00:00", "2024-01-01T22:00:00",
             str(self.output_dir / "QRR_music_show.mp3"), 200*1024*1024, "completed"),
            ("LFR", "深夜ラジオ", "2024-01-01T25:00:00", "2024-01-01T27:00:00",
             str(self.output_dir / "LFR_late_night.mp3"), 180*1024*1024, "completed")
        ]
        
        for recording in sample_recordings:
            cursor.execute("""
                INSERT INTO recordings (station_id, program_title, start_time, end_time,
                                      file_path, file_size, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, recording)
        
        sample_schedules = [
            ("TBS", "毎日ニュース", "2024-01-02T07:00:00", "2024-01-02T09:00:00", "daily", "active"),
            ("QRR", "週間音楽", "2024-01-06T20:00:00", "2024-01-06T22:00:00", "weekly", "active"),
            ("LFR", "月例特番", "2024-01-15T19:00:00", "2024-01-15T21:00:00", "monthly", "paused")
        ]
        
        for schedule in sample_schedules:
            cursor.execute("""
                INSERT INTO schedules (station_id, program_title, start_time, end_time,
                                     repeat_pattern, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, schedule)
        
        conn.commit()
        conn.close()
        
        # サンプル録音ファイル作成
        for recording in sample_recordings:
            file_path = Path(recording[4])
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(b"dummy audio data" * 1000)
    
    def _run_interactive_process(self, commands, timeout=30):
        """対話型プロセスを実行し、コマンドを送信"""
        # 環境変数設定（テスト時のログ出力制御）
        env = os.environ.copy()
        env['PYTEST_CURRENT_TEST'] = 'test'
        env['RECRADIKO_LOG_LEVEL'] = 'ERROR'
        
        # 対話型モードでプロセス開始
        process = subprocess.Popen(
            ['python', str(self.recradiko_script), '--config', str(self.config_file), '--interactive'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(self.project_root),
            env=env,
            bufsize=0  # バッファリング無効
        )
        
        self.processes.append(process)
        
        try:
            # コマンド送信とレスポンス収集
            input_text = "\\n".join(commands) + "\\nexit\\n"
            
            # タイムアウト付きで実行
            stdout, stderr = process.communicate(input=input_text, timeout=timeout)
            
            return process.returncode, stdout, stderr
        
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return -1, stdout, stderr
    
    def test_interactive_basic_workflow(self):
        """基本的な対話型ワークフローテスト"""
        commands = [
            "help",                    # ヘルプ表示
            "status",                  # システム状況確認
            "list-stations",           # 放送局一覧
            "list-schedules",          # スケジュール一覧
            "list-recordings",         # 録音ファイル一覧
            "stats"                    # 統計情報
        ]
        
        returncode, stdout, stderr = self._run_interactive_process(commands)
        
        # 基本検証
        self.assertEqual(returncode, 0, f"Process failed: {stderr}")
        
        # 出力内容確認
        self.assertIn("RecRadiko 対話型モード", stdout)
        self.assertIn("利用可能なコマンド", stdout)  # help
        self.assertIn("システム状況", stdout)       # status  
        self.assertIn("放送局一覧", stdout)         # list-stations
        self.assertIn("録音予約一覧", stdout)       # list-schedules
        self.assertIn("録音ファイル一覧", stdout)   # list-recordings
        self.assertIn("統計情報", stdout)          # stats
        self.assertIn("RecRadikoを終了します", stdout)
    
    def test_interactive_help_and_exit(self):
        """ヘルプ表示と終了のテスト"""
        commands = ["help"]
        
        returncode, stdout, stderr = self._run_interactive_process(commands)
        
        # 検証
        self.assertEqual(returncode, 0)
        self.assertIn("利用可能なコマンド", stdout)
        self.assertIn("record <放送局ID> <時間(分)>", stdout)
        self.assertIn("schedule", stdout)
        self.assertIn("list-stations", stdout)
        self.assertIn("exit", stdout)
    
    def test_interactive_status_and_stats(self):
        """ステータスと統計情報表示テスト"""
        commands = [
            "status",
            "stats"
        ]
        
        returncode, stdout, stderr = self._run_interactive_process(commands)
        
        # 検証
        self.assertEqual(returncode, 0)
        self.assertIn("RecRadiko システム状況", stdout)
        self.assertIn("アクティブな録音", stdout)
        self.assertIn("ストレージ使用状況", stdout)
        self.assertIn("統計情報", stdout)
        self.assertIn("総録音ファイル", stdout)
        self.assertIn("総スケジュール", stdout)
    
    def test_interactive_list_commands(self):
        """一覧表示コマンドのテスト"""
        commands = [
            "list-stations",
            "list-schedules", 
            "list-recordings"
        ]
        
        returncode, stdout, stderr = self._run_interactive_process(commands)
        
        # 検証
        self.assertEqual(returncode, 0)
        self.assertIn("放送局一覧", stdout)
        self.assertIn("録音予約一覧", stdout)
        self.assertIn("録音ファイル一覧", stdout)
        
        # データベースのサンプルデータが表示されることを確認
        self.assertIn("毎日ニュース", stdout)      # スケジュール
        self.assertIn("朝のニュース", stdout)      # 録音履歴
    
    def test_interactive_invalid_command_handling(self):
        """無効なコマンドの処理テスト"""
        commands = [
            "invalid-command",
            "record",  # 引数不足
            "help"     # 正常なコマンド
        ]
        
        returncode, stdout, stderr = self._run_interactive_process(commands)
        
        # 無効なコマンドでもプロセスは継続する
        self.assertEqual(returncode, 0)
        self.assertIn("利用可能なコマンド", stdout)  # help出力
    
    def test_interactive_empty_input_handling(self):
        """空入力の処理テスト"""
        commands = [
            "",        # 空文字列
            "   ",     # 空白のみ
            "status"   # 正常なコマンド
        ]
        
        returncode, stdout, stderr = self._run_interactive_process(commands)
        
        # 空入力は無視され、正常なコマンドが実行される
        self.assertEqual(returncode, 0)
        self.assertIn("システム状況", stdout)
    
    def test_interactive_session_persistence(self):
        """セッション状態の持続テスト"""
        commands = [
            "status",           # 初期状態確認
            "list-schedules",   # データ確認
            "stats",            # 統計確認
            "status"            # 再度状態確認
        ]
        
        returncode, stdout, stderr = self._run_interactive_process(commands)
        
        # セッション全体が正常に動作する
        self.assertEqual(returncode, 0)
        
        # 複数のstatusコマンド実行により状態が保持されていることを確認
        status_count = stdout.count("RecRadiko システム状況")
        self.assertEqual(status_count, 2)
    
    def test_interactive_command_sequence_performance(self):
        """コマンドシーケンスのパフォーマンステスト"""
        # 多数のコマンドを連続実行
        commands = []
        for i in range(10):
            commands.extend(["status", "stats", "list-schedules"])
        
        start_time = time.time()
        returncode, stdout, stderr = self._run_interactive_process(commands, timeout=60)
        end_time = time.time()
        
        # パフォーマンス検証
        self.assertEqual(returncode, 0)
        execution_time = end_time - start_time
        self.assertLess(execution_time, 45, "コマンド実行が遅すぎます")
        
        # 全コマンドが実行されたことを確認
        self.assertEqual(stdout.count("システム状況"), 10)
        self.assertEqual(stdout.count("統計情報"), 10)
        self.assertEqual(stdout.count("録音予約一覧"), 10)
    
    def test_interactive_error_recovery(self):
        """エラー復旧テスト"""
        commands = [
            "status",              # 正常コマンド
            "invalid-command",     # エラーコマンド
            "record",              # 引数不足エラー
            "status",              # 正常コマンド（復旧確認）
            "stats"                # 正常コマンド（継続確認）
        ]
        
        returncode, stdout, stderr = self._run_interactive_process(commands)
        
        # エラー後も正常動作継続
        self.assertEqual(returncode, 0)
        self.assertIn("システム状況", stdout)
        self.assertIn("統計情報", stdout)
        
        # エラーコマンドのハンドリング確認
        status_count = stdout.count("RecRadiko システム状況")
        self.assertEqual(status_count, 2)
    
    def test_interactive_user_experience_flow(self):
        """ユーザー体験フローテスト"""
        # 実際のユーザーが行うであろう操作シーケンス
        commands = [
            "help",                    # 初回利用時のヘルプ確認
            "list-stations",           # 利用可能な放送局確認
            "list-schedules",          # 既存のスケジュール確認
            "status",                  # 現在の状況確認
            "list-recordings",         # 過去の録音履歴確認
            "stats",                   # 全体的な統計確認
            "status"                   # 最終状態確認
        ]
        
        returncode, stdout, stderr = self._run_interactive_process(commands)
        
        # ユーザー体験の品質確認
        self.assertEqual(returncode, 0)
        
        # 各段階での適切な情報表示
        expected_flows = [
            ("help", "利用可能なコマンド"),
            ("list-stations", "放送局一覧"),
            ("list-schedules", "録音予約一覧"),
            ("status", "システム状況"),
            ("list-recordings", "録音ファイル一覧"),
            ("stats", "統計情報")
        ]
        
        for command, expected_output in expected_flows:
            self.assertIn(expected_output, stdout, 
                         f"コマンド '{command}' の期待出力 '{expected_output}' が見つかりません")
    
    def test_interactive_concurrent_operation_safety(self):
        """並行操作安全性テスト"""
        # 同一設定で複数の対話型セッションが安全に動作することを確認
        
        def run_session(commands, results_queue):
            try:
                returncode, stdout, stderr = self._run_interactive_process(commands, timeout=20)
                results_queue.put((returncode, stdout, stderr))
            except Exception as e:
                results_queue.put((None, None, str(e)))
        
        # 2つの並行セッション
        session1_commands = ["status", "list-schedules", "stats"]
        session2_commands = ["help", "list-recordings", "status"]
        
        results_queue = queue.Queue()
        
        # 並行実行
        thread1 = threading.Thread(target=run_session, args=(session1_commands, results_queue))
        thread2 = threading.Thread(target=run_session, args=(session2_commands, results_queue))
        
        thread1.start()
        thread2.start()
        
        thread1.join(timeout=30)
        thread2.join(timeout=30)
        
        # 結果確認
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        self.assertEqual(len(results), 2, "両方のセッションが完了していません")
        
        for returncode, stdout, stderr in results:
            if returncode is not None:
                self.assertEqual(returncode, 0, f"セッションが失敗しました: {stderr}")
    
    def test_interactive_configuration_integration(self):
        """設定統合テスト"""
        # カスタム設定での動作確認
        custom_config = self.test_config.copy()
        custom_config['log_level'] = 'INFO'
        custom_config['max_concurrent_recordings'] = 4
        
        custom_config_file = Path(self.test_dir) / "custom_config.json"
        with open(custom_config_file, 'w') as f:
            json.dump(custom_config, f)
        
        # カスタム設定での対話型モード実行
        env = os.environ.copy()
        env['PYTEST_CURRENT_TEST'] = 'test'
        
        process = subprocess.Popen(
            ['python', str(self.recradiko_script), '--config', str(custom_config_file), '--interactive'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(self.project_root),
            env=env
        )
        
        self.processes.append(process)
        
        # コマンド実行
        stdout, stderr = process.communicate(input="status\\nexit\\n", timeout=15)
        
        # 設定が反映されていることを確認
        self.assertEqual(process.returncode, 0)
        self.assertIn("システム状況", stdout)
    
    def test_interactive_graceful_shutdown(self):
        """正常終了テスト"""
        shutdown_commands = [
            ["exit"],
            ["quit"], 
            ["q"]
        ]
        
        for commands in shutdown_commands:
            with self.subTest(exit_command=commands[0]):
                returncode, stdout, stderr = self._run_interactive_process(commands, timeout=10)
                
                # 正常終了の確認
                self.assertEqual(returncode, 0)
                self.assertIn("RecRadikoを終了します", stdout)


if __name__ == '__main__':
    unittest.main()