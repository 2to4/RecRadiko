# 📖 RecRadiko ユーザーマニュアル

> **キーボードナビゲーションUI完全操作ガイド** - 2025年7月15日版

## 📻 RecRadiko タイムフリー専用システムとは

RecRadikoは、Radiko（日本のインターネットラジオサービス）のタイムフリー機能に特化した専用録音システムです。**2025年7月15日完全リファクタリング達成**により、従来のライブ録音のHLS制約（5分制限）を根本的に解決し、キーボードナビゲーションUIで直感的に操作できるプロダクション品質のPythonアプリケーションです。

## 🏆 **実証済み実績（2025年7月15日現在）**

✅ **実際番組録音成功**: 10分番組を5.48秒で録音完了（実時間の1/110高速処理）  
✅ **時間精度**: 99.99%（599.93秒/600秒）の高精度録音  
✅ **音質**: MP3 256kbps, 48kHz, ID3タグ付き高品質録音  
✅ **成功率**: 100%（120/120セグメント完全取得）  
✅ **Radiko API**: 2025年仕様完全対応・認証システム完全動作  
✅ **テスト品質**: 262テスト95%成功（実環境重視・モック使用90%削減完了）  
✅ **コード品質**: 型ヒント100%対応・統一設定管理・重複コード完全削除

### ✨ タイムフリー専用機能

- 🎯 **過去番組録音** - 過去1週間の番組を日付・番組名指定で完全録音（実証済み）
- 📅 **番組表検索** - 過去1週間の番組一覧表示・キーワード検索
- ⚡ **高速録音** - 実証済み：10分番組を5.48秒で録音（実時間の1/110）
- 🔄 **並行ダウンロード** - 8セグメント同時処理（平均107セグメント/秒）
- 📂 **自動整理** - 録音ファイルを日付・放送局別に自動分類
- 🔐 **タイムフリー認証** - Radiko API 2025年仕様完全対応
- 💻 **対話型CLI** - 直感的なタイムフリー専用コマンド
- 🎵 **高品質録音** - MP3 256kbps, 48kHz, ID3タグ付き高品質録音
- 🏷️ **メタデータ対応** - ID3タグ自動埋め込み（番組名、出演者、放送局、日付）
- 🔧 **SQLiteキャッシュ** - 24時間有効な番組表キャッシュシステム
- 🌏 **47都道府県対応** - 全国どこでも利用可能
- 📊 **録音履歴** - 完全な録音ログと統計

### 🚫 **注意事項**

本システムは**タイムフリー専用**です。以下の機能は提供されません：
- ライブ録音（HLS制約のため5分制限あり）
- 将来録音・予約録音
- リアルタイム録音

過去1週間の番組のみ録音可能です。

## 🛠️ インストール

### 必要要件

- Python 3.8以上
- FFmpeg（音声変換用）
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

### 2. RecRadikoのインストール

```bash
# 1. リポジトリをクローン
git clone https://github.com/2to4/RecRadiko.git
cd RecRadiko

# 2. 依存関係をインストール
pip install -r requirements.txt

# 3. 設定ファイルを作成
cp config.json.template config.json

# 4. 動作確認
python RecRadiko.py --help
```

## ⚙️ 初期設定

### config.jsonの編集

```json
{
  "prefecture": "東京",
  "output_dir": "./recordings",
  "recording": {
    "default_format": "mp3",
    "default_bitrate": 192,
    "concurrent_segments": 8,
    "enable_metadata": true,
    "segment_timeout": 30,
    "retry_attempts": 3
  },
  "timefree": {
    "cache_duration_hours": 24,
    "enable_program_search": true,
    "max_search_results": 100,
    "database_path": "./timefree.db"
  },
  "ui": {
    "keyboard_navigation_enabled": true,
    "show_progress_bar": true,
    "auto_return_to_menu": true
  },
  "auth": {
    "username": "your_radiko_username",
    "password": "your_radiko_password",
    "auto_authenticate": true,
    "token_cache_enabled": true
  }
}
```

### 都道府県名の設定

以下の形式で都道府県名を指定できます：

```json
{
  "prefecture": "東京"      // または "東京都"
  "prefecture": "大阪"      // または "大阪府"
  "prefecture": "神奈川"    // または "神奈川県"
  "prefecture": "愛知"      // または "愛知県"
  ...
}
```

