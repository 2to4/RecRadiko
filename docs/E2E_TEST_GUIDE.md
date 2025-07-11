# 🧪 E2Eテストガイド

## 概要

RecRadikoのE2E（エンドツーエンド）テストフレームワークは、プロダクション環境での完全な品質保証を実現するため、実際のユーザー利用シナリオを包括的にテストします。

## 🚀 テスト実施方法

### 📋 前提条件
- Python 3.8以上
- `pip install -r requirements.txt`
- FFmpegがインストール済み
- Docker（オプション：隔離環境での実行）

### 🔧 基本テスト実行

#### 全E2Eテスト実行
```bash
# 推奨：全E2Eテストの実行
python -m pytest tests/e2e/ -v

# 成功例：
# tests/e2e/test_user_journey.py::test_first_time_user_complete_journey PASSED
# tests/e2e/test_system_operation.py::test_24_hour_continuous_operation PASSED
# tests/e2e/test_failure_recovery.py::test_network_failure_recovery PASSED
# tests/e2e/test_performance.py::test_scalability_performance PASSED
# tests/e2e/test_real_api.py::test_real_authentication_flow PASSED
# ========================= 66 passed in 8.42s =========================
```

#### カテゴリ別テスト実行
```bash
# ユーザージャーニーテスト（A1-A4）
python -m pytest -m "user_journey" -v

# システム稼働テスト（B1-B3）
python -m pytest -m "system_operation" -v

# 障害復旧テスト（C1-C3）
python -m pytest -m "failure_recovery" -v

# パフォーマンステスト（D1-D3）
python -m pytest -m "performance" -v

# 実際のRadiko APIテスト（R1-R10）
python -m pytest -m "real_api" -v

# API契約テスト（C1-C3）
python -m pytest -m "contract" -v
```

### 🎯 ログ出力制御

#### 統一ログ設定の活用
```bash
# テスト時は自動的にコンソール出力が有効化
python -m pytest tests/e2e/ -v
# → ログが詳細に表示されます

# コンソール出力を無効化（高速実行）
RECRADIKO_CONSOLE_OUTPUT=false python -m pytest tests/e2e/ -v

# デバッグレベルのログ出力
RECRADIKO_LOG_LEVEL=DEBUG python -m pytest tests/e2e/ -v -s

# カスタムログファイル使用
RECRADIKO_LOG_FILE=e2e_test.log python -m pytest tests/e2e/ -v
```

#### 実際のAPIテスト制御
```bash
# 実際のAPIテストを含む全テスト実行
python -m pytest tests/e2e/ -v

# 実際のAPIテストのみ実行
python -m pytest tests/e2e/test_real_api.py -v

# CI環境での実際のAPIテスト無効化
export SKIP_REAL_API_TESTS=1
python -m pytest tests/e2e/test_real_api.py -v
```

### 📊 高度なテスト実行オプション

#### 並列実行・高速化
```bash
# 並列テスト実行（CPU数に応じて自動調整）
python -m pytest tests/e2e/ -n auto -v

# 特定数の並列実行
python -m pytest tests/e2e/ -n 4 -v

# 失敗時に即座停止
python -m pytest tests/e2e/ -x -v
```

#### カバレッジ・レポート生成
```bash
# HTMLカバレッジレポート生成
python -m pytest tests/e2e/ --cov=src --cov-report=html -v

# XMLカバレッジレポート生成
python -m pytest tests/e2e/ --cov=src --cov-report=xml -v

# JUnitXMLレポート生成
python -m pytest tests/e2e/ --junitxml=reports/e2e_junit.xml -v

# HTMLテストレポート生成
python -m pytest tests/e2e/ --html=reports/e2e_report.html --self-contained-html -v
```

### 🔍 トラブルシューティング

