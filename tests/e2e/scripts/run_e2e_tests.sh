#!/bin/bash

# E2Eテスト実行スクリプト
# Usage: ./run_e2e_tests.sh [test_category] [options]

set -e

# スクリプトのディレクトリ
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
E2E_DIR="$PROJECT_ROOT/tests/e2e"

# デフォルト設定
TEST_CATEGORY=""
TIME_ACCELERATION=100
PARALLEL_WORKERS=4
GENERATE_REPORT=true
CLEANUP_AFTER=true
VERBOSE=false

# ログ設定
LOG_DIR="$PROJECT_ROOT/logs/e2e"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/e2e_test_$(date +%Y%m%d_%H%M%S).log"

# 関数定義
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $*" | tee -a "$LOG_FILE"
}

error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $*" | tee -a "$LOG_FILE" >&2
}

usage() {
    cat << EOF
E2Eテスト実行スクリプト

Usage: $0 [OPTIONS] [TEST_CATEGORY]

TEST_CATEGORY:
    framework       フレームワーク動作確認
    user_journey    ユーザージャーニーテスト (A1-A4)
    system_operation システム稼働テスト (B1-B3)
    failure_recovery 障害復旧テスト (C1-C3)
    performance     パフォーマンステスト (D1-D3)
    live_streaming  ライブストリーミングテスト (L1-L8)
    all            全テスト実行

OPTIONS:
    -h, --help              このヘルプを表示
    -v, --verbose           詳細ログ出力
    -t, --time-acceleration TIME_FACTOR
                           時間加速倍率 (デフォルト: 100)
    -j, --parallel WORKERS  並列実行ワーカー数 (デフォルト: 4)
    --no-report            レポート生成をスキップ
    --no-cleanup           テスト後のクリーンアップをスキップ
    --docker               Docker環境で実行
    --monitor              リソース監視を有効化

例:
    $0 framework            # フレームワークテスト
    $0 user_journey -v      # ユーザージャーニーテスト（詳細ログ）
    $0 all --docker         # 全テストをDocker環境で実行
    $0 performance -t 1000  # パフォーマンステストを1000倍速で実行
EOF
}

# コマンドライン引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -t|--time-acceleration)
            TIME_ACCELERATION="$2"
            shift 2
            ;;
        -j|--parallel)
            PARALLEL_WORKERS="$2"
            shift 2
            ;;
        --no-report)
            GENERATE_REPORT=false
            shift
            ;;
        --no-cleanup)
            CLEANUP_AFTER=false
            shift
            ;;
        --docker)
            DOCKER_MODE=true
            shift
            ;;
        --monitor)
            ENABLE_MONITORING=true
            shift
            ;;
        framework|user_journey|system_operation|failure_recovery|performance|live_streaming|all)
            TEST_CATEGORY="$1"
            shift
            ;;
        *)
            error "不明なオプション: $1"
            usage
            exit 1
            ;;
    esac
done

# テストカテゴリが指定されていない場合はframeworkをデフォルト
if [[ -z "$TEST_CATEGORY" ]]; then
    TEST_CATEGORY="framework"
fi

log "E2Eテスト開始: カテゴリ=$TEST_CATEGORY"
log "設定: 時間加速=$TIME_ACCELERATION倍, 並列ワーカー=$PARALLEL_WORKERS"

# 環境変数設定
export E2E_TEST_MODE=true
export TIME_ACCELERATION="$TIME_ACCELERATION"
export LOG_LEVEL=$([ "$VERBOSE" = true ] && echo "DEBUG" || echo "INFO")
export PYTHONPATH="$PROJECT_ROOT"

# レポートディレクトリ作成
REPORT_DIR="$PROJECT_ROOT/reports/e2e/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$REPORT_DIR"

# Docker実行関数
run_docker_tests() {
    log "Docker環境でのテスト実行開始"
    
    cd "$PROJECT_ROOT"
    
    # Docker Compose環境起動
    if ! docker-compose -f tests/e2e/docker-compose.yml up -d; then
        error "Docker環境の起動に失敗"
        exit 1
    fi
    
    # テスト実行
    docker-compose -f tests/e2e/docker-compose.yml exec -T recradiko-e2e \
        python -m pytest "tests/e2e/test_$TEST_CATEGORY.py" \
        -v --tb=short \
        --html="$REPORT_DIR/docker_report.html" \
        --self-contained-html
    
    local exit_code=$?
    
    # ログ収集
    docker-compose -f tests/e2e/docker-compose.yml logs recradiko-e2e > "$REPORT_DIR/docker_logs.txt"
    
    # 環境停止
    if [[ "$CLEANUP_AFTER" = true ]]; then
        docker-compose -f tests/e2e/docker-compose.yml down -v
    fi
    
    return $exit_code
}

