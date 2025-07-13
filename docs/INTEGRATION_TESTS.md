# RecRadiko 結合テスト設計書

## 概要

RecRadikoプロジェクトの結合テスト（Integration Tests）設計書です。単体テスト（Unit Tests）が各モジュールの機能を個別にテストするのに対し、結合テストは複数のモジュール間の相互作用とデータフローを検証します。

## 🚀 テスト実施方法

### 📋 前提条件
- Python 3.8以上がインストール済み
- 必要な依存関係が全てインストール済み（`pip install -r requirements.txt`）
- FFmpegがシステムに正しくインストールされている
- テスト用のダミーデータファイルが準備済み

### 🔧 基本テスト実行

#### 結合テスト実行
```bash
# 全結合テスト実行（推奨）
python -m pytest tests/integration/ -v

# 成功例：
# tests/integration/test_end_to_end_recording.py::test_immediate_recording_workflow PASSED
# tests/integration/test_scheduling_integration.py::test_schedule_execution_workflow PASSED
# tests/integration/test_cli_integration.py::test_cli_daemon_integration PASSED
# tests/integration/test_error_handling_integration.py::test_error_propagation_flow PASSED
# tests/integration/test_file_management_integration.py::test_recording_file_integration PASSED
# ========================= 25 passed in 3.45s =========================
```

#### カテゴリ別テスト実行
```bash
# エンドツーエンド録音テスト
python -m pytest tests/integration/test_end_to_end_recording.py -v

# スケジューリング結合テスト
python -m pytest tests/integration/test_scheduling_integration.py -v

# CLI統合テスト
python -m pytest tests/integration/test_cli_integration.py -v

# エラーハンドリング結合テスト
python -m pytest tests/integration/test_error_handling_integration.py -v

# ファイル管理結合テスト
python -m pytest tests/integration/test_file_management_integration.py -v
```

### 🎯 ログ出力制御

#### 統一ログ設定の活用
```bash
# テスト時は自動的にコンソール出力が有効化
python -m pytest tests/integration/ -v
# → 結合テストの詳細なログが表示されます

# コンソール出力を無効化（高速実行）
RECRADIKO_CONSOLE_OUTPUT=false python -m pytest tests/integration/ -v

# デバッグレベルのログ出力（詳細な内部動作確認）
RECRADIKO_LOG_LEVEL=DEBUG python -m pytest tests/integration/ -v -s

# カスタムログファイル使用
RECRADIKO_LOG_FILE=integration_test.log python -m pytest tests/integration/ -v
```

### 📊 高度なテスト実行オプション

#### 並列実行・高速化
```bash
# 並列テスト実行（CPU数に応じて自動調整）
python -m pytest tests/integration/ -n auto -v

# 特定数の並列実行
python -m pytest tests/integration/ -n 2 -v

# 失敗時に即座停止
python -m pytest tests/integration/ -x -v

# 詳細な進捗表示
python -m pytest tests/integration/ -v --tb=short
```

#### カバレッジ・レポート生成
```bash
# HTMLカバレッジレポート生成
python -m pytest tests/integration/ --cov=src --cov-report=html -v

# XMLカバレッジレポート生成
python -m pytest tests/integration/ --cov=src --cov-report=xml -v

# JUnitXMLレポート生成
python -m pytest tests/integration/ --junitxml=reports/integration_junit.xml -v
```

### 🔍 トラブルシューティング

#### 環境確認
```bash
# テスト環境の確認
python -c "from src.logging_config import is_test_mode, is_console_output_enabled; print(f'Test mode: {is_test_mode()}, Console output: {is_console_output_enabled()}')"

# FFmpegの確認
which ffmpeg
ffmpeg -version

# 依存関係の確認
python -c "import requests, m3u8, sqlite3; print('Dependencies OK')"
```

#### よくある問題と解決法
```bash
# 1. モジュールインポートエラー
export PYTHONPATH=$PYTHONPATH:$(pwd)
python -m pytest tests/integration/ -v

# 2. データベースファイルの競合
rm -f test_*.db
python -m pytest tests/integration/ -v

# 3. 一時ファイルの残存
rm -rf /tmp/recradiko_test_*
python -m pytest tests/integration/ -v

# 4. ポート競合（デーモンテスト）
sudo lsof -i :8080  # 使用中のポート確認
```

