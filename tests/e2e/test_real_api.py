"""
実際のRadiko APIを使用するE2Eテスト

このテストは実際のRadiko APIを呼び出すため、CI環境では条件付きで実行されます。
環境変数 SKIP_REAL_API_TESTS=1 を設定することで無効化できます。
"""

import os
import pytest
import time
import tempfile
from datetime import datetime, timedelta
from typing import Optional

from src.auth import RadikoAuthenticator
from src.program_info import ProgramInfoManager
from src.streaming import StreamingManager
from src.recording import RecordingManager
from src.cli import RecRadikoCLI


class TestRealRadikoAPI:
    """実際のRadiko APIを使用するE2Eテスト"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """テストメソッドの前処理"""
        # CI環境では実際のAPIテストをスキップ
        if os.getenv('SKIP_REAL_API_TESTS') == '1':
            pytest.skip('Real API tests are disabled in CI environment')
        
        # テスト用の一時ディレクトリ作成
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'area_id': 'JP14',  # 神奈川県
            'output_dir': self.temp_dir,
            'max_concurrent_recordings': 2,
            'database_path': os.path.join(self.temp_dir, 'test_database.db'),
            'auth_cache_path': os.path.join(self.temp_dir, 'auth_cache.json'),
            'recording': {
                'default_format': 'aac',
                'default_bitrate': 128
            },
            'logging': {
                'level': 'INFO',
                'log_file': os.path.join(self.temp_dir, 'test.log')
            }
        }
        
        # 設定ファイルの作成（一時ファイル）
        import json
        self.config_file = os.path.join(self.temp_dir, 'config.json')
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)
        
        # 実際のAPIクライアント初期化
        self.auth = RadikoAuthenticator(self.config_file)
        self.program_info = ProgramInfoManager(self.config_file)
        self.streaming_manager = StreamingManager(self.config_file)
        self.recording_manager = RecordingManager(self.config_file)
        self.cli = RecRadikoCLI(config_file=self.config_file)
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    def test_real_authentication_flow(self):
        """R1: 実際のRadiko認証フローテスト"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        
        # 認証成功の確認
        assert auth_result is True, "Radiko認証が失敗しました"
        
        # 認証情報の取得
        auth_info = self.auth.get_valid_auth_info()
        assert auth_info is not None, "認証情報が取得できませんでした"
        assert auth_info.auth_token is not None, "認証トークンが取得できませんでした"
        assert auth_info.area_id is not None, "エリアIDが取得できませんでした"
        
        # JP14エリアの確認（神奈川県）
        assert auth_info.area_id == 'JP14', f"期待されるエリアID: JP14, 実際: {auth_info.area_id}"
        
        print(f"✅ 認証成功: トークン={auth_info.auth_token[:10]}..., エリア={auth_info.area_id}")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    def test_real_station_list_retrieval(self):
        """R2: 実際の放送局リスト取得テスト"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # 放送局リストの取得
        stations = self.program_info.get_station_list()
        
        # 放送局リストの検証
        assert len(stations) > 0, "放送局リストが空です"
        assert len(stations) >= 10, f"放送局数が少なすぎます: {len(stations)}局"
        
        # TBSラジオの存在確認
        tbs_station = None
        for station in stations:
            if station.id == 'TBS':
                tbs_station = station
                break
        
        assert tbs_station is not None, "TBSラジオが見つかりません"
        assert tbs_station.name is not None, "TBSラジオの名前が取得できません"
        assert len(tbs_station.name) > 0, "TBSラジオの名前が空です"
        
        # 主要局の存在確認
        major_stations = ['TBS', 'LFR', 'QRR', 'RN1', 'RN2', 'INT', 'FMT', 'FMJ', 'JORF']
        found_stations = [s.id for s in stations if s.id in major_stations]
        assert len(found_stations) >= 5, f"主要局が不足: {found_stations}"
        
        print(f"✅ 放送局リスト取得成功: {len(stations)}局")
        print(f"✅ 主要局確認: {found_stations}")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    def test_real_program_guide_retrieval(self):
        """R3: 実際の番組表取得テスト"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # 現在の日付で番組表を取得
        today = datetime.now().strftime('%Y%m%d')
        programs = self.program_info.get_program_list('TBS', today)
        
        # 番組表の検証
        assert len(programs) > 0, "番組表が空です"
        assert len(programs) >= 10, f"番組数が少なすぎます: {len(programs)}個"
        
        # 番組情報の検証
        for program in programs[:5]:  # 最初の5番組を検証
            assert program.title is not None, "番組タイトルが取得できません"
            assert len(program.title) > 0, "番組タイトルが空です"
            assert program.start_time is not None, "開始時刻が取得できません"
            assert program.end_time is not None, "終了時刻が取得できません"
            assert program.start_time < program.end_time, "開始時刻が終了時刻より遅いです"
        
        print(f"✅ 番組表取得成功: {len(programs)}番組")
        print(f"✅ 最初の番組: {programs[0].title}")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    def test_real_streaming_url_acquisition(self):
        """R4: 実際のストリーミングURL取得テスト"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # ストリーミングURLの取得
        stream_url = self.streaming_manager.get_stream_url('TBS')
        
        # ストリーミングURLの検証
        assert stream_url is not None, "ストリーミングURLが取得できませんでした"
        assert stream_url.startswith('http'), f"不正なURL形式: {stream_url}"
        assert '.m3u8' in stream_url, f"M3U8ファイルでない: {stream_url}"
        
        print(f"✅ ストリーミングURL取得成功: {stream_url[:50]}...")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    @pytest.mark.slow
    def test_real_short_recording(self):
        """R5: 実際の短時間録音テスト（30秒）"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # 30秒間の録音ジョブを作成
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=30)
        
        # 録音の実行
        job_id = self.recording_manager.create_recording_job(
            station_id='TBS',
            start_time=start_time,
            end_time=end_time,
            output_format='aac',
            title='E2E_Test_Recording'
        )
        
        assert job_id is not None, "録音ジョブが作成できませんでした"
        
        # 録音の開始
        recording_result = self.recording_manager.start_recording(job_id)
        assert recording_result is True, "録音開始が失敗しました"
        
        # 録音完了まで待機（最大45秒）
        max_wait_time = 45
        wait_time = 0
        while wait_time < max_wait_time:
            time.sleep(1)
            wait_time += 1
            
            # 録音状態の確認
            status = self.recording_manager.get_recording_status(job_id)
            if status and status.status == 'completed':
                break
        
        # 録音完了の確認
        final_status = self.recording_manager.get_recording_status(job_id)
        assert final_status is not None, "録音状態が取得できませんでした"
        assert final_status.status == 'completed', f"録音が完了していません: {final_status.status}"
        
        # 録音ファイルの確認
        assert final_status.output_file is not None, "録音ファイルパスが取得できませんでした"
        assert os.path.exists(final_status.output_file), "録音ファイルが存在しません"
        
        # ファイルサイズの確認（最低1KB以上）
        file_size = os.path.getsize(final_status.output_file)
        assert file_size > 1024, f"録音ファイルサイズが小さすぎます: {file_size}bytes"
        
        print(f"✅ 30秒録音成功: {final_status.output_file}")
        print(f"✅ ファイルサイズ: {file_size:,} bytes")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    def test_real_cli_integration(self):
        """R6: 実際のCLI統合テスト"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # CLI経由での放送局一覧取得
        stations_result = self.cli._execute_interactive_command(['list-stations'])
        assert stations_result == 0, "CLI放送局一覧取得が失敗しました"
        
        # CLI経由での番組表取得
        today = datetime.now().strftime('%Y-%m-%d')
        programs_result = self.cli._execute_interactive_command(['list-programs', '--station', 'TBS', '--date', today])
        assert programs_result == 0, "CLI番組表取得が失敗しました"
        
        print("✅ CLI統合テスト成功")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    def test_real_error_handling(self):
        """R7: 実際のエラーハンドリングテスト"""
        # 不正な放送局IDでのテスト
        try:
            stream_url = self.streaming_manager.get_stream_url('INVALID_STATION')
            # エラーが発生せずにURLが取得された場合は、適切なエラーメッセージを確認
            assert stream_url is None or 'error' in stream_url.lower(), "不正な放送局IDでエラーが発生しませんでした"
        except Exception as e:
            # 適切な例外が発生した場合は正常
            assert len(str(e)) > 0, "エラーメッセージが空です"
            print(f"✅ 適切なエラーハンドリング: {type(e).__name__}")
        
        # 不正な日付での番組表取得テスト
        try:
            programs = self.program_info.get_program_list('TBS', '20001231')  # 過去の日付
            # 空のリストが返されることを確認
            assert isinstance(programs, list), "番組表が正しい形式で返されませんでした"
            print(f"✅ 過去日付での番組表取得: {len(programs)}番組")
        except Exception as e:
            # 適切な例外が発生した場合も正常
            print(f"✅ 適切なエラーハンドリング: {type(e).__name__}")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    def test_real_api_rate_limiting(self):
        """R8: 実際のAPI レート制限テスト"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # 連続してAPI呼び出しを行い、レート制限を確認
        successful_calls = 0
        max_calls = 10
        
        for i in range(max_calls):
            try:
                stations = self.program_info.get_station_list()
                if len(stations) > 0:
                    successful_calls += 1
                time.sleep(0.5)  # 0.5秒間隔
            except Exception as e:
                print(f"API呼び出し{i+1}回目でエラー: {type(e).__name__}")
                break
        
        # 最低5回は成功することを確認
        assert successful_calls >= 5, f"API呼び出し成功回数が少なすぎます: {successful_calls}/{max_calls}"
        
        print(f"✅ API レート制限テスト: {successful_calls}/{max_calls}回成功")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    def test_real_authentication_expiry(self):
        """R9: 実際の認証有効期限テスト"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # 初回認証情報の取得
        auth_info1 = self.auth.get_valid_auth_info()
        assert auth_info1 is not None, "初回認証情報が取得できませんでした"
        
        # 短時間待機
        time.sleep(2)
        
        # 再度認証情報の取得
        auth_info2 = self.auth.get_valid_auth_info()
        assert auth_info2 is not None, "2回目の認証情報が取得できませんでした"
        
        # 認証情報の有効性確認
        assert auth_info1.auth_token == auth_info2.auth_token, "認証トークンが変更されました"
        assert auth_info1.area_id == auth_info2.area_id, "エリアIDが変更されました"
        
        print("✅ 認証有効期限テスト成功")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    def test_real_concurrent_access(self):
        """R10: 実際の同時アクセステスト"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # 複数の操作を同時に実行
        import threading
        import queue
        
        results = queue.Queue()
        
        def get_stations():
            try:
                stations = self.program_info.get_station_list()
                results.put(('stations', len(stations) > 0))
            except Exception as e:
                results.put(('stations', False))
        
        def get_programs():
            try:
                today = datetime.now().strftime('%Y%m%d')
                programs = self.program_info.get_program_list('TBS', today)
                results.put(('programs', len(programs) > 0))
            except Exception as e:
                results.put(('programs', False))
        
        def get_stream_url():
            try:
                stream_url = self.streaming_manager.get_stream_url('TBS')
                results.put(('stream_url', stream_url is not None))
            except Exception as e:
                results.put(('stream_url', False))
        
        # スレッドの作成と実行
        threads = [
            threading.Thread(target=get_stations),
            threading.Thread(target=get_programs),
            threading.Thread(target=get_stream_url)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=30)
        
        # 結果の確認
        test_results = {}
        while not results.empty():
            test_name, success = results.get()
            test_results[test_name] = success
        
        assert len(test_results) == 3, "全てのテストが完了していません"
        assert all(test_results.values()), f"同時アクセステストで失敗: {test_results}"
        
        print("✅ 同時アクセステスト成功")