# ローカル実行関数
run_local_tests() {
    log "ローカル環境でのテスト実行開始"
    
    cd "$PROJECT_ROOT"
    
    # pytest引数構築
    PYTEST_ARGS=(
        -v
        --tb=short
        --timeout=3600
        --maxfail=10
    )
    
    if [[ "$GENERATE_REPORT" = true ]]; then
        PYTEST_ARGS+=(
            --html="$REPORT_DIR/report.html"
            --self-contained-html
            --junit-xml="$REPORT_DIR/junit.xml"
            --cov=src
            --cov-report=html:"$REPORT_DIR/coverage"
            --cov-report=xml:"$REPORT_DIR/coverage.xml"
        )
    fi
    
    if [[ "$PARALLEL_WORKERS" -gt 1 ]] && [[ "$TEST_CATEGORY" != "performance" ]]; then
        PYTEST_ARGS+=(-n "$PARALLEL_WORKERS" --dist worksteal)
    fi
    
    # リソース監視開始
    if [[ "$ENABLE_MONITORING" = true ]]; then
        log "リソース監視開始"
        python -c "
import time
import psutil
import json
import threading

class Monitor:
    def __init__(self):
        self.running = True
        self.data = []
    
    def collect(self):
        while self.running:
            self.data.append({
                'timestamp': time.time(),
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            })
            time.sleep(1)
    
    def stop(self):
        self.running = False
        with open('$REPORT_DIR/monitoring.json', 'w') as f:
            json.dump(self.data, f, indent=2)

monitor = Monitor()
thread = threading.Thread(target=monitor.collect, daemon=True)
thread.start()

# モニター情報をファイルに保存
with open('$REPORT_DIR/monitor.pid', 'w') as f:
    f.write(str(id(monitor)))
" &
        MONITOR_PID=$!
    fi
    
    # テスト実行
    case "$TEST_CATEGORY" in
        framework)
            python -m pytest tests/e2e/test_framework.py "${PYTEST_ARGS[@]}"
            ;;
        user_journey)
            if [[ -f "tests/e2e/test_user_journey.py" ]]; then
                python -m pytest tests/e2e/test_user_journey.py "${PYTEST_ARGS[@]}" -m user_journey
            else
                log "ユーザージャーニーテストはまだ実装されていません"
                return 0
            fi
            ;;
        system_operation)
            if [[ -f "tests/e2e/test_system_operation.py" ]]; then
                python -m pytest tests/e2e/test_system_operation.py "${PYTEST_ARGS[@]}" -m system_operation
            else
                log "システム稼働テストはまだ実装されていません"
                return 0
            fi
            ;;
        failure_recovery)
            if [[ -f "tests/e2e/test_failure_recovery.py" ]]; then
                python -m pytest tests/e2e/test_failure_recovery.py "${PYTEST_ARGS[@]}" -m failure_recovery
            else
                log "障害復旧テストはまだ実装されていません"
                return 0
            fi
            ;;
        performance)
            if [[ -f "tests/e2e/test_performance.py" ]]; then
                python -m pytest tests/e2e/test_performance.py "${PYTEST_ARGS[@]}" -m performance
            else
                log "パフォーマンステストはまだ実装されていません"
                return 0
            fi
            ;;
        live_streaming)
            if [[ -f "tests/e2e/test_live_streaming_e2e.py" ]]; then
                log "ライブストリーミングE2Eテスト実行"
                python -m pytest tests/e2e/test_live_streaming_e2e.py "${PYTEST_ARGS[@]}" -m live_streaming
            else
                log "ライブストリーミングテストが見つかりません"
                return 1
            fi
            ;;
        all)
            python -m pytest tests/e2e/ "${PYTEST_ARGS[@]}" -m "e2e"
            ;;
        *)
            error "不明なテストカテゴリ: $TEST_CATEGORY"
            return 1
            ;;
    esac
    
    local exit_code=$?
    
    # リソース監視停止
    if [[ "$ENABLE_MONITORING" = true ]] && [[ -n "$MONITOR_PID" ]]; then
        kill $MONITOR_PID 2>/dev/null || true
        log "リソース監視停止"
    fi
    
    return $exit_code
}

# メイン実行
main() {
    # 事前チェック
    if [[ ! -f "$PROJECT_ROOT/src/__init__.py" ]]; then
        error "RecRadikoプロジェクトルートが見つかりません: $PROJECT_ROOT"
        exit 1
    fi
    
    if [[ ! -d "$E2E_DIR" ]]; then
        error "E2Eテストディレクトリが見つかりません: $E2E_DIR"
        exit 1
    fi
    
    # 必要なPythonパッケージチェック
    python -c "import pytest, psutil" 2>/dev/null || {
        error "必要なPythonパッケージが不足しています（pytest, psutil）"
        exit 1
    }
    
    # テスト実行
    local exit_code=0
    
    if [[ "$DOCKER_MODE" = true ]]; then
        run_docker_tests
        exit_code=$?
    else
        run_local_tests
        exit_code=$?
    fi
    
    # 結果レポート
    if [[ $exit_code -eq 0 ]]; then
        log "✅ E2Eテスト成功: $TEST_CATEGORY"
        log "レポート保存先: $REPORT_DIR"
    else
        error "❌ E2Eテスト失敗: $TEST_CATEGORY (終了コード: $exit_code)"
    fi
    
    # クリーンアップ
    if [[ "$CLEANUP_AFTER" = true ]]; then
        log "テスト環境クリーンアップ中..."
        # 一時ファイル削除など
        find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null || true
        find "$PROJECT_ROOT" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    fi
    
    log "E2Eテスト完了"
    return $exit_code
}

# トラップ設定（Ctrl+Cなどでの中断時のクリーンアップ）
trap 'error "テスト実行が中断されました"; exit 130' INT TERM

# メイン実行
main "$@"