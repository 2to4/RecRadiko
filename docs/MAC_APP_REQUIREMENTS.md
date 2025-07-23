# RecRadiko macOSアプリケーション化 要件定義書

## 📋 概要

RecRadikoをスタンドアロンのmacOSアプリケーションとして配布可能にする。ユーザーはPython環境の構築や依存関係のインストールなしに、ダブルクリックでアプリケーションを起動できる。

## 🎯 プロジェクト目標

1. **ユーザビリティ向上**: 技術的知識不要で即座に使用可能
2. **配布の簡易化**: DMGインストーラーによるワンクリックインストール
3. **互換性確保**: Intel Mac・Apple Silicon Mac両対応
4. **セキュリティ対応**: macOS Gatekeeperに準拠した安全な配布

## 📱 システム要件

### 対応OS
- macOS 12.0 Monterey以降
- Intel Mac（x86_64）およびApple Silicon Mac（ARM64）対応

### 必要なディスク容量
- アプリケーション本体: 約150MB
- 実行時の作業領域: 約500MB
- 録音ファイル保存: ユーザーの使用状況による

## 🔧 技術要件

### アプリケーションバンドル構造
```
RecRadiko.app/
├── Contents/
│   ├── Info.plist              # アプリケーションメタデータ
│   ├── MacOS/
│   │   └── RecRadiko           # メイン実行可能ファイル
│   ├── Resources/
│   │   ├── icon.icns           # アプリケーションアイコン
│   │   ├── ffmpeg              # ffmpegユニバーサルバイナリ
│   │   ├── config.json.template # 設定ファイルテンプレート
│   │   └── data/               # その他のリソース
│   └── Frameworks/             # 依存ライブラリ・Pythonランタイム
```

### 依存関係の内包
1. **Python 3.9+ランタイム**: PyInstallerによる同梱
2. **Pythonライブラリ**: requirements.txt記載の全ライブラリ
3. **ffmpeg**: ユニバーサルバイナリ版（ARM64 + x86_64）
4. **SQLite**: Python標準ライブラリに含まれる

### ユニバーサルバイナリ対応
- PyInstallerのuniversal2オプション使用
- ffmpegもユニバーサルバイナリ版を使用
- 単一の.appファイルで両アーキテクチャ対応

## 🔐 セキュリティ要件

### コード署名
- **Developer ID証明書**: Apple Developer Programメンバーシップ必須
- **署名対象**: アプリケーションバンドル全体および内部バイナリ
- **タイムスタンプ**: 署名時にタイムスタンプサーバー使用

### Notarization（公証）
- **必須要件**: macOS 10.15以降での配布に必須
- **提出方法**: notarytoolによる自動化
- **審査項目**: Hardened Runtime、セキュアな暗号化実装

### Entitlements（権限）
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Python実行に必要 -->
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <!-- ネットワーク通信 -->
    <key>com.apple.security.network.client</key>
    <true/>
    <!-- ファイル読み書き -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    <!-- Hardened Runtime有効化 -->
    <key>com.apple.security.runtime</key>
    <true/>
</dict>
</plist>
```

### プライバシー設定（Info.plist）
- ネットワーク使用目的の明記
- ファイルアクセス権限の説明
- マイクロフォン・カメラは不使用

## 📦 配布要件

### DMGインストーラー
- **デザイン**: 背景画像付きカスタムレイアウト
- **内容**: RecRadiko.appとApplicationsへのシンボリックリンク
- **サイズ**: 圧縮後約100MB目標
- **署名**: DMGファイル自体も署名・公証

### 自動アップデート（オプション）
- **Sparkleフレームワーク**: macOS標準的なアップデート機構
- **更新チャネル**: stable/beta選択可能
- **差分更新**: 帯域幅節約のための差分配信

## 🎨 UI/UX要件

### アプリケーションアイコン
- **フォーマット**: .icns（複数解像度含む）
- **サイズ**: 16x16〜1024x1024の各解像度
- **デザイン**: macOS Big Sur以降のデザインガイドライン準拠

### 初回起動体験
1. Gatekeeperの警告なし（公証済み）
2. 必要な権限の要求と説明
3. デフォルト設定での即座の使用開始

### ターミナル互換性
- ターミナル.appでのCLIモード維持
- .app内のCLIツール直接実行サポート

## 🚀 開発フェーズ

### Phase 1: 基本バンドル作成
- PyInstallerセットアップ
- 基本的な.app作成
- ローカルテスト

### Phase 2: ユニバーサルバイナリ対応
- ARM64/x86_64両対応ビルド
- ffmpegユニバーサルバイナリ統合
- 両アーキテクチャでのテスト

### Phase 3: 署名・公証
- Developer ID取得（必要な場合）
- コード署名実装
- Notarization対応

### Phase 4: インストーラー作成
- DMGデザイン・作成
- インストール手順書作成
- 配布準備

### Phase 5: テスト・品質保証
- 各macOSバージョンでのテスト
- M1/Intel Mac両方でのテスト
- ユーザビリティテスト

## 📊 成功基準

1. **起動時間**: ダブルクリックから5秒以内に起動
2. **互換性**: macOS 12.0以降、Intel/Apple Silicon両対応
3. **セキュリティ**: Gatekeeper警告なし、公証済み
4. **サイズ**: DMGファイル150MB以下
5. **安定性**: クラッシュレポート0件（初期リリース後1週間）

## 🔧 技術スタック

### ビルドツール
- **PyInstaller 6.0+**: Pythonアプリケーションバンドラー
- **create-dmg**: DMGインストーラー作成ツール
- **codesign**: macOSコード署名ツール
- **notarytool**: Apple公証ツール

### CI/CD（オプション）
- GitHub Actions: 自動ビルド・リリース
- TestFlight代替: ベータ配布システム

## 📝 ドキュメント要件

1. **インストールガイド**: スクリーンショット付き
2. **トラブルシューティング**: よくある問題と解決方法
3. **アンインストール手順**: 完全削除方法
4. **開発者向けビルドガイド**: ソースからのビルド手順

## ⚠️ リスクと対策

### リスク
1. **Apple Developer Program費用**: 年間$99
2. **公証審査の遅延**: 最大48時間
3. **依存関係の互換性問題**: 特定のPythonライブラリ
4. **ファイルサイズの増大**: Pythonランタイム含む

### 対策
1. **オープンソース向け無料証明書の検討**
2. **事前の公証テスト実施**
3. **徹底的な依存関係テスト**
4. **不要ファイルの除外設定**

---

**作成日**: 2025年7月22日  
**バージョン**: 1.0.0  
**ステータス**: 承認待ち