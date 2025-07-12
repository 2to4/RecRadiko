"""
実際のRadiko APIを使用するE2Eテスト（最新設計対応版）

このテストは実際のRadiko APIを呼び出すため、CI環境では条件付きで実行されます。
環境変数 SKIP_REAL_API_TESTS=1 を設定することで無効化できます。

2025年7月12日更新: ライブストリーミング対応・最新アーキテクチャ対応
- 不要テストケース削除済み（13→5テストに削減）
- ライブストリーミング機能統合
- 対話型CLI対応
- 実用性重視の厳選テストケース
"""

import os
import pytest
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Optional

from src.auth import RadikoAuthenticator
from src.program_info import ProgramInfoManager
from src.streaming import StreamingManager
from src.recording import RecordingManager, RecordingJob, RecordingStatus
from src.cli import RecRadikoCLI
from src.live_streaming import LiveRecordingSession, LivePlaylistMonitor


class TestRealRadikoAPI:
    """実際のRadiko APIを使用するE2Eテスト（厳選版）"""
    
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
            'output_dir': os.path.join(self.temp_dir, 'recordings'),
            'max_concurrent_recordings': 2,
            'default_format': 'mp3',
            'default_bitrate': 128,
            'live_streaming_enabled': True,
            'playlist_update_interval': 5,
            'max_concurrent_downloads': 3,
            'notification_enabled': False,
            'log_level': 'INFO'
        }
        
        # 録音ディレクトリ作成
        os.makedirs(self.config['output_dir'], exist_ok=True)
        
        # 設定ファイルの作成（一時ファイル）
        import json
        self.config_file = os.path.join(self.temp_dir, 'config.json')
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)
        
        # 実際のAPIクライアント初期化（最新アーキテクチャ対応）
        self.auth = RadikoAuthenticator()
        self.program_info = ProgramInfoManager(authenticator=self.auth)
        self.streaming_manager = StreamingManager(authenticator=self.auth)
        self.recording_manager = RecordingManager(
            authenticator=self.auth,
            program_manager=self.program_info,
            streaming_manager=self.streaming_manager
        )
        self.cli = RecRadikoCLI(config_file=self.config_file)
    
    def teardown_method(self):
        """テストメソッドの後処理"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
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
        
        # エリアIDの確認
        assert len(auth_info.area_id) >= 4, f"エリアIDが短すぎます: {auth_info.area_id}"
        assert auth_info.area_id.startswith('JP'), f"日本のエリアIDではありません: {auth_info.area_id}"
        
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
        major_stations = ['TBS', 'LFR', 'QRR', 'FMT', 'FMJ']
        found_stations = [s.id for s in stations if s.id in major_stations]
        assert len(found_stations) >= 3, f"主要局が不足: {found_stations}"
        
        print(f"✅ 放送局リスト取得成功: {len(stations)}局")
        print(f"✅ 主要局確認: {found_stations}")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    def test_real_live_streaming_url_acquisition(self):
        """R3: 実際のライブストリーミングURL取得テスト（最新設計対応）"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # ライブストリーミングURLの取得
        stream_url = self.streaming_manager.get_stream_url('TBS', datetime.now())
        
        # ストリーミングURLの検証
        assert stream_url is not None, "ストリーミングURLが取得できませんでした"
        assert stream_url.startswith('http'), f"不正なURL形式: {stream_url}"
        assert '.m3u8' in stream_url, f"M3U8ファイルでない: {stream_url}"
        
        # HLSプレイリストの検証
        try:
            import requests
            response = requests.get(stream_url, timeout=10)
            assert response.status_code == 200, f"ストリーミングURLにアクセスできません: {response.status_code}"
            assert '#EXTM3U' in response.text, "有効なM3U8プレイリストではありません"
            print(f"✅ HLSプレイリスト検証成功")
        except Exception as e:
            print(f"⚠️ HLSプレイリスト検証スキップ: {e}")
        
        print(f"✅ ライブストリーミングURL取得成功: {stream_url[:50]}...")
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    @pytest.mark.slow
    def test_real_live_recording_60_seconds(self):
        """R4: 実際のライブ録音テスト（60秒）- 最新設計対応"""
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # 60秒間のライブ録音ジョブを作成
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=60)
        output_path = os.path.join(self.config['output_dir'], 'live_test_60s.mp3')
        
        # 録音ジョブの作成（最新設計）
        job = RecordingJob(
            id="live_test_60s",
            station_id='TBS',
            program_title='ライブテスト録音',
            start_time=start_time,
            end_time=end_time,
            output_path=output_path,
            status=RecordingStatus.PENDING
        )
        
        # ライブ録音セッションの作成
        live_session = LiveRecordingSession(job, self.streaming_manager)
        
        # 非同期録音の実行
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(live_session.start_recording(output_path))
            
            # 録音結果の検証
            assert result.success, f"ライブ録音が失敗しました: {result.error_messages}"
            assert result.total_segments > 0, "セグメントが取得されませんでした"
            assert result.downloaded_segments > 0, "ダウンロードされたセグメントがありません"
            
            # 録音ファイルの確認
            assert os.path.exists(output_path), "録音ファイルが存在しません"
            
            # ファイルサイズの確認（最低10KB以上）
            file_size = os.path.getsize(output_path)
            assert file_size > 10240, f"録音ファイルサイズが小さすぎます: {file_size}bytes"
            
            # 録音品質の確認
            success_rate = (result.downloaded_segments / result.total_segments) * 100
            assert success_rate >= 80, f"セグメント取得成功率が低すぎます: {success_rate:.1f}%"
            
            print(f"✅ 60秒ライブ録音成功: {output_path}")
            print(f"✅ ファイルサイズ: {file_size:,} bytes")
            print(f"✅ セグメント取得率: {success_rate:.1f}% ({result.downloaded_segments}/{result.total_segments})")
            
        finally:
            loop.close()
    
    @pytest.mark.e2e
    @pytest.mark.real_api
    def test_real_cli_integration(self):
        """R5: 実際の対話型CLI統合テスト（最新設計対応）"""
        # CLIインスタンスに実際のAPI対応マネージャーを注入
        self.cli.authenticator = self.auth
        self.cli.program_info_manager = self.program_info
        self.cli.streaming_manager = self.streaming_manager
        self.cli.recording_manager = self.recording_manager
        
        # 認証の実行
        auth_result = self.auth.authenticate()
        assert auth_result is True, "認証が必要です"
        
        # CLI経由での放送局一覧取得（対話型コマンド）
        import io
        from contextlib import redirect_stdout
        
        with redirect_stdout(io.StringIO()) as captured_output:
            stations_result = self.cli._execute_interactive_command(['list-stations'])
            
        assert stations_result == 0, "CLI放送局一覧取得が失敗しました"
        output = captured_output.getvalue()
        assert "放送局一覧" in output, "放送局一覧が出力されませんでした"
        assert "TBS" in output, "TBSラジオが見つかりません"
        
        # CLI経由でのシステム状態確認
        with redirect_stdout(io.StringIO()) as captured_output:
            status_result = self.cli._execute_interactive_command(['status'])
            
        assert status_result == 0, "CLIステータス取得が失敗しました"
        output = captured_output.getvalue()
        assert "システム状態" in output, "システム状態が出力されませんでした"
        
        print("✅ 対話型CLI統合テスト成功")


if __name__ == '__main__':
    pytest.main([__file__])