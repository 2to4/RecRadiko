# RecRadiko ユーザーマニュアル

## 📻 RecRadikoとは

RecRadikoは、Radiko（日本のインターネットラジオサービス）の録音を自動化するPythonアプリケーションです。お気に入りの番組を予約録音したり、リアルタイムで録音したりできます。

**🏆 品質保証**: 319個のテスト（単体テスト228個 + 結合テスト25個 + E2Eテスト50個 + 実際APIテスト16個）が100%成功しており、エンタープライズグレード品質のコードベースです。

### ✨ 主な機能

- 🎯 **即座に録音** - 今聞いている番組をすぐに録音開始
- 📅 **予約録音** - 番組の時間を指定して自動録音
- 🔄 **繰り返し録音** - 毎日/毎週/月次など柔軟な定期録音スケジュール
- 📂 **自動整理** - 録音ファイルを日付・放送局別に自動分類
- 🚀 **デーモンモード** - バックグラウンドで24時間稼働
- 🔐 **プレミアム対応** - 無料・有料プランの両方に対応
- 💻 **CLI操作** - コマンドラインでの簡単操作
- 🎵 **高品質録音** - AAC/MP3/FLAC形式対応、最大320kbps
- 🔄 **並行録音** - 最大8番組の同時録音
- 📊 **システム監視** - CPU・メモリ・ディスク使用量の監視
- 🔔 **通知システム** - デスクトップ通知とメール通知（macOS標準通知対応）
- 🛠️ **自動復旧** - ネットワーク断線やエラー時の自動復旧（認証リトライ機能）
- 📈 **統計情報** - 録音履歴・統計の詳細表示
- 🔧 **統一ログ設定** - 使用環境に応じた最適なログ出力制御

## 🛠️ インストール

### 必要要件

- Python 3.8以上
- FFmpeg（音声録音用）
- インターネット接続

### 1. FFmpegのインストール

#### macOS (Homebrew)
```bash
brew install ffmpeg
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

#### Windows
1. [FFmpeg公式サイト](https://ffmpeg.org/download.html)からダウンロード
2. PATHに追加

### 2. RecRadikoのセットアップ

```bash
# リポジトリのクローン
git clone https://github.com/your-repo/RecRadiko.git
cd RecRadiko

# 依存関係のインストール
pip install -r requirements.txt
```

### 3. 動作確認

```bash
# FFmpegの確認
ffmpeg -version

# RecRadikoの確認
python RecRadiko.py --help
```

## 🚀 基本的な使い方

### 対話型モード（推奨）

RecRadikoは対話型モードで使用することを推奨します。処理が終わった後もコマンドを受け付ける状態が続きます。

```bash
# 対話型モードで起動
python RecRadiko.py --interactive
# または引数なしで実行
python RecRadiko.py

# 対話型プロンプトが表示されます
RecRadiko> list-stations
RecRadiko> record TBS 60
RecRadiko> help
RecRadiko> exit
```

### 放送局一覧を確認

```bash
# 対話型モード内で
RecRadiko> list-stations

# または一回だけ実行
python RecRadiko.py list-stations
```

出力例：
```
放送局一覧 (30 局)
--------------------------------------------------
TBS       TBSラジオ
QRR       文化放送
LFR       ニッポン放送
RN1       ラジオNIKKEI第1
```

### 即座に録音

```bash
# 対話型モード内で
RecRadiko> record TBS 60
RecRadiko> record QRR 30 --format mp3 --bitrate 192

# または一回だけ実行
python RecRadiko.py record TBS 60
python RecRadiko.py record QRR 30 --format mp3 --bitrate 192
```

### 番組表の確認

```bash
# 対話型モード内で
RecRadiko> list-programs TBS
RecRadiko> list-programs TBS --date 2024-01-01

# または一回だけ実行
python RecRadiko.py list-programs TBS
python RecRadiko.py list-programs TBS --date 2024-01-01

# 詳細ログ付きで実行（問題解決時）
RECRADIKO_LOG_LEVEL=DEBUG python RecRadiko.py list-programs TBS
```

### 予約録音

```bash
# 対話型モード内で
RecRadiko> schedule TBS "ラジオ番組名" "2024-01-01T20:00" "2024-01-01T21:00"

