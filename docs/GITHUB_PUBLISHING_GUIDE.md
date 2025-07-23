# RecRadiko GitHub公開ガイド

## 📋 公開ポリシー

RecRadikoプロジェクトのGitHub公開において、セキュリティ・プライバシー・配布戦略を考慮した適切なファイル管理を行います。

## ✅ 公開対象ファイル

### コアアプリケーション
- `src/` - メインソースコード
- `tests/` - テストスイート
- `RecRadiko.py` - メインエントリーポイント
- `requirements.txt` - 本番用依存関係

### ドキュメント
- `README.md` - プロジェクト概要
- `CLAUDE.md` - 開発ガイドライン
- `docs/` - 技術ドキュメント（一部除外）

### 設定・リソース
- `config.json.template` - 設定テンプレート
- `assets/icon.icns` - アプリケーションアイコン
- `pytest.ini` - テスト設定

## ❌ 公開除外ファイル

### 🔒 セキュリティ・機密情報
```gitignore
# 認証・暗号化関連
config.json                    # 個人設定
encryption.key                 # 暗号化キー
*.key                          # その他の鍵ファイル
auth_cache.json               # 認証キャッシュ

# 実行時データ
radiko.db                     # 個人の番組履歴
*.log                         # ログファイル
errors.json                   # エラー情報
```

### 📦 macOSアプリケーション配布物
```gitignore
# PyInstallerビルド出力
build/                        # ビルド中間ファイル
dist/                         # 配布用アプリケーション
*.spec                        # PyInstaller設定

# DMGインストーラー
*.dmg                         # 配布用インストーラー
dmg_contents/                 # DMG作成中間ファイル
dmg_assets/                   # DMG素材

# 署名・証明書
entitlements.plist            # アプリケーション権限
simple_entitlements.plist     # 簡易権限設定
*.p12                         # 証明書
*.mobileprovision            # プロビジョニング
```

### 🔧 開発・テスト用ファイル
```gitignore
# 開発用スクリプト
debug_*.py                    # デバッグスクリプト
/test_*.py                    # ルートレベルテストファイル
fix_*.py                      # 修正用スクリプト
build_*.py                    # ビルドスクリプト
create_*.py                   # 作成スクリプト
sign_*.py                     # 署名スクリプト

# 大容量テストファイル
test_timefree_*.mp3           # テスト音声ファイル
*.wav, *.aac, *.flac         # その他音声ファイル

# 開発用依存関係
requirements-dev.txt          # 開発専用ライブラリ
```

### 📄 配布戦略文書
```gitignore
# インストールガイド
*Installation_Guide.md        # ユーザー向けインストール手順

# 署名・配布ドキュメント
DEVELOPER_ID_GUIDE.md         # Apple Developer登録手順
SIGNING_TROUBLESHOOTING.md    # 署名問題対処法
MAC_APP_*.md                  # macOSアプリ化詳細
```

### 🗂️ 実行時生成ファイル
```gitignore
# テスト・カバレッジ
htmlcov/                      # カバレッジレポート
.coverage                     # カバレッジデータ

# 一時ファイル
*.tmp, *.temp                 # 一時ファイル
__pycache__/                  # Pythonキャッシュ
```

## 🎯 公開戦略

### オープンソース方針
- **透明性**: 全コードを公開し、セキュリティ監査可能
- **コミュニティ**: Issue・PR歓迎
- **ライセンス**: MIT License（自由な利用・改変・配布）

### 配布戦略
1. **ソースコード**: GitHub Releases
2. **DMGインストーラー**: 別途配布（GitHub Release Assets）
3. **ドキュメント**: GitHub Pages（オプション）

### セキュリティ考慮事項
- **個人情報保護**: 設定ファイル・ログを除外
- **署名証明書**: 開発者固有情報を除外
- **API認証**: Radiko APIの悪用防止

## 📝 .gitignore設定

### 更新済み内容
RecRadikoプロジェクトの`.gitignore`に以下を追加：

```gitignore
# ==============================================================
# macOSアプリケーション化関連（GitHub公開不適切ファイル）
# ==============================================================

# PyInstallerビルド出力
build/
dist/
*.spec

# DMGインストーラー（配布物）
*.dmg
dmg_contents/
dmg_assets/

# macOSアプリケーション署名・証明書関連
entitlements.plist
simple_entitlements.plist
*.p12
*.mobileprovision

# 開発・テスト用スクリプト（本番環境外）
debug_*.py
/test_*.py
fix_*.py
rebuild_*.py
create_*.py
build_*.py
sign_*.py

# テスト音声ファイル（サイズが大きく不要）
test_timefree_*.mp3

# 開発用依存関係
requirements-dev.txt

# インストールガイド（配布方法情報）
*Installation_Guide.md

# 実行時設定ファイル
radiko.db
```

## 🚀 公開手順

### 1. 最終チェック
```bash
# 機密ファイルが含まれていないか確認
git status
git ls-files | grep -E "(\.key|config\.json|\.dmg|entitlements)"

# .gitignoreの動作確認
git check-ignore build/ dist/ *.dmg
```

### 2. コミット・プッシュ
```bash
# 変更をコミット
git add .gitignore
git commit -m "feat: GitHub公開用.gitignore更新 - macOSアプリ配布物除外"

# リモートにプッシュ
git push origin main
```

### 3. GitHub Release作成
1. **リリースタグ**: `v2.0.0`
2. **リリースタイトル**: "RecRadiko 2.0.0 - macOSアプリケーション対応"
3. **Assets追加**: `RecRadiko-2.0.0.dmg`（別途アップロード）

### 4. README更新
- macOSアプリ配布に関する情報追加
- インストール手順の簡易版
- セキュリティに関する説明

## ⚠️ 注意事項

### 既に追跡されているファイル
過去にコミットされた機密ファイルがある場合：

```bash
# Git履歴から完全削除（危険：慎重に実行）
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch encryption.key' \
  --prune-empty --tag-name-filter cat -- --all

# 強制プッシュ（コラボレーターに影響）
git push origin --force --all
```

### 分散開発時の考慮点
- 開発者ごとに個人設定ファイルを分離
- 証明書・署名は各開発者で個別管理
- 統一された開発環境構築手順を文書化

## 📊 公開効果

### メリット
- **透明性**: セキュリティ監査可能
- **コミュニティ**: 機能改善・バグ修正の協力
- **知識共有**: Radiko録音技術の普及

### リスク管理
- **個人情報**: 完全に除外済み
- **法的リスク**: Radiko利用規約準拠を明記
- **悪用防止**: 適切な利用ガイドライン提供

---

**作成日**: 2025年7月23日  
**最終更新**: 2025年7月23日  
**ステータス**: GitHub公開準備完了