# E2Eテスト実行環境のDockerfile
FROM python:3.11-slim

# 必要なシステムパッケージのインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    wget \
    procps \
    htop \
    net-tools \
    iproute2 \
    tcpdump \
    && rm -rf /var/lib/apt/lists/*

# Python依存関係のインストール
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# E2Eテスト用の追加パッケージ
RUN pip install --no-cache-dir \
    pytest-xdist \
    pytest-timeout \
    pytest-benchmark \
    pytest-html \
    pytest-cov \
    pytest-mock \
    psutil \
    docker \
    requests-mock

# テスト用ディレクトリ作成
RUN mkdir -p /app/test_data /app/logs /app/cache /app/reports

# アプリケーションコードをコピー
COPY . .

# テスト実行用のスクリプト
COPY tests/e2e/scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.sh

# 環境変数設定
ENV PYTHONPATH=/app
ENV E2E_TEST_MODE=true
ENV LOG_LEVEL=DEBUG

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# デフォルトコマンド
CMD ["python", "-m", "pytest", "tests/e2e/", "-v", "--tb=short"]