# RecRadiko macOSアプリケーション ビルドガイド

## 📋 概要

RecRadikoをmacOSネイティブアプリケーション（.app）としてビルドする手順書です。

## ✅ ビルド済み成果物

### 基本バンドル作成 - 完了

```
dist/RecRadiko.app/
├── Contents/
│   ├── Info.plist          # アプリメタデータ（作成済み）
│   ├── MacOS/
│   │   ├── RecRadiko       # メイン実行ファイル
│   │   └── ffmpeg          # ffmpegバイナリ（コピー済み）
│   ├── Resources/          # リソースファイル
│   ├── Frameworks/         # Python依存関係
│   └── _CodeSignature/     # 署名情報（基本署名のみ）
```

## 🛠️ ビルド手順

### 1. 環境準備

```bash
# PyInstallerインストール
pip install pyinstaller

# ffmpegインストール（Homebrew経由）
brew install ffmpeg
```

### 2. ビルドスクリプト実行

```bash
# ビルドスクリプト実行
python build_mac_app.py

# または直接PyInstaller実行
pyinstaller --clean --noconfirm RecRadiko.spec
```

### 3. ffmpeg同梱

```bash
# ffmpegをアプリバンドルにコピー
cp $(which ffmpeg) dist/RecRadiko.app/Contents/MacOS/
```

## 🚀 アプリケーション実行

### Finderから実行
```bash
open dist/RecRadiko.app
```

### コマンドラインから実行
```bash
./dist/RecRadiko.app/Contents/MacOS/RecRadiko
```

## 📝 作成済みファイル

1. **RecRadiko.spec** - PyInstaller設定ファイル
   - アプリバンドル構成定義
   - Info.plist設定
   - 依存関係とデータファイル指定

2. **build_mac_app.py** - ビルド自動化スクリプト
   - 要件チェック
   - クリーンビルド
   - ffmpeg自動コピー
   - 基本テスト実行

3. **requirements-dev.txt** - 開発用依存関係
   - PyInstaller含む

## ⚠️ 既知の問題と解決策

### 1. アプリケーション起動時のタイムアウト
- **問題**: 初回起動時に時間がかかる場合がある
- **原因**: macOSのセキュリティチェック
- **解決**: Gatekeeperの初回チェック後は正常に動作

### 2. ffmpeg実行権限
- **問題**: ffmpegが実行できない
- **解決**: `chmod +x dist/RecRadiko.app/Contents/MacOS/ffmpeg`

### 3. Python依存関係
- **問題**: 特定のモジュールが見つからない
- **解決**: RecRadiko.specのhiddenimportsに追加

## 🔒 次のステップ: コード署名

### 自己署名（テスト用）
```bash
# 自己署名証明書で署名
codesign --force --deep --sign - dist/RecRadiko.app
```

### Developer ID署名（配布用）
```bash
# Developer ID証明書で署名（要Apple Developer Program）
codesign --force --deep --sign "Developer ID Application: Your Name" dist/RecRadiko.app

# 署名確認
codesign --verify --verbose dist/RecRadiko.app
```

## 📦 DMGインストーラー作成

```bash
# create-dmgインストール
brew install create-dmg

# DMG作成
create-dmg \
  --volname "RecRadiko" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "RecRadiko.app" 175 120 \
  --hide-extension "RecRadiko.app" \
  --app-drop-link 425 120 \
  "RecRadiko-2.0.0.dmg" \
  "dist/"
```

## 🔍 トラブルシューティング

### ビルドエラー
1. `ModuleNotFoundError`: hiddenimportsに追加
2. `Permission denied`: 実行権限を確認
3. `Code signature invalid`: 再署名を実行

### 実行時エラー
1. セキュリティ警告: システム環境設定で許可
2. ffmpeg not found: パスを確認してコピー
3. 設定ファイルエラー: 作業ディレクトリを確認

## 📚 参考リンク

- [PyInstaller Documentation](https://pyinstaller.org/)
- [Apple Developer - Code Signing](https://developer.apple.com/documentation/security/code_signing_services)
- [create-dmg GitHub](https://github.com/create-dmg/create-dmg)

---

**作成日**: 2025年7月23日  
**更新日**: 2025年7月23日  
**ステータス**: Phase 1完了 - 基本バンドル作成済み