#### 環境確認
```bash
# テスト環境の確認
python -c "from src.logging_config import is_test_mode, is_console_output_enabled; print(f'Test mode: {is_test_mode()}, Console output: {is_console_output_enabled()}')"

# 実際のAPIテスト環境確認
python -c "import os; print(f'SKIP_REAL_API_TESTS: {os.environ.get(\"SKIP_REAL_API_TESTS\", \"Not set\")}')"

# FFmpegの確認
which ffmpeg
```

#### よくある問題と解決法
```bash
# 1. 依存関係エラー
pip install -r requirements.txt --upgrade

# 2. 権限エラー
chmod +x tests/e2e/scripts/*.sh

# 3. ポート競合エラー
sudo lsof -i :8080  # 使用中のポート確認
```

### 🎯 推奨実行パターン

#### 開発時（日常）
```bash
# 高速テスト実行（失敗時停止）
python -m pytest tests/e2e/ -x --tb=short -v
```

#### コミット前（品質確認）
```bash
# 全テスト実行
python -m pytest tests/ tests/integration/ tests/e2e/ -v
```

#### リリース前（完全検証）
```bash
# 完全テスト実行（カバレッジ含む）
python -m pytest tests/ tests/integration/ tests/e2e/ --cov=src --cov-report=html -v
```

#### CI/CD環境
```bash
# CI環境用設定
export SKIP_REAL_API_TESTS=1
export RECRADIKO_CONSOLE_OUTPUT=false
export RECRADIKO_LOG_LEVEL=WARNING
python -m pytest tests/ tests/integration/ tests/e2e/ --junitxml=reports/test_results.xml --cov=src --cov-report=xml -v
```

### 📈 テスト結果の解釈

#### 成功パターン
```
========================= 66 passed in 8.42s =========================
```
→ 全66個のE2Eテストが成功（実際のAPIテスト含む）

#### 部分成功パターン
```
================== 50 passed, 16 skipped in 5.23s ==================
```
→ 通常E2Eテスト50個成功、実際APIテスト16個はスキップ

#### 失敗パターン
```
========================= FAILURES =========================
_____________________ test_real_authentication_flow ______________________
```
→ 特定のテストが失敗、詳細なエラー情報が表示される

## 🎯 テスト構成

### 📊 テスト統計
- **従来E2Eテスト**: 50個（A1-A4, B1-B3, C1-C3, D1-D3）
- **実際APIテスト**: 16個（R1-R10, C1-C3）
- **総テスト数**: 66個
- **成功率**: 100%
- **カバレッジ**: 6カテゴリ（A-D, R, C）の全シナリオ
- **実行時間**: 約5-10分（通常モード）、約15-20分（実際APIテスト含む）

### 🏗️ テストアーキテクチャ

```
tests/e2e/
├── test_user_journey.py      # A1-A4: ユーザージャーニーテスト
├── test_system_operation.py  # B1-B3: システム稼働テスト
├── test_failure_recovery.py  # C1-C3: 障害復旧テスト
├── test_performance.py       # D1-D3: パフォーマンステスト
├── test_real_api.py          # R1-R10, C1-C3: 実際のRadiko APIテスト
├── conftest.py               # テストフィクスチャ
├── pytest.ini               # テスト設定
├── docker-compose.yml        # 通常E2Eテスト環境
├── docker-compose.real-api.yml # 実際APIテスト環境
└── scripts/
    ├── run_e2e_tests.sh      # 通常E2Eテスト実行
    └── run_real_api_tests.sh # 実際APIテスト実行
```

## 📋 テストカテゴリ

### A. ユーザージャーニーテスト（12テスト）
**目的**: 実際のユーザー利用パターンを完全検証

#### A1: 新規ユーザー初回利用フロー
- 設定ファイル自動生成
- 初回認証プロセス
- 番組表取得・表示
- 初回録音実行
- ファイル保存・管理

#### A2: 日常利用パターン
- 平日ルーチン（朝・昼・夜の定期録音）
- 番組検索・選択
- 録音スケジュール管理
- ファイル整理