### 🎯 推奨実行パターン

#### 開発時（日常）
```bash
# 高速結合テスト実行
python -m pytest tests/integration/ -x --tb=short -v
```

#### モジュール修正後（重要な変更）
```bash
# 関連する結合テストのみ実行
python -m pytest tests/integration/test_end_to_end_recording.py tests/integration/test_scheduling_integration.py -v
```

#### コミット前（品質確認）
```bash
# 全テスト実行（単体+結合）
python -m pytest tests/ tests/integration/ -v
```

#### リリース前（完全検証）
```bash
# 完全テスト実行（単体+結合+E2E）
python -m pytest tests/ tests/integration/ tests/e2e/ --cov=src --cov-report=html -v
```

### 📈 テスト結果の解釈

#### 成功パターン
```
========================= 25 passed in 3.45s =========================
```
→ 全25個の結合テストが成功

#### 部分成功パターン
```
================== 20 passed, 5 failed in 4.12s ==================
```
→ 一部のテストが失敗、詳細なエラー情報を確認する必要あり

#### 失敗パターン
```
========================= FAILURES =========================
_____________________ test_immediate_recording_workflow ______________________
AssertionError: Expected recording to complete successfully
```
→ 特定のワークフローが失敗、モジュール間の統合に問題あり

### 🔧 テスト設定のカスタマイズ

#### 環境変数による制御
```bash
# テストデータディレクトリを指定
export RECRADIKO_TEST_DATA_DIR=/tmp/test_data

# テストタイムアウト設定
export RECRADIKO_TEST_TIMEOUT=30

# モック使用の制御
export RECRADIKO_USE_MOCK=true
```

#### 設定ファイルによる制御
```bash
# テスト用設定ファイル使用
python -m pytest tests/integration/ -v --config=tests/integration/test_config.json
```

## 目的

1. **モジュール間相互作用の検証**: 複数モジュールが正しく連携動作することを確認
2. **エンドツーエンドワークフローの検証**: 実際のユーザーシナリオでの動作確認
3. **データフローの整合性確認**: モジュール間でのデータ受け渡しの正確性検証
4. **エラー伝播の検証**: エラーが適切にモジュール間で伝播・処理されることを確認
5. **リアルタイム処理の検証**: スケジューリング、並行処理の動作確認

## モジュール依存関係分析

### 依存関係マップ

```
                    ┌─────────────┐
                    │   CLI.py    │
                    │(Orchestrator)│
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Daemon.py  │
                    │(Background) │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
    ┌───▼───┐         ┌────▼────┐        ┌───▼────┐
    │Auth.py│◄────────┤Recording│────────┤Schedule│
    │       │         │Manager  │        │Manager │
    └───┬───┘         └────┬────┘        └───┬────┘
        │                  │                 │
    ┌───▼────┐        ┌────▼──────┐     ┌───▼──────┐
    │Program │        │Streaming  │     │File      │
    │Info    │        │Manager    │     │Manager   │
    └────────┘        └───────────┘     └──────────┘
                           │
                      ┌────▼──────┐
                      │Error      │
                      │Handler    │
                      └───────────┘
```

## 結合テストカテゴリ

### 1. エンドツーエンド録音テスト（E2E Recording Tests）

#### 1.1 即座録音ワークフロー
```python
class TestEndToEndRecording:
    def test_immediate_recording_workflow(self):
        """CLI → 認証 → ストリーミング → 録音 → ファイル管理の完全フロー"""
        # テストシナリオ:
        # 1. CLI経由で即座録音コマンド実行
        # 2. 認証システムでRadikoトークン取得
        # 3. ストリーミング管理でHLSストリーム取得
        # 4. 録音管理でFFmpeg録音実行
        # 5. ファイル管理でメタデータ付きファイル保存
        # 検証項目:
        # - 各ステップの成功
        # - データの正確な受け渡し
        # - 最終ファイルの完整性
```

