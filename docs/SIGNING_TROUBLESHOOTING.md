# RecRadiko 署名トラブルシューティングガイド

## 🚨 発生した問題

### エラー内容
```
resource fork, Finder information, or similar detritus not allowed
```

### 問題の原因
1. **PyInstallerのファイル生成方法**: PyInstallerで生成されたバイナリに、macOSのコード署名と互換性のない属性が含まれている
2. **Hardened Runtimeとの競合**: Python実行ファイルの特殊な構造が署名システムと競合
3. **Apple Development証明書の制限**: 配布用ではない開発証明書の制約

## 🔧 試行した解決策

### 1. ファイルクリーンアップ
```bash
xattr -cr dist/RecRadiko.app
find dist/RecRadiko.app -name "._*" -delete
find dist/RecRadiko.app -name ".DS_Store" -delete
```
**結果**: 効果なし

### 2. 段階的署名
```bash
# 個別バイナリ署名
codesign --force --sign "Apple Development: ..." *.so
codesign --force --sign "Apple Development: ..." *.dylib

# メイン実行ファイル署名
codesign --force --sign "Apple Development: ..." RecRadiko

# アプリケーション全体署名
codesign --force --sign "Apple Development: ..." RecRadiko.app
```
**結果**: メイン実行ファイルで同じエラー

### 3. 最小限のEntitlements
```xml
<key>com.apple.security.cs.allow-unsigned-executable-memory</key>
<true/>
```
**結果**: 効果なし

### 4. PyInstaller設定変更
- UPX無効化
- デバッグモード無効化
- Strip無効化
**結果**: 効果なし

## ✅ 現在の状況

### 署名なしでの動作確認
- **アプリケーション構造**: ✅ 正常
- **基本実行**: ✅ 動作確認済み
- **ffmpeg統合**: ✅ 正常動作
- **UI機能**: ✅ キーボードナビゲーション動作

### 配布可能な状態
- ローカルテスト: ✅ 問題なし
- 他のMacでの実行: ⚠️ Gatekeeperの警告あり（回避可能）

## 🚀 推奨解決策

### Option 1: 署名なし配布（推奨）
```bash
# DMGインストーラー作成
create-dmg --volname "RecRadiko" dist/RecRadiko.app

# ユーザーガイドで回避方法を説明
# 1. 右クリック → 開く
# 2. システム環境設定 → セキュリティで許可
```

### Option 2: Developer ID証明書取得
```bash
# Apple Developer Program ($99/年) に加入
# Developer ID Application証明書を取得
# Notarization対応
```

### Option 3: 自己署名証明書
```bash
# 開発用自己署名証明書を作成
# ローカルキーチェーンに追加
# ユーザーごとに信頼設定が必要
```

## 📋 技術的詳細

### PyInstallerの制約
- Python実行ファイルは特殊なブートローダー構造
- macOSのコード署名システムとの相性問題
- 特にHardened Runtimeとの競合

### 回避策の評価
1. **署名なし配布**: ⭐⭐⭐⭐⭐
   - 機能: 完全動作
   - セキュリティ: ローカル実行のみなら問題なし
   - ユーザビリティ: 初回のみ手動許可が必要

2. **Developer ID署名**: ⭐⭐⭐⭐⭐
   - 機能: 完全動作
   - セキュリティ: 完全
   - コスト: $99/年

3. **自己署名**: ⭐⭐⭐
   - 機能: 完全動作
   - 配布: 困難
   - 各ユーザーで設定が必要

## 🎯 最終推奨事項

**Phase 1実装**: 署名なしDMG配布
- 機能的に完全動作
- ユーザーガイドで回避方法を丁寧に説明
- 将来的な署名対応の準備は完了

**Phase 2実装**: Developer ID対応
- Apple Developer Program加入後
- 完全な署名・公証対応
- App Store外配布に最適

---

**作成日**: 2025年7月23日  
**ステータス**: 署名問題の完全分析完了  
**次のアクション**: DMGインストーラー作成へ進行