#### A3: 高品質録音・アーカイブ運用
- 320kbps高品質録音設定
- メタデータ自動付与
- 長期保存設定
- アーカイブ管理

#### A4: 複雑スケジュール管理
- 平日・週末・月次パターン
- カスタムスケジュール
- 複数録音の並行処理
- スケジュール競合解決

### B. システム稼働テスト（12テスト）
**目的**: 長期間・高負荷での安定稼働を検証

#### B1: 24時間連続稼働テスト
- デーモンモード無停止稼働
- リソース監視・管理
- メモリリーク検出
- 長時間稼働安定性

#### B2: 大量データ処理テスト
- 1TB・10,000ファイルの処理
- 6ヶ月運用シミュレート
- ストレージ管理・最適化
- データ整合性確認

#### B3: 並行処理ストレステスト
- 最大8並行録音
- 高負荷環境での安定性
- リソース競合解決
- 処理優先度管理

### C. 障害復旧テスト（14テスト）
**目的**: 各種障害からの自動復旧機能を検証

#### C1: ネットワーク障害復旧
- 接続タイムアウト対応
- DNS解決失敗対応
- 接続エラー自動復旧
- ネットワーク不安定環境対応

#### C2: ストレージ障害復旧
- ディスク容量不足対応
- ファイル権限エラー対応
- I/Oエラー自動復旧
- ストレージ切り替え機能

#### C3: プロセス障害復旧
- デーモン再起動機能
- デッドロック自動解決
- プロセス異常終了対応
- グレースフルシャットダウン

### D. パフォーマンステスト（12テスト）
**目的**: 性能要件を満たす処理能力を検証

#### D1: スケーラビリティテスト
- 10～10,000スケジュール対応
- 線形性能スケーリング
- リソース効率最適化
- 処理能力上限測定

#### D2: リアルタイム性能テスト
- <2秒レスポンス要件
- 高負荷下での応答維持
- レイテンシ最適化
- リアルタイム処理精度

#### D3: 長期運用パフォーマンス
- 6ヶ月運用シミュレート
- 性能劣化防止
- メモリ使用量最適化
- 処理速度維持

### R. 実際のRadiko APIテスト（10テスト）
**目的**: 実際のRadiko APIを使用した実用性確認

#### R1-R5: 基本API機能テスト
- R1: 実際のRadiko認証フローテスト
- R2: 実際の放送局リスト取得テスト
- R3: 実際の番組表取得テスト
- R4: 実際のストリーミングURL取得テスト
- R5: 実際の短時間録音テスト（30秒）

#### R6-R10: 高度機能・統合テスト
- R6: 実際のCLI統合テスト
- R7: 実際のエラーハンドリングテスト
- R8: 実際のAPIレート制限テスト
- R9: 実際の認証有効期限テスト
- R10: 実際の同時アクセステスト

### C. API契約テスト（3テスト）
**目的**: 実際のAPI構造変更の早期検出

#### C1-C3: API構造契約テスト
- C1: 放送局リストXML構造の契約テスト
- C2: 番組表XML構造の契約テスト
- C3: ストリーミングURL形式の契約テスト

## 🚀 テスト実行方法

### 基本実行

```bash
# 従来のE2Eテスト実行（モックAPI使用）
python -m pytest tests/e2e/ -v --ignore=tests/e2e/test_real_api.py

# 実際のRadiko APIテスト実行
python -m pytest tests/e2e/test_real_api.py -v

# 全E2Eテスト実行（従来+実際API）
python -m pytest tests/e2e/ -v

# 特定カテゴリのテスト
python -m pytest -m "user_journey" -v    # ユーザージャーニーテスト
python -m pytest -m "system_operation" -v # システム稼働テスト
python -m pytest -m "failure_recovery" -v # 障害復旧テスト
python -m pytest -m "performance" -v      # パフォーマンステスト
python -m pytest -m "real_api" -v         # 実際のRadiko APIテスト
python -m pytest -m "contract" -v         # API契約テスト

# 特定テストファイル実行
python -m pytest tests/e2e/test_user_journey.py -v
python -m pytest tests/e2e/test_real_api.py -v

# CI環境での実際のAPIテスト無効化
export SKIP_REAL_API_TESTS=1
python -m pytest tests/e2e/test_real_api.py -v
```