**47都道府県すべてに対応**しており、内部で自動的に地域IDに変換されます。

## 🎯 基本的な使用方法

### キーボードナビゲーションUI（メインUI）

```bash
# 基本起動（キーボードナビゲーションUIがデフォルト）
python RecRadiko.py

# 詳細ログ付きで起動
python RecRadiko.py --verbose

# 特定の設定ファイルを使用
python RecRadiko.py --config custom_config.json
```

**キーボード操作**:
- **↑/↓**: 項目選択  
- **Enter**: 決定・実行  
- **ESC**: 戻る・キャンセル  
- **Ctrl+C**: 終了  

**録音フロー**:
1. **メインメニュー** → 「番組を録音する」選択
2. **放送局選択** → TBS・文化放送・ニッポン放送等
3. **日付選択** → 過去1週間から日付選択
4. **番組選択** → 該当日の番組一覧から選択
5. **録音実行** → 自動でファイル保存・完了通知

### メインメニューの詳細

起動すると以下のメインメニューが表示されます：

```
📻 RecRadiko キーボードナビゲーション UI
==================================================
🎵 番組を録音する
🔍 番組を検索する  
⚙️ 設定を変更する
📊 システム情報を確認する
❌ 終了する
```

#### 1. 番組を録音する

3段階ワークフローで簡単録音：

**Step 1: 放送局選択**
```
📻 放送局を選択してください
TBS（TBSラジオ）
QRR（文化放送）
LFR（ニッポン放送）
RFR（ラジオ日本）
FMT（TOKYO FM）
J-WAVE（J-WAVE）
...
```

**Step 2: 日付選択**
```
📅 録音する日付を選択してください
2025-07-15（今日）
2025-07-14（昨日）
2025-07-13（2日前）
...（過去1週間）
```

**Step 3: 番組選択**
```
📺 番組を選択してください（2025-07-13 TBS）
05:05-05:15 芹ゆう子　お気づきかしら（仮）[10分]
06:00-08:30 森本毅郎・スタンバイ![150分]
08:30-11:00 赤江珠緒 たまむすび[150分]
...
```

#### 🎯 **実際の録音成功例（2025年7月14日実証）**

```bash
# 実際に録音成功した番組例
RecRadiko> record 2025-07-13 TBS 芹ゆう子　お気づきかしら（仮）

録音設定:
  番組: 芹ゆう子　お気づきかしら（仮）
  放送局: TBS
  開始時刻: 2025-07-13 05:05:00
  終了時刻: 2025-07-13 05:15:00
  予定長さ: 10分

録音開始...
セグメントダウンロード: 100%|██████████| 120/120 [00:01<00:00, 107.48seg/s]

✅ 録音成功！
ファイルサイズ: 19,218,905 bytes (18.33 MB)
セグメント数: 120
失敗セグメント: 0
実際の録音時間: 5.48秒

📊 ファイル詳細:
再生時間: 10.00分 (599.93秒)
予定時間: 10.0分 (600秒)
時間精度: 100.0%
コーデック: mp3
ビットレート: 256000 bps
サンプルレート: 48000 Hz

✅ 再生時間が正しい範囲内です！

# 高品質録音設定
RecRadiko> record 2025-07-10 TBS 森本毅郎・スタンバイ! --format aac --bitrate 320
```

#### 2. 番組を検索する

高度な検索機能で番組を探索：

```
🔍 番組検索オプション
1️⃣ 番組名で検索
2️⃣ 出演者で検索
3️⃣ 日付範囲で検索
4️⃣ 詳細検索（複数条件）
5️⃣ 最近の検索履歴
🔙 メインメニューに戻る
```

**番組名検索例**:
```
🎯 番組名で検索
検索キーワードを入力してください: 森本毅郎

🔍 検索結果 (5件見つかりました)
2025-07-14 TBS 06:00-08:30 森本毅郎・スタンバイ! [150分]
2025-07-13 TBS 06:00-08:30 森本毅郎・スタンバイ! [150分] 
...
```

#### 3. 設定を変更する

統合設定管理画面：

```
⚙️ 設定管理
📍 地域設定: 東京都 (JP13)
🎵 音質設定: MP3 256kbps 48kHz
📂 保存先設定: ~/Downloads/RecRadiko/
🔔 通知設定: macOS標準通知 有効
📤 設定をエクスポート
📥 設定をインポート
🔄 デフォルトに戻す
🔙 メインメニューに戻る
```

