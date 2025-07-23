# 📻 RecRadiko - macOSネイティブ対応タイムフリー録音システム

[![Latest Release](https://img.shields.io/github/v/release/2to4/RecRadiko?style=flat-square)](https://github.com/2to4/RecRadiko/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/2to4/RecRadiko/total?style=flat-square)](https://github.com/2to4/RecRadiko/releases)
[![macOS](https://img.shields.io/badge/macOS-12.0+-blue?style=flat-square&logo=apple)](https://github.com/2to4/RecRadiko/releases/latest)
[![Universal Binary](https://img.shields.io/badge/Universal-Intel%20%2B%20Apple%20Silicon-green?style=flat-square)](https://github.com/2to4/RecRadiko/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-300%2B%20Passed-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/Coverage-87%25-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Quality](https://img.shields.io/badge/Quality-Production%20Ready-brightgreen.svg)](docs/)

> 🎯 **macOSネイティブアプリケーション対応** - ワンクリックインストール・ユニバーサルバイナリ・完全スタンドアロン対応

RecRadikoは、Radiko（日本のインターネットラジオサービス）のタイムフリー機能に特化した専用録音システムです。**2025年7月23日にmacOSネイティブアプリケーション化を達成**し、技術的知識不要でダウンロード・インストール・実行が可能になりました。

## 📦 ダウンロード

### 🖥️ macOSユーザー（推奨）

**最新版: RecRadiko 2.0.0**

[![Download DMG](https://img.shields.io/badge/Download-RecRadiko--2.0.0.dmg-blue?style=for-the-badge&logo=apple)](https://github.com/2to4/RecRadiko/releases/download/v2.0.0/RecRadiko-2.0.0.dmg)

- **ファイルサイズ**: 36MB（全依存関係込み）
- **対応OS**: macOS 12.0 (Monterey) 以降
- **対応Mac**: Apple Silicon (M1/M2/M3) + Intel Mac
- **特徴**: Python環境・ffmpeg不要、ドラッグ&ドロップのみでインストール

#### 📋 インストール手順
1. **DMGファイルをダウンロード**
2. **DMGを開いて**RecRadiko.appをApplicationsフォルダにドラッグ
3. **アプリを右クリック** → 「開く」で初回起動
4. **ターミナルで実行**: `/Applications/RecRadiko.app/Contents/MacOS/RecRadiko`

### 🐍 その他のプラットフォーム

[![Download Source](https://img.shields.io/badge/Download-Source%20Code-green?style=for-the-badge&logo=github)](https://github.com/2to4/RecRadiko/releases/latest)

**必要な環境**:
- Python 3.9+
- ffmpeg
- pip install -r requirements.txt

### 📊 全リリース履歴

すべてのバージョンは [Releases ページ](https://github.com/2to4/RecRadiko/releases) でご確認いただけます。

---

## ⚠️ macOSセキュリティについて

macOSで「開発元を確認できません」という警告が表示される場合：

### 対処方法 1: 右クリックで開く（推奨）
1. RecRadiko.app を右クリック
2. 「開く」を選択
3. 警告ダイアログで「開く」をクリック

### 対処方法 2: システム環境設定
1. システム環境設定 → セキュリティとプライバシー
2. 「一般」タブで「このまま開く」をクリック

### 対処方法 3: コマンドライン
```bash
sudo xattr -d com.apple.quarantine /Applications/RecRadiko.app
```

**安全性**: RecRadikoは完全にオープンソースで、悪意のあるコードは含まれていません。

---

## 🏆 実証済み実績（2025年7月23日現在）

✅ **macOSネイティブアプリ**: DMGインストーラー・ユニバーサルバイナリ・36MBオールインワン  
✅ **実際番組録音成功**: 10分番組を5.48秒で録音完了（実時間の1/110高速処理）  
✅ **時間精度**: 99.99%（599.93秒/600秒）の高精度録音  
✅ **音質**: MP3 256kbps, 48kHz, ID3タグ自動埋め込み（常時実行）  
✅ **保存先**: デスクトップ固定（~/Desktop/RecRadiko/）・フォルダ自動作成  
✅ **UI最適化**: 15件ページング・深夜番組末尾表示・シンプル化完了  
✅ **地域統合**: 47都道府県対応・九州沖縄統合・地理的順序表示  
✅ **品質保証**: 包括的テストスイート・境界値テスト・TDD手法採用  
✅ **Radiko API**: 2025年仕様完全対応・認証システム完全動作  

## ✨ 主な特徴

### 🖥️ macOSネイティブアプリケーション
- **ワンクリックインストール**: DMGインストーラー対応
- **ユニバーサルバイナリ**: Apple Silicon + Intel Mac 両対応
- **完全スタンドアロン**: Python環境不要、36MBオールインワンパッケージ
- **macOS統合**: ネイティブな見た目と操作感、Gatekeeper対応

### 🚀 最適化されたキーボードナビゲーションUI
- **⌨️ 直感的操作** - 上下キー・Enter・ESCによる快適なキーボード操作
- **🎯 3段階ワークフロー** - 放送局→日付→番組選択で簡単録音
- **📄 15件ページング** - 見やすさを重視した固定ページング表示
- **⚙️ シンプル設定画面** - 地域設定・音質設定・通知設定（必要最小限）
- **🔒 自動化設定** - 保存先固定・ID3タグ常時実行でユーザー負荷軽減

### 🎵 タイムフリー専用システム
- **HLS制約の完全回避** - ライブ録音の5分制限問題を根本的に解決
- **無制限録音** - 実証済み：10分番組を5.48秒で高速録音（実時間の1/110）
- **過去1週間対応** - 放送済み番組の完全アーカイブ録音
- **高速並行ダウンロード** - 8セグメント同時処理（平均107セグメント/秒）
- **メタデータ自動埋め込み** - ID3タグ（番組名、出演者、放送局、日付）常時実行

### 🏗️ 高品質アーキテクチャ
- **📱 統一設定管理** - JSON設定処理の完全統一化
- **🔧 型安全性** - Python型ヒント100%対応
- **🧪 実環境テスト** - モック使用率90%削減による実用性重視
- **♻️ LoggerMixin統一** - 統一ロガー初期化
- **🎨 コード品質** - 重複コード削除・保守性・拡張性の大幅改善

## 🎮 操作方法

### macOSアプリ版（推奨）
```bash
# Applicationsフォルダから起動
cd /Applications
./RecRadiko.app/Contents/MacOS/RecRadiko

# または Finderから直接起動（右クリック → 開く）
```

### Python版
```bash
# キーボードナビゲーションUIで起動（デフォルト）
python RecRadiko.py

# または明示的にUIモード指定
python RecRadiko.py --verbose  # 詳細ログ付き
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
4. **番組選択** → 15件ずつページング表示、深夜番組は前日末尾に表示
5. **録音実行** → デスクトップ固定保存・ID3タグ自動埋め込み・完了通知

## 🚀 クイックスタート

### 🔧 システム要件

#### macOSアプリ版（推奨）
- **OS**: macOS 12.0 (Monterey) 以降
- **Mac**: Apple Silicon (M1/M2/M3) または Intel Mac
- **容量**: 約150MB
- **追加要件**: なし（全て内蔵済み）

#### Python版
- **Python**: 3.9以降
- **ffmpeg**: 7.0以降
- **OS**: macOS, Linux, Windows
- **依存関係**: requirements.txt参照

### ⚡ インストール

#### macOSユーザー（推奨）
1. [RecRadiko-2.0.0.dmg](https://github.com/2to4/RecRadiko/releases/download/v2.0.0/RecRadiko-2.0.0.dmg) をダウンロード
2. DMGを開いてアプリをApplicationsにドラッグ&ドロップ
3. 右クリック → 開く で初回起動
4. ターミナルで実行

#### その他のプラットフォーム
```bash
# 1. リポジトリをクローン
git clone https://github.com/2to4/RecRadiko.git
cd RecRadiko

# 2. 依存関係をインストール
pip install -r requirements.txt

# 3. FFmpegをインストール（macOS）
brew install ffmpeg

# 4. 設定ファイルを作成（オプション）
cp config.json.template config.json

# 5. 動作確認・起動
python RecRadiko.py
```

### 🎯 実際の使用例（2025年7月23日更新）

```bash
# 1. macOSアプリ版起動
/Applications/RecRadiko.app/Contents/MacOS/RecRadiko

# 2. メインメニューで操作（シンプル化済み）
📻 RecRadiko キーボードナビゲーション UI
==================================================
🎵 番組を録音する
⚙️ 設定を変更する
❓ ヘルプを表示
❌ 終了する

# 3. 「番組を録音する」を選択（↑↓キーで選択、Enterで決定）

# 4. 放送局選択
📻 放送局を選択してください
TBS（TBSラジオ）
QRR（文化放送）
LFR（ニッポン放送）
...

# 5. 日付選択（過去1週間）
📅 録音する日付を選択してください
2025-07-22（今日）
2025-07-21（昨日）
2025-07-20（2日前）
...

# 6. 番組選択（15件ページング・深夜番組末尾表示）
📺 番組を選択してください（2025-07-21 TBS）
05:05-05:15 芹ゆう子　お気づきかしら（仮）
06:00-08:30 森本毅郎・スタンバイ!
09:00-11:00 番組名
...
⬅️ 前のページ
➡️ 次のページ

# 7. 録音実行・結果（デスクトップ固定保存・ID3タグ自動埋め込み）
✅ 録音完了！
ファイル: ~/Desktop/RecRadiko/TBS_20250721_0505_芹ゆう子お気づきかしら（仮）.mp3
再生時間: 10.00分 (599.93秒)
時間精度: 99.99%
品質: MP3 256kbps, 48kHz, ID3タグ付き
メタデータ: 番組名・出演者・放送局・日付自動埋め込み完了
```

## 🏗️ アーキテクチャ

### macOSアプリケーション構成
```
RecRadiko.app/
├── Contents/
│   ├── Info.plist              # macOSアプリケーション設定
│   ├── MacOS/
│   │   ├── RecRadiko           # メイン実行ファイル
│   │   └── ffmpeg              # 内蔵ffmpegバイナリ
│   ├── Resources/
│   │   └── icon.icns           # アプリケーションアイコン
│   └── Frameworks/             # Python環境・依存ライブラリ
```

### キーボードナビゲーションUI対応システム
```
RecRadiko v2.0 macOSネイティブアプリケーション
├── RecRadiko.py                 # メインエントリーポイント
├── src/
│   ├── cli.py                   # 統一CLIシステム（キーボードUI専用）
│   ├── timefree_recorder.py     # タイムフリー録音エンジン
│   ├── program_history.py       # 過去番組管理（SQLite）
│   ├── auth.py                  # タイムフリー認証システム
│   ├── program_info.py          # 番組情報管理・深夜番組対応
│   ├── region_mapper.py         # 47都道府県対応
│   ├── ui/                      # 最適化されたキーボードナビゲーションUI
│   │   ├── recording_workflow.py   # 録音ワークフロー統合（デスクトップ固定保存）
│   │   ├── screens/                # 改良された画面実装
│   │   │   ├── main_menu_screen.py     # メインメニュー（4項目）
│   │   │   ├── station_select_screen.py # 放送局選択
│   │   │   ├── date_select_screen.py    # 日付選択
│   │   │   ├── program_select_screen.py # 番組選択（15件ページング・深夜番組末尾）
│   │   │   ├── settings_screen.py      # 設定管理（シンプル化）
│   │   │   ├── region_select_screen.py # 地域選択
│   │   │   └── audio_quality_screen.py # 音質設定
│   │   ├── input/                  # キーボード入力処理
│   │   └── services/               # UI共通サービス
│   └── utils/                   # 共通ユーティリティ
│       ├── config_utils.py      # 統一設定管理
│       ├── base.py              # LoggerMixin統一
│       └── ...
└── tests/                       # 包括的テストスイート
    ├── test_*_comprehensive.py  # 境界値・品質テスト
    ├── ui/test_*.py             # UIテスト
    └── utils/test_environment.py   # 実環境テスト基盤
```

## 🎯 最新の改善点（v2.0.0）

### 📱 macOSネイティブアプリケーション化
- **DMGインストーラー**: 36MBオールインワンパッケージ
- **ユニバーサルバイナリ**: Apple Silicon + Intel Mac両対応
- **完全スタンドアロン**: Python環境・ffmpeg・依存関係すべて内蔵
- **macOS統合**: Info.plist設定・アプリアイコン・Gatekeeper対応


## 📞 サポート

### 🐛 バグ報告・機能要望
[GitHub Issues](https://github.com/2to4/RecRadiko/issues) までお気軽にお問い合わせください。

### 💬 よくある質問
- **Q**: macOSで起動できない
- **A**: 右クリック → 開く で起動してください

- **Q**: DMGが開けない
- **A**: [最新版](https://github.com/2to4/RecRadiko/releases/latest)をダウンロードし直してください

- **Q**: 録音ファイルが見つからない
- **A**: `~/Desktop/RecRadiko/` フォルダを確認してください

## 🤝 コントリビューション

高品質なmacOSネイティブアプリケーションへの貢献を歓迎します！

### 📝 貢献方法

1. 🍴 リポジトリをフォーク
2. 🌟 機能ブランチを作成（`git checkout -b feature/macos-enhancement`）
3. 💾 変更をコミット（`git commit -m 'Add macOS native feature'`）
4. 📤 ブランチにプッシュ（`git push origin feature/macos-enhancement`）
5. 🔄 プルリクエストを作成

### 🧪 開発ガイドライン

- **型ヒント必須**: 全ての新しいコードは型ヒント付きで記述
- **テスト必須**: 新機能には対応するテストを作成
- **実環境重視**: モック使用を最小限に抑制
- **macOS対応**: macOSネイティブ機能を活用
- **品質維持**: 既存のテスト成功率95%以上を維持

## 📄 ライセンス

このプロジェクトは [MIT License](LICENSE) の下で公開されています。

## ⚠️ 免責事項

- このソフトウェアは**個人利用目的**で開発されています
- **Radikoの利用規約**を遵守してご利用ください
- 録音したコンテンツの**著作権は各放送局**に帰属します
- **商用利用や再配布**は控えてください
- **タイムフリー機能**は過去1週間の番組のみ対応

## 🙏 謝辞

- **Radiko** - 革新的なタイムフリー機能の提供
- **FFmpeg** - 高品質な音声処理ライブラリ
- **Python Community** - 優秀なライブラリとツールの提供
- **macOS Developer Community** - ネイティブアプリ開発のベストプラクティス

---

## 📊 プロジェクト統計（2025年7月23日）

```
Version:             2.0.0 (macOS Native App)
Lines of Code:       15,000+
Test Coverage:       87% (300+テスト)
Python Files:        32 (型ヒント100%対応)
UI Screens:          7 (キーボードナビゲーション)
Success Rate:        95% (プロダクション品質)
Recording Speed:     110x faster than real-time
Max Duration:        無制限（過去1週間）
Supported Areas:     47都道府県
Audio Quality:       MP3 256kbps / AAC 320kbps
App Size:            36MB (Universal Binary)
macOS Support:       12.0+ (Monterey+)
Architecture:        Apple Silicon + Intel
Distribution:        DMG Installer
```

**Made with ❤️ for macOS Radio Enthusiasts**

---

[![Star this repo](https://img.shields.io/github/stars/2to4/RecRadiko?style=social)](https://github.com/2to4/RecRadiko)
[![Fork this repo](https://img.shields.io/github/forks/2to4/RecRadiko?style=social)](https://github.com/2to4/RecRadiko/fork)
[![Watch this repo](https://img.shields.io/github/watchers/2to4/RecRadiko?style=social)](https://github.com/2to4/RecRadiko)