# または一回だけ実行
python RecRadiko.py schedule TBS "ラジオ番組名" "2024-01-01T20:00" "2024-01-01T21:00"
python RecRadiko.py schedule QRR "毎週の番組" "2024-01-01T19:00" "2024-01-01T20:00" --repeat weekly
python RecRadiko.py schedule TBS "朝のニュース" "2024-01-01T07:00" "2024-01-01T09:00" --repeat weekdays
python RecRadiko.py schedule LFR "月例番組" "2024-01-01T20:00" "2024-01-01T22:00" --repeat monthly
python RecRadiko.py schedule QRR "音楽番組" "2024-01-01T20:00" "2024-01-01T22:00" --format aac --bitrate 320
```

### スケジュール管理

```bash
# 対話型モード内で
RecRadiko> list-schedules
RecRadiko> status
RecRadiko> stats

# または一回だけ実行
python RecRadiko.py list-schedules
python RecRadiko.py list-schedules --status active
python RecRadiko.py list-schedules --station TBS
python RecRadiko.py remove-schedule <スケジュールID>
```

## ⚙️ 設定

### 基本設定 (config.json)

```json
{
  "area_id": "JP13",
  "output_dir": "./recordings",
  "max_concurrent_recordings": 4,
  "auto_cleanup_enabled": true,
  "retention_days": 30,
  "min_free_space_gb": 10.0,
  "notification_enabled": true,
  "log_level": "INFO",
  "log_file": "recradiko.log",
  "max_log_size_mb": 100,
  "daemon": {
    "health_check_interval": 300,
    "monitoring_enabled": true,
    "pid_file": "./daemon.pid"
  },
  "error_handler": {
    "max_error_records": 1000,
    "notification_enabled": true,
    "email_config": {
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "your_email@gmail.com",
      "password": "your_app_password",
      "to_emails": ["admin@example.com"]
    }
  }
}
```

### プレミアム認証設定

```json
{
  "auth": {
    "username": "your_premium_username",
    "password": "your_premium_password",
    "auto_authenticate": true,
    "token_cache_enabled": true
  }
}
```

### 録音設定

```json
{
  "recording": {
    "default_format": "mp3",
    "default_bitrate": 192,
    "auto_metadata_enabled": true,
    "tag_audio_files": true,
    "max_concurrent_jobs": 4,
    "segment_timeout": 60,
    "retry_attempts": 3
  }
}
```

### ログ設定

```json
{
  "log_level": "INFO",
  "log_file": "recradiko.log",
  "max_log_size_mb": 100
}
```

#### 環境変数によるログ制御

```bash
# ログレベルの設定
export RECRADIKO_LOG_LEVEL=DEBUG
export RECRADIKO_LOG_LEVEL=INFO
export RECRADIKO_LOG_LEVEL=WARNING
export RECRADIKO_LOG_LEVEL=ERROR

# ログファイルの指定
export RECRADIKO_LOG_FILE=custom.log

# コンソール出力の制御
export RECRADIKO_CONSOLE_OUTPUT=true   # 強制有効
export RECRADIKO_CONSOLE_OUTPUT=false  # 強制無効

# 最大ログファイルサイズ（MB）
export RECRADIKO_MAX_LOG_SIZE=50
```

#### ログ出力動作の説明

RecRadikoは統一ログ設定により、使用環境に応じて最適なログ出力を自動制御します：

- **通常使用時**: コンソール出力なし、ファイルログのみ
- **テスト時**: コンソール出力あり、詳細ログ表示
- **デバッグ時**: 環境変数で詳細ログを有効化可能

## 🖥️ デーモンモード

### デーモンの開始

```bash
# バックグラウンドで開始
python RecRadiko.py --daemon

# 設定ファイルを指定
python RecRadiko.py --daemon --config /path/to/config.json
```

### デーモン監視

```bash
# システム状態確認
python RecRadiko.py status

# 統計情報
python RecRadiko.py stats