class TestRealAPIContracts:
    """実際のRadiko API契約テスト"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """テストメソッドの前処理"""
        if os.getenv('SKIP_REAL_API_TESTS') == '1':
            pytest.skip('Real API contract tests are disabled in CI environment')
        
        # 設定ファイルの作成
        import tempfile
        import json
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'area_id': 'JP14',
            'database_path': os.path.join(self.temp_dir, 'test_database.db'),
            'auth_cache_path': os.path.join(self.temp_dir, 'auth_cache.json'),
            'logging': {
                'level': 'INFO',
                'log_file': os.path.join(self.temp_dir, 'test.log')
            }
        }
        self.config_file = os.path.join(self.temp_dir, 'config.json')
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)
        
        self.auth = RadikoAuthenticator(self.config_file)
        self.program_info = ProgramInfoManager(self.config_file)
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    @pytest.mark.contract
    def test_station_list_xml_structure(self):
        """C1: 放送局リストXML構造の契約テスト"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # 実際のXMLレスポンスの検証
        stations = self.program_info.get_station_list()
        assert len(stations) > 0, "放送局リストが空です"
        
        # 構造の検証
        station = stations[0]
        assert hasattr(station, 'id'), "Station.idが存在しません"
        assert hasattr(station, 'name'), "Station.nameが存在しません"
        assert hasattr(station, 'area_id'), "Station.area_idが存在しません"
        
        # IDの形式確認
        assert len(station.id) > 0, "Station.idが空です"
        assert isinstance(station.id, str), f"Station.idが文字列でない: {type(station.id)}"
        
        print(f"✅ 放送局XML構造検証成功: {station.id}, {station.name}")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    @pytest.mark.contract
    def test_program_list_xml_structure(self):
        """C2: 番組表XML構造の契約テスト"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # 実際のXMLレスポンスの検証
        today = datetime.now().strftime('%Y%m%d')
        programs = self.program_info.get_program_list('TBS', today)
        assert len(programs) > 0, "番組表が空です"
        
        # 構造の検証
        program = programs[0]
        assert hasattr(program, 'title'), "Program.titleが存在しません"
        assert hasattr(program, 'start_time'), "Program.start_timeが存在しません"
        assert hasattr(program, 'end_time'), "Program.end_timeが存在しません"
        
        # データ型の確認
        assert isinstance(program.title, str), f"Program.titleが文字列でない: {type(program.title)}"
        assert isinstance(program.start_time, datetime), f"Program.start_timeがdatetimeでない: {type(program.start_time)}"
        assert isinstance(program.end_time, datetime), f"Program.end_timeがdatetimeでない: {type(program.end_time)}"
        
        print(f"✅ 番組XML構造検証成功: {program.title}")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    @pytest.mark.contract
    def test_streaming_url_format(self):
        """C3: ストリーミングURL形式の契約テスト"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # ストリーミングマネージャーの初期化
        streaming_manager = StreamingManager(self.config)
        
        # 実際のストリーミングURL取得
        stream_url = streaming_manager.get_stream_url('TBS')
        
        # URL形式の検証
        assert stream_url is not None, "ストリーミングURLが取得できませんでした"
        assert stream_url.startswith('http'), f"HTTPで始まらない: {stream_url}"
        assert '.m3u8' in stream_url, f"M3U8ファイルでない: {stream_url}"
        
        # URL構造の確認
        from urllib.parse import urlparse
        parsed = urlparse(stream_url)
        assert parsed.scheme in ['http', 'https'], f"不正なスキーム: {parsed.scheme}"
        assert parsed.netloc != '', f"ホスト名が空: {stream_url}"
        
        print(f"✅ ストリーミングURL形式検証成功: {parsed.netloc}")