#### 1.2 番組情報統合録音
```python
    def test_program_info_integration_recording(self):
        """認証 → 番組情報 → 録音の統合フロー"""
        # テストシナリオ:
        # 1. 認証完了後に番組情報取得
        # 2. 番組メタデータと録音設定の統合
        # 3. 番組情報を含むファイル作成
        # 検証項目:
        # - 番組メタデータの正確性
        # - ファイル名の自動生成
        # - ID3タグの適切な設定
```

#### 1.3 録音とファイル管理連携
```python
    def test_recording_file_management_integration(self):
        """録音管理 → ファイル管理の統合フロー"""
        # テストシナリオ:
        # 1. 録音完了後のファイル自動登録
        # 2. メタデータ自動抽出と保存
        # 3. ストレージ容量管理の動作
        # 検証項目:
        # - ファイルメタデータの正確性
        # - 自動クリーンアップの動作
        # - ストレージ統計の更新
```

### 2. スケジューリング結合テスト（Scheduling Integration Tests）

#### 2.1 スケジュール実行ワークフロー
```python
class TestSchedulingIntegration:
    def test_schedule_execution_workflow(self):
        """スケジューラ → 録音管理 → ファイル管理の自動実行フロー"""
        # テストシナリオ:
        # 1. 予約スケジュールの自動実行
        # 2. 録音ジョブの自動作成・実行
        # 3. 完了後のスケジュール状態更新
        # 検証項目:
        # - 正確な時刻での実行開始
        # - 録音ジョブの正しい設定
        # - スケジュール統計の更新
```

#### 2.2 競合検出と解決
```python
    def test_schedule_conflict_resolution(self):
        """スケジュール競合の検出と解決メカニズム"""
        # テストシナリオ:
        # 1. 重複する時間帯のスケジュール作成
        # 2. 競合検出アルゴリズムの動作
        # 3. 競合解決ストラテジーの実行
        # 検証項目:
        # - 競合の正確な検出
        # - 適切な警告・エラー処理
        # - ユーザーへの通知
```

#### 2.3 繰り返しスケジュール管理
```python
    def test_recurring_schedule_management(self):
        """繰り返しスケジュールの長期実行と管理"""
        # テストシナリオ:
        # 1. 日次・週次・月次スケジュールの設定
        # 2. 複数回の自動実行
        # 3. スケジュール履歴の管理
        # 検証項目:
        # - 正確な繰り返し実行
        # - 実行履歴の記録
        # - 終了条件の適切な処理
```

### 3. デーモンモード統合テスト（Daemon Integration Tests）

#### 3.1 デーモン初期化テスト
```python
class TestDaemonIntegration:
    def test_daemon_component_initialization(self):
        """デーモンによる全コンポーネントの正しい初期化"""
        # テストシナリオ:
        # 1. デーモン起動時の各モジュール初期化
        # 2. 依存関係の正しい順序での初期化
        # 3. 初期化エラー時の適切な処理
        # 検証項目:
        # - 全モジュールの正常初期化
        # - 依存関係の適切な解決
        # - エラー時の安全な停止
```

#### 3.2 ヘルスモニタリング統合
```python
    def test_daemon_health_monitoring_integration(self):
        """デーモンによる全モジュールのヘルス監視"""
        # テストシナリオ:
        # 1. 各モジュールの状態監視
        # 2. 異常検出時の通知
        # 3. 自動復旧メカニズムの動作
        # 検証項目:
        # - 正確な状態監視
        # - 適切な閾値での警告
        # - 自動復旧の成功
```

### 4. CLI統合テスト（CLI Integration Tests）

#### 4.1 CLIコマンド統合実行
```python
class TestCLIIntegration:
    def test_cli_record_command_integration(self):
        """CLIレコードコマンドの完全統合テスト"""
        # テストシナリオ:
        # 1. CLI引数解析から録音完了まで
        # 2. エラー時の適切な終了コード
        # 3. 進捗表示の正確性
        # 検証項目:
        # - コマンド実行の成功
        # - 適切な出力とログ
        # - エラー処理の正確性
```

#### 4.2 設定管理統合
```python
    def test_cli_config_management_integration(self):
        """CLI設定変更の全モジュールへの反映"""
        # テストシナリオ:
        # 1. CLI経由での設定変更
        # 2. 各モジュールでの設定反映
        # 3. 設定の永続化と復元
        # 検証項目:
        # - 設定変更の即座反映
        # - 設定の一貫性維持
        # - 再起動後の設定復元
```