# 録音ファイル一覧
python RecRadiko.py list-recordings
```

## 📊 統計とモニタリング

### 録音統計

```bash
# 統計情報表示
python RecRadiko.py stats
```

### システム監視

```bash
# システム状態確認
python RecRadiko.py status

# 設定確認
python RecRadiko.py show-config
```


## 🗂️ ファイル管理

### ファイル操作

```bash
# 録音ファイル一覧
python RecRadiko.py list-recordings

# 放送局でフィルター
python RecRadiko.py list-recordings --station TBS

# 日付でフィルター
python RecRadiko.py list-recordings --date 2024-01-01

# 番組名で検索
python RecRadiko.py list-recordings --search "ニュース"
```



## 🔧 トラブルシューティング

### ログ確認

```bash
# ログファイルの確認
tail -f recradiko.log

# エラーログのみ表示
grep "ERROR" recradiko.log

# 詳細ログで実行
RECRADIKO_LOG_LEVEL=DEBUG python RecRadiko.py record TBS 5

# ログ出力制御確認
python -c "from src.logging_config import is_test_mode, is_console_output_enabled; print(f'Test mode: {is_test_mode()}, Console output: {is_console_output_enabled()}')"
```

### よくある問題

#### 認証エラー
```bash
# 放送局一覧で認証確認
python RecRadiko.py list-stations

# システム状態確認
python RecRadiko.py status
```

#### 録音エラー
```bash
# FFmpeg確認
ffmpeg -version

# 実際の録音テスト（1分間）
python RecRadiko.py record TBS 1
```

#### ネットワークエラー
```bash
# 放送局一覧で接続確認
python RecRadiko.py list-stations

# DNS確認
nslookup radiko.jp

# 手動ping確認
ping radiko.jp
```

### 基本診断

```bash
# 設定表示
python RecRadiko.py show-config

# システム状態確認
python RecRadiko.py status

# 統計情報確認
python RecRadiko.py stats
```

## 🔧 高度な使い方

### 設定ファイルの使い分け

```bash
# 設定ファイルを指定
python RecRadiko.py --config production.json record TBS 60

# 複数設定での並行実行
python RecRadiko.py --config home.json --daemon &
python RecRadiko.py --config server.json --daemon &
```

### 環境変数による制御

```bash
# ログレベル制御
RECRADIKO_LOG_LEVEL=DEBUG python RecRadiko.py record TBS 5

# 出力ディレクトリ制御
RECRADIKO_OUTPUT_DIR=/tmp/recordings python RecRadiko.py record QRR 10

# 並行録音数制御
RECRADIKO_MAX_CONCURRENT=8 python RecRadiko.py --daemon
```

### バッチ処理

```bash
# 複数番組の一括予約
cat schedules.txt | while read line; do
  python RecRadiko.py schedule $line
done

# 複数放送局の一括録音
for station in TBS QRR LFR; do
  python RecRadiko.py record $station 30 &
done
```

### プログラマティック操作

```python
# Python APIを使用した操作
from src.cli import RecRadikoCLI
from src.recording import RecordingManager
from src.scheduler import RecordingScheduler
from datetime import datetime, timedelta

# CLIインスタンス作成
cli = RecRadikoCLI()

# 即座に録音
job_id = cli.record_now('TBS', duration_minutes=60)

# スケジュール作成
start_time = datetime.now() + timedelta(hours=1)
end_time = start_time + timedelta(hours=2)
schedule_id = cli.schedule_recording(
    station_id='TBS',
    program_title='プログラム録音',
    start_time=start_time,
    end_time=end_time,
    repeat_pattern='weekly'
)

