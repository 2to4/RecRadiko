"""
E2Eテストフレームワークの動作確認テスト

このモジュールでは、E2Eテストフレームワーク自体の機能を検証します。
- 時間加速機能
- テストデータ生成
- リソース監視
- ネットワークシミュレーション
"""

import pytest
import time
import os
from datetime import datetime, timedelta
from unittest.mock import patch

from .conftest import TimeAccelerator, TestDataGenerator, ResourceMonitor


class TestE2EFramework:
    """E2Eテストフレームワーク機能テスト"""
    
    def test_time_acceleration(self, time_accelerator):
        """時間加速機能のテスト"""
        start_time = time.time()
        
        # 10秒の加速スリープ（実際は0.1秒）
        time_accelerator.accelerated_sleep(10)
        
        elapsed = time.time() - start_time
        
        # 加速により実際の経過時間は大幅に短い
        assert elapsed < 1.0, f"時間加速が機能していない: {elapsed}秒経過"
        assert elapsed > 0.05, f"時間加速が速すぎる: {elapsed}秒経過"
    
    def test_accelerated_datetime(self, time_accelerator):
        """加速時刻機能のテスト"""
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        
        # 最初の時刻取得
        first_time = time_accelerator.accelerated_datetime(base_time)
        
        # 少し待機
        time.sleep(0.1)
        
        # 2回目の時刻取得
        second_time = time_accelerator.accelerated_datetime(base_time)
        
        # 加速により大幅に時間が進んでいる
        time_diff = second_time - first_time
        assert time_diff.total_seconds() > 5, f"時間加速が不十分: {time_diff.total_seconds()}秒"
    
    def test_temp_environment(self, temp_environment):
        """一時環境作成のテスト"""
        # 必要なディレクトリが作成されている
        assert os.path.exists(temp_environment["base_dir"])
        assert os.path.exists(temp_environment["config_dir"])
        assert os.path.exists(temp_environment["output_dir"])
        assert os.path.exists(temp_environment["log_dir"])
        assert os.path.exists(temp_environment["data_dir"])
        assert os.path.exists(temp_environment["cache_dir"])
        
        # ベースディレクトリにrecradiko_e2e_が含まれている
        assert "recradiko_e2e_" in temp_environment["base_dir"]
    
    def test_config_generation(self, test_config):
        """設定ファイル生成のテスト"""
        config_path, config_dict = test_config
        
        # 設定ファイルが作成されている
        assert os.path.exists(config_path)
        
        # 必要な設定項目が含まれている
        assert "area_id" in config_dict
        assert "output_dir" in config_dict
        assert "e2e_test" in config_dict
        assert config_dict["e2e_test"]["time_acceleration"] == 100
        assert config_dict["e2e_test"]["mock_external_apis"] is True
    
    def test_station_data_generation(self, test_data_generator):
        """放送局データ生成のテスト"""
        stations = test_data_generator.generate_stations(10)
        
        assert len(stations) == 10
        
        # 最初の数個は既知の放送局
        assert stations[0].id == "TBS"
        assert stations[0].name == "TBSラジオ"
        assert stations[1].id == "QRR"
        assert stations[1].name == "文化放送"
        
        # IDとnameが設定されている
        for station in stations:
            assert station.id
            assert station.name
            assert station.area_id == "JP13"
    
    def test_program_data_generation(self, test_data_generator):
        """番組データ生成のテスト"""
        stations = test_data_generator.generate_stations(3)
        programs = test_data_generator.generate_programs(stations, 2)  # 2日分
        
        # 3放送局 × 8番組/日 × 2日 = 48番組
        assert len(programs) == 48
        
        # 番組データの整合性確認
        for program in programs:
            assert program.id
            assert program.station_id in [s.id for s in stations]
            assert program.title
            assert program.start_time < program.end_time
            assert program.duration > 0
    
    def test_schedule_data_generation(self, test_data_generator):
        """スケジュールデータ生成のテスト"""
        stations = test_data_generator.generate_stations(5)
        schedules = test_data_generator.generate_schedules(stations, 20)
        
        assert len(schedules) == 20
        
        # スケジュールデータの整合性確認
        for schedule in schedules:
            assert schedule.schedule_id
            assert schedule.station_id in [s.id for s in stations]
            assert schedule.program_title
            assert schedule.start_time < schedule.end_time
            assert schedule.format in ["aac", "mp3"]
            assert 64 <= schedule.bitrate <= 320
    
    def test_large_dataset_generation(self, large_test_dataset):
        """大規模データセット生成のテスト"""
        dataset = large_test_dataset
        
        # 期待される数量
        assert dataset["station_count"] == 50
        assert dataset["program_count"] > 1000  # 50局 × 8番組 × 30日
        assert dataset["schedule_count"] == 5000
        
        # データの型確認
        assert len(dataset["stations"]) == 50
        assert len(dataset["programs"]) == dataset["program_count"]
        assert len(dataset["schedules"]) == 5000
    
    def test_large_file_generation(self, test_data_generator, temp_environment):
        """大量ファイル生成のテスト（小規模）"""
        # テスト用に少数のファイルを生成
        files = test_data_generator.generate_large_file_set(
            temp_environment["output_dir"], 
            10  # テスト用に10ファイルのみ
        )
        
        assert len(files) == 10
        
        # すべてのファイルが存在する
        for file_path in files:
            assert os.path.exists(file_path)
            assert os.path.getsize(file_path) > 1024 * 1024  # 1MB以上
    
    def test_resource_monitor(self, resource_monitor):
        """リソース監視のテスト"""
        # 監視開始
        resource_monitor.start_monitoring(0.1)  # 0.1秒間隔
        
        # 少し待機
        time.sleep(0.5)
        
        # 監視停止
        resource_monitor.stop_monitoring()
        
        # 監視結果確認
        summary = resource_monitor.get_summary()
        
        # CPU使用率が記録されている
        if "cpu_usage" in summary:
            assert summary["cpu_usage"]["count"] > 0
            assert 0 <= summary["cpu_usage"]["latest"] <= 100
        
        # メモリ使用量が記録されている
        if "memory_usage" in summary:
            assert summary["memory_usage"]["count"] > 0
            assert 0 <= summary["memory_usage"]["latest"] <= 100
    
    def test_mock_external_services(self, mock_external_services):
        """外部サービスモックのテスト"""
        mocks = mock_external_services
        
        # 認証モックの動作確認
        auth_result = mocks["auth"].return_value
        assert auth_result.auth_token == "test_token_e2e"
        assert auth_result.area_id == "JP13"
        
        # ストリーミングモックの動作確認
        stream_url = mocks["stream"].return_value
        assert stream_url == "https://example.com/test_stream.m3u8"
    
    def test_network_simulator(self, network_simulator):
        """ネットワークシミュレータのテスト"""
        # 正常接続
        network_simulator.set_normal_connection()
        assert network_simulator.conditions["latency"] == 50
        assert network_simulator.conditions["packet_loss"] == 0
        
        # 低品質接続
        network_simulator.set_poor_connection()
        assert network_simulator.conditions["latency"] == 1000
        assert network_simulator.conditions["packet_loss"] == 5
        
        # 不安定接続
        network_simulator.set_unstable_connection()
        assert network_simulator.conditions["latency"] == 500
        assert network_simulator.conditions["connection_drops"] is True
        
        # ネットワークエラーシミュレーション
        import requests
        with pytest.raises(requests.exceptions.ConnectionError):
            network_simulator.simulate_network_error()