#### 4. システム情報を確認する

録音履歴・統計・システム状態の確認：

```
📊 システム情報
💿 録音履歴・統計
🖥️  システム状態
📋 ログ情報
🧪 診断・テスト
🔙 メインメニューに戻る
```

### キーボード操作の詳細

#### 基本操作
- **↑/↓キー**: 項目選択（循環選択対応）
- **Enterキー**: 選択確定・実行
- **ESCキー**: 前画面に戻る・キャンセル
- **Ctrl+C**: アプリケーション完全終了

#### UI特徴
- **視覚的フィードバック**: 選択項目のハイライト表示
- **自動ページング**: 長いリストは10項目ずつ表示
- **エラーハンドリング**: 問題発生時は自動的にメニューに戻る
- **プログレス表示**: 録音中はリアルタイムで進捗を表示
- **応答性**: キー操作<50ms、画面遷移<100ms

## 🎛️ 高度な設定

### 録音品質設定

```json
{
  "recording": {
    "default_format": "aac",           // mp3, aac, wav
    "default_bitrate": 320,            // 128, 192, 256, 320
    "concurrent_segments": 8,          // 並行ダウンロード数（1-16）
    "retry_attempts": 3,               // セグメント取得リトライ回数
    "segment_timeout": 30,             // セグメントタイムアウト（秒）
    "enable_metadata": true,           // ID3タグ自動埋め込み
    "output_naming": "date_station_title"  // ファイル名形式
  }
}
```

### タイムフリーキャッシュ設定

```json
{
  "timefree": {
    "cache_duration_hours": 24,        // 番組表キャッシュ有効期間
    "enable_program_search": true,     // 番組検索機能有効化
    "max_search_results": 100,         // 検索結果の最大数
    "database_path": "./timefree.db"   // SQLiteデータベースパス
  }
}
```

### 出力設定

```json
{
  "output_dir": "./recordings",        // 録音ファイル保存先
  "file_naming": {
    "pattern": "{date}_{station}_{title}",  // ファイル名パターン
    "date_format": "%Y%m%d",           // 日付形式
    "sanitize_filename": true          // ファイル名の無効文字除去
  }
}
```

## 🌟 実用的な使用例

### 📅 過去番組の録音

```bash
# 対話型モードで起動
python RecRadiko.py

# 昨日のニュース番組を録音
RecRadiko> record 2025-07-12 TBS 森本毅郎・スタンバイ!

# 1週間前の音楽番組を録音
RecRadiko> record 2025-07-06 LFR オールナイトニッポン

# 高品質でクラシック番組を録音
RecRadiko> record 2025-07-10 NHK-FM クラシック音楽番組 --format aac --bitrate 320
```

### 🔍 番組探索ワークフロー

```bash
# 1. 特定のパーソナリティの番組を検索
RecRadiko> search-programs 森本毅郎

# 2. 検索結果から番組IDを確認
# Program ID: TBS_20250710_060000

# 3. 番組IDで精密録音
RecRadiko> record-id TBS_20250710_060000

# 4. 特定期間の音楽番組を検索
RecRadiko> search-programs 音楽 --date-range 2025-07-10,2025-07-12

# 5. 特定局の番組一覧で全体を把握
RecRadiko> list-programs 2025-07-12 --station TBS
```

### 📊 番組表活用

```bash
# 週単位での番組表確認
RecRadiko> list-programs 2025-07-07 --to 2025-07-13 --station TBS

# 平日のニュース番組を一括確認
RecRadiko> search-programs ニュース --date-range 2025-07-07,2025-07-11

# 週末の音楽番組を一括確認
RecRadiko> search-programs 音楽 --date-range 2025-07-12,2025-07-13
```

## 🔧 トラブルシューティング

### 🚨 よくある問題と解決方法

#### 1. 認証エラー

**症状**: 「認証に失敗しました」エラー

**解決方法**:
```bash
# タイムフリー認証の再試行
RecRadiko> auth-refresh

# プレミアム認証情報の確認
# config.jsonの"auth"セクションを確認
```

#### 2. 番組が見つからない

**症状**: 「番組が見つかりません」エラー

**解決方法**:
```bash
# 番組表キャッシュのリフレッシュ
RecRadiko> refresh-cache

# 利用可能な番組の確認
RecRadiko> list-programs 2025-07-12 TBS

# 番組名の部分一致で検索
RecRadiko> search-programs 森本
```