# 録音状況監視
status = cli.get_recording_status(job_id)
print(f"録音状況: {status['status']}")
```

## 📝 設定例

### 基本的な家庭用設定

```json
{
  "area_id": "JP13",
  "output_dir": "~/Music/Radio",
  "max_concurrent_recordings": 2,
  "auto_cleanup_enabled": true,
  "retention_days": 14,
  "min_free_space_gb": 5.0,
  "notification_enabled": true,
  "log_level": "INFO",
  "log_file": "recradiko.log",
  "max_log_size_mb": 50,
  "recording": {
    "default_format": "mp3",
    "default_bitrate": 128,
    "auto_metadata_enabled": true,
    "tag_audio_files": true
  },
  "daemon": {
    "health_check_interval": 300,
    "monitoring_enabled": true
  },
  "error_handler": {
    "notification_enabled": true,
    "max_error_records": 500
  }
}
```

### サーバー用設定

```json
{
  "area_id": "JP13",
  "output_dir": "/var/recordings",
  "max_concurrent_recordings": 8,
  "auto_cleanup_enabled": true,
  "retention_days": 90,
  "min_free_space_gb": 50.0,
  "notification_enabled": false,
  "log_level": "WARNING",
  "log_file": "/var/log/recradiko/recradiko.log",
  "max_log_size_mb": 200,
  "daemon": {
    "health_check_interval": 60,
    "monitoring_enabled": true,
    "pid_file": "/var/run/recradiko.pid"
  },
  "recording": {
    "default_format": "mp3",
    "default_bitrate": 192,
    "max_concurrent_jobs": 6,
    "quality_check_enabled": true
  },
  "file_manager": {
    "auto_cleanup_enabled": true,
    "checksum_verification": true
  },
  "error_handler": {
    "max_error_records": 2000,
    "email_config": {
      "smtp_server": "localhost",
      "smtp_port": 25,
      "to_emails": ["admin@server.local"]
    }
  }
}
```

### 高品質録音設定

```json
{
  "recording": {
    "default_format": "mp3",
    "default_bitrate": 320,
    "segment_timeout": 60,
    "retry_attempts": 5,
    "quality_check_enabled": true,
    "auto_metadata_enabled": true,
    "tag_audio_files": true
  },
  "streaming": {
    "max_workers": 8,
    "segment_buffer_size": 200,
    "connection_timeout": 60,
    "read_timeout": 120,
    "retry_segment_attempts": 5,
    "parallel_downloads": true
  },
  "file_manager": {
    "checksum_verification": true,
    "metadata_backup_enabled": true,
    "auto_repair_enabled": true
  },
  "max_concurrent_recordings": 4
}
```

## 📞 サポート

### バグレポート・機能要望

GitHub Issues: https://github.com/your-repo/RecRadiko/issues

### ライセンス

MIT License

### 免責事項

- このソフトウェアは個人利用目的で開発されています
- Radikoの利用規約を遵守してご利用ください
- 録音したコンテンツの著作権は各放送局に帰属します
- 商用利用や再配布は控えてください

---

## 📚 参考情報

### 対応地域ID

- `JP13`: 東京都
- `JP27`: 大阪府  
- `JP14`: 神奈川県
- `JP23`: 愛知県
- 他の地域IDは[Radiko公式サイト](https://radiko.jp/)で確認

### 主要放送局ID

- `TBS`: TBSラジオ
- `QRR`: 文化放送
- `LFR`: ニッポン放送
- `RN1`: ラジオNIKKEI第1
- `RN2`: ラジオNIKKEI第2
- `INT`: interfm
- `FMT`: TOKYO FM

### おすすめ設定

#### 日常使い
```bash
# 毎日のニュース番組を録音
python RecRadiko.py schedule TBS "森本毅郎・スタンバイ!" "2024-01-01T06:30" "2024-01-01T08:30" --repeat weekdays

# 週末の音楽番組を録音
python RecRadiko.py schedule LFR "オールナイトニッポン" "2024-01-06T01:00" "2024-01-06T03:00" --repeat weekends
```

#### 長期間録音
```bash
# デーモンモードで開始
python RecRadiko.py --daemon

# 複数番組を一括予約
for station in TBS QRR LFR; do
    python RecRadiko.py schedule $station "深夜番組" "2024-01-01T25:00" "2024-01-01T27:00" --repeat weekly
done
```

#### ログ制御の活用
```bash
# 問題解決時の詳細ログ
RECRADIKO_LOG_LEVEL=DEBUG python RecRadiko.py record TBS 5

# サーバー運用時の警告のみ
RECRADIKO_LOG_LEVEL=WARNING python RecRadiko.py --daemon

# カスタムログファイル
RECRADIKO_LOG_FILE=/var/log/recradiko_custom.log python RecRadiko.py --daemon
```