@pytest.mark.e2e
class TestE2EFrameworkIntegration:
    """E2Eフレームワーク統合テスト"""
    
    def test_complete_framework_setup(self, temp_environment, test_config, 
                                    large_test_dataset, time_accelerator,
                                    resource_monitor, mock_external_services):
        """フレームワーク全体のセットアップテスト"""
        # 環境セットアップ確認
        assert os.path.exists(temp_environment["base_dir"])
        
        # 設定ファイル確認
        config_path, config_dict = test_config
        assert os.path.exists(config_path)
        
        # 大規模データセット確認
        assert large_test_dataset["station_count"] == 50
        assert large_test_dataset["schedule_count"] == 5000
        
        # 時間加速機能確認
        start_time = time.time()
        time_accelerator.accelerated_sleep(1)
        elapsed = time.time() - start_time
        assert elapsed < 0.1  # 大幅に短縮
        
        # リソース監視開始
        resource_monitor.start_monitoring(0.1)
        
        # 少し待機
        time.sleep(0.3)
        
        # 監視停止・結果確認
        resource_monitor.stop_monitoring()
        summary = resource_monitor.get_summary()
        assert len(summary) > 0
        
        # モック確認
        assert mock_external_services["auth"].return_value.auth_token == "test_token_e2e"
    
    def test_framework_performance(self, test_data_generator, temp_environment):
        """フレームワークの性能テスト"""
        start_time = time.time()
        
        # 中規模データセット生成
        stations = test_data_generator.generate_stations(20)
        programs = test_data_generator.generate_programs(stations, 7)
        schedules = test_data_generator.generate_schedules(stations, 1000)
        
        generation_time = time.time() - start_time
        
        # データ生成時間は妥当な範囲内
        assert generation_time < 10.0, f"データ生成が遅すぎる: {generation_time}秒"
        
        # 生成されたデータ量確認
        assert len(stations) == 20
        assert len(programs) == 20 * 8 * 7  # 20局 × 8番組 × 7日
        assert len(schedules) == 1000


if __name__ == "__main__":
    # フレームワークテストの直接実行
    pytest.main([__file__, "-v"])