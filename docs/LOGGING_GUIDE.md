# RecRadiko ログシステム設定ガイド

## 概要

RecRadikoは統一ログ設定システムを採用しており、開発・テスト・本番環境で最適化されたログ出力を提供します。

## 🔧 ログ設定の特徴

### 自動環境検出
- **テスト環境**: 自動検出によりコンソール出力を有効化
- **本番環境**: コンソール出力を無効化、ファイルログのみ出力
- **開発環境**: 環境変数による柔軟な制御

### 統一設定
- 全モジュールで同じログ設定を使用
- 重複したログ設定コードを排除
- 一元的なログレベル・出力先制御

## 🎯 動作モード

### 通常使用時
```bash
# コンソール出力なし、ファイルログのみ
python RecRadiko.py record TBS 5
```

- **コンソール出力**: なし
- **ファイル出力**: `recradiko.log`
- **ログレベル**: INFO
- **用途**: 本番環境、バックグラウンド実行

### テスト実行時
```bash
# コンソール出力あり、詳細ログ表示
python -m pytest tests/ -v
```

- **コンソール出力**: あり
- **ファイル出力**: `recradiko.log`
- **ログレベル**: INFO
- **用途**: テスト実行、デバッグ

## 🛠️ 環境変数による制御

### 基本制御
```bash
# コンソール出力を強制有効
export RECRADIKO_CONSOLE_OUTPUT=true

# コンソール出力を強制無効
export RECRADIKO_CONSOLE_OUTPUT=false

# ログレベルを設定
export RECRADIKO_LOG_LEVEL=DEBUG

# ログファイルを指定
export RECRADIKO_LOG_FILE=custom.log
```

### 高度な制御
```bash
# テストモードを手動設定
export RECRADIKO_TEST_MODE=true

# ログローテーションサイズを設定（MB単位）
export RECRADIKO_MAX_LOG_SIZE=50

# ログディレクトリを設定
export RECRADIKO_LOG_DIR=/var/log/recradiko
```

## 📊 テスト実行とログ

### 基本テスト実行
```bash
# 単体テスト（コンソール出力自動有効）
python -m pytest tests/ -v

# 結合テスト（コンソール出力自動有効）
python -m pytest tests/integration/ -v

# E2Eテスト（コンソール出力自動有効）
python -m pytest tests/e2e/ -v
```

### ログ制御付きテスト実行
```bash
# 詳細ログ付きテスト実行
RECRADIKO_LOG_LEVEL=DEBUG python -m pytest tests/ -v -s

# ログ無効化テスト実行（高速化）
RECRADIKO_CONSOLE_OUTPUT=false python -m pytest tests/ -v

# カスタムログファイル付きテスト実行
RECRADIKO_LOG_FILE=test_run.log python -m pytest tests/ -v
```

## 🔍 ログレベル設定

### 利用可能なログレベル
- **DEBUG**: 詳細なデバッグ情報
- **INFO**: 一般的な情報（デフォルト）
- **WARNING**: 警告メッセージ
- **ERROR**: エラーメッセージ
- **CRITICAL**: 致命的なエラー

### ログレベル設定例
```bash
# 開発時（詳細ログ）
export RECRADIKO_LOG_LEVEL=DEBUG

# 本番時（エラーのみ）
export RECRADIKO_LOG_LEVEL=ERROR

# テスト時（情報レベル）
export RECRADIKO_LOG_LEVEL=INFO
```

## 🗂️ ログファイル管理

### ログローテーション
- **最大ファイルサイズ**: 10MB（デフォルト）
- **世代管理**: 5世代保存
- **自動ローテーション**: サイズ超過時に自動実行

### ログファイル設定
```bash
# ログファイル場所の確認
ls -la recradiko.log*

# ログファイル内容の確認
tail -f recradiko.log

# ログファイル統計
wc -l recradiko.log
```

## 📋 開発者向け設定

### コード内でのログ使用
```python
from src.logging_config import get_logger

# ロガーの取得
logger = get_logger(__name__)

# ログ出力
logger.info("情報メッセージ")
logger.warning("警告メッセージ")
logger.error("エラーメッセージ")
logger.debug("デバッグメッセージ")
```

