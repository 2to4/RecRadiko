# 🤝 RecRadikoプロジェクトへの貢献

RecRadikoプロジェクトへの貢献をご検討いただき、ありがとうございます！このガイドは、貢献プロセスをスムーズに進めるための手順とガイドラインを提供します。

## 📋 貢献の種類

### 🐛 バグレポート
- 詳細な再現手順を記載
- 環境情報（OS、Pythonバージョン、FFmpegバージョン）を含める
- エラーログがある場合は添付

### ✨ 機能提案
- 提案の背景と目的を明確に説明
- 実装案や技術的な考慮事項があれば記載
- 既存機能への影響を検討

### 🔧 コード貢献
- バグ修正
- 新機能の実装
- パフォーマンス改善
- ドキュメント改善

## 🚀 開発環境のセットアップ

### 1. リポジトリのフォーク
```bash
# GitHubでリポジトリをフォーク後
git clone https://github.com/your-username/RecRadiko.git
cd RecRadiko
```

### 2. 開発環境の構築
```bash
# 依存関係のインストール
pip install -r requirements.txt

# 開発用依存関係のインストール
pip install pytest pytest-cov black flake8

# FFmpegのインストール（macOS）
brew install ffmpeg

# 設定ファイルの作成
cp config.json.template config.json
```

### 3. テストの実行
```bash
# 全テストの実行
python -m pytest tests/ -v

# 単体テストのみ
python -m pytest tests/test_*.py -v

# 結合テストのみ
python -m pytest tests/integration/ -v

# E2Eテストのみ
python -m pytest tests/e2e/ -v

# カバレッジ付きテスト
python -m pytest tests/ --cov=src --cov-report=html
```

## 📝 コード品質ガイドライン

### 🧪 テスト駆動開発（必須）
RecRadikoは**テスト駆動開発**を厳格に採用しています：

```bash
# 1. 変更前のテスト確認
python -m pytest tests/ -v

# 2. コード変更・実装

# 3. 変更後のテスト実行（必須）
python -m pytest tests/ -v

# 4. 新機能の場合、対応するテストケースを作成
```

**重要**: 全テストが成功していない変更はマージされません。

### 📐 コードスタイル
```bash
# コードフォーマット
black src/ tests/

# リント検査
flake8 src/ tests/

# 型チェック（推奨）
mypy src/
```

### 📖 ドキュメント
- 新機能には適切なdocstringを追加
- 必要に応じてREADMEやユーザーマニュアルを更新
- 技術的な変更は技術設計書も更新

## 🔄 プルリクエストプロセス

### 1. ブランチの作成
```bash
# 機能ブランチの作成
git checkout -b feature/your-feature-name

# バグ修正ブランチの作成
git checkout -b fix/bug-description
```

### 2. 変更の実装
- 小さく、論理的な単位でコミット
- 明確なコミットメッセージを記載
- テストケースの追加/更新

### 3. プルリクエストの作成
**プルリクエストテンプレート:**
```markdown
## 📝 変更内容
<!-- 変更の概要を記載 -->

## 🎯 変更の理由
<!-- なぜこの変更が必要かを説明 -->

## 🧪 テスト
- [ ] 既存テストが全て通過
- [ ] 新しいテストケースを追加
- [ ] 手動テストを実行

## 📋 チェックリスト
- [ ] コードスタイルガイドに準拠
- [ ] ドキュメントを更新
- [ ] 破壊的変更の場合は明記
```

### 4. レビュープロセス
- メンテナーによるコードレビュー
- 必要に応じて修正対応
- テスト結果の確認
- マージ

## 🌟 コミットメッセージ規約

### フォーマット
```
<type>(<scope>): <subject>

<body>

<footer>
```

### タイプ
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント変更
- `style`: コードスタイルの変更
- `refactor`: リファクタリング
- `test`: テストの追加・修正
- `chore`: その他の変更

### 例
```
feat(recording): add MP3 format support

実装したMP3フォーマット対応により、従来のAAC形式に加えて
MP3形式での録音が可能になりました。

Closes #123
```

## 🔍 品質基準

### 必須要件
- [ ] 全テストが成功（346/346）
- [ ] コードカバレッジ維持
- [ ] リント検査通過
- [ ] ドキュメント更新

### 推奨事項
- [ ] 型ヒントの追加
- [ ] パフォーマンステスト
- [ ] セキュリティ考慮

## 🆘 サポート

### 質問・相談
- GitHub Issuesで質問を投稿
- ディスカッションタブを活用

### 技術的な質問
- CLAUDE.mdで開発ガイドラインを確認
- 技術設計書で システム構造を理解

## 🙏 謝辞

RecRadikoプロジェクトへの貢献に感謝いたします。あなたの貢献により、より良いラジオ録音ソリューションが実現できます！