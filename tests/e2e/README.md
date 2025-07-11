# 📋 RecRadiko E2Eテストフレームワーク

> **目的**: RecRadikoの完全なエンドツーエンドテストによる品質保証

## 🎯 概要

このE2Eテストフレームワークは、RecRadikoの実際のユーザーワークフローを完全にシミュレートし、プロダクション環境での信頼性を確保します。

### 📊 現在の状況
- **既存テスト**: 240個（単体テスト215個 + 結合テスト25個）が100%成功
- **従来E2Eテスト**: 50個（A1-A4, B1-B3, C1-C3, D1-D3）が100%成功
- **実際のAPIテスト**: 16個（R1-R10, C1-C3）- 実際のRadiko API使用
- **合計**: 306個のテストが完全成功
- **品質目標**: 99.9%稼働率、MTBF >720時間、MTTR <5分

## 🚀 クイックスタート

### 🔧 前提条件

```bash
# 必要なPythonパッケージ
pip install pytest pytest-xdist pytest-timeout pytest-html pytest-cov psutil

# FFmpegのインストール（macOS）
brew install ffmpeg

# Dockerの準備（オプション）
docker --version
docker-compose --version
```

### ⚡ 基本的な実行

```bash
# 従来のE2Eテスト実行（モックAPI使用）
./tests/e2e/scripts/run_e2e_tests.sh framework

# 実際のRadiko APIテスト実行
./tests/e2e/scripts/run_real_api_tests.sh

# 詳細ログ付きでフレームワークテスト
./tests/e2e/scripts/run_e2e_tests.sh framework -v

# Docker環境でのテスト実行
./tests/e2e/scripts/run_e2e_tests.sh framework --docker

# リソース監視付きでテスト実行
./tests/e2e/scripts/run_e2e_tests.sh framework --monitor
```

### 📊 テストレポート

実行後、以下の場所にレポートが生成されます：

```
reports/e2e/YYYYMMDD_HHMMSS/
├── report.html          # メインテストレポート
├── coverage/            # カバレッジレポート
├── junit.xml           # JUnit形式レポート
├── monitoring.json     # リソース監視データ
└── logs/               # 詳細ログ
```

## 🏗️ フレームワーク構成

### 📁 ディレクトリ構造

```
tests/e2e/
├── __init__.py              # E2Eテストモジュール
├── conftest.py              # pytest設定・フィクスチャ
├── pytest.ini              # pytest設定ファイル
├── docker-compose.yml      # Docker環境定義
├── Dockerfile               # E2Eテスト環境
├── README.md               # このファイル
├── scripts/                # 実行スクリプト
│   └── run_e2e_tests.sh    # メイン実行スクリプト
├── test_framework.py       # フレームワーク動作確認
├── test_user_journey.py    # ユーザージャーニーテスト（A1-A4）
├── test_system_operation.py # システム稼働テスト（B1-B3）
├── test_failure_recovery.py # 障害復旧テスト（C1-C3）
├── test_performance.py    # パフォーマンステスト（D1-D3）
├── test_real_api.py        # 実際のRadiko APIテスト（R1-R10, C1-C3）
├── docker-compose.real-api.yml # 実際のAPIテスト環境
└── monitoring/             # 監視設定
    ├── prometheus.yml      # Prometheus設定
    └── grafana/           # Grafanaダッシュボード
```

### 🛠️ 主要コンポーネント

#### 1. **時間加速機能** (`TimeAccelerator`)
```python
# 24時間のテストを1時間で実行
time_accelerator.accelerated_sleep(24 * 3600)  # 実際は864秒（14.4分）
```

#### 2. **テストデータ生成** (`TestDataGenerator`)
```python
# 大規模データセット自動生成
stations = generator.generate_stations(50)           # 50放送局
programs = generator.generate_programs(stations, 30) # 30日分番組
schedules = generator.generate_schedules(stations, 5000) # 5000スケジュール
```

#### 3. **リソース監視** (`ResourceMonitor`)
```python
# CPU・メモリ・ディスク使用量の継続監視
monitor.start_monitoring(interval=1.0)
# ... テスト実行 ...
summary = monitor.get_summary()
```

#### 4. **ネットワークシミュレータ** (`NetworkSimulator`)
```python
# 様々なネットワーク状態をシミュレート
network_sim.set_poor_connection()      # 低品質接続
network_sim.set_unstable_connection()  # 不安定接続
network_sim.simulate_network_error()   # ネットワークエラー
```

## 📋 テストカテゴリ詳細

### 🎯 **Category A: ユーザージャーニーテスト**

#### A1: 新規ユーザー初回利用フロー
```python
def test_first_time_user_journey():
    """
    1. 初回起動・設定ファイル自動生成
    2. 地域設定の自動検出
    3. 認証フローの実行
    4. 放送局一覧取得
    5. 初回録音実行
    6. ファイル生成・メタデータ付与確認
    """
```