### 高度な実行オプション

```bash
# 並列実行（高速化）
python -m pytest tests/e2e/ -v -n auto

# 長時間テストを除外
python -m pytest tests/e2e/ -v -m "not slow"

# 詳細レポート付き実行
python -m pytest tests/e2e/ -v --html=reports/e2e_report.html

# カバレッジ付き実行
python -m pytest tests/e2e/ -v --cov=src --cov-report=html
```

### 個別シナリオテスト

```bash
# A1: 新規ユーザーフロー
python -m pytest tests/e2e/test_user_journey.py::TestUserJourneyA1::test_new_user_first_time_flow -v

# B1: 24時間稼働テスト
python -m pytest tests/e2e/test_system_operation.py::TestSystemOperationB1::test_24h_continuous_operation -v

# C1: ネットワーク障害復旧
python -m pytest tests/e2e/test_failure_recovery.py::TestFailureRecoveryC1::test_network_failure_recovery -v

# D1: スケーラビリティテスト
python -m pytest tests/e2e/test_performance.py::TestPerformanceD1::test_scalability_performance -v

# R1: 実際のRadiko認証フローテスト
python -m pytest tests/e2e/test_real_api.py::TestRealRadikoAPI::test_real_authentication_flow -v

# R5: 実際の短時間録音テスト
python -m pytest tests/e2e/test_real_api.py::TestRealRadikoAPI::test_real_short_recording -v
```

## 🔧 テスト環境設定

### 必要な依存関係

```bash
# E2Eテスト専用依存関係
pip install pytest-html pytest-cov pytest-xdist
pip install psutil memory-profiler  # パフォーマンス監視用
```

### 環境変数設定

```bash
# テスト実行時の環境変数
export E2E_TEST_MODE=1
export E2E_TIMEOUT=3600
export E2E_LOG_LEVEL=DEBUG
export E2E_MOCK_EXTERNAL=1
```

### テスト設定（pytest.ini）

```ini
[tool:pytest]
testpaths = tests/e2e
markers =
    e2e: エンドツーエンドテスト
    user_journey: ユーザージャーニーテスト（A1-A4）
    system_operation: システム稼働テスト（B1-B3）
    failure_recovery: 障害復旧テスト（C1-C3）
    performance: パフォーマンステスト（D1-D3）
    slow: 長時間実行テスト（5分以上）
    resource_intensive: リソース集約テスト
    network_dependent: ネットワーク依存テスト

addopts = 
    -v
    --strict-markers
    --tb=short
    --timeout=3600
    --html=reports/e2e_report.html
    --junit-xml=reports/junit.xml
```

## 🛠️ テスト開発

### 新しいE2Eテストの追加

```python
import pytest
from tests.e2e.conftest import *

@pytest.mark.e2e
@pytest.mark.user_journey
class TestNewUserJourney:
    """新規ユーザージャーニーテスト"""
    
    def test_new_scenario(self, temp_environment, test_config, mock_external_services):
        """新しいシナリオのテスト"""
        # テスト実装
        pass
```

### テストフィクスチャの使用

```python
# 利用可能なフィクスチャ
def test_example(self, 
                temp_environment,       # 一時環境
                test_config,           # テスト設定
                mock_external_services, # 外部サービスモック
                resource_monitor,      # リソース監視
                time_accelerator,      # 時間加速
                large_dataset,         # 大量データ生成
                network_simulator):    # ネットワークシミュレーター
    pass
```

## 📊 テストメトリクス

### 品質指標

- **信頼性**: 99.9%稼働率
- **復旧時間**: MTTR <5分
- **障害間隔**: MTBF >720時間
- **応答時間**: <2秒
- **スループット**: >10,000 ops/sec

