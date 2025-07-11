# 🚀 RecRadiko セットアップガイド

このガイドでは、RecRadikoを初めて使用する際のセットアップ手順を詳しく説明します。

## 📋 システム要件

### 必須要件
- **Python 3.8以上**
- **FFmpeg**（音声処理用）
- **インターネット接続**
- **macOS/Linux/Windows**（Windowsは一部制限あり）

### 推奨要件
- **Python 3.9以上**
- **16GB以上のRAM**
- **50GB以上の空きディスク容量**（録音ファイル保存用）

## 🛠️ インストール手順

### 1. リポジトリのクローン
```bash
git clone https://github.com/your-username/RecRadiko.git
cd RecRadiko
```

### 2. Python依存関係のインストール
```bash
# 仮想環境の作成（推奨）
python -m venv recradiko-env
source recradiko-env/bin/activate  # Linux/macOS
# recradiko-env\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt
```

### 3. FFmpegのインストール

#### macOS（Homebrew）
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

### 4. 設定ファイルの作成
```bash
# テンプレートをコピー
cp config.json.template config.json

# エディタで設定を編集
nano config.json  # または好みのエディタ
```

## ⚙️ 設定の詳細

### 基本設定（config.json）
```json
{
  "area_id": "JP13",                    # お住まいの地域ID
  "output_dir": "./recordings",         # 録音ファイル保存先
  "max_concurrent_recordings": 4,       # 同時録音数
  "recording": {
    "default_format": "mp3",            # 録音形式（mp3/aac）
    "default_bitrate": 192              # 音質（128/192/320）
  }
}
```

### 地域ID一覧
| 地域 | ID | 主要放送局 |
|------|----|-----------| 
| 東京都 | JP13 | TBS、文化放送、ニッポン放送 |
| 大阪府 | JP27 | MBS、ABC、関西放送 |
| 神奈川県 | JP14 | tvk、FMヨコハマ |
| 愛知県 | JP23 | CBC、東海ラジオ |

### プレミアム認証設定（オプション）
```json
{
  "auth": {
    "username": "your_radiko_email",
    "password": "your_radiko_password",
    "auto_authenticate": true
  }
}
```

## ✅ 動作確認

### 1. 基本動作テスト
```bash
# ヘルプ表示
python RecRadiko.py --help

# 放送局一覧確認
python RecRadiko.py list-stations
```

### 2. 録音テスト
```bash
# 1分間のテスト録音
python RecRadiko.py record TBS --duration 1

# 録音ファイル確認
ls recordings/
```

### 3. テストスイート実行（開発者向け）
```bash
# 全テスト実行
python -m pytest tests/ -v

# 結果: 346/346 テスト成功を確認
```

## 🔧 トラブルシューティング

### よくある問題

#### 1. FFmpegが見つからない
**症状**: `ffmpeg: command not found`
**解決策**:
```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# パス確認
which ffmpeg
ffmpeg -version
```

#### 2. 認証エラー
**症状**: `Authentication failed`
**解決策**:
```bash
# 認証状況確認
python RecRadiko.py auth-status

# 認証キャッシュリセット
rm -f auth_cache.json

# 地域ID確認
python RecRadiko.py diagnose
```

#### 3. 録音ファイルが空
**症状**: 録音ファイルのサイズが0バイト
**解決策**:
```bash
# ネットワーク確認
python RecRadiko.py test-connection

# ストリーミング確認
python RecRadiko.py test-stream TBS

# ログ確認
tail -f recradiko.log
```

#### 4. 権限エラー
**症状**: `Permission denied`
**解決策**:
```bash
# 出力ディレクトリの権限確認
ls -la recordings/

# 権限修正
chmod 755 recordings/
```

## 📈 パフォーマンス最適化

### 同時録音数の調整
```json
{
  "max_concurrent_recordings": 2,  # 低スペック環境
  "max_concurrent_recordings": 8   # 高スペック環境
}
```

### ストレージ管理
```json
{
  "auto_cleanup_enabled": true,
  "retention_days": 30,           # 30日後に自動削除
  "min_free_space_gb": 10.0      # 最小空き容量
}
```

## 🔄 アップデート手順

### 1. リポジトリ更新
```bash
git pull origin main
```

### 2. 依存関係更新
```bash
pip install -r requirements.txt --upgrade
```

### 3. 設定ファイル確認
```bash
# 新しい設定項目があるかチェック
diff config.json config.json.template
```

### 4. テスト実行
```bash
python -m pytest tests/ -v
```

## 🆘 サポート

### ログファイル
- `recradiko.log` - アプリケーションログ
- `error.log` - エラーログ
- `daemon.log` - デーモンモードログ

### 診断コマンド
```bash
# 総合診断
python RecRadiko.py diagnose

# システム状況
python RecRadiko.py system-status

# 依存関係確認
python RecRadiko.py check-dependencies
```

### サポートリクエスト
問題が解決しない場合は、以下の情報を含めてIssueを作成してください：

1. **環境情報**
   ```bash
   python --version
   ffmpeg -version
   uname -a  # Linux/macOS
   ```

2. **設定ファイル**（機密情報は除く）
3. **エラーログ**
4. **再現手順**

## 🎯 次のステップ

1. **[ユーザーマニュアル](user_manual.md)** - 詳細な使用方法
2. **[対話型モード](README.md#対話型モード)** - 継続的なコマンド実行
3. **[デーモンモード](user_manual.md#デーモンモード)** - バックグラウンド稼働
4. **[予約録音](user_manual.md#予約録音)** - 自動録音スケジューリング

これでRecRadikoのセットアップは完了です！高品質なラジオ録音をお楽しみください 🎵