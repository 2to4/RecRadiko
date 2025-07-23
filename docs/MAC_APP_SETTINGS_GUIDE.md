# RecRadiko macOS固有設定ガイド

## 📋 概要

RecRadikoアプリケーションのmacOS固有設定（Info.plist、アイコン、権限）の実装詳細です。

## ✅ 実装済み内容

### 1. アイコン作成

#### 生成されたアイコン
- **ファイル**: `assets/icon.icns`
- **デザイン**: ダークブルー背景に白い"R"文字と電波アイコン
- **サイズ**: 16x16から1024x1024まで全解像度対応
- **作成スクリプト**: `create_icon.py`

#### アイコンの特徴
- macOS Big Sur以降のデザインガイドライン準拠
- 高解像度Retinaディスプレイ対応
- シンプルで視認性の高いデザイン

### 2. Info.plist設定

#### 基本情報
```xml
<key>CFBundleDisplayName</key>
<string>RecRadiko - Radikoタイムフリー録音</string>
<key>CFBundleIdentifier</key>
<string>com.recradiko.app</string>
<key>CFBundleVersion</key>
<string>2.0.0</string>
```

#### アプリケーション動作設定
```xml
<!-- Dockに表示しない（CLIアプリ） -->
<key>LSUIElement</key>
<true/>

<!-- 複数インスタンス許可 -->
<key>LSMultipleInstancesProhibited</key>
<false/>

<!-- 最小システム要件 -->
<key>LSMinimumSystemVersion</key>
<string>12.0</string>
```

#### プライバシー設定
```xml
<!-- ネットワーク使用説明 -->
<key>NSNetworkVolumesUsageDescription</key>
<string>RecRadikoはRadikoサービスに接続して番組を録音します。</string>

<!-- デスクトップフォルダアクセス説明 -->
<key>NSDesktopFolderUsageDescription</key>
<string>RecRadikoは録音したファイルをデスクトップに保存します。</string>

<!-- 通知用AppleEvents説明 -->
<key>NSAppleEventsUsageDescription</key>
<string>RecRadikoは録音完了時に通知を表示するためにAppleイベントを使用します。</string>

<!-- 不使用機能の明示 -->
<key>NSMicrophoneUsageDescription</key>
<string>RecRadikoはマイクを使用しません。</string>
<key>NSCameraUsageDescription</key>
<string>RecRadikoはカメラを使用しません。</string>
```

### 3. Entitlements（権限）設定

#### ファイル: `entitlements.plist`
```xml
<!-- ネットワーククライアント権限 -->
<key>com.apple.security.network.client</key>
<true/>

<!-- ファイル読み書き権限 -->
<key>com.apple.security.files.user-selected.read-write</key>
<true/>

<!-- Python実行用権限 -->
<key>com.apple.security.cs.allow-unsigned-executable-memory</key>
<true/>
<key>com.apple.security.cs.allow-jit</key>
<true/>

<!-- 動的ライブラリ権限 -->
<key>com.apple.security.cs.allow-dyld-environment-variables</key>
<true/>
```

### 4. 自動設定更新スクリプト

#### ファイル: `update_app_settings.py`
- Info.plist自動更新
- アイコンファイル自動コピー
- 実行権限自動設定
- エラーチェック機能

### 5. 署名スクリプト

#### ファイル: `sign_app.sh`
- アドホック署名（テスト用）
- Developer ID署名（配布用）
- 自動検証機能
- 段階的署名（内部バイナリ→フレームワーク→アプリ全体）

## 🛠️ 使用方法

### アイコン再生成
```bash
python create_icon.py
```

### 設定更新
```bash
python update_app_settings.py
```

### アプリケーション署名
```bash
# アドホック署名（ローカルテスト用）
./sign_app.sh
# オプション1を選択

# Developer ID署名（配布用）
./sign_app.sh
# オプション2を選択して証明書名を入力
```

## 🔍 設定の確認方法

### Info.plist確認
```bash
plutil -p dist/RecRadiko.app/Contents/Info.plist
```

### アイコン確認
```bash
# Finderで確認
open dist/RecRadiko.app -R
```

### 署名確認
```bash
codesign --verify --verbose dist/RecRadiko.app
codesign --display --verbose=4 dist/RecRadiko.app
```

## ⚠️ 注意事項

### CLIアプリケーション特有の設定
1. **LSUIElement = true**: Dockに表示されない
2. **コンソール出力**: Terminal.appで実行時のみ表示
3. **複数インスタンス**: 同時実行可能

### セキュリティ設定
1. **Hardened Runtime**: 署名時に`--options runtime`必須
2. **Entitlements**: Python実行に必要な権限を明示
3. **Gatekeeper**: 初回実行時の警告対応

### アイコン要件
1. **フォーマット**: .icns（複数解像度含む）
2. **最大サイズ**: 1024x1024（512x512@2x）
3. **透過**: RGBA対応

## 📊 テスト項目

### 基本動作テスト
- [ ] アプリケーションが起動する
- [ ] アイコンが正しく表示される
- [ ] Dockに表示されない（LSUIElement）
- [ ] ヘルプメッセージが表示される

### 権限テスト
- [ ] ネットワーク接続可能
- [ ] ファイル保存可能
- [ ] 通知表示可能（録音完了時）

### 署名テスト
- [ ] codesign検証成功
- [ ] Gatekeeper評価（Developer ID署名時）
- [ ] 初回起動時の警告確認

## 🔗 関連ドキュメント

- [MAC_APP_REQUIREMENTS.md](MAC_APP_REQUIREMENTS.md) - 要件定義
- [MAC_APP_BUILD_GUIDE.md](MAC_APP_BUILD_GUIDE.md) - ビルドガイド
- [Apple Developer - Info.plist](https://developer.apple.com/documentation/bundleresources/information_property_list)
- [Apple Developer - Entitlements](https://developer.apple.com/documentation/bundleresources/entitlements)

---

**作成日**: 2025年7月23日  
**更新日**: 2025年7月23日  
**ステータス**: Phase 2完了 - macOS固有設定実装済み