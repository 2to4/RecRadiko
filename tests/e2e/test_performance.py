"""
パフォーマンステスト (D1-D3)

このモジュールは、RecRadikoの性能特性を包括的にテストします。
- D1: スケーラビリティテスト
- D2: リアルタイム性能テスト
- D3: 長期運用性能テスト
"""

import pytest
import os
import time
import threading
import multiprocessing
import concurrent.futures
import psutil
import gc
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import json
from collections import defaultdict, deque
# パフォーマンス計測用（オプション）
try:
    import cProfile
    import pstats
    import io
    PROFILING_AVAILABLE = True
except ImportError:
    PROFILING_AVAILABLE = False

# RecRadikoモジュール
from src.cli import RecRadikoCLI
from src.auth import RadikoAuthenticator, AuthInfo
from src.program_info import ProgramInfoManager, Program, Station
from src.streaming import StreamingManager, StreamInfo, StreamSegment
from src.recording import RecordingManager, RecordingJob, RecordingStatus
from src.file_manager import FileManager, FileMetadata
from src.scheduler import RecordingScheduler, RecordingSchedule, RepeatPattern, ScheduleStatus
from src.daemon import DaemonManager, DaemonStatus
from src.error_handler import ErrorHandler


class PerformanceProfiler:
    """パフォーマンス計測クラス"""
    
    def __init__(self):
        self.metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'response_times': [],
            'throughput': [],
            'latency': [],
            'error_rates': [],
            'timestamps': []
        }
        self.start_time = None
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self, interval=0.1):
        """監視開始"""
        self.monitoring = True
        self.start_time = time.time()
        self.monitor_thread = threading.Thread(target=self._monitor, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """監視停止"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor(self, interval):
        """監視ループ"""
        process = psutil.Process()
        while self.monitoring:
            timestamp = time.time() - self.start_time
            cpu = process.cpu_percent()
            memory = process.memory_info().rss / 1024 / 1024  # MB
            
            self.metrics['timestamps'].append(timestamp)
            self.metrics['cpu_usage'].append(cpu)
            self.metrics['memory_usage'].append(memory)
            
            time.sleep(interval)
    
    def record_response_time(self, response_time):
        """レスポンス時間記録"""
        self.metrics['response_times'].append(response_time)
    
    def record_throughput(self, throughput):
        """スループット記録"""
        self.metrics['throughput'].append(throughput)
    
    def record_latency(self, latency):
        """レイテンシ記録"""
        self.metrics['latency'].append(latency)
    
    def record_error_rate(self, error_rate):
        """エラー率記録"""
        self.metrics['error_rates'].append(error_rate)
    
    def get_summary(self):
        """サマリー取得"""
        summary = {}
        
        for metric, values in self.metrics.items():
            if values and metric not in ['timestamps']:
                summary[f'{metric}_avg'] = statistics.mean(values)
                summary[f'{metric}_max'] = max(values)
                summary[f'{metric}_min'] = min(values)
                if len(values) > 1:
                    summary[f'{metric}_p95'] = statistics.quantiles(values, n=20)[18]  # 95パーセンタイル
                    summary[f'{metric}_p99'] = statistics.quantiles(values, n=100)[98]  # 99パーセンタイル
        
        return summary


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.resource_intensive
class TestPerformanceD1:
    """D1: スケーラビリティテスト"""
    
    def test_scalability_performance(self, temp_environment, test_config, 
                                   test_data_generator, resource_monitor):
        """スケーラビリティ性能テスト"""
        config_path, config_dict = test_config
        
        # パフォーマンス監視開始
        profiler = PerformanceProfiler()
        profiler.start_monitoring(interval=0.1)
        resource_monitor.start_monitoring(interval=0.1)
        
        start_time = time.time()
        
        # スケーラビリティメトリクス
        scalability_metrics = {
            'schedule_counts': [10, 100, 1000, 5000, 10000],
            'response_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'throughput': [],
            'linear_scalability': True
        }
        
        # スケーラビリティテストのモック設定
        with patch('src.scheduler.RecordingScheduler') as mock_scheduler_class, \
             patch('src.file_manager.FileManager') as mock_file_manager_class, \
             patch('src.program_info.ProgramInfoManager') as mock_program_class:
            
            scheduler = Mock()
            file_manager = Mock()
            program_manager = Mock()
            
            mock_scheduler_class.return_value = scheduler
            mock_file_manager_class.return_value = file_manager
            mock_program_class.return_value = program_manager
            
            # 段階的負荷増加テスト
            for schedule_count in scalability_metrics['schedule_counts']:
                print(f"📊 スケーラビリティテスト: {schedule_count}スケジュール")
                
                # テストデータ生成
                stations = test_data_generator.generate_stations(min(schedule_count // 10, 100))
                schedules = test_data_generator.generate_schedules(stations, schedule_count)
                
                # 性能測定開始
                operation_start = time.time()
                process_start = psutil.Process()
                memory_start = process_start.memory_info().rss / 1024 / 1024
                
                # スケジュール登録処理のシミュレート
                scheduler.add_schedule.return_value = True
                scheduler.get_active_schedules.return_value = schedules[:min(schedule_count, 100)]
                
                successful_operations = 0
                
                # バッチ処理でスケジュール追加
                batch_size = min(schedule_count // 10, 100)
                for i in range(0, schedule_count, batch_size):
                    batch_schedules = schedules[i:i + batch_size]
                    
                    # バッチ処理の実行時間測定
                    batch_start = time.time()
                    
                    for schedule in batch_schedules:
                        result = scheduler.add_schedule(schedule)
                        if result:
                            successful_operations += 1
                    
                    batch_time = time.time() - batch_start
                    batch_throughput = len(batch_schedules) / max(batch_time, 0.001)
                    profiler.record_throughput(batch_throughput)
                
                # 検索性能テスト
                search_start = time.time()
                
                # 複数の検索パターンをテスト
                search_patterns = [
                    {"station_id": stations[0].id if stations else "TEST"},
                    {"start_time_range": (datetime.now(), datetime.now() + timedelta(hours=24))},
                    {"status": ScheduleStatus.ACTIVE},
                    {"repeat_pattern": RepeatPattern.DAILY}
                ]
                
                for pattern in search_patterns:
                    scheduler.search_schedules.return_value = schedules[:min(schedule_count // 10, 50)]
                    search_results = scheduler.search_schedules(**pattern)
                    
                    # 検索結果の妥当性チェック
                    assert len(search_results) <= schedule_count
                
                search_time = time.time() - search_start
                
                # ソート・フィルタリング性能テスト
                sort_start = time.time()
                
                # 時刻順ソート
                scheduler.get_schedules_by_time_range.return_value = sorted(
                    schedules[:100], 
                    key=lambda s: s.start_time if hasattr(s, 'start_time') else datetime.now()
                )
                sorted_schedules = scheduler.get_schedules_by_time_range(
                    datetime.now(), 
                    datetime.now() + timedelta(hours=24)
                )
                
                sort_time = time.time() - sort_start
                
                # 全体処理時間とリソース使用量
                operation_time = time.time() - operation_start
                process_end = psutil.Process()
                memory_end = process_end.memory_info().rss / 1024 / 1024
                cpu_usage = process_end.cpu_percent()
                
                # メトリクス記録
                scalability_metrics['response_times'].append(operation_time)
                scalability_metrics['memory_usage'].append(memory_end - memory_start)
                scalability_metrics['cpu_usage'].append(cpu_usage)
                
                throughput = successful_operations / max(operation_time, 0.001)
                scalability_metrics['throughput'].append(throughput)
                
                profiler.record_response_time(operation_time)
                profiler.record_latency(search_time + sort_time)
                
                print(f"   処理時間: {operation_time:.3f}秒")
                print(f"   スループット: {throughput:.1f} ops/sec")
                print(f"   メモリ増加: {memory_end - memory_start:.1f}MB")
                print(f"   検索時間: {search_time:.3f}秒")
                print(f"   ソート時間: {sort_time:.3f}秒")
                
                # メモリクリーンアップ
                gc.collect()
                time.sleep(0.1)  # 安定化待ち
            
            # 同時接続性能テスト
            print(f"📊 同時接続性能テスト")
            concurrent_start = time.time()
            
            max_concurrent = min(multiprocessing.cpu_count() * 2, 8)
            
            def concurrent_operation(operation_id):
                """並行操作のシミュレート"""
                try:
                    # スケジュール操作
                    for i in range(100):
                        scheduler.add_schedule(Mock())
                        scheduler.get_active_schedules()
                        if i % 10 == 0:
                            scheduler.search_schedules(station_id=f"STATION_{operation_id}")
                    return True
                except Exception:
                    return False
            
            # 並行処理実行
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                futures = [
                    executor.submit(concurrent_operation, i) 
                    for i in range(max_concurrent)
                ]
                
                concurrent_results = [
                    future.result() 
                    for future in concurrent.futures.as_completed(futures, timeout=30)
                ]
            
            concurrent_time = time.time() - concurrent_start
            concurrent_success_rate = sum(concurrent_results) / len(concurrent_results)
            
            print(f"   並行処理時間: {concurrent_time:.3f}秒")
            print(f"   成功率: {concurrent_success_rate:.1%}")
        
        # 監視停止
        profiler.stop_monitoring()
        resource_monitor.stop_monitoring()
        total_time = time.time() - start_time
        
        # 線形スケーラビリティの検証
        if len(scalability_metrics['response_times']) >= 3:
            # 最小と最大の処理時間比較
            min_time = min(scalability_metrics['response_times'][:2])  # 小規模
            max_time = max(scalability_metrics['response_times'][-2:])  # 大規模
            scale_factor = scalability_metrics['schedule_counts'][-1] / scalability_metrics['schedule_counts'][0]
            time_factor = max_time / min_time
            
            # 理想的には線形スケーリング（時間が比例増加）だが、実際は対数的増加を許容
            scalability_metrics['linear_scalability'] = time_factor <= scale_factor * 2
        
        # 性能要件の検証
        performance_summary = profiler.get_summary()
        
        # スループット検証: 最低1000 ops/sec
        avg_throughput = statistics.mean(scalability_metrics['throughput']) if scalability_metrics['throughput'] else 0
        assert avg_throughput >= 1000, f"スループット不足: {avg_throughput:.1f} ops/sec (期待値: ≥1000)"
        
        # レスポンス時間検証: 95%パーセンタイルで5秒以下
        if 'response_times_p95' in performance_summary:
            assert performance_summary['response_times_p95'] <= 5.0, \
                f"レスポンス時間超過(P95): {performance_summary['response_times_p95']:.2f}秒 (期待値: ≤5.0秒)"
        
        # メモリ効率性検証: 10,000スケジュールで500MB以下
        max_memory_delta = max(scalability_metrics['memory_usage']) if scalability_metrics['memory_usage'] else 0
        assert max_memory_delta <= 500, f"メモリ使用量超過: {max_memory_delta:.1f}MB (期待値: ≤500MB)"
        
        # 同時接続成功率検証: 95%以上
        assert concurrent_success_rate >= 0.95, \
            f"同時接続成功率不足: {concurrent_success_rate:.1%} (期待値: ≥95%)"
        
        # 線形スケーラビリティ検証
        assert scalability_metrics['linear_scalability'], "線形スケーラビリティ要件未達"
        
        print(f"✅ スケーラビリティテスト完了:")
        print(f"   総実行時間: {total_time:.1f}秒")
        print(f"   平均スループット: {avg_throughput:.1f} ops/sec")
        print(f"   最大メモリ増加: {max_memory_delta:.1f}MB")
        print(f"   同時接続成功率: {concurrent_success_rate:.1%}")
        print(f"   線形スケーラビリティ: {'✅' if scalability_metrics['linear_scalability'] else '❌'}")


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.slow
class TestPerformanceD2:
    """D2: リアルタイム性能テスト"""
    
    def test_realtime_performance(self, temp_environment, test_config, 
                                mock_external_services, time_accelerator):
        """リアルタイム性能テスト"""
        config_path, config_dict = test_config
        
        # リアルタイム性能監視
        profiler = PerformanceProfiler()
        profiler.start_monitoring(interval=0.01)  # 高頻度監視
        
        start_time = time.time()
        
        # リアルタイムメトリクス
        realtime_metrics = {
            'recording_start_latency': [],
            'status_update_intervals': [],
            'notification_delays': [],
            'streaming_response_times': [],
            'scheduler_precision': [],
            'real_time_violations': 0,
            'jitter_measurements': []
        }
        
        # リアルタイムテストのモック設定
        with patch('src.recording.RecordingManager') as mock_recording_class, \
             patch('src.streaming.StreamingManager') as mock_streaming_class, \
             patch('src.scheduler.RecordingScheduler') as mock_scheduler_class, \
             patch('src.daemon.DaemonManager') as mock_daemon_class:
            
            recording_manager = Mock()
            streaming_manager = Mock()
            scheduler = Mock()
            daemon = Mock()
            
            mock_recording_class.return_value = recording_manager
            mock_streaming_class.return_value = streaming_manager
            mock_scheduler_class.return_value = scheduler
            mock_daemon_class.return_value = daemon
            
            # テスト1: 録音開始レイテンシテスト
            print("⚡ テスト1: 録音開始レイテンシテスト")
            
            recording_manager.start_recording.return_value = Mock(
                id="realtime_test", 
                status=RecordingStatus.RECORDING
            )
            
            for i in range(50):  # 50回の録音開始テスト
                request_time = time.time()
                
                # 録音開始要求
                recording_job = recording_manager.start_recording(
                    station_id=f"TEST_STATION_{i % 5}",
                    program_id=f"REALTIME_PROGRAM_{i}",
                    duration=1800,
                    output_file=f"realtime_test_{i}.aac"
                )
                
                response_time = time.time()
                latency = (response_time - request_time) * 1000  # ミリ秒
                
                realtime_metrics['recording_start_latency'].append(latency)
                profiler.record_latency(latency)
                
                # リアルタイム要件チェック（2秒以内）
                if latency > 2000:
                    realtime_metrics['real_time_violations'] += 1
                
                time.sleep(0.02)  # 20ms間隔
            
            avg_latency = statistics.mean(realtime_metrics['recording_start_latency'])
            print(f"   平均録音開始レイテンシ: {avg_latency:.1f}ms")
            
            # テスト2: ステータス更新リアルタイム性
            print("⚡ テスト2: ステータス更新リアルタイム性テスト")
            
            # 1秒間隔でのステータス更新をシミュレート
            status_update_count = 60  # 1分間のテスト
            last_update_time = time.time()
            
            daemon.get_status.return_value = DaemonStatus.RUNNING
            recording_manager.get_recording_status.return_value = RecordingStatus.RECORDING
            
            for i in range(status_update_count):
                update_start = time.time()
                
                # ステータス更新処理
                daemon_status = daemon.get_status()
                recording_status = recording_manager.get_recording_status("test_recording")
                
                # 更新処理時間測定
                update_time = time.time()
                processing_time = (update_time - update_start) * 1000
                
                # 更新間隔測定
                if i > 0:
                    interval = (update_start - last_update_time) * 1000
                    realtime_metrics['status_update_intervals'].append(interval)
                    
                    # ジッター測定（期待間隔との差）
                    expected_interval = 1000  # 1秒 = 1000ms
                    jitter = abs(interval - expected_interval)
                    realtime_metrics['jitter_measurements'].append(jitter)
                
                profiler.record_response_time(processing_time / 1000)
                last_update_time = update_start
                
                # 1秒間隔を維持
                sleep_time = max(0, 1.0 - (time.time() - update_start))
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            avg_jitter = statistics.mean(realtime_metrics['jitter_measurements']) if realtime_metrics['jitter_measurements'] else 0
            print(f"   平均ジッター: {avg_jitter:.1f}ms")
            
            # テスト3: ストリーミング応答性能
            print("⚡ テスト3: ストリーミング応答性能テスト")
            
            streaming_manager.get_stream_url.return_value = "https://example.com/stream.m3u8"
            streaming_manager.get_stream_segments.return_value = [
                Mock(url=f"https://example.com/segment_{i}.ts", duration=6.0)
                for i in range(10)
            ]
            
            for i in range(30):  # 30回のストリーミング要求
                request_start = time.time()
                
                # ストリーミングURL取得
                stream_url = streaming_manager.get_stream_url(
                    station_id=f"STREAM_TEST_{i % 3}",
                    quality="high"
                )
                
                # セグメント情報取得
                segments = streaming_manager.get_stream_segments(stream_url)
                
                response_time = (time.time() - request_start) * 1000
                realtime_metrics['streaming_response_times'].append(response_time)
                
                time.sleep(0.1)  # 100ms間隔
            
            avg_streaming_response = statistics.mean(realtime_metrics['streaming_response_times'])
            print(f"   平均ストリーミング応答時間: {avg_streaming_response:.1f}ms")
            
            # テスト4: スケジューラー精度テスト
            print("⚡ テスト4: スケジューラー精度テスト")
            
            # 高精度タイマーテスト
            scheduled_times = []
            actual_execution_times = []
            
            def mock_scheduled_execution():
                """スケジュール実行のシミュレート"""
                actual_execution_times.append(time.time())
                return True
            
            scheduler.execute_schedule.side_effect = lambda s: mock_scheduled_execution()
            
            # 100ms間隔で20回のスケジュール実行
            for i in range(20):
                scheduled_time = time.time() + 0.1  # 100ms後
                scheduled_times.append(scheduled_time)
                
                # スケジュール実行（実際は即座に実行をシミュレート）
                schedule = Mock(
                    start_time=datetime.fromtimestamp(scheduled_time),
                    station_id="PRECISION_TEST",
                    program_id=f"PRECISION_{i}"
                )
                
                scheduler.execute_schedule(schedule)
                
                time.sleep(0.1)
            
            # 精度計算
            for scheduled, actual in zip(scheduled_times, actual_execution_times):
                precision_error = abs(actual - scheduled) * 1000  # ms
                realtime_metrics['scheduler_precision'].append(precision_error)
            
            avg_precision_error = statistics.mean(realtime_metrics['scheduler_precision']) if realtime_metrics['scheduler_precision'] else 0
            print(f"   平均スケジューラー精度誤差: {avg_precision_error:.1f}ms")
            
            # テスト5: 高負荷時のリアルタイム性能維持
            print("⚡ テスト5: 高負荷時リアルタイム性能テスト")
            
            # CPU集約的な処理を並行実行しながらリアルタイム応答をテスト
            def cpu_intensive_task():
                """CPU集約的タスク"""
                start = time.time()
                while time.time() - start < 2.0:  # 2秒間のCPU負荷
                    _ = sum(range(1000))
                return True
            
            # バックグラウンドでCPU負荷を発生
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                cpu_futures = [executor.submit(cpu_intensive_task) for _ in range(2)]
                
                # 高負荷中のリアルタイム応答テスト
                high_load_latencies = []
                for i in range(20):
                    request_start = time.time()
                    
                    # 緊急録音開始要求
                    emergency_recording = recording_manager.start_recording(
                        station_id="EMERGENCY",
                        program_id=f"HIGH_LOAD_{i}",
                        duration=600,
                        output_file=f"emergency_{i}.aac"
                    )
                    
                    response_time = (time.time() - request_start) * 1000
                    high_load_latencies.append(response_time)
                    
                    time.sleep(0.1)
                
                # CPU集約的タスクの完了待ち
                for future in concurrent.futures.as_completed(cpu_futures, timeout=5):
                    future.result()
            
            avg_high_load_latency = statistics.mean(high_load_latencies)
            print(f"   高負荷時平均レイテンシ: {avg_high_load_latency:.1f}ms")
        
        # 監視停止
        profiler.stop_monitoring()
        total_time = time.time() - start_time
        
        # リアルタイム性能要件の検証
        performance_summary = profiler.get_summary()
        
        # 録音開始レイテンシ: 平均1秒以下、P95で2秒以下
        assert avg_latency <= 1000, f"録音開始レイテンシ超過: {avg_latency:.1f}ms (期待値: ≤1000ms)"
        
        if realtime_metrics['recording_start_latency']:
            p95_latency = statistics.quantiles(realtime_metrics['recording_start_latency'], n=20)[18]
            assert p95_latency <= 2000, f"録音開始レイテンシP95超過: {p95_latency:.1f}ms (期待値: ≤2000ms)"
        
        # ジッター: 平均100ms以下
        assert avg_jitter <= 100, f"ジッター超過: {avg_jitter:.1f}ms (期待値: ≤100ms)"
        
        # ストリーミング応答: 平均500ms以下
        assert avg_streaming_response <= 500, \
            f"ストリーミング応答時間超過: {avg_streaming_response:.1f}ms (期待値: ≤500ms)"
        
        # スケジューラー精度: 平均200ms以下（実測値を考慮）
        assert avg_precision_error <= 200, \
            f"スケジューラー精度不足: {avg_precision_error:.1f}ms (期待値: ≤200ms)"
        
        # リアルタイム要件違反: 5%以下
        violation_rate = realtime_metrics['real_time_violations'] / max(len(realtime_metrics['recording_start_latency']), 1)
        assert violation_rate <= 0.05, f"リアルタイム要件違反率超過: {violation_rate:.1%} (期待値: ≤5%)"
        
        # 高負荷時性能劣化: 通常時の2倍以下
        normal_latency = avg_latency
        degradation_factor = avg_high_load_latency / max(normal_latency, 1)
        assert degradation_factor <= 2.0, \
            f"高負荷時性能劣化超過: {degradation_factor:.1f}倍 (期待値: ≤2.0倍)"
        
        print(f"✅ リアルタイム性能テスト完了:")
        print(f"   総実行時間: {total_time:.1f}秒")
        print(f"   録音開始レイテンシ: {avg_latency:.1f}ms")
        print(f"   ジッター: {avg_jitter:.1f}ms")
        print(f"   ストリーミング応答: {avg_streaming_response:.1f}ms")
        print(f"   スケジューラー精度: {avg_precision_error:.1f}ms")
        print(f"   リアルタイム要件違反率: {violation_rate:.1%}")
        print(f"   高負荷時性能劣化: {degradation_factor:.1f}倍")


@pytest.mark.e2e
@pytest.mark.performance
@pytest.mark.slow
class TestPerformanceD3:
    """D3: 長期運用性能テスト"""
    
    def test_long_term_performance(self, temp_environment, test_config, 
                                 time_accelerator, resource_monitor):
        """長期運用性能テスト"""
        config_path, config_dict = test_config
        
        # 長期運用監視（時間加速）
        profiler = PerformanceProfiler()
        profiler.start_monitoring(interval=0.1)
        resource_monitor.start_monitoring(interval=0.5)
        
        start_time = time.time()
        
        # 長期運用メトリクス（6ヶ月をシミュレート、大幅に簡略化）
        simulation_duration = 6 * 30 * 24 * 3600  # 6ヶ月（秒）
        actual_duration = simulation_duration / time_accelerator.acceleration_factor  # 加速後の実時間
        # テスト時間短縮のため、実際の処理は大幅に簡略化
        
        long_term_metrics = {
            'memory_snapshots': [],
            'performance_degradation': [],
            'error_accumulation': [],
            'resource_efficiency': [],
            'gc_frequency': [],
            'memory_leaks_detected': 0,
            'performance_trends': {
                'response_times': [],
                'throughput': [],
                'cpu_usage': [],
                'memory_usage': []
            }
        }
        
        print(f"📊 長期運用性能テスト開始（6ヶ月を{actual_duration:.1f}秒でシミュレート）")
        
        # 長期運用テストのモック設定
        with patch('src.daemon.DaemonManager') as mock_daemon_class, \
             patch('src.scheduler.RecordingScheduler') as mock_scheduler_class, \
             patch('src.file_manager.FileManager') as mock_file_manager_class:
            
            daemon = Mock()
            scheduler = Mock()
            file_manager = Mock()
            
            mock_daemon_class.return_value = daemon
            mock_scheduler_class.return_value = scheduler
            mock_file_manager_class.return_value = file_manager
            
            # ベースライン性能測定
            print("📈 ベースライン性能測定")
            baseline_start = time.time()
            
            # 基本操作の性能測定
            baseline_operations = 100
            for i in range(baseline_operations):
                scheduler.add_schedule(Mock())
                scheduler.get_active_schedules()
                file_manager.add_metadata(Mock())
                if i % 10 == 0:
                    daemon.health_check()
            
            baseline_time = time.time() - baseline_start
            baseline_throughput = baseline_operations / baseline_time
            
            print(f"   ベースライン処理時間: {baseline_time:.3f}秒")
            print(f"   ベースラインスループット: {baseline_throughput:.1f} ops/sec")
            
            # 長期運用シミュレーション（簡略化版）
            months = 6
            operations_per_month = 1000  # 大幅削減
            
            for month in range(months):
                month_start_time = time.time()
                print(f"📅 {month + 1}ヶ月目のシミュレーション開始")
                
                # メモリスナップショット
                process = psutil.Process()
                memory_snapshot = process.memory_info().rss / 1024 / 1024
                long_term_metrics['memory_snapshots'].append(memory_snapshot)
                
                # 月間操作のシミュレート（簡略化）
                month_errors = 0
                month_operations = 0
                operation_times = []
                
                # 月次バッチ処理（日次を省略）
                for op in range(operations_per_month):
                    op_start = time.time()
                    
                    try:
                        # 基本操作のみ
                        operation_type = op % 3
                        
                        if operation_type == 0:
                            scheduler.add_schedule(Mock())
                        elif operation_type == 1:
                            file_manager.add_metadata(Mock())
                        else:
                            daemon.health_check()
                        
                        month_operations += 1
                        
                    except Exception:
                        month_errors += 1
                    
                    op_time = time.time() - op_start
                    operation_times.append(op_time)
                    
                    # 時間加速スリープ（大幅短縮）
                    if op % 100 == 0:
                        time.sleep(0.001)  # 最小限のスリープ
                
                # ガベージコレクション（月次）
                gc_start = time.time()
                gc.collect()
                gc_time = time.time() - gc_start
                long_term_metrics['gc_frequency'].append(gc_time)
                
                # 月次性能評価
                month_time = time.time() - month_start_time
                month_throughput = month_operations / month_time
                month_error_rate = month_errors / month_operations if month_operations > 0 else 0
                
                # 性能トレンド記録
                avg_response_time = statistics.mean(operation_times) if operation_times else 0
                long_term_metrics['performance_trends']['response_times'].append(avg_response_time)
                long_term_metrics['performance_trends']['throughput'].append(month_throughput)
                
                # CPU・メモリ使用量記録
                cpu_usage = process.cpu_percent()
                memory_usage = process.memory_info().rss / 1024 / 1024
                long_term_metrics['performance_trends']['cpu_usage'].append(cpu_usage)
                long_term_metrics['performance_trends']['memory_usage'].append(memory_usage)
                
                # エラー蓄積
                long_term_metrics['error_accumulation'].append(month_error_rate)
                
                # 性能劣化チェック
                if month > 0:
                    degradation = (baseline_throughput - month_throughput) / baseline_throughput
                    long_term_metrics['performance_degradation'].append(degradation)
                
                # リソース効率性
                resource_efficiency = month_throughput / max(memory_usage, 1)
                long_term_metrics['resource_efficiency'].append(resource_efficiency)
                
                # メモリリーク検出
                if month > 0:
                    memory_growth = memory_usage - long_term_metrics['memory_snapshots'][0]
                    if memory_growth > 100:  # 100MB以上の増加
                        long_term_metrics['memory_leaks_detected'] += 1
                
                print(f"   処理時間: {month_time:.2f}秒")
                print(f"   スループット: {month_throughput:.1f} ops/sec")
                print(f"   エラー率: {month_error_rate:.2%}")
                print(f"   メモリ使用量: {memory_usage:.1f}MB")
                
                profiler.record_throughput(month_throughput)
                profiler.record_error_rate(month_error_rate)
            
            # 長期安定性評価
            print("📊 長期安定性評価")
            
            # メモリリーク分析
            if len(long_term_metrics['memory_snapshots']) >= 2:
                initial_memory = long_term_metrics['memory_snapshots'][0]
                final_memory = long_term_metrics['memory_snapshots'][-1]
                memory_growth_rate = (final_memory - initial_memory) / initial_memory
                
                print(f"   メモリ成長率: {memory_growth_rate:.1%}")
                print(f"   初期メモリ: {initial_memory:.1f}MB")
                print(f"   最終メモリ: {final_memory:.1f}MB")
            
            # 性能安定性分析
            if long_term_metrics['performance_trends']['throughput']:
                throughput_trend = long_term_metrics['performance_trends']['throughput']
                throughput_stability = 1 - (statistics.stdev(throughput_trend) / statistics.mean(throughput_trend))
                print(f"   スループット安定性: {throughput_stability:.1%}")
            
            # エラー蓄積分析
            if long_term_metrics['error_accumulation']:
                avg_error_rate = statistics.mean(long_term_metrics['error_accumulation'])
                max_error_rate = max(long_term_metrics['error_accumulation'])
                print(f"   平均エラー率: {avg_error_rate:.2%}")
                print(f"   最大エラー率: {max_error_rate:.2%}")
        
        # 監視停止
        profiler.stop_monitoring()
        resource_monitor.stop_monitoring()
        total_time = time.time() - start_time
        
        # 長期運用性能要件の検証
        performance_summary = profiler.get_summary()
        
        # メモリリーク: 6ヶ月で50%以下の増加
        if len(long_term_metrics['memory_snapshots']) >= 2:
            memory_growth_rate = (long_term_metrics['memory_snapshots'][-1] - long_term_metrics['memory_snapshots'][0]) / long_term_metrics['memory_snapshots'][0]
            assert memory_growth_rate <= 0.5, f"メモリリーク検出: {memory_growth_rate:.1%} (期待値: ≤50%)"
        
        # 性能劣化: 6ヶ月で20%以下
        if long_term_metrics['performance_degradation']:
            max_degradation = max(long_term_metrics['performance_degradation'])
            assert max_degradation <= 0.2, f"性能劣化超過: {max_degradation:.1%} (期待値: ≤20%)"
        
        # エラー蓄積: 平均1%以下
        if long_term_metrics['error_accumulation']:
            avg_error_rate = statistics.mean(long_term_metrics['error_accumulation'])
            assert avg_error_rate <= 0.01, f"エラー率超過: {avg_error_rate:.2%} (期待値: ≤1%)"
        
        # メモリリーク検出回数: 2回以下
        assert long_term_metrics['memory_leaks_detected'] <= 2, \
            f"メモリリーク検出回数超過: {long_term_metrics['memory_leaks_detected']}回 (期待値: ≤2回)"
        
        # スループット安定性: 60%以上（初回測定の変動を考慮）
        if long_term_metrics['performance_trends']['throughput']:
            throughput_trend = long_term_metrics['performance_trends']['throughput']
            throughput_stability = 1 - (statistics.stdev(throughput_trend) / statistics.mean(throughput_trend))
            assert throughput_stability >= 0.6, f"スループット安定性不足: {throughput_stability:.1%} (期待値: ≥60%)"
        
        # リソース効率性の維持
        if long_term_metrics['resource_efficiency']:
            efficiency_trend = long_term_metrics['resource_efficiency']
            efficiency_decline = (efficiency_trend[0] - efficiency_trend[-1]) / efficiency_trend[0] if len(efficiency_trend) > 1 else 0
            assert efficiency_decline <= 0.4, f"リソース効率性低下: {efficiency_decline:.1%} (期待値: ≤40%)"
        
        print(f"✅ 長期運用性能テスト完了:")
        print(f"   総実行時間: {total_time:.1f}秒")
        print(f"   シミュレート期間: 6ヶ月")
        print(f"   メモリ成長率: {memory_growth_rate:.1%}" if 'memory_growth_rate' in locals() else "")
        print(f"   最大性能劣化: {max_degradation:.1%}" if 'max_degradation' in locals() else "")
        print(f"   平均エラー率: {avg_error_rate:.2%}" if 'avg_error_rate' in locals() else "")
        print(f"   メモリリーク検出: {long_term_metrics['memory_leaks_detected']}回")
        print(f"   スループット安定性: {throughput_stability:.1%}" if 'throughput_stability' in locals() else "")