### 5. エラーハンドリング統合テスト（Error Handling Integration Tests）

#### 5.1 エラー伝播テスト
```python
class TestErrorHandlingIntegration:
    def test_network_error_propagation(self):
        """ネットワークエラーのモジュール間伝播"""
        # テストシナリオ:
        # 1. ネットワーク障害のシミュレート
        # 2. エラーの上位モジュールへの伝播
        # 3. ユーザーへの適切な通知
        # 検証項目:
        # - エラーの正確な伝播
        # - 適切なエラーメッセージ
        # - 復旧可能性の判断
```

#### 5.2 認証エラー統合処理
```python
    def test_authentication_error_integration(self):
        """認証エラーの依存モジュールでの処理"""
        # テストシナリオ:
        # 1. 認証失敗の発生
        # 2. 依存モジュールでの処理停止
        # 3. 再認証による復旧
        # 検証項目:
        # - 認証エラーの正確な検出
        # - 依存処理の安全な停止
        # - 自動再試行メカニズム
```

### 6. データ永続化統合テスト（Data Persistence Integration Tests）

#### 6.1 データベース一貫性テスト
```python
class TestDataPersistenceIntegration:
    def test_database_consistency_across_modules(self):
        """複数モジュール間でのデータベース整合性"""
        # テストシナリオ:
        # 1. 複数モジュールでの同時データベースアクセス
        # 2. トランザクション処理の検証
        # 3. データ競合状態の処理
        # 検証項目:
        # - データの整合性維持
        # - 同時アクセスの安全性
        # - デッドロックの回避
```

### 7. 並行処理統合テスト（Concurrency Integration Tests）

#### 7.1 マルチレコーディング
```python
class TestConcurrencyIntegration:
    def test_concurrent_recording_jobs(self):
        """複数録音ジョブの同時実行"""
        # テストシナリオ:
        # 1. 複数放送局の同時録音
        # 2. リソース競合の管理
        # 3. 品質保証の維持
        # 検証項目:
        # - 同時録音の品質
        # - リソース使用量の管理
        # - エラー発生時の影響範囲
```

## 実装計画

### フェーズ1: 基盤結合テスト実装（最優先）
- エンドツーエンド録音テストの実装
- CLIコマンド統合テストの実装
- 基本的なエラーハンドリング統合テストの実装

### フェーズ2: 高度結合テスト実装（高優先）
- スケジューリング統合テストの実装
- デーモンモード統合テストの実装
- データ永続化統合テストの実装

### フェーズ3: 特殊ケース結合テスト実装（中優先）
- 並行処理統合テストの実装
- パフォーマンス統合テストの実装
- セキュリティ統合テストの実装

## テスト実行環境

### 必要なテストデータ
- モックRadikoサーバー環境
- サンプル番組データ
- テスト用ストリーミングコンテンツ
- 様々なエラー条件のシミュレート環境

### テスト実行コマンド
```bash
# 結合テスト実行
python -m pytest tests/integration/ -v

# 特定カテゴリの結合テスト実行
python -m pytest tests/integration/test_e2e_recording.py -v

# 結合テストカバレッジレポート
python -m pytest tests/integration/ --cov=src --cov-report=html
```

## 成功基準

### テスト成功率
- **目標**: 結合テスト成功率95%以上
- **最低基準**: 結合テスト成功率90%以上

### カバレッジ
- **目標**: モジュール間インタラクション90%以上
- **最低基準**: 主要ワークフロー85%以上

### パフォーマンス
- **目標**: 結合テスト実行時間10分以内
- **最低基準**: 結合テスト実行時間15分以内

## 注意事項

1. **テスト環境の独立性**: 結合テストは実際のRadikoサービスに影響を与えない独立した環境で実行
2. **データのクリーンアップ**: 各テスト後の適切なデータクリーンアップの実施
3. **リソース管理**: テスト実行時のシステムリソース使用量の監視
4. **継続的統合**: CI/CDパイプラインでの自動結合テスト実行の設定

このドキュメントは結合テスト実装の進行に合わせて継続的に更新されます。