#### A2: 日常利用パターン
```python 
def test_daily_routine():
    """
    朝・昼・夜の定期録音ルーチン
    - 6:30 ニュース番組録音開始
    - 12:00 ランチタイム番組
    - 20:00 音楽番組
    - 2:00 自動クリーンアップ
    """
```

#### A3: 高品質録音・アーカイブ運用
```python
def test_audiophile_workflow():
    """
    音楽愛好家による高品質録音
    - AAC 320kbps設定
    - 長時間録音（3時間）
    - ID3タグ自動付与
    - アーカイブ管理
    """
```

#### A4: 複雑スケジュール管理
```python
def test_complex_scheduling():
    """
    複数の繰り返しパターン
    - 平日毎日（weekdays）
    - 週末のみ（weekends）
    - 月例番組（monthly）
    - カスタムパターン
    """
```

### ⚡ **Category B: システム稼働テスト**

#### B1: 24時間連続稼働
```python
@pytest.mark.slow
def test_24h_continuous_operation():
    """
    デーモンモード24時間稼働
    - 複数番組の並行録音
    - リソース使用量監視
    - メモリリーク検出
    """
```

#### B2: 大量データ処理
```python
@pytest.mark.resource_intensive
def test_large_scale_data():
    """
    大規模データでの性能確認
    - 10,000録音ファイル
    - 1TB総データ量
    - 5,000スケジュール
    """
```

#### B3: 並行処理ストレス
```python
def test_concurrent_stress():
    """
    最大並行録音での安定性
    - 8番組同時録音
    - 高品質設定（320kbps）
    - システム負荷監視
    """
```

### 🛡️ **Category C: 障害復旧テスト**

#### C1: ネットワーク障害復旧
```python
def test_network_failure_recovery():
    """
    ネットワーク障害シナリオ
    - 接続断線・復旧
    - 不安定な接続環境
    - DNS解決失敗
    - 自動リトライ検証
    """
```

#### C2: ストレージ障害復旧
```python
def test_storage_failure_recovery():
    """
    ストレージ障害シナリオ
    - ディスク容量不足
    - 書き込み権限エラー
    - ファイルシステム破損
    - 自動復旧確認
    """
```

#### C3: プロセス障害復旧
```python
def test_process_failure_recovery():
    """
    プロセス障害シナリオ
    - システム再起動
    - 異常終了
    - メモリ不足
    - 状態復元確認
    """
```

### 📊 **Category D: パフォーマンステスト**

#### D1: スケーラビリティ
```python
def test_scalability():
    """
    スケーラビリティ測定
    - スケジュール数: 10→5,000
    - ファイル数: 100→50,000
    - 応答時間測定
    """
```

#### D2: リアルタイム性能
```python
def test_realtime_performance():
    """
    リアルタイム応答性
    - 録音開始遅延 <2秒
    - ステータス更新 1秒間隔
    - 高負荷時の応答性
    """
```

#### D3: 長期運用性能
```python
def test_long_term_performance():
    """
    長期運用での性能維持
    - 6ヶ月運用シミュレート
    - 性能劣化なし確認
    - メモリ効率性
    """
```

## 🌐 実際のRadiko APIテスト

### 📋 **Category R: 実際のRadiko APIテスト**

#### R1-R10: 実際のAPI動作確認
```python
@pytest.mark.real_api
def test_real_authentication_flow():
    """実際のRadiko認証フローテスト"""
    
def test_real_station_list_retrieval():
    """実際の放送局リスト取得テスト"""
    
def test_real_short_recording():
    """実際の短時間録音テスト（30秒）"""
```

#### C1-C3: API契約テスト
```python
@pytest.mark.contract
def test_station_list_xml_structure():
    """放送局リストXML構造の契約テスト"""
    
def test_program_list_xml_structure():
    """番組表XML構造の契約テスト"""
    
def test_streaming_url_format():
    """ストリーミングURL形式の契約テスト"""
```

### 🚀 実際のAPIテスト実行

```bash
# 実際のAPIテストのみ実行
python -m pytest tests/e2e/test_real_api.py -v

# 特定のテストカテゴリ
python -m pytest -m "real_api" -v      # 実際のAPIテスト
python -m pytest -m "contract" -v      # API契約テスト

# 専用スクリプトでの実行
./tests/e2e/scripts/run_real_api_tests.sh

# Docker環境での実行
docker-compose -f docker-compose.real-api.yml up
```

### ⚠️ 注意事項

実際のRadiko APIテストは以下の点にご注意ください：

- **インターネット接続**: 実際のRadiko APIアクセスが必要
- **API利用規約**: Radiko利用規約を遵守してください
- **レート制限**: APIレート制限に注意
- **実際の録音**: 短時間ですが実際の音声データをダウンロード

#### CI環境での実行制御

```bash
# CI環境では実際のAPIテストを無効化
export SKIP_REAL_API_TESTS=1
python -m pytest tests/e2e/test_real_api.py -v
```

## 🔧 設定とカスタマイズ

### ⚙️ pytest.ini 設定