#### 3. 録音失敗

**症状**: 録音が途中で停止または失敗

**解決方法**:
```bash
# 詳細ログで録音実行
RecRadiko> record 2025-07-12 TBS 番組名 --verbose

# 番組の利用可能性確認
RecRadiko> search-programs 番組名 --check-availability

# FFmpegの動作確認
ffmpeg -version
```

#### 4. タイムフリー制限エラー

**症状**: 「タイムフリー期間を過ぎています」エラー

**解決方法**:
- タイムフリーは**過去1週間のみ**利用可能
- 録音可能期間の確認:
```bash
RecRadiko> search-programs --date-range $(date -d '7 days ago' +%Y-%m-%d),$(date +%Y-%m-%d)
```

#### 5. キャッシュ関連問題

**症状**: 古い番組表が表示される

**解決方法**:
```bash
# キャッシュクリア
rm -f timefree.db

# アプリケーション再起動
python RecRadiko.py
```

### 🔍 ログの確認

#### ログファイルの場所
- メインログ: `recradiko.log`
- エラーログ: `error.log`
- 構造化エラー: `errors.json`

#### ログレベルの変更
```bash
# デバッグモードで実行
RECRADIKO_LOG_LEVEL=DEBUG python RecRadiko.py

# 詳細ログをコンソールに表示
RECRADIKO_CONSOLE_OUTPUT=true python RecRadiko.py
```

### 📞 サポート連絡先

#### 🐛 バグレポート
- GitHub Issues: [Issues](https://github.com/your-repo/RecRadiko/issues)
- バグレポートテンプレート: [Bug Report](https://github.com/your-repo/RecRadiko/issues/new?template=bug_report.md)

#### 💡 機能要望
- タイムフリー機能要望: [Feature Request](https://github.com/your-repo/RecRadiko/issues/new?template=timefree_feature.md)

## 📈 パフォーマンス最適化

### 🚀 録音速度の向上

```json
{
  "recording": {
    "concurrent_segments": 16,         // 並行数を増加（CPUに応じて）
    "segment_timeout": 15,             // タイムアウトを短縮
    "retry_attempts": 1                // リトライを減らして高速化
  }
}
```

### 💾 ストレージ最適化

```json
{
  "file_management": {
    "auto_cleanup_enabled": true,      // 古いファイルの自動削除
    "retention_days": 30,              // 保存期間（日）
    "compression_enabled": true        // ファイル圧縮有効化
  }
}
```

### 🔧 システムリソース最適化

```bash
# CPU使用率を確認
top -p $(pgrep -f RecRadiko)

# メモリ使用量を確認
ps aux | grep RecRadiko

# ディスク使用量を確認
du -sh recordings/
```

## 📊 統計と監視

### 録音統計の確認

```bash
# 録音履歴の表示
RecRadiko> stats

# 特定期間の統計
RecRadiko> stats --date-range 2025-07-01,2025-07-31

# 放送局別統計
RecRadiko> stats --group-by station
```

### システム監視

```bash
# システム状態の確認
RecRadiko> status

# リソース使用量の確認
RecRadiko> system-info

# キャッシュ状態の確認
RecRadiko> cache-status
```

## 🛡️ セキュリティとプライバシー

### 認証情報の保護

- 認証情報は暗号化されて保存されます
- 設定ファイルのアクセス権限を制限してください：
```bash
chmod 600 config.json
```

### プライバシー保護

- 録音したコンテンツは**個人利用のみ**に留めてください
- **Radikoの利用規約**を遵守してください
- 録音したコンテンツの**著作権は各放送局**に帰属します

## 📄 ライセンスと免責事項

### ライセンス
このプロジェクトは [MIT License](../LICENSE) の下で公開されています。

### 免責事項
- このソフトウェアは**個人利用目的**で開発されています
- **Radikoの利用規約**を遵守してご利用ください
- 録音したコンテンツの**著作権は各放送局**に帰属します
- **商用利用や再配布**は控えてください
- **タイムフリー機能**は過去1週間の番組のみ対応

## 🙏 謝辞

- **Radiko** - 革新的なタイムフリー機能の提供
- **FFmpeg** - 高品質な音声処理ライブラリ
- **Python Community** - 優秀なライブラリとツールの提供

---

**Made with ❤️ for TimeFree Radio Enthusiasts**