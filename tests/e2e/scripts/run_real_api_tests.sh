#!/bin/bash

# 実際のRadiko APIを使用するE2Eテスト実行スクリプト
# このスクリプトは実際のRadiko APIを呼び出すため、慎重に使用してください

set -e

# スクリプトの配置場所を基準にプロジェクトルートを決定
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." &> /dev/null && pwd )"

echo "🚀 実際のRadiko APIを使用するE2Eテスト実行"
echo "📁 プロジェクトルート: $PROJECT_ROOT"
echo "📅 実行日時: $(date)"

# プロジェクトルートに移動
cd "$PROJECT_ROOT"

# 環境変数の設定
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 実行モードの確認
if [ "$1" = "--ci" ]; then
    echo "⚠️  CI環境での実行のため、実際のAPIテストはスキップされます"
    export SKIP_REAL_API_TESTS=1
    TEST_COMMAND="python -m pytest tests/e2e/test_real_api.py -v"
else
    echo "🌐 実際のRadiko APIを使用してテストを実行します"
    echo "⚠️  このテストは実際のAPIを呼び出すため、ネットワーク接続が必要です"
    echo "⚠️  API利用規約を遵守して実行してください"
    
    # 実行確認
    read -p "実行を続行しますか？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ テスト実行を中止しました"
        exit 1
    fi
    
    # 実際のAPIテストを実行
    unset SKIP_REAL_API_TESTS
    TEST_COMMAND="python -m pytest tests/e2e/test_real_api.py -v"
fi

echo "🧪 テスト実行コマンド: $TEST_COMMAND"

# ログディレクトリの作成
mkdir -p "$PROJECT_ROOT/reports"
mkdir -p "$PROJECT_ROOT/logs"

# テストの実行
echo "▶️  テスト実行開始..."
if $TEST_COMMAND; then
    echo "✅ 実際のRadiko APIテストが正常に完了しました"
    exit 0
else
    echo "❌ 実際のRadiko APIテストが失敗しました"
    exit 1
fi