```ini
[tool:pytest]
testpaths = tests/e2e
markers =
    e2e: エンドツーエンドテスト
    user_journey: ユーザージャーニーテスト
    system_operation: システム稼働テスト
    failure_recovery: 障害復旧テスト
    performance: パフォーマンステスト
    slow: 長時間実行テスト
    resource_intensive: リソース集約テスト

addopts = 
    --timeout=3600
    --cov=src
    --html=reports/report.html
```

### 🐳 Docker環境

```bash
# Docker環境での実行
docker-compose -f tests/e2e/docker-compose.yml up

# サービス構成
- recradiko-e2e: メインテスト実行環境
- mock-radiko-api: Radiko APIモック
- test-monitor: Prometheus監視
- test-dashboard: Grafanaダッシュボード
- network-simulator: ネットワーク障害シミュレータ
```

### 📊 監視・メトリクス

#### Prometheus メトリクス
- CPU使用率、メモリ使用量
- ディスクI/O、ネットワークI/O
- テスト実行時間、成功率

#### Grafana ダッシュボード
- リアルタイム監視
- パフォーマンストレンド
- 障害発生・復旧状況

## 🎯 品質保証基準

### ✅ 成功基準

| メトリクス | 目標値 | 測定方法 |
|-----------|--------|----------|
| **稼働率** | 99.9% | 24時間テスト成功率 |
| **MTBF** | >720時間 | 障害間隔測定 |
| **MTTR** | <5分 | 復旧時間測定 |
| **応答時間** | <2秒 | 95%パーセンタイル |
| **スケーラビリティ** | 5,000スケジュール | 線形性能維持 |
| **リソース効率** | CPU <30% | 平均使用率 |

### 📈 期待効果

#### 🏆 品質向上
- プロダクション環境での信頼性確保
- ユーザー満足度の大幅向上
- バグ発生率の劇的削減

#### 🚀 開発効率化
- 新機能開発時の品質保証
- リグレッション防止
- 安心できるリリースプロセス

#### 📊 運用最適化
- キャパシティプランニング
- 障害予防の強化
- パフォーマンス特性の把握

## 🔄 開発ワークフロー

### 📅 実装スケジュール

#### Week 1: フレームワーク構築 ✅
- [x] 基盤インフラ構築
- [x] 時間加速機能
- [x] テストデータ生成
- [x] Docker環境
- [x] 監視システム

#### Week 2: ユーザージャーニーテスト（予定）
- [ ] A1: 新規ユーザーフロー
- [ ] A2: 日常利用パターン
- [ ] A3: 高品質録音運用
- [ ] A4: 複雑スケジュール管理

#### Week 3: システム稼働テスト（予定）
- [ ] B1: 24時間連続稼働
- [ ] B2: 大量データ処理
- [ ] B3: 並行処理ストレス

#### Week 4: 障害復旧テスト（予定）
- [ ] C1: ネットワーク障害復旧
- [ ] C2: ストレージ障害復旧
- [ ] C3: プロセス障害復旧

#### Week 5: パフォーマンステスト（予定）
- [ ] D1: スケーラビリティ
- [ ] D2: リアルタイム性能
- [ ] D3: 長期運用性能

### 🔧 コントリビューション

新しいE2Eテストを追加する場合：

1. **テストファイル作成**
```python
# tests/e2e/test_new_feature.py
import pytest
from .conftest import TimeAccelerator, TestDataGenerator

@pytest.mark.e2e
class TestNewFeature:
    def test_new_functionality(self, temp_environment, time_accelerator):
        # テスト実装
        pass
```

2. **マーカー追加**
```python
@pytest.mark.new_category  # pytest.iniにマーカー定義追加
def test_specific_scenario():
    pass
```

3. **実行スクリプト更新**
```bash
# scripts/run_e2e_tests.sh にカテゴリ追加
case "$TEST_CATEGORY" in
    new_category)
        python -m pytest tests/e2e/test_new_feature.py "${PYTEST_ARGS[@]}"
        ;;
esac
```

## 📞 サポート・トラブルシューティング

### 🐛 よくある問題

#### テスト実行エラー
```bash
# 依存関係確認
pip install -r requirements.txt
pytest --version

# パス設定確認
export PYTHONPATH=$(pwd)
```

#### Docker環境エラー
```bash
# Docker環境確認
docker --version
docker-compose --version

# 権限問題
sudo usermod -aG docker $USER
```

#### リソース不足
```bash
# 並列数を削減
./run_e2e_tests.sh framework -j 1

# メモリ使用量確認
free -h
```

### 📧 サポート

- **Issues**: [GitHub Issues](https://github.com/your-repo/RecRadiko/issues)
- **Documentation**: [E2E_TEST_CASES.md](../E2E_TEST_CASES.md)
- **Technical Design**: [technical_design.md](../../technical_design.md)

---

**🎉 RecRadiko E2Eテストフレームワークで、真にプロダクション対応の高品質ソフトウェアを実現！**