### 新しいモジュールでのログ設定
```python
from src.logging_config import get_logger, setup_logging

class NewModule:
    def __init__(self):
        # ログ設定（必要に応じて）
        setup_logging()
        
        # ロガーの取得
        self.logger = get_logger(__name__)
        
    def some_method(self):
        self.logger.info("メソッド実行")
```

## 🔧 トラブルシューティング

### よくある問題と解決法

#### 1. ログが出力されない
```bash
# 環境変数を確認
python -c "from src.logging_config import is_test_mode, is_console_output_enabled; print(f'Test mode: {is_test_mode()}, Console output: {is_console_output_enabled()}')"

# 強制的にコンソール出力を有効化
export RECRADIKO_CONSOLE_OUTPUT=true
python RecRadiko.py --help
```

#### 2. ログレベルが期待通りでない
```bash
# ログレベルを明示的に設定
export RECRADIKO_LOG_LEVEL=DEBUG

# 設定を確認
python -c "import logging; from src.logging_config import get_logger; logger = get_logger('test'); logger.info('Test message')"
```

#### 3. テスト時にログが多すぎる
```bash
# ログレベルを上げる
RECRADIKO_LOG_LEVEL=WARNING python -m pytest tests/ -v

# コンソール出力を無効化
RECRADIKO_CONSOLE_OUTPUT=false python -m pytest tests/ -v
```

#### 4. ログファイルが作成されない
```bash
# ログディレクトリの権限を確認
ls -ld .
mkdir -p logs
chmod 755 logs

# ログファイルパスを明示的に設定
export RECRADIKO_LOG_FILE=./logs/recradiko.log
```

## 🎯 最適化のヒント

### 本番環境での推奨設定
```bash
# 本番環境用環境変数設定
export RECRADIKO_CONSOLE_OUTPUT=false
export RECRADIKO_LOG_LEVEL=INFO
export RECRADIKO_LOG_FILE=/var/log/recradiko/recradiko.log
export RECRADIKO_MAX_LOG_SIZE=100  # 100MB
```

### 開発環境での推奨設定
```bash
# 開発環境用環境変数設定
export RECRADIKO_CONSOLE_OUTPUT=true
export RECRADIKO_LOG_LEVEL=DEBUG
export RECRADIKO_LOG_FILE=./dev_recradiko.log
```

### CI/CD環境での推奨設定
```bash
# CI/CD環境用環境変数設定
export RECRADIKO_CONSOLE_OUTPUT=false
export RECRADIKO_LOG_LEVEL=WARNING
export RECRADIKO_LOG_FILE=./ci_recradiko.log
```

## 📈 ログ統計とモニタリング

### ログ統計の確認
```bash
# ログレベル別統計
grep -c "INFO" recradiko.log
grep -c "WARNING" recradiko.log
grep -c "ERROR" recradiko.log

# 時間別統計
grep "$(date '+%Y-%m-%d')" recradiko.log | wc -l
```

### リアルタイムモニタリング
```bash
# ログのリアルタイム監視
tail -f recradiko.log

# エラーログのみ監視
tail -f recradiko.log | grep "ERROR"

# 特定モジュールのログ監視
tail -f recradiko.log | grep "auth"
```

## 🔄 設定の検証

### 設定状態の確認
```bash
# 現在の設定を確認
python -c "
from src.logging_config import is_test_mode, is_console_output_enabled
import os
print(f'Test mode: {is_test_mode()}')
print(f'Console output: {is_console_output_enabled()}')
print(f'Log level: {os.environ.get(\"RECRADIKO_LOG_LEVEL\", \"INFO\")}')
print(f'Log file: {os.environ.get(\"RECRADIKO_LOG_FILE\", \"recradiko.log\")}')
"
```

### 設定の動作テスト
```bash
# 各設定での動作確認
RECRADIKO_CONSOLE_OUTPUT=true python -c "from src.logging_config import get_logger; get_logger('test').info('Console test')"
RECRADIKO_CONSOLE_OUTPUT=false python -c "from src.logging_config import get_logger; get_logger('test').info('File test')"
```

この統一ログ設定システムにより、RecRadikoは開発・テスト・本番環境で最適化されたログ出力を提供し、開発者にとって使いやすく、本番環境では効率的なログ管理を実現しています。