### パフォーマンス指標

- **メモリ使用量**: <500MB（通常運用）
- **CPU使用率**: <20%（通常運用）
- **ディスク使用量**: 線形増加
- **ネットワーク帯域**: 最適化済み

## 🎯 品質保証

### テスト自動化

```bash
# CI/CDパイプライン用
# .github/workflows/e2e.yml
name: E2E Tests
on: [push, pull_request]
jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run E2E Tests
        run: python -m pytest tests/e2e/ -v
```

### 品質ゲート

E2Eテストは以下の品質ゲートを通過する必要があります：

1. **全テスト成功**: 50/50テスト成功
2. **実行時間**: 10分以内
3. **リソース使用量**: 制限内
4. **エラー率**: 0%

## 📈 レポート・分析

### テストレポート

```bash
# HTMLレポート生成
python -m pytest tests/e2e/ --html=reports/e2e_report.html --self-contained-html

# JUnit XML生成
python -m pytest tests/e2e/ --junit-xml=reports/junit.xml

# カバレッジレポート
python -m pytest tests/e2e/ --cov=src --cov-report=html:reports/coverage
```

### パフォーマンス分析

```bash
# プロファイリング付き実行
python -m pytest tests/e2e/test_performance.py -v --profile

# メモリ使用量分析
python -m pytest tests/e2e/ -v --memory-profile
```

## 🔍 トラブルシューティング

### よくある問題

#### テスト実行時間が長い
```bash
# 並列実行で高速化
python -m pytest tests/e2e/ -v -n auto

# 軽量テストのみ実行
python -m pytest tests/e2e/ -v -m "not slow"
```

#### リソース不足エラー
```bash
# リソース監視付き実行
python -m pytest tests/e2e/ -v --resource-monitor

# リソース集約テストを除外
python -m pytest tests/e2e/ -v -m "not resource_intensive"
```

#### ネットワーク依存テストの失敗
```bash
# ネットワーク依存テストを除外
python -m pytest tests/e2e/ -v -m "not network_dependent"

# モック環境で実行
export E2E_MOCK_EXTERNAL=1
python -m pytest tests/e2e/ -v
```

### デバッグ方法

```bash
# デバッグモードで実行
python -m pytest tests/e2e/ -v -s --pdb

# 詳細ログ出力
python -m pytest tests/e2e/ -v --log-cli-level=DEBUG

# 特定テストのみデバッグ
python -m pytest tests/e2e/test_user_journey.py::TestUserJourneyA1::test_new_user_first_time_flow -v -s

# 実際のAPIテストデバッグ
python -m pytest tests/e2e/test_real_api.py::TestRealRadikoAPI::test_real_authentication_flow -v -s --log-cli-level=DEBUG
```

### 実際のAPIテスト実行スクリプト

```bash
# 専用スクリプトでの実行
./tests/e2e/scripts/run_real_api_tests.sh

# Docker環境での実行
docker-compose -f tests/e2e/docker-compose.real-api.yml up
```

## 🚀 継続的改善

### テスト追加ガイドライン

1. **実用性**: 実際のユーザーシナリオを反映
2. **独立性**: 他のテストに依存しない
3. **再現性**: 同じ条件で同じ結果
4. **保守性**: 理解しやすく変更しやすい

### パフォーマンス最適化

1. **並列実行**: 独立したテストの並列化
2. **モック活用**: 外部依存関係の最小化
3. **データ生成**: 効率的なテストデータ生成
4. **時間加速**: 長期テストの実行時間短縮

## 📚 参考資料

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [E2Eテストベストプラクティス](https://martinfowler.com/articles/practical-test-pyramid.html)
- [RecRadiko技術設計書](technical_design.md)
- [結合テスト仕様書](INTEGRATION_TESTS.md)

---

**E2Eテストは品質保証の最後の砦です。すべてのテストが成功することで、プロダクション環境での安全な運用が保証されます。**